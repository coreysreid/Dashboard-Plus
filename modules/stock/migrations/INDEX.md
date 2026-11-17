# modules/stock/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py stock --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_stock_in_and_out.sql | The Stock in and out table | checking how movements are stored |
| 0004_places_inside_places.sql | Places can sit inside other places ("Inside") | checking how nested places are stored |
| 0003_drinking_water.sql | "Safe to drink" on items; existing water stays counted | checking how drinking water is stored |
| 0005_batches.sql | Batches: an item's stock split by use-by date and place; each existing item becomes one batch | checking how the tables are stored |
