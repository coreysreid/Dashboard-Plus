# modules/garden/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py garden --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_done_on.sql | Adds the optional Done on date to jobs, empty for every job already there (never guessed, decision 0129) | checking how a job's done day is stored |
