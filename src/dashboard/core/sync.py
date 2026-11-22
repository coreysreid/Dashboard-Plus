"""Permanent record IDs, revisions and the filtered change log (sync stage 1): nothing leaves this computer.

Decision 0100. Every record in every module table gets a random permanent ID (`global_id`) that never
changes, and a revision (`row_revision`) that goes up once for each operation that changes it. Every
create, change, delete and restore also writes a line to `core__sync_changes`, in the same transaction:
the record's permanent ID, its table, the revision before and after, the names of the changed fields and
the values that may travel to another computer of the household later. A value whose column says
`travels = "never"` (or whose `travels_when` rule does not allow it for this row) is never written there:
only its field name is listed as withheld. `core__audit` stays the local history and is never this format.

The ID and revision columns are added to module tables by `prepare`, which the core runs after each
module's own migrations, under that module's own confinement rule (decision 0055), so it can only touch
that module's tables. No module migration adds or fills them, and none can touch the core's tables.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Callable

from dashboard.core import db, migrations
from dashboard.core.modules import Column, Module
from dashboard.core.schema import join_table_name, table_name, target_table
from dashboard.errors import PlainError

log = logging.getLogger("dashboard.sync")
EXCHANGE_SCHEMA = 1  # the version of the change log and snapshot format below
ID, REVISION = "global_id", "row_revision"
RECORD_ACTIONS = ("create", "update", "delete", "restore")
LOG = "core__sync_changes"


class SyncError(PlainError):
    """Permanent record IDs could not be given safely; nothing was changed."""


def new_id() -> str:
    """A new permanent ID: random (UUID version 4), never made from a name, a row number, a time or a path."""
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _columns(conn, name: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}


def has_identity(conn, name: str) -> bool:
    """True once a table has its permanent ID and revision columns."""
    return {ID, REVISION} <= _columns(conn, name)


# ----- the household's identity and epoch ------------------------------------------------------------

def read_state(conn) -> dict | None:
    """{"household_id", "epoch", "exchange_schema"}, or None before permanent IDs started."""
    try:
        found = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM core__sync_state")}
    except sqlite3.OperationalError:
        return None  # a data file from before decision 0100
    if "household_id" not in found:
        return None
    return {"household_id": found["household_id"], "epoch": int(found.get("epoch", "0")),
            "exchange_schema": int(found.get("exchange_schema", str(EXCHANGE_SCHEMA)))}


def _put(conn, key: str, value: str) -> None:
    conn.execute("INSERT INTO core__sync_state (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO "
                 "UPDATE SET value = excluded.value, updated_at = excluded.updated_at", (key, value, _now()))


def _start_epoch(conn, epoch: int, reason: str, new_ids: int = 0) -> None:
    _put(conn, "epoch", str(epoch))
    conn.execute("INSERT INTO core__sync_epochs (epoch, started_at, reason, new_ids) VALUES (?, ?, ?, ?)",
                 (epoch, _now(), reason, new_ids))


def epochs(conn) -> list[dict]:
    """Every epoch, oldest first, with why it started."""
    return [dict(r) for r in conn.execute("SELECT epoch, started_at, reason, new_ids FROM core__sync_epochs "
                                          "ORDER BY epoch")]


# ----- giving permanent IDs (start-up and restore) -------------------------------------------------------

def _index(name: str) -> str:
    return f"{name}__{ID}__idx"


def _needs_work(conn, module: Module) -> bool:
    for table in module.tables.values():
        name = table_name(module.name, table.name)
        columns = _columns(conn, name)
        if not columns:
            continue
        if not {ID, REVISION} <= columns:
            return True
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (_index(name),)).fetchone():
            return True
        if conn.execute(f"SELECT 1 FROM {name} WHERE {ID} IS NULL LIMIT 1").fetchone():
            return True
    return False


def _has_records(conn, modules: list[Module]) -> bool:
    for module in modules:
        for table in module.tables.values():
            name = table_name(module.name, table.name)
            if _columns(conn, name) and conn.execute(f"SELECT 1 FROM {name} LIMIT 1").fetchone():
                return True
    return False


def _upgrade(conn, module: Module) -> tuple[int, list[str]]:
    """Give one module's tables their ID and revision columns and an ID for every record (deleted ones too),
    in one transaction, under the module's own confinement rule. Returns (IDs given, tables rebuilt)."""
    plan = {}
    for table in module.tables.values():
        name = table_name(module.name, table.name)
        columns = _columns(conn, name)
        if columns:
            plan[name] = columns
    known = {r[0] for r in conn.execute("SELECT table_name FROM core__sync_tables")}
    rebuilt = [name for name, columns in plan.items() if name in known and ID not in columns]
    given = 0
    with db.transaction(conn):
        conn.set_authorizer(migrations._confined_to(module.name))  # only this module's own tables (0055)
        try:
            for name, columns in plan.items():
                if ID not in columns:
                    conn.execute(f"ALTER TABLE {name} ADD COLUMN {ID} TEXT")
                if REVISION not in columns:
                    conn.execute(f"ALTER TABLE {name} ADD COLUMN {REVISION} INTEGER NOT NULL DEFAULT 0")
                missing = [r[0] for r in conn.execute(f"SELECT id FROM {name} WHERE {ID} IS NULL ORDER BY id")]
                conn.executemany(f"UPDATE {name} SET {ID} = ? WHERE id = ?", [(new_id(), i) for i in missing])
                given += len(missing)
                conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_index(name)} ON {name}({ID})")
                if conn.execute(f"SELECT 1 FROM {name} WHERE {ID} IS NULL LIMIT 1").fetchone():
                    raise SyncError(f"Some records in {name} could not be given a permanent ID.")
        finally:
            conn.set_authorizer(None)
        now = _now()
        conn.executemany("INSERT OR IGNORE INTO core__sync_tables (table_name, since) VALUES (?, ?)",
                         [(name, now) for name in plan])
    return given, rebuilt


