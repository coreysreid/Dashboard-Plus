# Private-detail erasure: current behavior and core contract

Design checked **18 November 2026** against `src/dashboard/core/{records,db,backups}.py`, `src/dashboard/web/templates/form.html`, [DESIGN section 11](../../../docs/DESIGN.md) and decisions 0055/0059. This is design only; no shipped code changes.

## What Delete currently does

`Records.delete()` sets `deleted_at` and Restore can bring the row back, including cascaded rows. `_audit()` writes unredacted JSON `before`/`after` values on create and update, so clearing a private field with the ordinary edit path writes its previous value into `core__audit`. `db.backup_to()` copies the whole SQLite database. The backup service keeps daily (14), safe-close (10) and before-update (5) copies in `data/backups` and, when enabled, a second computer-side folder keyed to this data folder. A failed or disconnected second copy is reported but does not stop the main backup. A temporary `.partial` copy can also exist during a failed write. The normal Delete wording promises restore, not erasure.

## Proposed scope and sequence

The action identifies one **table, record ID and sensitive field** from the module schema. It does not search for the same text in unrelated records. Preflight enumerates all app-managed backup directories and files, including incomplete copies, checks access and displays a count/status without revealing the value. Refuse to promise completion if an enabled second copy is unreachable. Pause backup writers and create a durable **erasure pending** marker that stores identifiers but never the erased text; the restore path must honor it even after a crash.

Inside a database transaction, clear the current field even on a soft-deleted row. Redact that field from every `core__audit.before` and `after` JSON for that table/record, keeping action, time and nonprivate fields; insert a redacted erasure event without re-auditing the old value. Do not use the ordinary update method for this. Invalidate any private reveal cache and refresh current list, sheet and history views. Confirm that no copy of the target field remains in active rows or matching audit fields.

Then remove every app-managed backup that predates the scrub and may contain the value, including both configured backup folders and any `.partial` file. Do not silently rewrite a possibly damaged old backup. Verify deletion, write and verify a fresh clean backup, and only then mark the ledger complete and show success. If any step fails, leave the pending marker and resume on next launch; block restore from an older managed copy until it is re-scrubbed or refused. A restore/import from an external old copy must check the ledger and warn that the private value may return, then reapply the scrub before activation or require explicit separate handling. The ledger must survive backup replacement and identify only the erased field, never its value.

**Limits:** This is erasure from the current data folder and app-managed backups it can reach, not a claim of physical secure wiping. OS/SSD remnants, filesystem snapshots, user-made copies, synced folders, printed sheets, exports, notifications, other computers or another field where someone repeated the value may remain. A future export/helper API needs the same policy. No secret-bearing undo copy may be retained after success. The way back is **Cancel before confirmation** or the reversible **Remove from dashboard** route; there is no Undo of the value after completed erasure.

## Core needs

There is no field-level scrub, audit redaction, backup enumeration/retirement, durable erasure ledger, restore gate, resume-on-failure job or success verification today. `status.json` only reports the last backup attempt. Ordinary record Delete and Restore must continue to mean reversible removal. Implementing this requires a Lane A decision about backup retention tradeoffs and how external restore is gated; until then, show no Erase action in the shipped UI. [Acceptance checks](ACCEPTANCE.md) specify the required behavior.
