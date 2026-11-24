# 0108. "Think it through": eight calm drills built on the Readiness questions, with practice runs whose own words stay on this computer

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0104 (Readiness questions and the recorded `[[scenario]]` shape), 0100 (permanent IDs, revisions and the travel rule), 0103 (Set up my home: rooms and connections), 0054 and 0077 (Home layout and its private access details), 0059 (private details only on Show), Lane B's draft `workbench/drafts/think_it_through/` (now removed; its DRILLS, SOURCES, STATE, ACCEPTANCE and NOTES are in git history), User 1's request in docs/BACKLOG.md

## In plain words
Readiness now has **Think it through**: eight short practice runs for situations a household
might meet, such as water leaking behind a bathroom wall, a bedroom candle fire at 9 pm, a
kitchen fire, someone breaking in at 2 am, the car stopping 150 km from home, the power off
for 72 hours, a regional warning not to drink tap water, and a cyclone forecast near your
suburb. Each walks through four or five calm questions, one at a time. Where your own records
can help, the step shows them ("Where is your water shut-off?" shows the shut-off you
recorded, with its full place); where they cannot, it says exactly what is missing ("You
haven't recorded where your water shut-off is.") with an **Add it now** link. You choose **I
have a plan**, **I need to check** or **Not relevant to my household**, and may write your own
words, which stay private on this computer. Stop at any point with **Save and continue
later**; when every step is done, **Save this practice** records the date you practised and the
date you choose to look again (12 months is suggested). Every drill first says to phone the
emergency service if anyone is in danger (000 in Australia, 911 in the United States, 999 in the
United Kingdom; elsewhere "Use your local emergency number"), says it does not replace official
advice, and lists its sources with the date each was checked. Nothing says your home is safe.

## What we chose
1. **The content is the module's, the engine is small and generic.** `prompts.toml` goes to
   format version `schema = 2` (version 1 files still load; drill settings in a version 1 file
   are refused with "Drills need schema = 2"). Version 2 adds:
   - `[[scenario]]`: `id`, `version` (raised when the steps change; each run keeps its own),
     `title`, `intro`, `fits`, `sources` (title, url, checked, optional `country` list) and
     `steps`, the ordered step IDs, plus an optional `review_every` (months, default 12).
   - `[[step]]`: a drill-only question with the same `answered_by` and exact `match` as a
     prompt, a required `missing` sentence, and optional `caution` (shown beside any record
     offered) and `supply` (a table whose days-of-cover working is shown).
   - `[[emergency]]`: one number per country, each with its own official source.
   - `runs` and `run_steps`: the module's two tables for practice runs, checked when the module
     loads (columns, choices, `suggestions = false`, and own words private and never travelling).
   A `[[prompt]]` may also carry `missing` and `caution`, so it can be a drill step.
   `core/prompts.py` reads it, `core/drills.py` works out fit, sources, records and runs, and
   `web/drills.py` with `drill*.html` shows it. The core still knows nothing about fire or water.
2. **Shared and drill-only steps.** Decision 0104 sketched drill-only questions as prompts with a
   flag; they are a separate `[[step]]` list instead, so no loop over questions (Home, Needs
   attention, the count of 49) can ever pick one up. A step that names an ordinary question
   (five do: smoke alarms, outside meeting place, food in a power cut, outage updates, storm
   warnings) is **shared**: choosing an answer there also saves that question's ordinary
   answer (plan = Yes, check = Not yet, not relevant = Not relevant) through 0104's own
   `questions.save`, so it counts on the Questions page, with the record when one was chosen,
   and never with the person's own words.
3. **The eight drills are Lane B's, written in the project's own words** (DRILLS.md), with the
   sources opened on 21 November 2026 (SOURCES.md). A few draft words were softened so no
   screen implies a verdict ("once the situation has settled" rather than "is safe").
4. **What fits comes only from Settings, as for questions,** plus `has_records`: the breakdown
   drill fits only a household with a vehicle recorded. The cyclone drill fits only where
   "Cyclone or severe storm" is ticked and the country is Australia or the United States; the
   building's-own-fire-plan step only for an apartment or townhouse (or a home type not given).
   A drill that does not fit is listed apart with the reason and can still be opened. Nothing
   is guessed from an address or a time zone.
5. **Sources by country.** A source with a `country` list is shown only where Settings name one
   of those countries, so UK motorway breakdown advice never reaches an Australian or US
   household, the Bureau of Meteorology shows in Australia and the National Weather Service in
   the US. A source whose link or date is broken, or that was checked more than 12 months ago
   (or after today), stays listed with **Source needs checking**; it is never dropped or swapped
   for other advice. No page or warning is fetched; links open only when chosen.
6. **Records are offered, never answers.** A step's record match is 0104's exact match, one link
   deep, and is shown with 0104's same wording rules: private details only as "You have a private
   record that may relate", access details never (they stay behind Show on their own record).
   Room connections and ways out carry a caution that they are possible paths to check, not
   checked routes; a vehicle kit is "last recorded", not present now; water is counted only when
   positive, in litres and marked as drinking water, and the days estimate is shown only when it
   can be worked out. "Add it now" opens the right add form with simple values filled in (a water
   shut-off), only while that list is switched on.
7. **Practice runs are their own records.** `readiness__drill_runs` keeps the drill, its version,
   started on, practised on, look again on and Continue later or Practised.
   `readiness__drill_steps` keeps each step's choice, the record chosen (permanent ID and revision
   fingerprint, as 0104) and the person's **own words** (`sensitive = true, travels = "never"`).
   Start carries on an unfinished run rather than making another; Continue later never sets a
   practised date; Save this practice needs every fitting step answered. A practised run is
   history: its steps cannot be changed and a new practice is a new run, so earlier runs stay.
   If a record chosen in a practice later changes, moves or goes, the practice says "A record you
   chose for this practice changed since. Look at this step again when you have time." without
   touching the answer. When the look-again date comes, the drill list says "It is time to look
   at this again." Not now saves nothing.
