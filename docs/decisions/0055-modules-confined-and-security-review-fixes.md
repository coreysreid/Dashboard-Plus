# 0055. Modules are confined to their own tables, and the security review's other fixes

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by User 1), at User 1's request for a security and privacy review
- **Refines:** decision 0007 ("declarative modules are safe by construction")

## In plain words
An independent review checked the whole program for ways private details
could leak or data could be damaged. The browser protections held up. It found
one serious gap: a files-only module, such as one a household copies in from
someone else, could include database changes that do anything at all: read
medical details, erase the history, or copy the whole database to another
folder. Now a module's database changes are watched as they run, and anything
outside the module's own tables is refused; the module is simply left out and
nothing changes. A handful of smaller fixes came with it.

## What we chose
- **A guard on module database changes** (SQLite's authorizer). Allowed:
  creating, changing, filling and dropping the module's own tables and
  indexes, reading its own tables, and adding entries to the change history
  (stock's batches upgrade needs that). Refused: everything else, including
  other modules' and the core's tables, triggers and views (which would act
  later, unguarded), attaching other files, PRAGMA settings, committing or
  vacuuming part-way. The core's own changes are not guarded; they ship with
  the program.
- **Private columns stay out of names and questions.** A batch name
  (`record_name`), a gap's question and a supply's unit cannot use a column
  marked private, because they appear on lists, the home page and sheets.
- **The second backup's folder** must be a name the program made (12 letters
  and digits); anything else, such as `../` or a full path, is replaced.
- **Files readable by this account only** on Mac and Linux: data folder,
  database, backups and the running-state file with the session key. Drives
  that don't keep permissions (FAT USB sticks) are left as they are.
- **The privacy check** now finds a database by its contents whatever its
  name, `.partial` files, `data/`, `backups/` and `secrets/` folders at any
  depth, Windows paths seen from Linux and named removable drives, and checks
  big files instead of skipping them.
- **Smaller web fixes:** an unusual digit in an address no longer crashes a
  page; a wrong request type is refused with its proper code, not reported as
  a crash; pages are never cached or shown inside another site; no write is
  exempt from the page's own token; a failed second copy is logged without the
  home folder's path.

## Why we chose it
- The project promises that files-only modules are safe for anyone to write
  and share. Running their SQL unchecked broke that promise.
- Generating every module change from `tables.toml` alone would also be safe,
  but data changes (like turning each item into a batch) need hand-written SQL.
  The guard keeps both.

## What else we considered
- Only running SQL generated from `tables.toml`: no data migrations possible.
- Showing a warning instead of refusing: households can't judge SQL.

## What this costs us (the downsides)
- A module can no longer change another module's data in its migrations. A
  module that needs to (such as Home layout taking over Stock's places, if that
  is ever done) needs a core change written and reviewed here.
- Not yet done: the session cookie is shared by every local port on the same
  computer name; a different name per port would close that gap.

## How hard it is to undo
Easy in code, and it should not be undone.

## We should revisit this if
- A shipped module genuinely needs to change another module's data: add a
  narrow, reviewed core step rather than loosening the guard.
