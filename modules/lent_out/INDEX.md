# modules/lent_out/  (summary: the Things lent out module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (the borrower) and Household stock (the item) | changing the module's details |
| tables.toml | Loans with a due-back reminder only while still out, a Mark returned button, and one question about reaching the borrower | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order, main list on home | changing wording or order |
| sheets.toml | Things still lent out sheet: what, who, their phone from People and the dates, with no notes | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
