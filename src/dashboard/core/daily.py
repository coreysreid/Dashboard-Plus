"""Daily totals by the household's own day: accepted entries only, amounts added only in matching units (decision 0110)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dashboard.core import settings

ZONE_KEY = "household.timezone"  # the household's time zone, saved from the browser in setup and Settings
UNPLURAL = ("g", "kg", "mg", "ml", "l", "oz", "lb")  # short units read the same for any amount


def household_zone(conn: sqlite3.Connection) -> tzinfo | None:
    """The household's time zone from its setting, or None to mean this computer's own clock and rules."""
    name = settings.get(conn, ZONE_KEY)
    if isinstance(name, str) and name.strip():
        try:
            return ZoneInfo(name.strip())
        except (ZoneInfoNotFoundError, ValueError, OSError):
            return None
    return None


def local(value, zone: tzinfo | None) -> datetime:
    """A stored date and time as the household's own clock read it, without a zone.

    A value saved without an offset (typed on a form, in the household's local time) is already that.
    A value with an offset (sent by a helper or another device) is an instant, moved into the household's zone,
    so it keeps its true moment and counts on the household's day it happened."""
    when = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if when.tzinfo is None:
        return when
    return (when.astimezone(zone) if zone is not None else when.astimezone()).replace(tzinfo=None)


def local_day(value, zone: tzinfo | None) -> str:
    """The household's day an entry belongs to, as 2026-11-20."""
    return local(value, zone).date().isoformat()


def today(conn: sqlite3.Connection, now: datetime | None = None) -> date:
    """The household's date now (by its time zone setting, or this computer's clock)."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.astimezone()
    return local(moment, household_zone(conn)).date()


def now_text(conn: sqlite3.Connection, now: datetime | None = None) -> str:
    """The household's local time now, as a form fills it in: 2026-11-20T07:15."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.astimezone()
    return local(moment, household_zone(conn)).isoformat(timespec="minutes")


def amount_words(amount, unit: str) -> str:
    """"120 g", "1 pouch", "2 pouches", "1.5 scoops"."""
    number = Decimal(str(amount)).normalize()
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    word = (unit or "").strip()
    if number != 1 and word and word.lower() not in UNPLURAL and not word.endswith("s"):
        word += "es" if word.endswith(("ch", "sh", "x")) else "s"
    return f"{text} {word}".strip()


@dataclass
class Day:
    """One subject's accepted entries on one household day, with totals by unit and the entries with no amount."""
    day: str
    entries: list[dict] = field(default_factory=list)
    totals: list[tuple[Decimal, str]] = field(default_factory=list)  # in the order each unit first appears
    unmeasured: int = 0


def _window(start: str, end: str) -> tuple[str, str]:
    """Stored text bounds wide enough for any offset: a day either side, filtered exactly afterwards."""
    return ((date.fromisoformat(start) - timedelta(days=1)).isoformat(),
            (date.fromisoformat(end) + timedelta(days=2)).isoformat())


def entries(conn: sqlite3.Connection, info, subject_id: int, start: str, end: str,
            zone: tzinfo | None) -> list[dict]:
    """Accepted, undeleted entries for one subject whose household day is from `start` to `end` (inclusive),
    in time order. Each row gains `_local` (the household's clock) and `_day`. Suggestions still waiting on
    Review are never here: they are not records until a person accepts them."""
    rule = info.table.daily
    low, high = _window(start, end)
    rows = conn.execute(
        f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed' AND {rule['per']} = ? "
        f"AND {rule['when']} >= ? AND {rule['when']} < ? ORDER BY {rule['when']}, id",
        (subject_id, low, high)).fetchall()
    found = []
    for row in rows:
        entry = dict(row)
        try:
            entry["_local"] = local(entry[rule["when"]], zone)
        except (TypeError, ValueError):
            continue
        entry["_day"] = entry["_local"].date().isoformat()
        if start <= entry["_day"] <= end:
            found.append(entry)
    found.sort(key=lambda e: (e["_local"], e["id"]))
    return found


def add_up(rule: dict, day: str, rows: list[dict]) -> Day:
    """Totals for one day's entries: one per unit (never across units) and a count of entries with no amount."""
    result = Day(day, list(rows))
    sums: dict[str, Decimal] = {}
    for row in rows:
        amount, unit = row.get(rule["amount"]), (row.get(rule["unit"]) or "").strip()
        if amount is None or not unit:
            result.unmeasured += 1
            continue
        sums[unit] = sums.get(unit, Decimal(0)) + Decimal(str(amount))
    result.totals = [(value, unit) for unit, value in sums.items()]
    return result


def days(conn: sqlite3.Connection, info, subject_id: int, start: str, end: str, zone: tzinfo | None) -> list[Day]:
    """Every household day from `start` to `end`, each with its entries and totals (an empty day stays empty)."""
    by_day: dict[str, list[dict]] = {}
    for entry in entries(conn, info, subject_id, start, end, zone):
        by_day.setdefault(entry["_day"], []).append(entry)
    found, current, last = [], date.fromisoformat(start), date.fromisoformat(end)
    while current <= last:
        key = current.isoformat()
        found.append(add_up(info.table.daily, key, by_day.get(key, [])))
        current += timedelta(days=1)
    return found


def count(conn: sqlite3.Connection, info, subject_id: int, start: str, end: str, zone: tzinfo | None) -> int:
    """How many accepted entries fall in the range: read before building a sheet, so it is complete or refused."""
    return len(entries(conn, info, subject_id, start, end, zone))


def totals_words(rule: dict, result: Day) -> str:
    """"240 g put out", "120 g and 1 pouch put out": separate totals for each unit, never one sum."""
    parts = [amount_words(value, unit) for value, unit in result.totals]
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{joined} {rule['verb']}"


def summary(rule: dict, result: Day, when: str = "today") -> str:
    """The plain sentence for one day. It sums saved entries; it never says what was eaten, or that a meal was missed.

    "Recorded today: 240 g put out", "Recorded today: 120 g and 1 pouch put out; 1 feeding has no amount",
    "2 feedings recorded; amounts not measured", "No feeding entry recorded today"."""
    one, many = rule["entry"]
    n = len(result.entries)
    if not n:
        return f"No {one} entry recorded {when}"
    if not result.totals:
        return (f"1 {one} recorded {when}; amount not measured" if n == 1 else
                f"{n} {many} recorded {when}; amounts not measured")
    text = f"Recorded {when}: {totals_words(rule, result)}"
    if result.unmeasured:
        text += (f"; 1 {one} has no amount" if result.unmeasured == 1 else
                 f"; {result.unmeasured} {many} have no amount")
    return text


def waiting(conn: sqlite3.Connection, info, subject_id: int) -> int:
    """Suggestions for this subject still waiting on Review: shown apart, never added to a total."""
    rule = info.table.daily
    count_ = 0
    for (values_json,) in conn.execute("SELECT values_json FROM core__proposals WHERE status = 'pending' "
                                       "AND entry_kind = 'record' AND table_name = ?", (info.name,)):
        try:
            if int(json.loads(values_json).get(rule["per"])) == subject_id:
                count_ += 1
        except (TypeError, ValueError, AttributeError):
            continue
    return count_


def latest(conn: sqlite3.Connection, info, subject_id: int, zone: tzinfo | None) -> dict | None:
    """The most recent accepted entry for this subject by the household's clock, or None."""
    rule = info.table.daily
    rows = conn.execute(
        f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed' AND {rule['per']} = ? "
        f"ORDER BY {rule['when']} DESC, id DESC LIMIT 20", (subject_id,)).fetchall()  # offsets can reorder a few
    best = None
    for row in rows:
        entry = dict(row)
        try:
            entry["_local"] = local(entry[rule["when"]], zone)
        except (TypeError, ValueError):
            continue
        if best is None or (entry["_local"], entry["id"]) > (best["_local"], best["id"]):
            best = entry
    return best


def recent_choices(conn: sqlite3.Connection, info, subject_id: int, columns: list[str], limit: int = 3) -> list[dict]:
    """The subject's latest distinct combinations of `columns` (newest first), to offer as quick picks.
    Shown on the button and filled into a visible form; nothing is ever saved from them without a person."""
    rule = info.table.daily
    found: list[dict] = []
    for row in conn.execute(
            f"SELECT {', '.join(columns)} FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed' "
            f"AND {rule['per']} = ? ORDER BY {rule['when']} DESC, id DESC LIMIT 200", (subject_id,)):
        choice = {c: row[c] for c in columns}
        if choice not in found:
            found.append(choice)
        if len(found) >= limit:
            break
    return found


def _same(a, b) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        return str(a or "").strip().casefold() == str(b or "").strip().casefold()
    if a is None or b is None:
        return a is None and b is None
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except ArithmeticError:
        return a == b


def possible_repeats(conn: sqlite3.Connection, info, values: dict, zone: tzinfo | None,
                     skip_proposal: int | None = None) -> list[dict]:
    """Entries that look like this suggested one: same subject and `same` values, within `minutes` of it.

    Each match is {"kind": "record", "row": ...} for an accepted entry or {"kind": "waiting", "proposal": id,
    "batch": id, "values": ...} for another suggestion on Review. Two real feedings can be close together, so this
    only warns; a person keeps both or rejects one."""
    rule = info.table.daily
    repeat = rule.get("repeat") if rule else None
    if not repeat:
        return []
    try:
        subject = int(values.get(rule["per"]))
        moment = local(values.get(rule["when"]), zone)
    except (TypeError, ValueError):
        return []
    gap = timedelta(minutes=repeat["minutes"])

    def close(other: dict) -> bool:
        try:
            other_moment = local(other.get(rule["when"]), zone)
        except (TypeError, ValueError):
            return False
        return abs(other_moment - moment) <= gap and all(_same(other.get(c), values.get(c)) for c in repeat["same"])

    found = []
    first, last = (moment - gap).date().isoformat(), (moment + gap).date().isoformat()
    for row in entries(conn, info, subject, first, last, zone):
        if close(row):
            found.append({"kind": "record", "row": row})
    for proposal in conn.execute(
            "SELECT id, batch_id, values_json FROM core__proposals WHERE status = 'pending' AND entry_kind = 'record' "
            "AND table_name = ? AND id != ? ORDER BY id", (info.name, skip_proposal or 0)):
        try:
            other = json.loads(proposal["values_json"])
            if int(other.get(rule["per"])) != subject:
                continue
        except (TypeError, ValueError, AttributeError):
            continue
        if close(other):
            found.append({"kind": "waiting", "proposal": proposal["id"], "batch": proposal["batch_id"],
                          "values": other})
    return found
