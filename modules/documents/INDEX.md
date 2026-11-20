# modules/documents/  (summary: the Important documents module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (whose paper) and Household stock (places) | changing the module's details |
| tables.toml | Where each paper is kept, whose it is, its review or renewal date and the places copies are also kept (copy_places), with one gap question; no document numbers | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Document review dates sheet: names, kinds, dates and where copies are kept; no original places or numbers | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
