# Restore and export: the household's path

Drafted 17 November 2026 for M2 / J4. The shipped app already makes verified daily and safe-close database copies and shows the latest status in Settings. It has no household restore or export screen yet. This is proposed behavior, not current instructions. Dates below are illustrative and must display in the household's chosen date format and local time, with year and time zone visible when copies could be confused.

## 1. Find a backup

From Home or Settings, choose **Backups and export**. The first panel says: “Your records are saved as you go. These are copies you can use if your data folder is lost or damaged.” Show the latest good copy and, below, a list ordered newest first. Each row shows `Made 17/11/26 at 14:35`, kind (`When I closed`, `Daily`, `Before update`, `Before restore`), source (`Data folder` or `This computer`), and state (`Ready to check`, `Damaged`, `Missing`, `Cannot open`). Group identical copies made in both places by time and content, with both locations shown; allow the person to choose either physical copy. Filter by date range and location. Never call a failed second copy “ready” merely because the data-folder copy worked.

Empty state: “No backup copies found yet. Your current records are still saved. Make a backup now.” A missing or disconnected USB: “This data folder is not available. Check that the drive is connected, or look for a copy on this computer.” If the app cannot identify which household a copy belongs to, show “Household unknown” and require an explicit selection after inspection.

## 2. See what the copy contains

Selecting a row opens a **Check this backup** page. Run integrity checks before displaying its summary. Show household display name only if present, copy date/time, app/schema version, enabled modules, record counts by table, last recorded change and whether attachments are included. For a version that predates an optional module, say “This copy has no Pets records” rather than implying deletion. Counts are a preview, not a promise that every value is correct. Mark any inaccessible, corrupt or unsupported copy “Cannot restore this copy” with a plain reason. A second copy with the same contents may still be usable.

Primary action: **Restore into a new folder**. Secondary: **Back to backups**. Do not put a one-click overwrite action on the list. Before proceeding show: “This will make a separate folder from the 17/11/26 backup. Your current folder will stay where it is.” Display the proposed destination and allow changing it. If it already exists, require another empty folder. Show the source and destination together.

## 3. Restore, compare and switch

Copy into a temporary new destination, validate the result, then give a comparison page: “Restored copy ready. It has 42 Stock items and 5 People records. Your current folder has 47 Stock items and 5 People records.” Show counts and last-change times for both, and a simple warning when restored data is older. Actions: **Open restored copy**, **Keep using current records**, **Use restored copy from now on**. Do not silently merge, delete or overwrite the current folder. Opening a restored copy first allows a household to inspect records and sheets without changing the active folder. On switching, make a verified snapshot of the then-current folder, record exactly which path was active, and show where the old folder and snapshot are. Close database connections before switching. If a removable drive disappears mid-copy, leave the current folder active and report “Restore did not finish. Your current records were not changed.”

After switching show **Undo this restore** until the household chooses to discard its previous folder/snapshot. Explain that undo switches back to the previous folder as it was at the time of the switch, so edits since switching are not merged. Before undo, make another verified snapshot of the currently active restored folder so those edits remain recoverable. A chain of two restores must offer the most recent switch to undo first. Never erase a folder automatically as part of restore or undo.

## 4. Export everything

From the same page choose **Export everything**. First say: “The export includes private details such as phone numbers, medical notes and locations. Choose a folder you control.” List included tables and file types before writing. Choose an empty destination folder; let the person change it. The result page says: “Export ready in [folder]. Open README.txt first.” It links or opens the folder and reports the number of CSVs, text files and attachments written, plus any failures. If any file fails, say “Export incomplete. No finished export was marked ready.” Keep a partial folder clearly named and offer retry or removal after review.

The folder contains one UTF-8 CSV per table, a `README.txt` mapping filenames to household words and explaining columns, and any attachments and notes as readable files. CSV header names are stable keys; README explains the labels. Choice columns carry both stored key and readable label in separate columns; links carry both linked record ID and readable name/path so repeated names stay distinct. Dates are ISO `YYYY-MM-DD` in exported data and the README explains how to display them in Excel or Google Sheets. Use proper CSV quoting, a UTF-8 BOM if needed for direct Excel opening, and a documented treatment for cells that spreadsheet software would execute as formulas. Keep a portable, lossless copy of the original values as well as a safe spreadsheet view if those needs conflict. Deleted records and audit history need explicit, documented inclusion choices; never silently lose them. The export is data, not a restorable app backup.

No secrets or helper tokens go in the export. The app should not upload the folder, email it or send it to a cloud sheet. A person's own sensitive fields *are* included, as the design says. Exact wording on completion: “Keep this folder private. Anyone who can open it can read your exported details.”

## References

- [Dashboard Plus design, section 11](../../../docs/DESIGN.md) and [J4](../../../docs/JOURNEYS.md), checked 17 November 2026: product contract and journey, not external safety guidance.
- [SQLite backup API](https://www.sqlite.org/backup.html), checked 17 November 2026: consistent database copy behavior. The shipped `src/dashboard/core/db.py` uses SQLite's online backup and `PRAGMA integrity_check`; `src/dashboard/core/backups.py` keeps daily, close and before-update copies.
- [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection), checked 17 November 2026: spreadsheet formula risk from untrusted cell text. Do not invent an escaping rule without testing Excel and Sheets import behavior.
