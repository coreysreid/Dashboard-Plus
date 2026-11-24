"""One reminder per policy: a household chooses, row by row and by exact ID, to move an older list's reminder into a newer one, and can move it back (0117).

A table may declare `takes_over` in tables.toml (Bills and insurance takes over Vehicle insurance). Nothing moves
when a module is switched on. The household chooses on the newer list's page: keep the reminders where they are,
review and move them one by one, or decide later. Moving one record, in one transaction after a backup:
- adds one record to the newer list with only the columns `copy` names (never a private one, never notes) and
  the `where` values, the date exactly as typed,
- writes one row in `core__reminder_moves` with both records' local numbers and permanent IDs, never a name,
- leaves the older record and its history where they were, read-only, as the earlier record.
From then on only the newer record reminds (Home, Needs attention, Things to do, sheets). Moving back copies the
newer record's current date into the older one and silences the newer one. One row per older record means a
second press, a retry or a restart never makes a second reminder; switching a module off never moves anything.
Which record reminds is worked out from that table alone, so it holds while either module is off.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from dashboard.core import confirm, db, naming, sync
from dashboard.core.modules import Module
from dashboard.core.records import Records, RecordNotFound, TableInfo, ValidationError
from dashboard.core.schema import table_name, target_table
from dashboard.errors import PlainError

TABLE = "core__reminder_moves"
MOVED, RETURNED, KEPT = "moved", "returned", "kept"
CHOICES = ("keep", "review", "later")  # the household's choice for the whole list, kept in core__settings
FIELD = "reminder"  # the key a refusal is reported under, beside the form's own fields

# The household's words when a module gives none (labels.toml `takes_over`). {source} is the older list's title,
# {source_module} and {target_module} the modules' titles; {count}, {name}, {date} and {link} are filled in where
# they apply.
DEFAULT_WORDS = {
    "title": "{source} already has reminders",
    "intro": "You have {count} {source} record(s) with a reminder in {source_module}. Keep their reminders there, "
             "or move them to {target_module} one by one. Each will have one reminder. Nothing private is "
             "copied. You can decide later.",
    "keep": "Keep reminders in {source_module}",
    "review": "Review and move to {target_module}",
    "later": "Decide later",
    "warning": "Check the date shown against your own papers. Notes in {source_module} stay there and keep their "
               "current sharing and export rules.",
    "question": "Move this reminder to {target_module}? {source_module} will stop reminding you for it. Its earlier "
                "record and history stay in {source_module}.",
    "no_date": "No date recorded. Add the date you want to be reminded.",
    "moved": "Moved {name} to {target_module}. One reminder is active there; the {source_module} reminder is off.",
    "source_kept": "This reminder is kept in {source_module}.",
    "source_moved": "This reminder is in {target_module}. Open {name}.",
    "target_moved": "Moved here from {source_module}. Due {date}.",
    "target_off": "These reminders are in {target_module}, which is off. Switch it on to see them, or choose "
                  "Transfer back.",
    "returned": "Moved back to {source_module}. One reminder is active there; this record no longer reminds.",
    "needs_choice": "Choose first where these reminders are kept: open {target} and choose “{keep}” or "
                    "“{review}”.",
    "duplicate": "{link} already has a reminder in {source_module} ({name}). Saving this makes a second reminder "
                 "unless it is a different one.",
    "duplicate_source": "{link} already has a reminder in {target_module} ({name}). Saving this makes a second "
                        "reminder unless it is a different one.",
    "back": "Transfer back",
}


@dataclass
class Rule:
    """One `takes_over` declaration: the newer list, the older one it may take reminders from, and what is copied."""
    target: TableInfo
    source_name: str  # the older list's real table name, such as vehicles__insurance
    source: TableInfo | None  # None while that module is switched off or not installed
    where: dict
    copy: dict  # this (newer) table's column -> the older table's column
    target_on: bool = True  # False while the newer list's module is switched off

    @property
    def date(self) -> str:
        return self.target.table.watch["expiring"]["date"]

    @property
    def source_date(self) -> str:
        return self.copy[self.date]


def _rule(info: TableInfo, registry: dict, target_on: bool) -> Rule:
    declared = info.table.takes_over
    other, _, other_table = declared["from"].partition(".")
    source_name = table_name(other, other_table)
    return Rule(info, source_name, registry.get(source_name), dict(declared["where"]), dict(declared["copy"]),
                target_on)


def rules(registry: dict, loaded: list[Module] | None = None) -> list[Rule]:
    """Every `takes_over` of the switched-on modules; with `loaded`, also of installed modules that are off, so the
    older record's page can still say where its reminder is and offer Transfer back."""
    found = [_rule(info, registry, True) for info in registry.values() if info.table.takes_over]
    for module in loaded or []:
        for table in module.tables.values():
            name = table_name(module.name, table.name)
            if table.takes_over and name not in registry:
                found.append(_rule(TableInfo(module, table), registry, False))
    return found


