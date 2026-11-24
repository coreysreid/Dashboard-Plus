"""Month calendars (decision 0119): a colour-coded grid with a symbol for every state, a legend and the same days in words."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, render_template, request

from dashboard.core import calendars, daily, dates, records
from dashboard.core.checklist import week_start
from dashboard.web import display

calendar_pages = Blueprint("calendar_pages", __name__)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH = re.compile(r"^(\d{4})-(\d{2})$")
AHEAD = 12  # months after this one that can be opened: only planned dates can be there


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def today_for(store: records.Records, info) -> date:
    """Today for this calendar: by the household's time zone for timed entries (decision 0110), else the
    computer's date, as Things to do reads it (decision 0107), so "Due today" means the same on both pages."""
    if info.table.columns[info.table.calendar["when"]].type == "datetime":
        clock = current_app.config.get("NOW")
        return daily.today(store.conn, clock() if clock else datetime.now(timezone.utc))
    return current_app.config["TODAY"]()


def chosen_month(text: str | None, today: date) -> tuple[int, int]:
    """The month asked for as 2026-11, or this month when it is missing, not a month, or too far ahead."""
    found = MONTH.match(text or "")
    if found:
        year, month = int(found.group(1)), int(found.group(2))
        latest = calendars.shift(today.year, today.month, AHEAD)
        if 1 <= month <= 12 and 1900 <= year and (year, month) <= latest:
            return year, month
    return today.year, today.month


def month_words(year: int, month: int) -> str:
    return f"{dates.MONTHS[month - 1]} {year}"


def _short_day(when: date, style: str) -> str:
    """"Mon 16 Nov", or "Mon Nov 16" where dates are written month first."""
    name, month = DAY_NAMES[when.weekday()][:3], dates.MONTHS[when.month - 1][:3]
    return f"{name} {month} {when.day}" if style == dates.MONTH_FIRST else f"{name} {when.day} {month}"


class Words:
    """The words for one calendar's looks, from its declaration and its state column's own choice labels."""

    def __init__(self, store: records.Records, info):
        self.info, self.rule = info, info.table.calendar
        self.store, self.formatter = store, display.Formatter(store)
        self.one, self.many = self.rule["entry"]
        state = info.table.columns.get(self.rule.get("state") or "")
        self.labels: dict[str, str] = {}
        if state is not None:
            for choice in state.choices:
                look = self.rule["looks"][choice.key]
                self.labels[look] = (self.labels[look] + " or " if look in self.labels else "") + \
                    self.formatter.text(info, state, choice.key)
        else:
            self.labels[self.rule["look"]] = f"{self.one[:1].upper()}{self.one[1:]} recorded"

    def looks(self) -> list[str]:
        """The looks this calendar can show, in the legend's order."""
        found = set(self.labels) | ({"due", "planned"} if self.rule.get("due") else set())
        return [look for look in calendars.LOOKS if look in found]

    def legend(self, look: str) -> str:
        if look == "due":
            return "Due, not recorded as done yet: shown once, on its own date"
        if look == "planned":
            return "Planned date"
        return self.labels[look]

    def count(self, look: str, n: int, day: date | None = None, today: date | None = None) -> str:
        """"2 feedings recorded", "Done: 2", "Due today", "Due, not recorded as done yet", "Planned"."""
        if look == "recorded" and not self.rule.get("state"):
            return f"{n} {self.one if n == 1 else self.many} recorded"
        if look == "due":
            words = "Due today" if day is not None and day == today else "Due, not recorded as done yet"
        elif look == "planned":
            words = "Planned"
        else:
            words = self.labels[look]
        return words if n == 1 else f"{words}: {n}"

    def total(self, look: str, n: int) -> str:
        """A month's count, always with its number: "18 feedings recorded", "Done: 1", "Planned: 2"."""
        if look == "recorded" and not self.rule.get("state"):
            return self.count(look, n)
        if look in ("due", "planned"):
            return f"{'Due, not recorded as done yet' if look == 'due' else 'Planned'}: {n}"
        return f"{self.labels[look]}: {n}"

    def subject(self, subject_id: int) -> str:
        column = self.info.table.columns[self.rule["per"]]
        return self.formatter.text(self.info, column, subject_id)

    def item(self, mark: calendars.Mark, today: date, style: str) -> dict:
        """One line of the list in words, with a link to the record it comes from."""
        if mark.kind == "due":
            target = calendars.subject_table(self.store.registry, self.info)
            when = ("due today" if mark.day == today else
                    f"due since {dates.show(mark.day, style)}, not recorded as done yet" if mark.day < today
                    else "planned")
            return {"look": mark.look, "symbol": calendars.SYMBOLS[mark.look],
                    "words": f"{self.subject(mark.subject_id)}: {when}", "href": f"/t/{target.name}/{mark.subject_id}"}
        state = self.info.table.columns.get(self.rule.get("state") or "")
        what = (self.formatter.text(self.info, state, mark.state) if state is not None
                else f"{self.one[:1].upper()}{self.one[1:]} recorded")
        if self.rule["show"] == "all":
            what = f"{self.subject(mark.subject_id)}: {what}"
        if mark.moment is not None:
            what = f"{mark.moment.hour % 12 or 12}:{mark.moment.minute:02d} {'am' if mark.moment.hour < 12 else 'pm'} · {what}"
        return {"look": mark.look, "symbol": calendars.SYMBOLS[mark.look], "words": what,
                "href": f"/t/{self.info.name}/{mark.record_id}"}


