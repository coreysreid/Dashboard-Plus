"""Review, a receipt line the helper could not match: choose its Stock item or make a new one, then confirm amount and date."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from dashboard.core import actions, dates, receipts, records, receipt_prices
from dashboard.core.units import unit_for
from dashboard.errors import PlainError
from dashboard.web import display, review
from dashboard.web.review import visible

line_pages = Blueprint("receipt_line", __name__)
MOST_ITEMS = 2000  # items offered in the picker, by name


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _back(done: str, **args):
    return redirect(url_for("review.review", done=done, **args))


def _line(store: records.Records, line_id: int) -> dict:
    """The line, its movement table (Stock in and out) and item table (Stock items), or a PlainError."""
    row = receipts.line(store.conn, line_id)
    if row["status"] != "pending":
        raise PlainError("decided")
    info = store.registry.get(row["table_name"])
    owner = receipts.owner_of(store.registry, info) if info is not None else None
    if owner is None:
        raise PlainError("off")
    hints = json.loads(row["values_json"])
    source = json.loads(row["source_json"]) if row["source_json"] else {}
    who = f"Import '{row['source_name']}'" if row["batch_kind"] == "import" else (row["helper_name"] or "The helper")
    return {"row": row, "info": info, "owner": owner, "hints": hints, "who": visible(who),
            "source": {k: visible(v) for k, v in source.items()}, "style": dates.household_style(store.conn)}


def _item_fields(owner) -> list[str]:
    """What a new item needs on this form: its name, its unit, and anything else it must have (its category)."""
    name = display.name_column(owner)
    wanted = []
    for column in display.form_columns(owner):
        if column.name in (name.name if name else None, "unit") or column.required_when or \
                (column.required and column.default is None and column.type in ("text", "choice")) or \
                (column.required and column.type == "choice"):
            wanted.append(column.name)
    return wanted


def _date_text(ctx: dict, typed: str | None) -> str:
    """The date to start with: what the person typed, else the date on the paper, else today, for them to check."""
    if typed is not None:
        return typed
    return dates.show(ctx["hints"].get("receipt_date") or date.today().isoformat(), ctx["style"])


def _page(ctx: dict, step: str, status: int = 200, **more):
    more.setdefault("typed", {})
    offer = receipt_prices.offer(current_app.config["CONNECT"](), ctx["info"], {})  # a price only a person types (0133)
    return render_template("review_line.html", ctx=ctx, step=step, hint=dates.HINTS[ctx["style"]] + ".", offer=offer,
                           owner_title=display.table_title(ctx["owner"]),
                           owner_noun=review.noun(ctx["owner"], {}), **more), status


def _amount_hint(ctx: dict, unit: str | None, name: str) -> tuple[str, str | None]:
    """(amount to start with, a note) from the helper's hint: used only when its unit is the item's own unit."""
    quantity, hinted = ctx["hints"].get("quantity_hint"), ctx["hints"].get("unit_hint")
    if not quantity:
        return "", None
    if receipts.units_fit(hinted, unit):
        return quantity, None
    counted = f"counted in {unit}" if unit else "counted without a unit"
    return "", visible(f"The helper read the amount as {quantity} {hinted}, but {name} is {counted}. Type how much "
                       f"you brought home in the item's own unit. Nothing is worked out for you.")


def _existing(store: records.Records, ctx: dict, item_id: int, errors: dict | None = None, typed: dict | None = None,
              status: int = 200):
    owner = ctx["owner"]
    try:
        item = store.get(owner.name, item_id)
    except PlainError:
        return _pick(store, ctx, error="Choose one of your Stock items, or make a new one.", status=400)
    name = display.display_name(owner, item, store)
    unit = item.get("unit") if "unit" in owner.table.columns else None
    amount, note = _amount_hint(ctx, unit, name)
    typed = typed or {}
    return _page(ctx, "amount", status, typed=typed, item=item, item_name=visible(name), unit=visible(unit or ""),
                 units=visible(unit_for(2, unit) if unit else ""), revision=actions.revision(store, owner, item_id),
                 amount=typed.get("amount", amount), note=note, when=_date_text(ctx, typed.get("when")),
                 errors=errors or {})


def _pick(store: records.Records, ctx: dict, error: str | None = None, status: int = 200):
    owner = ctx["owner"]
    column = display.name_column(owner)
    rows = store.page(owner.name, limit=MOST_ITEMS, order_by=column.name if column else "id")
    options = []
    for row in rows:
        unit = row.get("unit") if "unit" in owner.table.columns else None
        label = display.display_name(owner, row, store) + (f" (in {unit})" if unit else "")
        options.append((row["id"], visible(label)))
    options.sort(key=lambda option: option[1].lower())
    return _page(ctx, "pick", status, options=options, error=error)


def _new(store: records.Records, ctx: dict, values: dict | None = None, errors: dict | None = None,
         typed: dict | None = None, status: int = 200):
    owner, only = ctx["owner"], _item_fields(ctx["owner"])
    fields = display.build_fields(store, owner, values or {}, errors or {}, from_form=values is not None, only=only)
    typed = typed or {}
    return _page(ctx, "new", status, typed=typed, fields=fields, amount=typed.get("amount", ctx["hints"].get("quantity_hint", "")
                 if not ctx["hints"].get("unit_hint") else ""), when=_date_text(ctx, typed.get("when")),
                 errors=errors or {}, item_info=owner)


@line_pages.get("/review/line/<int:line_id>")
def choose(line_id):
    """"Choose item": pick one of the household's own Stock items, or make a new one (decision 0105)."""
    store = _store()
    try:
        ctx = _line(store, line_id)
    except PlainError as error:
        return _back("line_stale" if str(error) == "decided" else "stale")
    if request.args.get("new"):
        return _new(store, ctx)
    item = request.args.get("item", "")
    if item.isdigit():
        return _existing(store, ctx, int(item))
    return _pick(store, ctx)


