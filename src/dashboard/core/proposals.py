"""Suggestions from helpers and rows imported from a spreadsheet: checked, kept waiting, added only when a person accepts.

A batch comes either from a helper (`kind` "helper") or from a spreadsheet a person imported (`kind` "import",
decision 0080). Helpers only ever see their own batches: every helper query filters on `helper_id`, which an
import batch never has."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation

from dashboard.core import db, helpers, move_in, receipts
from dashboard.core.records import Records, ValidationError
from dashboard.core.schema import target_table
from dashboard.errors import PlainError

MAX_ENTRIES = 50
MAX_PER_DAY = 200
ALLOW_MORE = 200  # added to one helper's limit for today by each "Allow 200 more today" (decision 0101)
MAX_WAITING = 500  # suggestions one helper may have waiting on Review at once (decision 0085)
MAX_WHY = 300
MAX_KEY = 100
MAX_SOURCE_LINE = 200  # a receipt line, as the helper read it (decision 0097)
MAX_SOURCE_PRICE = 20
MAX_QUANTITY_HINT = 20  # an unmatched receipt line's amount, as text (decision 0105)
MAX_UNIT_HINT = 30
MAX_SHOP_LABEL = 80
UNMATCHED_LINE = receipts.UNMATCHED_LINE
LINE_KEYS = {"kind", "source", "receipt_date", "quantity_hint", "unit_hint"}
REQUEST_KEY = re.compile(r"^[A-Za-z0-9._:-]+$")
# Something shaped like a helper key (decision 0066). Keys belong only in the Authorization header.
KEY_LIKE = re.compile(re.escape(helpers.KEY_PREFIX) + r"[A-Za-z0-9_-]{8,}")
# Characters that are invisible or turn text around on screen: C0 controls except the newline, DEL, C1 controls,
# and the bidirectional embeddings, overrides and isolates (U+202A to U+202E, U+2066 to U+2069). Decision 0074.
HIDDEN_CHARACTERS = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")
NOT_FOUND = "That table or record could not be found. GET /api/v1/tables lists what this helper may use."
SCALARS = (str, int, float, bool, type(None))


class ProposalError(PlainError):
    """A request the helper API refuses: an HTTP status, a short code, a plain message and any problems found."""

    def __init__(self, status: int, code: str, message: str, problems: list[dict] | None = None):
        super().__init__(message)
        self.status, self.code, self.problems = status, code, problems or []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _title(info) -> str:
    """A table's friendly name, as labels.toml gives it."""
    return info.module.labels.get("tables", {}).get(info.table.name, {}).get("title") or info.table.title


def _bad(message: str = "This request could not be read. Check the fields and try again.") -> ProposalError:
    return ProposalError(400, "bad_request", message)


def today(now: datetime | None = None) -> tuple[str, str]:
    """The household's day: (its date, the moment it began in UTC as stored text). Decision 0101.

    The household's day is this computer's own calendar day, since Dashboard Plus runs on the household's
    computer. The daily limit and any "Allow 200 more today" both use this one boundary."""
    local = (now or datetime.now(timezone.utc)).astimezone()
    began = datetime.combine(local.date(), time()).astimezone()
    return local.date().isoformat(), began.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def used_today(conn: sqlite3.Connection, helper: helpers.Helper, now: datetime | None = None) -> int:
    """How many suggested rows this helper has sent since the household's day began."""
    began = today(now)[1]
    return conn.execute(
        "SELECT COUNT(*) FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
        "WHERE b.helper_id = ? AND p.created_at >= ?", (helper.id, began)).fetchone()[0]


def limit_today(conn: sqlite3.Connection, helper: helpers.Helper, now: datetime | None = None) -> int:
    """This helper's daily limit for today: 200, plus every "Allow 200 more today" pressed for today."""
    extra = conn.execute("SELECT COALESCE(SUM(extra), 0) FROM core__helper_allowances WHERE helper_id = ? "
                         "AND day = ?", (helper.id, today(now)[0])).fetchone()[0]
    return MAX_PER_DAY + int(extra)


def near_limit(conn: sqlite3.Connection, helper: helpers.Helper) -> dict | None:
    """For a helper that may suggest and has fewer than one full request (50) left today: what it has used.

    {"used": n, "limit": n, "left": n}, or None when it is not near its limit."""
    if not helper.active or not helper.may_suggest:
        return None
    used, limit = used_today(conn, helper), limit_today(conn, helper)
    if limit - used >= MAX_ENTRIES:
        return None
    return {"used": used, "limit": limit, "left": max(0, limit - used)}


class AllowanceRefused(PlainError):
    """More suggestions today could not be allowed for this helper (it is off, or may only look)."""


def allow_more(conn: sqlite3.Connection, helper_id: int, now: datetime | None = None) -> int:
    """A person pressed "Allow 200 more today" for a helper. Returns its new limit for today.

    Only for today (the household's day): tomorrow the limit is 200 again. Each press is a row of its own and a
    line in the history. Called only from a page's form with a one-use token, never from the helper API."""
    helper = helpers.get(conn, helper_id)
    if helper is None:
        raise AllowanceRefused("That helper could not be found.")
    if not helper.active:
        raise AllowanceRefused(f"{helper.name}'s access is off, so it cannot send suggestions.")
    if not helper.may_suggest:
        raise AllowanceRefused(f"{helper.name} may only look, so it has no suggestions to allow.")
    day = today(now)[0]
    at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds")
    with db.transaction(conn):
        allowance_id = conn.execute(
            "INSERT INTO core__helper_allowances (helper_id, day, extra, granted_at, granted_by) "
            "VALUES (?, ?, ?, ?, 'person')", (helper_id, day, ALLOW_MORE, at)).lastrowid
        conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                     "VALUES (?, 'person', 'helper_allow_more', 'core__helpers', ?, NULL, ?)",
                     (at, helper_id, json.dumps({"day": day, "extra": ALLOW_MORE, "allowance": allowance_id},
                                                sort_keys=True)))
    return limit_today(conn, helper, now)


def waiting_for(conn: sqlite3.Connection, helper: helpers.Helper) -> int:
    """How many of this helper's suggested rows are still waiting on Review. Imported rows never count."""
    return conn.execute(
        "SELECT COUNT(*) FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
        "WHERE b.helper_id = ? AND p.status = 'pending'", (helper.id,)).fetchone()[0]


def _texts(body):
    """Every piece of text in a request (names and values, at any depth), without recursion."""
    waiting = [body]
    while waiting:
        item = waiting.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            waiting.extend(item.keys())
            waiting.extend(item.values())
        elif isinstance(item, list):
            waiting.extend(item)


