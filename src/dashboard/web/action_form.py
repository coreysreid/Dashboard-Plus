"""An action's small form, such as Mark done: open it, save it once as one operation, and Undo it (decision 0091)."""
from __future__ import annotations

from flask import abort, redirect, render_template, request, url_for

from dashboard.core import actions, dates, records
from dashboard.web import display
from dashboard.web.pages import _info, _render_form, _store, pages


def _setup(table: str, record_id: int, key: str):
    info, store = _info(table), _store()
    try:
        action = actions.form_action(info, key)
        record = store.get(table, record_id)
    except records.RecordNotFound:
        abort(404)
    return info, store, action, record, actions.added_table(store, info, action)


def _fields(store, info, other, action, values, errors, from_form):
    """The asked fields, labelled "(optional)" when they may be left blank, with the action's own help."""
    fields = display.build_fields(store, other, values, errors, from_form, only=action["adds"]["ask"])
    style = dates.household_style(store.conn)
    for field in fields:
        if not field.column.required:
            field.label = f"{field.label} (optional)"
        words = action["help"].get(field.name)
        if words:
            field.help = f"{dates.HINTS[style]}. {words}" if field.kind == "date" else words
    return fields


def _render(info, store, action, record, other, values, errors=None, from_form=False, status=200, **extra):
    style = dates.household_style(store.conn)
    rule, latest = action.get("next_date"), action.get("latest")
    name = display.display_name(info, record, store)
    title = (display.action_word(info, action, "title") or display.action_words(info, action)[0]).replace(
        "{record}", name)
    done_on = values.get(latest["date"]) if latest else None
    if done_on and not dates.is_stored(str(done_on)):
        try:
            done_on = dates.parse(str(done_on), style)
        except ValueError:
            done_on = None
    next_box = None
    if rule:
        current = record.get(rule["into"])
        repeat = rule.get("repeat") or {}
        count, unit = record.get(repeat.get("count")), record.get(repeat.get("unit"))
        offered = actions.offer(action, record, done_on)
        next_box = {"question": rule["question"], "name": rule["into"], "hint": dates.HINTS[style] + ".",
                    "label": display.column_label(info, info.table.columns[rule["into"]]),
                    "current": dates.show(current, style) if current else None,
                    "has_repeat": bool(count and unit in dates.REPEAT_UNITS), "count": count, "unit": unit,
                    "offered": dates.show(offered, style) if offered else None,
                    "choice": request.form.get("next_choice") if from_form else None,
                    "date": request.form.get("next_date", "") if from_form else "",
                    "error": (errors or {}).get(rule["into"]) or (errors or {}).get("_next")}
    last = record.get(latest["into"]) if latest else None
    adds = action["adds"]
    return render_template(
        "action_form.html", info=info, other=other, record=record, record_name=name, title=title,
        intro=display.action_word(info, action, "intro"), key=action["key"], style=style,
        fields=_fields(store, info, other, action, values, errors or {}, from_form), errors=errors or {},
        next_box=next_box, save=f"Save {display.table_title(other).lower()}",
        last_text=(f"{display.column_label(info, info.table.columns[latest['into']])}: {dates.show(last, style)}"
                   if last else None),
        older=adds["add_button"] or f"Add to {display.table_title(other).lower()}",
        older_href=f"/t/{other.name}/new?{adds['link']}={record['id']}",
        record_href=f"/t/{info.name}/{record['id']}", table_title=display.table_title(info),
        date_field=latest["date"] if latest else None,
        **extra), status


@pages.get("/t/<table>/<int:record_id>/do/<key>")
def open_action_form(table, record_id, key):
    """The small form, with Done on filled in as today. Nothing is saved by opening or cancelling it."""
    info, store, action, record, other = _setup(table, record_id, key)
    values = {}
    for name in action["adds"]["ask"]:
        column = other.table.columns[name]
        default = records.resolve_default(column)
        if default is not None:
            values[name] = default
    latest, warning = action.get("latest"), None
    day = values.get(latest["date"]) if latest else None
    if actions.same_day(store, info, action, record_id, day):
        warning = action["messages"]["same_day"].replace("{date}", dates.show(day, dates.household_style(store.conn)))
    return _render(info, store, action, record, other, values, operation=actions.new_operation(),
                   revision=actions.revision(store, info, record_id), warning=warning)


def save_action_form(table, record_id, key):
    """Save the small form once (called from the action address's POST in pages.py)."""
    info, store, action, record, other = _setup(table, record_id, key)
    style = dates.household_style(store.conn)
    values, problems = display.values_from_form(other, request.form, style, only=action["adds"]["ask"])
    rule = action.get("next_date")
    typed_next = request.form.get("next_date", "").strip()
    next_date = None
    if rule and request.form.get("next_choice") == "date" and typed_next:
        try:
            next_date = dates.parse(typed_next, style)
        except ValueError as error:
            problems[rule["into"]] = str(error)
    seen = request.form.get("revision", "")
    op = request.form.get("operation", "")
    keep = {"operation": op, "revision": int(seen) if seen.isdecimal() and seen.isascii() else -1}
    raw = {k: request.form.get(k, "") for k in action["adds"]["ask"]}
    try:
        if problems:
            raise records.ValidationError(problems)
        actions.complete(store, table, record_id, key, values, keep["revision"], op,
                         next_choice=request.form.get("next_choice"), next_date=next_date,
                         past_ok=request.form.get("past_ok") or None)
    except records.RecordNotFound:
        abort(404)
    except records.ActionNotAvailable as error:  # changed while the form was open: nothing was saved
        fresh = store.get(table, record_id)
        return _render(info, store, action, fresh, other, raw, {"_form": str(error)}, True, status=409,
                       operation=op, revision=actions.revision(store, info, record_id))
    except records.ValidationError as error:
        errors = dict(error.problems)
        past = errors.pop("_past", None)
        chosen = next_date if request.form.get("next_choice") == "date" else \
            actions.offer(action, record, values.get((action.get("latest") or {}).get("date")))
        return _render(info, store, action, record, other, raw, errors, True, status=422, past=past,
                       past_ok=chosen if past else None, **keep)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id, done=key, op=op))


def done_notice(store, info, record_id: int, op: str | None) -> dict | None:
    """What a saved operation says on the record's page, worked out from what it saved, and whether it can
    still be undone: "Marked done on 19/11/26. Work done was saved. Do again by 19/02/27." """
    result = actions.operation(store, info, record_id, op) if op else None
    if result is None:
        return None
    action = next((a for a in info.table.actions if a["key"] == result["key"] and a.get("adds")), None)
    other = store.registry.get(result["added_table"])
    if action is None or other is None:
        return None
    formatter = display.Formatter(store)
    if result["undone"]:
        changed = " and ".join(display.column_label(info, info.table.columns[k]) for k in result["before"]
                               if k in info.table.columns)
        return {"words": f"Undone. The {display.table_title(other).lower()} entry was removed"
                         + (f", and {changed} {'are' if ' and ' in changed else 'is'} back to what "
                            f"{'they were' if ' and ' in changed else 'it was'}." if changed else "."),
                "undo": None}
    words = display.action_words(info, action)[1]
    for name, value in result["answers"].items():
        column = other.table.columns.get(name)
        if column is not None:
            words = words.replace("{" + name + "}", formatter.text(other, column, value) or "(blank)")
    if result.get("next"):
        due = result["after"].get(result["next"])
        column = info.table.columns[result["next"]]
        words += f" {display.column_label(info, column)} {formatter.text(info, column, due)}." if due \
            else f" {actions.NO_NEXT}"
    can = actions.can_undo(store, info, record_id, op)
    label = display.action_word(info, action, "undo")
    return {"words": words, "undo": {"label": label, "href": f"/t/{info.name}/{record_id}/undo/{op}"}
            if can and label else None}


@pages.post("/t/<table>/<int:record_id>/undo/<op>")
def undo_action(table, record_id, op):
    """Undo one saved operation, or say plainly why it can't be undone now (nothing is changed then)."""
    info, store = _info(table), _store()
    try:
        actions.undo(store, table, record_id, op)
    except records.RecordNotFound:
        abort(404)
    except records.ActionNotAvailable as error:
        try:
            record = store.get(table, record_id, include_deleted=True)
        except records.RecordNotFound:
            abort(404)
        return _render_form(info, store, record, {"_form": str(error)}, False, record=record, status=409)
    return redirect(url_for("pages.edit_record", table=table, record_id=record_id, op=op))
