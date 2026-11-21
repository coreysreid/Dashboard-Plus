# Routine checklist engine checks

Written **21 November 2026** for invented jobs, local dates and sources.

1. A Home care job due today appears once in Today and once as the *same linked row* in week/month/year views. **Mark done** uses decision 0091's form and commits one Work done plus chosen next date; no routine tick or duplicate completion is added.
2. A Garden job due today with `done = false` appears. Its shipped Mark done sets `done = true`, removes the due reminder and leaves the job in history. It does not make a new job for next week.
3. A Home layout alarm check date appears with **Open record to update**, not a fake tick. Opening without changing the date leaves its due warning visible.
4. A new daily, weekly, monthly and yearly routine stores a chosen repeat and one open occurrence. Double click/retry writes one completion. A repeat offers a new date but no completion happens without a person.
5. Miss three occurrences of a weekly routine. Today shows one **Due since** card and no shame/streak. On completion, scheduled versus done dates remain in history and **Earlier times were not recorded** appears; no three fake completed rows are backfilled. Skip this time is distinct and reversible.
6. Move a due date, switch a module off, delete a linked row and restore it. The view recomputes from current IDs/revisions; no stale cached tick survives or changes another module's record.
7. Check 31 January monthly repeat, 29 February yearly repeat, daylight-saving change, UTC/local midnight and two household week starts. Offered dates, week/month/year boundaries and labels follow the household setting; no UTC-day duplicate.
8. A seasonal question fits only the chosen hazard and source region. A linked positive Stock item is offered but never auto-ticks it. Answer date/reviewer is separate from the stock item's own movement/check date.
9. Undo a just-saved routine tick before another change: the original open occurrence returns. After a dependent edit, Undo refuses with exact words and preserves both records. Home care uses its existing Undo rules.
10. Empty views say no **recorded** dates, never that the household is safe or all work is done. A no-date job remains discoverable. Needs attention and the checklist show one source reminder, not two independent states.
11. At 1,000 recurring definitions and 10,000 historical occurrences, Today queries only active due/open rows and year view aggregates by month. Phone width, keyboard and screen reader keep every action associated with its row.