def _screen(body) -> None:
    """Refuse text that should never be kept: a helper key, or characters that hide or reverse text.

    Neither is ever repeated back, logged or stored."""
    texts = list(_texts(body))
    if any(KEY_LIKE.search(t) for t in texts):
        raise ProposalError(400, "looks_like_a_key",
                            "That looks like a helper key. Keys belong only in the Authorization header.")
    if any(HIDDEN_CHARACTERS.search(t) for t in texts):
        raise ProposalError(400, "hidden_characters",
                            "This request contains hidden control characters, such as marks that turn text "
                            "around on screen. Remove them and send it again. Line breaks are fine.")
    if any(receipts.looks_like_a_card(t) for t in texts):
        raise ProposalError(400, "payment_detail",
                            "This request contains a long number shaped like a payment card number. Leave card, "
                            "loyalty and account numbers out of receipt lines and send it again.")


def _read_source(source) -> dict:
    """An entry's optional `source`: the line it was read from and that line's price, as the helper wrote them.

    Screened like every other piece of the request (decision 0074) and kept only to show on Review (0097)."""
    if not isinstance(source, dict) or not source or set(source) - {"line", "price"}:
        raise _bad('A source must look like {"line": "KIDNEY BEANS 400G x2", "price": "3.80"}: the line, its '
                   'price, or both, as text.')
    cleaned = {}
    for name, longest in (("line", MAX_SOURCE_LINE), ("price", MAX_SOURCE_PRICE)):
        if name not in source:
            continue
        value = source[name]
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= longest:
            raise _bad(f"A source {name} must be text of 1 to {longest} characters.")
        cleaned[name] = value.strip()
    return cleaned


def _real_date(value) -> bool:
    """True for a real date written 2026-11-20."""
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _read_line(position: int, entry: dict) -> tuple[dict, dict]:
    """A receipt line the helper read but could not match to a record (decision 0105): (hints, source).

    It carries the line itself and, optionally, the date on the paper and the amount and unit as printed. These
    are hints shown on Review for the person to confirm, never values saved in the records."""
    if set(entry) - LINE_KEYS or entry.get("kind") != UNMATCHED_LINE:
        raise _bad(f'Entry {position}: a receipt line the helper could not match must look like {{"kind": '
                   f'"{UNMATCHED_LINE}", "source": {{"line": "TOM SPECIAL 400G 1 @ 1.50"}}}}, optionally with '
                   f'receipt_date, quantity_hint and unit_hint, and no table or values.')
    source = _read_source(entry.get("source"))
    if "line" not in source:
        raise _bad(f"Entry {position}: a receipt line the helper could not match needs the line itself, as "
                   f"source.line.")
    if receipts.not_a_good(source["line"]):
        raise _bad(f"Entry {position} looks like a total, tax, payment, coupon or refund line, not something "
                   f"bought. Leave it out, and tell the person about it in your conversation instead.")
    hints = {}
    if "receipt_date" in entry:
        if not _real_date(entry["receipt_date"]):
            raise _bad(f"Entry {position}: receipt_date must be a real date written 2026-11-20.")
        hints["receipt_date"] = entry["receipt_date"]
    if "quantity_hint" in entry:
        value = entry["quantity_hint"]
        try:
            number = Decimal(value.strip()) if isinstance(value, str) and len(value) <= MAX_QUANTITY_HINT else None
        except InvalidOperation:
            number = None
        if number is None or not number.is_finite() or number <= 0:
            raise _bad(f'Entry {position}: quantity_hint must be a number above 0, written as text, like "2" or '
                       f'"0.82" ({MAX_QUANTITY_HINT} characters at most).')
        hints["quantity_hint"] = value.strip()
    if "unit_hint" in entry:
        value = entry["unit_hint"]
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= MAX_UNIT_HINT:
            raise _bad(f'Entry {position}: unit_hint must be text of 1 to {MAX_UNIT_HINT} characters, like "tin".')
        hints["unit_hint"] = value.strip()
    return hints, source


def _read_context(value) -> dict:
    """A request's optional `receipt_context`: the purchase date on the paper and the shop's name (decision 0105)."""
    if not isinstance(value, dict) or set(value) - {"purchase_date", "shop_label"} or "purchase_date" not in value:
        raise _bad('A receipt_context must look like {"purchase_date": "2026-11-20", "shop_label": "Example Market"}; '
                   'the shop is optional.')
    if not _real_date(value["purchase_date"]):
        raise _bad("receipt_context.purchase_date must be a real date written 2026-11-20.")
    context = {"purchase_date": value["purchase_date"]}
    if "shop_label" in value:
        shop = value["shop_label"]
        if not isinstance(shop, str) or not 1 <= len(shop.strip()) <= MAX_SHOP_LABEL:
            raise _bad(f"receipt_context.shop_label must be text of 1 to {MAX_SHOP_LABEL} characters.")
        context["shop_label"] = shop.strip()
    return context


def _read_body(body) -> tuple[str, str, list[tuple[str | None, dict]], list[dict | None], dict | None]:
    """Check the shape of a request and return (request_key, why, [(table, values)], [source or None], context).

    A receipt line the helper could not match (decision 0105) is (None, its hints) in the list of entries."""
    _screen(body)
    if not isinstance(body, dict) or set(body) - {"request_key", "why", "entries", "receipt_context"}:
        raise _bad()
    key = body.get("request_key")
    if not isinstance(key, str) or not 1 <= len(key) <= MAX_KEY or not REQUEST_KEY.match(key):
        raise _bad("Give this request a key so a retry cannot add the same rows twice.")
    why = body.get("why")
    if not isinstance(why, str) or not 1 <= len(why.strip()) <= MAX_WHY:
        raise _bad("Say why, in a sentence, so the household knows where these came from.")
    entries = body.get("entries")
    if not isinstance(entries, list) or not entries:
        raise _bad()
    if len(entries) > MAX_ENTRIES:
        raise _bad(f"Send {MAX_ENTRIES} suggestions or fewer at a time.")
    context = _read_context(body["receipt_context"]) if "receipt_context" in body else None
    found, sources = [], []
    for position, entry in enumerate(entries):
        if isinstance(entry, dict) and "kind" in entry:
            hints, source = _read_line(position, entry)
            found.append((None, hints))
            sources.append(source)
            continue
        if not isinstance(entry, dict) or not {"table", "values"} <= set(entry) <= {"table", "values", "source"} \
                or not isinstance(entry["table"], str) or not isinstance(entry["values"], dict):
            raise _bad()
        found.append((entry["table"], entry["values"]))
        sources.append(_read_source(entry["source"]) if "source" in entry else None)
    return key, why.strip(), found, sources, context


