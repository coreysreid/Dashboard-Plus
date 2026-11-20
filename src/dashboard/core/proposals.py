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
from datetime import datetime, timezone

from dashboard.core import db, helpers
from dashboard.core.records import Records, ValidationError
from dashboard.core.schema import target_table
from dashboard.errors import PlainError

MAX_ENTRIES = 50
MAX_PER_DAY = 200
MAX_WAITING = 500  # suggestions one helper may have waiting on Review at once (decision 0085)
MAX_WHY = 300
MAX_KEY = 100
MAX_SOURCE_LINE = 200  # a receipt line, as the helper read it (decision 0097)
MAX_SOURCE_PRICE = 20
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


def used_today(conn: sqlite3.Connection, helper: helpers.Helper) -> int:
    """How many suggested rows this helper has sent since midnight (UTC)."""
    midnight = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
    return conn.execute(
        "SELECT COUNT(*) FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
        "WHERE b.helper_id = ? AND p.created_at >= ?", (helper.id, midnight)).fetchone()[0]


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


def _read_body(body) -> tuple[str, str, list[tuple[str, dict]], list[dict | None]]:
    """Check the shape of a request and return (request_key, why, [(table, values)], [source or None])."""
    _screen(body)
    if not isinstance(body, dict) or set(body) - {"request_key", "why", "entries"}:
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
    found, sources = [], []
    for entry in entries:
        if not isinstance(entry, dict) or not {"table", "values"} <= set(entry) <= {"table", "values", "source"} \
                or not isinstance(entry["table"], str) or not isinstance(entry["values"], dict):
            raise _bad()
        found.append((entry["table"], entry["values"]))
        sources.append(_read_source(entry["source"]) if "source" in entry else None)
    return key, why.strip(), found, sources


def _body_hash(why: str, entries: list[tuple[str, dict]], sources: list[dict | None] | None = None) -> str:
    """A fingerprint of a request. An entry without a source hashes exactly as it did before decision 0097."""
    sources = sources or [None] * len(entries)
    text = json.dumps({"why": why, "entries": [[t, v] if s is None else [t, v, s]
                                               for (t, v), s in zip(entries, sources)]}, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        info = registry[name]
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
    key, why, entries, sources = _read_body(body)
    digest = _body_hash(why, entries, sources)
    stored = conn.execute("SELECT id, body_hash FROM core__helper_batches WHERE helper_id = ? AND request_key = ?",
                          (helper.id, key)).fetchone()
    if stored:
        return _same_or_refuse(conn, stored, digest), False
    _check_limits(conn, helper, len(entries), queue_limit)
    _check_tables(helper, registry, entries)
    problems = _shape_problems(helper, registry, entries)
    if not problems:
        wrong = Records(conn, registry).check_create(entries, helper.actor, resolve=_resolve_refs)
        problems = [{"entry": position, "table": entries[position][0], "field": field[:60], "message": message}
                    for position, fields in sorted(wrong.items()) for field, message in fields.items()]
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
                "INSERT INTO core__helper_batches (helper_id, request_key, body_hash, why, created_at) "
                "VALUES (?, ?, ?, ?, ?)", (helper.id, key, digest, why, now)).lastrowid
            for position, ((name, values), source) in enumerate(zip(entries, sources)):
                proposal_id = conn.execute(
                    "INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at, source_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (batch_id, position, name, json.dumps(values, sort_keys=True), now,
                                                  json.dumps(source, sort_keys=True) if source else None)).lastrowid
                conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                             "VALUES (?, ?, 'propose', 'core__proposals', ?, NULL, ?, ?)",
                             (now, helper.actor, proposal_id, json.dumps({"table": name, "batch": batch_id}), batch_id))
    except sqlite3.IntegrityError:  # two identical requests at once: the second gets the first's answer
        stored = conn.execute("SELECT id, body_hash FROM core__helper_batches WHERE helper_id = ? AND request_key = ?",
                              (helper.id, key)).fetchone()
        if stored is None:
            raise
        return _same_or_refuse(conn, stored, digest), False
    return batch_result(conn, batch_id), True


def _check_limits(conn: sqlite3.Connection, helper: helpers.Helper, adding: int, queue_limit: int) -> None:
    """The daily limit and the Review queue cap (decision 0085), refused whole if either would be passed."""
    if used_today(conn, helper) + adding > MAX_PER_DAY:
        raise ProposalError(429, "daily_limit", f"This helper has reached {MAX_PER_DAY} suggestions today. "
                                                f"Try again tomorrow.")
    waiting = waiting_for(conn, helper)
    if waiting + adding > queue_limit:
        raise ProposalError(429, "review_queue_full",
                            f"{waiting} suggestion{' from this helper is' if waiting == 1 else 's from this helper are'} "
                            f"already waiting on Review. Ask the household to look at them first.")


def _same_or_refuse(conn, stored, digest: str) -> dict:
    if stored["body_hash"] != digest:
        raise ProposalError(409, "request_key_reused", "This request key was already used for different "
                                                        "suggestions. Check the earlier batch, then use a new key.")
    return batch_result(conn, stored["id"])


