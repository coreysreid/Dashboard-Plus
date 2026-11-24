"""Pages built from module declarations: the record grid, add and edit forms, and history."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from dashboard.core import actions, confirm, dates, records, schema, settings, suggest
from dashboard.core.units import unit_for
from dashboard.web import display

pages = Blueprint("pages", __name__)
PAGE_SIZE = 50
UNDER_LIMIT = 50  # records listed under another record's page, latest first; the rest are on their own list


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _info(table: str) -> records.TableInfo:
    registry = current_app.config["REGISTRY_FOR_REQUEST"]()
    if table not in registry:
        abort(404)
    return registry[table]


def _sorting(info: records.TableInfo) -> tuple[str, bool]:
    sort = request.args.get("sort", "id")
    # Never sort by a private column: the order alone could give its values away. Nor by a link into a list
    # that is switched off: the order would follow records nobody can see (decision 0115).
    off = _store().off_links(info)
    allowed = {"id"} | {c.name for c in display.list_columns(info) if not c.sensitive and c.name not in off}
    return (sort if sort in allowed else "id"), request.args.get("desc") == "1"


def _paths(store, info) -> dict[int, str]:
    """Every record's full path ("Kitchen › Pantry › Shelf 3"), for a table whose records nest."""
    rows = {r["id"]: dict(r) for r in store.page(info.name, limit=5000)}
    return {rid: display.path_name(info, rows, row) for rid, row in rows.items()}


def _rows(store, info, offset, sort, desc):
    formatter = display.Formatter(store)
    columns = display.list_columns(info)
    name_col = display.name_column(info)
    paths = _paths(store, info) if info.table.parent else {}
    if paths and not request.args.get("sort"):
        # Nested records are listed by full path, so each room is followed by what is inside it.
        ordered = sorted(paths, key=lambda rid: paths[rid].lower())[offset:offset + PAGE_SIZE]
        rows = [store.get(info.name, rid) for rid in ordered]
    else:
        rows = store.page(info.name, offset=offset, limit=PAGE_SIZE, order_by=sort, descending=desc)
    out = []
    for r in rows:
        label = paths.get(r["id"]) or display.display_name(info, dict(r), store)
        cells = []
        for c in columns:
            text = paths[r["id"]] if paths and name_col is not None and c.name == name_col.name \
                else formatter.text(info, c, r.get(c.name))
            if c.sensitive:  # the private value is never in the page; "Show" fetches it (privacy audit)
                cells.append({"text": "", "sensitive": True, "saved": bool(text), "column": c.name,
                              "label": display.column_label(info, c)})
                continue
            cells.append({"text": text, "sensitive": False, "label": display.column_label(info, c)})
        out.append({"id": r["id"], "review": r["review_status"], "label": label, "cells": cells})
    return out


@pages.get("/t/<table>")
def grid(table):
    info, store = _info(table), _store()
    sort, desc = _sorting(info)
    total = store.count(table)
    rows = _rows(store, info, 0, sort, desc)
    off = store.off_links(info)  # a link into a list that is switched off is not sorted by (decision 0115)
    columns = [{"name": c.name, "label": display.column_label(info, c), "sortable": c.name not in off}
               for c in display.list_columns(info)]
    from dashboard.web import moves_pages  # one reminder per policy: the household's choice (decision 0117)
    return render_template("grid.html", info=info, title=display.table_title(info), columns=columns, rows=rows,
                           total=total, next_offset=len(rows) if len(rows) < total else None,
                           sort=sort, desc=desc, moves_choice=moves_pages.choice_box(store, info),
                           moves_review=moves_pages.review_link(store, info))


@pages.get("/t/<table>/rows")
def more_rows(table):
    """The next page of rows, loaded by the grid as you scroll."""
    info, store = _info(table), _store()
    sort, desc = _sorting(info)
    offset = max(0, request.args.get("offset", 0, type=int))
    rows = _rows(store, info, offset, sort, desc)
    total = store.count(table)
    next_offset = offset + len(rows) if offset + len(rows) < total else None
    return render_template("rows.html", info=info, rows=rows, next_offset=next_offset)


