"""Month calendars from a table's dated or timed records by the household's own day; an empty day is never called missed (decision 0119), earlier done days read from history (0129, corrected by 0132)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta, tzinfo

from dashboard.core import checklist, daily, calendars_corrections, reminder_moves, watch
from dashboard.core.schema import target_table

# The fixed looks, in the order the legend and each day list them. Each has a colour (base.html, .cal-<look>),
# a symbol and, for some, a pattern or a dashed edge, so no state is told apart by colour alone.
LOOKS = ("done", "recorded", "skipped", "due", "planned")
SYMBOLS = {"done": "✓", "recorded": "●", "skipped": "–", "due": "○", "planned": "◇"}
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass
class Mark:
    """One thing on one day: a saved record (`record_id` in the calendar's table) or a linked record's open
    due date (`kind == "due"`). `subject_id` is the record it belongs to, such as the pet or the routine."""
    look: str
    kind: str  # "entry" or "due"
    record_id: int
    subject_id: int
    state: str | None = None  # the record's choice in the calendar's `state` column, such as "done"
    moment: object = None  # the household's clock time, for an entry with a date and time
    day: date | None = None  # the household's day it is on
    earlier: bool = False  # a done day read from the record's history, not the date it keeps now (decision 0129)


@dataclass
class Day:
    day: date
    in_month: bool
    marks: list[Mark] = field(default_factory=list)

    def counts(self) -> list[tuple[str, int]]:
        """How many marks of each look, in the legend's order."""
        found = {}
        for mark in self.marks:
            found[mark.look] = found.get(mark.look, 0) + 1
        return [(look, found[look]) for look in LOOKS if look in found]


@dataclass
class Month:
    year: int
    month: int
    weeks: list[list[Day]]
    today: date

    @property
    def days(self) -> list[Day]:
        return [d for week in self.weeks for d in week if d.in_month]

    def totals(self) -> dict[str, int]:
        found: dict[str, int] = {}
        for day in self.days:
            for look, n in day.counts():
                found[look] = found.get(look, 0) + n
        return found


def own(info) -> bool:
    """Whether a calendar is of its table's own records (no `per`, decision 0122), like Garden jobs or Bills."""
    return bool(info.table.calendar) and not info.table.calendar.get("per")


def calendar_tables(registry: dict, subject=None) -> list:
    """Tables that declare `calendar` and whose `per` table is switched on, or only those pointing at `subject`.
    A calendar of a table's own records (decision 0122) is never a panel on one of them, so `subject` leaves it out."""
    found = []
    for info in registry.values():
        rule = info.table.calendar
        if not rule:
            continue
        if own(info):
            if subject is None:
                found.append(info)
            continue
        target = target_table(info.module.name, info.table.columns[rule["per"]])
        if target in registry and (subject is None or target == subject.name):
            found.append(info)
    return found


def subject_table(registry: dict, info):
    """The table each mark belongs to: the `per` table, or the calendar's own table when it has no `per`."""
    if own(info):
        return info
    return registry[target_table(info.module.name, info.table.columns[info.table.calendar["per"]])]


def weekday_order(first_day: str) -> list[int]:
    """Weekday numbers (Monday is 0) in the household's order, starting on its chosen first day."""
    start = WEEKDAYS.index(first_day) if first_day in WEEKDAYS else 0
    return [(start + i) % 7 for i in range(7)]


def grid(year: int, month: int, first_day: str) -> list[list[date | None]]:
    """The month's days in whole weeks starting on the household's first day; None fills the edges."""
    first = date(year, month, 1)
    after = date(year + (month == 12), month % 12 + 1, 1)
    order = weekday_order(first_day)
    lead = order.index(first.weekday())
    cells: list[date | None] = [None] * lead
    current = first
    while current < after:
        cells.append(current)
        current += timedelta(days=1)
    cells += [None] * (-len(cells) % 7)
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


def shift(year: int, month: int, by: int) -> tuple[int, int]:
    """The month `by` months away: (2026, 1) and -1 give (2025, 12)."""
    index = year * 12 + month - 1 + by
    return index // 12, index % 12 + 1


def _entries(conn: sqlite3.Connection, registry: dict, info, start: date, end: date, zone: tzinfo | None,
             subject: int | None) -> list[Mark]:
    """Accepted, undeleted records whose household day is from `start` to `end`. A time with an offset counts on
    the household's day it happened; a time typed without one is already the household's clock (decision 0110)."""
    rule = info.table.calendar
    if not rule.get("when"):
        return []  # a calendar of a table's own records with no date column: its presses are read from history
    if rule.get("history"):  # also each earlier done day, from the record's own history (decision 0129)
        return [Mark(rule["look"], "entry", d.record_id, d.record_id, day=d.day, earlier=d.kind != "now")
                for d in done_days(conn, registry, info, rule["when"], start, end)
                if subject is None or d.record_id == subject]
    when = info.table.columns[rule["when"]]
    state = rule.get("state")
    per = rule.get("per") or "id"  # a table's own records each belong to themselves (decision 0122)
    low, high = start.isoformat(), (end + timedelta(days=1)).isoformat()
    if when.type == "datetime":  # wide enough for any offset, then checked exactly
        low, high = (start - timedelta(days=1)).isoformat(), (end + timedelta(days=2)).isoformat()
    clause, params = "", [low, high]
    if subject is not None:
        clause, params = f" AND {per} = ?", params + [subject]
    rows = conn.execute(
        f"SELECT id, {rule['when']} AS at, {per} AS subject" + (f", {state} AS state" if state else "") +
        f" FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed' AND {rule['when']} >= ? "
        f"AND {rule['when']} < ?{clause} ORDER BY {rule['when']}, id", params).fetchall()
    found = []
    for row in rows:
        try:
            moment = daily.local(row["at"], zone) if when.type == "datetime" else None
            day = moment.date() if moment is not None else date.fromisoformat(str(row["at"])[:10])
        except (TypeError, ValueError):
            continue
        if not start <= day <= end or row["subject"] is None:
            continue
        value = row["state"] if state else None
        look = rule["looks"].get(value, "recorded") if state else rule["look"]
        found.append(Mark(look, "entry", row["id"], row["subject"], value, moment, day))
    found.sort(key=lambda m: (m.day, m.moment.isoformat() if m.moment else "", m.record_id))
    return found


def _due(conn: sqlite3.Connection, registry: dict, info, start: date, end: date, today: date,
         subject: int | None) -> list[Mark]:
    """Each linked record's one open due date in the range, from the same reminder Things to do reads (with its
    `where`, so a paused routine is left out). It is shown once, on its own date: "due" up to today, "planned"
    after. Earlier repeats are never filled in, and the days between are never marked."""
    if not info.table.calendar.get("due"):
        return []
    target = subject_table(registry, info)
    rule = target.table.watch.get("expiring") or {}
    if not rule:
        return []
    clause, params = watch._where_sql(target, rule.get("where") or {})
    clause += reminder_moves.silent_clause(target.name)  # moved to another list: shown there only (decision 0117)
    if subject is not None:
        clause, params = clause + " AND id = ?", params + [subject]
    found = []
    for row in conn.execute(f"SELECT id, {rule['date']} AS due FROM {target.name} WHERE deleted_at IS NULL "
                            f"AND review_status = 'confirmed' AND {rule['date']} >= ? AND {rule['date']} <= ?"
                            f"{clause} ORDER BY {rule['date']}, id", [start.isoformat(), end.isoformat(), *params]):
        try:
            day = date.fromisoformat(str(row["due"])[:10])
        except ValueError:
            continue
        found.append(Mark("due" if day <= today else "planned", "due", row["id"], row["id"], day=day))
    return found


def _presses(conn: sqlite3.Connection, registry: dict, info, start: date, end: date,
             subject: int | None) -> list[Mark]:
    """For a calendar of a table's own records with no `when` column (decision 0122): each Mark done (or Skip)
    saved in history for them, on the day it was dated, read the way Things to do reads it, so an undone press or
    a deleted record is left out (decisions 0091 and 0112)."""
    if not own(info) or info.table.calendar.get("when"):
        return []
    found = [Mark("skipped" if d.counts_as == "skipped" else info.table.calendar["look"], "entry", d.record_id,
                  d.record_id, day=d.on)
             for d in checklist.done(conn, registry, start, end, only=info.name)
             if subject is None or d.record_id == subject]
    found.sort(key=lambda m: (m.day, m.record_id))
    return found


def month(conn: sqlite3.Connection, registry: dict, info, year: int, month_: int, today: date, first_day: str,
          subject: int | None = None) -> Month:
    """One month of marks, read fresh: nothing is stored by the calendar, so an edit, delete or restore shows at
    once. `subject` keeps one record's marks only (one pet, one routine)."""
    weeks = grid(year, month_, first_day)
    first = date(year, month_, 1)
    last = date(*shift(year, month_, 1), 1) - timedelta(days=1)
    zone = daily.household_zone(conn)
    by_day: dict[date, list[Mark]] = {}
    for mark in (_entries(conn, registry, info, first, last, zone, subject)
                 + _presses(conn, registry, info, first, last, subject)
                 + _due(conn, registry, info, first, last, today, subject)):
        by_day.setdefault(mark.day, []).append(mark)
    return Month(year, month_, [[Day(d, True, by_day.get(d, [])) if d else Day(None, False) for d in week]
                                for week in weeks], today)


# ----- earlier done days from a record's own history (decision 0129) ------------------------------------


@dataclass(frozen=True)
class DoneDay:
    """One day a record was done: `kind` is "now" (the date it keeps), "earlier" (a date it kept before and then
    moved on from to a later day) or "press" (a Mark done press saved before the table kept the date)."""
    record_id: int
    day: date
    kind: str


def _as_day(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value not in (None, "") else None
    except ValueError:
        return None


def _history(conn: sqlite3.Connection, info, column: str, zone: tzinfo | None
             ) -> tuple[dict[int, set[date]], dict[str, tuple[int, date]]]:
    """One pass over a table's history, in the order it was saved. Returns, for each record, the earlier dates
    `column` held (see `earlier_done`), and each dateless press (a one-step Mark done that did not set `column`)
    that a date typed afterwards belongs to, by its operation (decision 0132).

    A press and the date typed after it are one completion when the date is the first one saved after the press,
    while every field the press set still holds the value the press gave it (the job still shows done), and before
    any other press of that record. A field the press set changed on the way (the job ticked not done again) starts
    a new round, so a date typed then is its own completion and the press keeps its own day."""
    values: dict[int, list[list]] = {}  # per record: [the date it held, the day it was saved, cleared by an Undo]
    last: dict[int, int | None] = {}  # the value the record's previous history entry saved, if it saved one
    waiting: dict[int, tuple[str, dict]] = {}  # a dateless press per record, until its date is typed
    belongs: dict[str, tuple[int, date]] = {}
    for row in conn.execute("SELECT record_id, at, action, after FROM core__audit WHERE table_name = ? "
                            "AND action IN ('create', 'update', 'action', 'undo') ORDER BY id", (info.name,)):
        record_id, action = row["record_id"], row["action"]
        try:
            after = json.loads(row["after"]) if row["after"] else {}
        except ValueError:
            after = {}
        after = after if isinstance(after, dict) else {}
        saved_value = None
        if action in ("create", "update"):
            if column in after:
                try:
                    saved = daily.local_day(row["at"], zone)
                except (TypeError, ValueError):
                    saved = None
                if saved is not None:
                    values.setdefault(record_id, []).append([_as_day(after[column]), saved, False])
                    saved_value = len(values[record_id]) - 1
            press = waiting.get(record_id)
            if press is not None:
                if any(k in after and after[k] != v for k, v in press[1].items()):
                    del waiting[record_id]  # a new round: the press and a later date are two completions
                elif _as_day(after.get(column)) is not None:
                    belongs[press[0]] = (record_id, _as_day(after[column]))
                    del waiting[record_id]
        elif action == "undo":
            if last.get(record_id) is not None:  # Undo put the field back just before this line: never a done day
                values[record_id][last[record_id]][2] = True
            if record_id in waiting and waiting[record_id][0] == after.get("operation"):
                del waiting[record_id]
        else:  # a press
            fields = after.get("after") if isinstance(after.get("after"), dict) else {}
            if after.get("one_step") and column not in fields and after.get("operation"):
                waiting[record_id] = (after["operation"], fields)
            else:
                waiting.pop(record_id, None)
        last[record_id] = saved_value
    earlier: dict[int, set[date]] = {}
    for record_id, held in values.items():
        for (before, saved, _), (after, moved, by_undo) in zip(held, held[1:]):
            if before is None or moved <= saved:
                continue  # nothing was there, or it was changed again the same day it was typed
            if (after is None and not by_undo) or (after is not None and after > before):
                earlier.setdefault(record_id, set()).add(before)
    return earlier, belongs


def earlier_done(conn: sqlite3.Connection, info, column: str, zone: tzinfo | None) -> dict[int, set[date]]:
    """For each record, the dates `column` held before it was moved on, read from history in the order they were
    saved. A date counts only when it stood until a later household day than the day it was saved, and then was
    moved to a later date (decision 0129) or cleared by hand (decision 0132: a thing lent again, a job needing doing
    again). So a date typed back (a correction), a date changed or cleared again the same day it was typed (a slip
    fixed at once) and a date cleared by Undo never count: they may have been mistakes."""
    return _history(conn, info, column, zone)[0]


def done_days(conn: sqlite3.Connection, registry: dict, info, column: str, start: date, end: date) -> list[DoneDay]:
    """Every day from `start` to `end` that an accepted, undeleted record of `info` was done: the date `column`
    keeps now, each earlier date it was moved on from (see `earlier_done`), and each Mark done press that did not
    set `column` itself (pressed before the table kept the date), read the way Things to do reads presses, so an
    undone press is left out. A press whose date was typed afterwards counts once, on that date (see `_history`).
    A day from history the household took off the calendar ("Not a done day", decision 0132) is left out until it
    is put back; the date a record keeps now is never left out. One record counts once a day. Nothing is stored,
    so an edit, delete or restore shows at once."""
    live = {row["id"]: _as_day(row["value"]) for row in conn.execute(
        f"SELECT id, {column} AS value FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed'")}
    found: dict[tuple[int, date], str] = {}
    for record_id, day in live.items():
        if day is not None:
            found[(record_id, day)] = "now"
    earlier, belongs = _history(conn, info, column, daily.household_zone(conn))
    for record_id, before in earlier.items():
        if record_id in live:
            for day in before:
                found.setdefault((record_id, day), "earlier")
    if info.table.actions:
        for press in checklist.done(conn, registry, start, end, only=info.name):
            if press.record_id in live and press.counts_as == "done" and column not in press.fields \
                    and belongs.get(press.operation) not in found:
                found.setdefault((press.record_id, press.on), "press")
    taken_off = calendars_corrections.removed(conn, info.name)
    return sorted((DoneDay(r, d, k) for (r, d), k in found.items()
                   if start <= d <= end and (k == "now" or (r, d) not in taken_off)),
                  key=lambda d: (d.day, d.record_id))