def batch_result(conn: sqlite3.Connection, batch_id: int, detail: bool = False) -> dict:
    """One batch as the helper sees it: its rows with their state. `detail` adds record ids, reasons and dates."""
    batch = conn.execute("SELECT * FROM core__helper_batches WHERE id = ?", (batch_id,)).fetchone()
    rows = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? ORDER BY position", (batch_id,)).fetchall()
    proposals = []
    for r in rows:
        item = {"id": r["id"], "position": r["position"], "table": r["table_name"], "status": r["status"]}
        depends = sorted(set(refs_in(json.loads(r["values_json"])).values()))
        if depends:
            item["depends_on"] = depends
        if detail:
            item.update(record_id=r["record_id"], reason=r["reason"], decided_at=r["decided_at"])
        proposals.append(item)
    waiting = sum(1 for r in rows if r["status"] == "pending")
    if waiting:
        message = (f"{waiting} suggestion{' is' if waiting == 1 else 's are'} waiting for the household to review. "
                   f"Nothing changes until they accept {'it' if waiting == 1 else 'them'}.")
    else:
        message = "The household has decided on every suggestion in this batch."
    result = {"batch_id": batch_id, "state": "waiting" if waiting else "decided", "why": batch["why"],
              "proposals": proposals, "message": message}
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


def stage_import(conn: sqlite3.Connection, source_name: str, rows: list[tuple[int, str, dict]]) -> int:
    """Keep imported rows waiting for Review as one batch, and return its id. Nothing in the records changes.

    `rows` holds (spreadsheet row number, table, values), already checked by the caller with the same dry run
    helpers' suggestions get (Records.check_create). They are checked again, for real, on Accept."""
    if not rows:
        raise PlainError("There are no rows ready to send.")
    source_name = source_label(source_name)
    entries = [(table, values) for _row, table, values in rows]
    why = f"{len(rows)} row{'' if len(rows) == 1 else 's'} from {source_name}, imported by you."
    now = _now()
    with db.transaction(conn):
        batch_id = conn.execute(
            "INSERT INTO core__helper_batches (kind, helper_id, source_name, request_key, body_hash, why, created_at) "
            "VALUES ('import', NULL, ?, ?, ?, ?, ?)",
            (source_name, f"import-{secrets.token_hex(8)}", _body_hash(why, entries), why, now)).lastrowid
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
    and `made` maps the position of each row already accepted to its new record's id."""
    batches = conn.execute(
        "SELECT b.*, h.name AS helper_name, h.revoked_at AS helper_revoked_at FROM core__helper_batches b "
        "LEFT JOIN core__helpers h ON h.id = b.helper_id WHERE EXISTS "
        "(SELECT 1 FROM core__proposals p WHERE p.batch_id = b.id AND p.status = 'pending') "
        "ORDER BY b.id DESC").fetchall()
    found = []
    for b in batches:
        every = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? ORDER BY position", (b["id"],)).fetchall()
        rows = [_row_dict(r) for r in every if r["status"] == "pending"]
        imported = b["kind"] == "import"
        found.append({"id": b["id"], "kind": b["kind"], "source_name": b["source_name"],
                      "helper": f"Import '{b['source_name']}'" if imported else b["helper_name"],
                      "helper_off": not imported and b["helper_revoked_at"] is not None,
                      "why": b["why"], "created_at": b["created_at"], "total": len(every),
                      "proposals": rows, "groups": _groups(rows),
                      "made": {r["position"]: r["record_id"] for r in every if r["status"] == "accepted"}})
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
    try:
        with db.transaction(conn):
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
    return [r["id"] for r in conn.execute(
        "SELECT id FROM core__proposals WHERE batch_id = ? AND status = 'pending' ORDER BY position", (batch_id,))]


def _still_waiting(conn, proposal_id: int):
    return conn.execute("SELECT * FROM core__proposals WHERE id = ? AND status = 'pending'", (proposal_id,)).fetchone()


def accept_batch(conn: sqlite3.Connection, registry: dict, batch_id: int) -> tuple[int, list[str]]:
    """Accept every waiting row of a batch, earliest first. Returns (added, [reasons for the rest]).

    Each row is its own transaction, together with any row it needs. A row that needs one that could not be
    added is not tried; it stays waiting with that reason on it."""
    added, failed, blocked = 0, [], set()
    for proposal_id in _waiting_ids(conn, batch_id):
        row = _still_waiting(conn, proposal_id)
        if row is None:  # already added, because a row before it needed it
            continue
        if set(refs_in(json.loads(row["values_json"])).values()) & blocked:
            blocked.add(row["position"])
            reason = "This needs a suggestion above that cannot be added yet: see the reason on it."
            with db.transaction(conn):
                conn.execute("UPDATE core__proposals SET reason = ? WHERE id = ?", (reason, proposal_id))
            failed.append(reason)
            continue
        try:
            _table, _record, also = accept_counted(conn, registry, proposal_id)
            added += 1 + also
        except PlainError as error:
            blocked.add(row["position"])
            failed.append(str(error))
    return added, failed


def reject_batch(conn: sqlite3.Connection, batch_id: int) -> int:
    """Reject every waiting row of a batch. Returns how many."""
    count = 0
    for proposal_id in _waiting_ids(conn, batch_id):
        if _still_waiting(conn, proposal_id) is not None:  # not already rejected with a row it needed
            count += 1 + reject_counted(conn, proposal_id)[1]
    return count
