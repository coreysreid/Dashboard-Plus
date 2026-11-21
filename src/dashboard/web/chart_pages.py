"""The first charts (decision 0109): what makes up today's days of drinking water, and one pet's recorded weights."""
from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, current_app, render_template, request

from dashboard.core import dates, records, watch
from dashboard.core.schema import target_table
from dashboard.core.units import unit_for
from dashboard.web import charts, display

chart_pages = Blueprint("chart_pages", __name__)

MAX_BARS = 12  # bars drawn at most; every item is always in the table, and the page says when more exist
CAVEAT = "These daily figures are a starting point. Check your local authority's advice."


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _days_text(days: float) -> str:
    value = round(days, 1)
    return f"about {charts.number_text(value)} day{'' if value == 1 else 's'}"


def _who(home: watch.Household) -> str:
    who = f"{home.people} {'person' if home.people == 1 else 'people'}"
    if home.pets:
        who += f" and {home.pets} pet{'' if home.pets == 1 else 's'}"
    return who


def _local_time(stamp: str, style: str) -> str:
    """A stored UTC time as this computer's local date and time, like 21/11/26 14:05."""
    try:
        when = datetime.fromisoformat(stamp).astimezone()
    except ValueError:
        return ""
    return f"{dates.show(when.date(), style)} {when:%H:%M}"


# ----- 1. drinking water counted today ---------------------------------------------------------------------------

def _left_out(row: watch.SupplyRow, supply: watch.Supply) -> str:
    """The exact reason a record adds nothing to the total, or "" when it is counted."""
    if row.status == "not_counted":
        if row.answer is None:
            return f"Left out: not answered whether this is {supply.label}"
        return f"Left out: marked as not {supply.label}"
    if row.status == "wrong_unit":
        return f"Left out: recorded in {(row.unit or '').strip()}, not {supply.unit}"
    if row.status == "no_amount":
        return "Left out: no amount recorded (unknown, not zero)"
    return ""


def _place_column(store: records.Records, info: records.TableInfo):
    """The link column that says where a record is kept: one pointing at a nested table such as Places."""
    for column in info.table.columns.values():
        if column.type == "link" and not column.sensitive:
            target = store.registry.get(target_table(info.module.name, column))
            if target is not None and target.table.parent:
                return column
    return None


def _places(store: records.Records, info: records.TableInfo, formatter: display.Formatter, record_id: int) -> str:
    """Where a record's stock is: the full path of each batch's place that still holds some, else its own place."""
    found = []
    for other in store._totals_into(info):  # batches that add up into this record (DESIGN.md 5.7)
        rule, column = other.table.total, _place_column(store, other)
        if column is None:
            continue
        for (value,) in store.conn.execute(
                f"SELECT DISTINCT {column.name} FROM {other.name} WHERE deleted_at IS NULL AND {rule['link']} = ? "
                f"AND COALESCE({rule['amount']}, 0) > 0 AND {column.name} IS NOT NULL ORDER BY {column.name}",
                (record_id,)):
            text = formatter.text(other, column, value)
            if text and text not in found:
                found.append(text)
    own = _place_column(store, info)
    if not found and own is not None:
        value = store.conn.execute(f"SELECT {own.name} FROM {info.name} WHERE id = ?", (record_id,)).fetchone()[0]
        found = [formatter.text(info, own, value)] if value is not None else []
    return "; ".join(found)


