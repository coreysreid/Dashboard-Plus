# Layered use-by dates: interaction and core contract

The original pre-shipping fixture and exact old-item mapping are in [`MIGRATION_FIXTURE.md`](MIGRATION_FIXTURE.md), [`example_lots.toml`](example_lots.toml) and [`ITEM_TO_LOT.csv`](ITEM_TO_LOT.csv). Batches now ship; see [`SHIPPED_FOLLOWUP.md`](SHIPPED_FOLLOWUP.md) for actual behavior and the two loadable household copies. The paragraphs below preserve the earlier design proposal for comparison.

This is a **design draft**, not a loadable module. The target schema in `tables.toml` shows the new items, lots and movements after Lane A integrates them into Household stock and Home layout. The current core cannot maintain a derived item amount or show a shared full-path place, so shipping a fake standalone module would hide the gap.

## The example on screen

**Stock list:** “Kidney beans — 13 tins on hand — keep at least 6”. Opening it shows two lots:

| Amount | Use by | Place |
|---|---|---|
| 3 tins | 20/05/27 | Kitchen › Pantry › Shelf 3 |
| 10 tins | 20/11/27 | Garage › Grey shelves |

The item has one name, catalogue key, category, unit and minimum. The lots own the quantities, use-by dates and places. **13 is computed from 3 + 10.** A missing use-by date is allowed and shown as “Date not recorded”, never treated as fresh. Lot identifiers stay stable so changes and deletions can be audited.

## Five everyday screens

1. **Stocktake.** Typing `kid` offers Kidney beans. After selecting it, the form asks “Where is it?”, showing full Home layout paths, “How many?”, and “Use by” in the household's date order. A household can enter “Kidney beans, Kitchen › Pantry › Shelf 3, 5, use by 20/05/27”. If there is already a 3-tin lot with the same item, path and date, the screen says “3 recorded here. Counted 5. Change this lot to 5?” with a clear **Update count** action; it records a +2 correction. It must not silently add 5 to 3. If this is a new place or date, offer **Add a separate lot**. The item total updates immediately.
2. **Weekly shop.** “Stock in” finds the item by name or catalogue alias and asks for amount, use-by and place. Buying 10 tins with 20/11/27 in Garage › Grey shelves creates or, after confirmation, adds to that matching lot. The success line reads “Added 10 tins. Kidney beans: 13 tins on hand.” A receipt with several dates creates several lots. A package size may help calculate units, but the person confirms the actual quantity.
3. **Use some.** “Stock out” asks “How many tins did you use?” and suggests the earliest known use-by lot first: “3 tins, use by 20/05/27, Kitchen › Pantry › Shelf 3”. The household can pick another lot or split the amount across lots. The screen shows the remaining amounts before save. An unknown-date lot does not outrank a known earliest date. The core must reject taking more than a lot holds or taking from a lot belonging to another item. It writes an auditable movement for each affected lot.
4. **Throw out an expired lot.** On the lot page, **Throw away** preselects that lot and asks how many were discarded, defaulting to its remaining amount. The reason is “Expired” or “Thrown away” as chosen by the person. Confirming all 3 makes the lot zero or archived in history, and the item total becomes 10. Do not delete the lot's history or assume everything past a best-before date is unsafe.
5. **Needs attention.** With 30 days remaining, show exactly “3 tins of Kidney beans expire in 30 days” and link to the 20/05/27 lot and its full place. If two lots expire, show separate dated lines or a clearly grouped total with the dates. Running low uses the **sum** of active lots and compares it with “Keep at least 6”. A zero-quantity lot must not generate an expiry warning.

## Dates and units

The field accepts and displays **20/05/27** for Australia and the UK, and **05/20/27** for the US, using the configured household country and locale. Store the unambiguous ISO date **2027-05-20** internally. Use a date control or parsing that shows the expected format and reports an invalid or ambiguous date plainly. Never turn `20/05/27` into another day by assuming US order. A quantity is in the item's unit (here, tins); package size is separate, so 3 tins is not 3 × 400 g in the item total. If a household changes unit, require an explicit conversion of all lots and minimums or keep the old unit.

## Exact core work for Lane A

1. Extend Stock items with a stable catalogue key and **derived** amount equal to the sum of nondeleted lot quantities. Prevent independent edits to item quantity after migration. Keep a database constraint or transaction invariant that forbids negative lots.
2. Add lots linked to one item and one Home layout place, each with quantity, optional use-by, optional package size and history. Ensure item deletion, lot deletion and undo do not silently lose stock or movement history.
3. Recompute item total and running-low watch after every lot save, movement, correction, deletion or restore. Apply expiry watch to each positive-quantity lot, with the item name, amount, unit, date and full place in the message.
4. Make Stock in/out select a lot. For stock in, offer a matching item/place/date lot or a new one; for stock out, suggest earliest known use-by but allow a different lot or a split. Validate the selected lot belongs to the item. Move, discard and correction actions need clear history and atomic updates. A stocktake is a counted **final amount** at a place/date, not an unconditional addition.
5. Migrate each current single-date Stock item into one lot with its current quantity, existing place and `expires` value, keeping a reversible old-ID mapping and auditing zero or missing amounts. Migrate existing movements without replaying them into the new quantity; retain their history, then start lot-specific movements. Do this after Home layout place migration, or use a coordinated transaction.
6. Apply the household's locale to date entry and display throughout Stock, including existing date fields, while storing ISO dates. Test AU/UK and US parsing with `20/05/27` and `05/20/27`.
7. Change printable stock sheets and any supply calculation to read lot totals. Drinking-water totals must also filter on confirmed potable status and convert the entered unit to litres where applicable; don't count treatment tablets or flushing water.

## Date-entry decision for Lane A

The [acceptance checks](ACCEPTANCE.md) propose that a typed two-digit year `00`–`99` means 2000–2099, with a long-date preview before Save; four digits allow other centuries. This is simple and predictable, but a household entering a historical date must type four digits. If Lane A chooses a different cutoff, document it in the visible hint and test it in every country format. Keep ISO only as the stored form, and never silently swap day and month.

## Longer-term camera stocktake idea

A household could scan a **barcode** with a phone camera or an ordinary **webcam**, identify the product from a local or opt-in product database, and use the camera to propose the use-by date, package size and quantity. This could make large stocktakes and weekly shopping much easier, especially for someone without a dedicated scanner. Barcode identity alone does **not** give the date or the amount on hand; those require a readable package, optical character recognition or manual entry. Multiple packages may share a barcode but have different dates, so each proposed lot must be reviewable before saving. Start with scan-to-search and human confirmation; consider optional OCR and AI extraction only after measuring accuracy, privacy and time saved. Keep an offline/manual path and never send camera images or household stock lists to a service without explicit opt-in. Lane A would need camera/webcam access, barcode decoding, product data provenance and regional coverage, date and quantity extraction, confidence display, and an approve/correct step that creates the correct lot and movement. This is a **long-term goal**, not part of the current draft's implementation.
