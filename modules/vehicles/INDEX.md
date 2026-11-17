# modules/vehicles/  (summary: the Vehicles module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (who to call) and Household stock (places, car kit) | changing the module's details |
| tables.toml | Vehicles, insurance renewals, services and checks, with due dates and one gap question | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Vehicles sheet: who to call, where each is kept and the dates, with no private numbers | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
