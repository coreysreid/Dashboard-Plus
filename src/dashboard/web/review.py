"""The Review screen: helpers' suggested new records and imported rows, waiting for a person to accept or reject each one."""
from __future__ import annotations

import json

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from dashboard.core import csv_import, dates, helpers, move_in, proposals, receipts, records, receipt_prices
from dashboard.core.proposals import HIDDEN_CHARACTERS
from dashboard.core.units import unit_for
from dashboard.errors import PlainError
from dashboard.core.schema import target_table
from dashboard.web import display, helper_settings
from dashboard.web.daily_pages import review_note

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
    return HIDDEN_CHARACTERS.sub("�", text)


def _singular(title: str) -> str:
    """"Stock items" reads "Stock item" when it names one row; "Batches", "Batch"; "Places", "Place"."""
    if title.endswith("ies"):
        return title[:-3] + "y"
    if title.endswith(("ches", "shes", "sses", "xes")):
        return title[:-2]
    if title.endswith("s") and not title.endswith("ss"):
        return title[:-1]
    return title


def noun(info, values: dict) -> str:
    """What one row is called on Review: "Stock item", and for a movement "Stock in" or "Stock out"."""
    title = display.table_title(info)
    rule = info.table.adjusts
    if rule and rule.get("belongs_to") and title.endswith(" in and out"):
        direction = values.get(rule["direction"]) or info.table.columns[rule["direction"]].default
        return f"{title[:-len(' in and out')]} {'in' if direction in rule['adds'] else 'out'}"
    return _singular(title)


def movement_words(store: records.Records, info, values: dict, made: dict | None = None,
                   waiting: dict | None = None) -> tuple[str | None, set[str]]:
    """A Stock in or out in one plain sentence, and the fields it already says (Lane B, batch 19 item 82).

    "Add 1 pack of Demo red lentils on 20/11/26": the amount with the item's own unit (singular for exactly 1),
    the item's name, and the date. For an item suggested in the same batch and still waiting, its suggested name
    and unit are used. Read only: nothing is saved. (None, set()) for anything that is not a movement."""
    rule = info.table.adjusts
    if not rule or not rule.get("belongs_to") or values.get(rule["amount"]) in (None, ""):
        return None, set()
    owner_info = receipts.owner_of(store.registry, info)
    if owner_info is None:
        return None, set()
    owner, name, unit = values.get(rule["belongs_to"]), None, None
    ref = proposals.ref_of(owner)
    if ref is not None:
        if made and ref in made:
            owner = made[ref]
        else:
            row = (waiting or {}).get(ref)
            column = display.name_column(owner_info)
            name = row["values"].get(column.name) if row and column else None
            if not isinstance(name, str) or not name.strip():
                return None, set()
            name, unit = name.strip(), row["values"].get("unit")
    if name is None:
        try:
            record = store.get(owner_info.name, int(owner), include_deleted=True)
        except (PlainError, TypeError, ValueError, LookupError):
            return None, set()
        name = display.display_name(owner_info, record, store)
        unit = record.get("unit") if "unit" in owner_info.table.columns else None
    try:
        number = display._number_text(values[rule["amount"]])
    except (ArithmeticError, ValueError):
        return None, set()
    direction = values.get(rule["direction"]) or info.table.columns[rule["direction"]].default
    adds = direction in rule["adds"]
    unit = unit.strip() if isinstance(unit, str) else ""
    if unit:
        text = f"{'Add' if adds else 'Take away'} {number} {unit_for(number, unit)} of {name}"
    else:
        text = f"Add {number} to {name}" if adds else f"Take away {number} from {name}"
    when_column, used = receipts.date_column(info), {rule["belongs_to"], rule["amount"]}
    when = values.get(when_column) if when_column else None
    if when and dates.is_stored(str(when)):
        text += f" on {dates.show(when, dates.household_style(store.conn))}"
        used.add(when_column)
    if direction == rule["adds"][0]:
        used.add(rule["direction"])  # "Add" already says "Bought or added"
    return text, used


def describe(store: records.Records, proposal: dict, made: dict | None = None, waiting: dict | None = None) -> dict:
    """One suggestion in plain words: where it would be added, and each value as a person reads it.

    A value pointing at another suggestion in its batch (decision 0097) is shown as the record that suggestion
    made (`made`: position to record id), or as "the new ... above" while it is still waiting (`waiting`:
    position to that row). A Stock in or out leads with one sentence that says its amount, unit, item and date."""
    info = store.registry.get(proposal["table_name"])
    if info is None:  # the module is switched off (or gone): show the title of its part, and no values
        return {"table": _module_title(proposal["table_name"]), "parts": [], "off": True,
                "module": _module_title(proposal["table_name"]), "noun": _module_title(proposal["table_name"])}
    formatter = display.Formatter(store)
    values, pointed = dict(proposal["values"]), {}
    lead, said = movement_words(store, info, values, made, waiting)
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
    parts = [("", visible(lead))] if lead else []
    for column in info.table.columns.values():
        if column.name in said:
            continue
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
    return {"table": display.table_title(info), "parts": parts, "off": False, "module": info.module.title,
            "noun": noun(info, proposal["values"])}


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
            "none_ticked": "Nothing was ticked. Tick the rows you want first, then press Accept ticked or Reject ticked.",
            "held": receipts.HELD,
            "line_skipped": "Skipped this line. No Stock amount changed.",
            "line_unskipped": "This line is waiting again. Nothing was added.",
            "line_stale": "This receipt line was already decided. Nothing more was added.",
            "copy_rejected": "Rejected this copy. No Stock amount changed from it.",
            "kept": "Treat this as a separate purchase. Check each row before accepting.",
            "not_kept": "This receipt no longer looks like an earlier one, so there was nothing to keep."}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _and(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _added_words(args, registry) -> str | None:
    """"Added 1 to Stock items and 3 to Stock in and out.", from table names and counts in the address."""
    parts = []
    for item in args.getlist("n")[:20]:
        table, _sep, number = item.rpartition(":")
        if table in registry and number.isdigit():
            parts.append(f"{min(int(number), 10000)} to {display.table_title(registry[table])}")
    return f"Added {_and(parts)}." if parts else None


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
        text = _added_words(args, registry) or f"Added {_plural(count('added'), 'record')}."
        if not count("added"):
            text = "Nothing was added."
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
    if done == "line_added":
        words = _line_added_words(args.get("line", 0, type=int))
        if words:
            return "notice", f"{words} Review the remaining lines."
    if done == "finished":
        conn = current_app.config["CONNECT"]()
        return "notice", "Finished this receipt: " + receipts.outcome_text(
            receipts.outcome(conn, args.get("batch", 0, type=int)))
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
    if done in ("held", "not_kept", "line_stale"):
        return "problem", MESSAGES[done]
    return ("notice", MESSAGES[done]) if done in MESSAGES else None


def _line_added_words(line_id: int) -> str | None:
    """"Added 1 tin of Tinned tomatoes from this line.", read from the records, never from the address."""
    store = _store()
    try:
        row = receipts.line(store.conn, line_id)
    except PlainError:
        return None
    info = store.registry.get(row["table_name"])
    if row["status"] != "accepted" or info is None or not row["record_id"]:
        return None
    record = store.get(info.name, row["record_id"], include_deleted=True)
    words, _said = movement_words(store, info, record)
    if not words:
        return None
    return f"Added{words[len('Add'):]} from this line." if words.startswith("Add ") else f"{words}."


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
    return _and([f"{n} to {table}" for table, n in counts.items()]) if counts else ""


def group_words(group: list[dict]) -> str:
    """What the buttons of rows that go together do, true under group-by-group Accept all (decisions 0097, 0101).

    Accept on one row adds it and the new records it needs, never the rows that need it; Reject on a new
    record also rejects the rows that need it; Accept all and Accept ticked add a whole group or none of it."""
    news = [p for p in group if p["needed_by"]]
    needers = [p for p in group if p["needs"]]
    if len(group) == 2 and len(news) == 1 and len(needers) == 1:
        new, need = news[0]["text"]["noun"], needers[0]["text"]["noun"]
        return (f"Accepting the {need} also adds its new {new}. Accepting only the {new} leaves the {need} waiting. "
                f"Rejecting the {new} rejects the {need} too. Ticking one ticks both, and Accept all or Accept ticked "
                f"adds both or neither.")
    return ("Accepting a row also adds the new records above it that it needs. Accepting only a new record leaves the "
            "rows that need it waiting. Rejecting a new record rejects the rows that need it too. Ticking one ticks "
            "them all, and Accept all or Accept ticked adds the whole group or none of it.")


def _line_view(store: records.Records, line: dict, style: str) -> dict:
    """One receipt line the helper could not match, as Review shows it (decision 0105)."""
    hints, info = line["values"], store.registry.get(line["table_name"])
    shown = []
    if hints.get("receipt_date"):
        shown.append(f"Date on the paper: {dates.show(hints['receipt_date'], style)}")
    if hints.get("quantity_hint"):
        amount = hints["quantity_hint"] + (f" {hints['unit_hint']}" if hints.get("unit_hint") else "")
        shown.append(f"Amount as the helper read it: {amount}")
    elif hints.get("unit_hint"):
        shown.append(f"Unit as the helper read it: {hints['unit_hint']}")
    view = {"id": line["id"], "position": line["position"], "source": {k: visible(v) for k, v in
                                                                        (line["source"] or {}).items()},
            "hints": [visible(h) for h in shown], "off": info is None,
            "module": _module_title(line["table_name"]),
            "status": {"pending": "waiting", "accepted": "added", "rejected": "skipped"}[line["status"]]}
    if view["status"] == "added" and info is not None and line["record_id"]:
        record = store.get(info.name, line["record_id"], include_deleted=True)
        words, _said = movement_words(store, info, record)
        view["added"] = visible(f"Added{words[len('Add'):]}." if words and words.startswith("Add ") else
                                (words or "Added a Stock in") + ".")
        view["now"] = _now_has(store, info, record)
    return view


def _now_has(store: records.Records, info, movement: dict) -> str | None:
    """"Tinned tomatoes now has 4 tins.": the item's current amount, read now."""
    owner = receipts.owner_of(store.registry, info)
    if owner is None:
        return None
    try:
        item = store.get(owner.name, int(movement[info.table.adjusts["belongs_to"]]))
    except (PlainError, TypeError, ValueError, LookupError):
        return None
    for batch in store._totals_into(owner):
        amount = item.get(batch.table.total["into"])
        if amount is None:
            continue
        number = display._number_text(amount)
        unit = item.get("unit") if "unit" in owner.table.columns else None
        unit = f" {unit_for(number, unit)}" if unit else ""
        return visible(f"{display.display_name(owner, item, store)} now has {number}{unit}.")
    return None


def _repeat_view(conn, store: records.Records, batch: dict, style: str, on_review: set[int]) -> dict | None:
    """The possible-repeat warning for one receipt batch, in the person's words (decision 0105), or None."""
    found = receipts.possible_repeat(conn, store.registry, batch["id"])
    if found is None:
        return None
    earlier, items = found["batch"], found["items"]
    if earlier["kind"] == "import":
        who = f"from your spreadsheet import '{earlier['source_name']}'"
    else:
        who = f"by {earlier['helper_name'] or 'a helper'}"
    goods = found["matched"] + len(found["only_here"])
    return {"level": found["level"], "kept": found["kept"], "earlier": earlier["id"],
            "when": dates.show(earlier["created_at"][:10], style), "who": visible(who),
            "goods": goods, "matched": found["matched"], "state": receipts.state_words(found["states"]),
            "only_here": [visible(receipts.line_words(line, items, style)) for line in found["only_here"]],
            "only_there": [visible(receipts.line_words(line, items, style)) for line in found["only_there"]],
            "on_review": earlier["id"] in on_review}


def private_words(store: records.Records, hits: list[tuple[str, str]]) -> str | None:
    """"This may hold a private detail you keep in Vehicles (Registration)...": which private field, never its value."""
    named = []
    for table, column in hits:
        info = store.registry.get(table)
        if info is not None and column in info.table.columns:
            named.append(f"{display.table_title(info)} ({display.column_label(info, info.table.columns[column])})")
    if not named:
        return None
    return (f"This may hold a private detail you keep in {_and(named)}. Private details belong only in their "
            f"private field, typed by you. Reject this, or accept it and then remove that text.")


@review_pages.get("/review")
def review():
    conn, store = current_app.config["CONNECT"](), _store()
    batches = proposals.pending(conn)
    # Private text the household already keeps, compared in memory for this page only (decision 0112).
    known = move_in.private_values(conn, store.registry) if batches else {}
    style = dates.household_style(conn)
    same = {}  # one look at each table's names, for imported rows that repeat one
    number = 0  # each row's place on the page, for the keys (Up, Down, A, R, Space)
    on_review = {b["id"] for b in batches}
    for batch in batches:
        batch["when"] = dates.show(batch["created_at"][:10], style)
        batch["why"] = visible(batch["why"])
        waiting = {item["position"]: item for item in batch["proposals"]}
        twice = move_in.count_twice(store.registry, batch["records"])  # a starting amount counted twice (0112)
        batch["private"] = private_words(store, move_in.private_copies(known, batch["why"])) \
            if batch["kind"] != "import" else None
        for item in batch["proposals"]:
            item["text"] = describe(store, item, batch["made"], waiting)
            item["twice"] = twice.get(item["position"])
            item["private"] = private_words(store, move_in.private_copies(known, item["values"], item["source"]))
            item["exists"] = _already_there(store, same, item) if batch["kind"] == "import" else None
            item["price_offer"] = receipt_prices.offer(conn, store.registry.get(item["table_name"]), item["values"])
            item["repeat"] = review_note(store, item)  # a feeding that may be sent twice (decision 0110)
            item["source"] = {k: visible(v) for k, v in item["source"].items()} if item["source"] else None
            item["needs"] = sorted({ref for ref in item["refs"].values() if ref in waiting})
            item["needed_by"] = _needing(batch["proposals"], item["position"])
        for item in batch["proposals"]:
            item["needs_nouns"] = [waiting[ref]["text"]["noun"] for ref in item["needs"]]
        batch["adds"] = _adds(batch["proposals"])
        batch["twice"] = sum(1 for item in batch["proposals"] if item["twice"])
        batch["lines"] = [_line_view(store, line, style) for line in batch["lines"]]
        batch["lines_waiting"] = sum(1 for line in batch["lines"] if line["status"] == "waiting")
        batch["repeat"] = _repeat_view(conn, store, batch, style, on_review) if batch["receipt"] else None
        batch["held"] = bool(batch["repeat"] and batch["repeat"]["level"] == "repeat" and not batch["repeat"]["kept"])
        batch["finishing"] = bool(batch["lines"]) and not batch["proposals"] and not batch["lines_waiting"]
        if batch["finishing"]:
            batch["outcome"] = receipts.outcome_text(receipts.outcome(conn, batch["id"]))
        units = [{"kind": "group", "rows": group, "at": group[0]["position"],
                  "words": group_words(group) if len(group) > 1 else ""} for group in batch["groups"]]
        units += [{"kind": "line", "line": line, "at": line["position"]} for line in batch["lines"]]
        batch["units"] = sorted(units, key=lambda unit: unit["at"])
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


def _tally_args(tally: dict) -> dict:
    return {"n": [f"{table}:{n}" for table, n in tally.items()]} if tally else {}


@review_pages.post("/review/<int:proposal_id>/accept")
def accept(proposal_id):
    conn, registry = current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]()
    price = receipt_prices.typed(request.form)  # "Save a price with this Stock in?" (decision 0133)
    try:
        if price:
            receipt_prices.check(conn, registry, proposal_id, price)  # a mistake is kept as the row's reason
        table, _record, also = proposals.accept_counted(conn, registry, proposal_id, price or None)
    except receipts.RepeatHeld:
        return _back(done="held")
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
    if receipts.held(conn, registry, batch_id):
        return _back(done="held")
    tally: dict = {}
    added, failed = proposals.accept_batch(conn, registry, batch_id, tally)
    if not added and not failed:
        return _back(done="nothing")
    return _back(done="added_many", added=added, left=len(failed), **_tally_args(tally))


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
    tally: dict = {}
    added, failed = proposals.accept_ticked(conn, registry, ids, tally)
    if not added and not failed:
        return _back(done="stale")
    return _back(done="added_many", added=added, left=len(failed), **_tally_args(tally))


