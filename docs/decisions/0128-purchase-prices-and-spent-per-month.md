# 0128. What you paid on a Stock in, and Spent per month

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0097 (a receipt's price on Review is checking text only), 0100 (what travels), 0105 (receipt
  lines), 0111 (amounts in their own unit, never converted), 0117 (bills amounts stay on this computer), 0121
  (Show is a pressed button), 0124 (bars over time); Lane B's `workbench/drafts/purchase_history/` (DESIGN.md,
  WORDS.md, ACCEPTANCE.md, NOTES.md; now removed, in git history)

## In plain words
User 1 wants to see results and track changes as pictures, and spending is the natural next one. When you save a
bought Stock in, or later from its page, you can now type **What you paid**, say whether **That price is** the
**Total for these goods** or the **Price for each one**, and leave the currency blank for your household's usual one
(Settings: **Prices you type are usually in**). Household stock gets **Spent per month**: it counts your Stock ins
per month, and **Show** adds up the prices you typed, overall and for each category, in one currency at a time.
A month with Stock ins but no prices says "no price recorded", a month with none says "nothing recorded", and the
page says it covers only prices that were typed in. A price a helper read from a receipt stays on Review for
checking; nothing ever copies it into a price.

## What we chose
- **Four new Stock in and out columns** (stock migration 0008, four `ALTER TABLE … ADD COLUMN`, nothing rebuilt,
  every existing row kept with no price): `price` (money as typed), `price_basis` (a choice of exactly "total" and
  "each"), `paid_total` (the line total, worked out) and `currency` (a three-letter code). All four are private
  (`sensitive = true`) and `travels = "never"`.
- **A generic `[tables.<t>.price]` declaration** names those columns, the amount a price for each one is multiplied
  by, and `only` (here `reason = "bought"`), checked when the module loads (`_check_price`: each column's type,
  private and never travelling, the two exact choices, and plain words for every mistake). On every save and
  change (`core/records_prices.py`, called from the one write path) a price **must say its basis**; a price on a
  Stock out is refused ("A Stock out never takes money off"); the currency is the one typed, else the household's,
  else refused with words that point to Settings. The line total is the price, or the price times the amount for
  "each", rounded to the cent, and follows a corrected amount. Clearing the price clears the other three. A price
  never changes the stock amount. Every correction is an ordinary change with history.
- **Household currency** is a Settings choice (seven currencies of the countries Settings lists). Until it is
  chosen it follows the country; for a country the program does not know there is none, so none is guessed.
- **Amounts are household-local, like bills amounts (0117):** `travels = "never"`. A price says what this
  household paid and when, and the draft asked for local-only until User 1 chooses a member policy. The
  change log carries the column names only, never a value; local backups keep them.
- **Privacy follows from `sensitive`:** prices are off lists, sheets, Needs attention, the spreadsheet export and
  helper reads; on a Stock in's page each is behind Show; a spreadsheet import cannot carry one.
- **Helpers are left out.** The draft says helpers never get to choose what a receipt price means, and decision
  0097 keeps `source.price` on Review only. A helper that sends `price` (or any of the four) is refused with
  403 `private_detail`, as for every private column; its receipt line and price still show on Review for checking.
  A person who wants the price accepts the row and types it on the saved Stock in.
- **Spent per month** is 0124's `bars` declaration on Stock in and out: `measure = "sum"` of `paid_total`, `unit =
  "currency"`, `where = { reason = "bought" }`, `group = "item.category"`, by month or week, `missing = "price"`,
  and a caveat that only typed prices are added and a Stock out never takes money off. **Refunds**, per the draft,
  need an explicit refund event linked to the original purchase; none exists yet, so nothing is ever subtracted.
- **What the generic bars learned:** leaving out `per` gives one chart of the whole list, linked from the module's
  card on Home ("Spent per month · Bars over time") and from the list, never on a record's page; `group =
  "link.choice"` gives each choice of the linked record its own bars ("Each category on its own"); `amount` may be
  money (two decimals, "12.50 AUD") or private. A private amount is counted until a pressed Show (POST with the
  session check, `no-store`, `?show=1` does nothing); after it, By month, By week, In NZD, Earlier and Later are
  pressed buttons so moving keeps the amounts shown, and Hide amounts goes back. Other currencies are said ("also
  9.00 NZD, not in this chart"), never converted; a Stock in without a price is counted, never read as zero.
- **Examples:** Smith (three AUD prices, one a price for each pack), Garcia (two USD) and Taylor (one GBP, a price
  for each carton), each on an existing Stock in; no line is repeated to carry a price. Every amount is invented.
- **Tests** in `tests/test_purchase_prices.py` (19), and 0124's test updated for the new money and private rule.

## Why we chose it
- A line total and a unit price are both common on paper; asking which one keeps "never guess" from 0097 exact,
  and storing the worked-out total lets the bars add one column with 0124's own one-unit-at-a-time rule.
- Currency as each price's own unit means old prices keep their currency when Settings changes, and two
  currencies are told apart for free by the code that already keeps grams and pouches apart.
- Counting before Show gives the picture of shopping activity without putting money on a screen someone else can
  see, the same promise as every other private value.
- Generic declarations keep this out of hand-written Stock screens; any later list of bought things can use them.

## What else we considered
- **A separate purchase and purchase-line table** (the draft's full model, with receipt totals and shops): the
  right end state for receipts with discounts and non-Stock goods, but it needs the atomic purchase link, receipt
  reconciliation and refund design first. A price on the movement itself is the smallest true step and can be
  copied into such a table later.
- **"Save a price with this Stock in?" on Review**, confirming a helper's price: left out. It needs its own
  screened choices on Review and a decision record of its own; until then a helper's price never becomes a price.
- **Prices that are not private:** they would appear on lists, the export and helper reads, which the draft forbids.
- **Converting currencies or adding a receipt total:** refused, as in the draft.
- **A shop name:** left out for now; a free-text shop is a lasting record of routines and the draft wanted it
  private too. One more private column later if households ask.

## What this costs us (the downsides)
- Four more columns on Stock in and out, and one more declaration (`price`) to learn and keep checked.
- Spent per month needs a press of Show every visit; that is deliberate but slower than a glance.
- No receipt total, shop, discount or refund yet, so this is never "everything we spent" (the page says so).
- A price typed on a member computer later would stay there, and main's chart would not know it (sync stage 2
  must say coverage is incomplete, as the draft asks).
- The household currency list has seven currencies; a household elsewhere types its code on each price.
- After Show, the rows' "See these weeks" links are left out (they would hide the amounts); By week does the same.
- Rounding a price for each one times a decimal amount can differ from a shop's own rounding by a cent.

## How hard it is to undo
Easy. Remove the four columns and the `price` and `bars` sections from `modules/stock/tables.toml` and their labels,
and a new stock migration that drops the four columns (SQLite 3.35+ `DROP COLUMN`); remove `records_prices.py`,
`_check_price`, the currency setting, and the whole-list, `link.choice`, money and private-amount handling in
`bars.py` and `bar_pages.py`. No other value depends on a price.

## We should revisit this if
- Households want receipt totals, shops or refunds: build the draft's purchase and refund records then.
- People ask to confirm a helper's receipt price on Review instead of typing it again.
- Pressing Show for the chart every time feels like too much; a per-household "show amounts" choice is one setting.
- Member computers arrive (sync stage 2): decide whether confirmed prices travel.
