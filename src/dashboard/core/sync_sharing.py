"""What your other computers get: the household's sharing choice for each list and detail, starting from each module's own travel rule (decision 0140).

A list is Shared with your other computers, Shared but not the private details (said "but not the amount" where
a private detail is an amount), or Only on this computer. A detail is Shared, Only on this computer, or, where its
module shares it only for some kinds (an Important detail), Shared only for those kinds. With no choice saved,
everything follows the module's own rule in tables.toml (decision 0100), so the change log is exactly as before.

A column a module marks `travels_fixed` (codes, which work like passwords) and a private column whose module has
not said whether it travels can never be shared: they show as fixed, with the reason. Keeping something on this
computer happens at once and also cleans what is already waiting in the change log; starting to share something
private needs the person's confirmation, and every choice is a line in history, with Undo for one that shared more.
Nothing here names a module: it works over every declared table and column.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dashboard.core import db, fraud_guard
from dashboard.core.modules import Column
from dashboard.core.schema import join_table_name
from dashboard.errors import PlainError

TABLE = "core__sharing_choices"
HISTORY = TABLE  # history lines are kept in core__audit under this name, record_id 0
LOG = "core__sync_changes"
LIST_CHOICES = ("local", "shared_not_private", "shared")  # strictest first
DETAIL_CHOICES = ("local", "kinds", "shared")  # strictest first
LIST_WORDS = {"shared": "Shared with your other computers",
              "shared_not_private": "Shared, but not the private details",
              "local": "Only on this computer"}
DETAIL_WORDS = {"shared": "Shared with your other computers", "kinds": "Shared only for some kinds",
                "local": "Only on this computer"}
MONEY_TYPES = ("money",)
UNREVIEWED = "Its module has not said yet whether this may travel, so it stays on this computer."


class SharingError(PlainError):
    """A sharing choice could not be saved; nothing was changed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----- what each list and detail may be -------------------------------------------------------------------

def fixed_reason(column: Column) -> str | None:
    """Why this detail can never travel, or None when the household may choose."""
    if column.travels_fixed:
        return column.travels_fixed
    if not column.travels_reviewed:
        return UNREVIEWED
    return None


def private_columns(info) -> list[Column]:
    """The private details of a list that could travel by choice (not the fixed ones)."""
    return [c for c in info.table.columns.values() if c.sensitive and fixed_reason(c) is None]


def list_default(info) -> str:
    return "local" if info.table.travels == "never" else "shared"


def detail_default(column: Column) -> str:
    if fixed_reason(column) is not None or column.travels == "never":
        return "local"
    return "kinds" if column.travels == "when" else "shared"


def list_options(info) -> list[str]:
    """Shared, Shared but not the private details (only where there are any), Only on this computer."""
    return ["shared"] + (["shared_not_private"] if private_columns(info) else []) + ["local"]


def detail_options(column: Column) -> list[str]:
    """The choices one detail offers; none for a fixed detail. A detail its module shares only for some kinds
    (an Important detail) can be kept here, or shared for those kinds, never for every kind: the other kinds
    (access instructions) stay on this computer."""
    if fixed_reason(column) is not None:
        return []
    return ["kinds", "local"] if column.travels == "when" else ["shared", "local"]


def list_words(info, choice: str) -> str:
    if choice == "shared_not_private":
        if any(c.type in MONEY_TYPES for c in private_columns(info)):
            return "Shared, but not the amount"
        return LIST_WORDS[choice]
    return LIST_WORDS[choice]


def detail_words(column: Column, choice: str, kinds_words: str = "") -> str:
    if choice == "kinds" and kinds_words:
        return f"Shared only for {kinds_words}"
    return DETAIL_WORDS[choice]


def kinds_words(info, column: Column) -> str:
    """"allergy, condition or medication": the kinds a detail is shared for, in the module's own words."""
    if column.travels != "when":
        return ""
    (other, allowed), = column.travels_when.items()
    names = {c.key: c.label for c in info.table.columns[other].choices}
    found = [names.get(k, k).lower() for k in allowed]
    return found[0] if len(found) == 1 else ", ".join(found[:-1]) + " or " + found[-1]


