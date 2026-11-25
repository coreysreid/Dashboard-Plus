# 0133. Money back on a priced Stock in, and a price typed on Review

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0097 (a receipt's price on Review is checking text only), 0100 (what travels), 0105 (receipt
  lines), 0111 (amounts in their own unit, never converted), 0121 (Show is a pressed button), 0124 (bars over
  time), 0128 (what you paid and Spent per month, which listed these three follow-ups)

## In plain words
Three small things 0128 left open, all about the money a household typed on a bought Stock in.

1. **Money back.** If something you paid for is refunded, open that Stock in and press **Record money back**: pick
   the day and type how much came back. It is tied to that Stock in, always in the same currency as its price, and
   the program asks you to tick **This is more than was paid** if the money back for one Stock in ever adds up to
   more than you paid. **Spent per month** then says, beside the bar, "3.80 AUD spent, less 3.00 refunded" (in the
   month the money came back) and in the table. The bar itself is never taken down and no bar is ever negative,
   so a refund that arrives in a later month never makes an earlier month look cheaper.
2. **A price on Review.** On Review, a bought Stock in a helper read from a receipt gets **Save a price with this
   Stock in?** (also when you choose the item for a receipt line the helper could not match). You type what you
   paid and say whether it is the total or the price for each one; it is saved when you press Accept, together with
   the Stock in. The receipt's own price is shown next to it as words to check against, and is never filled in or
   copied. A helper still cannot send a price.
3. **The line total.** A Stock in's page says "Line total (worked out from the price, not typed)" with a **Show**
   button, so you can see what a price for each pack comes to (2 packs at 1.80 each is 3.60) without a field to
   type it into.

## What we chose
- **A new table, Money back** (`stock__refunds`, stock migration 0009, one `CREATE TABLE`, nothing else touched):
  `movement` (a required link to the Stock in, `on_delete = "restrict"` so a Stock in with money back cannot be
  removed from under it), `happened_on` (the day the money came back, today by default), `amount` (money, required),
  `currency`, `over_paid` (a tick) and `notes`. Amount, currency, the tick and the notes are private and
  `travels = "never"`, the same promise as a price (0128): never on a list, a sheet, the export, a helper or the
  change log's values. A helper that suggests money back is refused with 403 `private_detail`.
- **A generic `[tables.<t>.refund]` declaration** (`of`, `when`, `paid`, `currency_of`, `amount`, `currency`,
  `confirm`), checked when the module loads in plain words (`_check_refund`), and `core/records_refunds.py` on the one
  write path: the Stock in must still exist and **have a price** ("Save what you paid on that Stock in first"); the
  amount is more than 0; the currency is the Stock in's own (a different one typed is refused, none is guessed); the
  money back for one Stock in, this one included, may not pass the line total unless `over_paid` is ticked. A
  correction is not counted against itself, and a deleted refund no longer counts.
- **A refund does not change the stock.** Money coming back and goods going back are different facts: a shop may
  refund a damaged tin you keep, or give credit for goods you still hold. So the refund form says it does not change
  the amount, and the person chooses the other half themselves: a new Stock out reason **Returned to the shop**
  (a new choice on Stock in and out; a choice is stored as text, so no existing row or migration changes) takes the
  goods off the shelf, like any other Stock out, and never carries a price. Nothing is done for them silently.
- **Money back in Spent per month** is a new optional `refunds = "refunds"` on the `bars` declaration (checked: a
  table of this module whose records link to this one, only for a sum). After Show, each period's refunds are those
  whose own day falls in it (a refund is counted in the month the money came back), found by joining the Stock in
  so the chart's own `where` and category apply, and are said as "less 3.00 refunded" in the period's words, in the
  table, in the summary ("8.00 AUD spent, from 2 Stock ins, less 4.00 refunded (4.00 AUD after money back)") and
  in each category's own chart. A refund in a month with no Stock in reads "Nothing spent, 1.00 refunded". A refund
  in another currency is said ("also 2.00 NZD refunded, not in this chart") and never converted or taken off. When
  more came back than was spent in the months shown, the summary says so in words instead of showing a negative
  number. Before Show nothing about money back is on the page.