def _body_hash(why: str, entries: list[tuple[str | None, dict]], sources: list[dict | None] | None = None,
               context: dict | None = None) -> str:
    """A fingerprint of a request. An entry without a source hashes exactly as it did before decision 0097, and a
    request with no receipt lines and no receipt context exactly as before decision 0105."""
    sources = sources or [None] * len(entries)
    shown = []
    for (t, v), s in zip(entries, sources):
        if t is None:
            shown.append([UNMATCHED_LINE, v, s])
        else:
            shown.append([t, v] if s is None else [t, v, s])
    body = {"why": why, "entries": shown}
    if context is not None:
        body["receipt_context"] = context
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


# ----- one entry pointing at an earlier one: {"ref": 0} (decision 0097) -------------------------------

def ref_of(value) -> int | None:
    """The earlier entry a value points at, if it is exactly {"ref": <whole number>}; otherwise None."""
    if isinstance(value, dict) and set(value) == {"ref"} and isinstance(value["ref"], int) \
            and not isinstance(value["ref"], bool):
        return value["ref"]
    return None


def refs_in(values: dict) -> dict[str, int]:
    """{field: earlier position} for every value of a suggestion that points at an earlier entry."""
    return {field: ref for field, value in values.items() if (ref := ref_of(value)) is not None}


def _ref_problem(registry: dict, entries: list[tuple[str, dict]], position: int, info, column, value) -> str | None:
    """Why a value that points at an earlier entry cannot be used, or None if it can."""
    if column.type != "link":
        return "can point at an earlier entry only when it links to one record."
    ref = ref_of(value)
    if ref is None:
        return 'must be a record id, or {"ref": N} where N is the position of an earlier entry in this request.'
    if not 0 <= ref < position:
        if not position:
            return "points at an earlier entry, but this is the first entry in the request."
        return f"points at entry {ref}, but it can only point at an earlier entry in this request (0 to {position - 1})."
    wanted, given = target_table(info.module.name, column), entries[ref][0]
    if given is None:
        return (f"points at entry {ref}, which is a receipt line the helper could not match, not a new record. "
                f"Only a new record can be pointed at.")
    if given != wanted:
        return (f"points at entry {ref}, which would add to {_title(registry[given])}, "
                f"but this field links to {_title(registry[wanted]) if wanted in registry else wanted}.")
    return None


def _resolve_refs(values: dict, made: dict[int, int]) -> dict:
    """For the dry run (Records.check_create): swap each {"ref": N} for the record entry N made there."""
    found = refs_in(values)
    missing = {field: f"points at entry {ref}, which could not be added, so this cannot be either."
               for field, ref in found.items() if ref not in made}
    if missing:
        raise ValidationError(missing)
    return dict(values, **{field: made[ref] for field, ref in found.items()})


def _renumbered(message: str, kept: list[int]) -> str:
    """A dry-run message names entries as the request numbers them, receipt lines included."""
    return re.sub(r"entry (\d+)", lambda m: f"entry {kept[int(m.group(1))]}" if int(m.group(1)) < len(kept)
                  else m.group(0), message)


def _check_tables(helper: helpers.Helper, registry: dict, entries: list[tuple[str, dict]]) -> None:
    """Refuse tables and fields this helper may not use, by name alone: no value is ever looked up.

    A table in a part it was not given is answered exactly like a table that does not exist. A link into such
    a part is refused the same way whatever ID is sent, so nothing is learned about records it cannot see."""
    for name, _values in entries:
        if name not in registry or registry[name].module.name not in helper.modules:
            raise ProposalError(404, "not_found", NOT_FOUND)
    hidden = sorted({field for name, values in entries for field in values
                     if field in {c.name for c in helpers.hidden_links(registry[name], helper, registry)}})
    if hidden:
        raise ProposalError(403, "not_allowed", f"This helper may not set {', '.join(hidden)}: it links to a part of "
                                                f"the records this helper was not given. Leave it out.")
    private = sorted({field for name, values in entries for field in values
                      if field in registry[name].table.columns and registry[name].table.columns[field].sensitive})
    if private:
        raise ProposalError(403, "private_detail",
                            f"Private details are never shared with helpers. Leave out: {', '.join(private)}.")


def _shape_problems(helper: helpers.Helper, registry: dict, entries: list[tuple[str, dict]]) -> list[dict]:
    """Problems found by looking at field names and kinds of value alone, before anything is tried."""
    problems = []
    for position, (name, values) in enumerate(entries):
        if name is None:  # a receipt line the helper could not match: its shape was checked when read
            continue
        info = registry[name]
        if not info.table.suggestions:
            problems.append({"entry": position, "table": name, "field": "",
                             "message": "A person fills this table in on its own screens, so helpers cannot "
                                        "suggest records for it."})
            continue
        needs_private = [c.name for c in info.table.columns.values() if c.sensitive and c.required]
        if needs_private:
            problems.append({"entry": position, "table": name, "field": "",
                             "message": "Helpers cannot add to this table, because it needs a private detail."})
            continue
        if any(c.required for c in helpers.hidden_links(info, helper, registry)):
            problems.append({"entry": position, "table": name, "field": "",
                             "message": "This helper cannot add to this table, because it needs a link to a part "
                                        "of the records this helper was not given."})
            continue
        for field, value in values.items():
            column = info.table.columns.get(field)
            if column is None:
                problems.append({"entry": position, "table": name, "field": field[:60],
                                 "message": "is not a field of this table."})
            elif isinstance(value, dict):
                wrong = _ref_problem(registry, entries, position, info, column, value)
                if wrong:
                    problems.append({"entry": position, "table": name, "field": field, "message": wrong})
            elif column.type == "file":
                problems.append({"entry": position, "table": name, "field": field,
                                 "message": "is a file, and helpers cannot suggest files."})
            elif not (isinstance(value, SCALARS) or (column.type == "links" and isinstance(value, list)
                                                    and all(isinstance(v, SCALARS) for v in value))):
                problems.append({"entry": position, "table": name, "field": field,
                                 "message": "must be a single value."})
    return problems


LINK_PROBLEMS = ("must point at a record.", "points at a record that does not exist or has been deleted.")


def _with_link_hint(registry: dict, name: str, field: str, message: str, conn=None, value=None) -> str:
    """A link that points nowhere, with the plain next step: look the record up first, or suggest it (0102).

    A link sent as a name or part of a path ("Shelf 3") also names the exact full-path matches and their ids,
    and says to ask the household when more than one matches (decision 0112)."""
    column = registry[name].table.columns.get(field) if name in registry else None
    if column is None or column.type not in ("link", "links") or message not in LINK_PROBLEMS:
        return message
    target = target_table(registry[name].module.name, column)
    title = _title(registry[target]) if target in registry else "the linked list"
    named = move_in.name_hint(conn, registry, target, value) if conn is not None else None
    if named:
        return (f"{message} {named} Look up {title} first (GET /api/v1/tables/{target}/records, or the "
                f"dashboard_list_records tool) and compare the full path, never only the last name. If it is not "
                f'there, suggest it earlier in this request and point at it with {{"ref": N}}.')
    return (f"{message} Look up {title} first (GET /api/v1/tables/{target}/records, or the dashboard_list_records "
            f"tool) and send the id of the one that matches. If it is not there, suggest it earlier in this request "
            f'and point at it with {{"ref": N}}.')


