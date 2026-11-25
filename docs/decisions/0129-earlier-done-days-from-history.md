# 0129. Earlier done days from a record's own history, and Garden's done date

- **Status:** Accepted (three downsides resolved by 0132)
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0075 (one-press buttons), 0091 and 0112 (Mark done in history, with Undo), 0107 (Things to do),
  0119 (calendars, never "missed"), 0122 (a calendar of a table's own records), 0124 (bars over time), 0125 (the
  rest of the dated lists, and what it left out)

## In plain words
The calendars could only show the latest day a vehicle service, an alarm test or a return was done, because
each of those keeps one date. Now every earlier day shows too: when a household moves a service's "Last done"
from March to July, March stays on the calendar as ✓ done, marked "(an earlier time, from its history)". A date
typed back to fix a mistake, a date cleared, and a Mark done that was undone never show. Garden jobs now keep a
**Done on** date that Mark done fills in, and Garden gets **Jobs done per month** bars. Jobs marked done before
this change keep no date: nothing is guessed. Their Mark done press still shows on the day it was pressed.

## What we chose
- **Read the history the program already keeps**, not a new table (`done_days` in `core/calendars.py`). Every change to a
  record is saved in history with the values before and after (`core__audit`). For a calendar's `when`
  column, the values it held are read in the order they were saved. A value counts as an earlier done day only
  when **the very next value saved is a later date**, and it was **saved on a later household day** than the value
  itself was typed. So:
  - typing a date back (07-19 to 07-09) is a correction: 07-19 never counts;
  - clearing a date (by hand, or Undo of Mark returned or Mark done) never counts the cleared date;
  - a date changed again the same day it was typed (a slip fixed at once) never counts;
  - a deleted record has no done days; restored, it has them again;
  - one record counts once a day, whatever the history says.
- **A press that did not set the date** (a one-step press, decision 0112, whose saved fields leave out `when`)
  counts on the day it was pressed, read exactly as Things to do reads presses, so an undone press is left out.
  This keeps the Garden presses saved between 0112 and this decision on the calendar without writing a date into
  any job. `checklist.Done` gained `fields`, the fields a press set, so this can be told.
- **Opt in with `history = true`** on a calendar of a table's own records with `when` (0122's shape). The checker
  refuses it on a `per` calendar (each entry there is already its own record), without `when`, or not true or
  false, in plain words naming no module. Declared on Vehicle services (`last_done`), Home layout's alarms
  (`last_tested`), Things lent out (`returned_on`) and Garden jobs (`done_on`). An earlier day's line in words
  says "(an earlier time, from its history)", because the record's own page shows a different date.
- **Garden's done date.** A new optional date column `done_on` ("Done on") by an additive migration
  (`0002_done_on.sql`: `ALTER TABLE ... ADD COLUMN`, nothing filled in). Mark done now sets `done = true` and
  `done_on = "today"`, and Undo puts both back. Jobs done before keep an empty Done on; their press shows as
  above. A one-step press's "today" is now the day the press is dated by (the page's today), so the date it sets
  and the press always agree.
