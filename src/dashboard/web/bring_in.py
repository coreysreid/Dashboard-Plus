"""Bring in earlier entries: a list's own page to read a person's CSV, match it, preview every row, add them and Undo.

Decision 0137. Only the household's own pages reach these addresses (the session cookie and page token, as every
page); the helper API has no way in. The file is held in memory only (UploadRequest) and never written anywhere:
between steps its text travels inside the page, and every step checks it again from the start. A list with private
values needs a pressed Show before the file is chosen, every step is a POST, and nothing private is put in an
address. Pages are never cached (Cache-Control: no-store, set for every page in app.py and again here).
"""
from __future__ import annotations

import base64
import binascii

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from dashboard.core import csv_bring_in as bring_in, csv_import, dates, proposals, records
from dashboard.core.actions import new_operation
from dashboard.errors import PlainError
from dashboard.web import display
from dashboard.web.review import visible

bring_in_pages = Blueprint("bring_in", __name__)
PREFIX = "/bring-in"
PREVIEW_ROWS = 5


@bring_in_pages.after_request
def never_kept(response):
    response.headers["Cache-Control"] = "no-store"
    return response


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _info(store: records.Records, table: str) -> records.TableInfo:
    info = store.registry.get(table)
    if info is None or not bring_in.offered(info):
        abort(404)
    return info


def _shown(info) -> bool:
    """Whether the person has pressed Show for this list (always true for a list with nothing private)."""
    return not bring_in.needs_show(info) or request.form.get("shown") == "1"


def _recent(store, info) -> list[dict]:
    style = dates.household_style(store.conn)
    found = []
    for item in bring_in.recent(store, info):
        found.append({"id": item["id"], "day": dates.show(item["at"][:10], style), "count": item["count"],
                      "file": item.get("file") or "", "undone": item["undone"],
                      "can_undo": bring_in.undo_problem(store, info, item) is None})
    return found


def _start(store, info, shown: bool, error: str | None = None, notice: str | None = None, status: int = 200):
    one, many = bring_in.entry_words(info)
    return render_template("bring_in.html", step="start", info=info, title=display.table_title(info), one=one,
                           many=many, private=bring_in.needs_show(info), shown=shown, error=error, notice=notice,
                           recent=_recent(store, info), limit=csv_import.LIMIT_TEXT, max_rows=csv_import.MAX_ROWS,
                           hint=dates.HINTS[dates.household_style(store.conn)]), status


@bring_in_pages.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    store = _store()
    table = request.path.removeprefix(PREFIX + "/").split("/", 1)[0]
    return _start(store, _info(store, table), shown=bring_in.needs_show(_info(store, table)),
                  error=f"This file is too large. The limit is {csv_import.LIMIT_TEXT}: split it into smaller files "
                        f"and bring in each one.", status=413)


@bring_in_pages.get(PREFIX + "/<table>")
def start(table):
    store = _store()
    info = _info(store, table)
    return _start(store, info, shown=not bring_in.needs_show(info))


@bring_in_pages.post(PREFIX + "/<table>/show")
def show(table):
    store = _store()
    return _start(store, _info(store, table), shown=True)


@bring_in_pages.post(PREFIX + "/<table>/read")
def read(table):
    store = _store()
    info = _info(store, table)
    if not _shown(info):
        return _start(store, info, shown=False, error="Press Show first.", status=400)
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return _start(store, info, shown=True, error="Choose a CSV file.", status=400)
    data = upload.stream.read()  # held in memory only (UploadRequest), at most the request limit
    upload.stream.close()
    try:
        text = csv_import.decode(data)
        sheet = csv_import.parse(text)
    except csv_import.FileProblem as error:
        return _start(store, info, shown=True, error=str(error),
                      status=413 if len(data) > csv_import.MAX_BYTES else 400)
    mapping = bring_in.auto_match(store, info, sheet.headers)
    return _page(store, info, text, proposals.source_label(upload.filename), sheet, mapping)


