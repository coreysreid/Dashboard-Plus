# 0010. One real SQLite table per declared table

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Each thing a person tracks (for example weigh-ins) becomes its own table in the database file.

## What we chose
Generate real, named tables from the module files (`pets__weights`), not one giant generic table of key/value pairs.

## Why we chose it
- Fast, simple queries and readable by any SQLite tool, which keeps the 'no lock-in' promise.
- Constraints and indexes work properly.

## What else we considered
- A generic 'entity-attribute-value' table: flexible with no schema changes, but slow, awkward to query and hard to export cleanly.

## What this costs us (the downsides)
- Changing a table needs a migration (this is intended, and migrations are built in).
- More machinery to generate tables.

## How hard it is to undo
High once real data exists, which is why we chose it carefully now. It would need a data migration.

## We should revisit this if
- Schema changes from users become frequent enough that migrations are a burden.
