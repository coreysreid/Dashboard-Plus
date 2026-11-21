"""The Review screen: helpers' suggested new records and imported rows, waiting for a person to accept or reject each one."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from dashboard.core import csv_import, dates, helpers, proposals, records
from dashboard.core.proposals import HIDDEN_CHARACTERS
from dashboard.errors import PlainError
from dashboard.core.schema import target_table
from dashboard.web import display, helper_settings

review_pages = Blueprint("review", __name__)


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _module_title(table_name: str) -> str:
    name = table_name.split("__", 1)[0]
    return next((m.title for m in current_app.config["LOADED"] if m.name == name), name)


def visible(text: str) -> str:
    """Text with any hidden or text-reversing character shown as a plain replacement mark (U+FFFD).

    Suggestions with such characters are refused when sent (decision 0074); this is a second net, and also
    covers names already in the household's records that a suggestion links to."""
    return HIDDEN_CHARACTERS.sub("\ufffd", text)


def describe(store: records.Records, proposal: dict, made: dict | None = None, waiting: dict | None = None) -> dict:
    """One suggestion in plain words: where it would be added, and each value as a person reads it.

    A value pointing at another suggestion in its batch (decision 0097) is shown as the record that suggestion
    made (`made`: position to record id), or as "the new ... above" while it is still waiting (`waiting`:
    position to that row)."""
    info = store.registry.get(proposal["table_name"])
    if info is None:  # the module is switched off (or gone): show the title of its part, and no values
        return {"table": _module_title(proposal["table_name"]), "parts": [], "off": True,
                "module": _module_title(proposal["table_name"])}
    formatter = display.Formatter(store)
    values, pointed = dict(proposal["values"]), {}
    for field, ref in proposal.get("refs", {}).items():
        if made and ref in made:
            values[field] = made[ref]
        else:
            values.pop(field)
            pointed[field] = _new_above(store, info, field, (waiting or {}).get(ref))
    try:
        shown = store.clean(info, values, creating=False)  # read only: nothing is saved
    except records.ValidationError:
        shown = {k: v for k, v in values.items() if k in info.table.columns}
    parts = []
    for column in info.table.columns.values():
        if column.name in pointed:
            parts.append((display.column_label(info, column), visible(pointed[column.name])))
            continue
        if shown.get(column.name) in (None, "", []):
            continue
        try:
            text = formatter.text(info, column, shown[column.name])
        except Exception:  # noqa: BLE001 - a value that cannot be shown nicely is shown as typed
            text = str(shown[column.name])
        parts.append((display.column_label(info, column), visible(text)))
    return {"table": display.table_title(info), "parts": parts, "off": False, "module": info.module.title}


def _new_above(store: records.Records, info, field: str, row: dict | None) -> str:
    """How a link to a suggestion still waiting above reads: "Red lentils (new, suggested above)"."""
    target = store.registry.get(target_table(info.module.name, info.table.columns[field]))
    column = display.name_column(target) if target and row else None
    name = row["values"].get(column.name) if column else None
    if isinstance(name, str) and name.strip():
        return f"{name.strip()} (new, suggested above)"
    return "the new record suggested above"


MESSAGES = {"stale": "This row was already accepted or rejected.",
            "nothing": "Nothing is waiting on Review.",
            "none_ticked": "Nothing was ticked. Tick the rows you want first, then press Accept ticked or Reject ticked."}


def _message(args) -> tuple[str, str] | None:
    """The result line after a decision, built from fixed codes (never from text in the address)."""
    done, registry = args.get("done"), current_app.config["REGISTRY_FOR_REQUEST"]()
    table = registry.get(args.get("table", ""))
    title = display.table_title(table) if table else "your records"
    count = lambda key: max(0, min(args.get(key, 0, type=int), 10000))  # noqa: E731
    if done == "added":
        also = count("also")
        if also:
            return "notice", f"Added to {title}, together with the {also} row{'' if also == 1 else 's'} it needed."
        return "notice", f"Added to {title}."
    if done == "rejected":
        also = count("also")
        return "notice", f"Rejected. Nothing was added to {title}." + (
            f" {also} row{' that needed it was' if also == 1 else 's that needed it were'} rejected too." if also else "")
    if done == "added_many":
        left = count("left")
        text = f"Added {count('added')} record{'' if count('added') == 1 else 's'}."
        if left:
            text += f" {left} could not be added and {'is' if left == 1 else 'are'} still waiting: see the reasons below."
        return ("problem" if left else "notice"), text
    if done == "rejected_many":
        n = count("count")
        return "notice", f"Rejected {n} row{'' if n == 1 else 's'}. Nothing was added."
    if done == "imported":
        n = count("count")
        return "notice", (f"Sent {n} row{'' if n == 1 else 's'} from your spreadsheet to Review. Nothing is added to "
                          f"{title} until you accept {'it' if n == 1 else 'them'}.")
    if args.get("allowed"):
        conn = current_app.config["CONNECT"]()
        helper = helpers.get(conn, args.get("allowed", 0, type=int))
        if helper is not None:
            return "notice", (f"{helper.name} may now send {proposals.ALLOW_MORE} more suggestions today: "
                              f"{proposals.limit_today(conn, helper)} in all for today. Tomorrow its limit is back "
                              f"to {proposals.MAX_PER_DAY}.")
    if args.get("allow") in helper_settings.ALLOW_MESSAGES:
        return "problem", helper_settings.ALLOW_MESSAGES[args["allow"]]
    if done == "cannot":
        return "problem", "That suggestion could not be added. The reason is shown on it below."
    return ("notice", MESSAGES[done]) if done in MESSAGES else None


def _already_there(store: records.Records, cache: dict, item: dict) -> str | None:
    """For an imported row whose name is already in its list, the plain warning shown beside it (decision 0094)."""
    info = store.registry.get(item["table_name"])
    if info is None:
        return None
    if info.name not in cache:
        cache[info.name] = csv_import.SameName(store, info)
    name = cache[info.name].find(item["values"])
    if not name:
        return None
    title = display.table_title(info)
    text = f"Already exists: {name} is already in {title}. Accepting this row will make another {name}."
    if info.name == "stock__items":
        text += " To add what you bought, use Stock in; to correct a count, use Count this batch."
    return text


def _needing(waiting: list[dict], position: int) -> int:
    """How many waiting rows need the one at `position`, directly or through another: rejecting it rejects them."""
    hit = {position}
    for other in waiting:  # in position order, and a row only ever points at an earlier one
        if hit & set(other["refs"].values()):
            hit.add(other["position"])
    return len(hit) - 1


def _adds(items: list[dict]) -> str:
    """What Accept all would add, in plain words: "2 to Stock items and 1 to Stock in and out"."""
    counts: dict[str, int] = {}
    for item in items:
        counts[item["text"]["table"]] = counts.get(item["text"]["table"], 0) + 1
    parts = [f"{n} to {table}" for table, n in counts.items()]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


@review_pages.get("/review")
def review():
    conn, store = current_app.config["CONNECT"](), _store()
    batches = proposals.pending(conn)
    style = dates.household_style(conn)
    same = {}  # one look at each table's names, for imported rows that repeat one
    number = 0  # each row's place on the page, for the keys (Up, Down, A, R, Space)
    for batch in batches:
        batch["when"] = dates.show(batch["created_at"][:10], style)
        batch["why"] = visible(batch["why"])
        waiting = {item["position"]: item for item in batch["proposals"]}
        for item in batch["proposals"]:
            item["text"] = describe(store, item, batch["made"], waiting)
            item["exists"] = _already_there(store, same, item) if batch["kind"] == "import" else None
            item["source"] = {k: visible(v) for k, v in item["source"].items()} if item["source"] else None
            item["needs"] = sorted({ref for ref in item["refs"].values() if ref in waiting})
            item["needed_by"] = _needing(batch["proposals"], item["position"])
        batch["adds"] = _adds(batch["proposals"])
        for group in batch["groups"]:
            for item in group:
                number += 1
                item["number"] = number
    return render_template("review.html", batches=batches, message=_message(request.args),
                           waiting=sum(len(b["proposals"]) for b in batches),
                           limits=helper_settings.near_limits(conn), allow_more=proposals.ALLOW_MORE,
                           day_limit=proposals.MAX_PER_DAY)


def _back(**args):
    return redirect(url_for("review.review", **args))


@review_pages.post("/review/<int:proposal_id>/accept")
def accept(proposal_id):
    conn, registry = current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]()
    try:
        table, _record, also = proposals.accept_counted(conn, registry, proposal_id)
    except PlainError as error:
        # A reason worth keeping is already written on the suggestion; otherwise explain here.
        return _back(done="stale" if "already been decided" in str(error) or "could not be found" in str(error)
                     else "cannot")
    return _back(done="added", table=table, **({"also": also} if also else {}))


@review_pages.post("/review/<int:proposal_id>/reject")
def reject(proposal_id):
    try:
        table, also = proposals.reject_counted(current_app.config["CONNECT"](), proposal_id)
    except PlainError:
        return _back(done="stale")
    return _back(done="rejected", table=table, **({"also": also} if also else {}))


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


def _ticked() -> list[int]:
    return [int(v) for v in request.form.getlist("ids") if v.isdigit()][:proposals.MAX_WAITING * 4]


@review_pages.post("/review/ticked/accept")
def accept_ticked():
    """Accept the ticked rows; ticking one row of a group accepts its whole group, all or nothing (decision 0101)."""
    ids = _ticked()
    if not ids:
        return _back(done="none_ticked")
    conn, registry = current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]()
    added, failed = proposals.accept_ticked(conn, registry, ids)
    if not added and not failed:
        return _back(done="stale")
    return _back(done="added_many", added=added, left=len(failed))


@review_pages.post("/review/ticked/reject")
def reject_ticked():
    """Reject the ticked rows; ticking one row of a group rejects its whole group."""
    ids = _ticked()
    if not ids:
        return _back(done="none_ticked")
    count = proposals.reject_ticked(current_app.config["CONNECT"](), ids)
    return _back(done="rejected_many", count=count) if count else _back(done="stale")