def _carried(store, info):
    """The file text, its name, the sheet, the matches and the person's choices that the page sent back."""
    try:
        data = base64.b64decode(request.form.get("data", ""), validate=True)
    except (binascii.Error, ValueError):
        raise PlainError("That page had expired. Choose the file again.") from None
    text = csv_import.decode(data)
    sheet = csv_import.parse(text)
    mapping = [request.form.get(f"match_{i}", "") for i in range(len(sheet.headers))]
    picks = {key[5:]: value for key, value in request.form.items() if key.startswith("pick_") and value}
    add = {int(key[4:]) for key in request.form if key.startswith("add_") and key[4:].isdigit()}
    return text, proposals.source_label(request.form.get("file_name", "")), sheet, mapping, picks, add, \
        bool(request.form.get("dates_ok"))


def _row_words(store, info, columns, formatter, names, row) -> list[str]:
    """Each matched field of a ready row as the household reads it; private values too (this page is after Show)."""
    try:
        values = store.clean(info, dict(row.values), creating=True)
    except records.ValidationError:  # pragma: no cover - the row passed the full check a moment ago
        values = row.values
    cells = []
    for column in columns:
        value = values.get(column.name)
        if column.type == "link" and column.link_rule.get("shows") and value:
            target = names.target(info, column)
            found = store.conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (value,)).fetchone()
            cells.append(names.words(info, column, dict(found)) if found else "")
        else:
            cells.append(formatter.text(info, column, value))
    return cells


def _page(store, info, text, file_name, sheet, mapping, run=None, picks=None, add=None, dates_ok=False,
          notice=None, status=200):
    one, many = bring_in.entry_words(info)
    columns = [{"index": i, "header": visible(h) or f"Column {i + 1} (no heading)", "chosen": mapping[i]}
               for i, h in enumerate(sheet.headers)]
    options = [{"name": v, "label": t, "needed": n} for v, t, n in bring_in.options(store, info)]
    preview = [(n, [visible(cell) for cell in cells]) for n, cells in sheet.rows[:PREVIEW_ROWS]]
    problems = bring_in.mapping_problems(store, info, mapping) if run is not None or notice else []
    shown_columns = [info.table.columns[m] for m in dict.fromkeys(mapping)
                     if m and not m.endswith(bring_in.TIME)]
    ready, duplicates, chosen = [], [], []
    if run is not None:
        formatter, names = display.Formatter(store), bring_in.Names(store)
        for row in run.ready:
            item = {"row": row.number, "cells": [visible(c) for c in _row_words(store, info, shown_columns,
                                                                                 formatter, names, row)],
                    "duplicate": row.duplicate}
            (duplicates if row.duplicate else ready).append(item)
        chosen = run.chosen(add or set())
    style = dates.household_style(store.conn)
    return render_template(
        "bring_in.html", step="match", info=info, title=display.table_title(info), one=one, many=many,
        private=bring_in.needs_show(info), file_name=file_name, row_count=len(sheet.rows), columns=columns,
        options=options, preview=preview, problems=problems, notice=notice, run=run,
        data=base64.b64encode(text.encode("utf-8")).decode("ascii"),
        labels=[display.column_label(info, c) for c in shown_columns], ready=ready, duplicates=duplicates,
        picks=[{"key": p.key, "label": p.label, "text": visible(p.text), "context": visible(p.context),
                "rows": p.rows, "several": p.several, "chosen": p.chosen,
                "candidates": [(i, visible(w)) for i, w in p.candidates]} for p in (run.picks if run else [])],
        fixes=[(n, [visible(m) for m in messages]) for n, messages in run.problems] if run else [],
        unclear=sorted(run.unclear.items()) if run else [], add=add or set(), dates_ok=dates_ok,
        sending=len(chosen), left_out=run.left_out if run else [],
        checked=bring_in.fingerprint(info, text, mapping, picks or {}, add or set(), dates_ok) if run else "",
        operation=new_operation(), hint=dates.HINTS[style]), status


def _check(store, info, text, file_name, sheet, mapping, picks, add, dates_ok, notice=None):
    problems = bring_in.mapping_problems(store, info, mapping)
    if problems:
        return None, _page(store, info, text, file_name, sheet, mapping, notice=notice or "Check the matches.",
                           status=400)
    run = bring_in.plan(store, info, sheet, mapping, picks, file_name)
    return run, _page(store, info, text, file_name, sheet, mapping, run, picks, add, dates_ok, notice)


