# 0030. Plain SQLite access and numbered SQL migrations

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The program talks to the database file directly with Python's built-in SQLite
support, and every change to the database's shape is a small numbered SQL file
that runs once, in order, with a backup taken first.

## What we chose
- Python's built-in `sqlite3`, no database library on top (no "ORM").
- Every connection uses the USB-safe settings from decision 0009 and explicit
  transactions, so a change is saved completely or not at all.
- Migrations are files named `0001_name.sql`, `0002_name.sql`, ... in one folder
  per track: the core's in `src/dashboard/core/migrations/`, each module's in
  `modules/<name>/migrations/` (decision 0012).
- `core__migrations` records each applied migration with a checksum. The
  program refuses to start if a released migration was edited, or if the data
  folder was last used by a newer version, and says so in plain words.
- Each migration runs in its own transaction together with its record, so a
  failure leaves the database exactly as it was.
- If anything is pending and the database already holds data, a checked backup
  is written to `data/backups/before-update-<time>.db` first.
- The core track's latest number is stored in SQLite's `user_version`, so the
  file's version can be read with any SQLite tool.

## Why we chose it
- No extra dependency to keep alive; `sqlite3` ships with Python.
- Plain SQL files are readable by anyone and by any SQLite tool, matching the
  no-lock-in promise.
- Checksums and the newer-version check protect people from the two classic
  ways a database gets damaged by software updates.

## What else we considered
- SQLAlchemy and Alembic: powerful, but large, and the generated migrations are
  harder for newcomers to read.
- Building tables directly from `tables.toml` at start-up with no migration
  files: simpler, but silent and unsafe for renames and removals.

## What this costs us (the downsides)
- We write SQL by hand in the core and keep it compatible with SQLite only.
- Rules such as "required" are checked by the program, not the database, so
  they can change without rebuilding tables; code that bypasses the program's
  services could store incomplete rows.

## How hard it is to undo
Medium. Database access is concentrated in `src/dashboard/core/`.

## We should revisit this if
- Hand-written SQL becomes a frequent source of bugs.
- We need a database other than SQLite (a non-goal today).