def _amount_and_date(ctx: dict) -> tuple[str | None, str | None, dict]:
    """The amount and date the person typed, checked: (amount, date, problems)."""
    problems, amount, when = {}, request.form.get("amount", "").strip(), request.form.get("when", "").strip()
    try:
        number = Decimal(amount)
        if not number.is_finite() or number <= 0:
            raise InvalidOperation
    except InvalidOperation:
        problems["amount"] = "Type how much you brought home, as a number above 0."
        number = None
    stored = None
    try:
        stored = dates.parse(when, ctx["style"]) if when else None
        if stored is None:
            problems["when"] = "Type the date you bought it."
    except ValueError as error:
        problems["when"] = str(error)
    return (format(number, "f") if number is not None else None), stored, problems


@line_pages.post("/review/line/<int:line_id>/save")
def save(line_id):
    """"Save this Stock in": one Stock in, and a new item with it if the person made one, saved together once."""
    store = _store()
    try:
        ctx = _line(store, line_id)
    except PlainError as error:
        return _back("line_stale" if str(error) == "decided" else "stale")
    amount, when, problems = _amount_and_date(ctx)
    typed = {"amount": request.form.get("amount", ""), "when": request.form.get("when", ""),
             **{k: request.form.get(k, "") for k in receipt_prices.FIELDS}}
    price = receipt_prices.typed(request.form)
    making = bool(request.form.get("new"))
    owner = ctx["owner"]
    if making:
        only = _item_fields(owner)
        values, date_problems = display.values_from_form(owner, request.form, ctx["style"], only=only)
        if problems or date_problems:
            return _new(store, ctx, values, dict(problems, **date_problems), typed, status=400)
    else:
        item = request.form.get("item", "")
        if not item.isdigit():
            return _pick(store, ctx, error="Choose one of your Stock items, or make a new one.", status=400)
        if problems:
            return _existing(store, ctx, int(item), problems, typed, status=400)
    try:
        if making:
            receipts.add_for_line(store, line_id, amount, when, new_item=values, price=price)
        else:
            receipts.add_for_line(store, line_id, amount, when, item_id=int(item),
                                  seen_revision=request.form.get("revision", -1, type=int), price=price)
    except receipts.LineStale as error:
        return _existing(store, ctx, int(item), {"_form": str(error)}, typed, status=409)
    except records.ValidationError as error:
        labelled = {field: f"{display.column_label(owner, owner.table.columns[field])} {message}"
                    if field in owner.table.columns else message for field, message in error.problems.items()}
        if making:
            return _new(store, ctx, values, {"_form": "Nothing was saved. " + " ".join(labelled.values()),
                                             **error.problems}, typed, status=400)
        return _existing(store, ctx, int(item), {"_form": "Nothing was saved. " + " ".join(labelled.values())},
                         typed, status=400)
    except PlainError:
        return _back("line_stale")
    return _back("line_added", line=line_id)