@bring_in_pages.post(PREFIX + "/<table>/check")
def check(table):
    store = _store()
    info = _info(store, table)
    if not _shown(info):
        return _start(store, info, shown=False, error="Press Show first.", status=400)
    try:
        carried = _carried(store, info)
    except PlainError as error:
        return _start(store, info, shown=True, error=str(error), status=400)
    return _check(store, info, *carried)[1]


@bring_in_pages.post(PREFIX + "/<table>/add")
def add(table):
    store = _store()
    info = _info(store, table)
    if not _shown(info):
        return _start(store, info, shown=False, error="Press Show first.", status=400)
    try:
        text, file_name, sheet, mapping, picks, chosen_add, dates_ok = _carried(store, info)
    except PlainError as error:
        return _start(store, info, shown=True, error=str(error), status=400)
    carried = (text, file_name, sheet, mapping, picks, chosen_add, dates_ok)
    earlier = bring_in.by_operation(store, info, request.form.get("operation", ""))
    if earlier is not None:  # the same page pressed twice: its entries were already added, once
        return redirect(url_for("bring_in.done", table=info.name, audit_id=earlier["id"]))
    if request.form.get("checked", "") != bring_in.fingerprint(info, text, mapping, picks, chosen_add, dates_ok):
        return _check(store, info, *carried, notice="Your choices changed since the rows were checked. Here is the "
                                                     "new check: look it over, then bring them in.")[1]
    run, page = _check(store, info, *carried)
    if run is None:
        return page
    rows = run.chosen(chosen_add)
    if len(rows) != request.form.get("count", -1, type=int):
        return _check(store, info, *carried, notice="Your records changed since the rows were checked. Here is the "
                                                     "new check: look it over, then bring them in.")[1]
    if not rows:
        return _check(store, info, *carried, notice="No rows are chosen to bring in.")[1]
    if any(r.number in run.unclear for r in rows) and not dates_ok:
        return _check(store, info, *carried, notice="Some dates could be read either way. Look at how each will be "
                                                     "read, then tick the box to say they are right.")[1]
    operation = request.form.get("operation", "")
    if not records.OPERATION.match(operation):
        return _check(store, info, *carried, notice="That page had expired. Here is the check again.")[1]
    try:
        audit_id = bring_in.add(store, info, rows, file_name, operation)
    except bring_in.StaleOrChanged as error:
        return _check(store, info, *carried, notice=str(error))[1]
    return redirect(url_for("bring_in.done", table=info.name, audit_id=audit_id))


def _done(store, info, audit_id: int, notice: str | None = None, error: str | None = None, status: int = 200):
    found = bring_in.summary(store, info, audit_id)
    if found is None:
        abort(404)
    one, many = bring_in.entry_words(info)
    return render_template("bring_in.html", step="done", info=info, title=display.table_title(info), one=one,
                           many=many, found=found, file=found.get("file") or "", notice=notice, error=error,
                           can_undo=bring_in.undo_problem(store, info, found) is None,
                           why_not=bring_in.undo_problem(store, info, found),
                           day=dates.show(found["at"][:10], dates.household_style(store.conn))), status


@bring_in_pages.get(PREFIX + "/<table>/done/<int:audit_id>")
def done(table, audit_id):
    store = _store()
    return _done(store, _info(store, table), audit_id)


@bring_in_pages.post(PREFIX + "/<table>/undo")
def undo(table):
    store = _store()
    info = _info(store, table)
    audit_id = request.form.get("bring_in", 0, type=int)
    if bring_in.summary(store, info, audit_id) is None:
        abort(404)
    try:
        removed = bring_in.undo(store, info, audit_id)
    except PlainError as error:
        return _done(store, info, audit_id, error=str(error), status=409)
    one, many = bring_in.entry_words(info)
    return _done(store, info, audit_id, notice=f"Undone: {removed} {one if removed == 1 else many} taken off "
                                               f"again. They stay in each entry's history.")