def _upgrade_all(conn, found: list[Module], failures: dict | None) -> tuple[int, list[str]]:
    given, rebuilt = 0, []
    for module in found:
        if not _needs_work(conn, module):
            continue
        try:
            count, again = _upgrade(conn, module)
        except (sqlite3.Error, PlainError) as error:
            if failures is None:
                raise
            failures.setdefault(module.name, []).append(
                f"Its records could not be given permanent IDs, so it was left out and its records were not "
                f"changed. Details: {error}")
            continue
        given += count
        rebuilt += again
    return given, rebuilt


def prepare(conn, found: list[Module], before_change: Callable[[], None] | None = None,
            failures: dict | None = None) -> dict:
    """At start-up, after the migrations: make sure every record of every module in `found` has a
    permanent ID and revision, and that the household has an ID and an epoch.

    Safe to run every time: once done it changes nothing. If records already exist and need IDs,
    `before_change` is called first (start-up makes a backup there). A module whose tables cannot be
    upgraded is added to `failures` and left out, like a module whose migration failed."""
    work = [m for m in found if _needs_work(conn, m)]
    if work and before_change is not None and _has_records(conn, work):
        before_change()
    given, rebuilt = _upgrade_all(conn, work, failures)
    state = read_state(conn)
    with db.transaction(conn):
        if state is None:
            _put(conn, "household_id", new_id())
            _put(conn, "exchange_schema", str(EXCHANGE_SCHEMA))
            _start_epoch(conn, 1, "Permanent record IDs started on this computer.", given)
        elif rebuilt:
            # A module update rebuilt a table without carrying its IDs across: its records have new IDs now,
            # so anything copied before must not be matched to them. A new epoch says so.
            _start_epoch(conn, state["epoch"] + 1, "A module update rebuilt " + ", ".join(rebuilt) +
                         "; its records were given new permanent IDs.", given)
            log.warning("Tables rebuilt without their permanent IDs: %s", ", ".join(rebuilt))
    return {"ids_given": given, "rebuilt": rebuilt}


def after_restore(conn, found: list[Module], previous: dict | None, undo: bool = False) -> dict:
    """On a backup being put back (decision 0079): keep its IDs, give IDs to a backup from before they
    existed, and start a new epoch above both the restored copy's and the records-in-use's (`previous`), so
    an epoch never goes back and nothing from before the restore is mistaken for now."""
    had = read_state(conn)
    given, _ = _upgrade_all(conn, found, None)
    floor = max((previous or {}).get("epoch", 0), (had or {}).get("epoch", 0))
    household = (had or previous or {}).get("household_id") or new_id()
    reason = "Undid a restore." if undo else "Restored a backup."
    if had is None:
        reason += " The backup was from before permanent IDs, so its records were given new ones."
    with db.transaction(conn):
        _put(conn, "household_id", household)
        _put(conn, "exchange_schema", str(EXCHANGE_SCHEMA))
        _start_epoch(conn, floor + 1, reason, given)
    return {"epoch": floor + 1, "ids_given": given}