def rule_for(registry: dict, target: str, loaded: list[Module] | None = None) -> Rule | None:
    return next((r for r in rules(registry, loaded) if r.target.name == target), None)


def words(rule: Rule, key: str, **fill) -> str:
    """One of the household's sentences: the module's own from labels.toml `takes_over`, or the default."""
    labels = rule.target.module.labels.get("tables", {}).get(rule.target.table.name, {})
    text = (labels.get("takes_over") or {}).get(key) or DEFAULT_WORDS[key]
    source_title = rule.source.table.title if rule.source else rule.source_name
    source_module = rule.source.module.title if rule.source else rule.source_name.partition("__")[0].title()
    target_title = labels.get("title") or rule.target.table.title
    keep = (labels.get("takes_over") or {}).get("keep") or DEFAULT_WORDS["keep"]
    review = (labels.get("takes_over") or {}).get("review") or DEFAULT_WORDS["review"]
    values = {"source": source_title, "source_module": source_module, "target_module": rule.target.module.title,
              "target": target_title, "count": "", "name": "", "date": "", "link": "", **fill}
    values["keep"], values["review"] = keep.format(**values), review.format(**values)
    return text.format(**values)


# ----- who reminds now ---------------------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def entry(conn: sqlite3.Connection, table: str, record_id: int) -> dict | None:
    """The move a record takes part in, as the older or the newer record, or None."""
    row = conn.execute(f"SELECT * FROM {TABLE} WHERE (source_table = ? AND source_id = ?) OR "
                       f"(target_table = ? AND target_id = ?) ORDER BY id LIMIT 1",
                       (table, record_id, table, record_id)).fetchone()
    return dict(row) if row else None


def silent_clause(table: str) -> str:
    """SQL to add after a WHERE that leaves out the records of `table` that no longer remind: an older record whose
    reminder was moved, and a newer one whose reminder was moved back. `table` is a checked table name."""
    return (f" AND id NOT IN (SELECT source_id FROM {TABLE} WHERE source_table = '{table}' AND state = '{MOVED}' "
            f"UNION ALL SELECT target_id FROM {TABLE} WHERE target_table = '{table}' AND state = '{RETURNED}' "
            f"AND target_id IS NOT NULL)")


def silent(conn: sqlite3.Connection, table: str) -> set[int]:
    """The ids of the records of `table` that no longer remind."""
    return {r[0] for r in conn.execute(
        f"SELECT source_id FROM {TABLE} WHERE source_table = ? AND state = ? UNION ALL "
        f"SELECT target_id FROM {TABLE} WHERE target_table = ? AND state = ? AND target_id IS NOT NULL",
        (table, MOVED, table, RETURNED))}


def choice(conn: sqlite3.Connection, rule: Rule) -> str | None:
    row = conn.execute("SELECT value FROM core__settings WHERE key = ?", (_choice_key(rule),)).fetchone()
    value = json.loads(row["value"]) if row else None
    return value if value in CHOICES else None


def _choice_key(rule: Rule) -> str:
    return f"reminder_moves.{rule.target.name}"


def _put_choice(conn: sqlite3.Connection, rule: Rule, value: str, actor: str) -> None:
    """Save the household's choice inside the open transaction, with a line in history (never any record's details)."""
    now = _now()
    conn.execute("INSERT INTO core__settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE "
                 "SET value = excluded.value, updated_at = excluded.updated_at", (_choice_key(rule), json.dumps(value),
                                                                                  now))
    conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                 "VALUES (?, ?, 'reminder_choice', ?, 0, NULL, ?)",
                 (now, actor, rule.target.name, json.dumps({"choice": value, "from": rule.source_name})))


def choose(conn: sqlite3.Connection, rule: Rule, value: str, actor: str = "person") -> None:
    """Keep reminders where they are, review them, or decide later. Nothing moves by this alone."""
    if value not in CHOICES:
        raise PlainError("Choose Keep, Review or Decide later.")
    with db.transaction(conn):
        _put_choice(conn, rule, value, actor)


def _live_sources(conn: sqlite3.Connection, rule: Rule) -> list[dict]:
    return [dict(r) for r in conn.execute(f"SELECT * FROM {rule.source_name} WHERE deleted_at IS NULL ORDER BY id")]


def undecided(conn: sqlite3.Connection, rule: Rule) -> int:
    """How many live older records have no choice yet (never moved, kept or moved back)."""
    if rule.source is None:
        return 0
    return conn.execute(f"SELECT COUNT(*) FROM {rule.source_name} WHERE deleted_at IS NULL AND id NOT IN "
                        f"(SELECT source_id FROM {TABLE} WHERE source_table = ?)", (rule.source_name,)).fetchone()[0]


def needs_choice(conn: sqlite3.Connection, rule: Rule) -> bool:
    """True while the household has not chosen Keep or Review and older records still remind: until then a new
    record of the `where` kind (a vehicle policy) can't be saved in the newer list, so there are never two."""
    if rule.source is None or choice(conn, rule) in ("keep", "review"):
        return False
    return conn.execute(f"SELECT 1 FROM {rule.source_name} WHERE deleted_at IS NULL{silent_clause(rule.source_name)} "
                        f"LIMIT 1").fetchone() is not None


def show_choice(conn: sqlite3.Connection, rule: Rule) -> bool:
    """The first-time screen on the newer list: older records with a reminder and no household choice yet."""
    return rule.source is not None and choice(conn, rule) in (None, "later") and undecided(conn, rule) > 0


def _name(conn, registry, info: TableInfo, row: dict) -> str:
    return naming.record_name(conn, registry, info, row)


def candidates(conn: sqlite3.Connection, registry: dict, rule: Rule) -> list[dict]:
    """Every live older record, by its local number and permanent ID, with what it is now. Never matched by name:
    two policies with the same name on one vehicle are two rows."""
    if rule.source is None:
        return []
    moves = {r["source_id"]: dict(r) for r in conn.execute(f"SELECT * FROM {TABLE} WHERE source_table = ?",
                                                           (rule.source_name,))}
    found = []
    for row in _live_sources(conn, rule):
        move = moves.get(row["id"], {})
        found.append({"id": row["id"], "global_id": row.get(sync.ID), "row": row,
                      "name": str(row.get(rule.copy.get("name", "name")) or _name(conn, registry, rule.source, row)),
                      "title": _name(conn, registry, rule.source, row), "date": row.get(rule.source_date),
                      "state": move.get("state"), "target_id": move.get("target_id")})
    return found


# ----- the guards the record service runs ---------------------------------------------------------------------

def _matches(rule: Rule, record: dict) -> bool:
    return all(record.get(k) == v for k, v in rule.where.items())


def _source_rules(registry: dict, table: str) -> list[Rule]:
    return [r for r in rules(registry) if r.source_name == table]


def _title_of(registry: dict, table: str) -> str | None:
    info = registry.get(table)
    return info.module.title if info else None


