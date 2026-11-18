# Stocktake correction acceptance checks

Run with invented two-batch Kidney beans: 3 tins at Kitchen › Pantry › Shelf 3 due 20/05/27, and 10 tins at Garage › Garage shelves due 20/11/27. Item total starts at 13. Dates use the household's selected order. Contract checked **18 November 2026**.

1. **Exact batch:** Open the first batch from its item, Batches list or Needs attention. The count form shows item, full place path, use-by date, **3 recorded here**, and a single **You counted** input. Counting the item total without identifying a batch is not offered.
2. **Increase:** Enter 5. Review says 3 recorded, 5 counted, **+2 stocktake correction**, and 15 across two batches. Saving creates one `counted_more` movement linked to that batch and item, batch amount 5, item total 15.
3. **Decrease:** Start again from 3 and enter 1. Review says **−2**, explicitly not Used or Thrown away. Saving creates one `counted_less` movement, batch 1, item 11. Waste and shopping figures exclude it.
4. **No difference:** Enter 3 when 3 is recorded. No movement or audit change is made; the page says no correction was saved.
5. **Zero:** Count 0 from 3. The first batch stays as zero history, item total becomes 10, its use-by warning and supplies-sheet row disappear, and the second batch stays untouched.
6. **Invalid:** Blank, negative, malformed, unsupported precision, or a batch not belonging to the item is refused with no count or movement change. An undated batch can be counted without assigning a date.
7. **Concurrency:** Review 3→5, then change the same batch to 4 in another session. Saving the first review refuses it and shows 4; it never applies +2 to the new balance. Two Save clicks create one movement.
8. **History:** Stock in and out shows **Stocktake correction +2 tins** with date, item and batch. The batch and item audit histories show before/after amounts. It is never labelled Bought or added.
9. **Undo:** Deleting a correction reverses only its delta once; restoring reapplies it once. An undo that would make a later current batch negative is refused until later movements are reconciled.
10. **Later use:** After +2, a later Used movement reduces the chosen batch normally. Editing the earlier correction adjusts by the change in its delta without replaying the later Used movement; the final amount remains nonnegative.
11. **Dates:** AU/UK/NZ show **18/11/26**, US **11/18/26** for the same count day. The batch's use-by date remains its own date and is unchanged by a correction.
12. **Old records:** A pre-feature direct batch edit remains intelligible in audit but is not invented as a historical correction movement. Only new confirmed counts create this movement; the migration preserves old totals and Stock in/out history.

These are proposed checks for a future core/UI change, not tests of a shipped stocktake correction feature. Source: current Stock schema and decisions 0043/0053, checked 18 November 2026.