def _invalid(registry: dict, problems: list[dict]) -> ProposalError:
    tables = {p["table"] for p in problems}
    lead = f"{_title(registry[next(iter(tables))])}: some" if len(tables) == 1 else "Some"
    return ProposalError(422, "invalid", f"{lead} values could not be used. Nothing was saved.", problems)


def submit(conn: sqlite3.Connection, registry: dict, helper: helpers.Helper, body,
           queue_limit: int = MAX_WAITING) -> tuple[dict, bool]:
    """Check a helper's request and keep it waiting for the household. Returns (result, newly_created).

    All or nothing: if any entry is wrong, nothing is stored. The same `request_key` with the same body
    returns the first answer again. `registry` holds every table switched on. A request that would leave the
    helper with more than `queue_limit` suggestions waiting is refused whole (decision 0085)."""
    if not helper.may_suggest:
        raise ProposalError(403, "look_only", "This helper may look but not suggest changes. "
                                              "Ask the household to change its access in Settings.")
    key, why, entries, sources, context = _read_body(body)
    digest = _body_hash(why, entries, sources, context)
    stored = conn.execute("SELECT id, body_hash FROM core__helper_batches WHERE helper_id = ? AND request_key = ?",
                          (helper.id, key)).fetchone()
    if stored:
        return _same_or_refuse(conn, stored, digest, registry), False
    _check_limits(conn, helper, len(entries), queue_limit)
    line_table = None
    if any(name is None for name, _values in entries):  # receipt lines wait for a Stock in the person chooses
        line_table = receipts.line_table({n: i for n, i in registry.items() if i.module.name in helper.modules})
        if line_table is None:
            raise ProposalError(404, "not_found", "This helper has no list a receipt line could be added to. "
                                                  "GET /api/v1/tables lists what this helper may use.")
    _check_tables(helper, registry, [(n, v) for n, v in entries if n is not None])
    problems = _shape_problems(helper, registry, entries)
    if not problems:
        # A new item may carry its starting amount, use-by date and place, as the person's own add form does:
        # accepting it adds the item and its first batch together (decision 0102). Receipt lines are left out
        # of the dry run, and refs are counted among the records only.
        kept = [position for position, (name, _values) in enumerate(entries) if name is not None]
        index = {position: number for number, position in enumerate(kept)}
        dry = [(entries[p][0], {f: ({"ref": index[ref_of(v)]} if ref_of(v) in index else v)
                                for f, v in entries[p][1].items()}) for p in kept]
        wrong = Records(conn, registry).check_create(dry, helper.actor, starting_amounts=True,
                                                     resolve=_resolve_refs) if dry else {}
        problems = [{"entry": kept[number], "table": entries[kept[number]][0], "field": field[:60],
                     "message": _with_link_hint(registry, entries[kept[number]][0], field,
                                                _renumbered(message, kept), conn,
                                                entries[kept[number]][1].get(field))}
                    for number, fields in sorted(wrong.items()) for field, message in fields.items()]
    if problems:
        raise _invalid(registry, problems)
    now = _now()
    try:
        with db.transaction(conn):
            # A key turned off or replaced after this request was checked cannot still write (0093).
            if not helpers.still_current(conn, helper):
                raise ProposalError(401, "no_key", "This helper's access key is missing or no longer works. "
                                                   "Ask the household to check Helpers in Settings.")
            # Checked again inside the write lock, so two requests at the same moment cannot both pass (0088).
            _check_limits(conn, helper, len(entries), queue_limit)
            batch_id = conn.execute(
                "INSERT INTO core__helper_batches (helper_id, request_key, body_hash, why, created_at, receipt_json) "
                "VALUES (?, ?, ?, ?, ?, ?)", (helper.id, key, digest, why, now,
                                              json.dumps(context, sort_keys=True) if context else None)).lastrowid
            for position, ((name, values), source) in enumerate(zip(entries, sources)):
                kind = "record" if name is not None else "receipt_line"
                name = name or line_table
                proposal_id = conn.execute(
                    "INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at, source_json, "
                    "entry_kind) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (batch_id, position, name, json.dumps(values, sort_keys=True), now,
                     json.dumps(source, sort_keys=True) if source else None, kind)).lastrowid
                conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                             "VALUES (?, ?, 'propose', 'core__proposals', ?, NULL, ?, ?)",
                             (now, helper.actor, proposal_id, json.dumps({"table": name, "batch": batch_id}), batch_id))
    except sqlite3.IntegrityError:  # two identical requests at once: the second gets the first's answer
        stored = conn.execute("SELECT id, body_hash FROM core__helper_batches WHERE helper_id = ? AND request_key = ?",
                              (helper.id, key)).fetchone()
        if stored is None:
            raise
        return _same_or_refuse(conn, stored, digest, registry), False
    return batch_result(conn, batch_id, registry=registry), True


def _check_limits(conn: sqlite3.Connection, helper: helpers.Helper, adding: int, queue_limit: int) -> None:
    """The daily limit and the Review queue cap (decision 0085), refused whole if either would be passed."""
    limit, used = limit_today(conn, helper), used_today(conn, helper)
    if used + adding > limit:
        raise ProposalError(429, "daily_limit", daily_limit_message(limit, limit - used))
    waiting = waiting_for(conn, helper)
    if waiting + adding > queue_limit:
        raise ProposalError(429, "review_queue_full",
                            f"{waiting} suggestion{' from this helper is' if waiting == 1 else 's from this helper are'} "
                            f"already waiting on Review. Ask the household to look at them first.")


def daily_limit_message(limit: int, left: int = 0) -> str:
    """The plain refusal a helper gets when a request would pass its limit for today (decision 0101)."""
    if left > 0:
        lead = (f"This helper has {left} of its {limit} suggestions left for today, fewer than this request holds, "
                f"so nothing was saved.")
    else:
        lead = f"This helper has used all {limit} of its suggestions for today, so nothing was saved."
    return (f"{lead} Stop sending now and ask the household: they can allow more on the Review page in Dashboard "
            f"Plus (\"Allow {ALLOW_MORE} more today\"). Otherwise, try again tomorrow.")


def _same_or_refuse(conn, stored, digest: str, registry: dict | None = None) -> dict:
    if stored["body_hash"] != digest:
        raise ProposalError(409, "request_key_reused", "This request key was already used for different "
                                                        "suggestions. Check the earlier batch, then use a new key.")
    return batch_result(conn, stored["id"], registry=registry)


