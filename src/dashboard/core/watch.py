"""Work out what is running low, what expires soon, and how many days of supplies are on hand."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date

from dashboard.core import settings
from dashboard.core.records import TableInfo

PEOPLE_TABLE = "people__people"


@dataclass
class WatchItem:
    """One record that needs attention."""
    table: str
    record_id: int
    name: str
    detail: str
    sort_key: float


@dataclass
class Household:
    people: int | None
    pets: int
    source: str  # where the people count came from, in plain words


@dataclass
class Supply:
    """Days of cover for one supply (for example water)."""
    table: str
    title: str
    unit: str
    total: float
    daily_need: float
    days: float | None
    target_days: float
    shortfall: float
    working: str
    needs_household: bool = False
    rows: int = 0
    notes: list[str] = field(default_factory=list)


def _name_column(info: TableInfo) -> str | None:
    texts = [c for c in info.table.columns.values() if c.type == "text"]
    required = [c for c in texts if c.required]
    chosen = (required or texts or [None])[0]
    return chosen.name if chosen else None


def _name(info: TableInfo, row) -> str:
    column = _name_column(info)
    value = row[column] if column else None
    return str(value) if value not in (None, "") else f"{info.table.title} #{row['id']}"


def _number(value) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def running_low(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> list[WatchItem]:
    """Records whose quantity is below their minimum, biggest shortfall first."""
    items = []
    for info in registry.values():
        rule = info.table.watch.get("running_low")
        if not rule:
            continue
        q, m = rule["quantity"], rule["minimum"]
        unit = info.table.columns[q].unit or ""
        rows = conn.execute(
            f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND {m} IS NOT NULL "
            f"AND COALESCE({q}, 0) < {m}")
        for row in rows:
            have, want = row[q] or 0, row[m]
            items.append(WatchItem(info.name, row["id"], _name(info, row),
                                   f"{_number(have)} left, keep at least {_number(want)}{' ' + unit if unit else ''}",
                                   -(want - have)))
    return sorted(items, key=lambda i: (i.sort_key, i.name))


def expiring(conn: sqlite3.Connection, registry: dict[str, TableInfo], today: date | None = None) -> list[WatchItem]:
    """Records whose date is past or within the warning window, soonest first."""
    today = today or date.today()
    items = []
    for info in registry.values():
        rule = info.table.watch.get("expiring")
        if not rule:
            continue
        col, warn = rule["date"], rule["warn_days"]
        rows = conn.execute(f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND {col} IS NOT NULL "
                            f"AND {col} != ''")
        for row in rows:
            try:
                when = date.fromisoformat(row[col])
            except ValueError:
                continue
            days = (when - today).days
            if days > warn:
                continue
            if days < 0:
                detail = f"expired {when.isoformat()} ({-days} day{'s' if days != -1 else ''} ago)"
            elif days == 0:
                detail = "expires today"
            else:
                detail = f"expires {when.isoformat()} (in {days} day{'s' if days != 1 else ''})"
            items.append(WatchItem(info.name, row["id"], _name(info, row), detail, days))
    return sorted(items, key=lambda i: (i.sort_key, i.name))


def household(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> Household:
    """How many people and pets the household has, for days-of-cover sums."""
    pets = int(settings.get(conn, "household.pets", 0) or 0)
    info = registry.get(PEOPLE_TABLE)
    if info and "lives_here" in info.table.columns:
        count = conn.execute(f"SELECT COUNT(*) FROM {PEOPLE_TABLE} WHERE deleted_at IS NULL AND lives_here = 1"
                             ).fetchone()[0]
        if count:
            return Household(count, pets, "people marked as living here")
    people = settings.get(conn, "household.people")
    if people:
        return Household(int(people), pets, "the household size from setup")
    return Household(None, pets, "not set yet")


def supplies(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> list[Supply]:
    """Days of cover for every table with a `supply` rule, with the working shown."""
    home = household(conn, registry)
    results = []
    for info in registry.values():
        rule = info.table.watch.get("supply")
        if not rule:
            continue
        filters = rule["where"]
        clause = "".join(f" AND {name} = ?" for name in filters)
        row = conn.execute(f"SELECT COALESCE(SUM({rule['quantity']}), 0) AS total, COUNT(*) AS n FROM {info.name} "
                           f"WHERE deleted_at IS NULL{clause}", list(filters.values())).fetchone()
        total, count = float(row["total"]), row["n"]
        unit = rule["unit"]
        title = info.module.labels.get("tables", {}).get(info.table.name, {}).get("title") or info.table.title
        if home.people is None:
            results.append(Supply(info.name, title, unit, total, 0, None, rule["target_days"], 0,
                                  "Tell the program how many people live here to work out days of cover.",
                                  needs_household=True, rows=count))
            continue
        need = home.people * rule["per_person_per_day"] + home.pets * rule["per_pet_per_day"]
        target = rule["target_days"]
        u = f" {unit}" if unit else ""
        who = f"{home.people} {'person' if home.people == 1 else 'people'}"
        if home.pets and rule["per_pet_per_day"]:
            who += f" and {home.pets} pet{'s' if home.pets != 1 else ''}"
        if need <= 0:
            results.append(Supply(info.name, title, unit, total, 0, None, target, 0,
                                  "The daily need works out as zero, so days of cover cannot be calculated.", rows=count))
            continue
        days = total / need
        shortfall = max(0.0, target * need - total)
        working = (f"{_number(total)}{u} on hand ÷ {_number(need)}{u} a day for {who} "
                   f"= about {_number(round(days, 1))} days (aim: {_number(target)} days).")
        notes = ["The daily figures are a starting point. Your local authority's advice comes first."]
        results.append(Supply(info.name, title, unit, total, need, days, target, shortfall, working,
                              rows=count, notes=notes))
    return results
