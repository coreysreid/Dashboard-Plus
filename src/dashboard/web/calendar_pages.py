"""Month calendars (decision 0119): a colour-coded grid with a symbol for every state, a legend and the same days in words."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, redirect, render_template, request

from dashboard.core import calendars, daily, dates, calendars_corrections, records, watch
from dashboard.core.modules import CALENDAR_ENTRY_LOOKS
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
    when = info.table.columns.get(info.table.calendar["when"] or "")
    if when is not None and when.type == "datetime":
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


def _cell_day(when: date, style: str) -> str:
    """A grid cell's spoken name in the household's own order: "26 November", or "November 26" for month-first."""
    month = dates.MONTHS[when.month - 1]
    return f"{month} {when.day}" if style == dates.MONTH_FIRST else f"{when.day} {month}"


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
        self.not_done = self.rule.get("not_done") or "not recorded as done yet"  # the list's own words (decision 0142)
        state = info.table.columns.get(self.rule.get("state") or "")
        self.labels: dict[str, str] = {}
        if state is not None:
            for choice in state.choices:
                look = self.rule["looks"][choice.key]
                self.labels[look] = (self.labels[look] + " or " if look in self.labels else "") + \
                    self.formatter.text(info, state, choice.key)
        elif not calendars.own(info) or self.rule.get("when") or info.table.actions:
            # "Feeding recorded", "Job done": a calendar of a table's own records has entries only from its date
            # column or its Mark done buttons (decision 0122); one with neither, like Bills, shows due dates only.
            self.labels[self.rule["look"]] = f"{self.one[:1].upper()}{self.one[1:]} {self.rule['look']}"
            if calendars.own(info) and not self.rule.get("when") and any(
                    a.get("counts_as") == "skipped" for a in info.table.actions):
                self.labels["skipped"] = f"{self.one[:1].upper()}{self.one[1:]} skipped"
        self._rows: dict[int, dict] = {}

    def looks(self) -> list[str]:
        """The looks this calendar can show, in the legend's order."""
        found = set(self.labels) | ({"due", "planned"} if self.rule.get("due") else set())
        return [look for look in calendars.LOOKS if look in found]

    def legend(self, look: str) -> str:
        if look == "due":
            return f"Due, {self.not_done}: shown once, on its own date"
        if look == "planned":
            return "Planned date"
        return self.labels[look]

    def count(self, look: str, n: int, day: date | None = None, today: date | None = None) -> str:
        """"2 feedings recorded", "Done: 2", "Due today", "Due, not recorded as done yet", "Planned"."""
        if look in CALENDAR_ENTRY_LOOKS and not self.rule.get("state"):  # "2 feedings recorded", "1 job done"
            return f"{n} {self.one if n == 1 else self.many} {look}"
        if look == "due":
            words = "Due today" if day is not None and day == today else f"Due, {self.not_done}"
        elif look == "planned":
            words = "Planned"
        else:
            words = self.labels.get(look, look.capitalize())
        return words if n == 1 else f"{words}: {n}"

    def total(self, look: str, n: int) -> str:
        """A month's count, always with its number: "18 feedings recorded", "Done: 1", "Planned: 2"."""
        if look in CALENDAR_ENTRY_LOOKS and not self.rule.get("state"):
            return self.count(look, n)
        if look in ("due", "planned"):
            return f"{f'Due, {self.not_done}' if look == 'due' else 'Planned'}: {n}"
        return f"{self.labels.get(look, look.capitalize())}: {n}"

    def _row(self, record_id: int) -> dict:
        """One of a table's own records, for a calendar without `per` (decision 0122), read once per page."""
        if record_id not in self._rows:
            row = self.store.conn.execute(f"SELECT * FROM {self.info.name} WHERE id = ?", (record_id,)).fetchone()
            self._rows[record_id] = dict(row) if row else {"id": record_id}
        return self._rows[record_id]

    def subject(self, subject_id: int, hidden: bool = False) -> str:
        """Who the calendar is for. On a private table before Show it is only "this person" (decision 0123)."""
        if calendars.own(self.info):  # the record's own name, never one of its private columns (decision 0122)
            return display.display_name(self.info, self._row(subject_id), self.store)
        column = self.info.table.columns[self.rule["per"]]
        if hidden:
            return "this person"
        return self.formatter.text(self.info, column, subject_id)

    def item(self, mark: calendars.Mark, today: date, style: str) -> dict:
        """One line of the list in words, with a link to the record it comes from."""
        if mark.kind == "due":
            target = calendars.subject_table(self.store.registry, self.info)
            when = ("due today" if mark.day == today else
                    f"due since {dates.show(mark.day, style)}, {self.not_done}" if mark.day < today
                    else "planned")
            if calendars.own(self.info):  # "Hatchback: registration or vehicle tax due today" (decision 0122)
                what = watch.what_for(self.info.table.watch.get("expiring") or {}, self._row(mark.subject_id))
                when = f"{what} {when}" if what else when
            return {"look": mark.look, "symbol": calendars.SYMBOLS[mark.look],
                    "words": f"{self.subject(mark.subject_id)}: {when}", "href": f"/t/{target.name}/{mark.subject_id}"}
        state = self.info.table.columns.get(self.rule.get("state") or "")
        what = (self.formatter.text(self.info, state, mark.state) if state is not None
                else self.labels.get(mark.look, f"{self.one[:1].upper()}{self.one[1:]} {mark.look}"))
        if self.rule["show"] == "all":
            what = f"{self.subject(mark.subject_id)}: {what}"
        if mark.earlier:  # not the date the record keeps now, but one its history shows (decision 0129)
            what = f"{what} (an earlier date you recorded)"
        if mark.moment is not None:
            what = f"{mark.moment.hour % 12 or 12}:{mark.moment.minute:02d} {'am' if mark.moment.hour < 12 else 'pm'} · {what}"
        return {"look": mark.look, "symbol": calendars.SYMBOLS[mark.look], "words": what,
                "href": f"/t/{self.info.name}/{mark.record_id}"}


