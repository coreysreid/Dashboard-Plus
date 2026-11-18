# 0076. Vegetable garden is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
A household can now keep a simple garden record: its beds, pots and
windowsill spots (each at one of its own Places), what it grows, each
planting, what it picked, and garden jobs with a due date. *Needs attention*
says "job due in 7 days" for a job, and stops as soon as the job is ticked as
done. A one-page "Garden plan" sheet prints the beds, the plantings and the
jobs still to do. There is no growing advice anywhere in it.

## What we chose
- A new module, `modules/garden/`, built on Lane B's draft
  (`workbench/drafts/garden/`, now removed; its notes and example rows are in
  git history). Five lists: beds, crops, plantings, harvests and jobs. The
  draft had never been released, so its two migrations became one clean first
  migration (it includes the planting name the draft added later).
- **Beds are at your Places.** The draft's free-text "location" became a link
  to a Household stock Place, so "Backyard" means the same here as in Stock and
  Home layout, as Home care did (decision 0063). A Place with a bed cannot be
  deleted. The module says so (`requires = ["stock"]`). There was no free-text
  person in the draft, so People is not needed.
- **A finished job is never a reminder.** The reminder uses the `where` filter
  from decision 0072: `where = { done = false }`, wording "due", starting two
  weeks before the date the household typed. A job with no date is never a
  reminder, and a blank "Done?" counts as not done. Ticking "Done?" again
  later (a mistake) brings the reminder back.
- **One question, asked gently.** "Where is {name}? Choose one of your places."
  for a bed with no place. A household with no beds is asked nothing.
- **Harvests are named** "Back yard tomatoes 2026, picked 08/11/26", so a
  harvest says which planting it belongs to anywhere it is listed.
- **Nothing private, no advice.** No column is private. No sowing times,
  yields, watering or feeding advice is stored or suggested; every date and
  amount is the household's own. A test checks the module files for advice
  wording.
- **The plan sheet** prints beds (name and place), plantings and jobs not yet
  done. Notes are not printed, as in the other modules.
- **Home page:** garden jobs are the main list (`home = "main"`, decision
  0056); the other four lists are links.
- **Example households:** the Smiths (a raised bed in the Backyard, with one
  open job due in a week and one finished job), the Garcias (basil in a pot on
  a new "Balcony" place) and Sam Taylor (parsley on a new "Windowsill" place
  inside Kitchen). All three needed only invented rows.
- **The teaching example stays.** `examples/garden/` is still the small,
  copyable "how to write a module" example (decision 0060). It keeps its
  free-text "location" and no links, because a first-time module author should
  not need Household stock to follow it. It is not the installed module, and
  its own test (`tests/test_example_garden.py`) still passes.

## Why we chose it
- A garden is a common home record, and the one thing blocking it (a reminder
  that would stay on after a job was done) is fixed in the core (decision 0072).
- Linking Places keeps one copy of each place name and stops a bed being
  recorded at a place that does not exist.
- Leaving advice out keeps the module a record, not a source of claims that
  could be wrong for a household's climate.

## What else we considered
- **Keeping "location" as free text.** Simpler, but "Backyard" in one place and
  "back yard" in another would never match, and Home layout and Stock already
  share Places.
- **A person on each job** (who does it). Not in the draft; People could be
  linked later as a new column.
- **Changing the example in `examples/garden/` to match.** It would make the
  teaching example harder to follow; see above.
- **Repeating jobs** (water every week). Refused: it would be advice and a
  date the household did not choose.

## What this costs us (the downsides)
- The module needs Household stock switched on, and a household must make or
  choose a Place for each bed before the question stops.
- Two copies of the garden idea exist in the repository (this module and the
  teaching example), and a change to one is not copied to the other.
- A job ticked as done stays in its list as history; nothing archives it.
- The form cannot yet check that a harvest is not dated before its planting.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. Nothing in Household stock was changed.

## We should revisit this if
- Households want a person on each job, or jobs that come back by themselves.
- Households find the two-week reminder too early or too late.
- Anyone reads a record in this module as advice.
