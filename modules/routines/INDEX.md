# modules/routines/  (summary: the Routines module, files only; the household's own repeating tasks, promoted from Lane B's routine checklist draft)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (who) and Household stock (places) | changing the module's details |
| tables.toml | Routines with an optional repeat (days, weeks, months, years) and one next date; Done or skipped keeps the planned date; Mark this occurrence done and Skip this time; a month `calendar` of Done, Skipped and next dates | adding a field or changing the actions |
| labels.toml | Friendly labels, help text, form and list order, routines main on home | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |
