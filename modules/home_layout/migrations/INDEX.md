# modules/home_layout/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py home_layout --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_private_access_details.sql | Adds a private codes-or-access-details box to ways out, shut-offs, alarms and meters | checking the upgrade |