8. **Own words never leave this computer.** Because they are a private column that never travels,
   the existing rules keep them out of the export (listed as left out), the helper API (left out),
   the sync change log and snapshot (named as withheld only), sheets (none use these tables), Home
   and Needs attention (never shown), and every page until Show is pressed (0059). Helpers may
   read the runs but never suggest one, and a spreadsheet cannot be imported into them. History
   and backups on this computer keep them, as for every private detail (0059).
9. **Home changes are small.** The Readiness card on Home gains one line, **Think it through**,
   and the Questions page links to it. Drills never appear as Home cards or on Needs attention.
10. **Examples:** Smith (Australia, cyclone fits, a house) practised the pipe drill; Garcia (US,
    an apartment, no storm ticked) practised the power cut; Taylor (UK, a flat, storm ticked but
    no cyclone drill) practised the bedroom fire. None has own words.
11. **Tests:** `tests/test_module_readiness_drills.py` automates Lane B's twelve acceptance checks
    (check 11 by labels, order and wording in the page; the 320-pixel width in the browser check),
    plus own words absent from export, helpers, sync log and snapshot, sheets and Home; the exact
    missing sentences; a shared question counting on Questions; module off and on; and the three
    example households. The browser check walks the pipe drill: Continue later, a record offered
    and not chosen, Save this practice, own words behind Show, at 320 pixels.

## Why we chose it
- 0104 already did the hard, careful part (exact matches, fingerprints, private wording); a drill is
  an ordered view over the same machinery, so the same rules hold everywhere.
- The draft showed that one ordinary answer per question cannot hold a dated, multi-step practice,
  and that a narrative answer about who is home, keys or health must not travel like a note. A
  private column with `travels = "never"` is the one place every existing path (export, helpers,
  sync, Show) already treats correctly.
- A separate `[[step]]` list keeps the 49 questions and their counts exactly as they were.

## What else we considered
- **Own words in `readiness__answers.note`.** It travels, exports and reaches helpers; refused by the draft.
- **One practice per drill, overwritten.** Simpler, but loses the history the draft asks for.
- **A flag on `[[prompt]]` for drill-only questions (0104's sketch).** Every loop over questions
  would need to remember to skip them; a separate list cannot be missed.
- **Fetching live warnings or a national emergency-number list.** Nothing is sent from this
  program, and an out-of-date copy would be worse than "Use your local emergency number".
- **One page with every step.** Shorter to build, but the draft asks for a calm one-at-a-time run
  that can stop part-way.

## What this costs us (the downsides)
- Emergency numbers exist only for Australia, the United States and the United Kingdom; every
  other household sees "Use your local emergency number" until a sourced number is added.
- A source's "needs checking" mark is based on its date only; a link that breaks on the web is not
  noticed until someone opens it.
- The cyclone drill is limited to Australia and the US; New Zealand and others need their own
  sourced wording first.
- An empty unfinished run is kept if someone presses Start and leaves; it shows as "saved to
  continue later" and carries on next time.
- Own words cannot be cleared from the drill screen, only replaced (or edited on the Practice
  answers list); like every private detail they stay in this computer's history and backups.
- A shared step sets the ordinary answer each time it is answered in a drill, so a later drill
  answer replaces an earlier one given on the Questions page (history keeps both).
- The days-of-cover line shows Home's working; a household with no people count sees only the
  missing sentence.

## How hard it is to undo
Easy for the content: remove the drill sections from `prompts.toml` (runs stay as records), or
switch Readiness off. Medium for the engine: `core/drills.py`, `web/drills.py`, the `drill*.html`
pages and schema 2 in `core/prompts.py` would go together; migration 0002 of Readiness would
stay (released migrations are never edited) and its two tables would simply be unused.

## We should revisit this if
- Households want to practise a drill together on two computers and expect each other's own words.
- A country pack brings local emergency numbers, fire services or warning agencies.
- People find shared steps changing their Questions answers surprising.
- A purpose-built "checked way out" field is added (0104); its match must be reviewed before any
  drill offers it.
