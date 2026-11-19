# src/dashboard/core/migrations/  (summary: the core's numbered database changes; never edit a released one)
Add a new file with the next number instead of changing an old one.

| Entry | What it is | Open it when |
|---|---|---|
| 0001_core_tables.sql | Settings and the list of modules in use | checking the core tables |
| 0002_audit_history.sql | The history of every change to every record | checking how history is stored |
| 0003_helpers.sql | Helpers, their suggestion batches and the suggested records waiting for a decision | checking how helpers and suggestions are stored |
| 0004_import_batches.sql | Batches can come from a spreadsheet import by a person, not only a helper; rows keep their spreadsheet row | checking how imported rows wait for Review |