def supply_view(store: records.Records, supply: watch.Supply) -> dict:
    """Everything the drinking-water page shows, from the one `watch.supplies` result Home uses too."""
    info = store.registry[supply.table]
    rule = info.table.watch["supply"]
    formatter = display.Formatter(store)
    style = formatter.date_style
    columns = info.table.columns
    answer_column = columns.get(next(iter(rule.get("counts_only") or {}), ""))
    place_column = _place_column(store, info)
    unit = supply.unit
    rows = []
    for item in supply.items:
        place = _places(store, info, formatter, item.record_id) if place_column is not None else ""
        if item.amount is None:
            amount = "Not recorded"
        else:
            saved = (item.unit or "").strip()
            amount = charts.number_text(item.amount) + (f" {unit_for(item.amount, saved)}" if saved else "")
        answer = ""
        if answer_column is not None:
            answer = formatter.text(info, answer_column, item.answer) or "Not answered"
        if item.status == "counted":
            counted = f"{charts.number_text(item.counted)} {unit_for(item.counted, unit)} counted"
            if item.counted == 0:
                counted += " (recorded as none left)"
        else:
            counted = _left_out(item, supply)
        rows.append({"id": item.record_id, "href": f"/t/{info.name}/{item.record_id}", "name": item.name,
                     "place": place, "amount": amount, "unit": (item.unit or "").strip(), "answer": answer,
                     "counted": counted, "value": item.counted, "is_counted": item.status == "counted"})
    rows.sort(key=lambda r: (-r["value"], r["name"].lower(), r["id"]))
    bars_rows = [r for r in rows if r["is_counted"] and r["value"] > 0]
    total = charts.number_text(supply.total)
    chart_id = f"chart-{info.name}"
    bars = [charts.Bar(r["name"], r["value"], f"{charts.number_text(r['value'])} {unit_for(r['value'], unit)}",
                       f"#{chart_id}-row-{r['id']}") for r in bars_rows[:MAX_BARS]]
    home = supply.household
    where_value = next(iter(rule["where"].values()), "")
    empty = None
    if supply.rows == 0:
        empty = (f"No {supply.label} recorded yet. Add {unit} and answer whether each {where_value} item "
                 f"is safe to drink now.")
    elif not bars_rows:
        empty = f"No {unit} are counted as {supply.label} yet. Check each item's answer and unit."
    counted = f"{total} {unit_for(supply.total, unit)} counted"
    if supply.days is not None:
        headline = (f"{counted} · {_days_text(supply.days)} for {_who(home)} · "
                    f"aim {charts.number_text(supply.target_days)} days")
    elif supply.needs_household:
        headline = f"{counted}. Tell Dashboard Plus how many people live here to work out days."
    else:
        headline = f"{counted}. {supply.working}"
    latest = max((i.updated_at for i in supply.items), default="")
    chart = None
    if bars:
        description = (f"Bars for each item counted as {supply.label}, in {unit}, on a scale starting at 0. "
                       f"Items left out are listed in the table with the reason.")
        chart = charts.bar_chart(chart_id, f"{supply.label.capitalize()} counted now, by item", description, bars,
                                 f"{unit.capitalize()} counted now", unit)
    if home.people is not None:
        people = f"{_who(home)} ({home.source})"
    else:
        people = "people living here: not set yet" + (f"; {home.pets} pet{'' if home.pets == 1 else 's'}"
                                                       if home.pets else "")
    return {"supply": supply, "rows": rows, "chart": chart, "chart_id": chart_id, "empty": empty,
            "headline": headline, "caveat": CAVEAT, "total": total, "unit": unit, "people": people,
            "bar_count": len(bars), "counted_count": len(bars_rows),
            "answer_label": display.column_label(info, answer_column) if answer_column is not None else "",
            "place_label": display.column_label(info, place_column) if place_column is not None else "",
            "latest": _local_time(latest, style) if latest else "",
            "days": _days_text(supply.days) if supply.days is not None else None,
            "title": f"{supply.label.capitalize()} counted today"}


@chart_pages.get("/supplies/<table>")
def supply_page(table):
    store = _store()
    if table not in store.registry or not store.registry[table].table.watch.get("supply"):
        abort(404)
    conn = store.conn
    conn.execute("BEGIN")  # one read: the bars, the left-out list and the total come from the same moment
    try:
        supply = next(s for s in watch.supplies(conn, store.registry) if s.table == table)
        view = supply_view(store, supply)
    finally:
        conn.execute("COMMIT")
    return render_template("supply_chart.html", **view)


# ----- 2. one subject's recorded readings, such as a pet's weigh-ins ---------------------------------------------

