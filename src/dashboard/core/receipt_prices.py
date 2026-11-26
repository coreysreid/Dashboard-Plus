"""A price a person types while accepting a Stock in on Review (decision 0133): checked first, saved only with their press of Accept, never read from a helper's receipt text."""
from __future__ import annotations

import json

from dashboard.core import db, proposals, records, records_prices
from dashboard.errors import PlainError

# The form fields of "Save a price with this Stock in?"; they are the same names as the Stock in's own columns.
FIELDS = ("price", "price_basis", "currency")


def typed(form) -> dict:
    """The price the person typed on a Review row or line, as {column: text}; empty when they left it blank.

    Only these three fields are ever read, and only from the person's own press: a helper has no way to send them
    (decisions 0097 and 0128), and the receipt's own price is shown as checking text and never filled in."""
    found = {k: (form.get(k) or "").strip() for k in FIELDS}
    if not found["price"]:
        return {}
    return {k: v for k, v in found.items() if v}


def offered(info) -> bool:
    """Whether this table's records can carry a typed price (a bought Stock in): `price` is declared."""
    return bool(info.table.price)


def offer(conn, info, values: dict) -> dict | None:
    """What "Save a price with this Stock in?" shows for a waiting row, or None when it is not a bought Stock in:
    the choices for what the price means, and the household's usual currency (so a blank one is understood)."""
    rule = info.table.price if info is not None else None
    if not rule or any(values.get(k, info.table.columns[k].default) != v for k, v in rule["only"].items()):
        return None
    from dashboard.core import settings
    basis = info.table.columns[rule["basis"]]
    return {"basis": [(c.key, c.label) for c in basis.choices],
            "currency": settings.household_choice(conn, "currency") or ""}


def words(info, problems: dict[str, str]) -> str:
    """The problems of a price in one plain sentence, each led by its field's own label."""
    labels = {"price": "What you paid", "price_basis": "That price is", "currency": "Currency"}
    rule = info.table.price
    names = {rule["paid"]: labels["price"], rule["basis"]: labels["price_basis"],
             rule["currency"]: labels["currency"]} if rule else {}
    return " ".join(f"{names.get(column, column)} {message}" for column, message in problems.items())


def check(conn, registry: dict, proposal_id: int, price: dict) -> None:
    """Look at a typed price against the suggestion it would go with, saving nothing but a reason when it is wrong:
    a PlainError (and the reason written on the waiting row) for each mistake, nothing when it can be saved. The
    Stock in's own reason and amount are read from the suggestion; nothing else of it is needed."""
    row = proposals._load(conn, proposal_id)
    info = registry.get(row["table_name"])
    if info is None or not price:
        return
    if not offered(info):
        keep_reason(conn, proposal_id, info, {info.table.name: "can't be saved with this row: it has no place "
                                                              "for a price."})
    store = records.Records(conn, registry)
    values = json.loads(row["values_json"])
    base = {k: values.get(k) for k in ("reason", "amount") if k in values}
    base.setdefault("reason", info.table.columns["reason"].default if "reason" in info.table.columns else None)
    try:
        cleaned = store.clean(info, dict(price), creating=False)
        records_prices.fill(conn, info, dict(base, **cleaned))
    except (records.ValidationError, records_prices.PriceProblems) as error:
        keep_reason(conn, proposal_id, info, dict(error.problems))


def keep_reason(conn, proposal_id: int, info, problems: dict[str, str]) -> None:
    """Write why the price was not saved on the waiting row, so the person sees it where they typed it. Nothing is
    added and the row keeps waiting."""
    # A helper reading its batch sees only that the row still waits (proposals.PRICE_NOT_SAVED, decision 0134).
    reason = f"{proposals.PRICE_NOT_SAVED} " + words(info, problems) + " Check it, or leave it blank."
    with db.transaction(conn):
        conn.execute("UPDATE core__proposals SET reason = ? WHERE id = ? AND status = 'pending'",
                     (reason, proposal_id))
    raise PlainError(reason)
