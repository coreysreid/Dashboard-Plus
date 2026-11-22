# 0110. Pet feeding log, with daily totals by the household's own day

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)
- **Builds on:** 0047 (Pets), 0055 (module confinement), 0066-0069 and 0101-0102 (helpers and Review), 0100 (sync stage 1 travel rules), 0107 (Things to do), 0109 (charts); Lane B's draft `workbench/drafts/pet_feeding/` (batch 20 item 89, now removed; its FLOW, NOTES, ACCEPTANCE and example rows are in git history)

## In plain words
A household can now write down each time food goes into a pet's bowl, a bowl
is refilled, or a treat is given. An amount is food **put out**, not food
eaten, and it is optional. On a phone, **Pets → Rex → Add food** opens a short
form with the time now filled in and, for you to check, the choices from the
last entry; Save comes back to Rex's page. Home shows one line per pet:
"Rex · 2 feedings recorded today · 240 g put out", or "No feeding entry recorded
today", never "Rex has not been fed". Each day's page adds up only entries that
were accepted, only in matching units ("120 g and 1 pouch put out"), and says
how many have no amount. Days follow the household's own time zone. A **Pet
feeding log** sheet prints every entry of the last 14 days (or chosen dates)
with each day's totals by unit, or says the range is too long and offers
shorter ones. A helper may suggest feedings for Review; one that looks like an
entry already recorded, or like another one waiting, says **Possible repeat
feeding entry** with **Accept as another feeding** and **Reject this copy**.

## What we chose
- **A new module, `modules/pet_feeding/`**, requiring Pets, from Lane B's draft.
  One table, Food given (`pet_feeding__servings`). The draft's migration is
  used unchanged (renamed `0001_initial.sql`) and a test checks it still
  matches `tables.toml`. Added only defaults that do not change the schema:
  When is "now" and What happened is Bowl. A pet with feedings cannot be
  deleted (`on_delete = "restrict"`); its entries must be dealt with first.
- **A generic `daily` declaration, not feeding code.** `[tables.<name>.daily]`
  names `when` (a required datetime), `per` (a required link), `amount` and
  `unit`, the words the pages use and an optional `repeat` rule. The module
  checker explains a wrong one. `core/daily.py` does the work for any table
  that declares it.
- **The household's own day.** The zone is the existing `household.timezone`
  setting (saved from the browser by setup and Settings); if it is missing or
  unknown, this computer's own clock and its daylight-saving rules. A time
  typed on the form has no offset and is the household's local time, kept as
  typed. A time sent with an offset (a helper, later a member phone) is an
  instant: it is stored exactly as sent and counted on the household day it
  falls in, around midnight and across clock changes. A late entry counts on
  the day it happened, not the day it was typed.
- **Only accepted, undeleted rows are added up**, one total per unit, never
  across units and never converting a scoop or pouch to grams. Rows with no
  amount are counted and said. An amount needs a unit and a unit needs an
  amount (checked on every save, including when a suggestion is accepted).
  Suggestions waiting on Review are shown apart ("1 suggestion is waiting on
  Review, not counted until accepted").
- **No inference from absence.** No Needs attention warning, target, streak or
  "missed meal" exists. An empty day says "No feeding entry recorded today".
- **Pages.** Home card (at most 8 pets named); the pet's page panel with Add
  food and up to three recent combinations as quick picks (each opens the
  visible, filled-in form with "Filled in from a recent entry. Check each answer
  before you save."); `/daily/<table>?subject=&day=` for one pet's day with Day
  before and Day after; `/daily/<table>/sheet` for the sheet. A module switched
  off has no pages (404), no Home card and no panel; its records are kept.
- **Paging.** The full list is the ordinary paged grid (50 at a time). A day
  page reads one day through the pet and time indexes. A sheet counts first:
  more than 92 days or 1,000 entries is refused with the exact count and up to
  eight 14-day ranges to choose instead; otherwise every entry is printed. No
  full-year sheet.
- **Possible repeats.** A suggestion for the same pet within 30 minutes with the
  same food, amount and unit as an accepted entry, or as another waiting
  suggestion, is marked on Review with what it matches and where it came from.
  Nothing is merged; the household keeps both or rejects one. A helper's source
  line and reason are never saved into a feeding.
- **Travel (decision 0100).** Every column travels, notes included: a feeding
  note ("ate half") is useful to the whole household, like a weigh-in note.
  The form says notes go wherever the entry goes and not to put vet or private
  details there. The sheet leaves notes off. The change log covers every
  create, change and delete, with one permanent ID per entry and a revision
  for each correction.
- **No chart.** Bars of daily amounts would draw an empty day as a zero bar and
  mixed units cannot share one scale, so the 0109 declaration is not used yet.
- **Examples:** Smith (Rex, two 120 g bowls yesterday) and Garcia (Luna, one
  pouch and one unmeasured refill yesterday); Taylor has no pet and no feeding
  module. `tools/load_example.py` reads times like `today-1T07:15`.

## Why we chose it
- Corey's old tracker had about 700 events a year with daily totals; they need
  a home that is fast to add to and honest about what a total means.
- A declaration lets a later module (medicine given, water drunk) reuse the
  same local-day arithmetic instead of copying it.
- Using the existing zone setting keeps one meaning of "today" for the
  household; keeping instants as sent means nothing is lost when a member
  phone in another zone arrives.

## What else we considered
- **A separate zone column on each entry**, as the draft's notes suggested.
  An offset in the stored value already keeps the instant; a named zone per
  entry adds a field to fill in for no gain on the main computer. Can be added
  with a migration if member phones need it.
- **Private notes** (`sensitive = true, travels = "never"`): safer, but a
  feeding note is household information, and private fields cannot be read
  by helpers or members who also feed the pet.
- **Silently merging duplicates:** rejected; two real feedings can be close.
- **A monthly overview of counts:** left for later; the day page and the
  sheet answer the draft's questions.

## What this costs us (the downsides)
- "Today" uses the zone from the last time Settings was saved in a browser; if
  the computer's clock zone differs, the form's "now" default (computer clock)
  and the day boundary can disagree. The Add food button fills in the time in
  the household's zone, which avoids this on the usual path.
- On Windows without the time zone database, a named zone is unknown and the
  computer's clock is used instead.
- An entry typed without an offset stays on its wall-clock day if the household
  later changes its zone; one with an offset moves with the new zone.
- Times show as "7:15 am" everywhere in this module, whatever the household's
  date order.
- The repeat check compares wall-clock times, so within an hour of a clock
  change it can miss or over-flag a repeat; it only ever warns.
- The member phone app, offline saves on a phone and the "as of" age of a
  member's copy are not built; those draft checks wait for sync stage 2.
- A household that switches the module off can then delete a pet that still
  has feedings, because the switched-off table is not checked.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. To remove the feature: delete `core/daily.py`, `web/daily_pages.py`,
the three `*daily*` templates, the `daily` checker in `modules.py`, the
amount-and-unit check in `records.py`, the Home card, the pet-page panel, the
Review note (one line in `review.py` and the template block) and the `from=last`
notice in `pages.py`. No core table or migration was added.

## We should revisit this if
- Member phones in other time zones start sending entries.
- Households want a monthly or yearly overview, or a chart that can show an
  empty day honestly.
- People ask for private feeding notes, or a vet asks for amounts eaten.
