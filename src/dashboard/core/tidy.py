"""Tidy sensitive details (decision 0141): find codes, full numbers and card numbers saved before, and tidy each one.

Three kinds of saved value are found: anything in a retired column (such as the old "Codes or access details"), a
value in a guarded column that breaks its rule (an access detail that holds a code), and a full card number in any
ordinary text. Each can be kept as its last 4 digits, replaced by where it is kept, or removed. The page takes a
backup first; each tidy is one history entry that holds the old value only so that Undo works, until the person
presses Forget the old values, which also clears them from the record's earlier history.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dashboard.core import db, fraud_guard, sync
from dashboard.core.records import Records, TableInfo
from dashboard.errors import PlainError

TIDY, UNDO, FORGOTTEN = "tidy", "tidy_undo", "forgotten"
LAST4, WHERE, REMOVE = "last4", "where", "remove"
MAX_HINT = 200


class TidyRefused(PlainError):
    """A tidy or its Undo could not be done, with the plain reason. Nothing was changed."""


@dataclass
class Found:
    """One saved value to tidy. `value` is read only for the page after a pressed Show."""
    key: str            # "<table>|<record id>|<column>", what the page sends back
    info: TableInfo
    record_id: int
    column: str
    kind: str           # "retired", "guard" or "card"
    value: str
    deleted: bool
    options: list[str] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _options(info: TableInfo, column: str, kind: str, value: str) -> list[str]:
    if kind == "card":
        return [LAST4, REMOVE] if not info.table.columns[column].required else [LAST4]
    if kind == "guard":
        return [WHERE] if info.table.columns[column].required else [WHERE, REMOVE]
    rule = info.table.retired[column].retired
    into = info.table.columns.get(rule.get("replaced_by", ""))
    found = []
    if into is not None and into.guard == "last_digits" and fraud_guard.last_digits(value):
        found.append(LAST4)
    if (into is not None and into.guard == "where_kept") or rule.get("note_to"):
        found.append(WHERE)
    return found + [REMOVE]


def find(store: Records) -> list[Found]:
    """Every saved value to tidy, in the order of the lists, deleted records too (their values are still kept)."""
    found = []
    for info in store.registry.values():
        texts = [c for c in info.table.columns.values() if c.type in ("text", "longtext")]
        names = list(info.table.retired) + [c.name for c in texts]
        if not names:
            continue
        guarded = {c.name: c for c in texts if c.guard == "where_kept"}
        rows = store.conn.execute(f"SELECT * FROM {info.name} ORDER BY id")
        for row in rows:
            row = dict(row)
            for name in names:
                value = row.get(name)
                if not isinstance(value, str) or not value.strip():
                    continue
                if name in info.table.retired:
                    kind = "retired"
                elif fraud_guard.has_card_number(value):
                    kind = "card"
                elif name in guarded and _breaks_guard(guarded[name], row, value):
                    kind = "guard"
                else:
                    continue
                found.append(Found(f"{info.name}|{row['id']}|{name}", info, row["id"], name, kind, value,
                                   bool(row.get("deleted_at")), _options(info, name, kind, value)))
    return found


def _breaks_guard(column, row: dict, value: str) -> bool:
    if column.guard_when:
        (other, allowed), = column.guard_when.items()
        if row.get(other) not in allowed:
            return False
    return fraud_guard.check(value, column.guard) is not None


def waiting(store: Records) -> int:
    """How many retired values are still saved: a few counts, cheap enough for the home page."""
    total = 0
    for info in store.registry.values():
        for name in info.table.retired:
            total += store.conn.execute(
                f"SELECT COUNT(*) FROM {info.name} WHERE {name} IS NOT NULL AND TRIM({name}) <> ''").fetchone()[0]
    return total


def one(store: Records, key: str) -> Found:
    """The saved value a page's button names, found again now; refused if it was tidied or changed meanwhile."""
    table, _, rest = (key or "").partition("|")
    record, _, column = rest.partition("|")
    info = store.registry.get(table)
    if info is None or not record.isdecimal():
        raise TidyRefused("That detail could not be found. Open Tidy sensitive details again.")
    row = store.conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (int(record),)).fetchone()
    for item in find(Records(store.conn, {table: info})) if row is not None else []:
        if item.record_id == int(record) and item.column == column:
            return item
    raise TidyRefused("That detail was already tidied, or it changed. Nothing was changed.")


