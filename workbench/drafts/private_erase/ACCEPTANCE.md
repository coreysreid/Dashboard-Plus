# Private-detail erase acceptance checks

Use only an invented sensitive People Important detail and a fictional Vehicle plate in an isolated data folder. Checked against shipped retention behavior **18 November 2026**.

1. **Remove remains reversible:** Remove a private record from the dashboard. Lists/sheets omit it, Restore brings it back, and the screen says history/backups may still contain old values. No Erase success is claimed.
2. **Preflight:** Before erasing one field, show its record/field and status of the main and enabled second backup folders without including the value in page HTML, URL, logs or notifications. Cancel leaves every byte and backup unchanged.
3. **Active field:** Erase a current Important detail. Its active value is blank/redacted; record name and nonprivate fields remain. List, record, reveal endpoint, private sheet and history no longer return the old text.
4. **Deleted field:** Erase a value on a soft-deleted row. Restoring that row does not restore the value. Cascaded/linked records are not accidentally erased.
5. **Audit:** A value entered, edited twice and then removed is absent from every matching `core__audit.before` and `after` field after erasure. Actions and dates remain. The erasure event itself contains no old value.
6. **Backups:** Daily, safe-close and before-update copies in both app-managed folders that might contain the value are retired; incomplete `.partial` copies are checked. A newly made clean backup passes integrity and contains no target field value or matching audit value.
7. **Unavailable second copy:** With the enabled computer-side folder disconnected or unwritable, completion is refused and status says what remains. Reconnection and retry resume without exposing the old value; the app never silently marks the copy off.
8. **Crash:** Interrupt after active-data scrub but before backup retirement. Next launch sees an erasure-pending marker, blocks old restore, resumes safely and never reports success early.
9. **Old restore:** Attempt to import an older app or user-made backup with the erased value. The restore gate detects the erasure ledger, warns, and re-scrubs or refuses before the old value becomes visible.
10. **Scope:** Erasing one record/field does not silently erase a different record where the same fictional text was entered. The result names external copies, printouts and filesystem history as outside the app's reach.
11. **No secret undo:** After verified success, there is no Undo or hidden secret copy. Nonprivate history remains readable with the private field marked erased. A fresh value can later be entered as a new household action.
12. **Concurrent access:** A stale tab or duplicate click cannot reinsert the old value or report success twice. Backup writing and private reveal requests cannot race the scrub; authorization and local confirmation are checked again at commit.

These are future acceptance checks, not tests of a shipped erasure feature. Sources: `records.py`, `backups.py`, `db.py` and the shipped private reveal flow, checked 18 November 2026.
