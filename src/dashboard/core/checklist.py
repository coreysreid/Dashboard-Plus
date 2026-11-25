"""Things to do: Today, This week, This month and This year over the due dates modules already keep (decision 0107).

Nothing here stores a tick. A table takes part when its `watch.expiring` says `wording = "due"` (Home care
jobs, Garden jobs, alarm checks, kit checks, vehicle dates, document reviews, Routines...), with the same
`where` that keeps finished rows out of Needs attention. Every row is read fresh from its own table, so a
moved date, a deleted record or a module switched off changes the view at once, and one record is one row
however late it is. Completing stays with the record: its own Mark done form or one-step button, or else a
link to its page. What was done comes from the saved Mark done operations in history, never from a copy.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta

from dashboard.core import dates, reminder_moves, settings, watch
from dashboard.core.records import TableInfo

WINDOWS = ("today", "week", "month", "year")
# The household's own first day of the week (Settings); date.weekday() counts Monday as 0.
WEEK_STARTS = {"monday": 0, "saturday": 5, "sunday": 6}
WEEK_START_KEY = "household.week_starts"


@dataclass
class Source:
    """One table whose due dates appear: the date column, the filter that keeps finished rows out, its actions."""
    info: TableInfo
    date: str
    where: dict
    what: str
    forms: list = field(default_factory=list)  # actions that add a record through a small form (Mark done)
    presses: list = field(default_factory=list)  # one-step buttons that end the reminder (Garden's Mark done)
    what_when: list = field(default_factory=list)  # other words for some rows, like "bill check" (decision 0117)


@dataclass
class Task:
    """One record with a due date (or none yet), read now from its own table."""
    source: Source
    row: dict
    name: str
    due: date | None
    group: str  # "earlier" (before this year), "late", "today", "later" or "undated"
    what: str = ""  # what is due for this row: the list's `what`, or a `what_when` match (decision 0117)


@dataclass
class Done:
    """One saved Mark done (or Skip this time) whose date falls in the range and which was not undone."""
    source: Source
    record_id: int
    name: str
    on: date
    counts_as: str  # "done" or "skipped"
    operation: str
    planned: str | None
    missed: bool
    key: str  # the action that saved it, such as "done" or "skip"
    fields: tuple = ()  # the fields a one-step press set, such as ("done",): decision 0129 reads them


def sources(registry: dict[str, TableInfo]) -> list[Source]:
    """The tables of switched-on modules that keep a due date, in the registry's order."""
    found = []
    for info in registry.values():
        rule = info.table.watch.get("expiring") if isinstance(info.table.watch, dict) else None
        if not rule or rule.get("wording") != "due":
            continue  # a use-by date is not a task (Household stock batches)
        where = dict(rule.get("where") or {})
        forms = [a for a in info.table.actions if a.get("adds")]
        presses = [a for a in info.table.actions if not a.get("adds")
                   and any(k in a["set"] and a["set"][k] != v for k, v in where.items())]
        found.append(Source(info, rule["date"], where, rule.get("what") or "", forms, presses,
                            list(rule.get("what_when") or [])))
    return found


def week_start(conn: sqlite3.Connection) -> str:
    """The household's first day of the week: its setting, or Sunday where dates are written month first."""
    chosen = settings.get(conn, WEEK_START_KEY)
    if chosen in WEEK_STARTS:
        return chosen
    return "sunday" if dates.household_style(conn) == dates.MONTH_FIRST else "monday"


def bounds(window: str, today: date, first_day: str = "monday") -> tuple[date, date]:
    """The first and last day of the window around `today`, on the household's calendar (never a rolling 30 days)."""
    if window == "today":
        return today, today
    if window == "week":
        start = today - timedelta(days=(today.weekday() - WEEK_STARTS[first_day]) % 7)
        return start, start + timedelta(days=6)
    if window == "month":
        start = today.replace(day=1)
        following = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        return start, following - timedelta(days=1)
    if window == "year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    raise ValueError(f"'{window}' is not one of {', '.join(WINDOWS)}.")


def _rows(conn: sqlite3.Connection, source: Source, upto: date | None):
    clause, values = watch._where_sql(source.info, source.where)
    clause += reminder_moves.silent_clause(source.info.name)  # moved to another list: reminded there (0117)
    col = source.date
    if upto is None:  # No date yet
        sql = f"SELECT * FROM {source.info.name} WHERE deleted_at IS NULL AND ({col} IS NULL OR {col} = ''){clause}"
        return conn.execute(sql + " ORDER BY id LIMIT 500", values).fetchall()
    sql = (f"SELECT * FROM {source.info.name} WHERE deleted_at IS NULL AND {col} IS NOT NULL AND {col} != '' "
           f"AND {col} <= ?{clause} ORDER BY {col}, id")
    return conn.execute(sql, [upto.isoformat(), *values]).fetchall()