def check_write(store: Records, info: TableInfo, record_id: int | None, current: dict | None, changed: dict) -> None:
    """Refuse a change that would make a second reminder or edit a record that no longer owns its reminder."""
    if getattr(store, "moving", False):
        return  # the move itself
    conn, registry = store.conn, store.registry
    move = entry(conn, info.name, record_id) if record_id is not None else None
    if move and move["source_table"] == info.name and move["state"] == MOVED:
        where = _title_of(registry, move["target_table"])
        raise ValidationError({FIELD: (f"This record's reminder was moved to {where}. Change it there, or choose "
                                       f"Transfer back on this page." if where else
                                       "This record's reminder was moved to a list that is switched off. Switch it "
                                       "on to change it, or choose Transfer back on this page.")})
    if move and move["target_table"] == info.name and move["state"] == RETURNED:
        where = _title_of(registry, move["source_table"]) or "a list that is switched off"
        raise ValidationError({FIELD: f"This record's reminder was moved back to {where}, so it is kept as it was. "
                                      f"Move it here again to change it."})
    if not info.table.takes_over:
        return
    rule = _rule(info, registry, True)
    merged = {**(current or {}), **changed}
    if move and move["target_table"] == info.name and move["state"] == MOVED:
        if not _matches(rule, merged):
            raise ValidationError({FIELD: "This reminder was moved here from another list, so what it is for "
                                          "stays as it is. Choose Transfer back to change that."})
        return
    if _matches(rule, merged) and (current is None or not _matches(rule, current)) and needs_choice(conn, rule):
        raise ValidationError({FIELD: words(rule, "needs_choice")})


def check_delete(store: Records, info: TableInfo, record_id: int, direct: bool) -> None:
    """The earlier record of a moved reminder is kept: it is not deleted on its own (deleting what it belongs to,
    such as its vehicle, still takes it along, and restoring brings it back)."""
    if not direct:
        return
    move = entry(store.conn, info.name, record_id)
    if move and move["source_table"] == info.name and move["state"] == MOVED:
        raise ValidationError({"delete": "can't be done: this is the earlier record of a reminder that was moved. "
                                         "It is kept with its history. Choose Transfer back first if you want to "
                                         "change it."})


def _link_name(store: Records, info: TableInfo, column_name: str, value) -> str:
    column = info.table.columns[column_name]
    target = store.registry.get(target_table(info.module.name, column))
    row = store.conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (value,)).fetchone() if target else None
    return _name(store.conn, store.registry, target, dict(row)) if row else "This record"


def warnings(store: Records, info: TableInfo, record: dict, record_id: int | None) -> list[confirm.Warning]:
    """A gentle check before saving (Go back / Save as entered): the same linked record (a vehicle) already has a
    reminder of this kind in the other list. A different policy is allowed; the household says so by saving."""
    conn, registry, found = store.conn, store.registry, []
    move = entry(conn, info.name, record_id) if record_id is not None else None
    links = lambda rule: [(t, s) for t, s in rule.copy.items()  # noqa: E731
                          if rule.target.table.columns[t].type == "link"]
    if info.table.takes_over and not move:
        rule = _rule(info, registry, True)
        if rule.source is not None and _matches(rule, record):
            for mine, theirs in links(rule):
                if record.get(mine) in (None, ""):
                    continue
                for row in conn.execute(f"SELECT * FROM {rule.source_name} WHERE deleted_at IS NULL AND {theirs} = ?"
                                        f"{silent_clause(rule.source_name)} ORDER BY id", (record[mine],)):
                    found.append(_warning(rule, mine, f"{record[mine]}:{row['id']}", words(
                        rule, "duplicate", link=_link_name(store, info, mine, record[mine]),
                        name=_name(conn, registry, rule.source, dict(row)))))
    if not move or move["state"] != MOVED:
        for rule in _source_rules(registry, info.name):
            for mine, theirs in links(rule):
                if record.get(theirs) in (None, ""):
                    continue
                clause = "".join(f" AND {k} = ?" for k in rule.where)
                for row in conn.execute(f"SELECT * FROM {rule.target.name} WHERE deleted_at IS NULL AND {mine} = ?"
                                        f"{clause}{silent_clause(rule.target.name)} ORDER BY id",
                                        [record[theirs], *rule.where.values()]):
                    if move and move.get("target_id") == row["id"]:
                        continue
                    found.append(_warning(rule, theirs, f"{record[theirs]}:{row['id']}", words(
                        rule, "duplicate_source", link=_link_name(store, info, theirs, record[theirs]),
                        name=_name(conn, registry, rule.target, dict(row)))))
    return found


def _warning(rule: Rule, column: str, checked: str, message: str) -> confirm.Warning:
    digest = hashlib.sha256(f"{rule.target.name}@{checked}".encode()).hexdigest()[:16]
    return confirm.Warning("one_reminder", column, message, f"one_reminder-{digest}")


