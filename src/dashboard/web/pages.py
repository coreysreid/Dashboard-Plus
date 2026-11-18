"""Pages built from module declarations: the record grid, add and edit forms, and history."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

from dashboard.core import dates, records, schema, suggest
from dashboard.core.units import unit_for
from dashboard.web import display

pages = Blueprint("pages", __name__)
PAGE_SIZE = 50


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _info(table: str) -> records.TableInfo:
    registry = current_app.config["REGISTRY_FOR_REQUEST"]()
    if table not in registry:
        abort(404)
    return registry[table]


def _sorting(info: records.TableInfo) -> tuple[str, bool]:
    sort = request.args.get("sort", "id")
    # Never sort by a private column: the order alone could give its values away.
    allowed = {"id"} | {c.name for c in display.list_columns(info) if not c.sensitive}
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
    columns = [{"name": c.name, "label": display.column_label(info, c)} for c in display.list_columns(info)]
    return render_template("grid.html", info=info, title=display.table_title(info), columns=columns, rows=rows,
                           total=total, next_offset=len(rows) if len(rows) < total else None,
                           sort=sort, desc=desc)


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


def _render_form(info, store, values, errors, from_form, record=None, status=200, saved=None, back=None):
    fields = display.build_fields(store, info, values, errors, from_form, editing=record is not None)
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
                            "action": display.ACTION_TEXT.get(entry["action"], entry["action"]), "changes": changes})
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
            related.append({"href": f"/t/{other.name}/new?{column.name}={record['id']}",
                            "label": display.table_title(other)})
    return render_template("form.html", info=info, title=display.table_title(info), fields=fields, record=record,
                           record_name=record_name, errors=errors, history=history, saved=saved,
                           related=related, back=back, batches=batches, count_href=count_href), status


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
    values, date_problems = display.values_from_form(info, request.form, dates.household_style(store.conn),
                                                     () if creating else display.batch_columns(store, info))
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
    from_address = {k: v for k, v in request.args.items() if k in info.table.columns and k != "saved"}
    prefill.update(from_address)
    back = None
    for name, value in from_address.items():
        column = info.table.columns[name]
        if column.type == "link" and value.isdecimal() and value.isascii():
            back = f"/t/{schema.target_table(info.module.name, column)}/{value}"
    return _render_form(info, store, prefill, {}, True, saved=request.args.get("saved"), back=back)


@pages.post("/t/<table>/new")
def create_record(table):
    info, store = _info(table), _store()
    try:
        record_id = store.create(table, _form_values(info, store, creating=True))
    except records.ValidationError as error:
        back = request.form.get("back") if request.form.get("back", "").startswith("/t/") else None
        return _render_form(info, store, _raw_form(info), error.problems, True, status=422, back=back)
    if request.form.get("then") == "another":
        return redirect(url_for("pages.new_record", table=table, saved=display.display_name(
            info, store.get(table, record_id), store)))
    if request.form.get("then") == "back" and request.form.get("back", "").startswith("/t/"):
        return redirect(request.form["back"])
    return redirect(url_for("pages.grid", table=table))


@pages.get("/t/<table>/<int:record_id>")
def edit_record(table, record_id):
    info, store = _info(table), _store()
    try:
        record = store.get(table, record_id, include_deleted=True)
    except records.RecordNotFound:
        abort(404)
    return _render_form(info, store, record, {}, False, record=record, saved=request.args.get("saved"))


@pages.post("/t/<table>/<int:record_id>")
def update_record(table, record_id):
    info, store = _info(table), _store()
    try:
        record = store.get(table, record_id)
    except records.RecordNotFound:
        abort(404)
    try:
        store.update(table, record_id, _form_values(info, store, creating=False))
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


@pages.post("/t/<table>/<int:record_id>/restore")
def restore_record(table, record_id):
    _info(table)
    try:
        _store().restore(table, record_id)
    except records.RecordNotFound:
        abort(404)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id))


from dashboard.web import count  # noqa: E402,F401 - adds "Count this batch" to these pages
