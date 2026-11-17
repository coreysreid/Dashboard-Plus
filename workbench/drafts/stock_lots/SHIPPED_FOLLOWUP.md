# Shipped batches: acceptance check and two more households

Checked **17 November 2026** against shipped lots (decision 0053), [13 earlier acceptance checks](ACCEPTANCE.md), `tests/test_stock_batches.py`, `tests/test_dates.py`, and the current Stock forms, watch and sheets. The tests ran in `python tools/check_all.py`; both full [Garcia](garcia_with_second_batches.toml) and [Taylor](taylor_with_second_batches.toml) copies loaded through `tools/load_example.py` into empty temporary folders. All added dates and quantities are fictional package labels, not shelf-life advice.

## What matches, and what differs

| Earlier check | Shipped behavior observed | Difference from the proposed household flow |
|---|---|---|
| 1 Stocktake | Editing a batch amount recomputes its item total; the update is in record history. | There is no dedicated “3 recorded here. Counted 5. Update this batch?” flow or separate **+2 stocktake correction** movement. A direct edit does not explain the count change in Stock in and out. |
| 2 Weekly shop | Stock in with a new date/place creates another batch and sums the item. | No explicit “Add to this matching batch” choice or proposed “Added 10 tins. …” confirmation was found. |
| 3 Oldest first | Stock out without a batch chooses the earliest known use-by date. An undated batch does not outrank a dated one. | An amount spanning batches is refused with “Record that batch first, then the rest from the next one, or choose a batch.” It does not offer one reviewed split across batches. |
| 4 Overspend and wrong item | More than is held is refused; a batch from another item is refused. | The error words differ from the acceptance draft, but the guard holds. |
| 5 Expired batch | An expired Stock out leaves a zero batch in history and stops its warning. | No material count difference found. |
| 6 Needs attention | Each positive due batch has its own entry and zero batches are excluded. | The current detail uses “(in 30 days)” rather than the draft's full sentence. |
| 7 Running low | Uses the sum of batches against the item's minimum. | No material total difference found. |
| 8–11 Local dates | Parser tests cover AU/UK/NZ day-first, US month-first, ISO, two-digit years, impossible dates and the form error. | The five-surface display matrix in the original acceptance draft was not independently repeated here; do not count it as a new full-screen pass. |
| 12 Old items migrate | Migration creates one batch per existing item, preserves amount, place and date, and makes a before-update backup. Old movements are not replayed. | With exactly one historical batch, migration links old movements to it; this is the chosen shipped policy in decision 0053. The earlier fixture's “unknown provenance” caveat remains useful if future migration starts from an item with several historical batches. |
| 13 Drinking water | Shipped `counts_only` requires the item's confirmed drinkable flag and litre units for the days-of-water figure. | No new difference found in core tests. |

**Priority for Lane A:** If a household uses a batch edit as its stocktake, keep the before/after audit visible in the household flow and decide whether to record an explicit correction movement. For a Stock out across two batches, a reviewed split would avoid making the person enter it twice. These are core/UI needs; this workbench follow-up does not work around them.

## Garcia and Taylor: second batches ready to adopt

Both TOML files copy the full shipped household and change only two first-batch amounts plus two added `[[stock.lots]]` rows each. They keep the original item totals, units, minimums, other records and movement history. The loader makes each item's reduced first batch from its `[[stock.items]]` row, then adds the explicit second batch.

| Household / item | First batch | Added second batch | Total after load |
|---|---|---|---:|
| Garcia · Black beans | 5 cans, Kitchen cabinets, 10/05/28 | 3 cans, Storage locker, 06/11/28 | 8 cans |
| Garcia · Rice | 3 lb, Kitchen cabinets, 17/11/27 | 2 lb, Storage locker, 20/05/28 | 5 lb |
| Taylor · Gluten-free pasta | 1 pack, Kitchen cupboard, 16/05/27 | 1 pack, Hall cupboard, 13/09/27 | 2 packs |
| Taylor · Tinned soup | 2 tins, Kitchen cupboard, 03/10/27 | 1 tin, Hall cupboard, 31/03/28 | 3 tins |

The four dates shown above resolve `today+...` with **2026-11-17** as the fixture date. Garcia loaded **24 items, 26 batches and 6 old movements**; Taylor loaded **12 items, 14 batches and 3 old movements**. Read-only SQL confirmed each two-batch item total. Both `/sheet/stock/supplies` pages returned 200 and showed the added places. The exact diff from the source examples has four quantity edits and four new batch rows; no shipped example was edited. Sources: `examples/households/{garcia,taylor}.toml`, `modules/stock/{tables,labels,sheets}.toml`, decision 0053 and the named tests, checked 17 November 2026.
