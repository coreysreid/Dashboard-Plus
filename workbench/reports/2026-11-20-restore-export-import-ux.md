# Restore, export and import: three-household UX check

Checked **20 November 2026** against `main` at `9f6d1a1` and the invented Smith (AU), Garcia (US) and Taylor (UK) examples. Each run used a fresh temporary data folder and system Chromium at **320px** and a **1200px or 1280px desktop** viewport. The CSV was the unchanged `workbench/drafts/csv_import/EXAMPLE.csv`; column choices were changed on the import screen when needed. No real records or keys were used.

## Findings, worst first

### 1. Existing Stock names can be staged as new items

**Steps:** In Smith, import `EXAMPLE.csv` into **Stock items**, skip the unmatched **place** column, choose **Check again**, then **Send 3 rows to Review**. Smith already has **Rice** and **Kidney beans**. Review says each row **“would add to Stock items”** and offers **Accept**, without saying that an item with that name already exists. We accepted only the invented `TOM TINNED 400G` row, so no duplicate was made in this run. The add-only behavior is stated generically, but a household could accept an existing good as a second item and split its stock count.

**Exact added Review line for each matching name:** **“An item named Rice is already in Stock. Accepting this row will make another Rice item. To add what you bought, use Stock in; to correct a count, use Count this batch.”** Substitute the actual name. Do not auto-merge names: two goods can legitimately share a name. Core would need a current-item lookup and warning in the import dry run and Review; see `workbench/drafts/csv_import/NOTES.md`.

### 2. An ambiguous short date looks settled on AU/UK Review

**Steps:** In Smith or Taylor, follow the same import. Row 5 of `EXAMPLE.csv` contains `1/2/27` and its invented note says **“Ambiguous date needs review.”** The dry run calls the row ready and Review shows **“Use by: 01/02/27”** without a date warning. The household's day-first setting explains this interpretation, but a spreadsheet from a different country could have meant 2 January. Garcia's month-first import correctly refuses the separate `20/05/27` row and asks for `05/20/27` or `2027-05-20`.

**Exact added dry-run warning for row 5:** **“Row 5: ‘1/2/27’ could mean 1 February or 2 January. Use two digits for day and month in this household's order, or use 2027-02-01, then check again.”** The ISO example reflects the current AU/UK interpretation; the person must choose the intended date. Core needs a separate ambiguity rule for imported dates, without changing ordinary dates typed on a household form.

### 3. Skipping Place works, but the loss is easy to miss

**Steps:** The unchanged sample initially produces **0 rows ready, 4 need fixing** in all three households: `Kitchen › Pantry › Top shelf` and `Garage › Top shelf` are not saved places in those examples. Choose **Skip this column** for `place` and **Check again**. Smith and Taylor then have **3 ready, 1 needs fixing**; Garcia must also skip `use_by` because its US date order rejects `20/05/27`. The remaining water row is excluded because **Is this water safe to drink now?** is blank. The three ready rows reach Review, but none has a place (and Garcia's has no use-by date). Review omits skipped fields rather than calling out the loss.

**Exact added line above “Send 3 rows to Review”:** **“Skipped columns: Where it is”** (and **“, Use by”** for Garcia). **“These values will not be added. Check each row on Review, or go back and fix the file first.”** The current interface provides no per-row correction on Review. Preserve the existing refusal for the blank water answer; it must not default to safe to drink.

### 4. The missing-place hint names a place outside this household

**Steps:** Keep the `place` column mapped on any of the three imports and choose **Check the rows**. The error for each missing path ends **“Use the full path, like Kitchen › Pantry › Shelf 3.”** That example path is not a saved place in Garcia or Taylor, and it is not the missing sample's `Top shelf` path. The specific example can make the person search for a place they do not have.

**Exact replacement:** **“Use the full path of a place saved in this household, or add the place first.”** If a current-household example is available, it may be shown after this sentence, but the sentence must stand alone.

## What passed

| Household and widths | Restore → Undo | Export and spreadsheet | `EXAMPLE.csv` → Review |
|---|---|---|---|
| Smith · 320 / 1200 | A temporary Stock marker disappeared after Restore and returned after Undo. Preview showed the changed Stock-item count. | ZIP downloaded at both widths; its Stock CSV was opened and parsed as UTF-8 with headers and the marker. | Skipping Place gave 3 ready, 1 needing the water answer; three staged, one accepted, two remained waiting. |
| Garcia · 320 / 1280 | Same marker check passed; preview compared 25 Stock items in the backup with 26 now. | ZIP downloaded; 31 CSVs opened and parsed, including Stock headers and rows. | Skipping Place and Use by gave 3 ready; one accepted. The US date hint rejected `20/05/27` when mapped. |
| Taylor · 320 / 1200 | Same marker check passed; preview compared 12 Stock items in the backup with 13 now. | ZIP downloaded at both widths; 26 CSVs opened and parsed. The exported Stock CSV was opened by LibreOffice Calc 26.8 in headless mode and converted to a readable XLSX at both widths. | Skipping Place gave 3 ready; one accepted, two remained waiting. AU/UK-style dates showed day first. |

Visited pages included backup list, preview, restored and undone confirmations, export, import mapping, dry run and Review. Every captured route returned successfully, and document width stayed within its viewport at 320px and desktop. The spreadsheet check confirmed that Calc could read the Stock CSV, but it did **not** assess visual layout in an interactive spreadsheet window. The import examples test the shipped add-only path; they do not prove receipt-style Stock in or batch Undo. Expected behavior and exact words were checked against `src/dashboard/web/templates/{restore_*,export,import,review}.html`, `src/dashboard/core/csv_import.py`, the three example files and decisions 0078–0080 on the date above.
