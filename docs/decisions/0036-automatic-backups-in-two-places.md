# 0036. Automatic backups: daily and on close, in two places

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The program copies the data file every day it runs and every time it closes
safely, into the data folder and into a second folder on the computer itself,
so losing a USB stick does not lose everything.

## What we chose
- A daily backup (`daily-YYYY-MM-DD.db`) when the program starts and, while it
  stays open, checked every hour; a backup on every safe close
  (`close-<time>.db`); the existing backup before any database update.
- Each copy is made with SQLite's safe online backup and checked for damage
  before it is kept.
- Two places: `data/backups/` and a second folder on the computer
  (`%LOCALAPPDATA%\Dashboard Plus\backups` on Windows), following decision 0006.
  If the second copy fails it is logged and the main one still counts.
  `--no-extra-backup` turns the second copy off.
- Kept: the newest 14 daily, 10 close and 5 before-update backups in each place.
- The home page says when the last backup was made.

## Why we chose it
- A USB stick can be lost or fail; two places and frequent copies make that a
  small problem instead of a disaster.
- Checking each copy means a backup that cannot be restored is never kept.

## What else we considered
- Backups only in the data folder: lost with the stick.
- Keeping every backup forever: fills the drive.

## What this costs us (the downsides)
- Copies of personal data exist on the computer as well as the stick; the
  README and wizard must say so plainly (wizard in step 6).
- Restoring is by hand in M1; the restore screen arrives in M2.

## How hard it is to undo
Low. One file, `src/dashboard/core/backups.py`, and two calls in the server.

## We should revisit this if
- Backups take long enough to slow down closing.
- People object to the copy on the computer.
