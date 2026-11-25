# modules/stock/  (summary: the Household stock module, files only)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description | changing the module's details |
| tables.toml | Places (with a floor for the way-out sketch), connections between them (Set up my home), stock items (running low, use-by, days of water) and stock in and out (with an optional confirmed price and Spent per month) | adding a field, category or rule |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Emergency supplies checklist | changing what prints |
| catalogue.csv | 800 common goods to pick from while typing (from Lane B's catalogue) | adding or correcting a good |
| places.csv | 120 rooms, cupboards and shelves to pick from while typing a place (from Lane B's list) | adding a place name |
| migrations/ | Numbered database changes | after changing tables.toml |
