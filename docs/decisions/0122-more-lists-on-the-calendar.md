# 0122. Home care, Garden, Vehicles and Bills on the calendar, together on Things to do

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0072 (a finished job is never reminded about), 0091 (Home care's Mark done and Work done), 0107
  (Things to do), 0112 (one-press buttons in history, with Undo), 0117 (one reminder per policy), 0119 (the
  `calendar` declaration and its five fixed looks), 0121 (private tables on a calendar)

## In plain words
User 1's top priority is colour-coded calendars to see results and track changes. **Things to do → Calendar**
used to show Routines only. It now shows every dated list in one month: Home care's work done and each job's Do
again by date, Garden jobs on the day they were marked done and each open job's due date, each vehicle's
registration, insurance renewal and service dates (and the day a service was last done), and each bill or
policy's date to check it. Each line in words starts with its list ("Home care · Clear the gutters: Job done"),
the month says how many came from each list, and **Show: All / Bills and insurance / Home care / ...** links keep
one list at a time when the month is busy. The marks, legend, list in words and "a blank day never means missed"
are the same as before. A bill's amount, a car's registration number and every other private detail are never on
a calendar.

## What we chose
- **Home care** declares 0119's calendar on **Work done**: `when = "done_on"`, `per = "job"`, `show = "all"`,
  `look = "done"`, `due = true`. Every Work done entry (from Mark done or an older entry added by hand) is ✓ on its
  day, and each job's one Do again by date comes from the job's own reminder. A job's page shows its own month.
- **A calendar of a table's own records** for lists with no history table: the same `calendar` section without
  `per`. It needs `title`, `entry` and `due = true`, and the table's own `watch.expiring` with `wording = "due"`
  (with its `where`, so a finished Garden job has no due date). Done marks come from `when`, an optional date
  column of the same table that is not private and not the due date (Vehicle services' `last_done`), or else from
  the table's own Mark done presses saved in history, on the day they were pressed and read exactly as Things to
  do reads them (so **Undo Mark done** takes the mark away). `show` is always "all"; `state`, `looks` and a
  private table are refused. The module checker says each mistake in plain words, names no module, and refuses a
  record's due date on two calendars in one module (an own calendar on a table that a `per` calendar already
  shows with `due = true`). Such a calendar is never a panel on one of its own records' pages.
- **Declared by:** Garden jobs ("Garden calendar"), Vehicles' vehicles ("Registration calendar"), insurance
  ("Vehicle insurance calendar") and services ("Vehicle services calendar", `when = "last_done"`), and Bills and
  policies ("Bills and policies calendar"). Bills and Vehicles have no Mark done, so they show due dates only and
  their legends do not offer ✓.
- **Each date once.** Due marks leave out a record whose reminder was moved to another list (decision 0117), so a
  vehicle policy moved to Bills shows under Bills only. A due line for an own calendar says what is due, from the
  reminder's own `what` and `what_when`: "Example hatchback: registration or vehicle tax planned", "Example
  electricity: bill check due today".
- **Things to do, Calendar** puts every non-private calendar with due dates into one month (`together_view` in
  `web/calendar_pages.py`): one grid whose cells count each look across all lists ("Done: 2; Due today"), one
  legend in plain words (Done, Recorded, Skipped, Due, Planned date), "How many this month, by list: ...", and
  each day's lines prefixed with the module's title, sorted A to Z. **Show:** links (`?only=<module>`) keep one
  module's calendars; Previous month and Next month keep the choice; a module with one calendar shows that
  calendar as before, and an unknown or switched-off module shows All. When only one calendar exists at all (only
  Routines on), the tab looks exactly as in 0119 and has no Show links. The links are plain links: no script, and
  they are hidden when printing.
- **Words without a state** follow the look: "Job done" in the legend, "2 jobs done" on a day, "Clear the gutters:
  Job done" in the list; 0119's "Feeding recorded" is unchanged.
- **Privacy.** A line names only the record's own name (its `name` or `record_name`), the reminder's `what` and the
  module's title. Private columns, a bill's amount, cover, reference and notes, a vehicle's registration and Work
  done notes are never read into a calendar; a private table cannot have an own calendar, and Things to do's tab
  still never lists a private table (0121).
- **Tests** in `tests/test_calendars_more.py` (14): the checker's words, the shipped declarations, every list on
  one month with its label, Show links and the month kept, Undo taking a Garden press away, a late date marked
  once and nothing called missed, a policy moved to Bills shown once, no script, invented private values absent
  from every calendar page, the job page panel, and modules switched off.

## Why we chose it
- It answers the request with the dates households already keep: nothing new is typed and nothing is stored, so
  an edit, a delete or an Undo shows at once.
- Reusing the reminder and Things to do's reading of Mark done means "due" and "done" mean the same on the
  Calendar tab as on Today, This week and This month.
- Leaving out `per` is the smallest change to 0119's declaration: one rule, no module names in the code, and the
  same five looks.
- One combined month is what "see everything together" means; the module name on every line and the Show links
  keep it readable when it is busy.

## What else we considered
- **A Work done-style history table for Garden, Vehicles and Bills:** a migration in four modules and a second
  place to type the same date; history already has the Garden presses, and Vehicles and Bills have no done button.
- **Showing each list's calendar one under another** (as 0119 did for several): long at 320px and nothing reads
  across lists; kept only for a module's own page at `/calendar/<table>`.
- **A colour per module:** refused as in 0119; seven colours stop being distinguishable and the looks must stay
  fixed. The module's name in words is the label.
- **Showing a bill's amount or a "paid" mark:** refused; amounts are private, and nothing records a payment.
- **A script filter that hides rows in place:** plain links work without script, print and can be bookmarked.

## What this costs us (the downsides)
- One more shape of the `calendar` declaration to learn; its checker refuses more combinations.
- The combined month reads every list's calendar (two or three queries each) for every page view, and history for
  Garden presses; a household with years of history in many lists may notice it.
- A busy day's cell can hold three marks with counts that wrap at 320px; the list in words is the full version.
- Vehicles shows `last_done` only as the one latest date it keeps; earlier services are not in history, so they
  do not appear. A service marked done by changing its dates leaves no earlier mark.
- Garden presses before decision 0112 (with no named history entry) do not show.
- Bills shows only the date to check, never whether a bill was paid or a policy renewed.
- The combined legend says "Done" and "Skipped" in general words; each line says the list's own words.
- Module titles on lines are long on a phone ("Bills and insurance · Example electricity: bill check due today").
- Lists other than these (Documents, first aid checks, Home layout alarm tests, Things lent out) keep their due
  dates on Things to do but are not on the calendar until their module declares one line.

## How hard it is to undo
Easy. Remove the `calendar` sections from Home care's, Garden's, Vehicles' and Bills and insurance's `tables.toml`
(no migration was needed); in `core/modules.py` drop `_check_own_calendar`, its call and the one-calendar-per-date
check; in `core/calendars.py` drop `own`, `_presses`, the `per or "id"` fallback and the moved-reminder clause; in
`web/calendar_pages.py` drop `together_view`, the Show links and the own-calendar branches in `Words`, and give
`todo_calendar` its 0119 body back; restore `todo_calendar.html`. No stored data changed.

## We should revisit this if
- Households find the combined month too busy even with Show links, or ask for a week view.
- Someone reads a blank day or a due mark as "missed" or "not paid".
- A module wants an own calendar with a state (such as "partly done"), or several due dates per record.
- Documents, first aid or Home layout ask to be on the calendar: each is one `calendar` section.
