# workbench/drafts/stock_lots/  (summary: target design for per-lot stock amounts and dates)
| Entry | What it is | Open it when |
|---|---|---|
| tables.toml | Illustrative target item, lot and movement schema; not loadable yet | integrating lots into Stock |
| NOTES.md | Screen-by-screen flow, migration and exact core needs | planning core work |
| example.toml | Fictional rows for the Smith, Garcia and Taylor households | preparing promotion examples |
| ACCEPTANCE.md | Numbered stocktake, lot, watch, date and migration checks | testing lots and local dates |
| example_lots.toml | Every example Stock item as a target lot, with old movements preserved | testing lots migration |
| ITEM_TO_LOT.csv | Exact old item to migration and target-lot mapping | checking totals and IDs |
| validate_fixture.py | Check the three fixed-date lots fixtures against the shipped example Stock rows. | reviewing migration data |
| MIGRATION_FIXTURE.md | Two-stage migration and exact preservation checks | building the lots migration |
| SHIPPED_FOLLOWUP.md | Shipped acceptance differences and Garcia/Taylor second batches | reviewing lots after release |
| garcia_with_second_batches.toml | Full fictional Garcia example with two more batches | adopting Garcia test data |
| taylor_with_second_batches.toml | Full fictional Taylor example with two more batches | adopting Taylor test data |
