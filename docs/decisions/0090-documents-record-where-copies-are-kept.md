# 0090. Documents record where copies are kept, never the copy

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** User 1 (product choice, 20 November 2026); Claude (technical shape)
- **Refines:** decision 0062 (Important documents); follows decision 0089 (not a vault)

## In plain words
Each important paper can now say where copies of it are also kept: "Blue USB
drive", "Family cloud folder", "Solicitor". You name each place once and tick
it on every paper that has a copy there. Dashboard Plus still never holds the
paper, a scan or its number; it only remembers where to look.

## What User 1 asked for (20 November 2026)
"Maybe it's best for the app to provide a location for where the medical docs
are? Backed up on a blue USB drive, and on a family cloud folder, instead of hard copies in
the app." He also said he does not want the app to be a vault.

## What we chose
- A small new table in the Documents module, **Places copies are kept**, with
  one required field: the name.
- A new field on each document, **Copies also kept at**, that links to any
  number of those places. It uses the core's existing many-to-many link type
  (`links`), so no new core feature was needed beyond showing it on printed
  sheets. The database change is migration `0002_copies_also_kept.sql`.
- The form offers the places as ticks; the document page shows them; the
  Document review dates sheet lists them; Export includes them.
- Help text: "Where copies of this paper are kept, such as a hard drive or a
  family cloud folder. Dashboard Plus never stores the document itself."
- No file upload, no scan, no document number, no web address or password
  field. A place is a name only.
- The place names in the examples are invented ("Blue USB drive", "Family cloud
  folder"); the household's own words go in on their own copy.

## Why we chose it
- It answers User 1's wish exactly: the app points at the backup, it is not the
  backup.
- One place named once and reused avoids typing "Blue USB drive" ten different ways.
- It reuses a core feature that already existed, so the change is small and
  tested the same way as the rest.

## What else we considered
- **A free-text "copies" note.** Already possible in Notes; it cannot be reused
  or listed, and invites typing numbers and passwords.
- **Attaching the file or a scan.** Rejected: that would make the app a vault
  (decisions 0062 and 0089).
- **Reusing the Places in Household stock.** Rejected: a hard drive or a
  solicitor is not a room or shelf, and mixing them would clutter Stock.

## What this costs us (the downsides)
- The list page of documents does not show the copies column; the core's list
  grid cannot show several linked records yet. They show on the document page,
  the sheet and Export.
- The Document review dates sheet now prints where copies are kept. A household
  that does not want that on paper can ignore the field.
- Nothing checks that a copy really exists or is up to date; the field is only
  a reminder of where to look.
- One more small table for households to fill in.

## How hard it is to undo
Easy. Remove the field and table from `tables.toml` and add a migration that
drops them; the records for papers themselves are untouched.

## We should revisit this if
- People keep wanting copies on the document list itself, which would mean a
  core change to the grid.
- Households ask for more about each place (such as how often it is backed up).
  That would be a new decision, not a quiet extra field.
