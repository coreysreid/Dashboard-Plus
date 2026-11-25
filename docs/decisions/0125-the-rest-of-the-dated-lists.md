# 0125. The rest of the dated lists on the calendar, and Home care work done as bars

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0072 (a finished job is never reminded about), 0119 (the `calendar` declaration, never "missed"),
  0122 (a calendar of a table's own records, one month on Things to do), 0124 (bars over time)

## In plain words
**Things to do → Calendar** now also shows Documents (each paper's review or renewal date), First aid kit checks
(the day each check was done and each kit's next check date), Home layout's alarms and safety equipment (the day
each was last tested and its next check date), and Things lent out (the day each came back, and while a thing is
still out, the day it is due back). A lent thing that came back has no due date left, and nothing is ever called
late or missed. A job's page in Home care also gets **Work done per month** bars (and per week): how many times that
job was done. Utilities has no dated reminder, so it has nothing to show.

## What we chose
- **Own-records calendars** (0122's shape, no `per`) for Documents (`renew_by`), Home layout's equipment
  (`when = "last_tested"`, due from `next_check`) and Things lent out (`when = "returned_on"`, due from `due_back`,
  open loans only because the reminder's own `where` already says so).
- **0119's `per` shape** for Medical's Kit checks (`per = "kit"`, `when = "checked_on"`, `look = "done"`,
  `due = true`): it shows every past check, and the kit's one next date from the kit's reminder. The kits table has
  no calendar of its own, so each date is on one calendar.
- **Bars** on Home care's Work done: `measure = "count"`, `per = "job"`, by month or week.
- **Privacy.** Only a record's name and a date show. Notes, kinds, holders, places, who checked and Home layout's
  private access details are never read. Tests plant a secret in each of those and check it is on no page.
- **Tests** in `tests/test_calendars_rest.py` (7): the declarations, every new list on one month with its words, no
  private text and no "missed", a returned loan losing its due date, no script, modules off hidden with their records
  kept, and the Work done bars.

## What was left out, and why
- **Vehicle past services:** the services table keeps one `last_done` and one `next_due` per service, and Vehicle
  running's estimates are quotes, not services. There is no history of earlier services to show, and adding a
  history table is a migration and a second place to type a date. The calendar keeps showing the latest done day.
- **Garden jobs done per month (bars):** a bars chart needs a dated table with a required link to one subject. Garden
  jobs have only a "done" tick, no done date, and the presses live in history. Not possible without a new table.
- **Home care's own "Work done" bars by all jobs together:** bars show one job at a time, as the declaration requires.
- **Garden presses saved before 0112:** they have no named history entry, so nothing says which button press they
  were; guessing from a changed tick could show a wrong day. Left as documented in 0122.
- **First aid training renewals:** the table is a person's record; not asked for, so not added.

## Why we chose it
Each is one `calendar` section in a `tables.toml`; no new code, no stored data, and one date on one calendar.

## What this costs us (the downsides)
- Alarms and loans show only the latest tested or returned day, as Vehicles' services do.
- A kit's date line reads "Example kit: planned" because the reminder's own words are not used by a `per` calendar.
- "Return done" and "Test done" use the fixed look words.
- Things to do's month reads two or three more tables per page view.

## How hard it is to undo
Easy. Delete the added `calendar` and `bars` sections from the five `tables.toml` files; no data changed.

## We should revisit this if
- Households want a history of vehicle services or garden jobs with dates (a new table would be needed).
- Utilities gets a dated reminder (for example a contract end date): it is one `calendar` section.
