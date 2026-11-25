"""One record's timeline: dated entries from every table that links to it and declares `timeline`, newest first, by the household's own day (decision 0126)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime

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


def subject_table(info, rule: dict) -> str | None:
    """The real table whose records this timeline belongs to: where `per` points, through one link if it says so
    ("treatment.pet": the treatment's pet). None if the table it goes through is not there."""
    link = info.table.columns[rule["link"]]
    if not rule.get("through"):
        return target_table(info.module.name, link)
    hop = info.module.tables.get(link.to.partition(".")[2] if "." in link.to else link.to)
    return target_table(info.module.name, hop.columns[rule["through"]]) if hop is not None else None


def sources(registry: dict, subject) -> list[tuple]:
    """Every (table, rule) of a switched-on module whose timeline belongs to records of `subject`."""
    return [(info, info.table.timeline) for info in registry.values()
            if info.table.timeline and subject_table(info, info.table.timeline) == subject.name]


def entries(conn: sqlite3.Connection, info, rule: dict, subject_id: int, zone) -> list[dict]:
    """Every accepted, undeleted entry of one subject in time order, each with `_day` (the household's day) and
    `_local` (its clock, for a timed entry). Through a link, the linked record must also be there and not deleted.
    Nothing is stored, so an edit, delete or restore shows at once."""
    when = info.table.columns[rule["when"]]
    if rule.get("through"):
        hop = target_table(info.module.name, info.table.columns[rule["link"]])
        rows = conn.execute(
            f"SELECT e.* FROM {info.name} e JOIN {hop} h ON h.id = e.{rule['link']} WHERE e.deleted_at IS NULL "
            f"AND e.review_status = 'confirmed' AND h.deleted_at IS NULL AND h.{rule['through']} = ?",
            (subject_id,)).fetchall()
    else:
        rows = conn.execute(f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed' "
                            f"AND {rule['link']} = ?", (subject_id,)).fetchall()
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


def page(found: list[Item], before: date | None, limit: int = PAGE) -> tuple[list[Item], date | None]:
    """The lines before the day `before` (all of them when None), at most `limit` plus the rest of the last day
    listed, and the day the next "Earlier" page starts before (None when nothing is left)."""
    left = [item for item in found if before is None or item.day < before]
    shown = left[:limit]
    if shown:
        last = shown[-1].day
        shown += [item for item in left[limit:] if item.day == last]
    more = len(left) > len(shown)
    return shown, (shown[-1].day if more else None)
