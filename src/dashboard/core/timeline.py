"""One record's timeline: dated entries from every table that links to it and declares `timeline`, newest first, by the household's own day (decision 0126)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dashboard.core import daily
from dashboard.core.schema import target_table

# Each fixed look's symbol (base.html colours it with .tl-<look>); the kind's own words always sit beside it.
SYMBOLS = {"recorded": "●", "done": "✓", "measured": "◆", "visit": "■"}
# How many lines one page lists; a day is never split across two pages, so a page can hold a few more.
PAGE = 25
PANEL = 8


@dataclass
class Item:
    """One line of a timeline: one entry, or one day's entries of a table that summarises by day. `previous` is
    the entry of the same table before this one, for the change since it (`change` in the declaration)."""
    info: object
    rule: dict
    day: date
    rows: list[dict] = field(default_factory=list)
    moment: datetime | None = None  # the household's clock, for one timed entry
    previous: dict | None = None

    @property
    def order(self) -> tuple:
        clock = self.moment.strftime("%H:%M:%S") if self.moment is not None else ""
        return self.day, clock, self.info.name, self.rows[-1]["id"]


def subject_table(info, rule: dict, registry: dict | None = None) -> str | None:
    """The real table whose records this timeline belongs to: where `per` points, through one link if it says so
    ("treatment.pet": the treatment's pet; the linked table may be in another module). None if the table it goes
    through is not there."""
    link = info.table.columns[rule["link"]]
    if not rule.get("through"):
        return target_table(info.module.name, link)
    hop = (registry or {}).get(target_table(info.module.name, link))
    if hop is not None:
        return target_table(hop.module.name, hop.table.columns[rule["through"]])
    own = info.module.tables.get(link.to) if "." not in link.to else None
    return target_table(info.module.name, own.columns[rule["through"]]) if own is not None else None


def sources(registry: dict, subject) -> list[tuple]:
    """Every (table, rule) of a switched-on module whose timeline belongs to records of `subject`."""
    return [(info, info.table.timeline) for info in registry.values()
            if info.table.timeline and subject_table(info, info.table.timeline, registry) == subject.name]


def _from(info, rule: dict, subject_id: int) -> tuple[str, list]:
    """The rows of one source that belong to one subject, for SQL: accepted and undeleted, and through a link the
    linked record must also be there and not deleted. The table is `e`."""
    if rule.get("through"):
        hop = target_table(info.module.name, info.table.columns[rule["link"]])
        return (f"FROM {info.name} e JOIN {hop} h ON h.id = e.{rule['link']} WHERE e.deleted_at IS NULL "
                f"AND e.review_status = 'confirmed' AND h.deleted_at IS NULL AND h.{rule['through']} = ?"), [subject_id]
    return (f"FROM {info.name} e WHERE e.deleted_at IS NULL AND e.review_status = 'confirmed' "
            f"AND e.{rule['link']} = ?"), [subject_id]


def _parse(rows, info, rule: dict, zone) -> list[dict]:
    """Each row with `_day` and `_local`, in time order; a row with no usable date is left out."""
    when = info.table.columns[rule["when"]]
    found = []
    for row in rows:
        entry = dict(row)
        try:
            moment = daily.local(entry[rule["when"]], zone) if when.type == "datetime" else None
            day = moment.date() if moment is not None else date.fromisoformat(str(entry[rule["when"]])[:10])
        except (TypeError, ValueError):
            continue
        entry["_day"], entry["_local"] = day, moment
        found.append(entry)
    found.sort(key=lambda e: (e["_day"], e["_local"].strftime("%H:%M:%S") if e["_local"] else "", e["id"]))
    return found


def entries(conn: sqlite3.Connection, info, rule: dict, subject_id: int, zone) -> list[dict]:
    """Every accepted, undeleted entry of one subject in time order, each with `_day` (the household's day) and
    `_local` (its clock, for a timed entry). Through a link, the linked record must also be there and not deleted.
    Nothing is stored, so an edit, delete or restore shows at once."""
    sql, params = _from(info, rule, subject_id)
    return _parse(conn.execute(f"SELECT e.* {sql}", params).fetchall(), info, rule, zone)


def _newest(conn: sqlite3.Connection, info, rule: dict, subject_id: int, zone, upper: date | None, count: int,
            extra: str = "") -> tuple[list[dict], bool]:
    """The newest entries of one subject (decision 0136): enough of them that the newest `count` days (or entries,
    for a source that lists each one) are all there, and whether the whole list was read. Rows are read newest
    first by the date written in them, a few more each time. A household day is never more than a day away from the
    date written in a row (a time with an offset moves into the household's zone), so rows still unread cannot be on
    a day later than the day after the oldest row read; only entries on later days than that are trusted.
    `upper` leaves out entries on or after that day. Entries come back in time order."""
    sql, params = _from(info, rule, subject_id)
    column = f"e.{rule['when']}"
    if upper is not None:
        sql, params = sql + f" AND substr({column}, 1, 10) < ?", params + [(upper + timedelta(days=1)).isoformat()]
    sql += extra
    size = max(60, count * 4)
    while True:
        rows = conn.execute(f"SELECT e.* {sql} ORDER BY substr({column}, 1, 10) DESC, e.id DESC LIMIT ?",
                            params + [size]).fetchall()
        found = [e for e in _parse(rows, info, rule, zone) if upper is None or e["_day"] < upper]
        if len(rows) < size:
            return found, True
        try:
            reach = date.fromisoformat(str(rows[-1][rule["when"]])[:10]) + timedelta(days=1)
        except (TypeError, ValueError):
            reach = None
        if reach is not None:
            sure = [e for e in found if e["_day"] > reach]
            units = {e["_day"] for e in sure} if rule.get("summarise") == "day" else sure
            if len(units) >= count:
                return sure, False
        size *= 4


def _window_source(conn: sqlite3.Connection, info, rule: dict, subject_id: int, zone, before: date | None,
                   limit: int) -> tuple[list[Item], bool]:
    """The newest lines of one source below `before`: every line on its newest `limit + 1` days (or entries), with
    the entry before for a change, and whether older lines were left unread (decision 0136)."""
    day_lines = rule.get("summarise") == "day"
    rows, whole = _newest(conn, info, rule, subject_id, zone, before, limit + 1)
    units = sorted({e["_day"] for e in rows} if day_lines else [e["_day"] for e in rows], reverse=True)
    floor = units[limit] if len(units) > limit else None
    kept = [e for e in rows if floor is None or e["_day"] >= floor]
    cut = (not whole) or len(kept) < len(rows)
    if day_lines:
        by_day: dict[date, list[dict]] = {}
        for row in kept:
            by_day.setdefault(row["_day"], []).append(row)
        return [Item(info, rule, day, listed) for day, listed in by_day.items()], cut
    previous = None
    if rule.get("change") and floor is not None:  # the newest entry older than the lines kept that has a value
        older, _ = _newest(conn, info, rule, subject_id, zone, floor, 1, f" AND e.{rule['change']} IS NOT NULL")
        previous = older[-1] if older else None
    lines = []
    for row in kept:
        lines.append(Item(info, rule, row["_day"], [row], row["_local"], previous if rule.get("change") else None))
        if row.get(rule.get("change") or "") is not None:
            previous = row
    return lines, cut


def window(conn: sqlite3.Connection, registry: dict, subject, subject_id: int, before: date | None, limit: int
           ) -> tuple[list[Item], bool]:
    """Enough lines for `page` to give what it gives for the whole history, without reading it all (decision 0136):
    each source reads only its newest days. Returns the lines, newest first, and whether older ones were left
    unread; `page(lines, before, limit, cut)` then matches `page(items(...), before, limit)` exactly."""
    zone = daily.household_zone(conn)
    found: list[Item] = []
    cut = False
    for info, rule in sources(registry, subject):
        lines, source_cut = _window_source(conn, info, rule, subject_id, zone, before, limit)
        found.extend(lines)
        cut = cut or source_cut
    found.sort(key=lambda item: item.order, reverse=True)
    return found, cut


def items(conn: sqlite3.Connection, registry: dict, subject, subject_id: int) -> list[Item]:
    """Every line of one record's timeline, newest first: one per entry, or one per day for a table that
    summarises by day, with the entry before for a change."""
    zone = daily.household_zone(conn)
    found: list[Item] = []
    for info, rule in sources(registry, subject):
        rows = entries(conn, info, rule, subject_id, zone)
        if rule.get("summarise") == "day":
            by_day: dict[date, list[dict]] = {}
            for row in rows:
                by_day.setdefault(row["_day"], []).append(row)
            found.extend(Item(info, rule, day, listed) for day, listed in by_day.items())
            continue
        before = None
        for row in rows:
            found.append(Item(info, rule, row["_day"], [row], row["_local"], before if rule.get("change") else None))
            if row.get(rule.get("change") or "") is not None:
                before = row
    found.sort(key=lambda item: item.order, reverse=True)
    return found


def page(found: list[Item], before: date | None, limit: int = PAGE, cut: bool = False
         ) -> tuple[list[Item], date | None]:
    """The lines before the day `before` (all of them when None), at most `limit` plus the rest of the last day
    listed, and the day the next "Earlier" page starts before (None when nothing is left)."""
    left = [item for item in found if before is None or item.day < before]
    shown = left[:limit]
    if shown:
        last = shown[-1].day
        shown += [item for item in left[limit:] if item.day == last]
    more = len(left) > len(shown) or cut  # `cut`: older lines were left unread, so there are more
    return shown, (shown[-1].day if more else None)