- **Bars of a whole list, counting done days.** This uses the one "whole list" shape of 0124's declaration that
  decision 0128 added for Spent per month (built in parallel; the two were merged into one code path): leave out
  `per` and `subject` for one chart of the whole list, named by the module's title, linked from Home and from the
  list, never a panel on one record's page; 0128's groups by a choice of the linked record and its private amounts
  counted until a pressed Show are unchanged. This decision adds `history = true` (with `when` a non-private date
  column that need not be required), which counts the same done days the calendar shows, with `measure = "count"`
  and no `where` or `group`; it works with or without `per`. A whole-list chart is also shown under its table's own
  calendar at `/calendar/<table>`, and the list's single "See:" line links to both ("See: Garden calendar · Jobs
  done per month"). Garden declares **Jobs done**, by month or week. Its caveat says each bar counts the days each
  was recorded as done, earlier ones from history, and that a date typed back or cleared is never counted. Every
  0119 and 0124 rule stays: the fixed looks and symbols, never "missed", no script, 320px, private columns never
  read (only the record's name and a date are shown).
- **Tests** in `tests/test_done_history.py` (19): the checker's words, the shipped declarations, the migration
  adds an empty column only, the core names no module, earlier days moved forward, a date typed back, a same-day
  fix, a cleared date, delete and restore, alarm tests across months and on Things to do, a loan's undone return
  and a return moved back, Garden's Mark done and Undo, an old press without a date, Jobs done per month (page,
  list link, calendar panel, never on a job's page), Garden switched off, and one mark per record per day.

## Why we chose it
- **It is the honest record.** The history already holds every date the household saved, with when it was saved;
  no second place to type a date, and nothing is copied that could drift.
- **Nothing is stored or migrated** for Vehicles, alarms and loans, so it is safe for existing households: their
  past edits since they started using the program show at once, and removing `history = true` takes them away.
- The rules lean towards leaving a day out: a correction, a clear or a same-day change could be a mistake, so
  none of them is shown. A missing ✓ is a smaller harm than an invented one.
- Garden had no date to count at all, so a column was the only way to get bars; adding it empty and filling it
  forward only keeps 0125's promise that nothing is guessed.

## What else we considered
- **A small done-log table** written on every Mark done and every forward move of a date: a second copy of what
  history holds, a core migration, and the same judgement about which edits count, made once at save time instead
  of at read time (so a later correction could not take a wrong day away). Its one advantage, that a household
  could delete a wrong entry, would need new pages. Not now.
- **Counting every value the date ever held:** shows typing slips and undone presses as done days. Refused.
- **Filling Garden's `done_on` from the saved presses** in the migration: exact for presses since 0112, but a
  data change to every household's jobs, and the presses already show without it.
- **A history table per module** (as 0122 and 0125 noted): a migration in three modules and a second place to
  type a date.
- **Making `done_on` required when a job is done:** would refuse to save older done jobs that have no date.

## What this costs us (the downsides)
Decision 0132 resolves the first two and the Garden press one: a household can take a wrong earlier day off with **Not a done day** (with Undo), a date cleared a day or more after it was typed now counts, and an old press with a Done on typed later counts once.

- **A forward fix on a later day still counts the wrong date.** If a household types 1 September on 2 September
  and only on 10 September changes it to 10 September, 1 September shows as an earlier done day, and nothing on
  the page can remove it. The line says "from its history" so it can be recognised.
- **A cleared date is lost.** Lending the same thing again by clearing Returned on, then marking it returned,
  leaves only the newest return; the earlier one is not shown (a return is usually its own record, so this is
  rare).
- **Only edits saved by this program count.** Dates from before a household started, or from a spreadsheet
  imported as new records, show only the date each record keeps now; a backfilled history typed in one sitting
  (one date after another on the same day) counts only the last.
- Each calendar or bars view with `history` reads the table's whole history for that column, plus Mark done
  presses; fine for a household, slower with many years of daily edits.
- An old Garden press and a Done on typed by hand later for the same job show as two days if they differ.
- "(an earlier time, from its history)" makes lines longer at 320px; the list in words still wraps.
- One more declaration key on calendars and bars to learn and check.
- Vehicle services have no bars yet; they would need one `[[tables.services.bars]]` with `per = "vehicle"`.

## How hard it is to undo
Easy. Remove the `history = true` lines from the four `tables.toml` files and Garden's `[[tables.jobs.bars]]`;
drop `DoneDay`, `earlier_done`, `done_days` and the `history` branch in `calendars.py`, the `history` branches
in `bars.py` and `bar_pages.py`, the `history` checks in `modules.py`, `table_panels`, the calendar link in
`_see_also` (`pages.py`), the bars block
in `calendar.html`, and `Done.fields`. Garden's `done_on` column stays (a released migration is never edited);
taking `done_on` out of Mark done's `set` stops it being filled. No household data is changed.

## We should revisit this if
- Households see a wrong earlier day they cannot remove, or ask to delete one: that is the sign a done-log table
  with its own Delete is needed.
- Someone types a whole past service history in one sitting and expects every date to show.
- Vehicle services or alarms want bars ("services per year"): one `bars` section with `history = true`.
