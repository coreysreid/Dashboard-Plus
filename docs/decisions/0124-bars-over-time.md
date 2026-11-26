# 0124. Bars over time: how often and how much, per day, week or month

- **Status:** Accepted (before Show the dose bars name nobody, as the Dose calendar: amended by 0134)
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0109 (charts drawn on the server), 0110 (the household's own day, food put out), 0111 (readings in
  their own unit, nothing converted), 0119 (calendars, ranges as links, never "missed"), 0120 and 0121 (private
  history: counts until a pressed Show); Lane B's `workbench/drafts/charts/` (CHARTS.md, FIRST_TWO.md, NOTES.md)

## In plain words
User 1 wants graphs to see results and track changes. Besides the dots for a pet's weight, a page can now show
**bars over time**: one bar per day, week or month. A pet's page shows **Food put out per day**, in grams (or
pouches, one unit at a time), with **By day**, **By week**, **By month**, **Earlier** and **Later**. A routine's page
shows **Times done per month**. A person's page shows **Doses recorded per week**: how many doses, every medicine
together, never which one; **Show** (a pressed button) gives each medicine its own bars on that page only. Every bar
has its value in words beside it, the same values are in a table under it, and a day, week or month with nothing
written down says "nothing recorded", never "missed". The bar for this week or month is striped and says "so far".

## What we chose
- **A generic `bars` declaration**, a list on a table in `tables.toml`, checked when the module loads, naming no
  module in the code: `key`, `title`, `when` (a required date or date-and-time), `per` (a required link: one
  subject per chart), `measure` (`"count"`: how many accepted entries; `"sum"`: one number column added up),
  `amount`, `unit` (a choice or text column holding each entry's unit, or none when the number column has its own
  fixed unit), `verb` ("put out"), optional `where` (choices an entry must have, such as `outcome = "done"`),
  optional `group` (another required link whose records each get their own bars), `by` (some of day, week and
  month, the first shown first), `entry` (singular and plural), `subject` and an optional `caveat`. The checker
  explains each mistake in plain words; a sum without a unit, a private or money column, and an unknown setting
  are refused.