PRIVATE_WORDS = "Private history — press Show to see it."


def _private_lines(store: records.Records, info, subject_id: int | None, first: date, last: date) -> dict:
    """After Show on a private calendar (decision 0121): each entry's line by its household day, from the private
    daily log when it has one ("8:00 am · dose · the medicine · 1 tablet · Who gave it: ..."), else None."""
    from dashboard.web import private_daily
    rule = info.table.calendar
    if not info.table.daily or subject_id is None or info.table.daily["per"] != rule["per"]:
        return {}
    formatter = display.Formatter(store)
    zone = daily.household_zone(store.conn)
    found = {}
    for result in daily.days(store.conn, info, subject_id, first.isoformat(), last.isoformat(), zone):
        found[result.day] = {e["id"]: private_daily.line(store, info, e, formatter, True) for e in result.entries}
    return found


def month_view(store: records.Records, info, year: int, month: int, today: date, subject_id: int | None = None,
               link=None, full_href: str | None = None, show: bool = False, show_action: str | None = None,
               corrections: bool = False) -> dict:
    """Everything one calendar shows for one month: the grid, the legend, the summary and the same days in words.
    `link(year, month)` makes the Previous month and Next month addresses. A private table (decision 0121) shows
    only ● and how many each day until `show`, a person's pressed Show: no times, names, amounts or record links.
    `corrections` gives each day read from history its "Not a done day" button (decision 0132)."""
    rule = info.table.calendar
    private = info.table.private
    words = Words(store, info)
    style = dates.household_style(store.conn)
    first_day = week_start(store.conn)
    found = calendars.month(store.conn, store.registry, info, year, month, today, first_day, subject_id)
    cal_id = f"cal-{info.name}" + (f"-{subject_id}" if subject_id is not None else "")
    name = words.subject(subject_id, private and not show) if subject_id is not None else None
    totals_by_day = {}
    lines = _private_lines(store, info, subject_id, found.days[0].day, found.days[-1].day) if private and show else {}
    if not private and info.table.daily and subject_id is not None and rule["show"] == "one" and info.table.daily["per"] == rule["per"]:
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
                        "label": _cell_day(cell.day, style) + (", today" if cell.day == today else "")
                                 + (f": {said}" if said else "")})
            if chips:
                extra = totals_by_day.get(cell.day.isoformat())
                day_href = None
                if info.table.daily and subject_id is not None and rule["show"] == "one":
                    day_href = f"/daily/{info.name}?" + urlencode({"subject": subject_id, "day": cell.day.isoformat()})
                if private and not show:  # counts only: no time, name or link to a record (decision 0121)
                    marks = []
                elif private and cell.day.isoformat() in lines:
                    shown = lines[cell.day.isoformat()]
                    marks = [{"look": m.look, "symbol": calendars.SYMBOLS[m.look], "href": f"/t/{info.name}/{m.record_id}",
                              "words": shown.get(m.record_id) or words.item(m, today, style)["words"]}
                             for m in cell.marks]
                else:
                    marks = [words.item(m, today, style) for m in cell.marks]
                    if corrections:  # a day read from history can be taken off; today's own date is edited instead
                        for mark, shown in zip(cell.marks, marks):
                            if mark.earlier:
                                shown["remove"] = {"record": mark.record_id, "day": mark.day.isoformat(),
                                                   "day_words": _short_day(mark.day, style)}
                listed.append({"anchor": anchor, "day": _short_day(cell.day, style) + (" (today)" if cell.day == today
                                                                                       else ""),
                               "summary": said + (f" · {extra}" if extra else ""), "day_href": day_href,
                               "marks": marks})
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
            "full": full_href, "private": private, "show": show, "private_words": PRIVATE_WORDS,
            "show_action": show_action if private else None, "subject_id": subject_id,
            "month": f"{year:04d}-{month:02d}",
            "remove_action": f"/calendar/{info.name}/not-done" if corrections else None,
            "hide": link(year, month) if private and show and link else None,
            "name_hidden": bool(private and not show and name)}


def _href(path: str, **args):
    def make(year: int, month: int) -> str:
        return f"{path}?" + urlencode({**{k: v for k, v in args.items() if v is not None},
                                      "month": f"{year:04d}-{month:02d}"})
    return make


def record_panels(store: records.Records, subject_info, record: dict) -> list[dict]:
    """On a record's own page (a pet, a routine): this month's calendar of what was recorded for it."""
    panels = []
    for info in calendars.calendar_tables(store.registry, subject_info):
        if not _applies(store, info, record["id"]):
            continue  # a neighbour with no medication detail and no doses gets no dose calendar (decision 0121)
        today = today_for(store, info)
        path = f"/calendar/{info.name}"
        panels.append(month_view(store, info, today.year, today.month, today, record["id"],
                                 link=_href(path, subject=record["id"]),
                                 full_href=f"{path}?" + urlencode({"subject": record["id"]}), show_action=path))
    return panels


def _applies(store: records.Records, info, subject_id: int) -> bool:
    """Whether a subject has this calendar: always, except a private log that does not apply to them (0120)."""
    if info.table.private and info.table.daily and info.table.daily["per"] == info.table.calendar["per"]:
        from dashboard.web import private_daily
        return private_daily.applies(store, info, subject_id)
    return True


def todo_calendar_tables(registry: dict) -> list:
    """Calendars that show due dates, like Routines': the ones Things to do's Calendar tab shows."""
    return [info for info in calendars.calendar_tables(registry)
            if info.table.calendar.get("due") and not info.table.private]


@calendar_pages.get("/calendar/<table>")
def calendar_page(table):
    return _calendar_page(table, show=False)


@calendar_pages.post("/calendar/<table>")
def show_calendar_page(table):
    """Show on a private calendar (decision 0121): a pressed button with the session check, like the private sheet
    (decision 0071), so no address, bookmark or shared link opens each day's entries. Others have nothing to show."""
    info = _store().registry.get(table)
    if info is None or not info.table.private:
        abort(404)
    return _calendar_page(table, show=True)


def _calendar_page(table, show: bool):
    store = _store()
    info = store.registry.get(table)
    if info is None or not info.table.calendar or info not in calendars.calendar_tables(store.registry):
        abort(404)
    rule = info.table.calendar
    subject_info = calendars.subject_table(store.registry, info)
    today = today_for(store, info)
    year, month = chosen_month(request.values.get("month"), today)
    rows = [dict(r) for r in store.conn.execute(f"SELECT * FROM {subject_info.name} WHERE deleted_at IS NULL "
                                                 f"ORDER BY id")]
    hidden = info.table.private and not show  # names wait for Show, so the people are listed by number (0123)
    subjects = sorted(({"id": r["id"], "name": "" if hidden else display.display_name(subject_info, r, store)}
                       for r in rows if _applies(store, info, r["id"])),
                      key=lambda s: (s["id"],) if hidden else (s["name"].lower(), s["id"]))
    if hidden:
        subjects = display.private_subject_names(subjects)  # "Person 1", never a record number (decision 0142)
    wanted = request.values.get("subject", type=int)
    chosen = next((s for s in subjects if s["id"] == wanted), None)
    if rule["show"] == "one" and chosen is None:
        if not subjects:
            return render_template("calendar.html", title=rule["title"], view=None, subjects=[], chosen=None,
                                   table=table, month=None, add_subject=f"/t/{subject_info.name}/new",
                                   no_subject=f"Add to {display.table_title(subject_info)} first.")
        chosen = subjects[0]
    subject_id = chosen["id"] if chosen else None
    view = month_view(store, info, year, month, today, subject_id, link=_href(f"/calendar/{table}", subject=subject_id),
                      show=show, show_action=f"/calendar/{table}", corrections=_correctable(info))
    from dashboard.web.bar_pages import table_panels  # jobs done per month under the month (decision 0129)
    return render_template("calendar.html", title=rule["title"], view=view, subjects=subjects, chosen=chosen,
                           table=table, month=f"{year:04d}-{month:02d}", no_subject=None,
                           show_all=rule["show"] == "all", fix_notice=_fix_notice(store, info),
                           table_bars=table_panels(store, info) if calendars.own(info) else [],
                           subject_href=f"/t/{subject_info.name}/{subject_id}" if subject_id else None)


# ----- Not a done day (decision 0132) -------------------------------------------------------------------


def _correctable(info) -> bool:
    """A calendar whose days from history can be taken off: a table's own records with `history = true`. Never a
    private table (a calendar without `per` cannot be private, decision 0123; checked again here)."""
    return calendars.own(info) and bool(info.table.calendar.get("history")) and not info.table.private


def _fix_notice(store: records.Records, info) -> dict | None:
    """The notice after taking a day off or putting it back, with Undo while the day is still off."""
    if not _correctable(info):
        return None
    if request.args.get("unchanged"):
        return {"words": calendars_corrections.NOT_EARLIER, "undo": None}
    op = request.args.get("removed") or request.args.get("put_back")
    found = calendars_corrections.find(store.conn, info.name, op) if op else None
    if found is None:
        return None
    row = store.conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (found["record_id"],)).fetchone()
    name = display.display_name(info, dict(row), store) if row else "This record"
    day = _short_day(found["day"], dates.household_style(store.conn))
    if found["off"]:
        return {"words": f"Taken off the calendar: {name}, {day}. Its history keeps this, and Undo puts it back.",
                "undo": {"href": f"/calendar/{info.name}/put-back", "op": op}}
    return {"words": f"Put back on the calendar: {name}, {day}.", "undo": None}


def _correction_target(table):
    store = _store()
    info = store.registry.get(table)
    if info is None or not _correctable(info) or info not in calendars.calendar_tables(store.registry):
        abort(404)
    return store, info


def _month_arg() -> dict:
    month = request.form.get("month") or ""
    return {"month": month} if MONTH.match(month) else {}


@calendar_pages.post("/calendar/<table>/not-done")
def not_done_day(table):
    """"Not a done day — remove from the calendar": a pressed button with the session check, like Mark done. It
    adds one history entry for the record; nothing in the record or its earlier history is changed."""
    store, info = _correction_target(table)
    record_id = request.form.get("record", type=int)
    try:
        day = date.fromisoformat(request.form.get("day") or "")
    except ValueError:
        abort(404)
    if record_id is None:
        abort(404)
    try:
        op = calendars_corrections.take_off(store, info, record_id, day)
    except records.ActionNotAvailable:
        return redirect(f"/calendar/{table}?" + urlencode({**_month_arg(), "unchanged": 1}) + "#fix-notice")
    return redirect(f"/calendar/{table}?" + urlencode({**_month_arg(), "removed": op}) + "#fix-notice")


@calendar_pages.post("/calendar/<table>/put-back")
def put_back_day(table):
    """Undo of "Not a done day", from the calendar's notice or the record's history: one more history entry."""
    store, info = _correction_target(table)
    op = request.form.get("op") or ""
    try:
        found = calendars_corrections.put_back(store, info, op)
    except records.RecordNotFound:
        abort(404)
    except records.ActionNotAvailable:
        found = calendars_corrections.find(store.conn, info.name, op)
    if request.form.get("back") == "record":
        return redirect(f"/t/{table}/{found['record_id']}")
    month = _month_arg() or {"month": f"{found['day'].year:04d}-{found['day'].month:02d}"}
    return redirect(f"/calendar/{table}?" + urlencode({**month, "put_back": op}) + "#fix-notice")


# Words for each look when several lists share one month (decision 0122); each line in words says its own.
TOGETHER = {"done": "Done", "recorded": "Recorded", "skipped": "Skipped",
            "due": "Due, not recorded as done yet", "planned": "Planned"}
TOGETHER_LEGEND = {**TOGETHER, "due": "Due, not recorded as done yet: shown once, on its own date",
                   "planned": "Planned date"}
TOGETHER_BLANK = ("A blank day has nothing recorded or planned. Only each one's next open date is shown as due, "
                  "once; earlier times are never filled in as missed.")


def _together_count(look: str, n: int, day: date, today: date) -> str:
    words = "Due today" if look == "due" and day == today else TOGETHER[look]
    return words if n == 1 else f"{words}: {n}"


def together_view(store: records.Records, infos: list, year: int, month: int, today: date, link=None,
                  name: str = "Things to do calendar") -> dict:
    """Several calendars in one month (decision 0122): one grid of every list's marks, one legend, and each line in
    words starting with its module's name ("Home care · Clear the gutters: Job done"). Never a private table."""
    style = dates.household_style(store.conn)
    first_day = week_start(store.conn)
    cal_id = "cal-together"
    by_day: dict[date, list] = {}
    looks: set[str] = set()
    per_list: dict[str, int] = {}
    for info in infos:
        if info.table.private:
            continue
        words = Words(store, info)
        looks |= set(words.looks())
        label = info.module.title
        per_list.setdefault(label, 0)
        for cell in calendars.month(store.conn, store.registry, info, year, month, today, first_day).days:
            for mark in cell.marks:
                by_day.setdefault(cell.day, []).append((label, words, mark))
                per_list[label] += 1
    weeks, listed, totals = [], [], {}
    for week in calendars.grid(year, month, first_day):
        row = []
        for day in week:
            if day is None:
                row.append(None)
                continue
            marks = by_day.get(day, [])
            counts: dict[str, int] = {}
            for _, _, mark in marks:
                counts[mark.look] = counts.get(mark.look, 0) + 1
                totals[mark.look] = totals.get(mark.look, 0) + 1
            chips = [{"look": look, "symbol": calendars.SYMBOLS[look], "count": counts[look],
                      "words": _together_count(look, counts[look], day, today)}
                     for look in calendars.LOOKS if look in counts]
            said = "; ".join(c["words"] for c in chips)
            anchor = f"{cal_id}-d-{day.isoformat()}"
            row.append({"day": day.day, "iso": day.isoformat(), "today": day == today, "chips": chips,
                        "anchor": anchor if chips else None,
                        "label": _cell_day(day, style) + (", today" if day == today else "")
                                 + (f": {said}" if said else "")})
            if chips:
                items = []
                for label, words, mark in marks:
                    item = words.item(mark, today, style)
                    items.append({**item, "words": f"{label} · {item['words']}"})
                listed.append({"anchor": anchor, "day": _short_day(day, style) + (" (today)" if day == today else ""),
                               "summary": said, "day_href": None, "marks": items})
        weeks.append(row)
    heading = month_words(year, month)
    summary = (f"{heading} · " + " · ".join(f"{TOGETHER[look]}: {totals[look]}" for look in calendars.LOOKS
                                             if look in totals)
               if totals else f"Nothing recorded or planned in {heading}.")
    prev_y, prev_m = calendars.shift(year, month, -1)
    next_y, next_m = calendars.shift(year, month, 1)
    latest = calendars.shift(today.year, today.month, AHEAD)
    return {"id": cal_id, "title": name, "heading": heading, "name": None, "summary": summary,
            "caption": f"{name}, {heading}",
            "headers": [{"short": DAY_NAMES[i][:3], "long": DAY_NAMES[i]} for i in calendars.weekday_order(first_day)],
            "weeks": weeks, "days": listed, "blank": TOGETHER_BLANK,
            "legend": [{"look": look, "symbol": calendars.SYMBOLS[look], "words": TOGETHER_LEGEND[look]}
                       for look in calendars.LOOKS if look in looks],
            "by_list": [{"label": label, "count": n} for label, n in per_list.items()],
            "prev": link(prev_y, prev_m) if link else None, "prev_words": month_words(prev_y, prev_m),
            "next": link(next_y, next_m) if link and (next_y, next_m) <= latest else None,
            "next_words": month_words(next_y, next_m),
            "this_month": link(today.year, today.month) if link and (year, month) != (today.year, today.month) else None,
            "full": None, "private": False, "show": False, "show_action": None, "subject_id": None,
            "month": f"{year:04d}-{month:02d}", "hide": None}


@calendar_pages.get("/to-do/calendar")
def todo_calendar():
    """Things to do, Calendar: every list with due dates in one month (Routines, Home care, Garden, Vehicles,
    Bills...), done and skipped by the day they happened and each open date once, with Show links that keep one
    module's lists only (decision 0122)."""
    from dashboard.web.checklist import visible_tabs
    store = _store()
    found = sorted(todo_calendar_tables(store.registry), key=lambda i: i.module.title.lower())  # by name, A to Z
    if not found:
        abort(404)
    today = current_app.config["TODAY"]()
    year, month = chosen_month(request.args.get("month"), today)
    by_module: dict[str, dict] = {}
    for info in found:
        by_module.setdefault(info.module.name, {"name": info.module.name, "label": info.module.title, "infos": []})
        by_module[info.module.name]["infos"].append(info)
    only = request.args.get("only")
    if only not in by_module:
        only = None  # an unknown or switched-off module shows everything, never an error
    picked = by_module[only]["infos"] if only else found
    link = _href("/to-do/calendar", only=only)
    if len(picked) == 1:
        view = month_view(store, picked[0], year, month, today, link=link, full_href=f"/calendar/{picked[0].name}")
    else:
        view = together_view(store, picked, year, month, today, link=link,
                             name=f"{by_module[only]['label']} calendar" if only else "Things to do calendar")
    shown = f"{year:04d}-{month:02d}"
    choices = []
    if len(by_module) > 1:  # plain links, no script (decision 0122)
        choices = [{"label": "All", "current": only is None, "href": "/to-do/calendar?" + urlencode({"month": shown})}]
        choices += [{"label": m["label"], "current": only == m["name"],
                     "href": "/to-do/calendar?" + urlencode({"only": m["name"], "month": shown})}
                    for m in by_module.values()]
    return render_template("todo_calendar.html", views=[view], tabs=visible_tabs(store.registry), window="calendar",
                           heading=month_words(year, month), choices=choices)
