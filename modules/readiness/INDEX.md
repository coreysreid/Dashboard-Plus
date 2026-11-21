# modules/readiness/  (summary: the Readiness module, files only: 49 "Have you thought about…?" questions and the household's answers)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; needs no other module (record matches into other modules find nothing while those are off) | changing the module's details |
| tables.toml | Your answers: one record per question, answer, dates, note and the record used to confirm it; helpers may look, never suggest | changing how answers are kept |
| labels.toml | Friendly labels and help for Your answers, form and list order | changing wording or order |
| prompts.toml | The questions in seven groups, each with why, what it fits, the exact record match, review interval and official source | changing a question, a source or a record match |
| migrations/ | Numbered database changes | after changing tables.toml |
