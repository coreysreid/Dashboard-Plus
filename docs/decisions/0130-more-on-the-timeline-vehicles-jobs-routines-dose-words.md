# 0130. More on the timeline: vehicles, home care jobs, routines, and plainer dose words

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0126 (the timeline), 0111 (odometer readings and estimates: no mileage logic, quotes private),
  0119 (change words, never "missed"), 0121 and 0123 (private doses, Show is a POST)

## In plain words
Four more things now appear under **What happened, newest first**:
- A **vehicle's page** lists each odometer reading ("Odometer reading · Fri 20 Nov · 9:00 am · 49,740 km · up 1,240
  km since 2 Oct, from 48,500 km to 49,740 km") and each service estimate ("Service estimate · Wed 18 Nov · Family
  car: Routine service · Dealer"). The change is only the difference between two readings someone wrote down, and
  only when both are in the same unit. A reading in miles after one in kilometres says no change at all; nothing is
  converted. No distance a month, no "due", no average. An estimate's amount, what it includes and its notes are
  private and never appear.
- A **Home care job's page** lists each time the job was done, with who did it when that is written.
- A **routine's page** lists each time it was done or skipped. A skip is the household's choice and is never called missed.
- After pressing **Show** on a person's timeline, a dose now reads "8:00 am · Ibuprofen 200 mg" instead of
  "Ibuprofen 200 mg (Medication #3)". Only if two of that person's medicines have the same words does it add
  "(1 of 2 with the same words)", by the order they were added. Before Show nothing changed: only how many doses.

## What we chose
- **Declarations only** in three `tables.toml` files (Vehicle running log, Home care, Routines), each added as its
  own section at the end of the file.
- **Two small generic changes**, both checked when modules load, naming no module in the code:
  1. `change_unit = "<choice column>"` beside `change`: for a number whose unit is chosen on each entry (a reading
     is in km or mi). The change is said only between an entry and the one right before it when both have the same
     unit, and the unit's own label is used. The checker needs `change_unit` to name a required, non-private choice
     column and to go with `change`; a `change` with neither its own unit nor `change_unit` is still refused.
  2. `per = "service.vehicle"` may now go through a link into another module this one requires (before, only the
     same module). Estimates link to a service, which links to a vehicle. The module's own link is checked as
     before; the column on the other module's table is checked once both are loaded (`_cross_module_timeline_problems`),
     with a plain sentence if it is missing or not a required link.
- **Words that name nobody say nothing.** If every `{column}` in `words` is empty, the line has no words, so
  "by {done_by}" would never show a lone "by". A number named by `change` shows with thousands separators ("49,740"),
  like its change.
- **The dose wording** (`_private_link` in `web/timeline_pages.py`) uses the linked detail's own words. It looks at
  that person's other live records of the same kind (the link's `where` and `same` rules) and adds "(n of m with the
  same words)" only when words match ignoring capitals and spacing. A detail with no words reads "Medication with no
  words written". The ids "#3" are gone from the timeline; other pages are untouched.

## Not done, and why
- **Services done** (Vehicles' services have only a "last done" date, not a history) and **Garden jobs** (only a done
  yes/no, no date): there is no dated record to list. The parallel decision 0129 adds done history for those; their
  timelines then need only a declaration each.
- **A mileage per month** or any "due at distance": 0111 forbids it; the change line is only the difference between
  two readings.

## Why we chose it
- Each answer is "what happened with this thing lately", in one list in time order, with the same words as the pet's.
- Refusing to compare across units keeps 0111's promise that Dashboard never converts miles and kilometres.
- Plain medicine words are what the household wrote; an id means nothing to them.

## What else we considered
- **Comparing with the last reading in the same unit even if units switched in between.** Rejected: the line would
  skip over a reading and read as a claim about distance driven.
- **Showing an estimate's amount on the vehicle's timeline** after Show: the amount is private and only on this
  computer (0111); a timeline of quotes can read as advice. Left out.
- **A new `through` setting per module.** One rule ("one link further") covers it.

## What this costs us (the downsides)
- One more setting (`change_unit`) to learn, and `per` may now cross a module link, so a module that changes its
  columns could break another's timeline; the load-time check says so in plain words.
- "(1 of 2 with the same words)" depends on the order records were added; deleting one renumbers the other.
- A change after a switch of unit says nothing until two readings in a row share a unit.

## How hard it is to undo
Easy. Remove the three `timeline` sections added to `modules/vehicle_running`, `modules/home_care` and
`modules/routines`, `change_unit` from `_check_timeline` and `change_since`, the cross-module `per` branch and
`_cross_module_timeline_problems`, and restore the "#id" in `_private_link`.

## We should revisit this if
- Households want the service done list and garden done dates on their timelines (after 0129).
- Two medicines with the same words turn up often; then the detail page could carry a short label.