@pages.get("/t/<table>/suggest")
def suggest_names(table):
    """What to offer while someone types a name: their own records first, then the module's list."""
    info = _info(table)
    column = request.args.get("column", "")
    if column not in info.table.columns or info.table.columns[column].type != "text" or \
            info.table.columns[column].sensitive:  # private details are never offered as suggestions
        abort(404)
    typed = request.args.get("q", "")[:80]
    query = suggest.normalise(typed)
    own = []
    if query:
        conn = current_app.config["CONNECT"]()
        words = query.split()
        rows = conn.execute(f"SELECT id, {column} AS name FROM {info.name} WHERE deleted_at IS NULL "
                            f"AND {column} IS NOT NULL AND lower({column}) LIKE ? LIMIT 50",
                            (f"%{words[0][:3]}%",)).fetchall()
        own = [{"id": r["id"], "name": r["name"]} for r in rows]
    if info.table.parent and query:
        # Nested records are found and shown by full path ("kitchen" finds Kitchen › Pantry › Shelf 3).
        own = [{"id": rid, "name": path} for rid, path in _paths(_store(), info).items()]
    catalogue = info.module.catalogues.get((info.table.name, column), [])
    return jsonify(suggest.suggestions(typed, own, catalogue))


def _under(store, info, record) -> list[dict]:
    """Records of other tables listed on this record's page, like a service's quotes (labels.toml `under`, 0111).
    Private cells are never in the page: each is a Show button that fetches it, as on the list."""
    found = []
    formatter = display.Formatter(store)
    for other in store.registry.values():
        rule = display.labels_for(other).get("under")
        if not rule or schema.target_table(other.module.name, other.table.columns[rule["link"]]) != info.name:
            continue
        columns = [other.table.columns[c] for c in rule["columns"]]
        order = rule.get("order", "id")
        total = store.conn.execute(f"SELECT COUNT(*) FROM {other.name} WHERE deleted_at IS NULL AND {rule['link']} = ?",
                                   (record["id"],)).fetchone()[0]
        rows = store.conn.execute(
            f"SELECT * FROM {other.name} WHERE deleted_at IS NULL AND {rule['link']} = ? "
            f"ORDER BY {order} DESC, id DESC LIMIT ?", (record["id"], UNDER_LIMIT)).fetchall()
        listed = []
        for row in rows:
            row = dict(row)
            cells = [{"label": display.column_label(other, c), "sensitive": c.sensitive, "column": c.name,
                      "saved": row.get(c.name) not in (None, ""),
                      "text": "" if c.sensitive else formatter.text(other, c, row.get(c.name))} for c in columns]
            listed.append({"id": row["id"], "href": f"/t/{other.name}/{row['id']}", "cells": cells,
                           "name": display.display_name(other, row, store),
                           "private": any(c["sensitive"] and c["saved"] for c in cells)})
        found.append({"table": other.name, "title": rule["title"], "intro": rule.get("intro"),
                      "reveal": rule.get("reveal"), "labels": [display.column_label(other, c) for c in columns],
                      "rows": listed, "total": total, "more": total - len(listed),
                      "list": f"/t/{other.name}", "list_title": display.table_title(other)})
    return found