# ----- the household's saved choices -------------------------------------------------------------------------

def _saved(conn, table: str | None = None) -> dict:
    """{(table, column or ''): choice} as saved; empty for a data file from before decision 0140."""
    try:
        if table is None:
            rows = conn.execute(f"SELECT table_name, column_name, choice FROM {TABLE}").fetchall()
        else:
            rows = conn.execute(f"SELECT table_name, column_name, choice FROM {TABLE} WHERE table_name = ?",
                                (table,)).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {(r[0], r[1]): r[2] for r in rows}


@dataclass
class Rules:
    """One list's sharing as it is now: the list's choice and each detail's, defaults filled in."""
    info: object
    list: str
    details: dict = field(default_factory=dict)

    def allows(self, column: Column, row: dict, held: bool = False) -> bool:
        """May this column's value in this row travel? Never more than the module's rule unless chosen."""
        if self.list == "local" or fixed_reason(column) is not None:
            return False
        if self.list == "shared_not_private" and column.sensitive:
            return False
        choice = self.details.get(column.name, detail_default(column))
        if choice == "local":
            return False
        if choice == "kinds":
            (other, allowed), = column.travels_when.items()
            return not held and row.get(other) in allowed
        return True

    def status(self, column: Column) -> int:
        """0 stays here, 1 travels for some rows (some kinds), 2 travels: for what will start travelling."""
        if self.list == "local" or fixed_reason(column) is not None:
            return 0
        if self.list == "shared_not_private" and column.sensitive:
            return 0
        choice = self.details.get(column.name, detail_default(column))
        return DETAIL_CHOICES.index(choice)


def rules(conn, info, saved: dict | None = None) -> Rules:
    """The sharing of one list now: saved choices over the module's rule."""
    found = _saved(conn, info.name) if saved is None else saved
    choice = found.get((info.name, ""), list_default(info))
    if choice not in list_options(info):  # "but not the private details" on a list that no longer has any
        choice = "shared"
    details = {}
    for column in info.table.columns.values():
        wanted = found.get((info.name, column.name))
        details[column.name] = wanted if wanted in detail_options(column) else detail_default(column)
    return Rules(info, choice, details)


def current(conn, registry) -> dict:
    """{item key: choice} for every list and every choosable detail: "table" and "table.column"."""
    saved = _saved(conn)
    found = {}
    for name, info in registry.items():
        now = rules(conn, info, saved)
        found[name] = now.list
        for column in info.table.columns.values():
            if detail_options(column):
                found[f"{name}.{column.name}"] = now.details[column.name]
    return found


def default_of(registry, key: str) -> str:
    table, _, column = key.partition(".")
    info = registry[table]
    return detail_default(info.table.columns[column]) if column else list_default(info)


def options_of(registry, key: str) -> list[str]:
    table, _, column = key.partition(".")
    info = registry.get(table)
    if info is None:
        return []
    if not column:
        return list_options(info)
    found = info.table.columns.get(column)
    return detail_options(found) if found is not None else []


def _rank(key: str, choice: str) -> int:
    order = DETAIL_CHOICES if "." in key else LIST_CHOICES
    return order.index(choice)


def loosens(key: str, before: str, after: str) -> bool:
    return _rank(key, after) > _rank(key, before)


# ----- what a change would start or stop sharing -----------------------------------------------------------

def _with(conn, registry, wanted: dict) -> dict:
    """{table: Rules} for the tables in `wanted` as they would be with those choices."""
    saved = _saved(conn)
    for key, choice in wanted.items():
        table, _, column = key.partition(".")
        saved[(table, column)] = choice
    return {t: rules(conn, registry[t], saved) for t in {k.partition(".")[0] for k in wanted}}


