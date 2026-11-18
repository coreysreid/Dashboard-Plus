# 0063. Home care is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The household can now keep a short list of jobs around the home, such as
cleaning the gutters or servicing the hot water system: where each one is, who
usually does it, when it was last done and the date it wants to do it again.
*Needs attention* says "job due in 18 days" from that date. A second list,
*Work done*, keeps a dated note each time. A one-page "Home care" sheet prints
the jobs and dates without notes.

Nothing repeats by itself. When a job is done, the household types the next
"Do again by" date on the job; logging work done does not change it. The form
says so.

## What we chose
- A new module, `modules/home_care/`, built on Lane B's draft
  (`workbench/drafts/home_care/`, now removed; its notes and example rows are
  in git history). Two lists: home care jobs, and work done. The draft's
  working migration became one first migration because the draft was never
  released. Its only database change is two new, empty tables.
- **It reuses what the household already has.** Where a job is done is one of
  its Places (shared with Household stock, decision 0054), so a path such as
  Hall › Hall cupboard means the same everywhere. Who usually does it, and who
  did the work, are its People, so a tradesperson's number is kept and changed
  in one place. The module says so (`requires = ["people", "stock"]`).
- **No repeat engine and no invented dates.** The core has no way to work out
  a next date for a module's record (the generic events repeat does not reach
  module tables). So "Do again by" is a date the household types, from the
  manual, a tradesperson or its own plan, and a blank date raises no reminder.
  Its help text says nothing is worked out and logging work done does not
  change it.
- **Due, not expired.** The reminder reads "job due in 18 days" or "overdue",
  a month before the household's date, like Home layout and Vehicles.
- **No double entry with Home layout.** The draft's examples were all smoke
  alarm checks. Smoke alarms, carbon monoxide alarms, extinguishers and fire
  blankets already have their test dates in Home layout's *Alarms and safety
  equipment*, so Home care has no such kind, and its help text points there.
  The kinds are: gutters and downpipes; hot water system or water heater;
  heating or air conditioning; outside (roof, paths, fences or trees); other.
- **One question, asked gently.** For each job written down: "Where is {name}
  done? Choose one of your places." The household is never asked whether it
  has any jobs.
- **Nothing private is stored.** There is no field for alarm codes, where a key
  is hidden or how to get in; the notes' help text says not to write them
  down. So no private detail can reach a list, a sheet, a record's name or a
  question (decisions 0055, 0059). Notes are not printed.
- **Home page:** jobs are the main list (`home = "main"`), work done is a link
  (`home = "more"`, decision 0056).
- Changes from the draft, each small: places and people are links instead of
  free text; the smoke alarm kind is gone; "Next due" is now "Do again by";
  work done is named "Clean the gutters, done 21/06/26"; deleting a job
  deletes its history with it, and restoring brings it back; a place cannot be
  deleted while a job points at it (as in Stock, Medical, Home layout and
  Vehicles).

## Why we chose it
- Gutters, the hot water system and the heating are common, costly things to
  forget, and "who did it last time?" is exactly the kind of answer this
  dashboard exists to have ready.
- What the draft's notes listed as missing is either shipped (shared places,
  decision 0054) or handled honestly without new core code (the household
  types the next date).
- Keeping smoke alarms in one place avoids two test dates that drift apart.

## What else we considered
- **A "Mark done" button that logs the work and moves the date on.** It needs
  a core action that writes two records at once and a repeat rule chosen by
  the household. Left for later; the form explains the two steps meanwhile.
- **A "how often" field that works out the next date.** Refused for now:
  nothing would use it yet, and a figure shown without being used would
  mislead. Intervals depend on the equipment, the building and local rules.
- **Asking for a "Do again by" date on every job.** Refused: some jobs are
  one-off, and the question could not be answered "not needed" yet.
- **A private field for access instructions for a tradesperson.** Left out:
  it is easy to add later as `sensitive = true`, and keeping no such detail is
  the safest default.
- **Moving smoke alarms from Home layout into Home care.** Refused: Home
  layout already prints them on the Our home sheet with where they are.

## What this costs us (the downsides)
- Two steps after a job is done: log the work, then change the job's dates.
  A household may forget the second; the job then stays "overdue", which is at
  least visible.
- The sheet shows who usually does a job but not their number, because a sheet
  cannot print a detail from another module's record; it says numbers are kept
  in People.
- Home care needs both People and Household stock switched on.
- Two more lists in the menu, and one more module to maintain.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. Nothing in People, Household stock or Home layout was changed.

## We should revisit this if
- Households forget to type the next date after logging work (then build the
  "Mark done" action with a household-chosen repeat).
- Households ask to keep access instructions for tradespeople (add a private
  field).
- A sheet learns to print a linked record's detail across modules.