# ----- the travel rule ---------------------------------------------------------------------------------

def travels(column: Column, row: dict, held: bool = False) -> bool:
    """May this column's value in this row travel to another computer of the household? (decision 0100)"""
    if column.travels == "never":
        return False
    if column.travels == "when":
        (other, allowed), = column.travels_when.items()
        return not held and row.get(other) in allowed
    return True


def unreviewed(registry) -> list[str]:
    """Private columns that do not say whether they travel: kept local, and a later exchange must refuse them."""
    return [f"{name}.{c.name}" for name, info in registry.items() for c in info.table.columns.values()
            if not c.travels_reviewed]


def _id_of(conn, name: str, local_id, give: bool = True) -> str | None:
    """The permanent ID of one record, by its local number. Inside a change, one that somehow has none is
    given one now; a read-only caller (`give=False`) gets None instead and writes nothing."""
    if local_id is None or not has_identity(conn, name):
        return None
    row = conn.execute(f"SELECT {ID} FROM {name} WHERE id = ?", (local_id,)).fetchone()
    if row is None:
        return None
    if row[0] or not give:
        return row[0] or None
    found = new_id()
    conn.execute(f"UPDATE {name} SET {ID} = ? WHERE id = ?", (found, local_id))
    return found


def _project(conn, info, row: dict, names, held: set, give: bool = True) -> tuple[dict, list[str]]:
    """The values of `names` that may travel ({field: value}, links as permanent IDs) and the names of
    those that stay on this computer. Many-to-many links are logged as pairs instead."""
    patch, withheld = {}, []
    for name in names:
        column = info.table.columns[name]
        if not travels(column, row, name in held):
            withheld.append(name)
        elif column.type == "link":
            patch[name] = _id_of(conn, target_table(info.module.name, column), row.get(name), give)
        elif column.type != "links":
            patch[name] = row.get(name)
    return patch, sorted(withheld)


def _held(conn, name: str, global_id: str) -> set[str]:
    return {r[0] for r in conn.execute("SELECT column_name FROM core__sync_held WHERE table_name = ? AND "
                                       "global_id = ?", (name, global_id))}


def _note_kind_changes(conn, info, global_id: str, row: dict, before: dict, changed: set) -> None:
    """A row whose kind moved from a kind that stays local (such as access instructions) to one that travels
    (such as a medication) keeps its old value on this computer until that value is typed again, so a value
    typed as private never travels just because its label changed (STAGE1.md, decision 0100). The other way
    round needs nothing here: the value simply stops travelling."""
    for column in info.table.columns.values():
        if column.travels != "when":
            continue
        if column.name in changed:
            conn.execute("DELETE FROM core__sync_held WHERE table_name = ? AND global_id = ? AND column_name = ?",
                         (info.name, global_id, column.name))
            continue
        (other, allowed), = column.travels_when.items()
        if other not in changed or other not in before:
            continue
        if before[other] not in allowed and row.get(other) in allowed and row.get(column.name) not in (None, ""):
            conn.execute("INSERT OR IGNORE INTO core__sync_held (table_name, global_id, column_name, since) "
                         "VALUES (?, ?, ?, ?)", (info.name, global_id, column.name, _now()))


# ----- writing the change log ----------------------------------------------------------------------------

