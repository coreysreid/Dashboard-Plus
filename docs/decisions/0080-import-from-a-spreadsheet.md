# 0080. Import from a spreadsheet: rows wait on Review, like helpers' suggestions

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** decision 0068 (the waiting place now also holds imported rows); answers Lane B's
  `workbench/drafts/csv_import/` draft in part

## In plain words
You can bring rows from a spreadsheet into any list: Settings, then "Import from a spreadsheet". Choose the list,
choose the CSV file, check which column goes in which field, and Dashboard tells you how many rows are ready and
what is wrong with the rest, row by row ("Row 5: Use by must be a date like 20/05/27"). Nothing is saved yet.
"Send to Review" puts the ready rows on the Review page, where you accept them one by one or all at once. Only then
are they added, and their history says "Import 'pantry.csv'". The file itself is never saved.

## What we chose
- **Where it starts.** Settings, "6. Import from a spreadsheet" (`/settings/import`), with the list chosen on the
  page; `/settings/import?table=stock__items` opens with a list already chosen. One page serves every list, the same
  way Helpers does, and list pages stay as they are. Review links to it too.
- **Staged, never written directly.** Ready rows go into the same waiting place as helpers' suggestions
  (`core__helper_batches` and `core__proposals`, decision 0068) as one batch. Core migration 0004 lets a batch come
  from a helper (`kind` "helper", `helper_id` set) or from a person's import (`kind` "import", `helper_id` empty,
  `source_name` the file's name), checked by the database. Each waiting row keeps its spreadsheet row number
  (`source_row`). SQLite cannot loosen a column in place, so the two tables are rebuilt and refilled inside the
  migration; ids and every waiting suggestion are kept.
- **Helpers still see only their own batches.** Every helper query already filters on `helper_id`, which an import
  batch never has; tests check a helper cannot list, read or count one. Helper rules (daily limit, hidden links,
  request keys) apply only to helper batches.
- **Accept.** Accept and Accept all work as before. An imported record is created through the normal path, credited
  to `import:<file name>` (shown as "Import 'pantry.csv'"; the actor pattern now allows a dot) and marked
  `edited_by_person`, so a helper can never change it.
- **The same checks.** The dry run converts each cell, then runs `Records.check_create` (the full create path, rolled
  back) over every row, in order, exactly as a helper's suggestion is checked. One difference: a new item may start
  its first batch from an amount, use-by date and place, as the add form allows (`starting_amounts=True`); helpers
  still may not. Everything is checked again, for real, on Accept.
- **The file.** UTF-8 with or without a byte order mark, comma or semicolon (whichever the heading row uses more),
  quoted commas and line breaks, CRLF or LF. Up to 1 MB and 2,000 rows; the page says so before upload. Any other
  encoding is refused with how to save as "CSV UTF-8", never guessed or altered. Blank rows are skipped. Row numbers
  are the spreadsheet's own (the heading is row 1).
- **Never kept.** The upload is read in memory (the import pages never spill to a temporary file, and refuse a
  request over 3 MB before reading it) and is not written anywhere. Between steps its text travels inside the page
  as a hidden field, and each step reads and checks it again from the start. Before sending, the page's
  fingerprint of the file and matches must equal what was checked, and the count of ready rows must be the same;
  otherwise the person sees the new check first.
- **Matching columns.** Each heading is matched to a field by its label or key, ignoring case, spaces, underscores,
  dashes and question marks ("amount_on_hand" finds "Amount on hand"); a field is matched once. The person can change any
  match or choose "Skip this column". A field matched twice, or a needed field not matched, is explained before
  any row is checked.
- **Values.** Dates the household's way (core/dates.py) or as 2027-05-20. Numbers with a full stop for decimals; a
  comma is allowed only as a thousands separator (`1,000`), so `1,5` is a problem, not 15. A leading currency sign
  is dropped from money. Yes/no and choices are read as on the forms. Text is kept exactly, even when it starts with
  `=`, `+`, `-` or `@`: it is stored as words, never worked out as a formula. Hidden characters (decision 0074),
  including tabs, are a per-row problem.
