# modules/bills_insurance/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py bills_insurance --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_initial.sql | The commitments table and its link and date indexes, generated from tables.toml (optional links without a database rule) | checking how bills and policies are stored |
| 0002_last_four_digits.sql | Adds "Last 4 digits of the account or policy"; the old full reference is kept, unseen, until tidied (decision 0141) | checking the upgrade |
