# 0066. Helpers get a key from Settings: shown once, kept only as a fingerprint outside the database

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** DESIGN section 9 (the command-line tool there is replaced by a Settings screen)

## In plain words
A "helper" is a program, such as an AI assistant, that the household lets look at some of its records and suggest new
ones. To connect, a helper needs a secret key. You make the key on a Settings page, copy it once, and give it to the
helper. The program keeps only a scrambled fingerprint of the key, never the key itself, so nobody who gets a backup or
a look at the files can read it back. You can turn a helper's access off at any time, and a turned-off key stays dead
even if you later restore an old backup.

## What we chose
- Keys are made in Settings, Helpers: a name, what it may do ("Look only" or "Look and suggest new records") and which
  parts of the records (modules) it may use. None are ticked by default.
- A key is `dph_` followed by 32 random bytes. It appears once, on the page that answers the "Make a key" button (never
  in a link, a cookie or the history), and is never written to the database, the log or any file.
- The fingerprint (SHA-256) of each live key lives in `data/secrets/helper_keys.json`, a file readable only by this
  computer account, mapping fingerprint to a random `key_id`. The helper's row in the database holds the same `key_id`,
  its name, level, parts and dates. The file is written under a temporary name and swapped into place.
- Checking a key compares its fingerprint with every stored one in constant time, then needs a database row with that
  `key_id` that has not been turned off.
- Turning off removes the fingerprint from the file first, then marks the row. The row, its suggestions and its history
  are kept.

## Why we chose it
- A key worth stealing must not sit in the database: backups, copies of the data folder and "Save a report" would carry it.
- Keeping the fingerprints outside the database means restoring an old backup can never bring back a key that was turned
  off, and a key made after the backup cannot work against the restored database (its `key_id` is not there).
- A Settings screen is something a household can use; a command-line tool is not.
- SHA-256 is enough for keys that are 256 bits of randomness; a slow password hash would add nothing.

## What else we considered
- Keys stored (even hashed) in the database: simpler, but a restore could revive a turned-off key.
- A command-line tool, as DESIGN first said: kept for later; the screen is what households need first.
- One key per computer for all helpers: no way to turn one helper off without the others.

## What this costs us (the downsides)
- If the `data/secrets` folder is lost but the database is kept, every key stops working and must be made again.
- If a household copies the data folder to a new computer without the secrets folder, helpers must be given new keys.
- A key shown once cannot be shown again; a lost key means a new one.

## How hard it is to undo
Easy. Nothing else depends on how keys are stored; switching to another way means making new keys.

## We should revisit this if
- Households ask to see a key again, or want keys that expire by themselves.
