"""Tidy sensitive details (decision 0141): the page that lists saved codes and full numbers and tidies each one.

Values are in the page only after a pressed Show. Each is kept as its last 4 digits, replaced by where it is kept, or
removed, with a backup first and Undo."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request

from dashboard.core import backups, records, tidy
from dashboard.web import display

tidy_pages = Blueprint("tidy", __name__)

KINDS = {"retired": "No longer kept here", "guard": "Holds a code or number", "card": "Holds a full card number"}
CHOICES = {tidy.LAST4: "Keep only the last 4 digits", tidy.WHERE: "Write where it is kept instead",
           tidy.REMOVE: "Remove it"}
DONE = {tidy.LAST4: "Only the last 4 digits are kept.", tidy.WHERE: "Where it is kept is written down instead.",
        tidy.REMOVE: "It was removed."}


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _field_label(info, name: str) -> str:
    if name in info.table.retired:  # the words it had before it was retired, from tables.toml
        return info.table.retired[name].retired.get("label") or name.replace("_", " ").capitalize()
    column = info.table.columns.get(name)
    return display.column_label(info, column) if column is not None else name


def _record_name(store, info, record_id: int) -> str:
    try:
        return display.display_name(info, store.get(info.name, record_id, include_deleted=True), store)
    except records.RecordNotFound:
        return f"Record {record_id}"


def _page(store, show: bool, notice=None, problem=None, status=200):
    items = []
    for item in tidy.find(store):
        items.append({"key": item.key, "list": display.table_title(item.info),
                      "field": _field_label(item.info, item.column), "kind": KINDS[item.kind],
                      "name": _record_name(store, item.info, item.record_id), "deleted": item.deleted,
                      "value": item.value if show else None,
                      "choices": [(c, CHOICES[c]) for c in item.options], "where": tidy.WHERE in item.options})
    done = []
    for entry in tidy.recent(store):
        info = store.registry.get(entry["table"])
        if info is None:
            continue
        done.append(dict(entry, list=display.table_title(info), field=_field_label(info, entry["field"]),
                         name=_record_name(store, info, entry["record_id"]), words=DONE.get(entry["choice"], "")))
    keeping = any(not e["undone"] and not e["forgotten"] for e in done)
    return render_template("tidy.html", items=items, show=show, done=done, keeping=keeping, notice=notice,
                           problem=problem, max_hint=tidy.MAX_HINT), status


def _backup() -> None:
    data_dir = current_app.config.get("DATA_DIR")
    if data_dir is not None:
        backups.before_tidy(data_dir, current_app.config.get("EXTRA_BACKUP_DIR"))


@tidy_pages.get("/tidy")
def page():
    """The list by count and field, no saved value in the page."""
    store = _store()
    notice = {"done": "Tidied. A backup was made first.", "undone": "Undone. The detail is back as it was.",
              "forgotten": "The old values are forgotten."}.get(request.args.get("result", ""))
    return _page(store, False, notice=notice)


@tidy_pages.post("/tidy/show")
def show():
    """Show: the same page with each saved value, this time only (pressed, never a link; never cached)."""
    return _page(_store(), True)


@tidy_pages.post("/tidy/do")
def do():
    store = _store()
    try:
        item = tidy.one(store, request.form.get("key", ""))
        choice = request.form.get("choice", "")
        if choice not in item.options:
            raise tidy.TidyRefused("Choose what to do with this detail. Nothing was changed.")
        tidy.apply(store, item, choice, request.form.get("hint"), backup=_backup)  # a backup first, once checked
    except tidy.TidyRefused as error:
        return _page(store, False, problem=str(error), status=409)
    return redirect("/tidy?result=done")


@tidy_pages.post("/tidy/undo")
def undo():
    store = _store()
    number = request.form.get("tidy", "")
    try:
        if not number.isdecimal():
            raise tidy.TidyRefused("That tidy could not be found. Nothing was changed.")
        _backup()
        tidy.undo(store, int(number))
    except tidy.TidyRefused as error:
        return _page(store, False, problem=str(error), status=409)
    return redirect("/tidy?result=undone")


@tidy_pages.post("/tidy/forget")
def forget():
    store = _store()
    _backup()
    tidy.forget(store)
    return redirect("/tidy?result=forgotten")
