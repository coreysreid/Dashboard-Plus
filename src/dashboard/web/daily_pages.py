"""Daily totals pages (decision 0110): one subject's day, a dated sheet, the Home lines, the record panel and Review's repeat note."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from flask import Blueprint, abort, current_app, render_template, request

from dashboard.core import daily, dates, records
from dashboard.core.schema import target_table
from dashboard.web import display

daily_pages = Blueprint("daily_pages", __name__)

SHEET_DAYS = 14  # the default sheet length: for manageable paper only, not a feeding guideline
SHEET_MOST_DAYS = 92  # a longer sheet is refused with shorter ranges offered; there is no full-year sheet
SHEET_MOST_ROWS = 1000  # a sheet prints every entry in its range or says it cannot; it never stops part way
HOME_MOST = 8  # subjects named on Home; the rest are counted and on the daily page


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _now() -> datetime:
    clock = current_app.config.get("NOW")
    return clock() if clock else datetime.now(timezone.utc)


def daily_tables(registry: dict, subject: records.TableInfo | None = None) -> list[records.TableInfo]:
    """Tables that declare `daily`, or only those whose subject link points at `subject`."""
    found = []
    for info in registry.values():
        rule = info.table.daily
        if not rule:
            continue
        target = target_table(info.module.name, info.table.columns[rule["per"]])
        if target in registry and (subject is None or target == subject.name):
            found.append(info)
    return found


def _subject_info(store: records.Records, info: records.TableInfo) -> records.TableInfo:
    return store.registry[target_table(info.module.name, info.table.columns[info.table.daily["per"]])]


def _subjects(store: records.Records, info: records.TableInfo) -> list[dict]:
    subject_info = _subject_info(store, info)
    rows = [dict(r) for r in store.conn.execute(f"SELECT * FROM {subject_info.name} WHERE deleted_at IS NULL "
                                                f"ORDER BY id")]
    found = [{"id": r["id"], "name": display.display_name(subject_info, r, store)} for r in rows]
    return sorted(found, key=lambda s: (s["name"].lower(), s["id"]))


def clock_text(moment: datetime) -> str:
    """"7:15 am", "6:10 pm": the household's own clock time."""
    return f"{moment.hour % 12 or 12}:{moment.minute:02d} {'am' if moment.hour < 12 else 'pm'}"


def _day_words(day: str, today: str, style: str) -> str:
    if day == today:
        return "today"
    if day == (date.fromisoformat(today) - timedelta(days=1)).isoformat():
        return "yesterday"
    return f"on {dates.show(day, style)}"


def _shown(info: records.TableInfo) -> list:
    """The list's other columns, in list order: what an entry line and the remembered choices are made of.
    Never the subject, the time, a private column or a long note."""
    rule = info.table.daily
    return [c for c in display.list_columns(info) if c.name not in (rule["per"], rule["when"])
            and not c.sensitive and c.type not in ("longtext", "links", "file", "link")]


def amount_text(rule: dict, row: dict) -> str:
    amount, unit = row.get(rule["amount"]), (row.get(rule["unit"]) or "").strip()
    return daily.amount_words(amount, unit) if amount is not None and unit else ""


def entry_line(info: records.TableInfo, row: dict, formatter: display.Formatter) -> tuple[str, str]:
    """("7:15 am · Kitchen bowl · Example dry dog food · 120 g", "Bowl"): the time, the entry's words in list
    order and its amount, then its choices (such as Bowl, Refill or Treat) said on their own."""
    rule = info.table.daily
    parts, tags = [clock_text(row["_local"])], []
    for column in _shown(info):
        if column.name in (rule["amount"], rule["unit"]) or row.get(column.name) in (None, ""):
            continue
        (tags if column.type == "choice" else parts).append(formatter.text(info, column, row[column.name]))
    parts.append(amount_text(rule, row) or "no amount recorded")
    return " · ".join(parts), ", ".join(tags)


def add_link(store: records.Records, info: records.TableInfo, subject_id: int, choice: dict | None = None) -> str:
    """The Add food address: the subject, the household's time now, and any remembered choices, all shown on
    the form for checking. Nothing is saved until the person presses Save."""
    rule = info.table.daily
    args = {rule["per"]: subject_id, rule["when"]: daily.now_text(store.conn, _now())}
    if choice:
        for name, value in choice.items():
            if value not in (None, ""):
                args[name] = display.input_value(info.table.columns[name], value)
        args["from"] = "last"
    return f"/t/{info.name}/new?{urlencode(args)}"


def _choice_words(info: records.TableInfo, choice: dict, formatter) -> str:
    """"Bowl · Kitchen bowl · Example dry dog food · 120 g": a quick pick as its button says it."""
    rule = info.table.daily
    parts = [formatter.text(info, c, choice[c.name]) for c in _shown(info)
             if c.name in choice and c.name not in (rule["amount"], rule["unit"]) and choice[c.name] not in (None, "")]
    return " · ".join(parts + ([amount_text(rule, choice)] if amount_text(rule, choice) else []))


def day_view(store: records.Records, info: records.TableInfo, subject_id: int, day: str, show: bool = False) -> dict:
    """Everything one subject's day shows: its accepted entries, the honest totals and what is still waiting.
    A private table (decision 0120) shows counts and times until `show`, the person's deliberate Show."""
    if info.table.private:
        from dashboard.web import private_daily
        return private_daily.view(store, info, subject_id, day, show)
    rule = info.table.daily
    zone = daily.household_zone(store.conn)
    today = daily.today(store.conn, _now()).isoformat()
    style = dates.household_style(store.conn)
    formatter = display.Formatter(store)
    subject_info = _subject_info(store, info)
    subject = store.get(subject_info.name, subject_id)
    name = display.display_name(subject_info, subject, store)
    result = daily.days(store.conn, info, subject_id, day, day, zone)[0]
    rows = []
    for e in result.entries:
        line, tags = entry_line(info, e, formatter)
        rows.append({"href": f"/t/{info.name}/{e['id']}", "line": line, "kind": tags})
    picks = daily.recent_choices(store.conn, info, subject_id, [c.name for c in _shown(info)], limit=4)
    waiting = daily.waiting(store.conn, info, subject_id)
    before = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    after = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    return {"name": name, "subject_id": subject_id, "table": info.name, "rule": rule, "day": day,
            "heading": f"{rule['what']} for {name} · {dates.show(day, style)}",
            "summary": daily.summary(rule, result, _day_words(day, today, style)), "rows": rows,
            "waiting": waiting, "is_today": day == today, "today": today,
            "before": before, "after": after if after <= today else None,
            "add": add_link(store, info, subject_id, picks[0] if picks else None),
            "picks": [{"href": add_link(store, info, subject_id, p), "words": _choice_words(info, p, formatter)}
                      for p in picks[1:]],  # the first is already Add food
            "sheet": f"/daily/{info.name}/sheet?{urlencode({'subject': subject_id})}",
            "list": f"/t/{info.name}", "subject_href": f"/t/{subject_info.name}/{subject_id}",
            "entry_one": rule["entry"][0], "entry_many": rule["entry"][1],
            "calendar": (f"/calendar/{info.name}?" + urlencode({"subject": subject_id, "month": day[:7]})
                         if info.table.calendar else None)}  # the month around this day (decision 0119)


def review_note(store: records.Records, item: dict) -> dict | None:
    """On Review, a suggested entry that looks like one already recorded or another one waiting (decision 0110):
    "Possible repeat feeding entry", what it matches and from where, and the two plainly worded choices.
    It only warns; nothing is merged, and two real feedings close together can both be kept."""
    info = store.registry.get(item["table_name"])
    if info is None or not info.table.daily or not info.table.daily.get("repeat") or item.get("refs"):
        return None
    rule = info.table.daily
    zone = daily.household_zone(store.conn)
    found = daily.possible_repeats(store.conn, info, item["values"], zone, skip_proposal=item["id"])
    style = dates.household_style(store.conn)
    formatter = display.Formatter(store)
    matches = []
    for match in found[:3]:
        values = match["row"] if match["kind"] == "record" else match["values"]
        try:
            moment = daily.local(values[rule["when"]], zone)
        except (KeyError, TypeError, ValueError):
            continue
        what = " · ".join([f"{dates.show(moment.date().isoformat(), style)} {clock_text(moment)}"] + [
            formatter.text(info, c, values.get(c.name)) for c in _shown(info)
            if c.name not in (rule["amount"], rule["unit"]) and values.get(c.name) not in (None, "")]
            + ([amount_text(rule, values)] if amount_text(rule, values) else []))
        if match["kind"] == "record":
            actor = values.get("source") or "person"
            where = "already in your records" + ("" if actor == "person" else
                                                 f" (added from {display.actor_text(actor)})")
        else:
            batch = store.conn.execute(
                "SELECT b.kind, b.source_name, h.name AS helper FROM core__helper_batches b LEFT JOIN core__helpers h "
                "ON h.id = b.helper_id WHERE b.id = ?", (match["batch"],)).fetchone()
            who = (f"your spreadsheet import '{batch['source_name']}'" if batch and batch["kind"] == "import"
                   else (batch["helper"] if batch and batch["helper"] else "a helper"))
            where = f"also waiting on Review, from {who}"
        matches.append(f"{what}, {where}")
    if not matches:
        return None
    one = rule["entry"][0]
    return {"title": f"Possible repeat {one} entry", "matches": matches,
            "words": f"Two real {rule['entry'][1]} can be close together. Accept this if both happened, "
                     f"or reject this copy.",
            "accept": f"Accept as another {one}", "reject": "Reject this copy"}


def home_cards(conn, registry: dict, now: datetime | None = None) -> list[dict]:
    """Home's lines: "Rex · 2 feedings recorded today · 240 g put out", or "No feeding entry recorded today".
    No warning, target or missed meal is ever worked out from an empty day."""
    store = records.Records(conn, registry)
    cards = []
    for info in daily_tables(registry):
        if info.table.private:  # private history, such as medicine doses, is never on Home (decision 0120)
            continue
        rule = info.table.daily
        zone = daily.household_zone(conn)
        today = daily.today(conn, now).isoformat()
        subjects = _subjects(store, info)
        if not subjects:
            continue
        lines = []
        for subject in subjects[:HOME_MOST]:
            result = daily.days(conn, info, subject["id"], today, today, zone)[0]
            lines.append({"name": subject["name"], "words": home_words(rule, result),
                          "href": f"/daily/{info.name}?{urlencode({'subject': subject['id']})}"})
        cards.append({"title": f"{rule['what']} today", "lines": lines, "more": len(subjects) - len(lines),
                      "href": f"/daily/{info.name}", "table": info.name, "entry_one": rule["entry"][0]})
    return cards


def home_words(rule: dict, result: daily.Day) -> str:
    """"2 feedings recorded today · 240 g put out"; with gaps "· 1 has no amount"; none: the no-entry words."""
    one, many = rule["entry"]
    n = len(result.entries)
    if not n:
        return f"No {one} entry recorded today"
    text = f"{n} {one if n == 1 else many} recorded today"
    if result.totals:
        text += f" · {daily.totals_words(rule, result)}"
        if result.unmeasured:
            text += f" · {result.unmeasured} {'has' if result.unmeasured == 1 else 'have'} no amount"
    else:
        text += " · amount not measured" if n == 1 else " · amounts not measured"
    return text


def record_panels(store: records.Records, subject_info: records.TableInfo, record: dict) -> list[dict]:
    """On a pet's own page: today's food put out, Add food with the last choices shown, and the log's links."""
    panels = []
    for info in daily_tables(store.registry, subject_info):
        if info.table.private:
            from dashboard.web import private_daily
            if not private_daily.applies(store, info, record["id"]):
                continue  # a neighbour with no medication detail gets no dose panel (decision 0120)
        today = daily.today(store.conn, _now()).isoformat()
        view = day_view(store, info, record["id"], today)
        view["href"] = f"/daily/{info.name}?{urlencode({'subject': record['id']})}"
        panels.append(view)
    return panels


@daily_pages.get("/daily/<table>")
def day_page(table):
    return _day_page(table, show=False)


@daily_pages.post("/daily/<table>")
def show_day_page(table):
    """Show details on a private day (decision 0120): a pressed button, like the private sheet's (decision 0071), so
    no address, bookmark or shared link can open the medicines and amounts. An ordinary table has nothing to show."""
    info = _store().registry.get(table)
    if info is None or not info.table.private:
        abort(404)
    return _day_page(table, show=True)


def _day_page(table, show: bool):
    store = _store()
    info = store.registry.get(table)
    if info is None or not info.table.daily or info not in daily_tables(store.registry):
        abort(404)
    rule = info.table.daily
    subjects = _subjects(store, info)
    if info.table.private:  # only the people this private log applies to (decision 0120)
        from dashboard.web import private_daily
        subjects = [s for s in subjects if private_daily.applies(store, info, s["id"])]
    subject_info = _subject_info(store, info)
    title = f"{rule['what']} by day"
    if not subjects:
        return render_template("daily.html", title=title, subjects=[], view=None, table=table,
                               add_subject=f"/t/{subject_info.name}/new",
                               no_subject=f"Add to {display.table_title(subject_info)} first." if not info.table.private
                               else f"Nothing to record yet. Add a {display.column_label(info, info.table.columns[rule['group']]).lower()} "
                                    f"detail on a person's page first." if rule.get("group")
                               else f"Add to {display.table_title(subject_info)} first.")
    wanted = request.values.get("subject", type=int)
    chosen = next((s for s in subjects if s["id"] == wanted), subjects[0])
    today = daily.today(store.conn, _now()).isoformat()
    day = request.values.get("day", "")
    try:
        day = date.fromisoformat(day).isoformat() if day else today
    except ValueError:
        day = today
    day = min(day, today)
    view = day_view(store, info, chosen["id"], day, show=show)
    return render_template("daily.html", title=title, subjects=subjects, chosen=chosen, view=view, table=table,
                           no_subject=None)


def _sheet_bounds(typed: dict, style: str, today: str) -> tuple[str, str, list[str]]:
    bounds, problems = {}, []
    for key, words in (("from", "From"), ("to", "To")):
        if typed[key]:
            try:
                bounds[key] = dates.parse(typed[key], style)
            except ValueError as problem:
                problems.append(f"{words}: {problem}")
    end = bounds.get("to") or today
    start = bounds.get("from") or (date.fromisoformat(end) - timedelta(days=SHEET_DAYS - 1)).isoformat()
    if start > end:
        problems.append("From must not be after To.")
    return start, end, problems


def _pieces(start: str, end: str, table: str, subject: int, style: str) -> list[dict]:
    """Shorter ranges to offer instead of a sheet that would be too long: 14 days each, at most eight."""
    found, current, last = [], date.fromisoformat(start), date.fromisoformat(end)
    while current <= last and len(found) < 8:
        stop = min(current + timedelta(days=SHEET_DAYS - 1), last)
        found.append({"words": f"{dates.show(current.isoformat(), style)} to {dates.show(stop.isoformat(), style)}",
                      "href": f"/daily/{table}/sheet?" + urlencode(
                          {"subject": subject, "from": dates.show(current.isoformat(), style),
                           "to": dates.show(stop.isoformat(), style)})})
        current = stop + timedelta(days=1)
    return found


@daily_pages.get("/daily/<table>/sheet")
def sheet_page(table):
    """The printable log for one subject and an inclusive date range: every accepted entry, then each day's
    totals by unit and its entries with no amount. Complete, or it says it cannot be and offers shorter ranges."""
    store = _store()
    info = store.registry.get(table)
    if info is None or not info.table.daily or info not in daily_tables(store.registry) or info.table.private:
        abort(404)  # private history, such as medicine doses, has no printable sheet (decision 0120)
    rule = info.table.daily
    subjects = _subjects(store, info)
    if not subjects:
        abort(404)
    wanted = request.args.get("subject", type=int)
    chosen = next((s for s in subjects if s["id"] == wanted), subjects[0])
    style = dates.household_style(store.conn)
    zone = daily.household_zone(store.conn)
    today = daily.today(store.conn, _now()).isoformat()
    typed = {"from": request.args.get("from", "").strip()[:20], "to": request.args.get("to", "").strip()[:20]}
    start, end, problems = _sheet_bounds(typed, style, today)
    base = {"title": rule["sheet"], "rule": rule, "subjects": subjects, "chosen": chosen, "table": table,
            "typed": typed, "hint": dates.SHORT[style], "problems": problems, "days": [], "too_long": None,
            "caveat": rule["caveat"]}
    if problems:
        return render_template("daily_sheet.html", **base), 422
    span = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    total = daily.count(store.conn, info, chosen["id"], start, end, zone)
    range_words = f"{dates.show(start, style)} to {dates.show(end, style)}"
    base.update(range_words=range_words, total=total, start=start, end=end)
    if span > SHEET_MOST_DAYS or total > SHEET_MOST_ROWS:
        base["too_long"] = {
            "words": (f"This range has {span} days and {total} {rule['entry'][0 if total == 1 else 1]}, more than one "
                      f"sheet can print completely (up to {SHEET_MOST_DAYS} days and {SHEET_MOST_ROWS} entries). "
                      f"Nothing was left out: choose a shorter range."),
            "pieces": _pieces(start, end, table, chosen["id"], style)}
        return render_template("daily_sheet.html", **base)
    formatter = display.Formatter(store)
    columns = [c for c in _shown(info) if c.name not in (rule["amount"], rule["unit"])]
    base["headings"] = ["When"] + [display.column_label(info, c) for c in columns] + [
        display.column_label(info, info.table.columns[rule["amount"]])]
    shown = []
    for result in daily.days(store.conn, info, chosen["id"], start, end, zone):
        if not result.entries:
            continue  # the sheet lists recorded entries; an empty day is not printed as a missed one
        day_text = dates.show(result.day, style)
        lines = [[f"{day_text} {clock_text(e['_local'])}"] +
                 [formatter.text(info, c, e.get(c.name)) for c in columns] +
                 [amount_text(rule, e) or "Not measured"] for e in result.entries]
        subtotal = daily.totals_words(rule, result) if result.totals else "No measured amounts"
        if result.unmeasured:
            subtotal += f"; {result.unmeasured} without an amount"
        shown.append({"day": day_text, "lines": lines, "subtotal": subtotal})
    base.update(days=shown, printed=dates.show(today, style))
    return render_template("daily_sheet.html", **base)
