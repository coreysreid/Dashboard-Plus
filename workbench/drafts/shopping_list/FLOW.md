# Shopping from what is running low

Updated 18 November 2026 for shipped batches (decision 0053) and the item-following batch picker (0057), M2 / J2. The shipped Stock item has **Amount on hand**, **Unit**, **Keep at least** and **Category**. Its running-low watch applies below the minimum; this draft builds a shopping trip from those records. All household names and quantities here are invented. The list is a plan, and ticking a line in a shop never changes Stock.

## Make a list

From Needs attention or Stock choose **Make a shopping list**. The first panel says: “These items are below the amount you chose to keep. Check what you need before you shop.” Include each active item with a positive Keep at least and `Amount on hand < Keep at least`. Show `on hand`, `keep at least` and `suggested to buy = max(0, minimum − quantity)` in the item's own unit. A zero minimum means no automatic list row; offer a manual **Add something else** action. If stock changes while editing the list, show “Amounts changed since you made this list. Review the suggested quantities” and recompute proposals without overwriting the person's edited quantities.

Group by a household-chosen shop aisle when one exists, otherwise by Stock category. Suggested groups can be Pantry, Fresh food, Cleaning, Toiletries, Pets, Power and Other, but these are display hints and must be editable per household/shop. A fresh tomato is still a pantry-category Stock record today; the list can suggest Fresh food without silently changing its Stock category. Keep an “Unassigned aisle” group. Sort within each group by the household's order or name. Combine identical catalogue goods only if unit and destination Stock item are identical; otherwise preserve separate rows and show which item and batch each will replenish.

Worked example: Tinned tomatoes have 2 tins, Keep at least 6 tins, so suggest 4 tins. Rice has 0.5 kg, Keep at least 2 kg, so suggest 1.5 kg; a shop may sell 1 kg bags, so let the person change the buy quantity to 2 kg or 2 bags after choosing the conversion. Water has 4 litres, Keep at least 12 litres, so suggest 8 litres; do not suggest a number of bottles unless the person enters bottle size. Show exact copy: “Tinned tomatoes — 2 tins at home; keep at least 6; buy 4 tins.” The formula is arithmetic on the person's own figures, not a safety recommendation.

Before starting the trip, each row allows **Change amount**, **Remove from this trip**, or **Move aisle**. The list can be printed or used on the same device without a connection. A removed row does not change Keep at least or hide Needs attention. If there is nothing below minimum: “Nothing is below your chosen minimum. Add items if you want a list for this trip.”

## In the shop

Each row has a large checkbox labelled “Picked up [item]”. Tick or untick it; show a count such as “7 of 12 picked up”. Keep the list usable with keyboard and a screen reader. Allow “Could not find it” so the item remains visibly unpurchased. Changing a quantity (for example from 4 to 3 tins) records what was actually picked up. Do not interpret the tick as paid for, brought home or safely stored. A family member can use a printed copy; there is no shared cloud sync in this design.

## Bring the trip home, batch by batch

Choose **Add what came home to Stock**. The review begins: **“Check what came home. Stock has not changed yet.”** It shows only picked-up rows and asks for the actual amount in the item's Stock unit. A returned item can be unticked or changed to zero. If 3 tins came home for a planned 4, add 3; if Rice arrives as two 1 kg bags, confirm **2 kg** once. Do not count both kilograms and bags. A shopping tick is still only a plan.

For each item, choose **Add another date or place** to split the actual amount across batches. One purchase row means one quantity, the item's exact Stock ID, its printed **Use by** date if known, a full-path Place and either **Start a new batch** or an explicit **Add to this recorded batch** choice. Do not merge automatically just because a date/place matches. The shipped Stock in form already creates a new batch from a bought movement with no `lot` chosen; a chosen batch must belong to that item. The item-following **Which batch** picker from decision 0057 is the pattern to reuse. When an existing batch is chosen, hide the new-batch Use by and Where you put it fields and show the chosen batch's date and path for review.

**Worked two-date purchase:** Five invented tins of Tinned tomatoes came home. The review shows:

> Tinned tomatoes — **2 tins** — use by **20/05/27** — **Kitchen › Pantry › Shelf 3** — **Start a new batch**  
> Tinned tomatoes — **3 tins** — use by **20/11/27** — **Garage › Garage shelves** — **Start a new batch**

If the item previously held 2 tins, the result says **“Added 5 tins to Stock in 2 batches. Tinned tomatoes now has 7 tins on hand.”** Link each created batch and movement. The two bought movements add 2 and 3 exactly once; their distinct Stock batch (`lot`) IDs keep date and place separate. A blank date displays **“Use by not recorded”**; never infer a date from the catalogue. A household in the US sees **05/20/27** and **11/20/27** for those same days.

For drinking water, confirm actual litres and retain the linked Stock item's own **Safe to drink** answer. Only a confirmed drinkable-water item in litres affects days of water; the shopping list must not turn the flag on. Keep package size and Stock unit separate.

On **Save Stock in**, save the accepted purchase rows as one **trip commit**, then mark them **Added to Stock**. This trip commit ID is distinct from every Stock batch (`lot`) ID and links each trip line to its exact bought movement and batch. Show new on-hand amounts and which items remain below minimum. A second press or restart must not double-add. If one row fails, roll back the whole trip commit and leave the review visible. Offer **Undo this trip's Stock in** only with a conflict review that respects later movements and cannot make a batch negative. Unpicked rows stay on the list and under Needs attention if still low. Closing a trip without buying changes no Stock, and later list edits do not mutate saved movements.

## References

- [Shipped Stock fields and running-low watch](../../../modules/stock/tables.toml) and [Stock labels](../../../modules/stock/labels.toml), checked 18 November 2026. The only suggested amounts are calculated from a household's own entries.
- [Shipped batch contract](../../../modules/stock/tables.toml) and [decision 0057](../../../docs/decisions/0057-batch-picker-follows-the-item.md), checked 18 November 2026.
- [J2: the shopping comes home](../../../docs/JOURNEYS.md), checked 18 November 2026. This is a product journey, not guidance on how much to keep.