def _render_form(info, store, values, errors, from_form, record=None, status=200, saved=None, back=None,
                 done=None, notice=None, confirm_warnings=None, then=None):
    fields = display.build_fields(store, info, values, errors, from_form, editing=record is not None, saved=record)
    history = []
    if record:
        formatter = display.Formatter(store)
        columns = info.table.columns
        for entry in reversed(store.history(info.name, record["id"])):
            changes = []
            for name, after in (entry["after"] or {}).items():
                if entry["action"] == "update" and name in columns:
                    before = (entry["before"] or {}).get(name)
                    changes.append({"label": display.column_label(info, columns[name]),
                                    "before": formatter.text(info, columns[name], before),
                                    "after": formatter.text(info, columns[name], after),
                                    "sensitive": columns[name].sensitive})
            history.append({"at": entry["at"].replace("T", " ")[:16], "who": display.actor_text(entry["actor"]),
                            "action": display.operation_text(store, info, entry) or
                            display.ACTION_TEXT.get(entry["action"], entry["action"]), "changes": changes})
    record_name = display.display_name(info, record, store) if record else None
    if record and info.table.parent:
        chain = store.ancestors(info, record["id"])
        record_name = display.path_name(info, {r["id"]: r for r in chain}, chain[-1]) if chain else record_name
    batches = []  # an item's batches, each with its amount, use-by date and place (DESIGN.md 5.7)
    if record:
        for other in store._totals_into(info):
            rule = other.table.total
            rows = store.conn.execute(
                f"SELECT * FROM {other.name} WHERE deleted_at IS NULL AND {rule['link']} = ? "
                f"ORDER BY {rule['amount']} = 0, "
                + (f"{rule['earliest']['date']} IS NULL, {rule['earliest']['date']}, " if rule["earliest"] else "")
                + "id", (record["id"],)).fetchall()
            into = info.table.columns[rule["into"]]
            amount = display.Formatter(store).text(info, into, record.get(rule["into"])) or "0"
            unit = record.get("unit") if "unit" in info.table.columns else None
            unit = unit_for(record.get(rule["into"]), unit) if unit else unit
            held = sum(1 for r in rows if r[rule["amount"]])
            summary = (f"{display.column_label(info, into)}: {amount}{' ' + unit if unit else ''}, "
                       f"in {held} batch{'es' if held != 1 else ''}")
            countable = store.count_table(other.name) is not None and not record.get("deleted_at")
            batches.append({"title": display.table_title(other), "table": other.name, "summary": summary,
                            "add": f"/t/{other.name}/new?{rule['link']}={record['id']}",
                            "rows": [{"href": f"/t/{other.name}/{r['id']}",
                                      "count": f"/t/{other.name}/{r['id']}/count" if countable else None,
                                      "name": display.display_name(other, dict(r), store)} for r in rows]})
    count_href = None  # "Count this batch": a stocktake saved as one correction (decision 0070)
    if record and not record.get("deleted_at") and store.count_table(info.name) is not None:
        count_href = f"/t/{info.name}/{record['id']}/count"
    related = []
    if record and not record.get("deleted_at"):
        for other, column in store._dependents(info):
            if other.table.private:  # private history is added from its own panel, never offered here (0120)
                continue
            # An action that adds these records may give this button clearer words (decision 0091).
            words = next((a["adds"]["add_button"] for a in info.table.actions if a.get("adds") and
                          a["adds"]["table"] == other.table.name and a["adds"]["link"] == column.name), None)
            words = words or display.labels_for(other).get("add_button")  # "Add a reading" (decision 0111)
            related.append({"href": f"/t/{other.name}/new?{column.name}={record['id']}",
                            "label": display.table_title(other), "words": words})
    charts = []  # a pet's recorded weights, drawn on its own page (decision 0109)
    if record and not record.get("deleted_at"):
        from dashboard.web.chart_pages import chart_tables, dots_view
        for other in chart_tables(store.registry, info):
            charts.append({"title": f"Recorded {other.table.chart['what'][1]}",
                           "view": dots_view(store, other, record["id"], latest_only=UNDER_LIMIT),
                           "href": f"/charts/{other.name}?subject={record['id']}"})
    feeding = []  # a pet's food put out today, with Add food (decision 0110)
    if record and not record.get("deleted_at"):
        from dashboard.web.daily_pages import record_panels
        feeding = record_panels(store, info, record)
    month_calendars = []  # this month's calendar of what was recorded for this record (decision 0119)
    if record and not record.get("deleted_at"):
        from dashboard.web.calendar_pages import record_panels as calendar_panels
        month_calendars = calendar_panels(store, info, record)
    return render_template("form.html", info=info, title=display.table_title(info), fields=fields, record=record,
                           record_name=record_name, errors=errors, history=history, saved=saved, charts=charts,
                           feeding=feeding, month_calendars=month_calendars,
                           related=related, back=back, batches=batches, count_href=count_href,
                           under=_under(store, info, record) if record and not record.get("deleted_at") else [],
                           confirm=confirm_warnings or [], then=then, moves=_moves(store, info, record),
                           actions=display.actions_for(info, record), done=done, notice=notice), status


def _moves(store, info, record) -> list[dict]:
    """Where this record's reminder is, if it was moved or could be (decision 0117)."""
    from dashboard.web import moves_pages
    return moves_pages.record_notices(store, info, record, moved=request.args.get("moved") == "1")


def _default_text(column) -> str:
    """A default as it should appear in an empty form."""
    value = records.resolve_default(column)
    return "" if value is None else str(value)


def _raw_form(info):
    """What the person typed, so a form with mistakes comes back filled in."""
    raw = {k: request.form.get(k) for k in request.form}
    raw["_keep_private"] = request.form.getlist("_keep_private")  # private details left unopened
    for column in info.table.columns.values():
        if column.type == "links":
            raw[column.name] = request.form.getlist(column.name)
        elif column.type == "boolean":
            raw[column.name] = "yes" if request.form.get(column.name) else ""
    return raw