def month_view(store: records.Records, info, year: int, month: int, today: date, subject_id: int | None = None,
               link=None, full_href: str | None = None) -> dict:
    """Everything one calendar shows for one month: the grid, the legend, the summary and the same days in words.
    `link(year, month)` makes the Previous month and Next month addresses."""
    rule = info.table.calendar
    words = Words(store, info)
    style = dates.household_style(store.conn)
    first_day = week_start(store.conn)
    found = calendars.month(store.conn, store.registry, info, year, month, today, first_day, subject_id)
    cal_id = f"cal-{info.name}" + (f"-{subject_id}" if subject_id is not None else "")
    name = words.subject(subject_id) if subject_id is not None else None
    totals_by_day = {}
    if info.table.daily and subject_id is not None and rule["show"] == "one" and info.table.daily["per"] == rule["per"]:
        last = found.days[-1].day.isoformat()  # food put out by unit, never added across units (decision 0110)
        zone = daily.household_zone(store.conn)
        for result in daily.days(store.conn, info, subject_id, found.days[0].day.isoformat(), last, zone):
            if result.totals:
                totals_by_day[result.day] = daily.totals_words(info.table.daily, result)
    weeks, listed = [], []
    for week in found.weeks:
        row = []
        for cell in week:
            if not cell.in_month:
                row.append(None)
                continue
            counts = cell.counts()
            chips = [{"look": look, "symbol": calendars.SYMBOLS[look], "count": n,
                      "words": words.count(look, n, cell.day, today)} for look, n in counts]
            said = "; ".join(c["words"] for c in chips)
            anchor = f"{cal_id}-d-{cell.day.isoformat()}"
            row.append({"day": cell.day.day, "iso": cell.day.isoformat(), "today": cell.day == today,
                        "chips": chips, "anchor": anchor if chips else None,
                        "label": f"{cell.day.day} {dates.MONTHS[month - 1]}" + (", today" if cell.day == today else "")
                                 + (f": {said}" if said else "")})
            if chips:
                extra = totals_by_day.get(cell.day.isoformat())
                day_href = None
                if info.table.daily and subject_id is not None and rule["show"] == "one":
                    day_href = f"/daily/{info.name}?" + urlencode({"subject": subject_id, "day": cell.day.isoformat()})
                listed.append({"anchor": anchor, "day": _short_day(cell.day, style) + (" (today)" if cell.day == today
                                                                                       else ""),
                               "summary": said + (f" · {extra}" if extra else ""), "day_href": day_href,
                               "marks": [words.item(m, today, style) for m in cell.marks]})
        weeks.append(row)
    order = calendars.weekday_order(first_day)
    heading = month_words(year, month)
    totals = found.totals()
    if totals:
        summary = f"{heading}" + (f" · {name}" if name else "") + " · " + " · ".join(
            words.total(look, totals[look]) for look in calendars.LOOKS if look in totals)
    elif rule.get("due"):
        summary = f"Nothing recorded or planned in {heading}" + (f" for {name}" if name else "") + "."
    else:
        summary = f"No {words.one} entry recorded" + (f" for {name}" if name else "") + f" in {heading}."
    if rule.get("due"):
        blank = ("A blank day has nothing recorded or planned. Only each one's next open date is shown as due, once; "
                 "earlier times are never filled in as missed.")
    else:
        blank = f"A blank day has no {words.one} entry recorded. It does not mean anything was missed."
    prev_y, prev_m = calendars.shift(year, month, -1)
    next_y, next_m = calendars.shift(year, month, 1)
    latest = calendars.shift(today.year, today.month, AHEAD)
    return {"id": cal_id, "title": rule["title"], "heading": heading, "name": name, "summary": summary,
            "caption": f"{rule['title']}" + (f" for {name}" if name else "") + f", {heading}",
            "headers": [{"short": DAY_NAMES[i][:3], "long": DAY_NAMES[i]} for i in order],
            "weeks": weeks, "days": listed, "blank": blank,
            "legend": [{"look": look, "symbol": calendars.SYMBOLS[look], "words": words.legend(look)}
                       for look in words.looks()],
            "prev": link(prev_y, prev_m) if link else None, "prev_words": month_words(prev_y, prev_m),
            "next": link(next_y, next_m) if link and (next_y, next_m) <= latest else None,
            "next_words": month_words(next_y, next_m),
            "this_month": link(today.year, today.month) if link and (year, month) != (today.year, today.month) else None,
            "full": full_href}


def _href(path: str, **args):
    def make(year: int, month: int) -> str:
        return f"{path}?" + urlencode({**{k: v for k, v in args.items() if v is not None},
                                      "month": f"{year:04d}-{month:02d}"})
    return make


def record_panels(store: records.Records, subject_info, record: dict) -> list[dict]:
    """On a record's own page (a pet, a routine): this month's calendar of what was recorded for it."""
    panels = []
    for info in calendars.calendar_tables(store.registry, subject_info):
        today = today_for(store, info)
        path = f"/calendar/{info.name}"
        panels.append(month_view(store, info, today.year, today.month, today, record["id"],
                                 link=_href(path, subject=record["id"]),
                                 full_href=f"{path}?" + urlencode({"subject": record["id"]})))
    return panels


def todo_calendar_tables(registry: dict) -> list:
    """Calendars that show due dates, like Routines': the ones Things to do's Calendar tab shows."""
    return [info for info in calendars.calendar_tables(registry) if info.table.calendar.get("due")]


@calendar_pages.get("/calendar/<table>")
def calendar_page(table):
    store = _store()
    info = store.registry.get(table)
    if info is None or not info.table.calendar or info not in calendars.calendar_tables(store.registry):
        abort(404)
    rule = info.table.calendar
    subject_info = calendars.subject_table(store.registry, info)
    today = today_for(store, info)
    year, month = chosen_month(request.args.get("month"), today)
    rows = [dict(r) for r in store.conn.execute(f"SELECT * FROM {subject_info.name} WHERE deleted_at IS NULL "
                                                 f"ORDER BY id")]
    subjects = sorted(({"id": r["id"], "name": display.display_name(subject_info, r, store)} for r in rows),
                      key=lambda s: (s["name"].lower(), s["id"]))
    wanted = request.args.get("subject", type=int)
    chosen = next((s for s in subjects if s["id"] == wanted), None)
    if rule["show"] == "one" and chosen is None:
        if not subjects:
            return render_template("calendar.html", title=rule["title"], view=None, subjects=[], chosen=None,
                                   table=table, month=None, add_subject=f"/t/{subject_info.name}/new",
                                   no_subject=f"Add to {display.table_title(subject_info)} first.")
        chosen = subjects[0]
    subject_id = chosen["id"] if chosen else None
    view = month_view(store, info, year, month, today, subject_id, link=_href(f"/calendar/{table}", subject=subject_id))
    return render_template("calendar.html", title=rule["title"], view=view, subjects=subjects, chosen=chosen,
                           table=table, month=f"{year:04d}-{month:02d}", no_subject=None,
                           show_all=rule["show"] == "all",
                           subject_href=f"/t/{subject_info.name}/{subject_id}" if subject_id else None)


@calendar_pages.get("/to-do/calendar")
def todo_calendar():
    """Things to do, Calendar: each list with due dates (Routines) as one month, done and skipped by the day they
    happened and each open date once."""
    from dashboard.web.checklist import visible_tabs
    store = _store()
    found = todo_calendar_tables(store.registry)
    if not found:
        abort(404)
    today = current_app.config["TODAY"]()
    year, month = chosen_month(request.args.get("month"), today)
    views = [month_view(store, info, year, month, today, link=_href("/to-do/calendar"),
                        full_href=f"/calendar/{info.name}") for info in found]
    return render_template("todo_calendar.html", views=views, tabs=visible_tabs(store.registry), window="calendar",
                           heading=month_words(year, month))
