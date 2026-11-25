# 0126. One timeline on a record's page: what happened, newest first

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0109 (dots chart of weights), 0110 (the household's own day, food put out), 0119 (calendars, change
  words, never "missed"), 0120 and 0121 (private doses: counts until Show), 0123 (Show is a POST, names after it),
  0124 (bars over time); Lane B's `workbench/drafts/charts/` (record summaries, not diagnoses)

## In plain words
User 1 wants to track pets' weights and medication visually and see changes over time. A pet's page and a
person's page now end with **What happened, newest first**: one list of everything recorded for them, under month
headings. For a pet: each weigh-in ("Weigh-in · Tue 24 Nov · 4.7 kg · up 0.3 kg since 2 Oct, from 4.4 kg to
4.7 kg"), each vet visit and its reason, each treatment given (flea drops, worming, medicine), and feedings as one
line a day ("3 feedings recorded on Tue 24 Nov · 240 g put out"). For a person: doses as one line a day, saying
only "3 doses recorded on Tue 24 Nov"; which medicine each was appears only after pressing **Show** on the
timeline's own page, and the amount and who gave it never appear here. Every kind has its own symbol beside its
words, **Earlier** goes back a page, and a pet with nothing yet says "Nothing recorded yet for Rex."

## What we chose
- **A generic `timeline` declaration** on a table in `tables.toml`, checked when the module loads, naming no module
  in the code (`core/modules.py`, `_check_timeline`):
  `when` (a required date or date-and-time column), `per` (a required link to the record whose timeline it is, or
  one link further inside the same module, such as `"treatment.pet"`: a treatment given belongs to the treatment's
  pet), `entry` (singular and plural), optional `words` (a short text with `{column}` names, such as
  `"{weight}"` or `"{reason}"`; only columns that are not private), `look` (one of four fixed looks), optional
  `summarise = "day"` (one line a day with how many) and optional `change` (a number column with its own unit:
  the change since the entry before, in 0119's words). The checker explains each mistake in plain words: a missing
  or wrong column, a private column in `words`, a brace without its pair, a look or summary it does not know, a
  change on a column with no unit or with a summary, and unknown settings.
- **Four fixed looks**, each a symbol beside the words, so a kind is never told apart by colour alone:
  ● recorded (blue), ✓ done (green), ◆ measured (amber), ■ visit (dashed edge, no fill). The colours reuse the
  calendars' light and dark pairs, print (`print-color-adjust`) and become plain edges in Windows high contrast.
  The symbol is hidden from screen readers; the kind's own words ("Weigh-in", "Vet visit") are always there.
- **The arithmetic** (`core/timeline.py`): for each switched-on table whose timeline points at the record, every
  accepted, undeleted entry (and, through a link, only while that linked record is not deleted), placed on the
  household's own day with `daily.local` (0110). Lines are sorted newest first; a table that summarises gives one
  line per day. The change is against the previous accepted, undeleted entry of the same kind, so a deleted or
  waiting weigh-in is skipped and the next one compares with the one before it. Nothing is stored, so an edit,
  delete or restore shows at once.
- **Pages** (`web/timeline_pages.py`, `_timeline.html`, `timeline.html`): the record's page shows the newest 8
  lines with **Earlier** and **Open the whole timeline**; `/timeline/<table>/<id>` shows 25 lines a page. **Earlier**
  is an ordinary link (`?before=2026-03-14`) and a day is never split across two pages; **Back to the newest**
  returns. Month headings ("November 2026") are real headings; each line is a list item with its date ("Tue 24
  Nov", or "Nov 24" where dates are written month first), a time for a timed entry, its words, the change and
  **Open** (or **See this day** for a summarised day of a table with a daily log). An empty timeline says
  "Nothing recorded yet for Rex."; nothing before a chosen day says "Nothing recorded for Rex before 01/01/26.".
  A caveat says a gap only means nothing was written down, never that anything was missed. No script; at 320px
  each line wraps beside its symbol; print hides the links and the Show button.
- **Private tables (0121, 0123).** The checker requires `summarise = "day"` and refuses `change` and any private
  column in `words`. Before Show a day says only how many and links only to its day page (itself private until
  Show); no dose's own page is linked. **Show** is a POST with the session check on `/timeline/<table>/<id>`
  (`?show=1` does nothing). After it, each dose under its day says its time and its words: Medicine doses declares
  `words = "{medication}"`, which a private table shows as the medication detail's own words and number ("...
  (Medication #3)"), on that page only, with **Hide details** back. The amount (a private column) and the giver are
  never named in `words`, so they never appear on a timeline, before or after Show.
- **Applied:** Pets' Weigh-ins (◆, the weight, the change since the weigh-in before), Vet visits (■, the reason),
  Treatments given (✓, which treatment, through `treatment.pet`); Pet feeding (●, one line a day with the day's
  totals in each unit, never added across units); Medicine doses (✓, one line a day, the medicine after Show).
  Vaccinations are recorded as vet visits; Pets' "Vaccinations due" is a due date, not something that happened, so
  it stays on Things to do. People's Important details (medical details) have no date, so they are not on the
  timeline; their changes stay in each detail's own history.
- **Switched off:** a module switched off has no lines on any timeline (its tables are not in the registry) and its
  records are kept; a record whose table has no timeline sources has no panel and its page answers 404, as does a
  private table's own record and a deleted record.
- **Tests** in `tests/test_timeline.py` (15) and a browser step at 320px.

## Why we chose it
- "What has happened with Rex lately?" is one question; today its answer is spread over a dots chart, a calendar,
  bars and three lists. One list in time order answers it in words, with the pictures still above it.
- A declaration means the next module (home care work, garden jobs, vehicle services) can put its entries on a
  record's timeline without new code, as with calendars and bars.
- One line a day for feedings keeps a year of twice-daily bowls to a readable page, and is the only safe shape for
  private doses: how many, never which, until a pressed Show.
- Reusing 0119's change words keeps one way of saying "up 0.3 kg" across the program, without a verdict.

## What else we considered
- **Each table's own history list on the page**: already there for some; it does not mix kinds or show order.
- **Reading the audit history for medical details' changes**: it would put private words' changes on a page and
  its dates are when someone typed, not when something happened. Left out.
- **Paging by a number (offset)**: an entry added or deleted between pages would shift or repeat lines; paging by
  day keeps each page stable and never splits a day.
- **A colour per module**: rejected for the same reasons as 0119; four fixed looks with symbols stay readable.
- **Showing a dose's amount after Show**: the amount is a private column with its own Show on the dose; a timeline
  of amounts can read as advice. Counts and names answer "how often and what".

## What this costs us (the downsides)
- One more declaration with seven settings to learn and keep checked.
- Each page reads every entry of the record from each table, then pages in memory: fine for years of daily
  feedings (a few thousand rows), slower for tens of thousands.
- Within one day, lines without a time are ordered by their list's name, not by when they happened.
- Long record pages: a pet's page now has weights, today's feeding, the calendar, the bars and the timeline.
- The change line compares only with the entry before in the same list, never with a reading in another unit or
  another list, and it says nothing about why or whether it matters.
- `per` may go through only one link, and only inside the same module.
- A person's timeline names them in its heading on its own page, as their record's page already does; the lines
  themselves name no one before Show.
- Symbols rely on the system font having ●, ✓, ◆ and ■; the words always stay.

## How hard it is to undo
Easy. Remove the `timeline` sections from the three `tables.toml` files (no migration was needed),
`core/timeline.py`, `web/timeline_pages.py`, `_timeline.html` and `timeline.html`, the timeline CSS in
`base.html`, the panel in `pages.py` and `form.html`, the blueprint lines in `app.py`, and `_check_timeline` with
its constants in `modules.py`.

## We should revisit this if
- People read a gap in the timeline as "missed" despite the words.
- People want to filter the timeline to one kind, or see several pets together.
- Home care, Garden or Vehicles ask for their work on a place's or vehicle's page: they only need a `timeline`
  declaration (the builder of 0125 is adding more calendar and bars declarations in parallel).
- A medicine's own page after Show is wanted: it could carry that medicine's timeline with the same rules.
