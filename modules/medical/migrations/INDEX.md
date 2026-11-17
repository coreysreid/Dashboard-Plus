# modules/medical/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py medical --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_where_kits_are_kept.sql | Adds whether each kit is kept at home, in a vehicle or somewhere else | checking how the tables are stored |
