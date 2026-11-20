# modules/documents/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py documents --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first table, generated from tables.toml | checking how the table is stored |
| 0002_copies_also_kept.sql | Places copies are kept, and the link from each paper to them | checking how copies are stored |
