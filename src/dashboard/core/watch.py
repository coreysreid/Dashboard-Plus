"""Work out what is running low, what expires soon, how many days of supplies are on hand, and what is worth filling in."""
from __future__ import annotations

import math
import sqlite3
import string
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlencode

from dashboard.core import dates, naming, reminder_moves, schema, settings
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
    label: str = "supplies"
    rows: int = 0
    basis: str = ""  # the daily amounts the estimate assumes, e.g. "3 litres per person a day, 1 per pet"
    not_counted: float = 0  # amount that matches but is left out by `counts_only` (e.g. water for flushing)
    wrong_unit: list = field(default_factory=list)  # names of rows recorded in another unit (e.g. bottles)
    notes: list[str] = field(default_factory=list)
    items: list = field(default_factory=list)  # every SupplyRow behind the total, counted or left out (0109)
    household: Household | None = None  # the people and pets count the daily need was worked out from


def _name_column(info: TableInfo) -> str | None:
    texts = [c for c in info.table.columns.values() if c.type == "text" and not c.sensitive]
    required = [c for c in texts if c.required]
    chosen = (required or texts or [None])[0]
    return chosen.name if chosen else None


def _name(info: TableInfo, row, conn=None, registry=None, leave_out=()) -> str:
    if conn is not None and info.table.record_name:
        return naming.record_name(conn, registry, info, row, leave_out=leave_out)  # "Kidney beans, 3 tins"
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
    style = dates.household_style(conn)
    items = []
    for info in registry.values():
        rule = info.table.watch.get("expiring")
        if not rule:
            continue
        col, warn = rule["date"], rule["warn_days"]
        positive = f" AND {rule['only_positive']} > 0" if rule.get("only_positive") else ""  # used up: no warning
        clause, values = _where_sql(info, rule.get("where", {}))  # e.g. only loans still out (decision 0072)
        clause += reminder_moves.silent_clause(info.name)  # a reminder moved to another list (decision 0117)
        rows = conn.execute(f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND {col} IS NOT NULL "
                            f"AND {col} != ''{positive}{clause}", values)
        for row in rows:
            try:
                when = date.fromisoformat(row[col])
            except ValueError:
                continue
            days = (when - today).days
            if days > warn:
                continue
            detail = _due_words(rule.get("wording", "expires"), what_for(rule, row), when, days, style)
            items.append(WatchItem(info.name, row["id"], _name(info, row, conn, registry, (col,)), detail, days))
    return sorted(items, key=lambda i: (i.sort_key, i.name))


def what_for(rule: dict, row) -> str:
    """What a due date is about for this row: the first `what_when` whose filter it matches, else `what` (0117)."""
    for option in rule.get("what_when", ()):
        if all(row[k] == v for k, v in option["where"].items()):
            return option["what"]
    return rule.get("what", "")


def _where_sql(info: TableInfo, filters: dict) -> tuple[str, list]:
    """SQL for equality filters like { status = "out" }. A blank yes/no counts as no, as the form shows it."""
    clause, values = "", []
    for name, value in filters.items():
        if info.table.columns[name].type == "boolean":
            clause += f" AND COALESCE({name}, 0) = ?"
            values.append(int(value))
        else:
            clause += f" AND {name} = ?"
            values.append(value)
    return clause, values


def _due_words(wording: str, what: str, when: date, days: int, style: str = dates.DAY_FIRST) -> str:
    """How a date reads under Needs attention: "expires …" for use-by dates, "due …" for things to do."""
    plural = lambda n: f"{n} day{'s' if n != 1 else ''}"  # noqa: E731
    if wording == "due":
        if days < 0:
            words = f"overdue since {dates.show(when, style)} ({plural(-days)} ago)"
        elif days == 0:
            words = "due today"
        else:
            words = f"due {dates.show(when, style)} (in {plural(days)})"
    elif days < 0:
        words = f"expired {dates.show(when, style)} ({plural(-days)} ago)"
    elif days == 0:
        words = "expires today"
    else:
        words = f"expires {dates.show(when, style)} (in {plural(days)})"
    return f"{what} {words}" if what else words


