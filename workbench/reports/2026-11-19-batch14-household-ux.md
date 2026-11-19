# Things lent out, stocktake and Garden: three-household UX check

Checked **19 November 2026** against `main` at `94f398f`. This is batch 14 item 55. I loaded the invented Smith, Garcia and Taylor examples into fresh temporary data folders, then ran each flow in Chromium at **1200px desktop** and **320px phone** widths with the household's AU, US or UK date order. The [90-screen matrix](2026-11-19-batch14-ux-matrix.csv) lists each visited route, HTTP status and document width. Two [Smith stocktake captures](ux_2026_11_19/INDEX.md) show the finding at both widths. No real household records were used.

## Finding, worst first

### Minor: the count review says “1 tins”

**Where and steps:** In Smith, open **Kidney beans**, choose **Count** on the first batch (3 tins at Kitchen › Pantry › Shelf 3), enter **4**, then choose **Review count**. This reproduced at 320px and desktop. The same review route said “1 litres” when counting Garcia's water jugs and Taylor's bottled water one unit higher.

**Expected:** The difference reads naturally for one unit without changing the household's stored unit. **Actual:** The review says **“This adds 1 tins as a stocktake correction. It is not a purchase.”** The surrounding count and final item total are correct. This is a wording issue, not an amount error.

**Exact suggested replacement:** **“This adds 1 to this batch as a stocktake correction. It is not a purchase.”** For a lower count, use **“This removes 1 from this batch as a stocktake correction. It does not say they were used or thrown away.”** These forms also work for user-entered units that have no safe singular form. The line above still shows the counted and recorded amounts with their unit.

## What worked

| Household | Things lent out | Count this batch | Garden |
|---|---|---|---|
| Smith (AU) | Created a new invented loan; the drill's return reminder appeared while out and disappeared after **Mark returned**. The already returned trowel did not remind. | Kidney beans, first batch 3 → 4 tins. The item total became 14 across two batches; only the selected batch rose, and exactly one `counted_more` movement was added. | **Check bed ties** reminded while unfinished, then disappeared after **Mark done**. The already finished bed-edge job did not remind. |
| Garcia (US) | Created a new invented loan; the trolley reminder appeared at its seven-day boundary and disappeared after **Mark returned**. | Water jugs, selected batch 22.7 → 23.7 litres. One correction changed that batch and the item total. | **Check pot** reminded, then disappeared after **Mark done**. |
| Taylor (UK) | Created a new invented loan; the overdue bike-pump reminder disappeared after **Mark returned**. | Bottled water, selected batch 12 → 13 litres. One correction changed that batch and the item total. | **Check windowsill pot** reminded, then disappeared after **Mark done**. |

Each journey saved the new loan once, stored a return date, set the Garden job to done, and left other Stock batches untouched. The count review explained that the change was a stocktake correction rather than a purchase. Every one of the 90 route snapshots returned HTTP 200 and had document width no greater than its 320px or 1200px viewport. AU/UK screens showed day first and US screens month first.

**Limit:** This was a Chromium viewport check with invented local records. It does not prove touch behavior on a physical phone or screen-reader behavior. Source for expected behavior: shipped `modules/lent_out/`, `modules/stock/` and `modules/garden/` contracts and the three `examples/households/` files, checked 19 November 2026; no outside household guidance was used.