def batch_result(conn: sqlite3.Connection, batch_id: int, detail: bool = False, registry: dict | None = None) -> dict:
    """One batch as the helper sees it: its rows with their state. `detail` adds record ids, reasons and dates.
    With `registry`, a new item's starting amount sent with a Stock in for it is named under `warnings`."""
    batch = conn.execute("SELECT * FROM core__helper_batches WHERE id = ?", (batch_id,)).fetchone()
    rows = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? ORDER BY position", (batch_id,)).fetchall()
    proposals = []
    for r in rows:
        item = {"id": r["id"], "position": r["position"], "table": r["table_name"], "status": r["status"]}
        if r["entry_kind"] == "receipt_line":  # decision 0105: accepted means a person added a Stock in for it
            item["kind"] = UNMATCHED_LINE
        depends = sorted(set(refs_in(json.loads(r["values_json"])).values()))
        if depends:
            item["depends_on"] = depends
        if detail:
            item.update(record_id=r["record_id"], reason=r["reason"], decided_at=r["decided_at"])
        proposals.append(item)
    waiting = sum(1 for r in rows if r["status"] == "pending")
    lines = sum(1 for r in rows if r["status"] == "pending" and r["entry_kind"] == "receipt_line")
    if lines:
        ready = waiting - lines
        message = (f"{ready} suggestion{' is' if ready == 1 else 's are'} ready to check and {lines} receipt "
                   f"line{' needs' if lines == 1 else 's need'} the household's choice. Nothing has changed yet.")
    elif waiting:
        message = (f"{waiting} suggestion{' is' if waiting == 1 else 's are'} waiting for the household to review. "
                   f"Nothing changes until they accept {'it' if waiting == 1 else 'them'}.")
    else:
        message = "The household has decided on every suggestion in this batch."
    result = {"batch_id": batch_id, "state": "waiting" if waiting else "decided", "why": batch["why"],
              "proposals": proposals, "message": message}
    # A new item's starting amount and a Stock in for it in one send (decision 0112): allowed, but said plainly.
    twice = move_in.count_twice(registry, [dict(r, values=json.loads(r["values_json"])) for r in rows
                                           if r["entry_kind"] == "record"]) if rows and registry else {}
    if twice:
        result["warnings"] = [{"entry": position, "code": "may_count_twice", "message": words}
                              for position, words in sorted(twice.items())]
    if detail:
        result.update(request_key=batch["request_key"], created_at=batch["created_at"])
    return result


def helper_batches(conn: sqlite3.Connection, helper: helpers.Helper, after: int | None, limit: int) -> list[dict]:
    """This helper's own batches, newest first, with how many rows are in each state."""
    rows = conn.execute(
        "SELECT b.id, b.request_key, b.why, b.created_at, COUNT(p.id) AS total, "
        "COALESCE(SUM(p.status = 'pending'), 0) AS pending, COALESCE(SUM(p.status = 'accepted'), 0) AS accepted, "
        "COALESCE(SUM(p.status = 'rejected'), 0) AS rejected FROM core__helper_batches b "
        "LEFT JOIN core__proposals p ON p.batch_id = b.id WHERE b.helper_id = ? AND b.id < ? "
        "GROUP BY b.id ORDER BY b.id DESC LIMIT ?", (helper.id, after or 2 ** 62, limit)).fetchall()
    return [{"id": r["id"], "request_key": r["request_key"], "why": r["why"], "created_at": r["created_at"],
             "state": "waiting" if r["pending"] else "decided", "total": r["total"], "pending": r["pending"],
             "accepted": r["accepted"], "rejected": r["rejected"]} for r in rows]


def owns(conn: sqlite3.Connection, helper: helpers.Helper, batch_id: int) -> bool:
    return conn.execute("SELECT 1 FROM core__helper_batches WHERE id = ? AND helper_id = ?",
                        (batch_id, helper.id)).fetchone() is not None


# ----- a person's spreadsheet import (decision 0080) ---------------------------------------------------

MAX_SOURCE_NAME = 100


