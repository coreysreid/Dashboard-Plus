"""Actions that add a linked record through a small form, like Mark done: one saved operation, a one-use number and Undo.

A table's `[[tables.<t>.actions]]` entry with `adds` (decision 0091) opens a short form on a record's page.
Saving it, in one transaction: adds one linked record (such as Work done) through the ordinary create path,
changes the record's own fields (such as Last done and Do again by) through the ordinary change path, and
writes one named operation in history. The form carries the record's revision (the newest history entry
for it), so a form left open while the record changed saves nothing, and a one-use operation number, so
a double click or a retried request returns the first result instead of saving twice. Undo is its own
audited transaction, refused when either record changed since.

A one-step button (decision 0075) saves its own named operation in `Records.action` (decision 0112): no record
is added, so its Undo only puts the record's fields back, under the same revision rule.
"""
from __future__ import annotations

import json
import secrets
from datetime import date

from dashboard.core import dates, db
from dashboard.core.modules import DEFAULT_MESSAGES
from dashboard.core.records import (OPERATION, ActionNotAvailable, ActionStale, RecordNotFound, Records,
                                    TableInfo, ValidationError, resolve_word)
from dashboard.core.schema import table_name

NO_NEXT = "No next reminder is set."
CHOICES = ("date", "repeat", "none")


def new_operation() -> str:
    """A fresh one-use operation number for a form (random, so it cannot be guessed or reused by chance)."""
    return secrets.token_urlsafe(18)


def form_action(info: TableInfo, key: str) -> dict:
    """The declared action `key` that adds a record, or RecordNotFound."""
    action = next((a for a in info.table.actions if a["key"] == key), None)
    if action is None or not action.get("adds"):
        raise RecordNotFound(f"There is no '{key}' form for {info.table.title.lower()}.")
    return action


def added_table(store: Records, info: TableInfo, action: dict) -> TableInfo:
    return store.registry[table_name(info.module.name, action["adds"]["table"])]


def revision(store: Records, info: TableInfo, record_id: int) -> int:
    """A number that goes up whenever the record changes: its newest history entry (0 when it has none)."""
    row = store.conn.execute("SELECT MAX(id) FROM core__audit WHERE table_name = ? AND record_id = ?",
                             (info.name, record_id)).fetchone()
    return row[0] or 0


def _repeat(action: dict, record: dict):
    """(count, unit, planned date, anchor day) of the record's own repeat, or None without one."""
    rule = (action.get("next_date") or {}).get("repeat")
    if not rule:
        return None
    count, unit = record.get(rule["count"]), record.get(rule["unit"])
    if not count or unit not in dates.REPEAT_UNITS:
        return None
    planned = record.get(rule["from"]) if rule.get("from") else None
    anchor = record.get(rule["anchor"]) if rule.get("anchor") else None
    try:
        day = date.fromisoformat(str(anchor)[:10]).day if anchor else None
    except ValueError:
        day = None
    return int(count), unit, planned, day


def offer(action: dict, record: dict, done_on: str | None) -> str | None:
    """The one next date the household's own repeat offers, or None without a repeat.

    Without `from`, it is one step after `done_on` (Home care, decision 0091). With `from` (a routine's planned
    date, decision 0107) it is the first repeat date after `done_on`, stepping from the planned date and keeping
    the anchor's day of the month; the dates in between are skipped, never filled in."""
    found = _repeat(action, record)
    if found is None or not done_on:
        return None
    count, unit, planned, day = found
    try:
        if (action["next_date"]["repeat"] or {}).get("from") and planned:
            return dates.next_after(planned, count, unit, done_on, day)
        return dates.add_period(done_on, count, unit, day)
    except (ValueError, OverflowError):
        return None


def missed(action: dict, record: dict, done_on: str | None) -> bool:
    """True when at least one whole repeat passed between the planned date and `done_on`: "Earlier times were
    not recorded." Nothing is filled in for them."""
    found = _repeat(action, record)
    if found is None or not done_on or not found[2] or not (action["next_date"]["repeat"] or {}).get("from"):
        return False
    count, unit, planned, day = found
    try:
        return dates.add_period(planned, count, unit, day) <= str(done_on)
    except (ValueError, OverflowError):
        return False


def same_day(store: Records, info: TableInfo, action: dict, record_id: int, day: str | None) -> bool:
    """True if a live linked record is already dated `day` (such as Work done for this job that day)."""
    latest = action.get("latest")
    if not latest or not latest.get("into") or not day:
        return False
    other, adds = added_table(store, info, action), action["adds"]
    return store.conn.execute(
        f"SELECT 1 FROM {other.name} WHERE deleted_at IS NULL AND {adds['link']} = ? AND {latest['date']} = ? "
        f"LIMIT 1", (record_id, day)).fetchone() is not None


def _what(info: TableInfo) -> str:
    """What one record is called in a reminder ("job"), for "the job will appear as overdue"."""
    expiring = info.table.watch.get("expiring") if isinstance(info.table.watch, dict) else None
    return (expiring or {}).get("what") or "record"


def _find(store: Records, operation: str, kind: str = "action", info: TableInfo | None = None,
          record_id: int | None = None):
    sql = "SELECT id, table_name, record_id, before, after FROM core__audit WHERE action = ? " \
          "AND json_extract(after, '$.operation') = ?"
    params: list = [kind, operation]
    if info is not None:
        sql += " AND table_name = ? AND record_id = ?"
        params += [info.name, record_id]
    return store.conn.execute(sql + " ORDER BY id LIMIT 1", params).fetchone()


def operation(store: Records, info: TableInfo, record_id: int, op: str) -> dict | None:
    """What one saved operation did: its key, the added record, and the fields before and after."""
    if not isinstance(op, str) or not OPERATION.match(op):
        return None
    row = _find(store, op, info=info, record_id=record_id)
    if row is None:
        return None
    result = json.loads(row["after"])
    result["undone"] = _find(store, op, "undo", info, record_id) is not None
    return result


def complete(store: Records, name: str, record_id: int, key: str, answers: dict, seen_revision: int, op: str,
             next_choice: str | None = None, next_date: str | None = None, past_ok: str | None = None,
             actor: str = "person", today: date | None = None) -> dict:
    """Save the form: add the linked record, change this record's fields, and write one named operation.

    `answers` are the asked fields of the added record, dates already in stored form (2026-11-19). If the
    record's revision is no longer `seen_revision`, ActionStale and nothing is saved. Sent again with the
    same `op`, the first result comes back with repeated=True and nothing new is saved. `next_choice` is
    "date" (with `next_date`), "repeat" or "none" when the action asks for a next date; a next date that has
    already passed needs `past_ok` set to that date, so the person has seen it will show as overdue."""
    store._check_actor(actor)
    info = store.info(name)
    action = form_action(info, key)
    if not isinstance(op, str) or not OPERATION.match(op):
        raise ValidationError({"_form": "This form is out of date. Open it again from the record's page."})
    today_text = (today or date.today()).isoformat()
    with db.transaction(store.conn):
        earlier = _find(store, op)
        if earlier is not None:
            result = json.loads(earlier["after"])
            if (earlier["table_name"], earlier["record_id"], result.get("key")) != (info.name, record_id, key):
                raise ActionNotAvailable("That form was already used for something else. Nothing was changed.")
            return dict(result, repeated=True)
        current = store._row(info, record_id)
        if revision(store, info, record_id) != seen_revision:
            raise ActionStale(action["messages"]["stale"])
        other, adds = added_table(store, info, action), action["adds"]
        values = {n: answers.get(n) for n in adds["ask"]}
        values.update({k: resolve_word(other.table.columns[k], v) for k, v in adds["values"].items()})
        values.update({into: current.get(source) for into, source in adds.get("copy", {}).items()})
        values[adds["link"]] = record_id
        problems: dict[str, str] = {}
        latest, rule = action.get("latest"), action.get("next_date")
        if latest and values.get(latest["date"]) in (None, ""):
            problems[latest["date"]] = "is required."
        try:
            cleaned = store.clean(other, values, creating=True)
        except ValidationError as error:
            problems = {**error.problems, **problems}
            cleaned = {}
        sets = {k: resolve_word(info.table.columns[k], v) for k, v in action["set"].items()}
        style = dates.household_style(store.conn)
        day = cleaned.get(latest["date"]) if latest and latest["date"] not in problems else None
        if day:
            label = store._label(other, latest["date"])
            previous = current.get(latest["into"]) if latest.get("into") else None
            if day > today_text:
                problems[latest["date"]] = f"{label} can't be after today."
            elif previous and day < str(previous):
                problems[latest["date"]] = (f"{label} can't be before {store._label(info, latest['into'])} "
                                            f"({dates.show(previous, style)}). Record older work as an older "
                                            f"entry instead; that changes no dates here.")
            elif same_day(store, info, action, record_id, day):
                problems[latest["date"]] = action["messages"]["same_day"].replace("{date}", dates.show(day, style))
            elif latest.get("into"):
                sets[latest["into"]] = day
        if rule:
            into_label, chosen = store._label(info, rule["into"]), None
            if next_choice == "date":
                if next_date in (None, ""):
                    problems[rule["into"]] = f"{into_label} is needed when you choose a date."
                else:
                    try:
                        chosen = date.fromisoformat(str(next_date)).isoformat()
                    except ValueError:
                        problems[rule["into"]] = dates.problem(style)
            elif next_choice == "repeat":
                chosen = offer(action, current, day)
                if chosen is None and day:
                    problems["_next"] = "There is no repeat to use. Choose a date, or No date yet."
            elif next_choice != "none":
                has_repeat = offer(action, current, day or today_text) is not None
                problems["_next"] = "Choose one: a date, " + ("your repeat, " if has_repeat else "") + "or No date yet."
            if chosen and day and chosen < day:
                problems[rule["into"]] = f"{into_label} can't be before {store._label(other, latest['date'])}."
            elif chosen and chosen < today_text and past_ok != chosen and not problems:
                problems["_past"] = f"This date has passed, so the {_what(info)} will appear as overdue. " \
                                    f"Save again to keep it."
            sets[rule["into"]] = chosen
        if problems:
            raise ValidationError(problems)
        before = {k: current.get(k) for k in sets}
        added = store._create(other, values, actor)
        store._update(info, record_id, sets, actor)
        saved = store._row(info, record_id)
        result = {"key": key, "operation": op, "added_table": other.name, "added": added,
                  "added_revision": revision(store, other, added), "before": before,
                  "after": {k: saved.get(k) for k in sets}, "next": rule["into"] if rule else None,
                  "answers": {k: cleaned.get(k) for k in adds["ask"]},
                  "copied": {k: cleaned.get(k) for k in adds.get("copy", {})},
                  "counts_as": action.get("counts_as", "done"), "missed": missed(action, current, day)}
        store._audit(actor, "action", info, record_id, before, result)
        return dict(result, repeated=False)


def declared(info: TableInfo, key: str) -> dict | None:
    """The declared action `key` of either kind (a one-step button or a small form), or None."""
    return next((a for a in info.table.actions if a["key"] == key), None)


def _undo_check(store: Records, info: TableInfo, record_id: int, op: str):
    """The saved operation, if it can still be undone; otherwise ActionNotAvailable or ActionStale.

    A one-step press (decision 0112) added no record, so only the record itself must be as the press left it."""
    row = _find(store, op, info=info, record_id=record_id) if isinstance(op, str) and OPERATION.match(op) else None
    if row is None:
        raise RecordNotFound("That completion was not found.")
    result = json.loads(row["after"])
    if _find(store, op, "undo", info, record_id) is not None:
        raise ActionNotAvailable("That was already undone. Nothing was changed.")
    action = declared(info, result["key"])
    if action is None:
        raise RecordNotFound("That completion was not found.")
    refused = ActionStale((action.get("messages") or DEFAULT_MESSAGES)["undo_refused"])
    one_step = not result.get("added_table")
    other = None if one_step else store.registry.get(result["added_table"])
    if (other is None and not one_step) or revision(store, info, record_id) != row["id"]:
        raise refused  # the record changed, a later operation was saved, or it was deleted and restored
    if not one_step:
        added = store.conn.execute(f"SELECT deleted_at FROM {other.name} WHERE id = ?",
                                   (result["added"],)).fetchone()
        if added is None or added["deleted_at"] or revision(store, other, result["added"]) != result["added_revision"]:
            raise refused
    try:
        store._row(info, record_id)
    except RecordNotFound:
        raise refused from None
    return result, other


def can_undo(store: Records, info: TableInfo, record_id: int, op: str) -> bool:
    """True while Undo would still work for this operation (nothing about either record changed since)."""
    try:
        _undo_check(store, info, record_id, op)
    except (RecordNotFound, ActionNotAvailable):
        return False
    return True


def undo(store: Records, name: str, record_id: int, op: str, actor: str = "person") -> dict:
    """Undo one saved operation, in one transaction: delete the record it added (kept in history, as every
    delete is) and put this record's fields back exactly as they were. A one-step press (decision 0112) only
    puts the fields back. Refused, changing nothing, if either record changed since or it was already undone.
    Returns the operation as it was saved."""
    store._check_actor(actor)
    info = store.info(name)
    with db.transaction(store.conn):
        result, other = _undo_check(store, info, record_id, op)
        if other is not None:
            store._delete(other, result["added"], actor, set(), f"{other.name}:{result['added']}")
        store._update(info, record_id, dict(result["before"]), actor)
        store._audit(actor, "undo", info, record_id, result["after"],
                     {"key": result["key"], "operation": op, "added_table": other.name if other else None,
                      "added": result["added"]})
    return result
