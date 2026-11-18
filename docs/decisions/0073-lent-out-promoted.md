# 0073. Things lent out is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The household can now write down a tool or other thing when it lends it: who
borrowed it, when, and the date they agreed it would come back. *Needs
attention* says "return due in 4 days" or "return overdue since …" from a week
before that date, and only while it is still out. When it comes back, the
household chooses "Yes, returned" and types the date; the reminder goes, and
the loan stays as history. A one-page "Things still lent out" sheet prints the
open loans with each borrower's phone number from People.

## What we chose
- A new module, `modules/lent_out/`, built on Lane B's draft
  (`workbench/drafts/lent_out/`, now removed; its notes, checks and example
  rows are in git history). One list: things lent out. The draft's working
  migration became one first migration because the draft was never released.
  Its only database change is one new, empty table.
- **It reuses what the household already has.** The borrower is one of its
  People, so their number is kept and changed in one place, and a borrower
  cannot be deleted while a loan points at them. The thing lent may be linked
  to a Household stock item, only to recognise it: lending it never changes
  the Stock count, and deleting the item keeps the loan's own name. The module
  says so (`requires = ["people", "stock"]`).
- **A returned loan is never overdue.** The reminder uses the new `where`
  filter (decision 0072): `where = { status = "out" }`. It starts a week before
  the date, because loans are short; the default month would flag a two-week
  loan from the day it was lent.
- **Returning is two fields on the same form.** "Is it back?" reads "No, still
  out" or "Yes, returned". "Returned on" appears once "Yes, returned" is
  chosen, and is then required, so a return always has a date. Setting it back
  to "No, still out" reopens a mistaken return, and the reminder comes back.
- **One question, asked gently.** "How would you reach {borrower} about
  {name}? Add a phone number if you have one." It is asked only while a loan
  is out, once per borrower, and it opens their People record.
- **Records are named "Cordless drill, lent to Dave Wilson"**, so *Needs
  attention* says what and who in one line.
- **Nothing private is stored.** No column is private; the borrower's name and
  phone are ordinary People details. Notes' help text says not to write
  private details, and notes are not printed (decisions 0055, 0059).
- **Home page:** the loans list is the main list (`home = "main"`, decision
  0056).
- **Example households:** the Smiths lent Dave Wilson a drill (due in 4 days;
  Dave has no number, so the question shows) and had a trowel returned
  (history, no reminder); the Garcias lent Luis a folding trolley; Sam Taylor's
  bike pump is two days overdue with Chris, whose number is still to add.

## Why we chose it
- "Who has our ladder?" is a common, small household question, and a reminder
  that disappears when the thing comes back is exactly what the draft asked
  for. The one thing blocking it, a reminder that would stay overdue after a
  return, is fixed in the core (decision 0072).
- Linking People and Stock keeps one copy of each name and number.

## What else we considered
- **A one-step "Mark returned" button** that sets the date and status at once.
  It needs a core action for a record (no module can declare one yet). Left
  for later; the help text says which two fields to change.
- **Only a "Returned on" date, with no "Is it back?" choice.** Simpler data,
  but the core's reminder filter matches values, not blanks, and a choice
  reads more clearly on the list and sheet. Kept the draft's choice.
- **A link to where the thing is usually kept (`stock.places`).** Left out: a
  linked Stock item already has its place, and an untracked thing rarely needs
  one. Easy to add as a new column if households ask.
- **Changing the Stock count when something is lent.** Refused, as the draft
  advised: a quantity rule for loans would surprise people, and a household
  that wants it can log a Stock out.

## What this costs us (the downsides)
- The form cannot yet check that "Returned on" is not before "Lent on".
- A household that types "Returned on" but leaves "No, still out" keeps the
  reminder; the help text tells them to change both.
- One more list on the home page and one more module to maintain; it needs
  People and Household stock switched on.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. Nothing in People or Household stock was changed.

## We should revisit this if
- Households forget to change "Is it back?" (then build the "Mark returned"
  action).
- Households ask where a returned thing should go back to (add a place link).
- People want to lend to someone without adding them to People first.