def source_label(file_name: str) -> str:
    """A file's name as shown on Review and in history: no folders, no hidden characters, at most 100 characters."""
    name = (file_name or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = HIDDEN_CHARACTERS.sub("", name).strip()
    return name[:MAX_SOURCE_NAME] or "spreadsheet.csv"


def import_actor(source_name: str) -> str:
    """Who an imported record's history names: "import:pantry.csv" (shown as "Import 'pantry.csv'")."""
    slug = re.sub(r"[^a-z0-9_.-]+", "-", source_name.lower()).strip("-.")[:60]
    return f"import:{slug or 'spreadsheet'}"


def stage_import(conn: sqlite3.Connection, source_name: str, rows: list[tuple[int, str, dict]],
                 receipt: dict | None = None) -> int:
    """Keep imported rows waiting for Review as one batch, and return its id. Nothing in the records changes.

    `rows` holds (spreadsheet row number, table, values), already checked by the caller with the same dry run
    helpers' suggestions get (Records.check_create). They are checked again, for real, on Accept. `receipt`
    ({"purchase_date": ...}) says the person ticked "These rows are from one receipt" (decision 0105)."""
    if not rows:
        raise PlainError("There are no rows ready to send.")
    source_name = source_label(source_name)
    entries = [(table, values) for _row, table, values in rows]
    why = f"{len(rows)} row{'' if len(rows) == 1 else 's'} from {source_name}, imported by you."
    now = _now()
    with db.transaction(conn):
        batch_id = conn.execute(
            "INSERT INTO core__helper_batches (kind, helper_id, source_name, request_key, body_hash, why, created_at, "
            "receipt_json) VALUES ('import', NULL, ?, ?, ?, ?, ?, ?)",
            (source_name, f"import-{secrets.token_hex(8)}", _body_hash(why, entries), why, now,
             json.dumps(_read_context(receipt), sort_keys=True) if receipt else None)).lastrowid
        for position, (row_number, table, values) in enumerate(rows):
            proposal_id = conn.execute(
                "INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at, source_row) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (batch_id, position, table, json.dumps(values, sort_keys=True), now, row_number)).lastrowid
            conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                         "VALUES (?, 'person', 'propose', 'core__proposals', ?, NULL, ?, ?)",
                         (now, proposal_id, json.dumps({"table": table, "batch": batch_id, "row": row_number}),
                          batch_id))
    return batch_id


# ----- the household's side: Review -------------------------------------------------------------------

def pending_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM core__proposals WHERE status = 'pending'").fetchone()[0]


def pending(conn: sqlite3.Connection) -> list[dict]:
    """Batches that still have rows waiting, newest first, each with its waiting rows and who it came from.

    `helper` names the author: the helper's name, or "Import 'pantry.csv'" for a person's import. Each row has
    its `source` (the line a helper read it from, or None) and `refs` ({field: earlier position}). `groups`
    holds the waiting rows again, gathered so that rows pointing at each other sit together (decision 0097),
    and `made` maps the position of each row already accepted to its new record's id. `records` holds every
    record row of the batch, decided or not, for the move-in checks on Review (decision 0112).

    `lines` holds the batch's receipt lines the helper could not match (decision 0105), waiting or decided: a
    batch with any stays here until the person presses "Finish receipt review", so a skip can be undone."""
    batches = conn.execute(
        "SELECT b.*, h.name AS helper_name, h.revoked_at AS helper_revoked_at FROM core__helper_batches b "
        "LEFT JOIN core__helpers h ON h.id = b.helper_id WHERE EXISTS "
        "(SELECT 1 FROM core__proposals p WHERE p.batch_id = b.id AND (p.status = 'pending' "
        "OR (p.entry_kind = 'receipt_line' AND b.finished_at IS NULL))) "
        "ORDER BY b.id DESC").fetchall()
    found = []
    for b in batches:
        every = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? ORDER BY position", (b["id"],)).fetchall()
        rows = [_row_dict(r) for r in every if r["status"] == "pending" and r["entry_kind"] == "record"]
        imported = b["kind"] == "import"
        found.append({"id": b["id"], "kind": b["kind"], "source_name": b["source_name"],
                      "helper": f"Import '{b['source_name']}'" if imported else b["helper_name"],
                      "helper_off": not imported and b["helper_revoked_at"] is not None,
                      "why": b["why"], "created_at": b["created_at"], "total": len(every),
                      "proposals": rows, "groups": _groups(rows),
                      "lines": [_row_dict(r) for r in every if r["entry_kind"] == "receipt_line"],
                      "receipt": json.loads(b["receipt_json"]) if b["receipt_json"] else None,
                      "decided": {"accepted": sum(1 for r in every if r["status"] == "accepted"),
                                  "rejected": sum(1 for r in every if r["status"] == "rejected"
                                                  and r["entry_kind"] == "record")},
                      "made": {r["position"]: r["record_id"] for r in every if r["status"] == "accepted"},
                      "records": [_row_dict(r) for r in every if r["entry_kind"] == "record"]})
    return found


def _row_dict(row) -> dict:
    values = json.loads(row["values_json"])
    return dict(row, values=values, refs=refs_in(values),
                source=json.loads(row["source_json"]) if row["source_json"] else None)


def _groups(rows: list[dict]) -> list[list[dict]]:
    """Waiting rows gathered so that a row and the waiting rows it points at are in one group, earliest first."""
    leader = {r["position"]: r["position"] for r in rows}

    def top(position: int) -> int:
        while leader[position] != position:
            position = leader[position]
        return position

    for r in rows:
        for ref in r["refs"].values():
            if ref in leader:
                leader[top(r["position"])] = top(ref)
    grouped: dict[int, list[dict]] = {}
    for r in rows:
        grouped.setdefault(top(r["position"]), []).append(r)
    return sorted(grouped.values(), key=lambda group: group[0]["position"])


def _audit(conn, action: str, proposal_id: int, after: dict | None, batch_id: int) -> None:
    conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                 "VALUES (?, 'person', ?, 'core__proposals', ?, NULL, ?, ?)",
                 (_now(), action, proposal_id, json.dumps(after, sort_keys=True) if after else None, batch_id))


ROW_QUERY = ("SELECT p.*, h.slug AS slug, b.helper_id AS helper_id, b.kind AS kind, b.source_name AS source_name "
             "FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
             "LEFT JOIN core__helpers h ON h.id = b.helper_id ")


def _load(conn, proposal_id: int):
    row = conn.execute(ROW_QUERY + "WHERE p.id = ?", (proposal_id,)).fetchone()
    if row is None:
        raise PlainError("That suggestion could not be found.")
    if row["status"] != "pending":
        raise PlainError("That suggestion has already been decided.")
    if row["entry_kind"] != "record":
        raise PlainError("That is a receipt line the helper could not match: choose an item for it or skip it.")
    return row


def _batch_rows(conn, batch_id: int) -> dict:
    """Every row of a batch, by position."""
    return {r["position"]: r for r in conn.execute(ROW_QUERY + "WHERE p.batch_id = ?", (batch_id,))}


def _why_not(store: Records, info, error: ValidationError) -> str:
    parts = []
    for field, message in error.problems.items():
        label = store._label(info, field) if field in info.table.columns else field
        parts.append(f"{label} {message}" if field else message)
    return "This can't be added as it is: " + " ".join(parts) + " Reject it, or add the record yourself."


def _table_title(registry: dict, name: str) -> str:
    return _title(registry[name]) if name in registry else name.split("__", 1)[0]


def _needed_first(conn, registry: dict, row) -> tuple[list, dict[int, int]]:
    """The waiting rows this one needs (directly or through others), earliest first and then itself, and the
    record ids of rows it needs that were already accepted. A needed row that was rejected refuses it."""
    rows = _batch_rows(conn, row["batch_id"])
    chain, made, seen, waiting = [], {}, set(), [row["position"]]
    while waiting:
        position = waiting.pop()
        if position in seen:
            continue
        seen.add(position)
        needed = row if position == row["position"] else rows.get(position)  # itself: always claimed below
        if needed is None or needed["status"] == "rejected":
            title = _table_title(registry, needed["table_name"]) if needed else "record"
            _keep_reason(conn, row["id"], f"This needs a new record in {title} suggested with it, which was "
                                          f"rejected. Reject this too, or add the record yourself.")
        if needed["status"] == "accepted":
            made[position] = needed["record_id"]
            continue
        chain.append(needed)
        waiting.extend(refs_in(json.loads(needed["values_json"])).values())
    return sorted(chain, key=lambda r: r["position"]), made


def _ready(conn, registry: dict, row) -> tuple:
    """(row, table, values, actor) for a row about to be added, or a PlainError with the reason kept on it."""
    info = registry.get(row["table_name"])
    if info is None:
        module = row["table_name"].split("__", 1)[0]
        _keep_reason(conn, row["id"], f"This is for {module}, which is switched off. Reject it, or switch it on "
                                      f"in Settings first.")
    values = json.loads(row["values_json"])
    if row["kind"] == "import":  # a person's own file: no helper limits apply, and the person decides here
        actor = import_actor(row["source_name"])
    else:
        actor = f"agent:{row['slug']}"
        _check_helper_links(conn, registry, info, row, values, row["id"])
    return row, info, values, actor


def _note_needed(conn, registry: dict, asked, failing) -> None:
    """When a row it needs cannot be added, say so on the row that was asked for too."""
    if failing["id"] != asked["id"]:
        with db.transaction(conn):
            conn.execute("UPDATE core__proposals SET reason = ? WHERE id = ? AND status = 'pending'",
                         (f"This needs a new record in {_table_title(registry, failing['table_name'])} above, "
                          f"which cannot be added yet: see the reason on it.", asked["id"]))