@review_pages.post("/review/ticked/reject")
def reject_ticked():
    """Reject the ticked rows; ticking one row of a group rejects its whole group."""
    ids = _ticked()
    if not ids:
        return _back(done="none_ticked")
    count = proposals.reject_ticked(current_app.config["CONNECT"](), ids)
    return _back(done="rejected_many", count=count) if count else _back(done="stale")


# ----- receipts: lines a helper could not match, and a receipt sent twice (decision 0105) -------------

@review_pages.post("/review/line/<int:line_id>/skip")
def skip_line(line_id):
    try:
        receipts.skip(current_app.config["CONNECT"](), line_id)
    except PlainError:
        return _back(done="line_stale")
    return _back(done="line_skipped")


@review_pages.post("/review/line/<int:line_id>/undo-skip")
def undo_skip(line_id):
    try:
        receipts.undo_skip(current_app.config["CONNECT"](), line_id)
    except PlainError:
        return _back(done="stale")
    return _back(done="line_unskipped")


@review_pages.post("/review/batch/<int:batch_id>/finish")
def finish(batch_id):
    try:
        receipts.finish(current_app.config["CONNECT"](), batch_id)
    except PlainError:
        return _back(done="stale")
    return _back(done="finished", batch=batch_id)


@review_pages.post("/review/batch/<int:batch_id>/keep")
def keep(batch_id):
    try:
        receipts.keep(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"](), batch_id)
    except PlainError:
        return _back(done="not_kept")
    return _back(done="kept", _anchor=f"batch-{batch_id}")


@review_pages.get("/review/batch/<int:batch_id>")
def earlier(batch_id):
    """"Open earlier receipt": one receipt's rows and what became of each, read only (decision 0105)."""
    conn, store = current_app.config["CONNECT"](), _store()
    batch = conn.execute("SELECT b.*, h.name AS helper_name FROM core__helper_batches b LEFT JOIN core__helpers h "
                         "ON h.id = b.helper_id WHERE b.id = ? AND b.receipt_json IS NOT NULL", (batch_id,)).fetchone()
    if batch is None:
        return _back(done="stale")
    style = dates.household_style(conn)
    rows = []
    for row in conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? ORDER BY position", (batch_id,)):
        item = proposals._row_dict(row)
        info = store.registry.get(row["table_name"])
        if row["entry_kind"] == "receipt_line":
            view = _line_view(store, item, style)
            words = (view.get("added") or "") if view["status"] == "added" else \
                ("Skipped: nothing was added." if view["status"] == "skipped" else "Still waiting for your choice.")
            rows.append({"what": "Receipt line: " + (view["source"].get("line") or ""), "state": words})
            continue
        text = describe(store, item)
        state = {"pending": "Still waiting.", "rejected": "Rejected: nothing was added."}.get(row["status"], "Added.")
        if row["status"] == "accepted" and info is not None:
            live = conn.execute(f"SELECT deleted_at FROM {info.name} WHERE id = ?", (row["record_id"],)).fetchone()
            if live is None or live["deleted_at"]:
                state = "Added, then undone: it has since been deleted."
        rows.append({"what": f"{text['table']}: " + " · ".join(f"{label}: {t}" if label else t
                                                              for label, t in text["parts"]), "state": state})
    who = f"Import '{batch['source_name']}'" if batch["kind"] == "import" else (batch["helper_name"] or "A helper")
    return render_template("review_batch.html", rows=rows, who=visible(who),
                           when=dates.show(batch["created_at"][:10], style),
                           bought=dates.show(json.loads(batch["receipt_json"])["purchase_date"], style))


@review_pages.post("/review/batch/<int:batch_id>/reject-copy")
def reject_copy(batch_id):
    """"Reject this copy": this batch's waiting rows only (and their dependants); the earlier one is untouched."""
    conn = current_app.config["CONNECT"]()
    count = proposals.reject_batch(conn, batch_id)
    return _back(done="copy_rejected") if count else _back(done="nothing")