# ----- moving, keeping and moving back ------------------------------------------------------------------------

def _history(conn, actor: str, action: str, table: str, record_id: int, after: dict) -> None:
    """A line in the record's history naming the other record by list and number only."""
    conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                 "VALUES (?, ?, ?, ?, ?, NULL, ?)", (_now(), actor, action, table, record_id, json.dumps(after)))


def _global_id(conn, table: str, record_id) -> str | None:
    if record_id is None or not sync.has_identity(conn, table):
        return None
    row = conn.execute(f"SELECT {sync.ID} FROM {table} WHERE id = ?", (record_id,)).fetchone()
    return row[0] if row else None


def _need_source(rule: Rule) -> None:
    if rule.source is None:
        raise PlainError("Switch on the list these reminders came from first. Nothing was changed.")


def move(store: Records, rule: Rule, source_id: int, actor: str = "person", backup=None) -> dict:
    """Move one older record's reminder to the newer list. Returns {"status": "moved" | "already", "target_id"}.

    `backup()` is called first; if it fails nothing is moved. Everything else happens in one transaction: the new
    record (or, after a Transfer back, the same newer record brought up to date), its row in core__reminder_moves
    and both history lines. A second press finds that row and changes nothing."""
    _need_source(rule)
    if not rule.target_on:
        raise PlainError(f"Switch on {rule.target.module.title} first. Nothing was changed.")
    conn = store.conn
    current = entry(conn, rule.source_name, source_id)
    if current and current["state"] == MOVED:
        return {"status": "already", "target_id": current["target_id"]}
    if backup is not None:
        try:
            backup()
        except Exception as error:  # noqa: BLE001 - no backup, no move
            raise PlainError("Nothing was moved because a backup could not be made first. Check Settings, "
                             "Backups.") from error
    with db.transaction(conn):
        row = store._row(rule.source, source_id)
        current = entry(conn, rule.source_name, source_id)  # again, inside the write lock
        if current and current["state"] == MOVED:
            return {"status": "already", "target_id": current["target_id"]}
        copied = {mine: row.get(theirs) for mine, theirs in rule.copy.items()}
        store.moving = True
        try:
            target_live = current and current["target_id"] is not None and conn.execute(
                f"SELECT 1 FROM {rule.target.name} WHERE id = ? AND deleted_at IS NULL",
                (current["target_id"],)).fetchone()
            if target_live:
                target_id = current["target_id"]
                store._update(rule.target, target_id, copied, actor)
            else:
                target_id = store._create(rule.target, {**copied, **rule.where}, actor)
        finally:
            store.moving = False
        now = _now()
        ids = (_global_id(conn, rule.source_name, source_id), rule.target.name, target_id,
               _global_id(conn, rule.target.name, target_id))
        if current:
            conn.execute(f"UPDATE {TABLE} SET source_global_id = ?, target_table = ?, target_id = ?, "
                         f"target_global_id = ?, state = ?, updated_at = ? WHERE id = ?", (*ids, MOVED, now,
                                                                                           current["id"]))
        else:
            conn.execute(f"INSERT INTO {TABLE} (source_table, source_id, source_global_id, target_table, target_id, "
                         f"target_global_id, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (rule.source_name, source_id, *ids, MOVED, now, now))
        if choice(conn, rule) != "review":
            _put_choice(conn, rule, "review", actor)
        _history(conn, actor, "reminder_moved", rule.source_name, source_id,
                 {"to": rule.target.name, "to_id": target_id})
        _history(conn, actor, "reminder_moved", rule.target.name, target_id,
                 {"from": rule.source_name, "from_id": source_id})
    return {"status": "moved", "target_id": target_id}


def keep(store: Records, rule: Rule, source_id: int, actor: str = "person") -> None:
    """Keep this one older record's reminder where it is (per row). Nothing is copied."""
    _need_source(rule)
    conn = store.conn
    with db.transaction(conn):
        store._row(rule.source, source_id)
        current = entry(conn, rule.source_name, source_id)
        if current and current["state"] != KEPT:
            raise PlainError("This one was moved already; use Transfer back instead. Nothing was changed.")
        if current:
            return
        now = _now()
        conn.execute(f"INSERT INTO {TABLE} (source_table, source_id, source_global_id, target_table, target_id, "
                     f"target_global_id, state, created_at, updated_at) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?)",
                     (rule.source_name, source_id, _global_id(conn, rule.source_name, source_id), rule.target.name,
                      KEPT, now, now))
        _history(conn, actor, "reminder_kept", rule.source_name, source_id, {"kept_from": rule.target.name})


def later(store: Records, rule: Rule, source_id: int, actor: str = "person") -> None:
    """Undo a per-row Keep so the record is asked about again. A moved one is left as it is."""
    conn = store.conn
    with db.transaction(conn):
        current = entry(conn, rule.source_name, source_id)
        if current and current["state"] == KEPT:
            conn.execute(f"DELETE FROM {TABLE} WHERE id = ?", (current["id"],))
            _history(conn, actor, "reminder_later", rule.source_name, source_id, {"later_for": rule.target.name})


def move_back(store: Records, rule: Rule, source_id: int, actor: str = "person", backup=None) -> dict:
    """Transfer back: the older record takes the newer record's current date and reminds again; the newer one is
    kept, silent, with its own details. Returns {"status": "returned" | "already", "date"}."""
    _need_source(rule)
    conn = store.conn
    current = entry(conn, rule.source_name, source_id)
    if not current or current["state"] != MOVED:
        return {"status": "already", "date": None}
    if backup is not None:
        try:
            backup()
        except Exception as error:  # noqa: BLE001 - no backup, no move
            raise PlainError("Nothing was moved back because a backup could not be made first. Check Settings, "
                             "Backups.") from error
    with db.transaction(conn):
        current = entry(conn, rule.source_name, source_id)
        if not current or current["state"] != MOVED:
            return {"status": "already", "date": None}
        target = conn.execute(f"SELECT * FROM {rule.target.name} WHERE id = ?", (current["target_id"],)).fetchone()
        if target is None or target["deleted_at"]:
            raise PlainError("The record in the newer list was deleted. Restore it there first, then choose Transfer "
                             "back. Nothing was changed.")
        try:
            store._row(rule.source, source_id)
        except RecordNotFound:
            raise PlainError("The earlier record was deleted (for example with its vehicle). Restore it first. "
                             "Nothing was changed.") from None
        date = target[rule.date]
        store.moving = True
        try:
            store._update(rule.source, source_id, {rule.source_date: date}, actor)
        finally:
            store.moving = False
        conn.execute(f"UPDATE {TABLE} SET state = ?, updated_at = ? WHERE id = ?", (RETURNED, _now(), current["id"]))
        _history(conn, actor, "reminder_returned", rule.source_name, source_id,
                 {"from": rule.target.name, "from_id": current["target_id"]})
        _history(conn, actor, "reminder_returned", rule.target.name, current["target_id"],
                 {"to": rule.source_name, "to_id": source_id})
    return {"status": "returned", "date": date}


# ----- what export and sync say -------------------------------------------------------------------------------

def all_moves(conn: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in conn.execute(f"SELECT * FROM {TABLE} ORDER BY id")]


def export_words(move: dict, table: str, titles: dict) -> str:
    """A spreadsheet cell saying which record reminds, so an earlier record is never read as a second reminder."""
    other = titles.get(move["target_table"] if move["source_table"] == table else move["source_table"],
                       "another list")
    if move["state"] == KEPT:
        return "Reminds here (kept here by the household's choice)"
    if move["source_table"] == table:
        if move["state"] == MOVED:
            return f"Earlier record: its reminder moved to {other} (ID {move['target_id']}); it does not remind"
        return f"Reminds here (moved back from {other}, ID {move['target_id']})"
    if move["state"] == MOVED:
        return f"Reminds here (moved from {other}, ID {move['source_id']})"
    return f"Moved back to {other} (ID {move['source_id']}); it does not remind"


def snapshot(conn: sqlite3.Connection) -> list[dict]:
    """The moves by permanent IDs only, for sync's snapshot: a later stage must carry them with the records."""
    return [{"from_table": m["source_table"], "from": m["source_global_id"], "to_table": m["target_table"],
             "to": m["target_global_id"], "state": m["state"]} for m in all_moves(conn)]