def accept(conn: sqlite3.Connection, registry: dict, proposal_id: int) -> tuple[str, int]:
    """Add the suggested (or imported) record. Returns (table, new record id).

    History names the helper ("agent:<slug>") or the file ("import:<name>") as the creator. A suggestion that
    points at another one waiting in its batch (decision 0097) adds that one first, in the same transaction.

    If the world has changed so the record can no longer be added, the suggestion stays waiting with the
    reason written on it, nothing else is changed, and a PlainError says why."""
    table, record_id, _also = accept_counted(conn, registry, proposal_id)
    return table, record_id


def accept_counted(conn: sqlite3.Connection, registry: dict, proposal_id: int) -> tuple[str, int, int]:
    """Accept, as above. Returns (table, new record id, how many rows it needed were added first)."""
    row = _load(conn, proposal_id)
    chain, made = _needed_first(conn, registry, row)
    plan = []
    for needed in chain:
        try:
            plan.append(_ready(conn, registry, needed))
        except PlainError:
            _note_needed(conn, registry, row, needed)
            raise
    store = Records(conn, registry)
    failing, failing_info = row, None
    receipts.guard(conn, registry, row["batch_id"])  # a possible repeat receipt waits for the person (0105)
    try:
        with db.transaction(conn):
            receipts.guard(conn, registry, row["batch_id"])  # again under the write lock
            for needed, info, values, actor in plan:
                failing, failing_info = needed, info
                _claim(conn, needed["id"], "accepted")  # first, so a second click or window cannot add it again
                values = dict(values, **{field: made[ref] for field, ref in refs_in(values).items()})
                record_id = store.create_in(needed["table_name"], values, actor=actor,
                                            review_status="confirmed", batch_id=needed["batch_id"])
                conn.execute(f"UPDATE {info.name} SET edited_by_person = 1 WHERE id = ?", (record_id,))
                conn.execute("UPDATE core__proposals SET record_id = ?, reason = NULL WHERE id = ?",
                             (record_id, needed["id"]))
                _audit(conn, "accept", needed["id"], {"table": info.name, "record_id": record_id}, needed["batch_id"])
                made[needed["position"]] = record_id
    except ValidationError as error:
        _note_needed(conn, registry, row, failing)
        _keep_reason(conn, failing["id"], _why_not(store, failing_info, error))
    return row["table_name"], made[row["position"]], len(plan) - 1


def _check_helper_links(conn, registry: dict, info, row, values: dict, proposal_id: int) -> None:
    """Refuse a helper's suggestion that sets a link into a part the helper was not given (decision 0074)."""
    helper = helpers.get(conn, row["helper_id"])
    if helper is None or set(values) & {c.name for c in helpers.hidden_links(info, helper, registry)}:
        # Refused when suggested since decision 0074; this catches anything kept from before, or a part since
        # switched off. The reason does not say which part, because the helper can read it.
        _keep_reason(conn, proposal_id, "This suggestion sets a link to a part of your records the helper was not "
                                        "given, so it cannot be added. Reject it, or add the record yourself.")


def _claim(conn, proposal_id: int, status: str) -> None:
    """Inside a transaction: decide a suggestion only if it is still waiting, or refuse.

    The check and the change are one statement, so two decisions at once cannot both win."""
    changed = conn.execute("UPDATE core__proposals SET status = ?, decided_at = ? WHERE id = ? AND status = 'pending'",
                           (status, _now(), proposal_id)).rowcount
    if changed != 1:
        raise PlainError("That suggestion has already been decided.")


def _keep_reason(conn, proposal_id: int, reason: str):
    """Write why a suggestion cannot be added on it (if it is still waiting), then refuse with that reason."""
    with db.transaction(conn):
        conn.execute("UPDATE core__proposals SET reason = ? WHERE id = ? AND status = 'pending'", (reason, proposal_id))
    raise PlainError(reason) from None


def reject(conn: sqlite3.Connection, proposal_id: int) -> str:
    """Say no to one suggestion, and to any waiting in its batch that need it. Nothing is added. Returns its table."""
    return reject_counted(conn, proposal_id)[0]


def reject_counted(conn: sqlite3.Connection, proposal_id: int) -> tuple[str, int]:
    """Reject, as above. Returns (table, how many rows that needed it were rejected with it)."""
    row = _load(conn, proposal_id)
    hit, needing = {row["position"]}, []
    for other in sorted(_batch_rows(conn, row["batch_id"]).values(), key=lambda r: r["position"]):
        if other["status"] == "pending" and set(refs_in(json.loads(other["values_json"])).values()) & hit:
            hit.add(other["position"])
            needing.append(other)
    also = 0
    with db.transaction(conn):
        _claim(conn, proposal_id, "rejected")
        _audit(conn, "reject", proposal_id, {"table": row["table_name"]}, row["batch_id"])
        for other in needing:
            also += conn.execute(
                "UPDATE core__proposals SET status = 'rejected', decided_at = ?, reason = ? WHERE id = ? "
                "AND status = 'pending'", (_now(), f"Rejected with entry {row['position']}, which it needed.",
                                           other["id"])).rowcount
            _audit(conn, "reject", other["id"], {"table": other["table_name"], "with": proposal_id}, row["batch_id"])
    return row["table_name"], also


def _waiting_ids(conn, batch_id: int) -> list[int]:
    """The batch's waiting suggested records. Receipt lines are never rejected with them: each is skipped by hand."""
    return [r["id"] for r in conn.execute(
        "SELECT id FROM core__proposals WHERE batch_id = ? AND status = 'pending' AND entry_kind = 'record' "
        "ORDER BY position", (batch_id,))]


def _still_waiting(conn, proposal_id: int):
    return conn.execute("SELECT * FROM core__proposals WHERE id = ? AND status = 'pending' AND entry_kind = 'record'",
                        (proposal_id,)).fetchone()


IN_GROUP_FAILED = ("This is added together with the rows in its group, and one of them cannot be added yet: see "
                   "the reason on it. Nothing in this group was added.")
NEEDS_FAILED = "This needs a suggestion above that cannot be added yet: see the reason on it."


def _hold(conn, ids_reasons: list[tuple[int, str]]) -> None:
    """Write a reason on each row that stays waiting."""
    with db.transaction(conn):
        for proposal_id, reason in ids_reasons:
            conn.execute("UPDATE core__proposals SET reason = ? WHERE id = ? AND status = 'pending'",
                         (reason, proposal_id))


