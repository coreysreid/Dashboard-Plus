# Receipt lines that a helper cannot match

Design only, checked **21 November 2026** against decision 0097, the shipped connector tool schema, Review and Stock tables. This extends the live [batch 19 receipt run](../../reports/2026-11-21-receipt-group-review.md). All line text below is invented. The current connector has no photo tool, and current Review accepts only proposals for known tables; the unmatched row and buttons here **need core work**. A household may give a photo to its own assistant app, which may be an online service. Crop payment, loyalty, address and personal details before doing that.

## The household's Review screen

The helper sends clear Stock suggestions and unresolved product lines in one ordered receipt group. Review has a heading: **“Example receipt helper read 3 goods. 2 Stock in rows are ready to check; 1 line needs your choice. Nothing has been added.”** Say “read” rather than “found” because the helper can misread the paper. Show the helper's short reason as its words, each short source line and price as in 0097. No price is a Stock field. A source line can be wrong; the household can compare with the paper.

For an unresolved product line, show this exact card:

> **Could not match this receipt line to your Stock**  
> “TOM SPECIAL 400G  1 @ $1.50” · Price shown on paper: $1.50  
> The helper could not tell which good this is. No Stock amount will change until you choose an item and confirm the amount.  
> **Choose item** · **Skip line**

The source line is helper-supplied text, escaped and screened as for 0097. A line that is only `TOTAL`, a coupon, payment, tax or a refund is not an unmatched good and must not be offered as Stock in. If it is unclear whether a line is a good at all, the helper should say so in its own conversation and leave it out of this receipt group until the household confirms it is a purchase. Review does not promise to hold the whole photo.

**Choose item** opens a focused decision form headed **“What did this line add to your Stock?”** Its picker searches the household's own Stock items first, then catalogue names; a catalogue match is a suggested name, not proof. Show the receipt source throughout. After the person chooses an existing item, ask **“How much did you bring home?”** with that item's unit, and show the receipt date as a proposed date for confirmation. Example: **“Add 1 tin of Tinned tomatoes on 20/11/26?”** The person may change the amount and date; an ambiguous `2L` or `12PK` never sets two litres or twelve packs without this choice. Provide **“Save this Stock in”** and **“Back to Review”**. If no existing item fits, offer **“Make a new Stock item”**; collect name, category and unit, then confirm its first Stock in in one transaction using the dependency model from 0097. No item is created just because a catalogue option was displayed.

After a person saves, say **“Added 1 tin of Tinned tomatoes from this line. Review the remaining lines.”** Mark just that line **Added** with the linked item and movement ID; remove it from waiting. Other receipt lines stay pending. A later open of Review shows the decision and the current Stock amount, not another Accept button. If a record changed while this form was open, refuse the save and say **“This Stock item changed while you were checking the line. Check its current amount and try again. Nothing was added.”** A chosen new item plus its first Stock in must either both save or neither save.

**Skip line** asks no extra confirmation for this one reversible Review decision and says **“Skipped this line. No Stock amount changed.”** It marks that line Skipped in the group's review history; it does not create an item, movement, batch, price, catalogue entry or shopping-list row. The receipt group stays open after its last row is decided until the person presses **Finish receipt review**. Give **“Undo skip”** until then, returning the line to waiting; Undo skip never adds Stock. Closing the group with skipped lines needs an explicit summary: **“2 Stock in rows added; 1 line skipped. No Stock was added for the skipped line.”** Never silently count a skipped line as bought.

## What the helper sends

Keep `dashboard_suggest_new_records` for existing valid entries. Extend its `entries` array with a distinct, closed **unmatched product line** form. Existing `{table, values, source}` entries stay valid. Proposed wire example, **not shipped**:

```json
{
  "request_key": "example-market-2026-11-20-lines-v1",
  "why": "I read this invented receipt; one product line needs your choice.",
  "entries": [
    {"table": "stock__movements", "values": {"item": 5, "reason": "bought", "amount": 3, "happened_on": "2026-11-20"}, "source": {"line": "TINNED TOMATOES 400G x3", "price": "$3.30"}},
    {"kind": "unmatched_product_line", "source": {"line": "TOM SPECIAL 400G  1 @ $1.50", "price": "$1.50"}, "receipt_date": "2026-11-20", "quantity_hint": "1", "unit_hint": "tin"}
  ]
}
```

The four new keys are fixed: `kind`, `receipt_date`, `quantity_hint`, `unit_hint`. `kind` has only `unmatched_product_line`; the latter three are optional hints, not saved Stock values. `receipt_date` must be a real ISO date; `quantity_hint` is a positive finite decimal string of at most 20 characters; `unit_hint` is at most 30 visible characters. The helper may send an unmatched line only when it has reason to treat it as a bought product but cannot identify an item or compatible unit. It must supply `source.line` (1–200 characters, per 0097); `source.price` remains optional and is display text only. A purchase date from the paper is a hint to confirm, never silently applied. The helper must not include `table`, `values`, a guessed item ID, `{"ref": N}`, or a made-up catalogue key on an unmatched row. The API rejects mixed or unknown keys, key-shaped text, controls and hidden direction changes using the existing 0074/0097 screening. At most 50 entries, matched and unmatched together, and the same `request_key` plus same body must return the same group without another line.

