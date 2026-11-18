# 0072. Reminders skip finished rows, and sheets print a linked contact's phone

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Two small things a module can now say in its files. First, a reminder can
leave out rows that are finished: a drill already given back is never "overdue".
Second, a printed sheet can show a phone number kept in People, so the Vehicles
sheet shows who to call if the car breaks down *and* their number, and the Home
care sheet shows who usually does a job and their number. Private details from
another module are never printed this way.

## What we chose
- **`where` on `expiring`.** In `tables.toml`, the due-date reminder may add
  equality filters on columns of the same table:
  `expiring = { date = "due_back", wording = "due", where = { status = "out" } }`.
  Only rows matching every filter are reminded about. A blank yes/no counts as
  "no", the way the form shows it (so `where = { done = false }` includes jobs
  never ticked); a blank choice matches nothing. The filters are checked when
  the module loads, with the same plain errors as the `where` of gaps and
  sheets ("'lost' is not one of the choices for 'status'", "'done' is a yes/no
  column, so write true or false").
- **Sheet columns through a link into another module.** In `sheets.toml`, a
  column like `roadside_contact.phone` may follow a link into a module listed
  under `requires` (links elsewhere are already refused). Because that module's
  files are read separately, the column is checked once every module has
  loaded, as cross-module gap questions already are: a misspelt column is a
  plain error that stops only this module. A column that is **private**
  (`sensitive = true`) in the other module is refused outright: "'info.detail'
  is private in the 'people' module, so this sheet can't print it."
- **Used straight away.** Vehicles prints the roadside contact's phone, Home
  care prints the phone of whoever usually does a job, and Things lent out
  (decision 0073) reminds about due-back dates only for loans still out.

## Why we chose it
- Without the filter, a returned loan or a finished garden job would stay
  "overdue" for ever, which teaches a household to ignore *Needs attention*.
  Two of Lane B's drafts (Things lent out, Garden) were waiting on exactly
  this.
- Equality filters already exist for gaps, sheets and supplies, so module
  authors learn nothing new and the checks are shared.
- A roadside or tradesperson number is the one detail you need when you reach
  for these sheets. Keeping it in People means it is changed once.
- Refusing another module's private columns keeps decisions 0055 and 0059
  true: a module can only print what is ordinary in the module that owns it,
  and nothing private leaves People through a link.

## What else we considered
- **`unless_set = "returned_on"`** (remind only while a date is blank). It
  reads well but is a second way to say the same thing, and the drafts that
  need it already have a status or yes/no column. Left out until a module
  needs it.
- **Comparisons such as "returned_on is after due_back".** More power than any
  module needs now, and harder to explain in an error.
- **Allowing private columns from another module on a sheet marked private.**
  Sheets have no "private" flag yet; refusing is simpler and safe. If a module
  needs it, add an explicit flag and the same "Show private details" step
  as the medical sheet.
- **Printing a "see the Emergency sheet" note instead of the number.** That is
  what Vehicles did; it sends people to a second page in a hurry.

## What this costs us (the downsides)
- A reminder filter is only as good as the household's data: a loan whose
  status was never changed to "returned" still shows as overdue.
- A sheet column into another module is checked later than the rest, so its
  error appears among cross-module problems rather than with the sheet's own.
- The column heading reads "Phone" with no hint whose phone it is; it sits
  beside the contact's name, which we judge clear enough.

## How hard it is to undo
Easy. Remove `where` from the rules that use it (Things lent out) and the
`link.phone` columns from the Vehicles and Home care sheets; the core code is
two small additions. No data or migration is involved.

## We should revisit this if
- A module needs "only while a date is blank" or a comparison (then add
  `unless_set`).
- A module wants a private detail from People on a sheet (then add a private
  sheet flag rather than loosening the refusal).