- **On the Stock in's page:** the existing "add a record that points here" button reads **Record money back**, and
  the money back recorded for it is listed with its amount behind **Show money back** (the `under` panel, as a
  quote's cost estimates are on a service page).
- **The line total** is a read-only line on a priced Stock in's page, using the same pressed Show as every private
  value (a POST with the session check, never cached); it adds the currency ("4.50 AUD"). The line total is not a
  form field, so there is nothing to type or change.
- **A price on Review** (`core/receipt_prices.py`, `proposals.accept_counted(..., typed)`, `receipts.add_for_line(...,
  price=)`): the three fields are the Stock in's own columns, read only from the person's own press of Accept (or
  Save this Stock in) and checked before anything is added with the same rules as a typed price (it must say what
  it means, the currency is the household's unless typed). A mistake adds nothing and writes the reason on the
  waiting row; the row stays waiting. A correct price is saved in the same transaction as the Stock in. The field
  starts empty; the paper's price is shown only in the sentence beside it. **Accept all** and **Accept ticked**
  save no price (a price is one person's answer about one row).
- **Examples:** Smith has one invented refund (1.20 against the Rice's 6.40 price); Garcia and Taylor have none.
- **Tests** in `tests/test_refunds_and_review_price.py` (28).

## Why we chose it
- Money back is its own event, not a negative price: it keeps the original price true, has its own date (so a refund
  next month is a next-month fact), and can be several against one purchase, as the draft behind 0128 asked.
- Linking to the Stock in lets "never more than paid" and "same currency" be exact checks instead of reminders.
- Saying "less 3.00 refunded" beside the bar, never as a smaller bar, means nothing is hidden or negative and the
  table matches the words.
- Leaving the stock alone by default matches how shops really work, and a Stock out choice the person makes is
  truthful and already has history and Undo.
- Keeping the Review field empty and typed by a person is 0097 and 0128 unchanged: a misread receipt never becomes
  a price by itself.

## What else we considered
- **A negative price or negative line on the Stock in:** loses the date and the original price, and cannot say
  "more than paid".
- **A refund that always makes a Stock out:** wrong for refunds of goods you keep or for credit notes.
- **Refund as a Stock out reason with a price:** would let a Stock out carry money, which 0128 refuses on purpose.
- **Filling the Review field from the receipt's price when it looks like a number:** left out; a misread digit
  would be saved after one tap. The paper's price is shown right beside the field to type from.
- **Taking a refund off the bar (net spending):** a month would look cheaper because of an older purchase, and a
  negative bar is possible. The summary gives the net for the months shown as words.

## What this costs us (the downsides)
- One more table (Money back) and one more declaration to learn and keep checked.
- A refund is not rechecked if the price on its Stock in is lowered later; the money back then shows as it was
  recorded. Correcting the refund fixes it.
- Money back in a month with no spending is only said in words, never drawn.
- Refunds need a price on the Stock in first; a refund for something you never priced means pricing it first.
- On Review the price is typed one row at a time; Accept all and Accept ticked add no prices.

## How hard it is to undo
Easy. Remove the `refunds` table, its `refund` and `under` sections, the `refunds` setting on the bars, and the
Returned to the shop choice from the stock module, and add a stock migration that drops `stock__refunds` (nothing
else refers to it). Remove `records_refunds.py`, `receipt_prices.py`, the `typed` and `price` arguments of
`accept_counted` and `add_for_line`, and the price offer in the two Review templates. A price saved from Review is
an ordinary price and stays valid.

## We should revisit this if
- Households want credit notes, store credit or a partial return worked out for them.
- Member computers arrive (sync stage 2): decide whether money back travels (today it never does).
- People ask to accept many rows with prices at once.
