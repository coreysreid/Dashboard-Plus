"""Money back on a priced Stock in (decision 0133): a refund is linked to that Stock in, always in its currency, and never more than was paid unless the person says so."""
from __future__ import annotations

from decimal import Decimal

from dashboard.core.schema import target_table


class RefundProblems(Exception):
    """What is wrong with a refund, by column, in plain words."""

    def __init__(self, problems: dict[str, str]):
        super().__init__("; ".join(problems.values()))
        self.problems = problems


def _money(cents: int, currency: str) -> str:
    return f"{Decimal(int(cents)) / 100:,.2f} {currency}".strip()


def fill(conn, info, registry: dict, record: dict, record_id: int | None) -> dict:
    """Check one refund about to be saved and work out its currency.

    `record` is the refund as it will be (for a change: the saved refund with the new values on top) and `record_id`
    its own id (None for a new one), so it is not counted twice against what was paid. The Stock in it is for must
    have a price saved; the money back is more than 0 and in that Stock in's currency; all the money back for one
    Stock in together may not be more than was paid unless the person ticked the yes that says that is right.
    Returns {currency column: code}. Raises RefundProblems ({column: words})."""
    rule = info.table.refund
    link, amount_column, currency, confirm = (rule[k] for k in ("of", "amount", "currency", "confirm"))
    problems = {}
    cents = record.get(amount_column)
    if cents is not None and int(cents) <= 0:
        problems[amount_column] = "must be more than 0. Money back is the amount that came back to you."
    target = registry[target_table(info.module.name, info.table.columns[link])]
    stock_in = conn.execute(f"SELECT * FROM {target.name} WHERE id = ? AND deleted_at IS NULL",
                            (record.get(link),)).fetchone()
    if stock_in is None:
        problems[link] = "must be a Stock in that is still saved."
    elif stock_in[rule["paid"]] is None:
        problems[link] = ("has no price saved. Save what you paid on that Stock in first, so the money back has "
                          "something to come off.")
    if problems:
        raise RefundProblems(problems)
    code = stock_in[rule["currency_of"]]
    typed = (record.get(currency) or "").strip().upper()
    if typed and typed != code:
        raise RefundProblems({currency: f"is always the one the Stock in was paid in ({code}), so it is filled in "
                                        f"for you."})
    paid = int(stock_in[rule["paid"]])
    back = conn.execute(
        f"SELECT COALESCE(SUM({amount_column}), 0) FROM {info.name} WHERE deleted_at IS NULL AND {link} = ? "
        f"AND id != ?", (stock_in["id"], record_id if record_id is not None else -1)).fetchone()[0]
    if cents is not None and back + int(cents) > paid and not record.get(confirm):
        raise RefundProblems({amount_column: (
            f"would put the money back for this Stock in ({_money(back + int(cents), code)}) above what was paid "
            f"({_money(paid, code)}). Check the amounts. If that is right, for example a deposit, tick "
            f"\"This is more than was paid\" and save again.")})
    return {currency: code}
