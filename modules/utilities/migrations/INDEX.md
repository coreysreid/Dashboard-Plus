# modules/utilities/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py utilities --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_initial.sql | The module's first table, generated from tables.toml | checking how services are stored |
| 0002_last_four_digits.sql | Adds "Last 4 digits of the account"; the old full account number is kept, unseen, until tidied (decision 0141) | checking the upgrade |
