"""Private daily history (decision 0120), such as medicine doses: counts and times until Show, per-medicine totals after it."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import urlencode

from dashboard.core import daily, dates, records
from dashboard.core.schema import target_table
from dashboard.web import display


def group_rows(store: records.Records, info: records.TableInfo, subject_id: int) -> list[dict]:
    """The records a subject's entries may be grouped by, such as one person's own medication details: those the
    group link's `link_rule` allows for this subject. Read by its choices and links only; no private text."""
    rule = info.table.daily
    column = info.table.columns.get(rule.get("group") or "")
    target = store.registry.get(target_table(info.module.name, column)) if column is not None else None
    if target is None:
        return []
    clauses, params = ["deleted_at IS NULL"], []
    for name, value in column.link_rule.get("where", {}).items():
        clauses.append(f"{name} = ?")
        params.append(value)
    for theirs, mine in column.link_rule.get("same", {}).items():
        if mine == rule["per"]:
            clauses.append(f"{theirs} = ?")
            params.append(subject_id)
    return [dict(r) for r in store.conn.execute(
        f"SELECT * FROM {target.name} WHERE {' AND '.join(clauses)} ORDER BY id", params)]


def applies(store: records.Records, info: records.TableInfo, subject_id: int) -> bool:
    """Whether a subject's page offers this private log: it has something to group by (a medication detail of
    their own) or entries already. A neighbour with no medication detail gets no dose panel."""
    if not info.table.daily.get("group"):
        return True
    if group_rows(store, info, subject_id):
        return True
    return store.conn.execute(f"SELECT 1 FROM {info.name} WHERE deleted_at IS NULL AND {info.table.daily['per']} = ? "
                              f"LIMIT 1", (subject_id,)).fetchone() is not None


def _links(info: records.TableInfo) -> list:
    """The ordinary links an entry line names, such as who gave it: never the subject, the group or anything private."""
    rule = info.table.daily
    return [c for c in display.form_columns(info) if c.type == "link" and not c.sensitive
            and c.name not in (rule["per"], rule.get("group"))]


def group_words(store: records.Records, info: records.TableInfo, group_id, show: bool) -> str:
    """What a group is called: after Show, its private words (the medication detail as the household wrote it);
    otherwise only its kind and number, "Medication #3"."""
    rule = info.table.daily
    column = info.table.columns[rule["group"]]
    target = store.registry.get(target_table(info.module.name, column))
    words = " ".join(next((c.label for c in target.table.columns[k].choices if c.key == v), v)
                     for k, v in column.link_rule.get("where", {}).items()) if target is not None else ""
    plain = f"{words or display.column_label(info, column)} #{group_id}"
    shows = column.link_rule.get("shows")
    if not show or not shows or target is None:
        return plain
    row = store.conn.execute(f"SELECT {shows} FROM {target.name} WHERE id = ?", (group_id,)).fetchone()
    return f"{row[0]} ({plain})" if row and row[0] else plain


def line(store, info: records.TableInfo, row: dict, formatter: display.Formatter, show: bool) -> str:
    """"8:00 am · dose · Given by: Maria Garcia"; after Show also the medicine and the amount entered."""
    from dashboard.web.daily_pages import amount_text, clock_text
    rule = info.table.daily
    parts = [clock_text(row["_local"]), rule["entry"][0]]
    if show:
        if rule.get("group"):
            parts.append(group_words(store, info, row[rule["group"]], True))
        parts.append(amount_text(rule, row) or "no amount entered")
    for column in _links(info):
        name = formatter.text(info, column, row.get(column.name)) if row.get(column.name) not in (None, "") else ""
        parts.append(f"{display.column_label(info, column).rstrip('?')}: {name or 'not known'}")
    return " · ".join(parts)