def chart_tables(registry: dict, subject: records.TableInfo | None = None) -> list[records.TableInfo]:
    """Tables that declare a dots chart, or only those whose `per` link points at `subject`."""
    found = []
    for info in registry.values():
        rule = info.table.chart
        if not rule:
            continue
        target = target_table(info.module.name, info.table.columns[rule["per"]])
        if target in registry and (subject is None or target == subject.name):
            found.append(info)
    return found


def _changed(store: records.Records, info: records.TableInfo, ids: list[int], watched: tuple[str, ...],
             style: str) -> dict[int, str]:
    """"Corrected on 20/11/26" for a reading whose date or value was changed, "Restored on" for one brought back."""
    marks: dict[int, str] = {}
    if not ids:
        return marks
    holes = ",".join("?" * len(ids))
    for row in store.conn.execute(
            f"SELECT record_id, at, action, after FROM core__audit WHERE table_name = ? AND record_id IN ({holes}) "
            f"AND action IN ('update', 'restore') ORDER BY id", [info.name, *ids]):
        after = row["after"] or ""
        if row["action"] == "update" and not any(f'"{name}"' in after for name in watched):
            continue
        word = "Corrected" if row["action"] == "update" else "Restored"
        marks[row["record_id"]] = f"{word} on {_local_time(row['at'], style).partition(' ')[0]}"
    return marks


def dots_view(store: records.Records, info: records.TableInfo, subject_id: int, start: str | None = None,
              end: str | None = None, chosen_period: bool = False) -> dict:
    """One subject's readings in a date range: the plain sentence, the dots and the equal table."""
    rule = info.table.chart
    columns = info.table.columns
    x, y, per = columns[rule["x"]], columns[rule["y"]], columns[rule["per"]]
    subject_info = store.registry[target_table(info.module.name, per)]
    subject = store.get(subject_info.name, subject_id)
    name = display.display_name(subject_info, subject, store)
    formatter = display.Formatter(store)
    style = formatter.date_style
    unit = y.unit or ""
    what_one, what_many = rule["what"]
    entry_one, entry_many = rule["entry"]
    recorded = store.conn.execute(f"SELECT COUNT(*) FROM {info.name} WHERE deleted_at IS NULL AND {per.name} = ?",
                                  (subject_id,)).fetchone()[0]
    clause, params = "", [subject_id]
    if start:
        clause, params = clause + f" AND {x.name} >= ?", params + [start]
    if end:
        clause, params = clause + f" AND {x.name} <= ?", params + [end]
    found = [dict(r) for r in store.conn.execute(
        f"SELECT id, {x.name} AS day, {y.name} AS value FROM {info.name} WHERE deleted_at IS NULL "
        f"AND {per.name} = ?{clause} ORDER BY {x.name}, id", params)]
    marks = _changed(store, info, [r["id"] for r in found], (x.name, y.name), style)
    chart_id = f"chart-{info.name}-{subject_id}"
    per_day: dict[str, int] = {}
    for r in found:
        per_day[r["day"]] = per_day.get(r["day"], 0) + 1
    seen: dict[str, int] = {}
    rows, dots = [], []
    for r in found:
        seen[r["day"]] = seen.get(r["day"], 0) + 1
        value_text = f"{charts.number_text(r['value'])}{' ' + unit if unit else ''}"
        day_text = dates.show(r["day"], style)
        same = f"reading {seen[r['day']]} of {per_day[r['day']]} that day" if per_day[r["day"]] > 1 else ""
        rows.append({"id": r["id"], "day": day_text, "value": value_text, "same": same, "mark": marks.get(r["id"], ""),
                     "href": f"/t/{info.name}/{r['id']}"})
        dots.append(charts.Dot(date.fromisoformat(r["day"]), float(r["value"]),
                               f"{day_text}: {value_text}" + (f", {same}" if same else ""),
                               f"#{chart_id}-row-{r['id']}"))
    if found:
        first, last = dates.show(found[0]['day'], style), dates.show(found[-1]['day'], style)
        span = f"{first} to {last}" if first != last else f"on {first}"
    else:
        span = ""
    if chosen_period and (start or end):
        period = (f"{dates.show(start, style) if start else 'the first reading'} to "
                  f"{dates.show(end, style) if end else 'the latest reading'}")
    else:
        period = f"all dates ({span})" if span else "all dates"
    empty, note = None, None
    if not recorded:
        empty = f"No {what_many} recorded for {name} yet."
    elif not found:
        empty = f"No {what_many} recorded in this period."
    elif len(found) == 1:
        note = f"One {what_one} recorded. Add another dated reading to compare, if you choose to track this."
    summary = None
    if found:
        last = found[-1]
        summary = (f"{name} · {charts.number_text(last['value'])}{' ' + unit if unit else ''} on "
                   f"{dates.show(last['day'], style)} · {len(found)} {entry_one if len(found) == 1 else entry_many} "
                   f"recorded" + (f" from {period}" if chosen_period and (start or end) else ""))
    chart = None
    if dots:
        description = (f"One dot for each recorded {what_one} of {name}, {span}, in {unit or 'the recorded unit'}, "
                       f"on a scale starting at 0. The dots are not joined. The table lists the same values.")
        chart = charts.dot_chart(chart_id, f"{name}'s recorded {what_many}", description, dots,
                                 display.column_label(info, x), unit, lambda d: dates.show(d, style))
    return {"name": name, "subject_id": subject_id, "table": info.name, "chart": chart, "chart_id": chart_id,
            "rows": rows, "empty": empty, "note": note, "summary": summary, "period": period,
            "heading": f"{name}'s recorded {what_many} · {period}", "x_label": display.column_label(info, x),
            "y_label": display.column_label(info, y) + (f" ({unit})" if unit else ""),
            "entry_one": entry_one, "add": f"/t/{info.name}/new?{per.name}={subject_id}"}


