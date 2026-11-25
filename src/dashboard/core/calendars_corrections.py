"""Not a done day (decision 0132): a household takes an earlier done day off a calendar, kept as a history entry and put back the same way."""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import date

from dashboard.core import dates, db
from dashboard.core.records import ActionNotAvailable, RecordNotFound, Records, TableInfo

# The two history entries this writes, beside the record's own history. They only ever add a line: nothing in
# the record or its earlier history is changed or deleted, so putting a day back is one more line, not an erase.
OFF = "not_done_day"
BACK = "done_day_back"
KINDS = (OFF, BACK)
NOT_EARLIER = ("Nothing was changed. That day is not an earlier done day from history any more: it may be the "
               "date the record keeps now (change that on its own page), or it was already taken off.")


def _rows(conn: sqlite3.Connection, table: str, extra: str = "", params: tuple = ()):
    for row in conn.execute(f"SELECT id, record_id, action, after FROM core__audit WHERE table_name = ? "
                            f"AND action IN (?, ?){extra} ORDER BY id", (table, *KINDS, *params)):
        try:
            after = json.loads(row["after"] or "{}")
            yield row["record_id"], row["action"], after["operation"], date.fromisoformat(after["calendar_day"])
        except (KeyError, TypeError, ValueError):
            continue


def removed(conn: sqlite3.Connection, table: str) -> dict[tuple[int, date], str]:
    """Each (record, day) the household said was not a done day and has not put back, with its operation."""
    taken, back = {}, set()
    for record_id, action, op, day in _rows(conn, table):
        if action == OFF:
            taken[op] = (record_id, day)
        else:
            back.add(op)
    return {key: op for op, key in taken.items() if op not in back}


def find(conn: sqlite3.Connection, table: str, op: str) -> dict | None:
    """One "Not a done day" by its operation: its record, its day and whether it is still off the calendar."""
    found = None
    for record_id, action, saved_op, day in _rows(conn, table):
        if saved_op != op:
            continue
        if action == OFF and found is None:
            found = {"record_id": record_id, "day": day, "off": True}
        elif action == BACK and found is not None:
            found["off"] = False
    return found


def take_off(store: Records, info: TableInfo, record_id: int, day: date, actor: str = "person") -> str:
    """Say `day` was not a done day for one record: one history entry, and the day leaves the calendar and its
    bars. Only a day read from history (an earlier date or an old press) can be taken off; the date the record
    keeps now is changed on its own page. Pressing twice gives the first entry back. Returns its operation."""
    from dashboard.core import calendars  # calendars reads `removed`, so it is imported only when needed
    store._check_actor(actor)
    with db.transaction(store.conn):
        existing = removed(store.conn, info.name).get((record_id, day))
        if existing:
            return existing
        found = [d for d in calendars.done_days(store.conn, store.registry, info, info.table.calendar["when"], day,
                                                day) if d.record_id == record_id]
        if not found or found[0].kind == "now":
            raise ActionNotAvailable(NOT_EARLIER)
        op = secrets.token_urlsafe(18)
        store._audit(actor, OFF, info, record_id, None, {"calendar_day": day.isoformat(), "operation": op})
    return op


def put_back(store: Records, info: TableInfo, op: str, actor: str = "person") -> dict:
    """Undo one "Not a done day": one more history entry, and the day shows again if its history still says so."""
    store._check_actor(actor)
    with db.transaction(store.conn):
        found = find(store.conn, info.name, op) if isinstance(op, str) else None
        if found is None:
            raise RecordNotFound("That was not found. Nothing was changed.")
        if not found["off"]:
            raise ActionNotAvailable("That day was already put back on the calendar. Nothing was changed.")
        store._audit(actor, BACK, info, found["record_id"], None,
                     {"calendar_day": found["day"].isoformat(), "operation": op})
    return found


def history_words(conn: sqlite3.Connection, entry: dict) -> str | None:
    """A history line for either entry: "said 01/09/26 was not a done day: taken off the calendar"."""
    if entry.get("action") not in KINDS or not isinstance(entry.get("after"), dict):
        return None
    try:
        day = dates.show(date.fromisoformat(entry["after"]["calendar_day"]), dates.household_style(conn))
    except (KeyError, TypeError, ValueError):
        day = "a day"
    if entry["action"] == OFF:
        return f"said {day} was not a done day: taken off the calendar"
    return f"put {day} back on the calendar"
