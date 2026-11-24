# modules/pet_feeding/  (summary: the Pet feeding log, files only; built on Lane B's draft, linking to Pets)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires Pets | changing the module's details |
| tables.toml | Food given: one entry per bowl, refill or treat, food put out (not eaten); `daily` totals by the household's day, the possible-repeat rule and a month `calendar` per pet | adding a field or changing the daily words |
| labels.toml | Friendly labels, help text (put out, not eaten; units never converted), form and list order | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |
