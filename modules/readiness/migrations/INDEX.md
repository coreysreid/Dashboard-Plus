# modules/readiness/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py readiness --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The answers table, generated from tables.toml | checking how answers are stored |
| 0002_drill_runs.sql | Practice runs and practice answers for Think it through (decision 0108) | checking how practice runs are stored |
