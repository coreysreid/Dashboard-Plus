"""Settings, Import from a spreadsheet: choose a table, upload a CSV, match its columns, check the rows, send to Review.

The uploaded file is read in memory and never written to disk or kept after the request: between steps its text
travels inside the page itself (a hidden field), and every step checks it again from the start (decision 0080).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io

from flask import Blueprint, Request, current_app, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge

from dashboard.core import csv_import, proposals, records
from dashboard.errors import PlainError
from dashboard.web import display
from dashboard.web.review import describe, visible

imports = Blueprint("imports", __name__)
PREFIX = "/settings/import"
# The whole request may carry the file once more as text in the page (a third larger), plus the matches.
REQUEST_LIMIT = 3 * csv_import.MAX_BYTES
PREVIEW_ROWS = 5
SHOWN_READY = 10


class UploadRequest(Request):
    """A request that keeps an imported file in memory only; every other request is unchanged.

    Werkzeug normally writes uploads over 500 KB to a temporary file. For the import pages the upload is held in
    memory instead, and the request is refused above REQUEST_LIMIT before anything is read."""

    def _import(self) -> bool:
        return self.path == PREFIX or self.path.startswith(PREFIX + "/")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._import():  # the limits Flask lets one request set for itself
            self.max_content_length = REQUEST_LIMIT
            self.max_form_memory_size = REQUEST_LIMIT

    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        if self._import():
            return io.BytesIO()
        return super()._get_file_stream(total_content_length, content_type, filename, content_length)


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _tables(store: records.Records) -> tuple[list[dict], list[str]]:
    """Tables a spreadsheet can go into, grouped by part, and plain reasons for those it can't."""
    groups, refused = {}, []
    for info in store.registry.values():
        reason = csv_import.why_not_table(info)
        if reason:
            refused.append(reason)
            continue
        groups.setdefault(info.module.title, []).append({"name": info.name, "title": display.table_title(info)})
    return [{"module": m, "tables": t} for m, t in groups.items()], refused


def _choose(error: str | None = None, status: int = 200, table: str | None = None):
    store = _store()
    groups, refused = _tables(store)
    return render_template("import.html", step="choose", groups=groups, refused=refused, error=error,
                           chosen=table or request.args.get("table", ""), limit=csv_import.LIMIT_TEXT,
                           max_rows=csv_import.MAX_ROWS), status


@imports.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return _choose(f"This file is too large. The limit is {csv_import.LIMIT_TEXT}: split it into smaller files "
                   f"and import each one.", 413)


@imports.get(PREFIX)
def choose():
    return _choose()


def _table(store: records.Records, name: str):
    info = store.registry.get(name or "")
    if info is None or csv_import.why_not_table(info):
        raise PlainError("Choose the list to import into.")
    return info


@imports.post(PREFIX)
def upload():
    store = _store()
    try:
        info = _table(store, request.form.get("table"))
    except PlainError as error:
        return _choose(str(error), 400)
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return _choose("Choose a CSV file to import.", 400, info.name)
    data = upload.stream.read()  # at most REQUEST_LIMIT, held in memory (UploadRequest)
    upload.stream.close()  # the file is gone after this request; only its text travels in the page
    try:
        text = csv_import.decode(data)
        sheet = csv_import.parse(text)
    except csv_import.FileProblem as error:
        return _choose(str(error), 413 if len(data) > csv_import.MAX_BYTES else 400, info.name)
    mapping = csv_import.auto_match(store, info, sheet.headers)
    return _match_page(store, info, text, proposals.source_label(upload.filename), sheet, mapping)


def _carried(store: records.Records):
    """The table, file text, file name, sheet and matches the page sent back; checked again from the start."""
    info = _table(store, request.form.get("table"))
    try:
        data = base64.b64decode(request.form.get("data", ""), validate=True)
    except (binascii.Error, ValueError):
        raise PlainError("That page had expired. Choose the file again.") from None
    text = csv_import.decode(data)
    sheet = csv_import.parse(text)
    mapping = [request.form.get(f"match_{i}", "") for i in range(len(sheet.headers))]
    return info, text, proposals.source_label(request.form.get("file_name", "")), sheet, mapping


def _fingerprint(info, text: str, mapping: list[str]) -> str:
    return hashlib.sha256("\n".join([info.name, text, *mapping]).encode("utf-8")).hexdigest()


def _match_page(store, info, text, file_name, sheet, mapping, run=None, notice=None, status=200):
    usable, _private = csv_import.fields(store, info)
    options = [{"name": c.name, "label": display.column_label(info, c), "required": c.required and c.default is None}
               for c in usable]
    private = csv_import.private_headers(store, info, sheet.headers)
    columns = [{"index": i, "header": visible(h) or f"Column {i + 1} (no heading)", "chosen": mapping[i],
                "private": private.get(i)} for i, h in enumerate(sheet.headers)]
    preview = [(n, [visible(cell) for cell in cells]) for n, cells in sheet.rows[:PREVIEW_ROWS]]
    problems = csv_import.mapping_problems(store, info, mapping) if run is not None or notice else []
    ready = []
    if run is not None:
        for number, values in run.ready[:SHOWN_READY]:
            ready.append({"row": number, "text": describe(store, {"table_name": info.name, "values": values})})
    return render_template(
        "import.html", step="match", info=info, title=display.table_title(info), file_name=file_name,
        data=base64.b64encode(text.encode("utf-8")).decode("ascii"), columns=columns, options=options,
        preview=preview, row_count=len(sheet.rows), run=run, ready=ready, problems=problems, notice=notice,
        fixes=[(n, [visible(m) for m in messages]) for n, messages in run.problems] if run else [],
        checked=_fingerprint(info, text, mapping) if run is not None else ""), status


def _check(store, info, text, file_name, sheet, mapping, notice=None):
    problems = csv_import.mapping_problems(store, info, mapping)
    if problems:
        return None, _match_page(store, info, text, file_name, sheet, mapping, notice=notice or "Check the matches.",
                                 status=400)
    run = csv_import.dry_run(store, info, sheet, mapping)
    return run, _match_page(store, info, text, file_name, sheet, mapping, run=run, notice=notice)


@imports.post(PREFIX + "/check")
def check():
    store = _store()
    try:
        info, text, file_name, sheet, mapping = _carried(store)
    except PlainError as error:
        return _choose(str(error), 400)
    return _check(store, info, text, file_name, sheet, mapping)[1]


@imports.post(PREFIX + "/send")
def send():
    store = _store()
    try:
        info, text, file_name, sheet, mapping = _carried(store)
    except PlainError as error:
        return _choose(str(error), 400)
    if request.form.get("checked", "") != _fingerprint(info, text, mapping):
        return _check(store, info, text, file_name, sheet, mapping,
                      notice="The matches changed since the rows were checked. Here is the new check: "
                             "look it over, then send.")[1]
    run, page = _check(store, info, text, file_name, sheet, mapping)
    if run is None:
        return page
    if len(run.ready) != request.form.get("ready", -1, type=int):
        return _check(store, info, text, file_name, sheet, mapping,
                      notice="Your records changed since the rows were checked. Here is the new check: "
                             "look it over, then send.")[1]
    if not run.ready:
        return page
    batch = proposals.stage_import(store.conn, file_name, csv_import.staged(info, run))
    return redirect(url_for("review.review", done="imported", count=len(run.ready), table=info.name,
                            _anchor=f"batch-{batch}"))