def _plan(item: Found, action: str, hint: str | None, current: dict) -> dict:
    """The new value of each column this tidy changes; `current` is the record as saved now."""
    if action not in item.options:
        raise TidyRefused("That choice is not offered for this detail. Nothing was changed.")
    columns = item.info.table.columns
    if action == WHERE:
        hint = (hint or "").strip()
        if not hint or len(hint) > MAX_HINT or fraud_guard.check(hint, "where_kept"):
            raise TidyRefused(f"Write who to ask or where it is kept, in {MAX_HINT} characters or fewer, such as "
                              f"“In the password manager” or “Ask Alex next door”. Leave out the code or number "
                              f"itself. Nothing was changed.")
    if item.kind == "card":
        if action == LAST4:
            return {item.column: fraud_guard.mask_cards(item.value)}
        left = re.sub(r"[ \t]{2,}", " ", "".join(_without_cards(item.value))).strip()
        return {item.column: left or None}
    if item.kind == "guard":
        return {item.column: hint if action == WHERE else None}
    rule = item.info.table.retired[item.column].retired
    plan = {item.column: None}
    into = columns.get(rule.get("replaced_by", ""))
    if action == LAST4:
        plan[into.name] = fraud_guard.stored_last_digits(item.value)
    elif action == WHERE:
        if into is not None and into.guard == "where_kept":
            plan[into.name] = hint
        else:
            note = rule["note_to"]
            earlier = (current.get(note) or "").strip()
            plan[note] = (earlier + "\n" if earlier else "") + f"Where the full number is kept: {hint}"
    return plan


def _without_cards(text: str):
    last = 0
    for start, end, _digits in fraud_guard.card_numbers(text):
        yield text[last:start]
        last = end
    yield text[last:]


def apply(store: Records, item: Found, action: str, hint: str | None = None, backup=None) -> int:
    """Tidy one saved value as the person chose, in one transaction. Returns the history entry, for Undo.

    `backup` is called once the choice is checked and before anything changes. Ordinary columns change through the change log so the household's other
    computers follow; the old value is kept only in this entry, for Undo, until Forget the old values."""
    conn = store.conn
    current = dict(conn.execute(f"SELECT * FROM {item.info.name} WHERE id = ?", (item.record_id,)).fetchone())
    plan = _plan(item, action, hint, current)
    before = {k: current.get(k) for k in plan}
    if backup is not None:
        backup()
    with db.transaction(conn):
        _write(store, item.info, item.record_id, plan, before)
        audit = conn.execute(
            "INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
            "VALUES (?, 'person', ?, ?, ?, ?, ?)",
            (_now(), TIDY, item.info.name, item.record_id, json.dumps(before, sort_keys=True),
             json.dumps({"columns": plan, "kind": item.kind, "choice": action, "field": item.column},
                        sort_keys=True))).lastrowid
        from dashboard.core import sync_sharing  # decision 0142: the old number leaves the waiting change lines too
        sync_sharing.mask_waiting_cards(conn)
    return audit


def _write(store: Records, info: TableInfo, record_id: int, values: dict, before: dict) -> None:
    sets = ", ".join(f"{k} = ?" for k in values)
    store.conn.execute(f"UPDATE {info.name} SET {sets}, updated_at = ? WHERE id = ?",
                       [*values.values(), store.clock(), record_id])
    shared = {k: v for k, v in values.items() if k in info.table.columns}
    if shared:  # a retired column never travels; the rest follow on the household's other computers
        sync.record(store.conn, info, record_id, "update", {k: None for k in shared}, shared)