def add_link(store: records.Records, info: records.TableInfo, subject_id: int) -> str:
    """Record a dose: the person, the household's time now, and the medicine and giver of the last entry if they
    still fit, shown on the form for checking. The amount is never copied from an earlier entry."""
    from dashboard.web.daily_pages import _now
    rule = info.table.daily
    args: dict = {}
    columns = [c.name for c in _links(info)] + ([rule["group"]] if rule.get("group") else [])
    last = daily.recent_choices(store.conn, info, subject_id, columns, limit=1) if columns else []
    fits = {r["id"] for r in group_rows(store, info, subject_id)}
    if last:
        for name, value in last[0].items():
            if value in (None, "") or (name == rule.get("group") and value not in fits):
                continue
            args[name] = value
        if args:
            args["from"] = "last"
    if rule.get("group") and rule["group"] not in args and len(fits) == 1:
        args[rule["group"]] = next(iter(fits))  # the person's only medication detail, still shown for checking
    args[rule["when"]] = daily.now_text(store.conn, _now())
    args[rule["per"]] = subject_id
    return f"/t/{info.name}/new?{urlencode(args)}"


def first_add(store: records.Records, info: records.TableInfo, subject_id: int) -> dict | None:
    """Where to add the first thing to group by, such as a medication detail for this person, when there is none."""
    rule = info.table.daily
    column = info.table.columns.get(rule.get("group") or "")
    if column is None or group_rows(store, info, subject_id):
        return None
    target = store.registry.get(target_table(info.module.name, column))
    if target is None:
        return None
    args = dict(column.link_rule.get("where", {}))
    args.update({theirs: subject_id for theirs, mine in column.link_rule.get("same", {}).items() if mine == rule["per"]})
    return {"href": f"/t/{target.name}/new?{urlencode(args)}", "title": display.table_title(target)}


def view(store: records.Records, info: records.TableInfo, subject_id: int, day: str, show: bool = False) -> dict:
    """One subject's private day: how many entries and when, with Record a dose; after Show, each group's own
    totals by unit (never added across medicines) and every entry's amount. No missed-dose words, ever."""
    from dashboard.web.daily_pages import _day_words, _now, _subject_info
    rule = info.table.daily
    zone = daily.household_zone(store.conn)
    today = daily.today(store.conn, _now()).isoformat()
    style = dates.household_style(store.conn)
    formatter = display.Formatter(store)
    subject_info = _subject_info(store, info)
    name = display.display_name(subject_info, store.get(subject_info.name, subject_id), store)
    result = daily.days(store.conn, info, subject_id, day, day, zone)[0]
    rows = [{"href": f"/t/{info.name}/{e['id']}", "line": line(store, info, e, formatter, show)}
            for e in result.entries]
    groups = []
    if show and rule.get("group"):
        for key, part in daily.by_group(rule, result):
            one, many = rule["entry"]
            n = len(part.entries)
            words = f"{n} {one if n == 1 else many}"
            if part.totals:
                words += f" · {daily.totals_words(rule, part)}"
            if part.unmeasured:
                words += f" · {part.unmeasured} without an amount"
            groups.append({"name": group_words(store, info, key, True), "words": words})
    before = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    after = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    here = f"/daily/{info.name}?{urlencode({'subject': subject_id, 'day': day})}"
    group = info.table.columns.get(rule.get("group") or "")
    return {"private": True, "name": name, "subject_id": subject_id, "table": info.name, "rule": rule, "day": day,
            "heading": f"{rule['what']} for {name} · {dates.show(day, style)}",
            "summary": daily.count_words(rule, result, _day_words(day, today, style)), "rows": rows,
            "groups": groups, "show": show, "hide_href": here,
            "group_title": f"Each {display.column_label(info, group).lower()} on its own, this day" if group else None,
            "waiting": 0, "is_today": day == today, "today": today,
            "before": before, "after": after if after <= today else None,
            "add": add_link(store, info, subject_id), "first_add": first_add(store, info, subject_id),
            "picks": [], "sheet": None, "list": f"/t/{info.name}",
            "subject_href": f"/t/{subject_info.name}/{subject_id}",
            "entry_one": rule["entry"][0], "entry_many": rule["entry"][1]}
