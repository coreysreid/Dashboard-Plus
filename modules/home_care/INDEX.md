# modules/home_care/  (summary: the Home care module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (who does it) and Household stock (places) | changing the module's details |
| tables.toml | Home care jobs with a do-again-by date and one gap question, and the work done on each | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order, which list is main on home | changing wording or order |
| sheets.toml | Home care sheet: each job, where, who usually does it and its dates, with no notes | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
