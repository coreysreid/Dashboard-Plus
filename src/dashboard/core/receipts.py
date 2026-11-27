"""Receipt lines a helper could not match, and receipts sent twice: kept on Review, decided only by a person (0105).

A receipt line the helper read but could not match waits on Review as its own kind of row. Only a person turns it
into a Stock in, by choosing the item (or making a new one) and confirming the amount and date; or skips it. A
batch that says it is one receipt is compared with earlier ones by what it would add (the date, the item, the
amount and its unit), never by the receipt's text or a stored fingerprint. An exact match waits until the person
rejects this copy or keeps it as another purchase."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from dashboard.core import actions, dates, db, fraud_guard
from dashboard.core.records import Records
from dashboard.core.schema import target_table
from dashboard.core.units import _SINGULAR, unit_for
from dashboard.errors import PlainError

UNMATCHED_LINE = "unmatched_product_line"
EARLIER_LIMIT = 1000  # receipts compared, newest first: enough for years of shopping, and always bounded
# A line that is a total, tax, payment, change, coupon or refund: never a good that was bought.
_NOT_A_GOOD = re.compile(r"^\W*(sub\s*-?\s*total|total|tax|gst|vat|change|cash|card|eftpos|visa|mastercard|amex|"
                         r"coupon|discount|refund|payment|balance|rounding|savings?|loyalty|points)\b", re.I)


class RepeatHeld(PlainError):
    """Accepting is held: this batch may be a receipt already sent, and the person has not chosen yet."""


class LineStale(PlainError):
    """The chosen Stock item changed while the person was checking the line."""


STALE = ("This Stock item changed while you were checking the line. Check its current amount and try again. "
         "Nothing was added.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def not_a_good(line: str) -> bool:
    """True for a receipt line that is a total, tax, payment, coupon or refund rather than something bought."""
    return bool(_NOT_A_GOOD.match(line or ""))


def looks_like_a_card(text: str) -> bool:
    """True if the text holds a payment card number: the one check every text value gets (decision 0141).

    13 to 19 digits passing the card check digit (Luhn); a shop barcode with its own valid check digit is not one."""
    return fraud_guard.has_card_number(text)


# ----- which table a receipt line becomes -------------------------------------------------------------

def line_table(registry: dict) -> str | None:
    """The table a receipt line becomes a record in: one whose records add to or take from a batch of an item
    (Stock in and out). None if the registry (a helper's grant, say) has none."""
    for name, info in registry.items():
        rule = info.table.adjusts
        if rule and rule.get("belongs_to") and rule.get("adds"):
            return name
    return None


def owner_of(registry: dict, info):
    """The table a movement belongs to (Stock items), from its `belongs_to` link."""
    column = info.table.columns[info.table.adjusts["belongs_to"]]
    return registry.get(target_table(info.module.name, column))


def date_column(info) -> str | None:
    """The movement's own date: its first required date field (Date, `happened_on`)."""
    return next((c.name for c in info.table.columns.values() if c.type == "date" and c.required), None)


def _norm_unit(unit) -> str:
    word = (unit or "").strip().lower()
    return _SINGULAR.get(word, word)


def _norm_name(name) -> str:
    return " ".join(str(name or "").lower().split())


def _amount(value) -> str | None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return format(number.normalize(), "f")


def units_fit(hint: str | None, unit: str | None) -> bool:
    """True when a helper's unit hint is the item's own unit (tin and tins match; 12PK and tins do not)."""
    if not hint:
        return True
    return _norm_unit(hint) == _norm_unit(unit) or _norm_unit(hint) == _norm_unit(unit).rstrip("s")


# ----- deciding a receipt line ------------------------------------------------------------------------

def _audit(conn, action: str, table: str, record_id: int, after: dict | None, batch_id: int | None) -> None:
    conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                 "VALUES (?, 'person', ?, ?, ?, NULL, ?, ?)",
                 (_now(), action, table, record_id, json.dumps(after, sort_keys=True) if after else None, batch_id))


def line(conn: sqlite3.Connection, line_id: int):
    """One receipt line with its batch, or a PlainError if there is none."""
    row = conn.execute("SELECT p.*, b.finished_at AS finished_at, b.helper_id AS helper_id, h.name AS helper_name, "
                       "b.kind AS batch_kind, b.source_name AS source_name FROM core__proposals p "
                       "JOIN core__helper_batches b ON b.id = p.batch_id LEFT JOIN core__helpers h ON h.id = b.helper_id "
                       "WHERE p.id = ? AND p.entry_kind = 'receipt_line'", (line_id,)).fetchone()
    if row is None:
        raise PlainError("That receipt line could not be found.")
    return row


def add_for_line(store: Records, line_id: int, amount, happened_on: str | None, item_id: int | None = None,
                 seen_revision: int | None = None, new_item: dict | None = None,
                 price: dict | None = None) -> int:
    """A person chose what a receipt line added: one Stock in, saved once. Returns the new Stock in's id.

    Either `item_id` (an item already in Stock, with the revision the person saw) or `new_item` (the values of a
    new item, added in the same transaction). The line's own text and hints are never copied into either. If
    the item changed since the person looked, LineStale and nothing is saved; a second press finds the line
    already decided and adds nothing.

    `price` is what the person typed in "Save a price with this Stock in?" (decision 0133): saved with the Stock in
    or not at all. The line's own price text is never used for it."""
    conn, registry = store.conn, store.registry
    row = line(conn, line_id)
    if row["status"] != "pending":
        raise PlainError("This receipt line was already decided. Nothing more was added.")
    info = registry.get(row["table_name"])
    if info is None:
        raise PlainError("This line is for a part of your records that is switched off. Skip it, or switch that part "
                         "on in Settings first.")
    rule, owner = info.table.adjusts, owner_of(registry, info)
    with db.transaction(conn):
        changed = conn.execute("UPDATE core__proposals SET status = 'accepted', decided_at = ? WHERE id = ? "
                               "AND status = 'pending' AND entry_kind = 'receipt_line'", (_now(), line_id)).rowcount
        if changed != 1:
            raise PlainError("This receipt line was already decided. Nothing more was added.")
        if new_item is None:
            current = conn.execute(f"SELECT id FROM {owner.name} WHERE id = ? AND deleted_at IS NULL",
                                   (item_id,)).fetchone()
            if current is None or seen_revision is None or \
                    actions.revision(store, owner, int(item_id)) != int(seen_revision):
                raise LineStale(STALE)
        else:
            item_id = store.create_in(owner.name, new_item, actor="person", batch_id=row["batch_id"])
        values = {rule["belongs_to"]: int(item_id), rule["direction"]: rule["adds"][0], rule["amount"]: amount}
        when = date_column(info)
        if when and happened_on:
            values[when] = happened_on
        if price:
            values.update(price)
        movement = store.create_in(info.name, values, actor="person", batch_id=row["batch_id"])
        conn.execute("UPDATE core__proposals SET record_id = ?, reason = NULL WHERE id = ?", (movement, line_id))
        _audit(conn, "line_add", "core__proposals", line_id,
               {"table": info.name, "record_id": movement, "item": int(item_id), "new_item": new_item is not None},
               row["batch_id"])
    return movement


def skip(conn: sqlite3.Connection, line_id: int) -> None:
    """Skip a receipt line: nothing is added anywhere. It can be undone until the receipt review is finished."""
    row = line(conn, line_id)
    with db.transaction(conn):
        changed = conn.execute("UPDATE core__proposals SET status = 'rejected', decided_at = ?, reason = NULL "
                               "WHERE id = ? AND status = 'pending' AND entry_kind = 'receipt_line'",
                               (_now(), line_id)).rowcount
        if changed != 1:
            raise PlainError("This receipt line was already decided.")
        _audit(conn, "line_skip", "core__proposals", line_id, None, row["batch_id"])


def undo_skip(conn: sqlite3.Connection, line_id: int) -> None:
    """Put a skipped line back to waiting. Never adds anything. Refused once the receipt review is finished."""
    row = line(conn, line_id)
    if row["finished_at"]:
        raise PlainError("This receipt review is finished, so the skip stays. Nothing was added for this line.")
    with db.transaction(conn):
        changed = conn.execute(
            "UPDATE core__proposals SET status = 'pending', decided_at = NULL WHERE id = ? AND status = 'rejected' "
            "AND entry_kind = 'receipt_line' AND (SELECT finished_at FROM core__helper_batches WHERE id = ?) IS NULL",
            (line_id, row["batch_id"])).rowcount
        if changed != 1:
            raise PlainError("This line is not skipped any more.")
        _audit(conn, "line_unskip", "core__proposals", line_id, None, row["batch_id"])


def outcome(conn: sqlite3.Connection, batch_id: int) -> dict:
    """How a receipt's rows were decided: rows added, rows rejected, lines skipped and anything still waiting."""
    found = {"added": 0, "rejected": 0, "skipped": 0, "waiting": 0}
    for r in conn.execute("SELECT status, entry_kind FROM core__proposals WHERE batch_id = ?", (batch_id,)):
        if r["status"] == "pending":
            found["waiting"] += 1
        elif r["status"] == "accepted":
            found["added"] += 1
        elif r["entry_kind"] == "receipt_line":
            found["skipped"] += 1
        else:
            found["rejected"] += 1
    return found


def outcome_text(found: dict) -> str:
    """"2 rows added; 1 line skipped. No Stock was added for the skipped line." """
    added = found["added"]
    parts = [f"{added} row{'' if added == 1 else 's'} added"]
    if found["rejected"]:
        parts.append(f"{found['rejected']} rejected")
    skipped = found["skipped"]
    if skipped:
        parts.append(f"{skipped} line{'' if skipped == 1 else 's'} skipped")
    text = "; ".join(parts) + "."
    if skipped:
        text += f" No Stock was added for the skipped line{'' if skipped == 1 else 's'}."
    return text


def finish(conn: sqlite3.Connection, batch_id: int) -> dict:
    """"Finish receipt review": close a receipt whose rows and lines are all decided, so skips stay skipped."""
    found = outcome(conn, batch_id)
    if found["waiting"]:
        raise PlainError("Some rows of this receipt are still waiting. Decide them first.")
    with db.transaction(conn):
        changed = conn.execute("UPDATE core__helper_batches SET finished_at = ? WHERE id = ? AND finished_at IS NULL",
                               (_now(), batch_id)).rowcount
        if changed:
            _audit(conn, "receipt_finish", "core__helper_batches", batch_id, found, batch_id)
    return found


# ----- a receipt sent twice ---------------------------------------------------------------------------

class _Items:
    """Item names and units looked up once each."""

    def __init__(self, conn, owner):
        self.conn, self.owner, self.seen = conn, owner, {}

    def get(self, item_id) -> tuple[str, str]:
        if item_id not in self.seen:
            row = None
            if self.owner is not None:
                unit = "unit" if "unit" in self.owner.table.columns else "NULL"
                name = next((c.name for c in self.owner.table.columns.values() if c.type == "text"), None)
                row = self.conn.execute(f"SELECT {name or 'NULL'} AS name, {unit} AS unit FROM {self.owner.name} "
                                        f"WHERE id = ?", (item_id,)).fetchone()
            self.seen[item_id] = (row["name"] or "", row["unit"] or "") if row else ("", "")
        return self.seen[item_id]


def _receipt_rows(conn, registry, batch_ids: list[int]) -> dict[int, list]:
    rows: dict[int, list] = {b: [] for b in batch_ids}
    for start in range(0, len(batch_ids), 500):
        chunk = batch_ids[start:start + 500]
        for r in conn.execute(f"SELECT * FROM core__proposals WHERE batch_id IN ({', '.join('?' * len(chunk))}) "
                              f"ORDER BY batch_id, position", chunk):
            rows[r["batch_id"]].append(r)
    return rows


def _basket(conn, registry, rows: list, context: dict | None, items: _Items) -> tuple[list[tuple], dict, bool]:
    """What one batch would add or has added: ([(date, item, amount, unit)], {state: count}, lines waiting).

    `item` is ("id", record id) for an item already in Stock, or ("new", name, unit) for one suggested with it,
    which is only a guess until a person accepts it. Rejected rows and skipped lines are not part of it. A row's
    state is "waiting", "added" or "undone" (its Stock in was deleted later)."""
    by_position = {r["position"]: r for r in rows}
    purchase = (context or {}).get("purchase_date")
    basket, states, lines_waiting = [], Counter(), False
    for r in rows:
        if r["status"] == "rejected":
            continue
        info = registry.get(r["table_name"])
        if r["entry_kind"] == "receipt_line":
            if r["status"] == "pending":
                lines_waiting = True
                continue
            values = _movement(conn, info, r["record_id"])
            if values is None:
                states["undone"] += 1
                continue
        else:
            values = json.loads(r["values_json"])
        state = "waiting" if r["status"] == "pending" else "added"
        if r["status"] == "accepted" and info is not None and r["entry_kind"] == "record":
            live = conn.execute(f"SELECT deleted_at FROM {info.name} WHERE id = ?", (r["record_id"],)).fetchone()
            if live is None or live["deleted_at"]:
                state = "undone"
        states[state] += 1
        rule = info.table.adjusts if info is not None else None
        if not rule or not rule.get("belongs_to"):
            continue
        direction = values.get(rule["direction"], info.table.columns[rule["direction"]].default)
        if direction not in rule["adds"]:
            continue
        owner = values.get(rule["belongs_to"])
        ref = owner.get("ref") if isinstance(owner, dict) else None
        if ref is not None:
            needed = by_position.get(ref)
            if needed is not None and needed["status"] == "accepted" and needed["record_id"]:
                owner = needed["record_id"]
            else:
                suggested = json.loads(needed["values_json"]) if needed is not None else {}
                name = next((v for k, v in suggested.items() if k == "name"), "")
                identity = ("new", _norm_name(name), _norm_unit(suggested.get("unit")))
                basket.append((values.get(date_column(info)) or purchase, identity,
                               _amount(values.get(rule["amount"])), identity[2]))
                continue
        if not isinstance(owner, int) or isinstance(owner, bool):
            continue
        basket.append((values.get(date_column(info)) or purchase, ("id", owner),
                       _amount(values.get(rule["amount"])), _norm_unit(items.get(owner)[1])))
    return basket, dict(states), lines_waiting


def _movement(conn, info, record_id) -> dict | None:
    """A Stock in a person added for a receipt line, as values, or None if it was deleted since."""
    if info is None or not record_id:
        return None
    row = conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (record_id,)).fetchone()
    if row is None or row["deleted_at"]:
        return None
    return dict(row)


def _same(a: tuple, b: tuple, items: _Items) -> bool:
    """Two lines that may be the same purchase: same item (or a suggested item with an item's name and unit),
    the same amount and unit, and the same date (a missing date matches any)."""
    if a[2] != b[2] or a[3] != b[3] or (a[0] and b[0] and a[0] != b[0]):
        return False
    if a[1] == b[1]:
        return True
    for x, y in ((a[1], b[1]), (b[1], a[1])):
        if x[0] == "new" and y[0] == "id":
            name, unit = items.get(y[1])
            return (x[1], x[2]) == (_norm_name(name), _norm_unit(unit))
    return False


def _compare(here: list[tuple], there: list[tuple], items: _Items) -> tuple[bool, int, list, list]:
    """(exact, how many lines match, lines only here, lines only there). Repeated lines count each time."""
    exact = bool(here) and Counter(here) == Counter(there) and \
        all(line[0] and line[1][0] == "id" for line in here)
    left, right, matched = list(here), list(there), 0
    for line in list(left):
        found = next((other for other in right if _same(line, other, items)), None)
        if found is not None:
            left.remove(line)
            right.remove(found)
            matched += 1
    return exact, matched, left, right


def _earlier(conn, before: int | None) -> list:
    query = ("SELECT b.*, h.name AS helper_name FROM core__helper_batches b LEFT JOIN core__helpers h "
             "ON h.id = b.helper_id WHERE b.receipt_json IS NOT NULL")
    args: tuple = ()
    if before is not None:
        query, args = query + " AND b.id < ?", (before,)
    return conn.execute(query + " ORDER BY b.id DESC LIMIT ?", args + (EARLIER_LIMIT,)).fetchall()


def _match(conn, registry, here: list[tuple], lines_waiting: bool, before: int | None, items: _Items) -> dict | None:
    """The earlier receipt this basket looks most like, or None.

    "repeat": every line matches an earlier receipt whose rows are still waiting or added (held until the person
    chooses); "undone": it matches one whose Stock in rows were all deleted since; "similar": at least half the
    lines match. Only "repeat" holds Accept."""
    if not here:
        return None
    dates_here = {line[0] for line in here}
    earlier = _earlier(conn, before)
    rows = _receipt_rows(conn, registry, [b["id"] for b in earlier])
    best = None
    for batch in earlier:
        basket, states, waiting_lines = _basket(conn, registry, rows[batch["id"]],
                                                json.loads(batch["receipt_json"]), items)
        if not basket or not ({line[0] for line in basket} & dates_here or None in dates_here):
            continue
        exact, matched, only_here, only_there = _compare(here, basket, items)
        exact = exact and not lines_waiting and not waiting_lines
        if not matched or (not exact and matched * 2 < max(len(here), len(basket))):
            continue
        active = states.get("waiting", 0) + states.get("added", 0)
        level = "repeat" if exact and active else ("undone" if not active else "similar")
        found = {"level": level, "batch": batch, "states": states, "matched": matched, "only_here": only_here,
                 "only_there": only_there, "rows": rows[batch["id"]]}
        if level == "repeat":
            return found
        if best is None or matched > best["matched"]:
            best = found
    return best


def _batch(conn, batch_id: int):
    return conn.execute("SELECT * FROM core__helper_batches WHERE id = ?", (batch_id,)).fetchone()


def _owner_for(registry):
    name = line_table(registry)
    return owner_of(registry, registry[name]) if name else None


def possible_repeat(conn: sqlite3.Connection, registry: dict, batch_id: int) -> dict | None:
    """For a receipt batch: the earlier receipt it may repeat (see `_match`), with `kept` if the person chose
    "Keep this as another purchase" and nothing has changed since. None for a batch that is not one receipt."""
    batch = _batch(conn, batch_id)
    if batch is None or not batch["receipt_json"]:
        return None
    items = _Items(conn, _owner_for(registry))
    rows = _receipt_rows(conn, registry, [batch_id])[batch_id]
    here, _states, lines_waiting = _basket(conn, registry, rows, json.loads(batch["receipt_json"]), items)
    found = _match(conn, registry, here, lines_waiting, batch_id, items)
    if found is None:
        return None
    found["kept"] = bool(batch["repeat_ok_json"]) and \
        json.loads(batch["repeat_ok_json"]) == _signature(conn, found, batch_id)
    found["items"] = items
    return found


def _signature(conn, found: dict, batch_id: int) -> dict:
    """What "Keep this as another purchase" was decided on: the earlier receipt and the state of its rows, and
    this receipt's rows still counted. Only row ids and states, never goods or amounts."""
    earlier = [[r["id"], r["status"], r["record_id"]] for r in found["rows"]]
    here = [r["id"] for r in conn.execute("SELECT id FROM core__proposals WHERE batch_id = ? AND status != 'rejected' "
                                          "ORDER BY position", (batch_id,))]
    return {"earlier": found["batch"]["id"], "earlier_rows": earlier, "undone": found["states"].get("undone", 0),
            "rows": here}


