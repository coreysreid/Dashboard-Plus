# modules/stock/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py stock --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_stock_in_and_out.sql | The Stock in and out table | checking how movements are stored |
| 0004_places_inside_places.sql | Places can sit inside other places ("Inside") | checking how nested places are stored |
| 0003_drinking_water.sql | "Safe to drink" on items; existing water stays counted | checking how drinking water is stored |
| 0006_connections_between_places.sql | Connections between places: which rooms lead into which, and doors to outside (decision 0103) | checking how connections are stored |
| 0007_way_out_sketch_facts.sql | A floor, sleeping and checked-window flag on places, and a confirmed destination on doors to outside, for the way-out sketch (decision 0118) | checking how the sketch's facts are stored |
| 0005_batches.sql | Batches: an item's stock split by use-by date and place; each existing item becomes one batch | checking how the tables are stored |
| 0009_money_back.sql | A table of money back (refunds) on a priced Stock in; nothing existing changes (decision 0133) | checking how refunds are stored |
| 0008_purchase_prices.sql | A confirmed purchase price, how it was meant, its line total and currency on Stock in and out; existing rows keep no price (decision 0128) | checking how prices are stored |