def accept_group(conn: sqlite3.Connection, registry: dict, positions: set[int], batch_id: int,
                 tally: dict | None = None) -> tuple[int, list[str]]:
    """Accept the waiting rows of one group (decision 0101): all of them in one transaction, or none.

    Rows are added earliest first, so a new item is made before its Stock in. If any row cannot be added, nothing
    in the group is: the reason is kept on that row, and the others say why they wait. Returns (added, [one
    reason for each row still waiting]). `tally`, if given, counts what was added by table (decision 0105)."""
    rows = _batch_rows(conn, batch_id)
    made = {p: r["record_id"] for p, r in rows.items() if r["status"] == "accepted"}
    waiting = [rows[p] for p in sorted(positions) if p in rows and rows[p]["status"] == "pending"
               and rows[p]["entry_kind"] == "record"]
    if not waiting:
        return 0, []
    try:
        receipts.guard(conn, registry, batch_id)  # a possible repeat receipt waits for the person (0105)
    except receipts.RepeatHeld as held:
        return 0, [str(held)] * len(waiting)
    mine = {r["position"] for r in waiting}

    def needs(row, failing: int) -> bool:
        """True if `row` points at `failing`, directly or through another row of the group."""
        seen, todo = set(), list(refs_in(json.loads(row["values_json"])).values())
        while todo:
            ref = todo.pop()
            if ref == failing:
                return True
            if ref in mine and ref not in seen:
                seen.add(ref)
                todo.extend(refs_in(json.loads(rows[ref]["values_json"])).values())
        return False

    def fail(failing, reason: str) -> tuple[int, list[str]]:
        others = [(r["id"], NEEDS_FAILED if needs(r, failing["position"]) else IN_GROUP_FAILED)
                  for r in waiting if r["id"] != failing["id"]]
        _hold(conn, [(failing["id"], reason)] + others)
        return 0, [reason] + [why for _id, why in others]

    plan = []
    for row in waiting:
        for ref in refs_in(json.loads(row["values_json"])).values():
            if ref not in made and ref not in mine:  # the row it needs was rejected (or never existed)
                needed = rows.get(ref)
                title = _table_title(registry, needed["table_name"]) if needed else "record"
                return fail(row, f"This needs a new record in {title} suggested with it, which was rejected. "
                                 f"Reject this too, or add the record yourself.")
        try:
            plan.append(_ready(conn, registry, row))
        except PlainError as error:
            return fail(row, str(error))
    store = Records(conn, registry)
    failing, failing_info = waiting[0], None
    try:
        with db.transaction(conn):
            receipts.guard(conn, registry, batch_id)  # again under the write lock
            for row, info, values, actor in plan:
                failing, failing_info = row, info
                _claim(conn, row["id"], "accepted")  # first, so a second click or window cannot add it again
                values = dict(values, **{field: made[ref] for field, ref in refs_in(values).items()})
                record_id = store.create_in(row["table_name"], values, actor=actor,
                                            review_status="confirmed", batch_id=row["batch_id"])
                conn.execute(f"UPDATE {info.name} SET edited_by_person = 1 WHERE id = ?", (record_id,))
                conn.execute("UPDATE core__proposals SET record_id = ?, reason = NULL WHERE id = ?",
                             (record_id, row["id"]))
                _audit(conn, "accept", row["id"], {"table": info.name, "record_id": record_id}, row["batch_id"])
                made[row["position"]] = record_id
    except ValidationError as error:
        return fail(failing, _why_not(store, failing_info, error))
    except receipts.RepeatHeld as held:  # it became a possible repeat meanwhile: nothing here changed
        return 0, [str(held)] * len(waiting)
    except PlainError as error:
        if "already been decided" in str(error):  # decided meanwhile in another window: nothing here changed
            return 0, []
        return fail(failing, str(error))
    if tally is not None:
        for row, info, _values, _actor in plan:
            tally[info.name] = tally.get(info.name, 0) + 1
    return len(plan), []


def groups_of(conn: sqlite3.Connection, batch_id: int) -> list[set[int]]:
    """The positions of each group of waiting rows in a batch, as Review shows them (decision 0097)."""
    every = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? AND status = 'pending' "
                         "AND entry_kind = 'record' ORDER BY position", (batch_id,)).fetchall()
    return [{r["position"] for r in group} for group in _groups([_row_dict(r) for r in every])]


def accept_batch(conn: sqlite3.Connection, registry: dict, batch_id: int,
                 tally: dict | None = None) -> tuple[int, list[str]]:
    """Accept every waiting row of a batch, group by group, earliest first. Returns (added, [reasons for the rest]).

    Each group (a row and the rows it points at or that point at it) is one transaction: if any row of it cannot
    be added, none of the group is, and the reason stays on it. Other groups still go through (decision 0101).
    Receipt lines the helper could not match are never part of it: they wait for the person's choice (0105)."""
    added, failed = 0, []
    for group in groups_of(conn, batch_id):
        done, reasons = accept_group(conn, registry, group, batch_id, tally)
        added, failed = added + done, failed + reasons
    return added, failed


def _ticked_groups(conn, proposal_ids) -> list[tuple[int, set[int]]]:
    """(batch, positions) for every group that holds a ticked waiting row: ticking one row ticks its group."""
    wanted: dict[int, set[int]] = {}
    for proposal_id in proposal_ids:
        row = _still_waiting(conn, proposal_id)
        if row is not None:
            wanted.setdefault(row["batch_id"], set()).add(row["position"])
    found = []
    for batch_id in sorted(wanted, reverse=True):  # newest batch first, as Review lists them
        found += [(batch_id, group) for group in groups_of(conn, batch_id) if group & wanted[batch_id]]
    return found


def accept_ticked(conn: sqlite3.Connection, registry: dict, proposal_ids,
                  tally: dict | None = None) -> tuple[int, list[str]]:
    """Accept the ticked rows, each with the whole group it belongs to; each group is all or nothing."""
    added, failed = 0, []
    for batch_id, group in _ticked_groups(conn, proposal_ids):
        done, reasons = accept_group(conn, registry, group, batch_id, tally)
        added, failed = added + done, failed + reasons
    return added, failed


def reject_ticked(conn: sqlite3.Connection, proposal_ids) -> int:
    """Reject the ticked rows, each with the whole group it belongs to. Returns how many were rejected."""
    count = 0
    for batch_id, group in _ticked_groups(conn, proposal_ids):
        rows = _batch_rows(conn, batch_id)
        for position in sorted(group):
            if _still_waiting(conn, rows[position]["id"]) is not None:  # not already rejected with one it needed
                count += 1 + reject_counted(conn, rows[position]["id"])[1]
    return count


def reject_batch(conn: sqlite3.Connection, batch_id: int) -> int:
    """Reject every waiting row of a batch. Returns how many."""
    count = 0
    for proposal_id in _waiting_ids(conn, batch_id):
        if _still_waiting(conn, proposal_id) is not None:  # not already rejected with a row it needed
            count += 1 + reject_counted(conn, proposal_id)[1]
    return count