@chart_pages.get("/charts/<table>")
def dots_page(table):
    store = _store()
    info = store.registry.get(table)
    if info is None or not info.table.chart or info not in chart_tables(store.registry):
        abort(404)
    rule = info.table.chart
    subject_info = store.registry[target_table(info.module.name, info.table.columns[rule["per"]])]
    style = dates.household_style(store.conn)
    subjects = [{"id": r["id"], "name": display.display_name(subject_info, r, store)} for r in
                (dict(row) for row in store.conn.execute(f"SELECT * FROM {subject_info.name} WHERE deleted_at IS NULL "
                                                          f"ORDER BY id"))]
    subjects.sort(key=lambda s: (s["name"].lower(), s["id"]))
    title = f"Recorded {rule['what'][1]}"
    if not subjects:
        return render_template("dot_chart.html", title=title, subjects=[], view=None, problems=[],
                               no_subject=f"Add a {rule['subject']} before showing its {rule['what'][0]} history.",
                               add_subject=f"/t/{subject_info.name}/new", table=table, typed={}, style=style)
    wanted = request.args.get("subject", type=int)
    chosen = next((s for s in subjects if s["id"] == wanted), subjects[0])
    typed = {"from": request.args.get("from", "").strip(), "to": request.args.get("to", "").strip()}
    bounds, problems = {}, []
    for key, words in (("from", "From"), ("to", "To")):
        if typed[key]:
            try:
                bounds[key] = dates.parse(typed[key], style)
            except ValueError as problem:
                problems.append(f"{words}: {problem}")
    if bounds.get("from") and bounds.get("to") and bounds["from"] > bounds["to"]:
        problems.append("From must not be after To.")
    if problems:
        bounds = {}  # the page says it shows all dates instead
    view = dots_view(store, info, chosen["id"], bounds.get("from"), bounds.get("to"), chosen_period=bool(bounds))
    return render_template("dot_chart.html", title=title, subjects=subjects, chosen=chosen, view=view,
                           problems=problems, no_subject=None, table=table, typed=typed, style=style,
                           subject_word=rule["subject"], hint=dates.SHORT[style])
