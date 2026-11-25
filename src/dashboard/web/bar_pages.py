"""Bars over time (decision 0124): how often, or how much in one unit, per day, week or month, drawn on the server with the same values in a table and in words."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, render_template, request

from dashboard.core import bars, daily, dates, records
from dashboard.core.checklist import week_start
from dashboard.core.schema import target_table
from dashboard.web import charts, display

bar_pages = Blueprint("bar_pages", __name__)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BY_WORDS = {"day": "By day", "week": "By week", "month": "By month"}
PRIVATE_WORDS = "Private history — press Show to see each one on its own."


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def bar_rules(registry: dict, subject=None) -> list[tuple]:
    """Every (table, bars rule) whose `per` table is switched on, or only those pointing at `subject`. A chart of
    every record of a table together (no `per`, decision 0129) is never a panel on one record's page."""
    found = []
    for info in registry.values():
        for rule in info.table.bars:
            if not rule.get("per"):
                if subject is None:
                    found.append((info, rule))
                continue
            target = target_table(info.module.name, info.table.columns[rule["per"]])
            if target in registry and (subject is None or target == subject.name):
                found.append((info, rule))
    return found


def _find(registry: dict, table: str, key: str):
    return next(((info, rule) for info, rule in bar_rules(registry) if info.name == table and rule["key"] == key),
                (None, None))


def today_for(store: records.Records, info, rule) -> date:
    """Today by the household's time zone for timed entries (decision 0110), else the computer's date, as the
    calendars read it (decision 0119)."""
    if info.table.columns[rule["when"]].type == "datetime":
        clock = current_app.config.get("NOW")
        return daily.today(store.conn, clock() if clock else datetime.now(timezone.utc))
    return current_app.config["TODAY"]()


def _short(day: date, by: str, style: str) -> str:
    """The name drawn beside a bar: "Tue 17 Nov", "From 16 Nov", "Nov 2026" (month first where dates are)."""
    month = dates.MONTHS[day.month - 1][:3]
    if by == "month":
        return f"{month} {day.year}"
    when = f"{month} {day.day}" if style == dates.MONTH_FIRST else f"{day.day} {month}"
    return f"{DAY_NAMES[day.weekday()][:3]} {when}" if by == "day" else f"From {when}"


def _full(period: bars.Period, by: str, style: str) -> str:
    """The period in full words: "Tuesday 17/11/26", "Week from 16/11/26 to 22/11/26", "November 2026"."""
    if by == "day":
        return f"{DAY_NAMES[period.start.weekday()]} {dates.show(period.start, style)}"
    if by == "week":
        return f"Week from {dates.show(period.start, style)} to {dates.show(period.end, style)}"
    return f"{dates.MONTHS[period.start.month - 1]} {period.start.year}"


def _entries(n: int, rule: dict) -> str:
    one, many = rule["entry"]
    return f"{n:,} {one if n == 1 else many}"


def _amount(value: Decimal, unit: str) -> str:
    """"1,680 g", "2 pouches": an amount in its own unit, with thousands separators."""
    words = daily.amount_words(value, unit)
    number, _, rest = words.partition(" ")
    whole, dot, part = number.partition(".")
    return f"{int(whole):,}{dot}{part} {rest}".strip() if whole.lstrip("-").isdigit() else words


