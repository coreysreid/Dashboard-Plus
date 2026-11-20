# modules/home_care/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py home_care --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_repeat_choice.sql | Adds the optional household repeat (every N weeks, months or years) to jobs, unset for every job | checking how the repeat is stored |