def recent(store: Records, limit: int = 20) -> list[dict]:
    """The latest tidies with whether each can still be undone, newest first. No value is read out."""
    rows = store.conn.execute(
        "SELECT a.id, a.at, a.table_name, a.record_id, a.before, a.after, "
        "EXISTS (SELECT 1 FROM core__audit u WHERE u.action = ? AND json_extract(u.before, '$.undoes') = a.id) "
        "AS undone FROM core__audit a WHERE a.action = ? ORDER BY a.id DESC LIMIT ?", (UNDO, TIDY, limit))
    found = []
    for r in rows:
        after = json.loads(r["after"])
        found.append({"id": r["id"], "at": r["at"], "table": r["table_name"], "record_id": r["record_id"],
                      "field": after.get("field"), "choice": after.get("choice"), "undone": bool(r["undone"]),
                      "forgotten": FORGOTTEN in json.loads(r["before"] or "{}")})
    return found


def undo(store: Records, audit_id: int) -> None:
    """Put a tidied value back exactly as it was, if nothing changed it since and its old value was not forgotten."""
    conn = store.conn
    row = conn.execute("SELECT * FROM core__audit WHERE id = ? AND action = ?", (audit_id, TIDY)).fetchone()
    entry = next((e for e in recent(store, 10_000) if e["id"] == audit_id), None)
    if row is None or entry is None:
        raise TidyRefused("That tidy could not be found. Nothing was changed.")
    if entry["undone"]:
        raise TidyRefused("That tidy was already undone. Nothing was changed.")
    if entry["forgotten"]:
        raise TidyRefused("The old value was forgotten, so this tidy cannot be undone. A backup made before it "
                          "still holds it: see Settings, Backups.")
    info = store.registry.get(row["table_name"])
    if info is None:
        raise TidyRefused("That list is switched off. Switch it on to undo this tidy. Nothing was changed.")
    before, plan = json.loads(row["before"]), json.loads(row["after"])["columns"]
    current = conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (row["record_id"],)).fetchone()
    if current is None or any(current[k] != v for k, v in plan.items()):
        raise TidyRefused("This record has changed since it was tidied. Nothing was undone. Check it first.")
    with db.transaction(conn):
        _write(store, info, row["record_id"], before, plan)
        conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                     "VALUES (?, 'person', ?, ?, ?, ?, NULL)",
                     (_now(), UNDO, info.name, row["record_id"], json.dumps({"undoes": audit_id})))


def forget(store: Records) -> int:
    """Forget the old values: clear them from every tidy entry and from the earlier history of the same records
    and fields, so they are nowhere in the data file. Backups made before keep them until they age out."""
    conn = store.conn
    count = 0
    with db.transaction(conn):
        rows = conn.execute("SELECT id, table_name, record_id, before, after FROM core__audit WHERE action = ?",
                            (TIDY,)).fetchall()
        for r in rows:
            before = json.loads(r["before"] or "{}")
            if FORGOTTEN in before:
                continue
            columns = list(before)
            conn.execute("UPDATE core__audit SET before = ? WHERE id = ?",
                         (json.dumps({FORGOTTEN: True, "columns": columns}, sort_keys=True), r["id"]))
            for h in conn.execute("SELECT id, before, after FROM core__audit WHERE table_name = ? AND record_id = ? "
                                  "AND id < ? AND action NOT IN (?, ?)",
                                  (r["table_name"], r["record_id"], r["id"], TIDY, UNDO)).fetchall():
                changed = {}
                for side in ("before", "after"):
                    data = json.loads(h[side]) if h[side] else None
                    if isinstance(data, dict) and any(c in data for c in columns):
                        changed[side] = json.dumps({k: (None if k in columns else v) for k, v in data.items()},
                                                   sort_keys=True)
                for side, text in changed.items():
                    conn.execute(f"UPDATE core__audit SET {side} = ? WHERE id = ?", (text, h["id"]))
            count += 1
    return count
