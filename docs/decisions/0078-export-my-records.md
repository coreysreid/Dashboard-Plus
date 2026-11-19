# 0078. Export my records: a zip of spreadsheet files, with private details left out

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Settings now has "Export my records". One button downloads a zip file with a
spreadsheet file for every list the household keeps, plus a short README in
plain words. It opens in Excel or Google Sheets. It is a copy for reading and
sorting, not a backup, and anything marked private is left out.

## What we chose
- **One zip, built in memory and sent as a download**, named
  `dashboard-plus-export-YYYY-MM-DD.zip`, with `Cache-Control: no-store`. Nothing
  is written to disk, so there is no half-finished export folder to clean up.
  It is a POST with the page's own token, like every other form.
- **Contents:** `<module>__<table>.csv` for each table of a module that is switched
  on (a table with no records still gets its headings), `manifest.json` and
  `README.txt`. The manifest lists the app version, the time made, each module's
  version, each table's file, title and row count, every column's heading and
  internal name (and unit and choice keys), and the labels of the columns left
  out as private.
- **How values are written:** the heading is the household's label from
  `labels.toml`, through the same helpers the screens use. A link is its record's
  name (the full path, `Kitchen > Pantry > Shelf 3`, for nested places) in one
  column and its id in the next, called `<label> (id)`, so repeated names stay
  distinct. Dates and times stay ISO. Money is whole units with two decimals (12.50),
  yes/no is Yes/No, a choice is its label (its key is in the manifest), an amount
  has its unit in the heading. Files are UTF-8 with a byte-order mark so Excel opens
  accents correctly.
- **Deleted records** are left out. A checkbox includes them, with a "Deleted on"
  column. A link to a deleted record still shows its name.
- **Private columns are never read into the files.** Any column marked
  `sensitive` is skipped, the manifest and README name it by label only, and the
  folder `data/secrets/` is never opened. A record's name never uses a private
  column (decision 0055). A test puts a made-up private value in every private
  column and checks it is nowhere in the zip.
- **Spreadsheet formulas.** Every text cell (including headings, link names and
  choice labels) that begins with `=`, `+`, `-`, `@`, a tab or a carriage return gets a
  leading apostrophe, as OWASP advises. Numbers, money, dates and ids are
  written from numbers and are never changed, so a negative amount is still a
  number. The README and manifest say so, and that the apostrophe is not part of the
  original text. Typed text keeps its other characters exactly.
- **One consistent moment.** The whole export runs inside one read transaction
  (`BEGIN`, then reads, then `ROLLBACK`), so a save in another window cannot
  make one file newer than another.
- **Code placement:** `core/export.py` builds the zip and borrows the labelling
  helpers in `web/display.py` (labels, titles, names, place paths) so the export
  can never describe a column differently from the screens; `web/export_page.py`
  is the page and the button.

## Why we chose it
- A household's first need is to see and sort their own records in a tool they
  know. A zip of CSVs does that with no other software.
- Leaving private details out is the safe default for a file that is easy to
  email or leave in Downloads. Decision 0055 and the core promise say private
  details are never copied anywhere casually.
- An in-memory download avoids choosing a folder, permission problems, and
  partial exports, and needs no new dependency.
- Apostrophe-prefixing is the common fix for formula injection and keeps the file
  legible; it is applied only where a formula could run.

## What else we considered
- **Writing a folder on disk** (the earlier draft in `workbench/drafts/restore_export`):
  more to go wrong (unwritable folder, half-finished export). It can still be added
  later for attachments.
- **Including private columns behind a warning:** kept for a later, deliberate
  decision; it would need its own confirmation. Not now.
- **Prefixing every cell, or a second raw copy of every value:** noisier, and it
  makes ordinary numbers text. A lossless raw copy is not needed while this is not a backup.
- **A tab or a second header row of internal names:** the manifest does this
  without cluttering the sheet.
- **Excel `.xlsx`:** needs a dependency and has the same formula issue.

## What this costs us (the downsides)
- **The apostrophe changes the text.** A name that really begins with `-` or `+`
  (a phone number such as `+44 20 7946 0000`) is changed in the export, so a
  household wanting to re-import it must strip the apostrophe. A tab or return at the
  start is shown as an apostrophe plus that character. The README explains it.
  Excel and Sheets may show the apostrophe or hide it, depending on how the file is
  opened; we have not tested every version of either.
- **Private details are not in it.** A household that wants everything on paper or
  in a spreadsheet cannot get it here. Backups still hold it all.
- **Not a backup and cannot restore anything.** It has no attachments, notes,
  change history or settings, and it says so.
- **Held in memory.** A very large household would use memory proportional to its
  records; the largest planned one is a few thousand rows, so this is small.
- **A new reason for core to reach into `web/display.py`**, which is a layering
  shortcut for the sake of identical wording.
- **The file is not encrypted**, and the household must keep it private; the page and the README say so.

## How hard it is to undo
Easy. It is one new core file, one page, one template and a link in Settings;
removing them changes no stored data.

## We should revisit this if
- A household wants a re-importable copy, or private details deliberately
  exported: add an explicit, warned option.
- Someone reports Excel or Sheets running a formula from an export, or
  confusion over the apostrophe.
- Exports become large enough to need writing to disk in pieces.
- The restore screens arrive (they will need attachments and a safer bundle).
