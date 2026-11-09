# examples/households/  (summary: three made-up households for demos, screenshots and tests)
Every name, number and address is invented; phones use ranges set aside for fiction, emails use example.com.
Each file: `title`, `summary`, `[setup]` (the first-run answers), then records as `[[module.table]]` rows.
Links name the record they point at (person = "Mary Smith"). Dates may be "today", "today+12" or "today-3".
Stock amounts are what is on hand today, after the `[[stock.movements]]` rows, which are oldest first.
Load one with: `python tools/load_example.py smith --data <an empty folder>`.
| Entry | What it is | Open it when |
|---|---|---|
| smith.toml | The Smith family: two parents, two children, a dog and a cat; Australia | showing a busy family |
| garcia.toml | The Garcia household: three generations, care needs and medication, a cat; United States | showing care needs |
| taylor.toml | Sam Taylor: one person just starting, with gaps to fill; United Kingdom | showing a first week |
