"""Count this batch: a stocktake of one batch, reviewed and then saved as one stocktake correction."""
from __future__ import annotations

from decimal import Decimal

from flask import abort, redirect, render_template, request, url_for

from dashboard.core import dates, records, schema
from dashboard.web import display
from dashboard.web.pages import _info, _store, pages


def _amount(value, unit: str | None) -> str:
    """"5 tins", "1.5 kg", "2": a number with the item's unit, if it has one."""
    number = Decimal(str(value or 0))
    text = f"{number:f}"
    text = text.rstrip("0").rstrip(".") if "." in text else text
    return f"{text} {unit}" if unit else text


def _context(store, info, batch_id):
    """What the count pages show about a batch: its item, where it is, its use-by date and amount."""
    movements = store.count_table(info.name)
    if movements is None:
        abort(404)
    try:
        batch = store.get(info.name, batch_id, include_deleted=True)
    except records.RecordNotFound:
        abort(404)
    rule = movements.table.adjusts
    owner_col = rule["belongs_to"]
    owner_info = store.registry[schema.target_table(info.module.name, info.table.columns[owner_col])]
    owner = store.get(owner_info.name, batch[owner_col], include_deleted=True)
    unit = owner.get("unit") if "unit" in owner_info.table.columns else None
    formatter = display.Formatter(store)
    where = [display.display_name(owner_info, owner, store)]
    for column in sorted(display.form_columns(info), key=lambda c: c.type != "link"):  # place, then dates
        value = batch.get(column.name)
        if column.name in (owner_col, rule["quantity"]) or column.type not in ("link", "date"):
            continue
        if column.type == "link" and value not in (None, ""):
            where.append(formatter.text(info, column, value))
        elif column.type == "date":
            label = display.column_label(info, column)
            where.append(f"{label} {formatter.text(info, column, value)}" if value else f"No {label.lower()} date")
    return {"info": info, "batch": batch, "owner": owner, "owner_info": owner_info, "unit": unit,
            "where": " · ".join(where), "movements": movements,
            "batch_href": f"/t/{info.name}/{batch_id}", "owner_href": f"/t/{owner_info.name}/{owner['id']}",
            "movements_href": f"/t/{movements.name}", "count_href": f"/t/{info.name}/{batch_id}/count",
            "recorded": _amount(batch[rule["quantity"]], unit), "recorded_value": batch[rule["quantity"]] or 0}


def _changed(seen: str, recorded: Decimal) -> bool:
    try:
        return Decimal(seen.strip()) != recorded
    except ArithmeticError:
        return True


def _across(held: int) -> str:
    return f"across {held} batches" if held != 1 else "in 1 batch"


def _render(ctx, step="count", status=200, **extra):
    return render_template("count.html", title=display.table_title(ctx["info"]), step=step, **ctx, **extra), status


@pages.get("/t/<table>/<int:record_id>/count")
def count_batch(table, record_id):
    """The count form, or what was saved once a count is done (?done=<correction> or ?same=1)."""
    info, store = _info(table), _store()
    ctx = _context(store, info, record_id)
    if ctx["batch"].get("deleted_at"):
        return _render(ctx, error="This batch was deleted, so it cannot be counted. Restore it first.", status=409)
    done = request.args.get("done", "")
    if done.isdecimal() and done.isascii():
        return _render(ctx, step="done", done=_done_words(store, ctx, int(done)))
    return _render(ctx, counted=request.args.get("counted", "")[:20])


def _done_words(store, ctx, movement_id: int) -> str | None:
    """"Count updated. This batch has 5 tins; Kidney beans has 15 tins across 2 batches. Stocktake correction:
    +2 tins, 18/11/26." From what is saved now, so a reload says the same."""
    movements, rule = ctx["movements"], ctx["movements"].table.adjusts
    try:
        movement = store.get(movements.name, movement_id)
    except records.RecordNotFound:
        return None
    if movement[rule["link"]] != ctx["batch"]["id"] or movement[rule["direction"]] not in rule["counts"].values():
        return None
    sign = "+" if movement[rule["direction"]] == rule["counts"]["more"] else "−"
    day = next((movement[c.name] for c in movements.table.columns.values() if c.type == "date" and c.default == "today"), None)
    held = store.conn.execute(
        f"SELECT COUNT(*) FROM {ctx['info'].name} WHERE deleted_at IS NULL AND {rule['belongs_to']} = ? "
        f"AND {rule['quantity']} > 0", (ctx["owner"]["id"],)).fetchone()[0]
    total = ctx["info"].table.total
    name = display.display_name(ctx["owner_info"], ctx["owner"], store)
    owner_words = f"; {name} has {_amount(ctx['owner'][total['into']], ctx['unit'])} {_across(held)}" if total else ""
    when = f", {dates.show(day, dates.household_style(store.conn))}" if day else ""
    return (f"Count updated. This batch has {ctx['recorded']}{owner_words}. "
            f"Stocktake correction: {sign}{_amount(movement[rule['amount']], ctx['unit'])}{when}.")


@pages.post("/t/<table>/<int:record_id>/count")
def review_or_save_count(table, record_id):
    """Review a count (step=review), or save it as one stocktake correction (step=save)."""
    info, store = _info(table), _store()
    ctx = _context(store, info, record_id)
    if ctx["batch"].get("deleted_at"):
        return _render(ctx, error="This batch was deleted, so it cannot be counted. Restore it first.", status=409)
    counted = request.form.get("counted", "")[:40]
    try:
        if request.form.get("step") == "save":
            result = store.count_batch(table, record_id, counted, request.form.get("recorded", ""))
            if result["status"] == "same":
                return _render(_context(store, info, record_id), same=True)
            return redirect(url_for("pages.count_batch", table=table, record_id=record_id, done=result["movement"]))
        plan = store.check_count(table, record_id, counted)
        seen = request.form.get("recorded", "")
        if seen and _changed(seen, plan["recorded"]):
            raise records.CountOutOfDate({}, plan["recorded"])  # it changed while the count form was open
    except records.CountOutOfDate:
        fresh = _context(store, info, record_id)
        return _render(fresh, counted=counted, status=409,
                       error=f"This batch now shows {fresh['recorded']}, so the count you reviewed is out of "
                             f"date. Check it again before saving.")
    except records.ValidationError as error:
        message = error.problems.get("counted") or " ".join(error.problems.values())
        return _render(ctx, counted=counted, status=422,
                       field_error=message if message[:1].isupper() else f"The number you counted {message}")
    if not plan["difference"]:
        return _render(ctx, same=True)
    unit, name = ctx["unit"], display.display_name(ctx["owner_info"], ctx["owner"], store)
    after = f"{name} will show {_amount(plan['owner_after'], unit)} {_across(plan['batches_holding'])}." \
        if plan["owner_after"] is not None else ""
    return _render(ctx, step="review", counted=counted, plan=plan, after=after,
                   counted_text=_amount(plan["counted"], unit),
                   difference_text=_amount(abs(plan["difference"]), unit))