- **The arithmetic** (`core/bars.py`): 14 days, 12 weeks (starting on the household's first weekday, as Things to
  do does) or 12 months, ending with the one that holds the chosen day (today when none, never later). Only
  accepted, undeleted records count; a timed entry is placed on the household's own day with `daily.local` from
  0110 (a typed time is the household's clock; a time with an offset is an instant moved into its zone). Nothing
  is stored, so an edit, delete or restore shows at once.
- **One unit at a time (0111).** A sum adds only amounts in one unit: the latest entry's unit, or another chosen
  with **In g** / **In pouch** links. Amounts in other units are said ("also 1 pouch, not in this chart"), never
  converted or added in. An entry with no amount is counted and said ("1 feeding has no amount, so it is counted
  but not added"), never read as zero. A period with entries but nothing in this unit says "none in g".
- **Drawing** (`web/charts.py`, `period_chart`): an SVG drawn on the server, as 0109's: a `<title>` and `<desc>`
  named by `aria-labelledby`/`aria-describedby`; one row per period, oldest at the top, its short name on the left
  ("Tue 17 Nov", "From 16 Nov", "Nov 2026"), the bar from zero and its value printed beside it; each row a link with
  the full period and value in words that goes to its table row. A period with nothing to draw has no bar, a dashed
  empty box and its words. The period still going on is striped (a pattern, not only a colour) and its words say
  "so far". A count's scale is whole numbers. No script, no animation; colours come from the page's light and dark
  pairs, with print and Windows high-contrast rules. Horizontal rows keep every name and value readable at 320px.
- **The equal table** lists every period with its value in words ("240 g put out", "3 doses recorded", "Nothing
  recorded") and what else is known (how many entries, how many without an amount, other units), with **See this
  day** (a day page, for a table with a `daily` log) or **See these days** / **See these weeks**. On a phone each
  row becomes a card. On a record's own page the table is folded under "…, as a table".
- **Where it shows.** `/bars/<table>/<key>?subject=&by=&end=&unit=`, with a chooser of subjects, and each subject's
  own page by the first period in `by`. Periods, earlier and later ranges and units are ordinary server links. A
  module switched off has no page (404) and no panel; its records are kept.
- **Applied:** Pet feeding's Food given, `measure = "sum"` of the amount in its unit, by day, week or month,
  "Food put out, not necessarily eaten."; Routines' Done or skipped, `measure = "count"` with
  `where = { outcome = "done" }`, by month or week (a skipped time never counts as done); Medicine doses,
  `measure = "count"` with `group = "medication"`, by week, day or month.
- **Private tables (0121), decided: offered, but counts only.** The checker allows a private table only
  `measure = "count"` with no `where`, so the bars cannot carry an amount or tell one kind of entry from another.
  Before Show the page and the person's panel show every medicine together, the person's own name (it is their
  page, as on the Dose calendar) and no medicine, amount, giver, time or record link. **Show** is a POST with the
  session check, never an address (`?show=1` does nothing); it adds **Each medicine on its own**: one chart and
  table per medicine, named by its private words ("… (Medication #3)"). Amounts are never added, before or after
  Show. A person with no medication detail and no doses gets no dose bars, as for the dose panel.
- **Not applied to the vehicle running log.** Distance per month would be the difference between odometer
  readings, which 0111 rules out ("nothing works out a distance travelled"): readings are observations that can be
  corrected, rolled over or in another unit. The dots chart stays the right picture there.
- **Tests** in `tests/test_bar_charts.py` (21) and a browser step at 320px.

## Why we chose it
- "How often" and "how much" per week or month are the questions a household asks of feeding, routines and doses;
  bars answer them at a glance where a calendar shows only one month of marks.
- Adding in one unit at a time, and saying the rest, keeps every total true without inventing conversions (a scoop
  is not a number of grams).
- Counting only, with names after a pressed Show, gives a carer the picture of "about the same each week" without
  putting a medicine's name or amount on a screen someone else can see.
- A declaration lets the next module (garden jobs, home care work) get bars without new code.

## What else we considered
- **Vertical columns:** the usual look for time, but at 320px fourteen columns leave no room for a period's name or
  its value; rows keep both readable.
- **Adding all units together, or converting:** refused (0110, 0111).
- **Not offering dose bars at all:** safe, but User 1 asked for medication over time; counts with names after Show
  match the Dose calendar's rule.
- **Summing dose amounts per medicine after Show:** left out; amounts are optional, private, and a sum of doses can
  read as advice. Counts answer "how often".
- **An average or target line:** not now; DESIGN.md 10.3 asks for guardrails before anything is called a trend.

## What this costs us (the downsides)
- One more declaration with fourteen settings to learn and keep checked.
- The default unit is the latest entry's, so a household that mostly uses grams sees pouches after one pouch entry
  until it presses **In g**.
- Each chart reads its whole range in one query, and each medicine after Show reads it again; fine for years of
  daily entries, slower for many thousands.
- Long pages: a pet's page now has the weights, today's feeding, the calendar and the bars.
- A period's short name is shortened ("From 16 Nov"); the full words are in the link and the table.
- Week and month ranges count back from the household's day for timed entries and the computer's date for dated
  ones, as the calendars do.
- The striped "so far" bar relies on SVG patterns; a very old browser may draw it plain, though its words stay.

## How hard it is to undo
Easy. Remove the `[[tables.*.bars]]` sections from the three `tables.toml` files (no migration was needed),
`core/bars.py`, `web/bar_pages.py`, `_bars.html` and `bars.html`, `period_chart` in `charts.py`, the bars CSS in
`base.html`, the record-page panel in `pages.py` and `form.html`, the blueprint line in `app.py` and the checker in
`modules.py`.

## We should revisit this if
- A household reads an empty or striped bar as "missed" or "low" despite the words.
- People want two units side by side, a year view, or several pets on one chart.
- The latest-unit default confuses people more than it helps; "the unit with the most entries" is one line.
- Garden or Home care ask for "jobs done per month": they only need a `bars` declaration.
