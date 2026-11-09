# 0012. Each module has its own migration track

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Adding or removing a module cannot upset the numbering of other modules' database changes.

## What we chose
Numbered, forward-only migrations with separate tracks for the core and for each module, recorded in a migrations table with checksums.

## Why we chose it
- Required by the brief; also the only way module add/remove stays safe.
- Checksums catch accidental edits to released migrations.

## What else we considered
- One global numbered list: simpler, but modules would clash and block each other.

## What this costs us (the downsides)
- Slightly more bookkeeping, and dependencies between modules must be declared.

## How hard it is to undo
High once released, so it is settled now.

## We should revisit this if
- Module dependencies become tangled in practice.
