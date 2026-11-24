# 0119. Colour-coded month calendars, and trends on the dots chart

- **Status:** Accepted
- **Date:** 2026-11-24
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0107 (Things to do and Routines), 0109 (first charts), 0110 (pet feeding and the household's own day), 0111 (readings in their own unit), 0112 (one-press history); Lane B's `workbench/drafts/charts/CHARTS.md` and `NOTES.md`

## In plain words
User 1 asked for "colour coded calendar layouts or graphs etc to visualise
results and track changes", for example pets' weights and medication. A pet's
page now shows a **Feeding calendar**: the month as a grid, where a day with a
feeding shows ● and how many, with Previous month and Next month. **Things to
do** has a **Calendar** tab for Routines: ✓ Done and – Skipped on the day it
happened, and each routine's next date once, as ○ Due or ◇ Planned. Every mark
has its own symbol as well as a colour, a legend says what each means, and the
same days are listed in words underneath. A blank day only means nothing was
recorded; nothing is ever called missed. A pet's recorded weights can now be
shown for the last 3 months, the last year or all dates, say "Since the reading
before, on 25/09/26: up 1.2 kg, from 20.1 kg to 21.3 kg" and since the start of
the range, and draw a thin line between readings, on a scale that still starts
at zero.

## What we chose
- **A generic `calendar` declaration** on a table in `tables.toml`, checked when
  the module loads (no module is named in the code):
  `when` (a required date or date-and-time column), `per` (a required link: the
  pet, the routine), `show` (`"one"`: one record's month at a time, with a
  chooser; `"all"`: every record together), `title`, `entry` (singular and
  plural), and either `look` (one look for every record) or `state` with
  `looks` (a required choice column, each choice given a look). `due = true`
  also shows the linked record's one open due date, read from that table's own
  `watch.expiring` reminder with `wording = "due"` and its `where` (so a paused
  routine has none), and must be in the same module. The checker explains each
  mistake in plain words.
- **Five fixed looks, never chosen per module:** ✓ done (green), ● recorded
  (blue), – skipped (grey, striped, dotted edge), ○ due (amber, dashed edge) and
  ◇ planned (no fill, dashed edge). Modules may use done, recorded and skipped;
  due and planned come only from a due rule. Each colour has a dark-mode pair,
  prints (`print-color-adjust`), and in Windows high contrast the symbols and
  edges remain. So no state depends on colour alone.
- **The household's own day** (`core/calendars.py`): a date-and-time entry is
  placed with `daily.local` from decision 0110 (a typed time is the household's
  clock; a time with an offset is an instant moved into the household's zone),
  around midnight, at a month's edge and across clock changes. Today is the
  household's day for timed entries and the computer's date for dated ones, as
  Things to do reads it, so "Due today" means the same on both pages. Only
  accepted, undeleted records count; nothing is stored, so an edit, delete or
  restore shows at once.
- **Never shame, never fill in.** A day with no record is blank and the legend
  says "A blank day has no feeding entry recorded. It does not mean anything was
  missed." A routine's open date is marked once, on its own date, as "Due, not
  recorded as done yet" (today: "Due today"; later: "Planned"); the days since
  stay blank, as in 0107's "Due since". An empty month says "No feeding entry
  recorded for Rex in November 2026." or "Nothing recorded or planned".
- **Drawn as an HTML table on the server**, not SVG: a caption, seven column
  headings with each day's full name for screen readers, today marked with
  `aria-current="date"` and a thick outline, each day's words in hidden text,
  the marks themselves hidden from screen readers (their words are said
  instead), a legend, and an ordered list of every day with something on it
  ("Mon 23 Nov: 2 feedings recorded · 240 g put out · See this day"), each line
  linking to its record. A day number with marks jumps to its line. It fits a
  320px phone without scrolling sideways, uses no script, prints, and the
  month links stay on the server (`?month=2026-11`, up to 12 months ahead).
- **Where it shows.** `/calendar/<table>` for any calendar; a record's own page
  shows this month's calendar of what was recorded for it (a pet's feedings, a
  routine's times), with the day list folded away; the feeding day page links
  to its month; Things to do gets a **Calendar** tab (`/to-do/calendar`) for
  every calendar with `due = true`. Pet feeding declares `show = "one"`;
  Routines' Done or skipped declares `show = "all"`, `state = "outcome"` and
  `due = true`. A module switched off has no page (404), no tab and no panel;
  its records are kept.
- **Trends on the dots chart** (decision 0109's declaration gains four optional
  keys): `ranges` (some of `"3m"`, `"1y"`, `"all"`: links that choose the last
  3 months or year back to the same day of the month, or the month's last day);
  `change = true` (the change since the reading before and since the start of
  the range or the first reading, in words with the unit: "up", "down" or "no
  change", never a cause, never across units); `line` (`true` or
  `{ gap_days = N }`: a thin line under the dots, hidden from screen readers,
  broken where readings are more than N days apart, with the caption saying it
  does not show values between them); and `scale = "fitted"` (the value axis
  starts near the lowest reading and the chart says "Scale starts at 4.3 kg,
  not 0"; otherwise it starts at zero, as 0109 requires). Pets' Weigh-ins
  declares all three ranges, change words and a line broken after a year, and
  keeps the zero scale. Dates typed in still win over a preset.
- **Tests** in `tests/test_calendars_and_trends.py` (31) and a browser step at
  320px (the feeding month with today in words and a symbol, the keyboard
  reaching a day's words, the routines legend, and the weights page for the
  last year with the change in words).

## Why we chose it
- A month grid is the plainest way to see "what happened when" for things done
  daily or weekly; the list in words keeps it equal for people who do not use
  the picture.
- Fixed looks keep every calendar readable the same way and stop a module from
  making a colour-only state or a red "missed" day.
- Reusing `daily.local` and the reminder Things to do already reads means one
  meaning of "today" and "due" across the program.
- An HTML table reads well with a screen reader, wraps at phone width and prints
  without the drawing work an SVG grid would need.
- Ranges, change words and an optional line answer "is the weight changing?"
  without a health verdict, and the zero scale stops a small change from
  looking dramatic unless a module asks otherwise and says so.

## What else we considered
- **An SVG calendar** like 0109's charts: harder to make equal to text and to
  fit 320px; a table gives rows, columns and headings for free.
- **Colour by module or user choice**: rejected; seven colours stop being
  distinguishable, and a choice could make a state colour-only.
- **Marking each missed day of a repeat**: rejected by 0107 and 0110; it would
  shame and guess.
- **A heat map of amounts per day** for feeding: mixed units cannot share one
  scale (0110), so a count with the totals in words is shown instead.
- **A trend line or average**: not now; DESIGN.md 10.3 asks for about 20 points
  and guardrails before anything is called a trend.

## What this costs us (the downsides)
- One more declaration and four more chart keys to learn and keep checked.
- A calendar reads one month at a time with one query per calendar (and one for
  due dates); a month with many thousands of entries would be slow.
- The marks are small at 320px: a day with three kinds of mark wraps inside its
  cell, and the count beside a symbol is in a small font. The list in words is
  the full version.
- Symbols rely on the system font having ✓, ●, ○ and ◇; very old systems may
  draw boxes, though the words stay.
- Things to do's Calendar tab shows only calendars with a due rule; Home care's
  Work done or Garden's jobs have no calendar until they declare one.
- The due rule shows only the one open date the record keeps, so a calendar
  cannot show a past date that was moved without a Done or skipped record.
- The line, even broken after long gaps, can still suggest a steady change
  between readings; the caption says it does not.
- `ranges` counts back in calendar months on the computer's date, not the
  household's zone (as Things to do does).

## How hard it is to undo
Easy. Remove the `calendar` lines from the three `tables.toml` files (no
migration was needed), `core/calendars.py`, `web/calendar_pages.py`, the three
calendar templates and their CSS in `base.html`, the Calendar tab
(`visible_tabs` and the TABS row in `web/checklist.py`), the record-page panel in
`pages.py` and `form.html`, the link on the day page, and the calendar checker
in `modules.py`. For trends, drop `ranges`, `change` and `line` from Pets' chart
line; the chart goes back to 0109's dots.

## We should revisit this if
- A medication module (being built in parallel) needs a state the fixed looks do
  not cover, such as "given late" or "refused". To plug in, it declares on its
  doses table `calendar = { when = "<given at>", per = "<medicine>", show =
  "one" or "all", title, entry, state = "<outcome choice>", looks = { given =
  "done", skipped = "skipped", ... } }`, and `due = true` if the medicine table
  has a `watch.expiring` reminder with `wording = "due"` in the same module.
  Private doses stay out: `state` may not be a private column, and the calendar
  shows only the subject's display name and the state's label.
- People ask for a week view, a year overview or several pets on one grid.
- A household reads a blank day as "missed" despite the legend.
- Someone asks for a fitted scale on pet weights; that is one declaration word.