- **Links.** Matched by the linked record's name within the parts switched on, ignoring case; nested places by full
  path (`Kitchen › Pantry › Top shelf`, `>` also understood), or by a name alone when only one place has it. An
  unknown name, or a name that matches more than one place (both full paths are listed), is a problem for that row;
  no record is ever invented. A column that links to several records takes names separated by `;`.
- **Private details.** A private (sensitive) column cannot be matched in this version: a heading that names one is
  marked "will be skipped", and a list that needs a private detail is not offered.
- **Rows that need fixing are left out.** "Send" stages only the ready rows; the page says the others are left out
  and should be fixed in the spreadsheet and imported on their own.

## Why we chose it
- The Review screen and its waiting place already make sure nothing reaches a list, total or sheet until a person
  says yes, and that one row is added once however many times Accept is pressed. Reusing it gives imports the same
  guarantees with one small migration, instead of a second staging system.
- One validator for helpers, imports and Accept means the dry run cannot promise something Accept then refuses,
  except when the records change in between, which Review already explains row by row.
- Keeping the file out of the data folder keeps a household's other spreadsheets (and anything private in them)
  out of backups, reports and the database.
- Settings is where things that bring records in from outside already live (Helpers), and one generic page covers
  every list a module declares, now and later.

## What else we considered
- **Writing rows straight into the list after the dry run.** Simpler, but a mistaken match would land in totals and
  sheets at once, and undo for a whole import is not built yet. Rejected.
- **A separate `core__import_batches` table.** Waiting rows point at their batch; a second batch table would need a
  second waiting table or a pointer that could point at either. Rebuilding one table was smaller.
- **A dummy "Import" helper.** No migration, but it would show up under Helpers, need a key and break "helpers see
  only their own batches". Rejected.
- **Keeping the upload on the server between steps** (memory or a temporary file). Saves sending it back and forth,
  but the file would outlive the request. Rejected.
- **An Import link on every list page.** Easier to find from Stock; left for later so list pages stay unchanged
  while Export and Restore are being built.
- **Blocking "Send" until every row is fixed.** Stricter, but a 200-row file with one typo would need re-uploading
  before anything could be reviewed. Leaving those rows out, and saying so, was judged kinder.
- **Lane B's fuller design** (matching existing items and catalogue names, "Set current amounts" versus "Add as
  Stock in", duplicate warnings, undo of a whole import). Not in this version: every imported row adds a new record.

## What this costs us (the downsides)
- Every row adds a new record. Importing the same file twice adds everything twice, and an import cannot change
  an existing item's amount; a stocktake still goes through Count this batch.
- The table is still called `core__helper_batches` though it now also holds imports; renaming it would touch every
  helper query for no change in behaviour.
- The rebuild in migration 0004 copies both waiting tables once. With thousands of old suggestions it takes a
  moment; a backup is made before it runs, as for every migration.
- The page carries the file (up to about 1.4 MB as text) back and forth on each step, which is slower on an old
  computer.
- Rows that need fixing are left out, so the person must remember to import them afterwards.
- Private details, files and links to parts that are switched off cannot be imported at all.
- `1/2/27` is read the household's way without asking, and a date written the other way round in a day-first
  household is read wrongly if the day is 12 or less.

## How hard it is to undo
Medium. The screens and `core/csv_import.py` can be removed freely. Migration 0004 stays (released migrations are
never edited); imported batches would remain as history, and a later migration could drop the extra columns.

## We should revisit this if
- People import the same file twice by mistake, or ask to update existing items (duplicate warnings, matching
  existing records, "Set current amounts").
- People look for the import on the Stock page rather than in Settings.
- Households need private details or files brought in from a spreadsheet.
