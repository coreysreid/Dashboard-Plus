# modules/wine/  (summary: the Wine collection module, files only; built on Lane B's draft, no links to other modules)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires nothing | changing the module's details |
| tables.toml | Wines, bottles (a count you type, a free-text place, an ordinary price) and tasting notes; one question about where bottles are kept | adding a field or a gap question |
| labels.toml | Friendly labels, help text (says price and notes enter exports), form and list order | changing wording or order |
| sheets.toml | Wine collection sheet: wine, count, place and bought on, with no price or notes | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
