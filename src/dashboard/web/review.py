"""The Review screen: helpers' suggested new records, waiting for a person to accept or reject each one."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from dashboard.core import dates, proposals, records
from dashboard.errors import PlainError
from dashboard.web import display

review_pages = Blueprint("review", __name__)


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _module_title(table_name: str) -> str:
    name = table_name.split("__", 1)[0]
    return next((m.title for m in current_app.config["LOADED"] if m.name == name), name)


def describe(store: records.Records, proposal: dict) -> dict:
    """One suggestion in plain words: where it would be added, and each value as a person reads it."""
    info = store.registry.get(proposal["table_name"])
    if info is None:  # the module is switched off (or gone): show the title of its part, and no values
        return {"table": _module_title(proposal["table_name"]), "parts": [], "off": True,
                "module": _module_title(proposal["table_name"])}
    formatter = display.Formatter(store)
    try:
        shown = store.clean(info, proposal["values"], creating=False)  # read only: nothing is saved
    except records.ValidationError:
        shown = {k: v for k, v in proposal["values"].items() if k in info.table.columns}
    parts = []
    for column in info.table.columns.values():
        if shown.get(column.name) in (None, "", []):
            continue
        try:
            text = formatter.text(info, column, shown[column.name])
        except Exception:  # noqa: BLE001 - a value that cannot be shown nicely is shown as typed
            text = str(shown[column.name])
        parts.append((display.column_label(info, column), text))
    return {"table": display.table_title(info), "parts": parts, "off": False, "module": info.module.title}


MESSAGES = {"stale": "That suggestion had already been decided.",
            "nothing": "Nothing was waiting to be decided."}


def _message(args) -> tuple[str, str] | None:
    """The result line after a decision, built from fixed codes (never from text in the address)."""
    done, registry = args.get("done"), current_app.config["REGISTRY_FOR_REQUEST"]()
    table = registry.get(args.get("table", ""))
    title = display.table_title(table) if table else "your records"
    count = lambda key: max(0, min(args.get(key, 0, type=int), 10000))  # noqa: E731
    if done == "added":
        return "notice", f"Added to {title}."
    if done == "rejected":
        return "notice", f"Rejected. Nothing was added to {title}."
    if done == "added_many":
        left = count("left")
        text = f"Added {count('added')}."
        if left:
            text += f" {left} could not be added and {'is' if left == 1 else 'are'} still waiting: see the reasons below."
        return ("problem" if left else "notice"), text
    if done == "rejected_many":
        n = count("count")
        return "notice", f"Rejected {n} suggestion{'' if n == 1 else 's'}. Nothing was added."
    if done == "cannot":
        return "problem", "That suggestion could not be added. The reason is shown on it below."
    return ("notice", MESSAGES[done]) if done in MESSAGES else None


@review_pages.get("/review")
def review():
    conn, store = current_app.config["CONNECT"](), _store()
    batches = proposals.pending(conn)
    style = dates.household_style(conn)
    for batch in batches:
        batch["when"] = dates.show(batch["created_at"][:10], style)
        for item in batch["proposals"]:
            item["text"] = describe(store, item)
    return render_template("review.html", batches=batches, message=_message(request.args),
                           waiting=sum(len(b["proposals"]) for b in batches))


def _back(**args):
    return redirect(url_for("review.review", **args))


@review_pages.post("/review/<int:proposal_id>/accept")
def accept(proposal_id):
    conn, registry = current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]()
    try:
        table, _record = proposals.accept(conn, registry, proposal_id)
    except PlainError as error:
        # A reason worth keeping is already written on the suggestion; otherwise explain here.
        return _back(done="stale" if "already been decided" in str(error) or "could not be found" in str(error)
                     else "cannot")
    return _back(done="added", table=table)


@review_pages.post("/review/<int:proposal_id>/reject")
def reject(proposal_id):
    try:
        table = proposals.reject(current_app.config["CONNECT"](), proposal_id)
    except PlainError:
        return _back(done="stale")
    return _back(done="rejected", table=table)


@review_pages.post("/review/batch/<int:batch_id>/accept-all")
def accept_all(batch_id):
    conn, registry = current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]()
    added, failed = proposals.accept_batch(conn, registry, batch_id)
    if not added and not failed:
        return _back(done="nothing")
    return _back(done="added_many", added=added, left=len(failed))


@review_pages.post("/review/batch/<int:batch_id>/reject-all")
def reject_all(batch_id):
    count = proposals.reject_batch(current_app.config["CONNECT"](), batch_id)
    return _back(done="rejected_many", count=count) if count else _back(done="nothing")