def _form_values(info, store, creating: bool) -> dict:
    """The submitted values, with dates read the household's way. A date that cannot be read is
    reported together with every other problem in the form, and nothing is saved."""
    # A link into a list that is switched off is never read from the form: the saved one is kept (0115).
    hide = store.off_links(info) | (set() if creating else display.batch_columns(store, info))
    values, date_problems = display.values_from_form(info, request.form, dates.household_style(store.conn), hide)
    if date_problems:
        problems = dict(date_problems)
        try:
            store.clean(info, values, creating)
        except records.ValidationError as error:
            problems = {**error.problems, **date_problems}
        raise records.ValidationError(problems)
    return values


@pages.get("/t/<table>/<int:record_id>/reveal")
def reveal_private(table, record_id):
    """One private detail, fetched only when the person chooses Show (privacy audit, decision 0059)."""
    info, store = _info(table), _store()
    column = info.table.columns.get(request.args.get("column", ""))
    if column is None or not column.sensitive:
        abort(404)
    try:
        record = store.get(table, record_id)
    except records.RecordNotFound:
        abort(404)
    value = record.get(column.name)
    return jsonify({"text": display.Formatter(store).text(info, column, value),
                    "value": "" if value is None else str(display.input_value(column, value))})


@pages.get("/t/<table>/new")
def new_record(table):
    """An empty form; values in the address (for example ?item=3) are filled in."""
    info, store = _info(table), _store()
    prefill = {c.name: _default_text(c) for c in info.table.columns.values()
               if c.default is not None and c.type != "boolean"}
    prefill.update({c.name: "yes" for c in info.table.columns.values() if c.type == "boolean" and c.default})
    prefill.update({c.name: settings.household_choice(store.conn, c.default_from)  # the usual km or mi (0111)
                    for c in info.table.columns.values() if c.default_from})
    from_address = {k: v for k, v in request.args.items() if k in info.table.columns and k != "saved"}
    prefill.update(from_address)
    back = None
    for name, value in from_address.items():
        column = info.table.columns[name]
        if column.type == "link" and value.isdecimal() and value.isascii():
            back = f"/t/{schema.target_table(info.module.name, column)}/{value}"
    per = info.table.daily.get("per") if info.table.daily else None
    if per and str(from_address.get(per, "")).isdecimal() and str(from_address[per]).isascii():  # back to the subject
        back = f"/t/{schema.target_table(info.module.name, info.table.columns[per])}/{from_address[per]}"
    notice = None  # remembered choices are shown for checking, never saved unseen (decision 0110)
    if request.args.get("from") == "last" and info.table.daily:
        notice = {"words": "Filled in from a recent entry. Check each answer before you save."}
    return _render_form(info, store, prefill, {}, True, saved=request.args.get("saved"), back=back, notice=notice)


def _held(info, store, values: dict, record: dict | None) -> list:
    """The gentle checks (tables.toml `confirm`, decision 0111) that Save as entered has not answered yet."""
    from dashboard.core import reminder_moves
    cleaned = store.clean(info, values, creating=record is None)
    whole = {**(record or {}), **cleaned}
    formatter = display.Formatter(store)
    found = confirm.warnings(store.conn, info, whole, record["id"] if record else None,
                             lambda column, value: formatter.text(info, column, value)) if info.table.confirm else []
    # The same vehicle already has this kind of reminder in the other list: say so before a second (0117).
    changed = record is None or any(record.get(k) != v for k, v in cleaned.items())
    if changed:
        found += reminder_moves.warnings(store, info, whole, record["id"] if record else None)
    if changed and info.table.daily.get("repeat", {}).get("form"):
        found += _repeat_warnings(store, info, whole, record["id"] if record else None)
    return confirm.unconfirmed(found, request.form.getlist("_confirm"))


def _repeat_warnings(store, info, whole: dict, record_id: int | None) -> list:
    """A possible repeat asked on the household's own form (decision 0120), such as a second dose of the same
    medicine for the same person close in time: the time of the entry already saved, then Go back or Keep. A real
    second entry stays possible, and a double press of Save is caught here instead of saving twice."""
    import hashlib
    from dashboard.core import daily
    from dashboard.web.daily_pages import clock_text
    rule = info.table.daily
    found = daily.form_repeats(store.conn, info, whole, daily.household_zone(store.conn), record_id)
    if not found:
        return []
    style = dates.household_style(store.conn)
    times = ", ".join(f"{clock_text(m['row']['_local'])} on {dates.show(m['row']['_day'], style)}" for m in found[:3])
    checked = "@".join(str(whole.get(c)) for c in [rule["per"], rule["when"], *rule["repeat"]["same"]])
    token = f"repeat-{hashlib.sha256(checked.encode()).hexdigest()[:16]}"
    return [confirm.Warning("repeat", rule["when"], f"{rule['repeat']['form']} Already recorded: {times}.", token,
                            rule["repeat"]["keep"])]


@pages.post("/t/<table>/new")
def create_record(table):
    info, store = _info(table), _store()
    back = request.form.get("back") if request.form.get("back", "").startswith("/t/") else None
    then = request.form.get("then") or request.form.get("_then")
    try:
        values = _form_values(info, store, creating=True)
        held = _held(info, store, values, None)
        if held:  # nothing saved yet: say why, with Go back and Save as entered
            return _render_form(info, store, _raw_form(info), {}, True, back=back, confirm_warnings=held, then=then)
        record_id = store.create(table, values)
    except records.ValidationError as error:
        return _render_form(info, store, _raw_form(info), error.problems, True, status=422, back=back)
    if then == "another":
        return redirect(url_for("pages.new_record", table=table, saved=display.display_name(
            info, store.get(table, record_id), store)))
    if then == "back" and back:
        return redirect(back)
    return redirect(url_for("pages.grid", table=table))


@pages.get("/t/<table>/<int:record_id>")
def edit_record(table, record_id):
    info, store = _info(table), _store()
    try:
        record = store.get(table, record_id, include_deleted=True)
    except records.RecordNotFound:
        abort(404)
    return _render_form(info, store, record, {}, False, record=record, saved=request.args.get("saved"),
                        done=display.done_words(info, request.args.get("done")),
                        notice=action_form.done_notice(store, info, record_id, request.args.get("op")))


@pages.post("/t/<table>/<int:record_id>")
def update_record(table, record_id):
    info, store = _info(table), _store()
    try:
        record = store.get(table, record_id)
    except records.RecordNotFound:
        abort(404)
    try:
        values = _form_values(info, store, creating=False)
        held = _held(info, store, values, record)
        if held:
            return _render_form(info, store, _raw_form(info), {}, True, record=record, confirm_warnings=held)
        store.update(table, record_id, values)
    except records.ValidationError as error:
        return _render_form(info, store, _raw_form(info), error.problems, True, record=record, status=422)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id, saved="1"))


@pages.post("/t/<table>/<int:record_id>/delete")
def delete_record(table, record_id):
    info, store = _info(table), _store()
    try:
        store.delete(table, record_id)
    except records.RecordNotFound:
        abort(404)
    except records.ValidationError as error:
        record = store.get(table, record_id)
        return _render_form(info, store, record, {"_form": error.problems["delete"]}, False,
                            record=record, status=409)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id))


@pages.post("/t/<table>/<int:record_id>/do/<key>")
def run_action(table, record_id, key):
    """A one-step button such as "Mark returned": saved like any change, then back to the record (decision 0075)."""
    info, store = _info(table), _store()
    action = next((a for a in info.table.actions if a["key"] == key), None)
    if action is None:
        abort(404)
    if action.get("adds"):  # an action with a small form, such as Mark done (decision 0091)
        return action_form.save_action_form(table, record_id, key)
    back = action_form.back_to()  # pressed on Things to do (decision 0107): go back there
    op = actions.new_operation()  # named in history, so it counts as done and can be undone (decision 0112)
    try:
        store.action(table, record_id, key, op=op, today=current_app.config["TODAY"]())
    except records.RecordNotFound:
        abort(404)
    except (records.ActionNotAvailable, records.ValidationError) as error:
        if back and isinstance(error, records.ActionNotAvailable):
            return redirect(f"{back}?changed=1")
        if isinstance(error, records.ValidationError):  # e.g. "Returned on can't be before Lent on."
            columns = info.table.columns
            said = [m if m[:1].isupper() else f"{display.column_label(info, columns[f])} {m}" if f in columns else m
                    for f, m in error.problems.items()]
            message = "Nothing was changed. " + " ".join(said)
        else:
            message = str(error)
        record = store.get(table, record_id)
        return _render_form(info, store, record, {"_form": message}, False, record=record, status=409)
    if back:
        return redirect(action_form.back_with(back, table, record_id, op=op))
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id, op=op))


@pages.post("/t/<table>/<int:record_id>/restore")
def restore_record(table, record_id):
    _info(table)
    try:
        _store().restore(table, record_id)
    except records.RecordNotFound:
        abort(404)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id))


from dashboard.web import action_form, count  # noqa: E402,F401 - adds action forms and "Count this batch" to these pages
