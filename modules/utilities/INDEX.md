# modules/utilities/  (summary: the Utilities module, files only; built on Lane B's draft, linking to People and Home layout)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (provider and fault contact) and Home layout (meter) | changing the module's details |
| tables.toml | Services with a private account reference and notes, and two gap questions about the fault contact | adding a field or a gap question |
| labels.toml | Friendly labels, help text (says what is private), form and list order | changing wording or order |
| sheets.toml | Utility contacts sheet: service, provider, fault contact, their phone and the meter, with nothing private | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |
