# modules/bills_insurance/  (summary: the Bills and insurance module, files only; built on Lane B's draft, beside Utilities)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (provider); Vehicles and Household stock only optionally (decisions 0115, 0117) | changing the module's details |
| tables.toml | Bills and policies with private amount, cover, reference and notes that never travel; due words per kind; `takes_over` of Vehicle insurance; a `calendar` of check dates, never amounts (decision 0122) | adding a field or changing the reminder |
| labels.toml | Friendly labels and help, the optional vehicle and place words, and the household's words for moving a Vehicle insurance reminder | changing wording or order |
| sheets.toml | Bills and policies to check: names, kinds, providers and dates, nothing private | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
