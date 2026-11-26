# 0136. Staying quick with years of records: a timing tool, and two pages that read less

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0119 (calendars), 0124 (bars), 0126 (timelines), 0129 and 0132 (earlier done days from history), 0128 and 0133 (Spent per month)

## In plain words
We checked that the pages built in 0119 to 0133 stay quick for a household that has used the program for years:
three pets fed twice a day for five years, two people with a daily dose for three years, two cars, 40 routines,
2,000 Stock ins with prices and some refunds, and so on, about 19,000 records. Every page opens in well under a
tenth of a second on this machine (the slowest, a vehicle's calendar, took 33 ms; the target was 300 ms). We made
the two slowest kinds of page read less anyway, because they grow with every year of use, and added a tool so the
check can be repeated. Nothing a household sees has changed: the same words, the same days, the same links.

## What we chose
- **A timing tool, `tools/time_pages.py`.** It builds an invented household of that size in a temporary folder
  (names like "Example Pet 1"; nothing real), opens each page through the real program, and prints how long it took
  and how many database questions it asked, marking any page over 300 ms. It is not part of `check_all.py`: building
  and timing takes a minute and speed depends on the computer. `--data FOLDER` keeps the household between runs,
  `--rebuild` starts again. `tests/test_speed_0136.py` builds a small one (about 3 seconds) for its checks.
- **Timelines read only the newest rows.** A record's timeline showed 25 lines but read every feeding the pet ever
  had (11,000 for each pet, 36,000 after 20 years) to find them. Now each list asks the database for its newest
  rows first, a few more at a time, and stops as soon as the newest 25 lines (or 8 on a record's page) are
  certain, which is a handful of days. A date written with an offset can fall on the day before or after the date
  written in it, so rows within one day of the oldest row read are never trusted until the next batch confirms
  them. "Earlier" works the same way from the day it starts before; the change "since the last weigh-in" still
  finds the weigh-in before the page. If nothing older is left to show, or a day has nothing, the old full read is
  used (the rare empty page). New: `timeline.window` and `cut` on `timeline.page`.
- **Earlier done days read only the records that can matter.** Vehicle services, alarm tests, loans and Garden jobs
  find earlier done days by reading the table's history. Now a record whose history never held a date in the month
  or period being drawn, and that never had a Mark done press, is skipped, because it cannot add a day to that
  view. The date saved in each history line is read inside the database instead of reading the whole line, and the
  day a line was saved is worked out only for a date inside the view. A record with presses is read in full, as
  before, because a press and the date typed after it belong together (0132). Reading the whole table's history
  (no view given) still works and gives what it always gave.
- **No new tables and no migrations.** The columns these queries use for ranges already have indexes (`pet` and
  `given_at` on feedings, the table and record on history). A combined index would save a sort of one pet's rows
  (about 3 ms for 36,000) and is not worth a migration in each module.

## Numbers (milliseconds, fastest of three to five loads, this machine)
The invented household as described above (about 19,000 records, 25,000 history lines). "Five years" is the usual
size; "twenty years" is the same household with four times as much history, to see which pages grow.

| Page | 5 years before | 5 years after | 20 years before | 20 years after |
|---|---:|---:|---:|---:|
| Home | 9 | 9 | 76 | 31 |
| Needs attention | 4 | 4 | 19 | 11 |
| Feeding calendar (month) | 4 | 4 | 26 | 8 |
| Vehicle services calendar | 33 | 17 | 170 | 58 |
| Things to do: Calendar, all lists | 34 | 16 | 302 | 176 |
| Bars by day or month (feeding, doses, routines, Home care) | 2 to 8 | 2 to 7 | 5 to 24 | 3 to 11 |
| Vehicle services bars by month | 18 | 14 | 71 | 43 |
| Spent per month, before and after Show | 3 and 6 | 3 and 6 | 4 and 8 | 3 and 4 |
| Pet timeline, first page and Earlier | 28 and 29 | 9 and 8 | 197 and 118 | 24 and 24 |
| Pet's own page with its panels | 37 | 16 | 208 | 42 |
| Other record pages | 3 to 11 | 4 to 11 | 5 to 40 | 4 to 40 |

The 20-year figures were measured once each, with a single load, and vary by about 20 percent between runs.

## Why we chose it
- Nothing needed fixing at the size asked for, so the honest change is small: only the two places whose cost
  grows with the length of the history, and only where the answer can be proved the same.
- Both changes keep the rule "nothing is stored, so an edit, delete or restore shows at once": there is no cache
  that could show something old.
- Tests compare the new reads with the old ones on the invented household (every page of every timeline, and the
  earlier done days for four tables across five periods), including times written with an offset around midnight
  in a household on the other side of the date line.

## What else we considered
- **A saved list of done days or timeline lines**, updated on every change: fastest, but a second copy that could
  drift, and a migration. Refused (the same reasoning as 0129).
- **Doing the whole history rule inside the database**: possible with window functions, but the rule has several
  exceptions (corrections, Undo, presses) that are clearer and safer in Python.
- **Combined indexes** such as pet then time: see above.
- **Fetching every named record on a page in one question**: a calendar names each mark with a few small lookups
  (a few hundredths of a millisecond each), 50 to 170 on the busiest page. Measured, it is not what makes a page
  slow, so it was left.

## What this costs us (the downsides)
- The timeline reader is harder to read than the old one: it must be sure about the day boundary. If a row's date
  could not be read it is treated as the old code treated it (left out) except that the page may then offer an
  "Earlier" link that leads to an empty page.
- A record with many Mark done presses (hundreds on one Garden job) is still read in full for its earlier done
  days. At twenty years of heavy use that is the slowest remaining view (Things to do, Calendar, 176 ms).
- The query-count limits in the tests are loose on purpose (a calendar asks one small question per mark
  today), so they catch a page that starts asking per record twice over, not a small slip.
- The timing numbers belong to this machine; a slow USB stick or an old laptop will be several times slower.

## How hard it is to undo
Easy. `timeline.items` and `timeline.page` without `cut` are unchanged: point `timeline_view` back at them. For
done days, call `_history` without a window. The timing tool and its tests can simply be removed.

## We should revisit this if
- `tools/time_pages.py` shows a page over 300 ms at the five-year size on a household's own computer.
- A household with a very long Garden or loan history finds Things to do's Calendar slow: the next step is a
  small done-log table (the option 0129 refused), which would also let the press logic be read from the database.
- Pages start to ask one small question per record for hundreds of records: then fetch the names together.