def _and(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def group_name(store: records.Records, info, rule: dict, group_id: int, show: bool) -> str:
    """What one group's bars are called: its linked record's name; for a private table only after Show, its own
    private words (a medication detail as the household wrote it), otherwise never anything it holds."""
    column = info.table.columns[rule["group"]]
    target = store.registry.get(target_table(info.module.name, column))
    if target is None:
        return f"{display.column_label(info, column)} #{group_id}"
    if not info.table.private:
        return display.Formatter(store).text(info, column, group_id)
    kind = " ".join(next((c.label for c in target.table.columns[k].choices if c.key == v), v)
                    for k, v in column.link_rule.get("where", {}).items() if k in target.table.columns)
    plain = f"{kind or display.column_label(info, column)} #{group_id}"
    shows = column.link_rule.get("shows")
    if not show or not shows or shows not in target.table.columns:
        return plain
    row = store.conn.execute(f"SELECT {shows} FROM {target.name} WHERE id = ?", (group_id,)).fetchone()
    return f"{row[0]} ({plain})" if row and row[0] else plain


def _link(info, rule: dict, subject_id: int | None, **args) -> str:
    return f"/bars/{info.name}/{rule['key']}?" + urlencode(
        {k: v for k, v in dict(subject=subject_id, **args).items() if v not in (None, "")})


def table_panels(store: records.Records, info) -> list[dict]:
    """The bars of every record of one table together (no `per`, decision 0129), such as Garden's jobs done per
    month: shown on that table's own calendar page."""
    return [bars_view(store, info, rule, None, panel=True) for rule in info.table.bars if not rule.get("per")]


def table_links(info) -> list[dict]:
    """Links from a table's list to its whole-table bars (decision 0129): "Jobs done per month"."""
    return [{"href": f"/bars/{info.name}/{rule['key']}", "words": f"{rule['title']} per {rule['by'][0]}"}
            for rule in info.table.bars if not rule.get("per")]


def bars_view(store: records.Records, info, rule: dict, subject_id: int | None, by: str | None = None,
              end: date | None = None, unit: str | None = None, show: bool = False, group_id: int | None = None,
              panel: bool = False) -> dict:
    """Everything one bars chart shows: the plain sentence, the bars and the equal table, for one subject's periods
    ending with the one that holds `end` (today when missing or later). A sum is in one unit at a time, the latest
    entry's unless another is chosen; other units and entries with no amount are said, never added in. A private
    table (decision 0121) gives counts only, and each group's own bars only after a pressed Show."""
    by = by if by in rule["by"] else rule["by"][0]
    today = today_for(store, info, rule)
    last_day = min(end or today, today)
    style = dates.household_style(store.conn)
    found = bars.build(store.conn, info, rule, subject_id, by, last_day, week_start(store.conn), today, group_id,
                       registry=store.registry)
    if rule.get("per"):
        subject_info = store.registry[target_table(info.module.name, info.table.columns[rule["per"]])]
        name = display.display_name(subject_info, store.get(subject_info.name, subject_id), store)
    else:  # every record of the table together (decision 0129): the chart is named by the list itself
        name = display.table_title(info)
    is_sum = rule["measure"] == "sum"
    units = bars.units(rule, found) if is_sum else []
    chosen = unit if unit in units else (units[0] if units else "")
    chart_id = f"bars-{info.name}-{rule['key']}-{subject_id}" + (f"-g{group_id}" if group_id is not None else "")
    smaller = {"week": "day", "month": "week" if "week" in rule["by"] else "day"}.get(by)
    total_n = sum(p.count for p in found)
    total, added, unmeasured, others = Decimal(0), 0, 0, {}
    rows, drawn = [], []
    daily_page = bool(info.table.daily) and bool(rule.get("per")) and info.table.daily["per"] == rule["per"] \
        and group_id is None
    for period in found:
        n = period.count
        full = _full(period, by, style) + (" (so far)" if period.so_far else "")
        details, value = [], None
        if is_sum:
            part = bars.amounts(rule, period, chosen)
            total, added, unmeasured = total + part.total, added + part.added, unmeasured + part.unmeasured
            for other, amount in part.others.items():
                others[other] = others.get(other, Decimal(0)) + amount
            if part.added:
                value, text = float(part.total), _amount(part.total, chosen)
                said = f"{text} {rule['verb']}"
            elif n:
                text = said = "no amount recorded" if not part.others else f"none in {chosen}"
            else:
                text, said = "nothing recorded", "Nothing recorded"
            if n:
                details.append(f"{_entries(n, rule)} recorded")
            if part.unmeasured:
                details.append(f"{part.unmeasured} with no amount")
            if part.others:
                details.append("also " + _and([_amount(v, u) for u, v in part.others.items()]) + ", not in this chart")
        else:
            value = float(n) if n else None
            text = f"{n:,}" if n else "nothing recorded"
            said = f"{_entries(n, rule)} recorded" if n else "Nothing recorded"
        href = None
        if group_id is not None:
            pass  # one group's rows sit under the whole chart, whose rows carry the links
        elif n and by == "day" and daily_page:
            href = f"/daily/{info.name}?" + urlencode({"subject": subject_id, "day": period.start.isoformat()})
            link_words = "See this day"
        elif n and smaller in rule["by"]:
            href = _link(info, rule, subject_id, by=smaller, end=period.end.isoformat(), unit=chosen or None)
            link_words = f"See {'these days' if smaller == 'day' else 'these weeks'}"
        row_id = f"{chart_id}-row-{period.start.isoformat()}"
        rows.append({"id": row_id, "period": full, "value": said, "details": " · ".join(details),
                     "href": href, "link_words": link_words if href else "", "empty": not n})
        drawn.append(charts.PeriodBar(_short(period.start, by, style), full, value, text, f"#{row_id}",
                                      period.so_far))
    first, last = found[0], found[-1]
    span_end = "today" if last.so_far else dates.show(last.end, style)
    span = f"{len(found)} {by}s, {dates.show(first.start, style)} to {span_end}"
    one, many = rule["entry"]
    if rule.get("history"):  # any done day up to today, earlier ones from history included (decision 0129)
        recorded = bool(total_n) or bool(bars.done_days(store.conn, store.registry, info, rule, subject_id,
                                                        date(1900, 1, 1), today))
    else:
        recorded = store.conn.execute(
            f"SELECT 1 FROM {info.name} WHERE deleted_at IS NULL AND review_status = 'confirmed'"
            + (f" AND {rule['per']} = ?" if rule.get("per") else "")
            + "".join(f" AND {c} = ?" for c in rule["where"])
            + (f" AND {rule['group']} = ?" if group_id is not None else "") + " LIMIT 1",
            [*([subject_id] if rule.get("per") else []), *rule["where"].values(),
             *([group_id] if group_id is not None else [])]).fetchone()
    empty, notes = None, []
    if not recorded:
        empty = f"No {many} recorded for {name} yet."
    elif not total_n:
        empty = f"Nothing recorded for {name} in these {span}."
    if is_sum and total_n:
        if added:
            summary = (f"{name} · {span} · {_amount(total, chosen)} {rule['verb']}, from "
                       f"{_entries(added, rule)}")
        else:
            summary = f"{name} · {span} · {_entries(total_n, rule)} recorded; amounts not measured"
        if unmeasured:
            notes.append(f"{_entries(unmeasured, rule)} {'has' if unmeasured == 1 else 'have'} no amount, so "
                         f"{'it is' if unmeasured == 1 else 'they are'} counted but not added.")
        if others:
            notes.append(f"Also recorded in another unit, not added and never converted: "
                         f"{_and([_amount(v, u) for u, v in others.items()])}.")
    else:
        summary = f"{name} · {span} · {_entries(total_n, rule)} recorded"
    unit_links = [{"words": f"In {u}", "current": u == chosen,
                   "href": _link(info, rule, subject_id, by=by, end=None if last.so_far else last.end.isoformat(),
                                 unit=u)} for u in units] if len(units) > 1 else []
    keep_end = None if last.so_far else last.end.isoformat()
    by_links = [{"words": BY_WORDS[b], "current": b == by,
                 "href": _link(info, rule, subject_id, by=b, end=keep_end, unit=chosen or None)}
                for b in rule["by"]] if len(rule["by"]) > 1 else []
    earlier = _link(info, rule, subject_id, by=by, end=(first.start - timedelta(days=1)).isoformat(),
                    unit=chosen or None)
    later = None
    if not last.so_far:
        ahead = last.end + timedelta(days=(last.end - first.start).days + 1)
        later = _link(info, rule, subject_id, by=by, end=None if ahead >= today else ahead.isoformat(),
                      unit=chosen or None)
    if group_id is not None:  # one group's bars sit under the whole chart and move with its links
        by_links, unit_links, earlier, later = [], [], None, None
    title = f"{rule['title']} per {by}" + (f" in {chosen}" if is_sum and chosen else "")
    unit_words = chosen if is_sum else ""
    axis = (f"{rule['title']} ({chosen})" if is_sum and chosen else f"{many[:1].upper()}{many[1:]} recorded")
    caption = (f"One bar for each {by}, oldest at the top, on a scale starting at 0. A striped bar is the {by} "
               f"still going on, so far. A {by} with no bar has nothing to add up; it does not mean anything was "
               f"missed. Choose a bar to go to its row.")
    chart = None
    if any(b.value for b in drawn):
        description = (f"{title} for {name}, {span}: one bar for each {by}"
                       + (f", in {chosen} only" if is_sum else "") + ", on a scale starting at 0. "
                       "The table lists the same values.")
        chart = charts.period_chart(chart_id, f"{name}: {title.lower()}" if not panel else title, description,
                                    drawn, axis, unit_words, whole=not is_sum)
    caveat = " ".join(c for c in (rule.get("caveat"), (
        "Each bar adds up the amounts written down, in one unit only; other units are never converted or added in."
        if is_sum else "Each bar counts the days each was recorded as done, earlier ones from each one's history; "
                       "a date typed back or cleared is never counted." if rule.get("history")
        else "Each bar counts the entries written down.")
        + " A period with nothing recorded only means nothing was written down.") if c)
    groups = []
    private = info.table.private
    if rule.get("group") and group_id is None and total_n and (show or not private):
        ids = sorted({e[rule["group"]] for p in found for e in p.entries if e.get(rule["group"]) is not None})
        for gid in ids:
            part = bars_view(store, info, rule, subject_id, by, last_day, chosen or None, show, gid, panel=True)
            part["name"] = group_name(store, info, rule, gid, show)
            groups.append(part)
        groups.sort(key=lambda g: g["name"].lower())
    return {"id": chart_id, "table": info.name, "key": rule["key"], "title": title, "name": name,
            "subject_id": subject_id, "by": by, "end": keep_end or "", "unit": chosen, "summary": summary,
            "notes": notes, "empty": empty, "caveat": caveat, "chart": chart, "caption": caption, "rows": rows,
            "heading": f"{rule['title']} for {name} · {span}", "value_label": (
                f"{rule['title']} ({chosen})" if is_sum and chosen else f"{many[:1].upper()}{many[1:]}"),
            "by_links": by_links, "unit_links": unit_links, "earlier": earlier, "later": later,
            "today_href": _link(info, rule, subject_id, by=by, unit=chosen or None) if later else None,
            "full": _link(info, rule, subject_id) if panel and group_id is None else None,
            "private": private, "show": show, "private_words": PRIVATE_WORDS,
            "can_show": private and bool(rule.get("group")) and not show and bool(total_n),
            "show_action": f"/bars/{info.name}/{rule['key']}", "groups": groups,
            "group_title": (f"Each {display.column_label(info, info.table.columns[rule['group']]).lower()} on its own"
                            if rule.get("group") else None),
            "hide": (_link(info, rule, subject_id, by=by, end=keep_end, unit=chosen or None)
                     if show and group_id is None else None)}


def _applies(store: records.Records, info, subject_id: int) -> bool:
    """Whether a subject has this chart: always, except a private log that does not apply to them (0120), as for
    its calendar: a neighbour with no medication detail and no doses gets no dose bars."""
    if info.table.private and info.table.daily and info.table.daily.get("group"):
        from dashboard.web import private_daily
        return private_daily.applies(store, info, subject_id)
    return True


def record_panels(store: records.Records, subject_info, record: dict) -> list[dict]:
    """On a record's own page (a pet, a person, a routine): each bars chart of its records, by its first period."""
    return [bars_view(store, info, rule, record["id"], panel=True)
            for info, rule in bar_rules(store.registry, subject_info) if _applies(store, info, record["id"])]


def _end(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


@bar_pages.get("/bars/<table>/<key>")
def bars_page(table, key):
    return _bars_page(table, key, show=False)


@bar_pages.post("/bars/<table>/<key>")
def show_bars_page(table, key):
    """Show on a private table's bars (decision 0121): a pressed button with the session check, never an address,
    so no bookmark or shared link opens each group's own bars. Other tables have nothing to show."""
    info, _ = _find(_store().registry, table, key)
    if info is None or not info.table.private:
        abort(404)
    return _bars_page(table, key, show=True)


def _bars_page(table, key, show: bool):
    store = _store()
    info, rule = _find(store.registry, table, key)
    if info is None:
        abort(404)
    if not rule.get("per"):  # every record of the table together (decision 0129): no one to choose
        view = bars_view(store, info, rule, None, request.values.get("by"), _end(request.values.get("end")))
        return render_template("bars.html", title=rule["title"], view=view, subjects=[],
                               chosen={"id": None, "name": view["name"]}, rule=rule, no_subject=None,
                               subject_href=None, list_href=f"/t/{info.name}")
    subject_info = store.registry[target_table(info.module.name, info.table.columns[rule["per"]])]
    rows = [dict(r) for r in store.conn.execute(f"SELECT * FROM {subject_info.name} WHERE deleted_at IS NULL "
                                                 f"ORDER BY id")]
    subjects = sorted(({"id": r["id"], "name": display.display_name(subject_info, r, store)} for r in rows
                       if _applies(store, info, r["id"])), key=lambda s: (s["name"].lower(), s["id"]))
    if not subjects:
        return render_template("bars.html", title=rule["title"], view=None, subjects=[], chosen=None, rule=rule,
                               add_subject=f"/t/{subject_info.name}/new",
                               no_subject=f"Add a {rule['subject']} before showing its {rule['title'].lower()}.")
    wanted = request.values.get("subject", type=int)
    chosen = next((s for s in subjects if s["id"] == wanted), subjects[0])
    view = bars_view(store, info, rule, chosen["id"], request.values.get("by"), _end(request.values.get("end")),
                     request.values.get("unit"), show=show)
    return render_template("bars.html", title=rule["title"], view=view, subjects=subjects, chosen=chosen, rule=rule,
                           no_subject=None, subject_href=f"/t/{subject_info.name}/{chosen['id']}",
                           list_href=f"/t/{info.name}")
