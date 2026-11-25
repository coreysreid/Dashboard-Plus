"""Confirmed purchase prices on a Stock in (decision 0128): what a person typed, whether it is the total or the price for each, the line total worked out from it, and its currency."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from dashboard.core import settings

# The two ways a person can say what a price means. Nothing else is ever guessed (decision 0097: a receipt's
# price on Review is checking text only).
BASES = ("total", "each")


def fill(conn, info, record: dict, current: dict | None = None) -> dict:
    """Check the price on one record about to be saved and work out what goes with it.

    `record` is the record as it will be (for a change: the saved record with the new values on top). Returns the
    values to store for the price's own columns: the line total and the currency, or the basis, total and currency
    cleared when no price was typed. Raises PriceProblems ({column: words}), which the caller turns into a
    ValidationError. A price on a record that is not a bought Stock in, or without saying whether it is the total
    or the price for each, is refused, so nothing is ever guessed."""
    rule = info.table.price
    paid, basis, total, currency, amount = (rule[k] for k in ("paid", "basis", "total", "currency", "amount"))
    price = record.get(paid)
    if price is None:
        return {basis: None, total: None, currency: None}
    problems = {}
    wrong = {k: v for k, v in rule["only"].items() if record.get(k) != v}
    if wrong:
        problems[paid] = rule["only_words"]
    chosen = record.get(basis)
    if chosen not in BASES:
        problems[basis] = ("say whether the price is the total for these goods or the price for each one. Leave "
                           "the price blank if you are unsure.")
    code = (record.get(currency) or "").strip().upper()
    if current is not None and not code and current.get(currency):
        code = current[currency]  # a change that leaves the currency alone keeps it
    if not code:
        code = settings.household_choice(conn, "currency") or ""
    if not code:
        problems[currency] = ("say which currency this was paid in, like EUR, or choose the household's usual "
                              "currency in Settings.")
    elif not (len(code) == 3 and code.isalpha() and code.isascii()):
        problems[currency] = "must be a three-letter currency code, like AUD, EUR or USD."
    if problems:
        raise PriceProblems(problems)
    line = price
    if chosen == "each":
        count = Decimal(str(record.get(amount) or 0))
        line = int((Decimal(int(price)) * count).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {total: line, currency: code}


class PriceProblems(Exception):
    """What is wrong with a typed price, by column, in plain words."""

    def __init__(self, problems: dict[str, str]):
        super().__init__("; ".join(problems.values()))
        self.problems = problems
