"""Things to do: the Today, This week, This month, This year and No date yet pages, each row with its record's own action."""
from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, current_app, render_template, request

from dashboard.core import actions, checklist, dates, records
from dashboard.web import display
from dashboard.web.action_form import done_notice

checklist_pages = Blueprint("checklist", __name__)
# Address, tab words and the words when nothing is in the view. Empty words never say all work is done.
TABS = [("today", "/to-do", "Today"), ("week", "/to-do/week", "This week"), ("month", "/to-do/month", "This month"),
        ("year", "/to-do/year", "This year"), ("undated", "/to-do/no-date", "No date yet")]
EMPTY = {"today": "Nothing is due or late from the dates you recorded. This does not mean every household task "
                  "is done.",
         "week": "Nothing is due or late this week from the dates you recorded. This does not mean every household "
                 "task is done.",
         "month": "No recorded dates fall in this month. Add a date to a task you want to see here.",
         "year": "No dated work is recorded for this year.",
         "undated": "Every task in these lists has a date recorded."}
CHANGED = "This task changed while you were looking at it. Check the current date and try again. Nothing was saved."
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SHORT_MONTHS = [m[:3] for m in dates.MONTHS]
# A reminder's `what` that adds nothing to "Due" for a task's own name ("job", "routine").
GENERIC_WHAT = ("job", "routine", "")


def _registry():
    return current_app.config["REGISTRY_FOR_REQUEST"]()


def _day(when: date, style: str, month: bool = True) -> str:
    """"Mon 16 Nov" (or "Mon Nov 16" where dates are written month first); without the month: "Mon 16"."""
    if not month:
        return f"{DAYS[when.weekday()]} {when.day}"
    if style == dates.MONTH_FIRST:
        return f"{DAYS[when.weekday()]} {SHORT_MONTHS[when.month - 1]} {when.day}"
    return f"{DAYS[when.weekday()]} {when.day} {SHORT_MONTHS[when.month - 1]}"


def week_range(start: date, end: date, style: str) -> str:
    """"Mon 16–Sun 22 Nov" for a week inside one month, "Mon 30 Nov–Sun 6 Dec" across two."""
    if style != dates.MONTH_FIRST and start.month == end.month:
        return f"{_day(start, style, month=False)}–{_day(end, style)}"
    return f"{_day(start, style)}–{_day(end, style)}"


def _source_word(task_source, all_sources) -> str:
    """Where a row comes from: the module ("Home care"), or the list when a module has several ("Insurance")."""
    module = task_source.info.module
    if sum(1 for s in all_sources if s.info.module.name == module.name) > 1:
        return display.table_title(task_source.info)
    return module.title


def _context(formatter, info, row) -> str | None:
    """The place or record a row belongs to: a link to one of the household's Places first, else the first link."""
    links = [c for c in info.table.columns.values() if c.type == "link" and not c.sensitive and row.get(c.name)]
    if not links:
        return None
    chosen = next((c for c in links if c.to == "stock.places"), links[0])
    return formatter.text(info, chosen, row.get(chosen.name)) or None


def _row_actions(task, back: str) -> list[dict]:
    """The record's own ways to finish it: its Mark done form (and Skip this time), its one-step button that ends
    the reminder, or else a link to open the record. Nothing here ticks anything by itself."""
    info, row = task.source.info, task.row
    shown = []
    for action in info.table.actions:
        if not all(row.get(k) == v for k, v in action["show_when"].items()):
            continue
        label = display.action_words(info, action)[0]
        href = f"/t/{info.name}/{row['id']}/do/{action['key']}"
        if action.get("adds"):
            shown.append({"label": label, "href": f"{href}?back={back}", "post": False,
                          "quiet": action.get("counts_as") == "skipped"})
        elif action in task.source.presses:
            shown.append({"label": label, "href": href, "post": True, "quiet": False})
    if not shown:
        shown.append({"label": "Open record to update", "href": f"/t/{info.name}/{row['id']}", "post": False,
                      "quiet": True})
    shown.sort(key=lambda a: a["quiet"])
    return shown


def _when(task, style: str) -> str:
    """"Due since 18/11/26", "Due today" or "Due 25/11/26", naming what is due when the list says ("Kit check due")."""
    if task.due is None:
        return "No date yet"
    what = task.what or task.source.what
    due = f"{what[:1].upper()}{what[1:]} due" if what and what not in GENERIC_WHAT else "Due"
    if task.group in ("late", "earlier"):
        return f"{due} since {dates.show(task.due, style)}"
    if task.group == "today":
        return f"{due} today"
    return f"{due} {dates.show(task.due, style)}"


def _view(window: str):
    conn = current_app.config["CONNECT"]()
    registry = _registry()
    store = records.Records(conn, registry)
    today = current_app.config["TODAY"]()
    style = dates.household_style(conn)
    first_day = checklist.week_start(conn)
    all_sources = checklist.sources(registry)
    only = request.args.get("only")
    if only not in {s.info.name for s in all_sources}:
        only = None
    path = next(p for k, p, _ in TABS if k == window)
    formatter = display.Formatter(store)
    found = checklist.tasks(conn, registry, window, today, first_day, only)
    rows = [{"name": t.name, "source": _source_word(t.source, all_sources), "group": t.group, "due": t.due,
             "context": _context(formatter, t.source.info, t.row), "when": _when(t, style),
             "late": t.group in ("late", "earlier"), "actions": _row_actions(t, path),
             "href": f"/t/{t.source.info.name}/{t.row['id']}"} for t in found]
    start, end = checklist.bounds(window, today, first_day) if window != "undated" else (None, None)
    groups = _groups(window, rows, today, start, end, first_day, style)
    finished = []
    if window != "undated" and window != "year":
        for entry in checklist.done(conn, registry, start, end, only):
            action = next((a for a in entry.source.info.table.actions if a["key"] == entry.key), None)
            label = display.undo_word(entry.source.info, action)
            can = label and actions.can_undo(store, entry.source.info, entry.record_id, entry.operation)
            finished.append({"name": entry.name, "source": _source_word(entry.source, all_sources),
                             "skipped": entry.counts_as == "skipped", "on": dates.show(entry.on, style),
                             "planned": dates.show(entry.planned, style) if entry.planned else None,
                             "missed": entry.missed, "href": f"/t/{entry.source.info.name}/{entry.record_id}",
                             "undo": {"label": label, "href": f"/t/{entry.source.info.name}/{entry.record_id}"
                                                               f"/undo/{entry.operation}"} if can else None})
    months = None
    if window == "year":
        months = [dict(m, name=dates.MONTHS[m["month"] - 1])
                  for m in checklist.by_month(conn, registry, today.year, only)]
    notice = _notice(store, registry)
    open_count = sum(1 for r in rows if r["group"] in ("late", "earlier", "today") or
                     (window not in ("today", "undated") and r["group"] == "later"))
    if window == "year":
        heading = str(today.year)
    elif window == "month":
        heading = f"{dates.MONTHS[today.month - 1]} {today.year}"
    elif window == "week":
        heading = week_range(start, end, style)
    elif window == "today":
        heading = dates.long(today, style)
    else:
        heading = "Tasks in lists that keep a due date, with no date recorded yet"
    return render_template("checklist.html", window=window, tabs=TABS, path=path, groups=groups, rows=rows,
                           finished=finished, months=months, notice=notice, heading=heading, empty=EMPTY[window],
                           open_count=open_count, only=only,
                           filters=[{"name": s.info.name, "title": _source_word(s, all_sources)} for s in all_sources],
                           has_sources=bool(all_sources), changed=request.args.get("changed") == "1",
                           first_day=first_day.capitalize())


def _groups(window, rows, today, start, end, first_day, style) -> list[dict]:
    """The rows in the draft's order: still to decide, late, today, then later (by week in a month)."""
    words = {"earlier": "Still to decide (from an earlier year)", "late": "Late", "today": "Today",
             "undated": "No date yet",
             "later": {"week": "Later this week", "year": "Coming up this year"}.get(window, "Later this month")}
    groups = []
    for key in ("earlier", "late", "today", "undated"):
        chosen = [r for r in rows if r["group"] == key]
        if chosen:
            groups.append({"title": words[key], "rows": chosen, "key": key})
    later = [r for r in rows if r["group"] == "later"]
    if later and window == "month":
        by_week: dict[date, list] = {}
        for row in later:
            week, _ = checklist.bounds("week", row["due"], first_day)
            by_week.setdefault(week, []).append(row)
        for week, chosen in by_week.items():
            last = min(week + timedelta(days=6), end)
            groups.append({"title": f"Week of {week_range(max(week, start), last, style)}", "rows": chosen,
                           "key": "later"})
    elif later:
        groups.append({"title": words["later"], "rows": later, "key": "later"})
    return groups


def _notice(store, registry) -> dict | None:
    """What was just saved from this page: a Mark done notice (with Undo while it is safe) or a button's words."""
    table, record = request.args.get("table"), request.args.get("record", "")
    if table not in registry or not record.isdecimal() or not record.isascii():
        return None
    info = registry[table]
    op, pressed = request.args.get("op"), request.args.get("pressed")
    if op:
        return done_notice(store, info, int(record), op)
    words = display.done_words(info, pressed)
    return {"words": words, "undo": None} if words else None


@checklist_pages.get("/to-do")
def today_page():
    """Today: what is due today, and each late task once as "Due since"."""
    return _view("today")


@checklist_pages.get("/to-do/week")
def week_page():
    return _view("week")


@checklist_pages.get("/to-do/month")
def month_page():
    return _view("month")


@checklist_pages.get("/to-do/year")
def year_page():
    return _view("year")


@checklist_pages.get("/to-do/no-date")
def undated_page():
    return _view("undated")


def home_summary(conn, registry, today: date) -> dict | None:
    """The Home card: how many tasks are due or late today and this week, or None when no list keeps a due date."""
    if not checklist.sources(registry):
        return None
    first_day = checklist.week_start(conn)
    found = checklist.tasks(conn, registry, "week", today, first_day)
    return {"today": sum(1 for t in found if t.group in ("late", "today")), "week": len(found)}
