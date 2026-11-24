# modules/medicine_doses/  (summary: Medicine doses, files only; built on Lane B's draft, linking to People)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People | changing the module's details |
| tables.toml | Medicine doses: a private table (no helpers, imports, Home or sheets), the medicine limited to the person's own medication details by `link_rule`, every column travels; `daily` totals per medicine the two-hour repeat question and a private month `calendar` per person (0121) | adding a field or changing the daily words |
| labels.toml | Friendly labels, help text (check the pack; the amount is never copied), "I do not know" for the giver, form and list order | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |
