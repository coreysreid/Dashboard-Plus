# Entering a shopping receipt

Drafted 17 November 2026 for M2. All sample lines and prices below are invented, not copied from a retailer. The matching table has **200 one-to-one candidate descriptions** selected from common pantry, fresh-food and household goods in the workbench catalogue. It is not a measured top-200 sales ranking. `region_hint` changes which spelling to offer first; it does not prohibit a match in another country.

## Start

From Stock choose **Add from a receipt**. First screen: “Paste receipt text or add a photo. We will suggest Stock items; you check each one before anything is saved.” Offer pasted text first, a file/photo only when the core can process it locally. Ask for shop date, country and currency, prefilled from household settings but editable. Make clear that no receipt is sent away. Never ask for or retain payment-card information. If a pasted receipt includes card digits, redact the display and raw-staging copy before saving.

## Read the lines

Receipts can mix item descriptions, pack size, quantity, weighed amount, unit price, multibuy discount, tax and total. Some item lines may be abbreviated or brand-heavy. Below are **fictional parsing examples**, not claims about a specific till format:

| Region | Invented line(s) | Suggested interpretation to review |
|---|---|---|
| AU | `TOM TINNED 400G  4 @ $1.20  $4.80` | Tinned tomatoes, 4 tins, 400 g each. |
| AU | `BANANAS 0.820 KG @ $3.00/KG  $2.46` | Bananas, 0.82 kg; do not turn 0.82 into 1 item. |
| US | `CANNED TOMATOES 4 X 14 OZ $5.00` then `MULTIBUY -$1.00` | 4 cans; keep discount with cost, not as negative Stock. |
| UK | `COURGETTE 0.450KG £1.35` | Zucchini, 0.45 kg; show both names for confirmation. |
| NZ | `MILK FULL CRM 2L 2 FOR $7.00` | Milk, 2 cartons of 2 litres; ask whether Stock uses cartons or litres. |

The app first separates product rows from subtotal, tax/GST/VAT, loyalty, coupon, savings, bottle deposit, delivery and payment rows. A discount can refer to several preceding products; if the link is unclear, leave its cost unmatched. For weighed goods retain both weight and price per weight, then convert only if the Stock unit is compatible. A multipack's inner count is not the number purchased. For example `4 X 14 OZ` is four cans, while `12PK` on a single tissue pack is one purchased pack. A refund or void should never be treated as an addition without explicit review.

## Review before saving

Show a table with one row per proposed Stock action: original line, suggested catalogue name, amount and unit, pack size, cost/discount if recognised, and a confidence label. Example: **“We think this is Tinned tomatoes, 4 tins. Is that right?”** Actions on each row: **Yes**, **Change**, **Skip**. A changed name opens the same Stock picker, with the household's own items first. Show all original product rows, even unmatched ones: **“We could not match ‘TOM SPECIAL’. Choose an item or skip it.”** Do not turn a guessed match into a saved item until the person accepts it. Flag a mismatch such as a price-only discount as “Not a Stock item.”

Before the final save show: “12 lines accepted, 2 skipped, 1 still needs a choice. Nothing has been added yet.” Disable **Add 12 items to Stock** until every row is accepted, changed or skipped. Let the person choose a place and, when lots land, actual date/lot details; never invent use-by dates from catalogue shelf-life hints. Saving creates a single reviewable batch of Stock in movements, so one mistaken receipt can be undone as a batch. After save: “12 Stock amounts added from this receipt. Review them or undo this batch.” Make repeated import of the same receipt recognizable and ask before applying it again.

## Matching-table contract

`match_table.csv` has 200 unique `catalogue_key` values from the current `workbench/drafts/catalogue/catalogue.csv` (checked 17 November 2026). `sample_receipt_line` is synthetic text to exercise parsing and search. `match_words` contains alternate words separated by `|`; match these case-insensitively after normalizing spacing and punctuation. `region_hint` is `all` or a `|`-separated list of AU, US, UK and NZ. `review_if` highlights ambiguities. A term is a **candidate**, never proof: “cream” could mean dairy cream or skin cream; a brand, flavor, weight or size may distinguish items. The core must rank using the whole line, units and household history, then require a person to confirm every row.

## Acceptance examples

1. Paste each invented regional example above. The review screen preserves the exact original line and proposes the stated amount, unit and catalogue key, or marks ambiguity to change. No Stock amount changes before the final save.
2. Paste `2 FOR $7`, a separately printed `-$1.00` coupon and a `TOTAL` row. Neither creates a negative Stock movement. The cost calculation stays explainable and can be corrected independently of quantity.
3. Paste a weighed `0.820 KG` banana line and a `12PK` tissue line. Bananas add 0.82 kg; tissues add one pack unless the person changes it. A `4 X` line adds four outer packages only when that format is clear.
4. Paste an unknown name and a same-looking name with incompatible units. Both appear for review with **Change** and **Skip**; neither silently creates a catalogue item.
5. Submit the same source twice. The second attempt shows “This receipt may already have been added on [date]. Check before adding it again.” Rejecting the second attempt leaves amounts unchanged.
6. After saving, undo the entire receipt batch. All its Stock-in movements reverse together; prior household edits stay intact. If a person has since changed one of those items, require a conflict review rather than overwriting that change.
