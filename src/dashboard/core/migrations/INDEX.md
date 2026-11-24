# src/dashboard/core/migrations/  (summary: the core's numbered database changes; never edit a released one)
Add a new file with the next number instead of changing an old one.

| Entry | What it is | Open it when |
|---|---|---|
| 0001_core_tables.sql | Settings and the list of modules in use | checking the core tables |
| 0002_audit_history.sql | The history of every change to every record | checking how history is stored |
| 0003_helpers.sql | Helpers, their suggestion batches and the suggested records waiting for a decision | checking how helpers and suggestions are stored |
| 0004_import_batches.sql | Batches can come from a spreadsheet import by a person, not only a helper; rows keep their spreadsheet row | checking how imported rows wait for Review |
| 0005_helper_key_rotation.sql | A helper can get a new key and keep its history: when the key was changed, a change still in progress, and a count of keys | checking how a key change is stored |
| 0006_proposal_source_lines.sql | A helper's suggestion can keep the line it was read from (a receipt line and price), shown on Review only | checking how source lines are stored |
| 0007_sync_identity.sql | Sync stage 1: the household ID and epochs, the change log, and values held after a kind change (decision 0100) | checking how permanent IDs and the change log are stored |
| 0008_helper_daily_allowance.sql | "Allow 200 more today": each press adds to one helper's daily limit for that day only, with who and when (decision 0101) | checking how a raised daily limit is stored |
| 0009_receipt_lines_and_repeats.sql | Receipt lines a helper could not match wait on Review as their own kind; a batch can be one receipt, stay open until finished, and be kept as another purchase (decision 0105) | checking how receipt lines and repeat receipts are stored |
| 0010_reminder_moves.sql | One reminder per policy: which older records (Vehicle insurance) were moved to a newer list (Bills and insurance), by exact IDs and a state, never names or dates (decision 0117) | checking how a moved reminder is stored |
