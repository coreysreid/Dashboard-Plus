# Garden promotion notes

Checked **2026-11-17** against the working example in `examples/garden/`, the shipped module contract and `docs/DESIGN.md` sections 5 and 6. This workbench copy keeps the teaching example's table keys and initial migration. It adds a **planting name** with an additive migration so a harvest in `example.toml` can link to one planting through the existing example loader. The name also distinguishes two sowings of the same crop in one bed. Lane A should use the additive migration when promoting an existing garden database; do not silently replace a released migration.

The bed-location gap asks only where a named bed or pot is. The current `expiring` watch has no `where` filter, so it cannot exclude jobs marked done. Leave garden jobs out of Needs attention until the core can filter `done = false`, then use the household's own due date with wording **“due”**. The printed plan already excludes finished jobs.

The three examples use a yard bed, balcony pot and windowsill pot. Their dates and amounts are invented illustrations, not growing advice, expected yields or seasonal recommendations. No external source or licence is needed for these made-up records.
