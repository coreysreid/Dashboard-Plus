"""Bars over time: how often, or how much in one unit, per day, week or month by the household's own day; an empty period is never called missed (decision 0124)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta, tzinfo
from decimal import Decimal

from dashboard.core import calendars, daily

PERIODS = ("day", "week", "month")
# How many periods one chart shows: two weeks of days, about a quarter of weeks, a year of months. Earlier and
# Later move by the same number, so a chart never grows too tall to read on a phone.
SPAN = {"day": 14, "week": 12, "month": 12}


@dataclass
class Period:
    """One bar's period, from `start` to `end` (both included), and the accepted records in it."""
    start: date
    end: date
    entries: list[dict] = field(default_factory=list)
    so_far: bool = False  # the period has not finished yet: it includes today

    @property
    def count(self) -> int:
        return len(self.entries)


@dataclass
class Amounts:
    """One period's amounts in one unit: the total, how many entries it adds, how many have no amount, and the
    other units seen there (never converted or added in)."""
    total: Decimal = Decimal(0)
    added: int = 0
    unmeasured: int = 0
    others: dict[str, Decimal] = field(default_factory=dict)


def period_start(day: date, by: str, first_day: str) -> date:
    """The first day of the day, week (on the household's first weekday) or month that `day` is in."""
    if by == "day":
        return day
    if by == "week":
        first = calendars.weekday_order(first_day)[0]
        return day - timedelta(days=(day.weekday() - first) % 7)
    return day.replace(day=1)


def period_end(start: date, by: str) -> date:
    if by == "day":
        return start
    if by == "week":
        return start + timedelta(days=6)
    year, month = calendars.shift(start.year, start.month, 1)
    return date(year, month, 1) - timedelta(days=1)


def periods(by: str, last_day: date, first_day: str, today: date) -> list[Period]:
    """`SPAN[by]` periods in time order, the last one holding `last_day`; a period holding today is "so far"."""
    found = []
    start = period_start(last_day, by, first_day)
    for _ in range(SPAN[by]):
        found.append(Period(start, period_end(start, by), so_far=start <= today <= period_end(start, by)))
        start = period_start(start - timedelta(days=1), by, first_day)
    return found[::-1]


def entries(conn: sqlite3.Connection, info, rule: dict, subject_id: int, start: date, end: date,
            zone: tzinfo | None, group_id: int | None = None) -> list[dict]:
    """Accepted, undeleted records of one subject whose household day is from `start` to `end`, matching the
    rule's `where` choices (and one `group` record when given). A time with an offset counts on the household's
    day it happened; a time typed without one is already the household's clock (decision 0110). Each row gains
    `_day`. Nothing is stored, so an edit, delete or restore shows at once."""
    when = info.table.columns[rule["when"]]
    low, high = start.isoformat(), (end + timedelta(days=1)).isoformat()
    if when.type == "datetime":  # wide enough for any offset, then checked exactly
        low, high = (start - timedelta(days=1)).isoformat(), (end + timedelta(days=2)).isoformat()
    clause, params = f" AND {rule['per']} = ?", [low, high, subject_id]
    for column, value in (rule.get("where") or {}).items():
        clause, params = clause + f" AND {column} = ?", params + [value]
    if group_id is not None:
        clause, params = clause + f" AND {rule['group']} = ?", params + [group_id]
    rows = conn.execute(
        f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed' AND {rule['when']} >= ? "
        f"AND {rule['when']} < ?{clause} ORDER BY {rule['when']}, id", params).fetchall()
    found = []
    for row in rows:
        entry = dict(row)
        try:
            moment = daily.local(entry[rule["when"]], zone) if when.type == "datetime" else None
            day = moment.date() if moment is not None else date.fromisoformat(str(entry[rule["when"]])[:10])
        except (TypeError, ValueError):
            continue
        if start <= day <= end:
            entry["_day"], entry["_local"] = day, moment
            found.append(entry)
    found.sort(key=lambda e: (e["_day"], e["_local"].isoformat() if e["_local"] else "", e["id"]))
    return found


def build(conn: sqlite3.Connection, info, rule: dict, subject_id: int, by: str, last_day: date, first_day: str,
          today: date, group_id: int | None = None) -> list[Period]:
    """The periods of one chart with their records, read fresh in one query."""
    found = periods(by, last_day, first_day, today)
    rows = entries(conn, info, rule, subject_id, found[0].start, found[-1].end, daily.household_zone(conn), group_id)
    for entry in rows:
        for period in found:
            if period.start <= entry["_day"] <= period.end:
                period.entries.append(entry)
                break
    return found


def unit_of(rule: dict, entry: dict) -> str:
    """An entry's unit: its own unit column, or the amount column's one fixed unit."""
    if rule.get("unit"):
        return str(entry.get(rule["unit"]) or "").strip()
    return rule.get("fixed_unit") or ""


def units(rule: dict, found: list[Period]) -> list[str]:
    """Every unit with an amount in these periods, the latest entry's unit first: a chart shows one at a time."""
    seen: list[str] = []
    for period in reversed(found):
        for entry in reversed(period.entries):  # in the household's time order
            unit = unit_of(rule, entry)
            if entry.get(rule["amount"]) is not None and unit and unit not in seen:
                seen.append(unit)
    return seen


def amounts(rule: dict, period: Period, unit: str) -> Amounts:
    """One period's amounts added up in `unit` only. An entry with no amount is counted, never read as zero; an
    amount in another unit is kept apart, never converted (decisions 0110 and 0111)."""
    result = Amounts()
    for entry in period.entries:
        value, its_unit = entry.get(rule["amount"]), unit_of(rule, entry)
        if value is None or not its_unit:
            result.unmeasured += 1
        elif its_unit == unit:
            result.total += Decimal(str(value))
            result.added += 1
        else:
            result.others[its_unit] = result.others.get(its_unit, Decimal(0)) + Decimal(str(value))
    return result
