# 0032. One checked path for every record change, with soft deletes and history

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Every record is saved, changed or deleted through one part of the program. It
checks each value, explains anything wrong in plain words, and writes down who
changed what and when. Deleted records are hidden, not destroyed, so they can be
brought back.

## What we chose
- `src/dashboard/core/records.py` (`Records`) is the only code that writes
  module records. Screens, the Agent API and module sources will all use it.
- Values are checked against the module's declaration: required fields, numbers
  and their limits, whole numbers, dates, yes/no, choices (by key or by their
  friendly label), links to records that exist and are not deleted, and files
  that stay inside the data folder. Every problem is reported at once, and
  nothing is saved if anything is wrong.
- Money is stored as whole cents.
- Each create, change, delete and restore adds a row to `core__audit` with the
  time, who or what did it (`person`, `agent:<name>`, `module:<name>`,
  `import:<name>`, `system`), and the before and after values of only the fields
  that changed.
- Deleting sets `deleted_at` rather than removing the row. Links follow the
  column's rule: `restrict` refuses and says which records still point at it,
  `cascade` deletes those too, `clear` empties the link. All of it happens in one
  transaction.
- A change by a person sets `edited_by_person`, which will stop helpers from
  changing that row (the Agent API in M2).
- Lists come a page at a time, sortable only by known columns.

## Why we chose it
- One path means the checks, the history and the helper rules cannot be skipped
  by accident.
- Soft deletes and history make mistakes recoverable, which matters more to a
  household than saving disk space.
- Plain messages per field let the screens show the problem next to the box
  that caused it.

## What else we considered
- Checking values with database constraints: they cannot explain themselves in
  plain words and need a migration every time a rule changes.
- Hard deletes with a separate recycle bin: two places to keep in step.

## What this costs us (the downsides)
- The history table grows with every change (small for a household, and it can
  be trimmed later if needed).
- Deleted rows still take space and must be left out of every list and count.
- Code that writes to the database directly would bypass the checks; the
  project rule is that nothing does.

## How hard it is to undo
Medium. Other parts will build on this service.

## We should revisit this if
- The history makes the data file noticeably large or slow.
- Households want permanent deletion (for privacy), which would need a purge.
