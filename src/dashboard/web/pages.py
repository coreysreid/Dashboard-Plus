"""Pages built from module declarations: the record grid, add and edit forms, and history."""
from __future__ import annotations

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from dashboard.core import records, schema
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
    allowed = {"id"} | {c.name for c in display.list_columns(info)}
    return (sort if sort in allowed else "id"), request.args.get("desc") == "1"


def _rows(store, info, offset, sort, desc):
    formatter = display.Formatter(store)
    columns = display.list_columns(info)
    rows = store.page(info.name, offset=offset, limit=PAGE_SIZE, order_by=sort, descending=desc)
    return [{"id": r["id"], "review": r["review_status"],
             "cells": [{"text": formatter.text(info, c, r.get(c.name)), "sensitive": c.sensitive} for c in columns]}
            for r in rows]


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


def _render_form(info, store, values, errors, from_form, record=None, status=200, saved=None, back=None):
    fields = display.build_fields(store, info, values, errors, from_form)
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
    record_name = display.display_name(info, record) if record else None
    related = []
    if record and not record.get("deleted_at"):
        for other, column in store._dependents(info):
            related.append({"href": f"/t/{other.name}/new?{column.name}={record['id']}",
                            "label": display.table_title(other)})
    return render_template("form.html", info=info, title=display.table_title(info), fields=fields, record=record,
                           record_name=record_name, errors=errors, history=history, saved=saved,
                           related=related, back=back), status


def _default_text(column) -> str:
    """A default as it should appear in an empty form."""
    value = records.resolve_default(column)
    return "" if value is None else str(value)


def _raw_form(info):
    """What the person typed, so a form with mistakes comes back filled in."""
    raw = {k: request.form.get(k) for k in request.form}
    for column in info.table.columns.values():
        if column.type == "links":
            raw[column.name] = request.form.getlist(column.name)
        elif column.type == "boolean":
            raw[column.name] = "yes" if request.form.get(column.name) else ""
    return raw


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
        if column.type == "link" and value.isdigit():
            back = f"/t/{schema.target_table(info.module.name, column)}/{value}"
    return _render_form(info, store, prefill, {}, True, saved=request.args.get("saved"), back=back)


@pages.post("/t/<table>/new")
def create_record(table):
    info, store = _info(table), _store()
    values = display.values_from_form(info, request.form)
    try:
        record_id = store.create(table, values)
    except records.ValidationError as error:
        back = request.form.get("back") if request.form.get("back", "").startswith("/t/") else None
        return _render_form(info, store, _raw_form(info), error.problems, True, status=422, back=back)
    if request.form.get("then") == "another":
        return redirect(url_for("pages.new_record", table=table, saved=display.display_name(
            info, store.get(table, record_id))))
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
    values = display.values_from_form(info, request.form)
    try:
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


@pages.post("/t/<table>/<int:record_id>/restore")
def restore_record(table, record_id):
    _info(table)
    try:
        _store().restore(table, record_id)
    except records.RecordNotFound:
        abort(404)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id))