The connector needs a schema union that keeps the old record entry exact and adds this one distinct form. The helper's response should say **“2 suggestions are ready to check and 1 receipt line needs your choice. Nothing has changed yet.”** It must not say that the unmatched line is a Stock suggestion or that its quantity is confirmed. If the helper has no reliable purchase date, omit the hint and let the household enter it. If it has no reliable quantity, omit both quantity and unit hints. Do not send one unmatched row for a discount, total or payment line merely to avoid losing it; explain excluded lines in the assistant conversation.

## Core storage and decisions needed

The present `core__proposals` record contract assumes a table and values. Core needs a distinct receipt-line row kind, its own validation and a group view that includes both row kinds in source order. An unmatched row's state is **waiting**, **added** (with linked item and movement IDs) or **skipped**. This row is not a proposal to add an unknown Stock record. `Choose item` must take a current item revision and operation token, revalidate unit and date, and commit one normal bought movement; a new item and its first movement commit atomically. Respect the same Stock lot rules as a person-entered Stock in. The household, not the helper, chooses the item and amount. A stale or double submit cannot add twice.

Store the short helper-supplied source and hints in Review's proposal data, under the same local backup/privacy behavior as decision 0097. Do not copy them into Stock names, notes, movement history, ordinary export or print sheets. After **Skip**, retain the decision and short source in Review history so a household can tell which line it skipped; do not retain the raw photo, payment details or an invented item. If a future retention rule removes old source text, say so on Review and preserve only the decision outcome and IDs. A skipped line is a decision, not a Stock record; Undo skip is allowed only while its group is still open. A saved movement follows the normal Stock Undo rules, not Undo skip.

The receipt group may still contain clear, independent suggestions. Its batch button becomes **“Accept 2 ready Stock rows; 1 line still needs your choice”** and accepts only the ready record rows, leaving the unmatched row waiting. It never silently skips that line. After every product line is accepted, rejected or skipped, show the outcome summary and **Finish receipt review**; only that button closes the group and ends Undo skip. Receipt-wide Undo and duplicate receipt recognition remain separate designs; neither follows automatically from this row kind.

## Acceptance checks for Lane A

1. Send the two-entry JSON above through the connector. The matched movement and unmatched card appear in one group in source order; Stock stays unchanged before a person acts. An older caller without `kind` still stages exactly as before.
2. An unmatched `source.line` missing, over 200 characters, containing a key-shaped string or a hidden bidirectional character refuses the entire request. No partial Review row or Stock write survives. Extra keys and `table`/`values` on the unmatched form also refuse.
3. A helper without Household stock suggest access, or with Look only, cannot send either row. Turning its access off leaves previously staged rows for the person but prevents new ones.
4. Retry identical `request_key` and body: same group and line IDs, no duplicate. Retry same key with changed source, price, date or hint: refuse. A second different key is a new request; duplicate receipt handling is item 86.
5. At 320px and desktop, source, hint, waiting count and **Choose item** / **Skip line** remain readable by keyboard and screen reader without page overflow. Source text is escaped, displayed as helper text and is not treated as an instruction.
6. Choose an existing Tinned tomatoes item, confirm **1 tin** and a household-format date. Exactly one bought movement and one corresponding batch change are saved, with the source line absent from Stock fields and export. The line becomes Added and cannot add again by refresh or double press.
7. Choose a catalogue suggestion that is not already a Stock item. It remains a candidate until **Make a new Stock item** is confirmed; the new item and first Stock in appear together or neither appears. An impossible date or invalid amount refuses the whole action.
8. A helper hint `12PK` or `0.820 KG` with an incompatible chosen unit does not convert silently. The form asks for a compatible amount and unit; leaving it unresolved changes nothing.
9. Skip one unmatched line. No Stock or catalogue row is created; the summary counts it as skipped. Undo skip before **Finish receipt review** returns it to waiting and never adds Stock. Once the group is closed, the decision stays in history.
10. A `TOTAL`, tax, coupon, payment or refund line does not arrive as a bought product row. If the helper cannot classify it safely, it reports the uncertainty in its conversation instead of staging a fake movement.
11. If the Stock item changes between opening Choose item and saving, show the stale message and make no movement. Retry from the fresh item view; do not overwrite the household's count or date.
12. **Accept 1 ready Stock row; 1 line still needs your choice** accepts only the matched row and leaves the unmatched one waiting. It does not claim the receipt is complete. Rejecting the matched row also does not skip the unmatched one.
13. In a backup/restore and general export, the matched Stock movement follows existing rules; the Review-only source and skipped decision do not become a Stock field or CSV cell. A restored open group has the same decisions and cannot reapply an already Added line.

Sources checked 21 November 2026: `docs/decisions/0097-receipt-lines-and-grouped-suggestions.md`, `src/dashboard/connector/tools.py`, `src/dashboard/core/proposals.py`, `src/dashboard/web/review.py`, `src/dashboard/web/templates/review.html`, and `modules/stock/tables.toml`. This is a proposal for core and connector changes, not a shipped screen.