def household(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> Household:
    """How many people and pets the household has, for days-of-cover sums."""
    pets = int(settings.get(conn, "household.pets", 0) or 0)
    if "pets__pets" in registry:  # the Pets module is switched on: count the pets recorded there
        pets = conn.execute("SELECT COUNT(*) FROM pets__pets WHERE deleted_at IS NULL").fetchone()[0]
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


@dataclass
class SupplyRow:
    """One record a `supply` rule looked at, and whether its amount was added up (the working behind Home's days)."""
    record_id: int
    name: str
    amount: float | None  # None: no amount recorded (unknown, never zero)
    unit: str | None
    answer: object  # the stored `counts_only` answer (for water: safe to drink now), None if not answered
    counted: float  # what this row adds to the total: its amount when counted, otherwise 0
    status: str  # "counted", "no_amount", "not_counted" (counts_only says no or is blank) or "wrong_unit"
    updated_at: str = ""


def supply_rows(conn: sqlite3.Connection, info: TableInfo, rule: dict) -> list[SupplyRow]:
    """Every record a supply rule looks at, each sorted into counted or left out, in one read (decision 0109)."""
    filters = rule["where"]
    clause = "".join(f" AND {name} = ?" for name in filters)
    only = rule.get("counts_only") or {}
    accepted = None
    if rule.get("unit_from"):
        # Only rows in the supply's own unit are added up; "6 bottles" is not 6 litres.
        accepted = {"", rule["unit"].lower(), rule["unit"].lower().rstrip("s"), *rule.get("unit_words", [])}
    name_column = _name_column(info) or "id"
    picked = ["id", f"{name_column} AS _name", f"{rule['quantity']} AS _amount", "updated_at"]
    if rule.get("unit_from"):
        picked.append(f"{rule['unit_from']} AS _unit")
    picked += [f"{name} AS _only_{i}" for i, name in enumerate(only)]
    rows = []
    for row in conn.execute(f"SELECT {', '.join(picked)} FROM {info.name} WHERE deleted_at IS NULL{clause} "
                            f"ORDER BY id", list(filters.values())):
        amount = None if row["_amount"] is None else float(row["_amount"])
        unit = row["_unit"] if rule.get("unit_from") else rule["unit"]
        answers = [row[f"_only_{i}"] for i in range(len(only))]
        if not all((a or 0) == int(v) for a, v in zip(answers, only.values())):
            status = "not_counted"
        elif accepted is not None and (unit or "").strip().lower() not in accepted:
            status = "wrong_unit"
        elif amount is None:
            status = "no_amount"
        else:
            status = "counted"
        rows.append(SupplyRow(row["id"], str(row["_name"]), amount, unit, answers[0] if answers else None,
                              amount if status == "counted" else 0.0, status, row["updated_at"] or ""))
    return rows


def supplies(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> list[Supply]:
    """Days of cover for every table with a `supply` rule, with the working shown."""
    home = household(conn, registry)
    results = []
    for info in registry.values():
        rule = info.table.watch.get("supply")
        if not rule:
            continue
        rows = supply_rows(conn, info, rule)
        count = len(rows)
        total = math.fsum(r.counted for r in rows)
        not_counted = math.fsum(r.amount or 0 for r in rows if r.status == "not_counted")
        wrong_unit = [f"{r.name} ({_number(r.amount or 0)} {r.unit})" for r in rows if r.status == "wrong_unit"]
        unit = rule["unit"]
        u = f" {unit}" if unit else ""
        basis = f"{_number(rule['per_person_per_day'])}{u} per person a day"
        if rule["per_pet_per_day"] and home.pets:
            basis += f", {_number(rule['per_pet_per_day'])} per pet"
        title = info.module.labels.get("tables", {}).get(info.table.name, {}).get("title") or info.table.title
        if home.people is None:
            results.append(Supply(info.name, title, unit, total, 0, None, rule["target_days"], 0,
                                  "Tell the program how many people live here to work out days of cover.",
                                  needs_household=True, rows=count, label=rule["label"], basis=basis,
                                  not_counted=not_counted, wrong_unit=wrong_unit, items=rows, household=home))
            continue
        need = home.people * rule["per_person_per_day"] + home.pets * rule["per_pet_per_day"]
        target = rule["target_days"]
        who = f"{home.people} {'person' if home.people == 1 else 'people'}"
        if home.pets and rule["per_pet_per_day"]:
            who += f" and {home.pets} pet{'s' if home.pets != 1 else ''}"
        if need <= 0:
            results.append(Supply(info.name, title, unit, total, 0, None, target, 0,
                                  "The daily need works out as zero, so days of cover cannot be calculated.", rows=count,
                                  label=rule["label"], basis=basis, not_counted=not_counted, wrong_unit=wrong_unit,
                                  items=rows, household=home))
            continue
        days = total / need
        shortfall = max(0.0, target * need - total)
        working = (f"{_number(total)}{u} on hand ÷ {_number(need)}{u} a day for {who} "
                   f"= about {_number(round(days, 1))} days (aim: {_number(target)} days).")
        notes = ["The daily figures are a starting point. Your local authority's advice comes first."]
        if wrong_unit:
            notes.insert(0, f"Not counted until its total is entered in {unit}: {', '.join(wrong_unit)}.")
        if not_counted:
            notes.insert(0, f"Not counted: {_number(not_counted)}{u} not marked as {rule['label']} "
                            f"(for example water for washing or flushing).")
        results.append(Supply(info.name, title, unit, total, need, days, target, shortfall, working,
                              rows=count, notes=notes, label=rule["label"], basis=basis, not_counted=not_counted,
                              wrong_unit=wrong_unit, items=rows, household=home))
    return results


@dataclass
class Gap:
    """A detail worth filling in, asked as a question, with where to fill it in."""
    table: str
    record_id: int | None
    message: str
    fix: str  # the page where the detail can be added


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _filter_value(value):
    return int(value) if isinstance(value, bool) else value


def _show(info: TableInfo, registry: dict[str, TableInfo], conn: sqlite3.Connection, column: str, value) -> str:
    """A value as a person would read it inside a gap message."""
    col = info.table.columns[column]
    if _blank(value):
        return "(not filled in)"
    if col.type == "choice":
        return next((c.label for c in col.choices if c.key == value), str(value))
    if col.type == "boolean":
        return "yes" if int(value) else "no"
    if col.type == "link":
        target = registry.get(schema.target_table(info.module.name, col))
        row = conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (value,)).fetchone() if target else None
        if target is None:
            return "(in another list)"  # a part this reader may not see: never its name (decision 0067)
        return _name(target, row) if row is not None else "(deleted)"
    if col.type in ("integer", "decimal", "measure"):
        return _number(value)
    return str(value)


def gaps(conn: sqlite3.Connection, registry: dict[str, TableInfo]) -> list[Gap]:
    """Details worth filling in, from every table's `gaps` rules, in the order they are declared."""
    found = []
    for info in registry.values():
        for rule in info.table.watch.get("gaps", []):
            if "none" in rule:
                filters = rule["none"]
                clause = "".join(f" AND {name} = ?" for name in filters)
                exists = conn.execute(f"SELECT 1 FROM {info.name} WHERE deleted_at IS NULL{clause} LIMIT 1",
                                      [_filter_value(v) for v in filters.values()]).fetchone()
                if not exists:
                    prefill = urlencode({k: ("yes" if v is True else "" if v is False else v) for k, v in filters.items()})
                    found.append(Gap(info.name, None, rule["message"],
                                     f"/t/{info.name}/new" + (f"?{prefill}" if prefill else "")))
                continue
            filters = rule["where"]
            clause = "".join(f" AND {name} = ?" for name in filters)
            rows = conn.execute(f"SELECT * FROM {info.name} WHERE deleted_at IS NULL{clause} ORDER BY id",
                                [_filter_value(v) for v in filters.values()]).fetchall()
            link, _, field_name = rule["missing"].rpartition(".")
            target = None
            if link:
                target = registry.get(schema.target_table(info.module.name, info.table.columns[link]))
                if target is None:
                    continue
            elif info.table.columns[field_name].type in ("link", "links") and schema.target_table(
                    info.module.name, info.table.columns[field_name]) not in registry:
                continue  # a link into a list this reader may not see: even whether it is filled in stays hidden
            seen: set[str] = set()
            for row in rows:
                if target is None:
                    if _blank(row[field_name]):
                        found.append(Gap(info.name, row["id"], _message(info, registry, conn, rule, row),
                                         f"/t/{info.name}/{row['id']}"))
                    continue
                if row[link] is None:
                    continue
                linked = conn.execute(f"SELECT * FROM {target.name} WHERE id = ? AND deleted_at IS NULL",
                                      (row[link],)).fetchone()
                fix = f"/t/{target.name}/{row[link]}"
                if linked is not None and _blank(linked[field_name]) and fix not in seen:
                    seen.add(fix)  # one question per person, even if they have several roles
                    found.append(Gap(info.name, row["id"], _message(info, registry, conn, rule, row),
                                     fix))
    return found


def _message(info, registry, conn, rule, row) -> str:
    names = {f for _, f, _, _ in string.Formatter().parse(rule["message"]) if f}
    fields = {name: _show(info, registry, conn, name, row[name]) for name in names}
    return rule["message"].format(**fields)
