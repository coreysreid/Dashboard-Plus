# 0107. Things to do: Today, This week, This month and This year over the work modules already own; Routines

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Corey asked for "checklists for making sure today's tasks are done, the weekly
tasks are done and the monthly, and annual tasks are done". There is now a
**Things to do** page (in the top bar, and a card on Home) with tabs **Today**,
**This week**, **This month**, **This year** and **No date yet**. It gathers the
dates you already recorded: Home care jobs, Garden jobs, alarm and kit checks,
pet treatments, vehicle registration, insurance and services, document reviews,
things lent out, and a new list, **Routines**, for your own repeating tasks such
as watering the pot plants or putting the bins out.

Every row is finished the same way as on its own page. Home care's **Mark done**
opens Home care's own form; Garden's **Mark done** ticks the Garden job; an alarm
check says **Open record to update**, because pressing a button should never hide
a reminder without the record changing. A routine has **Mark this occurrence
done** and **Skip this time**, each asking for the next date (your repeat offers
one; nothing is chosen for you). Something late shows once, as "Due since
18/11/26", never as a pile of missed weeks or a streak. When a late routine is
done, it says "Earlier times were not recorded"; nothing is filled in for them.
Straight after a tick, **Undo** puts it back, as long as nothing has changed since.

## What we chose
- **No second store of ticks.** `src/dashboard/core/checklist.py` reads, on each
  page view, every switched-on table whose `watch.expiring` says `wording = "due"`,
  with the same `where` that keeps finished rows out of Needs attention (Garden
  jobs not done, loans still out, routines not paused). Use-by dates (Household
  stock batches) are not tasks and stay out. One record is one row; its date is
  the only open occurrence. A moved date, a deleted or restored record, or a
  module switched off changes the view at once, because nothing is cached.
- **Which button a row gets is worked out from the module's own declarations:**
  an action with `adds` (a Mark done form) is a link to that form; a one-step
  action whose `set` takes the row out of the reminder's `where` (Garden's Mark
  done, Things lent out's Mark returned) is a small POST form; anything else is
  **Open record to update**. No module is named in the code.
- **Windows follow the household's calendar.** Today is the computer's date, as
  everywhere. This week starts on the household's choice in Settings ("Weeks
  start on": Monday, Sunday or Saturday; unset, Sunday where dates are written
  month first, otherwise Monday). This month and This year are calendar ranges,
  not rolling days. Late rows are shown in every window from their own date; in
  This year, late rows from an earlier year are under **Still to decide**.
- **What was done** comes from the saved Mark done (and Skip this time)
  operations in history (decision 0091), dated by the day the person entered,
  not by the UTC time it was saved; undone ones, and ones whose record or added
  entry was deleted, are left out. **Done today / this week / this month**
  lists them with **Undo** while it is still safe. This year shows, for each
  month, how many open dates fall in it and how many times work was recorded as
  done or skipped, one grouped query per table.
- **A new Routines module** (`modules/routines`, files only, requires People and
  Household stock): Routines (task, optional Place and person, optional repeat
  every 1 to 99 days, weeks, months or years, First date, Next date, Last done,
  Paused, notes) and **Done or skipped** (routine, Done or Skipped this time,
  Was planned for, On, who, notes). No column is private; notes say not to write
  codes, and every column travels like other ordinary records (decision 0100).
- **Four small additions to actions that add a record** (DESIGN.md 5.8):
  `adds.copy` copies fields of this record into the added one (the planned date
  into Was planned for); `latest` may leave out `into` (a skip records its day
  but never sets Last done); `next_date.repeat` may say `from` (step the repeat
  from this record's planned date instead of the day it was done, skipping past
  dates rather than filling them in) and `anchor` (keep a date's day of the
  month, so a routine on the 31st comes back to the 31st after February, and
  29 February to 29 February in a leap year); and `counts_as = "skipped"`.
  Repeats may now be in days too. Home care's behaviour is unchanged.
- **Back to Things to do.** Opened from the page, a form or button returns there
  (only to `/to-do...` addresses, never elsewhere) with its notice and Undo; a
  button pressed on a row that changed meanwhile says "This task changed while
  you were looking at it. Check the current date and try again. Nothing was
  saved."
- **Screens need no script**: links and small forms only. At phone width each
  row stacks, the date and source come before the button, and every button's
  accessible name includes the task.

## Why we chose it
- The draft's first rule (Lane B, batch 20 item 96) is one source of truth per
  task. Reading the existing due dates and actions means Home care's Mark done
  stays the only way to complete a Home care job, and nothing can disagree with
  Needs attention.
- Declaring through `watch.expiring` and `actions`, which every module already
  writes, keeps the view generic: a module added later appears without new code.
- A routine needs a real home for "done on which day, planned for which day",
  and the Mark done machinery (one transaction, revision check, one-use number,
  Undo) already gives the draft's double-click, stale-page and Undo rules.

## What else we considered
- **A separate table of occurrences, one row per planned date.** Rejected: it
  would have to be kept in step with every module's dates, and would tempt the
  page into stacking missed rows. The record's own date is the one open
  occurrence; Done or skipped keeps the history.
- **Ticks stored by the checklist for every module.** Rejected by the draft: a
  tick that hides an alarm check's reminder without the check date changing
  would be a false "done".
- **A one-step Mark done for routines.** Rejected: the next date is the
  household's choice each time, as in Home care.
- **Seasonal review questions in This month.** Not now: the seasonal checklist
  draft is not promoted and its sources would need re-checking first.

## What this costs us (the downsides)
- Every page view runs one query per table that keeps a due date, plus one over
  recent history for the Done list. Fine at 1,000 routines and 10,000 times
  (a test checks it); a household with far more would want an index on history.
- Garden's and Things lent out's one-step buttons leave no named operation in
  history, so they do not appear under "Done this week" or in This year's done
  counts; the row simply leaves the list, and Garden keeps the finished job.
  (Since decision 0112 they do write one, so they are listed and counted, with Undo.)
- Only the most recent tick can be undone, and only while nothing changed since,
  as in decision 0091; after that, changes are made by editing.
- "Due since" for every late row means a document review that is a year late
  reads the same as yesterday's bins. That is deliberate (no urgency badges),
  but some households may want to sort by source instead; the Show filter helps.
- A routine's repeat is worked out on the server for its form, so the offered
  date does not change as Done on is typed (Home care's still does).
- A household week start is one more setting, shown only in Settings.

## How hard it is to undo
Easy to Medium. Remove `checklist_pages`, the template, the Home card and the nav
link to take the page away; nothing is stored by it. Switching Routines off hides
it and keeps its records; removing the module means a migration-free deletion of
its folder (its tables stay in old databases, as with any module). The four action
additions are optional keys; removing them means removing them from Routines too.

## We should revisit this if
- Households ask for Done counts for Garden or loans (one-step actions would then
  need to write a named operation).
- Pages with many sources feel slow, or households want Next week as a preview.
- The seasonal question draft is promoted and its questions should be offered under
  This month as **Look at this question**, never as a tick.
