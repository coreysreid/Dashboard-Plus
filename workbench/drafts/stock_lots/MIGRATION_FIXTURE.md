# Three households, every item mapped to lots

Checked **2026-11-17** against the three shipped `examples/households/*.toml` files and the current Stock schema. Treat **2026-11-17** as `today` when resolving their relative dates. Run `python workbench/drafts/stock_lots/validate_fixture.py` to check the frozen source files, all item fields, lot amounts and places, and movement history. All records are invented.

| Household | Existing places | Existing items | Existing item-level movements | Migration lots | Target demonstration lots |
|---|---:|---:|---:|---:|---:|
| Smith | 13 | 27 | 6 | 27 | 28 |
| Garcia | 11 | 24 | 6 | 24 | 24 |
| Taylor | 7 | 12 | 3 | 12 | 12 |
| **Total** | **31** | **63** | **15** | **63** | **64** |

[`ITEM_TO_LOT.csv`](ITEM_TO_LOT.csv) has one row per source item, in source order. In a fresh `tools/load_example.py` load, that ordinal is also the item ID (verified for all three households on 2026-11-17). It gives the old amount, unit, minimum, full old place path and resolved ISO date; the one migration lot that must be created from it; then the target lot references, amounts and total. The references such as `smith-006-01` are **fixture references**, not production database IDs. The target TOML marks each reference in a comment immediately before its lot. **Keep the old item ID** when migrating and assign a stable new database ID to each lot.

[`example_lots.toml`](example_lots.toml) rewrites *every* Stock place, item and movement row for the three households. The 63 item rows retain their identity, category, unit, minimum, water decision and notes, while quantity, place and use-by move to lots. It includes 64 target lots and all 15 old movements as `legacy_movements`. That history section is a fixture convention, not a new shipped table declaration. It tells Lane A to keep the records without inventing a lot for a past event. The existing movements already contributed to the source item's present amount and **must not be replayed during migration**.

## Two separate stages for Smith's kidney beans

The shipped Smith example has **5 tins**, Keep at least **4**, at **Kitchen › Pantry › Shelf 3**, with source `expires = today+190`, which resolves to **26/05/27**. A correct migration creates **one 5-tin lot** with that date and place, preserving the 5-tin item total and minimum 4. It does **not** silently turn five into thirteen or change the date.

The requested demonstration is a *later household action* on the migrated item. Count the shelf lot as **3 tins** (a documented stocktake correction of **−2**) and set its date from the package to **20/12/26**, then record a separate **10-tin purchase** at **Garage › Garage shelves** due **20/05/27**. The target item shows **13 tins** from **3 + 10**, still with minimum 4. `example_lots.toml` is this final demonstration state. The row for `smith-006-01` in the CSV records the exact migration state and the transition; `smith-006-02` is the new purchased lot. The date changes and +8 net quantity change belong to those explicit actions, not to migration.

## Migration checks for Lane A

1. Start from each current example loaded into a fresh database with fixed today 2026-11-17. Capture item IDs, current amounts, drinking flags, place IDs, use-by dates and all movement IDs and rows before migration.
2. Create exactly one lot for each of the 63 existing items, including undated and zero-amount items. The new lot amount, date and place match the CSV's `migration_*` and `source_*` columns. The item ID, name, category, unit, minimum, drinking answer and notes do not change. A zero lot may be archived, but it must never warn about expiry.
3. Keep the 31 existing Stock places and their nested paths unchanged at this stage. A lot points to the same old place ID that its item pointed to; no path is guessed from text. Item 30 covers the later shared Home layout place migration.
4. Preserve all 15 existing movements with their IDs, item links, reasons, signed effect, date and notes. The old movements have **unknown lot provenance**; permit a null lot link or a separate legacy audit representation. Do not force them onto the new lot and do not replay them into present stock. New movements after migration must name a lot.
5. Compare each item total to its source quantity, not merely the combined total across unlike units. In particular, water remains **34.4 litres** for Smith, **24.7 litres** for Garcia and **12 drinkable litres plus 1 non-drinking litre** for Taylor. Use the confirmed `drinking` answer and the unit when calculating days of water.
6. Apply the two explicit Smith changes above in a second fixture step. Then compare the final rows with `example_lots.toml`: 64 target lots and a 13-tin Kidney beans item. The other 62 item totals remain unchanged. All full place paths and date formats appear correctly in forms, Needs attention and sheets.
7. A failed migration leaves the original item, place and movement records usable from the pre-migration backup or rolls back the transaction. Retrying does not create duplicate lots or reapply old movements.

**Core gap:** The illustrative `stock_lots/tables.toml` makes `movements.lot` required, but existing movement rows cannot truthfully be assigned to a lot. The migration needs a legacy exception or a separate history representation with a documented path back. This is a preservation issue, not a reason to fabricate a lot link.

The target data is a **test fixture**, not directly loadable by the current Stock module. The current module has no lots table. The method and screen rules are in [`NOTES.md`](NOTES.md) and [`ACCEPTANCE.md`](ACCEPTANCE.md). No outside source or licence is needed for fictional household records; source fields were checked against `examples/households/` and `modules/stock/tables.toml` on the date above.
