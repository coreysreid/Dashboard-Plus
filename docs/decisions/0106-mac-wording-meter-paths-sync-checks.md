# 0106. Mac preview wording, the meter's full place path, and extra sync stage 1 checks

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)
- **Builds on:** 0096 (Mac preview), 0099 (Utilities), 0100 (sync stage 1), 0103 (Set up my home), `workbench/reports/2026-11-21-mac-preview-readthrough.md`, `workbench/drafts/sync/STAGE1_ACCEPTANCE.md`

## In plain words
Three small tidy-ups. The Mac instructions now say only what is true (an online
helper can send things; a new preview may warn again; which ZIP to open). The
Utilities list shows where a meter is, such as "Water meter — Front yard ›
Meter box". And six more tests guard the offline sync foundation.

## What we chose
1. **Mac wording.** README's Mac section and the read-me inside the Mac app use
   the read-through's replacement words: Dashboard Plus does not send records
   to an online service by itself, but a connected helper may; each new unsigned
   build may need allowing again, and if the warning looks different the tester
   stops and reports it; a chip check (About This Mac); sign in, newest green
   run on `main`, outer ZIP then inner ZIP; "someone with access to this Mac
   account or its backups may be able to read" the records; Replace steps for an
   update; the two folders to delete are listed separately and only for a
   deliberate erase. Behaviour is unchanged.
2. **`with_place` on a link column.** A single link may name a link column of the
   linked table (`meter = { type = "link", to = "home_layout.meters", with_place = "place" }`).
   Wherever the link is shown (list, record page, sheet) or chosen, it reads
   "name — full place path", using the same path machinery as Our home. A blank
   place shows just the name. Only Utilities uses it today.
3. **Sync checks.** `sync.check` also names a many-to-many pair whose record is
   not there (found while writing the tests: it checked single links but not
   pairs). New tests in `tests/test_sync_extra_checks.py` cover Utilities'
   private fields and Pets microchip, held People details, corrupt IDs and links,
   confinement of the core ID step, and Set up my home's connections in the log.

## Why we chose it
- The read-through found the old words promised more than the preview can prove.
- `with_place` is a declaration, so no module code and no change to what Home
  layout or Our home show; a table-wide `record_name` on meters would have
  changed names everywhere and weakened Import's duplicate-name check.
- The tests are the cases the acceptance plan ranked highest.

## What else we considered
- **Utilities without Home layout** (a household with only internet): not done.
  `requires` is all-or-nothing in this module system: the database link, the
  sheet, gap questions and load order all assume the required module is on, and
  Settings refuses to switch Utilities on without it. An optional dependency
  would touch migrations and every cross-module check, which is not small or
  safe. Home layout can be switched on and left empty; it needs only Stock.
- `record_name` on meters: see above.

## What this costs us (the downsides)
- The Mac text is longer and still unproven on a real Mac.
- A household with only an internet service must keep Home layout on.
- `with_place` is not checked across modules at load time: a wrong column name
  quietly shows just the name. A test pins the shipped use.
- Retyping a People detail with the same words does not release a held value
  (the safe side); it must change.

## How hard it is to undo
Easy. Remove `with_place` from `modules/utilities/tables.toml` (the code can stay
unused), restore the old wording, and delete the added tests and check.

## We should revisit this if
- A real Mac test shows the steps are wrong or confusing.
- Households ask for Utilities without Home layout, or another table wants a
  place path beside a link.
