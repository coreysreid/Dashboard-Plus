# 0009. SQLite in delete-journal mode with full syncing

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
How the database file is written so unplugging a USB stick is less likely to damage it.

## What we chose
Use `journal_mode=DELETE`, `synchronous=FULL`, foreign keys on, short transactions and a safe-close step. No WAL mode.

## Why we chose it
- WAL mode keeps extra side files and is unsafe on some removable and network drives.
- A household database is small and used by one person, so the speed gain of WAL is not needed.
- SQLite is a stable, widely readable file format, which supports no lock-in.

## What else we considered
- WAL mode: faster concurrent access, but riskier on USB.

## What this costs us (the downsides)
- Slightly slower writes.
- Only one writer at a time (fine for one person).

## How hard it is to undo
Low. It is a connection setting.

## We should revisit this if
- We see corruption despite this.
- Performance is a problem on large imports.
