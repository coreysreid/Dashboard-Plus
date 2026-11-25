"""One record's timeline (decision 0126): "What happened, newest first", by month, a symbol and words per kind, Earlier by server links, and private entries only as counts until a pressed Show."""
from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, render_template, request

from dashboard.core import daily, dates, records, timeline
from dashboard.core.modules import TIMELINE_WORD
from dashboard.core.schema import target_table
from dashboard.web import display
from dashboard.web.calendar_pages import _short_day
from dashboard.web.chart_pages import change_words
from dashboard.web.daily_pages import clock_text

timeline_pages = Blueprint("timeline_pages", __name__)

TITLE = "What happened, newest first"
CAVEAT = ("Only what was written down and accepted is listed. A gap only means nothing was recorded; it does not "
          "mean anything was missed.")
PRIVATE_WORDS = "Private history — press Show to see what each one was, on that page only."


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _upper(words: str) -> str:
    return words[:1].upper() + words[1:]


def _since(day: date, than: date, style: str) -> str:
    """"2 Oct" (or "Oct 2" where dates are month first), with the year when it is not the same year."""
    month = dates.MONTHS[day.month - 1][:3]
    words = f"{month} {day.day}" if style == dates.MONTH_FIRST else f"{day.day} {month}"
    return words if day.year == than.year else f"{words} {day.year}"


def change_since(info, rule: dict, item: timeline.Item, style: str) -> str | None:
    """"up 0.3 kg since 2 Oct, from 4.4 kg to 4.7 kg": decision 0119's change words, since the entry before of the
    same kind. Only a fixed unit is compared (the checker makes sure), so never across units."""
    row, before = item.rows[0], item.previous
    column = info.table.columns[rule["change"]]
    if before is None or row.get(column.name) is None:
        return None
    unit = column.unit
    if rule.get("change_unit"):  # each entry says its own unit (decision 0130): never compared across units
        unit_column = info.table.columns[rule["change_unit"]]
        if row.get(unit_column.name) != before.get(unit_column.name):
            return None
        unit = next((c.label for c in unit_column.choices if c.key == row.get(unit_column.name)), "")
    words = change_words(column, {"value": before[column.name]}, {"value": row[column.name]}, unit)
    when = _since(before["_day"], item.day, style)
    if words.startswith("no change"):
        return f"no change since {when}{words[len('no change'):]}"
    head, _, rest = words.partition(", ")
    return f"{head} since {when}, {rest}"


def _private_link(store: records.Records, info, column, value) -> str:
    """A private table's link after Show: the linked record's private words where its `link_rule` says which, as
    the household wrote them ("Ibuprofen 200 mg"), with no id. Only when two of that person's records of the same
    kind have the same words does it say which one: "(1 of 2 with the same words)", by the order they were added
    (decision 0130). Otherwise the link's ordinary name."""
    target = store.registry.get(target_table(info.module.name, column))
    shows = column.link_rule.get("shows")
    if target is None or not shows or shows not in target.table.columns:
        return display.Formatter(store).text(info, column, value)
    own = store.conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (value,)).fetchone()
    words = " ".join(str(own[shows] or "").split()) if own is not None else ""
    if own is None or not words:
        kind = " ".join(next((c.label for c in target.table.columns[k].choices if c.key == v), v)
                        for k, v in column.link_rule.get("where", {}).items() if k in target.table.columns)
        return f"{kind or display.column_label(info, column)} with no words written"
    same = {k: own[k] for k in (*column.link_rule.get("where", {}), *column.link_rule.get("same", {}).keys())
            if k in target.table.columns}
    clause = "".join(f" AND {k} = ?" if v is not None else f" AND {k} IS NULL" for k, v in same.items())
    rows = store.conn.execute(f"SELECT id, {shows} FROM {target.name} WHERE deleted_at IS NULL{clause} ORDER BY id",
                              [v for v in same.values() if v is not None]).fetchall()
    twins = [r[0] for r in rows if " ".join(str(r[1] or "").split()).casefold() == words.casefold()]
    if len(twins) > 1 and value in twins:
        return f"{words} ({twins.index(value) + 1} of {len(twins)} with the same words)"
    return words


def fill(store: records.Records, formatter: display.Formatter, info, rule: dict, row: dict) -> str:
    """The declared words with each {column} as a person reads it; an empty value leaves its words out."""
    def one(match) -> str:
        column = info.table.columns[match.group(1)]
        value = row.get(column.name)
        if value in (None, ""):
            return ""
        if info.table.private and column.type == "link":
            return _private_link(store, info, column, value)
        if column.name == rule.get("change") and column.type == "integer":
            return f"{int(value):,}"  # a reading reads like its change: 49,740 (decision 0130)
        return formatter.text(info, column, value)
    words = TIMELINE_WORD.sub(one, rule["words"]).strip()
    named = TIMELINE_WORD.findall(rule["words"])
    if named and not any(row.get(m) not in (None, "") for m in named):
        return ""  # "by {done_by}" with nobody named says nothing, not "by"
    return words.strip(" ·:,") if words else ""


def _line(store: records.Records, formatter: display.Formatter, item: timeline.Item, style: str,
          subject_id: int, show: bool) -> dict:
    info, rule = item.info, item.rule
    one, many = rule["entry"]
    line = {"look": rule["look"], "symbol": timeline.SYMBOLS[rule["look"]], "kind": None, "when": None,
            "words": "", "change": None, "href": None, "link_words": "", "label": "", "entries": [],
            "private": info.table.private, "id": f"tl-{info.name}-{item.rows[-1]['id']}"}
    if rule.get("summarise") == "day":
        n = len(item.rows)
        said = f"{n:,} {one if n == 1 else many} recorded on {_short_day(item.day, style)}"
        daily_rule = info.table.daily
        same = bool(daily_rule) and daily_rule["per"] == rule["per"] and daily_rule["when"] == rule["when"]
        if same and not info.table.private:  # food put out by unit, never added across units (decision 0110)
            result = daily.add_up(daily_rule, item.day.isoformat(), item.rows)
            if result.totals:
                said += " · " + daily.totals_words(daily_rule, result)
        line["words"] = said
        if same:
            line["href"] = f"/daily/{info.name}?" + urlencode({"subject": subject_id, "day": item.day.isoformat()})
            line["link_words"], line["label"] = "See this day", f"See {many} on {_short_day(item.day, style)}"
        if info.table.private and show:
            for row in item.rows:
                clock = clock_text(row["_local"]) if row["_local"] is not None else ""
                words = fill(store, formatter, info, rule, row) if rule["words"] else one
                line["entries"].append(" · ".join(w for w in (clock, words) if w))
        return line
    row = item.rows[0]
    line["kind"] = _upper(one)
    line["when"] = _short_day(item.day, style) + (f" · {clock_text(item.moment)}" if item.moment else "")
    line["words"] = fill(store, formatter, info, rule, row) if rule["words"] else ""
    if rule.get("change"):
        line["change"] = change_since(info, rule, item, style)
    line["href"], line["link_words"] = f"/t/{info.name}/{row['id']}", "Open"
    line["label"] = f"Open this {one}, {_short_day(item.day, style)}"
    return line


def _link(subject, subject_id: int, before: date | None = None) -> str:
    return f"/timeline/{subject.name}/{subject_id}" + (f"?before={before.isoformat()}" if before else "")


def timeline_view(store: records.Records, subject, subject_id: int, before: date | None = None,
                  show: bool = False, panel: bool = False) -> dict:
    """One page of a record's timeline: lines newest first under month headings, Earlier as a link, the empty
    words, and for private entries the counts only, until a pressed Show on the full page."""
    style = dates.household_style(store.conn)
    found = timeline.items(store.conn, store.registry, subject, subject_id)
    shown, earlier = timeline.page(found, before, timeline.PANEL if panel else timeline.PAGE)
    name = display.display_name(subject, store.get(subject.name, subject_id), store)
    formatter = display.Formatter(store)
    months = []
    for item in shown:
        key = f"{item.day.year:04d}-{item.day.month:02d}"
        if not months or months[-1]["key"] != key:
            months.append({"key": key, "heading": f"{dates.MONTHS[item.day.month - 1]} {item.day.year}",
                           "lines": []})
        months[-1]["lines"].append(_line(store, formatter, item, style, subject_id, show))
    empty = None
    if not found:
        empty = f"Nothing recorded yet for {name}."
    elif not shown:
        empty = f"Nothing recorded for {name} before {dates.show(before, style)}."
    private = any(line["private"] for month in months for line in month["lines"])
    view_id = f"timeline-{subject.name}-{subject_id}"
    return {"id": view_id, "title": TITLE, "name": name, "months": months, "empty": empty, "caveat": CAVEAT,
            "earlier": _link(subject, subject_id, earlier) if earlier else None,
            "newest": _link(subject, subject_id) if before and not panel else None,
            "full": _link(subject, subject_id) if panel and found else None,
            "private": private, "show": show, "can_show": private and not show, "private_words": PRIVATE_WORDS,
            "show_action": _link(subject, subject_id), "before": before.isoformat() if before else "",
            "hide": _link(subject, subject_id, before) if show else None,
            "heading": f"What happened for {name}, newest first"}


def record_panel(store: records.Records, subject, record: dict) -> dict | None:
    """On a record's own page (a pet, a person): the newest lines of its timeline, or None when no switched-on
    table puts anything on it."""
    if not timeline.sources(store.registry, subject):
        return None
    return timeline_view(store, subject, record["id"], panel=True)


def _before(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


@timeline_pages.get("/timeline/<table>/<int:record_id>")
def timeline_page(table, record_id):
    return _timeline_page(table, record_id, show=False)


@timeline_pages.post("/timeline/<table>/<int:record_id>")
def show_timeline_page(table, record_id):
    """Show on a timeline with private entries (decisions 0121 and 0123): a pressed button with the session check,
    never an address, so no bookmark or shared link opens what each one was. Others have nothing to show."""
    store = _store()
    subject = store.registry.get(table)
    if subject is None or not any(info.table.private for info, _ in timeline.sources(store.registry, subject)):
        abort(404)
    return _timeline_page(table, record_id, show=True)


def _timeline_page(table, record_id, show: bool):
    store = _store()
    subject = store.registry.get(table)
    if subject is None or subject.table.private or not timeline.sources(store.registry, subject):
        abort(404)
    try:
        store.get(subject.name, record_id)
    except records.RecordNotFound:
        abort(404)
    view = timeline_view(store, subject, record_id, _before(request.values.get("before")), show=show)
    return render_template("timeline.html", title=view["heading"], view=view,
                           subject_href=f"/t/{subject.name}/{record_id}")