def record(conn, info, record_id: int, action: str, before, after, effect: bool = False,
           at: str | None = None) -> None:
    """Write (or extend) this operation's change-log line for one record, inside the caller's transaction.

    Called by Records for every create, change, delete and restore, right after the row is written. A record
    touched twice by one operation (an item and its first batch) keeps one line and one revision step.
    `effect` marks changes worked out from another record (an item's amount from its batches): a later
    exchange recomputes these rather than applying them as separate edits."""
    if action not in RECORD_ACTIONS or not has_identity(conn, info.name):
        return
    state = read_state(conn)
    if state is None:
        return
    found = conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (record_id,)).fetchone()
    if found is None:
        return
    row = dict(found)
    global_id = row[ID] or _id_of(conn, info.name, record_id)
    operation = db.current_operation(conn) or new_id().replace("-", "")
    declared = info.table.columns
    now_changed = {k for k in (after or {}) if k in declared} if action in ("create", "update") else set()
    prior = conn.execute(f"SELECT * FROM {LOG} WHERE operation_id = ? AND table_name = ? AND global_id = ? "
                         f"AND target_id = ''", (operation, info.name, global_id)).fetchone()
    if prior is not None:
        base, revision = prior["base_revision"], prior["revision"]
        changed = set(json.loads(prior["columns"])) | now_changed
        if prior["action"] == "create" and action == "update":
            action = "create"  # a record made and then worked on by one operation is still one new record
        effect = bool(prior["effect"]) and effect
    else:
        base = row[REVISION] or 0
        revision = base + 1
        conn.execute(f"UPDATE {info.name} SET {REVISION} = ? WHERE id = ?", (revision, record_id))
        changed = now_changed
    if action == "update":
        _note_kind_changes(conn, info, global_id, row, before or {}, now_changed)
    held = _held(conn, info.name, global_id)
    if action == "create":
        names = list(declared)
    elif action == "update":
        names = sorted(changed)
    else:
        names = []
    patch, withheld = _project(conn, info, row, names, held)
    when = at or _now()
    values = (action, json.dumps(sorted(changed)), json.dumps(patch, sort_keys=True), json.dumps(withheld),
              int(effect))
    if prior is not None:
        conn.execute(f"UPDATE {LOG} SET action = ?, columns = ?, patch = ?, withheld = ?, effect = ? WHERE seq = ?",
                     values + (prior["seq"],))
    else:
        conn.execute(f"INSERT INTO {LOG} (epoch, operation_id, table_name, global_id, base_revision, revision, "
                     f"action, columns, patch, withheld, effect, exchange_schema, at) "
                     f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (state["epoch"], operation, info.name, global_id, base, revision) + values +
                     (EXCHANGE_SCHEMA, when))
    _record_pairs(conn, info, row, global_id, operation, state, base, revision, before, after, now_changed, when)


def _record_pairs(conn, info, row, global_id, operation, state, base, revision, before, after, changed, when):
    """A many-to-many link (such as a document's copy places) is logged pair by pair, as the two records'
    permanent IDs; adding a pair that is already there adds nothing."""
    for name in sorted(changed):
        column = info.table.columns[name]
        if column.type != "links" or not travels(column, row):
            continue
        old, new = set((before or {}).get(name) or []), set((after or {}).get(name) or [])
        join, target = join_table_name(info.module.name, info.table.name, name), target_table(info.module.name, column)
        for action, ids in (("link", new - old), ("unlink", old - new)):
            for local_id in sorted(ids):
                other = _id_of(conn, target, local_id)
                if other is None:
                    continue
                conn.execute(
                    f"INSERT INTO {LOG} (epoch, operation_id, table_name, global_id, target_id, base_revision, "
                    f"revision, action, columns, patch, withheld, effect, exchange_schema, at) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{{}}', '[]', 0, ?, ?) "
                    f"ON CONFLICT(operation_id, table_name, global_id, target_id) DO UPDATE SET action = excluded.action",
                    (state["epoch"], operation, join, global_id, other, base, revision, action,
                     json.dumps([name]), EXCHANGE_SCHEMA, when))


# ----- reading it back (offline only in stage 1) -----------------------------------------------------------

def changes(conn, after_seq: int = 0, limit: int = 500) -> list[dict]:
    """The change log after `after_seq`, oldest first: what a later stage would send, in its order."""
    rows = conn.execute(f"SELECT * FROM {LOG} WHERE seq > ? ORDER BY seq LIMIT ?", (after_seq, max(1, limit)))
    found = []
    for r in rows:
        entry = dict(r)
        for key in ("columns", "patch", "withheld"):
            entry[key] = json.loads(entry[key])
        found.append(entry)
    return found