def held(conn: sqlite3.Connection, registry: dict, batch_id: int) -> dict | None:
    """The possible repeat that holds Accept for this batch, or None."""
    found = possible_repeat(conn, registry, batch_id)
    return found if found and found["level"] == "repeat" and not found["kept"] else None


HELD = ("This may be the same receipt again, so nothing from it was added. On Review, choose Reject this copy or "
        "Keep this as another purchase first.")


def guard(conn: sqlite3.Connection, registry: dict, batch_id: int) -> None:
    """Refuse to accept from a batch that may be a receipt already sent, until the person has chosen. Called
    before and again inside the write transaction of every Accept, Accept all and Accept ticked."""
    if held(conn, registry, batch_id):
        raise RepeatHeld(HELD)


def keep(conn: sqlite3.Connection, registry: dict, batch_id: int) -> None:
    """"Keep this as another purchase": for this batch only, and only while neither receipt changes. Adds nothing."""
    with db.transaction(conn):
        found = possible_repeat(conn, registry, batch_id)
        if found is None or found["level"] != "repeat":
            raise PlainError("This receipt no longer looks like an earlier one, so there is nothing to keep.")
        signature = _signature(conn, found, batch_id)
        conn.execute("UPDATE core__helper_batches SET repeat_ok_json = ? WHERE id = ?",
                     (json.dumps(signature, sort_keys=True), batch_id))
        _audit(conn, "receipt_keep", "core__helper_batches", batch_id, {"earlier": signature["earlier"]}, batch_id)


def lookalike(conn: sqlite3.Connection, registry: dict, entries: list[tuple[str, dict]],
              purchase_date: str) -> dict | None:
    """For rows about to be imported as one receipt: an earlier receipt they look like, or None (decision 0105)."""
    items = _Items(conn, _owner_for(registry))
    fake = [{"id": -1 - n, "position": n, "status": "pending", "entry_kind": "record", "table_name": table,
             "values_json": json.dumps(values), "record_id": None} for n, (table, values) in enumerate(entries)]
    here, _states, _lines = _basket(conn, registry, fake, {"purchase_date": purchase_date}, items)
    found = _match(conn, registry, here, False, None, items)
    if found is not None:
        found["items"] = items
    return found


# ----- words for Review --------------------------------------------------------------------------------

def line_words(line: tuple, items: _Items, style: str) -> str:
    """One basket line as a person reads it: "2 tins of Kidney beans on 20/11/26"."""
    when, identity, amount, unit = line
    if identity[0] == "id":
        name, unit_text = items.get(identity[1])
    else:
        name, unit_text = identity[1], identity[2]
    amount_text = amount if amount is not None else "?"
    text = f"{amount_text} {unit_for(amount_text, unit_text)} of {name}" if unit_text else f"{amount_text} of {name}"
    return text + (f" on {dates.show(when, style)}" if when else "")


def state_words(states: dict) -> str:
    """The earlier receipt's real state: never "already added" for rows still waiting."""
    waiting, added, undone = states.get("waiting", 0), states.get("added", 0), states.get("undone", 0)
    total = waiting + added + undone
    rows = lambda n: f"{n} row{'' if n == 1 else 's'}"  # noqa: E731
    if added == total:
        return f"Already added: {rows(added)}."
    if waiting == total:
        return f"Still waiting: {rows(waiting)}."
    if undone == total:
        return "Earlier receipt was undone: none of its Stock in rows remain."
    text = f"Partly added: {added} of {rows(total)}."
    if undone:
        text += f" {undone} {'was' if undone == 1 else 'were'} undone."
    if waiting:
        text += f" {waiting} still waiting."
    return text
