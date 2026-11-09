# 0031. Module files are checked strictly, and their migrations are generated

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
When someone writes a module, the program reads its files carefully and points
at each mistake in plain words ("unknown type 'measur'. Did you mean
'measure'?"). A helper tool then writes the database changes for the module, so
nobody has to write SQL to add a topic.

## What we chose
- `src/dashboard/core/modules.py` checks `module.toml`, `tables.toml` and
  `labels.toml`: required settings, allowed types, choices, links between
  tables, links into other modules only when listed under `requires`, reserved
  column names, and unknown settings with a "did you mean" suggestion. Every
  problem is collected, not just the first.
- A module with problems is left out and listed on the home page. It never
  stops the program or other modules from starting.
- Modules are loaded in requirement order. A module whose requirement is
  missing, broken, or in a loop is left out with the reason.
- `tools/make_migration.py <module>` replays the module's existing migrations in
  memory, compares the result with `tables.toml`, and writes the next numbered
  migration for new tables and columns. Removing or renaming something stops
  with an explanation, because it could lose data; that needs a hand-written
  migration.
- Every declared table gets the system columns from `DESIGN.md` section 3
  (id, timestamps, review status, source, batch, edited-by-person, deleted).
  Link columns become foreign keys with indexes; date columns get indexes;
  `links` columns get a small join table.
- Money is stored as whole cents in an integer; the household's currency is a
  setting, not a per-row value.

## Why we chose it
- Modules written by non-programmers, or by an AI from a sentence, need
  feedback that says exactly what to fix.
- Generating migrations keeps declarative modules code-free while still giving
  them the safety of numbered, checksummed migrations (decision 0030).
- Isolating broken modules keeps one mistake from taking the whole program down.

## What else we considered
- Stop at the first problem: faster to write, slower for authors.
- Keep a separate schema snapshot file to compare against: one more file to
  keep in step; replaying the migrations already gives the truth.

## What this costs us (the downsides)
- The checker must grow carefully as module files gain new settings.
- Per-row currencies are not supported; a household with several currencies
  would need a later change.

## How hard it is to undo
Low to medium. The checker and generator are two files; generated migrations
are ordinary SQL.

## We should revisit this if
- Module authors still struggle to understand the messages.
- Households need several currencies.