def snapshot(conn, registry) -> dict:
    """Every record (deleted ones as tombstones) and many-to-many pair, filtered by the travel rule exactly
    as the change log is: the full copy a later stage would send first. Built offline; nothing is sent."""
    state = read_state(conn) or {}
    records, pairs = [], []
    for name, info in registry.items():
        if not has_identity(conn, name):
            continue
        held: dict[str, set] = {}
        for r in conn.execute("SELECT global_id, column_name FROM core__sync_held WHERE table_name = ?", (name,)):
            held.setdefault(r[0], set()).add(r[1])
        names = [c for c, col in info.table.columns.items() if col.type != "links"]
        ids = {}
        for found in conn.execute(f"SELECT * FROM {name} ORDER BY id").fetchall():
            row = dict(found)
            ids[row["id"]] = row[ID]
            values, withheld = _project(conn, info, row, names, held.get(row[ID], set()), give=False)
            records.append({"table": name, "id": row[ID], "revision": row[REVISION],
                            "deleted": bool(row["deleted_at"]), "values": values, "withheld": withheld})
        for column in info.table.columns.values():
            if column.type != "links" or column.travels == "never":
                continue
            join = join_table_name(info.module.name, info.table.name, column.name)
            target = target_table(info.module.name, column)
            for pair in conn.execute(f"SELECT from_id, to_id FROM {join} ORDER BY from_id, to_id").fetchall():
                pairs.append({"table": join, "from": ids.get(pair[0]), "to": _id_of(conn, target, pair[1], False)})
    return {"exchange_schema": EXCHANGE_SCHEMA, "household_id": state.get("household_id"),
            "epoch": state.get("epoch"), "records": records, "pairs": pairs}


def check(conn, registry) -> list[str]:
    """Everything that would stop a later exchange, in plain words; empty when all is well. Fails closed:
    a table without IDs, a missing or repeated ID, a link to nothing, a table no module declares, or a
    private column that does not say whether it travels."""
    problems = []
    joins = set()
    for name, info in registry.items():
        joins |= {join_table_name(info.module.name, info.table.name, c.name)
                  for c in info.table.columns.values() if c.type == "links"}
        for column in info.table.columns.values():  # a pair that names a record that is not there
            if column.type == "links":
                join = join_table_name(info.module.name, info.table.name, column.name)
                target = target_table(info.module.name, column)
                if column.optional and not _columns(conn, target):
                    continue  # an optional module that is not installed (decision 0115): nothing to point at
                if conn.execute(f"SELECT 1 FROM {join} AS p LEFT JOIN {name} AS a ON a.id = p.from_id "
                                f"LEFT JOIN {target} AS b ON b.id = p.to_id "
                                f"WHERE a.id IS NULL OR b.id IS NULL LIMIT 1").fetchone():
                    problems.append(f"{join} has a pair that points at a record that is not there.")
        if not has_identity(conn, name):
            problems.append(f"{name} has no permanent IDs.")
            continue
        if conn.execute(f"SELECT 1 FROM {name} WHERE {ID} IS NULL OR {ID} = '' LIMIT 1").fetchone():
            problems.append(f"{name} has records without a permanent ID.")
        if conn.execute(f"SELECT 1 FROM {name} GROUP BY {ID} HAVING COUNT(*) > 1 LIMIT 1").fetchone():
            problems.append(f"{name} has two records with the same permanent ID.")
        for column in info.table.columns.values():
            if column.type == "link":
                target = target_table(info.module.name, column)
                if column.optional and not _columns(conn, target):
                    continue  # an optional module that is not installed (decision 0115): nothing to point at
                if conn.execute(f"SELECT 1 FROM {name} AS a LEFT JOIN {target} AS b ON b.id = a.{column.name} "
                                f"WHERE a.{column.name} IS NOT NULL AND b.id IS NULL LIMIT 1").fetchone():
                    problems.append(f"{name}.{column.name} points at a record that is not there.")
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '%\\_\\_%' "
                                "ESCAPE '\\' AND name NOT LIKE 'core\\_\\_%' ESCAPE '\\'").fetchall():
        if name not in registry and name not in joins:
            problems.append(f"{name} is not declared by any module in use, so it cannot be shared.")
    problems += [f"{c} is private and does not say whether it travels." for c in unreviewed(registry)]
    return problems