def tasks(conn: sqlite3.Connection, registry: dict[str, TableInfo], window: str, today: date,
          first_day: str = "monday", only: str | None = None) -> list[Task]:
    """Every open record due up to the end of the window (late ones included, once each), oldest first.
    `window` may also be "undated": records with no date yet. `only` keeps one table."""
    found = []
    start, end = bounds(window, today, first_day) if window != "undated" else (None, None)
    year_start = date(today.year, 1, 1)
    for source in sources(registry):
        if only and source.info.name != only:
            continue
        for row in _rows(conn, source, end):
            row = dict(row)
            due = None
            if end is not None:
                try:
                    due = date.fromisoformat(str(row[source.date])[:10])
                except ValueError:
                    continue
            if due is None:
                group = "undated"
            elif due < today:
                group = "earlier" if window == "year" and due < year_start else "late"
            elif due == today:
                group = "today"
            else:
                group = "later"
            name = watch._name(source.info, row, conn, registry, (source.date,))
            what = watch.what_for({"what": source.what, "what_when": source.what_when}, row)
            found.append(Task(source, row, name, due, group, what))
    found.sort(key=lambda t: (t.due or date.max, t.name.lower()))
    return found


def _live(conn: sqlite3.Connection, table: str, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    marks = ",".join("?" * len(ids))
    return {r[0] for r in conn.execute(f"SELECT id FROM {table} WHERE deleted_at IS NULL AND id IN ({marks})",
                                       list(ids))}


def done(conn: sqlite3.Connection, registry: dict[str, TableInfo], start: date, end: date,
         only: str | None = None) -> list[Done]:
    """Mark done and Skip this time saved for dates from `start` to `end`, newest first, leaving out any that
    were undone, whose record or added entry was deleted since, or whose module is off."""
    by_table = {s.info.name: s for s in sources(registry) if s.info.table.actions and (not only or s.info.name == only)}
    if not by_table:
        return []
    marks = ",".join("?" * len(by_table))
    # A completion is saved on or after the day it is dated, and history is kept in UTC: start a day early.
    since = (start - timedelta(days=1)).isoformat()
    rows = conn.execute(f"SELECT table_name, record_id, after FROM core__audit WHERE action = 'action' AND at >= ? "
                        f"AND table_name IN ({marks}) ORDER BY id", [since, *by_table]).fetchall()
    undone = {r[0] for r in conn.execute("SELECT json_extract(after, '$.operation') FROM core__audit "
                                         "WHERE action = 'undo' AND at >= ?", (since,))}
    picked, wanted, added = [], {}, {}
    for row in rows:
        source, result = by_table[row["table_name"]], json.loads(row["after"])
        if result.get("operation") in undone:
            continue
        action = next((a for a in source.info.table.actions if a["key"] == result.get("key")), None)
        latest = (action or {}).get("latest") or {}
        # A form is dated by the day the person entered; a one-step press by the day it was pressed (0112).
        day = result.get("on") if result.get("one_step") else (result.get("answers") or {}).get(latest.get("date"))
        try:
            on = date.fromisoformat(str(day)[:10])
        except ValueError:
            continue
        if not start <= on <= end:
            continue
        picked.append((source, row["record_id"], on, result, action))
        wanted.setdefault(source.info.name, set()).add(row["record_id"])
        if result.get("added_table"):
            added.setdefault(result["added_table"], set()).add(result.get("added"))
    live = {t: _live(conn, t, ids) for t, ids in wanted.items()}
    live_added = {t: _live(conn, t, {i for i in ids if isinstance(i, int)}) for t, ids in added.items()
                  if t in registry}
    names: dict[tuple[str, int], str] = {}
    found = []
    for source, record_id, on, result, action in picked:
        if record_id not in live.get(source.info.name, ()) or (result.get("added_table") and
                                                                 result.get("added") not in
                                                                 live_added.get(result["added_table"], ())):
            continue
        key = (source.info.name, record_id)
        if key not in names:
            row = conn.execute(f"SELECT * FROM {source.info.name} WHERE id = ?", (record_id,)).fetchone()
            names[key] = watch._name(source.info, row, conn, registry, (source.date,))
        planned = next((v for v in (result.get("copied") or {}).values() if v), None)
        found.append(Done(source, record_id, names[key], on, result.get("counts_as") or
                          (action or {}).get("counts_as") or "done", result["operation"], planned,
                          bool(result.get("missed")), result.get("key") or "",
                          tuple((result.get("after") or {}) if result.get("one_step") else ())))
    found.sort(key=lambda d: (d.on, d.operation), reverse=True)
    return found


def by_month(conn: sqlite3.Connection, registry: dict[str, TableInfo], year: int,
             only: str | None = None) -> list[dict]:
    """This year at a glance: for each month, how many open records are due in it, and how many times work
    was recorded as done or skipped. Worked out per month with one query per table; no day is filled in."""
    months = [{"month": m, "due": 0, "done": 0, "skipped": 0} for m in range(1, 13)]
    for source in sources(registry):
        if only and source.info.name != only:
            continue
        clause, values = watch._where_sql(source.info, source.where)
        clause += reminder_moves.silent_clause(source.info.name)
        col = source.date
        for row in conn.execute(
                f"SELECT CAST(substr({col}, 6, 2) AS INTEGER) AS m, COUNT(*) AS n FROM {source.info.name} "
                f"WHERE deleted_at IS NULL AND {col} >= ? AND {col} <= ?{clause} GROUP BY m",
                [f"{year:04d}-01-01", f"{year:04d}-12-31", *values]):
            if 1 <= (row["m"] or 0) <= 12:
                months[row["m"] - 1]["due"] += row["n"]
    for entry in done(conn, registry, date(year, 1, 1), date(year, 12, 31), only):
        months[entry.on.month - 1]["skipped" if entry.counts_as == "skipped" else "done"] += 1
    return months