def starts(conn, registry, wanted: dict) -> list[dict]:
    """What would start travelling with these choices, list by list: [{"table", "columns": [Column...],
    "list_starts": bool, "private": bool}]. A list that starts being shared also tells another computer that
    its records exist."""
    before = {t: rules(conn, registry[t]) for t in {k.partition(".")[0] for k in wanted}}
    after = _with(conn, registry, wanted)
    found = []
    for table in sorted(after):
        info = registry[table]
        old, new = before[table], after[table]
        columns = [c for c in info.table.columns.values() if new.status(c) > old.status(c)]
        list_starts = old.list == "local" and new.list != "local"
        if columns or list_starts:
            # private history, a private detail, or a list with private details starting to be shared at all
            # (another computer would learn, say, that money came back)
            private = bool(info.table.private or any(c.sensitive for c in columns) or
                           (list_starts and any(c.sensitive for c in info.table.columns.values())))
            found.append({"table": table, "info": info, "columns": columns, "list_starts": list_starts,
                          "private": private})
    return found


def needs_confirmation(found: list[dict]) -> bool:
    """Starting to share anything private (a private detail, or a list of private history) asks first."""
    return any(f["private"] for f in found)


def check(registry, wanted: dict) -> None:
    """Refuse a choice a list or detail does not offer, such as sharing a code."""
    for key, choice in wanted.items():
        options = options_of(registry, key)
        if not options:
            raise SharingError("That detail can never be shared, so nothing was changed.")
        if choice not in options:
            raise SharingError("That choice is not one this list offers, so nothing was changed.")


# ----- saving a choice -------------------------------------------------------------------------------------

def _store(conn, registry, key: str, choice: str, now: str) -> None:
    table, _, column = key.partition(".")
    if choice == default_of(registry, key):
        conn.execute(f"DELETE FROM {TABLE} WHERE table_name = ? AND column_name = ?", (table, column))
    else:
        conn.execute(f"INSERT INTO {TABLE} (table_name, column_name, choice, updated_at) VALUES (?, ?, ?, ?) "
                     f"ON CONFLICT(table_name, column_name) DO UPDATE SET choice = excluded.choice, "
                     f"updated_at = excluded.updated_at", (table, column, choice, now))


def apply(conn, registry, wanted: dict, actor: str = "person", undoing: int | None = None) -> int | None:
    """Save these choices in one transaction, with one line in history, and clean the change log of anything
    a tighter choice now keeps here. Returns the history line's number, or None when nothing changed.

    The caller decides whether the person has confirmed: this only refuses choices that are not offered."""
    check(registry, wanted)
    now_choices = current(conn, registry)
    changed = {k: v for k, v in wanted.items() if now_choices.get(k) != v}
    if not changed:
        return None
    before = {k: now_choices[k] for k in changed}
    loosened = any(loosens(k, before[k], changed[k]) for k in changed)
    tightened = [k for k in changed if loosens(k, changed[k], before[k])]
    now = _now()
    with db.transaction(conn):
        for key, choice in changed.items():
            _store(conn, registry, key, choice, now)
        after = {"choices": changed, "loosened": loosened}
        if undoing is not None:
            after["undid"] = undoing
        cursor = conn.execute(
            "INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
            "VALUES (?, ?, ?, ?, 0, ?, ?)",
            (now, actor, "sharing_undo" if undoing is not None else "sharing_choice", HISTORY,
             json.dumps({"choices": before}, sort_keys=True), json.dumps(after, sort_keys=True)))
        if tightened:
            scrub(conn, registry, {k.partition(".")[0] for k in tightened})
    return cursor.lastrowid


def scrub(conn, registry, tables, after_seq: int = 0) -> int:
    """Clean change-log lines after `after_seq` (stage 1 sends nothing, so every line) of what these lists now
    keep here: every line of a list now Only on this computer (so not even that a record exists is left), and
    the values of details now kept here, which become withheld names. Returns how many lines changed."""
    touched = 0
    try:
        conn.execute(f"SELECT 1 FROM {LOG} LIMIT 1")
    except sqlite3.OperationalError:
        return 0
    for table in sorted(tables):
        info = registry.get(table)
        if info is None:
            continue
        now = rules(conn, info)
        if now.list == "local":
            joins = [join_table_name(info.module.name, info.table.name, c.name)
                     for c in info.table.columns.values() if c.type == "links"]
            for name in [table] + joins:
                touched += conn.execute(f"DELETE FROM {LOG} WHERE seq > ? AND table_name = ?",
                                        (after_seq, name)).rowcount
            continue
        kept = {c.name for c in info.table.columns.values() if now.status(c) == 0}
        for column in info.table.columns.values():
            if column.type == "links" and column.name in kept:
                join = join_table_name(info.module.name, info.table.name, column.name)
                touched += conn.execute(f"DELETE FROM {LOG} WHERE seq > ? AND table_name = ?",
                                        (after_seq, join)).rowcount
        for line in conn.execute(f"SELECT seq, patch, withheld FROM {LOG} WHERE seq > ? AND table_name = ?",
                                 (after_seq, table)).fetchall():
            patch, withheld = json.loads(line["patch"]), set(json.loads(line["withheld"]))
            gone = kept & set(patch)
            if gone:
                for name in gone:
                    patch.pop(name)
                conn.execute(f"UPDATE {LOG} SET patch = ?, withheld = ? WHERE seq = ?",
                             (json.dumps(patch, sort_keys=True), json.dumps(sorted(withheld | gone)), line["seq"]))
                touched += 1
    return touched


def mask_waiting_cards(conn, after_seq: int = 0) -> int:
    """Decision 0142: a full card number that reached a waiting (unsent) change-log line before decision 0141 is
    replaced there by its last four digits (••••1234), whichever field it sits in. Stage 1 sends nothing, so every
    line after `after_seq` is waiting. Returns how many lines changed."""
    try:
        lines = conn.execute(f"SELECT seq, patch FROM {LOG} WHERE seq > ?", (after_seq,)).fetchall()
    except sqlite3.OperationalError:
        return 0
    changed = 0
    for line in lines:
        try:
            patch = json.loads(line["patch"])
        except ValueError:
            continue
        cleaned = {k: fraud_guard.mask_cards(v) if isinstance(v, str) else v for k, v in patch.items()}
        if cleaned != patch:
            conn.execute(f"UPDATE {LOG} SET patch = ? WHERE seq = ?", (json.dumps(cleaned, sort_keys=True), line["seq"]))
            changed += 1
    return changed


# ----- history and Undo ------------------------------------------------------------------------------------

def history(conn, limit: int = 20) -> list[dict]:
    """The household's sharing choices, newest first: {"id", "at", "action", "before", "after", "loosened",
    "undid"}."""
    rows = conn.execute("SELECT id, at, action, before, after FROM core__audit WHERE table_name = ? AND "
                        "action IN ('sharing_choice', 'sharing_undo') ORDER BY id DESC LIMIT ?",
                        (HISTORY, max(1, limit))).fetchall()
    found = []
    for r in rows:
        after = json.loads(r["after"] or "{}")
        found.append({"id": r["id"], "at": r["at"], "action": r["action"],
                      "before": json.loads(r["before"] or "{}").get("choices", {}),
                      "after": after.get("choices", {}), "loosened": bool(after.get("loosened")),
                      "undid": after.get("undid")})
    return found


def _undone(conn) -> set[int]:
    found = set()
    for r in conn.execute("SELECT after FROM core__audit WHERE table_name = ? AND action = 'sharing_undo'",
                          (HISTORY,)):
        undid = json.loads(r[0] or "{}").get("undid")
        if undid is not None:
            found.add(int(undid))
    return found


def undoable(conn, registry, entry: dict) -> bool:
    """A choice that shared more can be undone while every one of its choices is still as it left them."""
    if entry["action"] != "sharing_choice" or not entry["loosened"] or entry["id"] in _undone(conn):
        return False
    now = current(conn, registry)
    return all(now.get(k) == v for k, v in entry["after"].items()) and \
        all(options_of(registry, k) for k in entry["before"])


def undo(conn, registry, entry_id: int, actor: str = "person") -> int:
    """Put back the choices from before one that shared more. Keeping things here happens at once."""
    found = next((e for e in history(conn, 10_000) if e["id"] == entry_id), None)
    if found is None or not undoable(conn, registry, found):
        raise SharingError("This choice has changed since then, or was already undone, so nothing was undone.")
    done = apply(conn, registry, found["before"], actor, undoing=entry_id)
    if done is None:
        raise SharingError("Nothing needed undoing.")
    return done
