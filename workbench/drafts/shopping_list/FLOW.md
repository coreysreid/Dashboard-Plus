# Shopping from what is running low

Drafted 17 November 2026 for M2 / J2. The shipped Stock item has **Amount on hand**, **Unit**, **Keep at least** and **Category**. Its running-low watch applies below the minimum; this draft builds a shopping trip from those records. All household names and quantities here are invented. The list is a plan, and ticking a line in a shop never changes Stock.

## Make a list

From Needs attention or Stock choose **Make a shopping list**. The first panel says: “These items are below the amount you chose to keep. Check what you need before you shop.” Include each active item with a positive Keep at least and `Amount on hand < Keep at least`. Show `on hand`, `keep at least` and `suggested to buy = max(0, minimum − quantity)` in the item's own unit. A zero minimum means no automatic list row; offer a manual **Add something else** action. If stock changes while editing the list, show “Amounts changed since you made this list. Review the suggested quantities” and recompute proposals without overwriting the person's edited quantities.

Group by a household-chosen shop aisle when one exists, otherwise by Stock category. Suggested groups can be Pantry, Fresh food, Cleaning, Toiletries, Pets, Power and Other, but these are display hints and must be editable per household/shop. A fresh tomato is still a pantry-category Stock record today; the list can suggest Fresh food without silently changing its Stock category. Keep an “Unassigned aisle” group. Sort within each group by the household's order or name. Combine identical catalogue goods only if unit and destination Stock item are identical; otherwise preserve separate rows and show which place or lot each will replenish.

Worked example: Tinned tomatoes have 2 tins, Keep at least 6 tins, so suggest 4 tins. Rice has 0.5 kg, Keep at least 2 kg, so suggest 1.5 kg; a shop may sell 1 kg bags, so let the person change the buy quantity to 2 kg or 2 bags after choosing the conversion. Water has 4 litres, Keep at least 12 litres, so suggest 8 litres; do not suggest a number of bottles unless the person enters bottle size. Show exact copy: “Tinned tomatoes — 2 tins at home; keep at least 6; buy 4 tins.” The formula is arithmetic on the person's own figures, not a safety recommendation.

Before starting the trip, each row allows **Change amount**, **Remove from this trip**, or **Move aisle**. The list can be printed or used on the same device without a connection. A removed row does not change Keep at least or hide Needs attention. If there is nothing below minimum: “Nothing is below your chosen minimum. Add items if you want a list for this trip.”

## In the shop

Each row has a large checkbox labelled “Picked up [item]”. Tick or untick it; show a count such as “7 of 12 picked up”. Keep the list usable with keyboard and a screen reader. Allow “Could not find it” so the item remains visibly unpurchased. Changing a quantity (for example from 4 to 3 tins) records what was actually picked up. Do not interpret the tick as paid for, brought home or safely stored. A family member can use a printed copy; there is no shared cloud sync in this design.

## Bring the trip home

Choose **Add what came home to Stock**. The review page shows only picked-up rows and asks for actual quantity, item, place and, when lots ship, printed use-by/best-before date and lot details. Wording: “Check what came home. Nothing has changed in Stock yet.” A picked-up but returned item can be unticked or changed to zero. If 3 tins came home for a planned 4, add 3 tins. For Rice bought as two 1 kg bags, confirm **2 kg** to the Rice item; do not add **2 kg and 2 bags**. For drinking water, confirm litres and “Safe to drink” under the normal Stock rules. Keep package size and Stock unit separate.

On **Save Stock in**, create bought/add movements with the trip's date and one batch ID, then mark those shopping rows `Added to Stock`. Show new on-hand amounts and which items remain below minimum. Offer **Undo this trip's Stock in** with a conflict review if any affected item was edited afterward. A second press or page reload must not double-add. Unpicked rows remain on the list and under Needs attention if still low. A trip can be closed without adding anything; later edits to the list must not mutate historical Stock movements.

## References

- [Shipped Stock fields and running-low watch](../../../modules/stock/tables.toml) and [Stock labels](../../../modules/stock/labels.toml), checked 17 November 2026. The only suggested amounts are calculated from a household's own entries.
- [J2: the shopping comes home](../../../docs/JOURNEYS.md), checked 17 November 2026. This is a product journey, not guidance on how much to keep.
