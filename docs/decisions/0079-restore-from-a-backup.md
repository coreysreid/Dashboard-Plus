# 0079. Restore from a backup, with an Undo that survives a restart

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Settings → Backups now lists every backup Dashboard Plus has made, checks each
one without changing it, and shows what is in it compared with now. The
household can put a backup back in place. Before anything changes, the program
makes a fresh, checked copy of the records as they are, so **Undo restore**
can put them back, even after the dashboard is closed and opened again. If
anything goes wrong, the records in use are not touched and the page says
"Nothing was changed."

## What we chose
**The backup list** (`core/restore.py`, `web/restore.py`)
- Lists the copies in the data folder's `backups/` folder and, when it is
  switched on, the second copy folder on this computer (decision 0006). Only
  file names the program makes are listed (`daily-`, `close-`,
  `before-update-`, `before-restore-`, `before-undo-`); a page can only name a
  copy by its place ("data" or "computer") and that exact file name.
- Each copy is opened **read-only** (`mode=ro`) and checked with SQLite's
  `quick_check` for the list and the full `integrity_check` for the preview
  and the restore itself. Nothing is ever written to a backup file, and no
  database change is ever run on one.
- Each copy's record of database changes (`core__migrations`) is compared
  with this program's:
  - a part the program does not know about (a module it does not have) →
    refused;
  - a step this program does not know (made by a newer version) → refused,
    "update Dashboard Plus first";
  - a step whose text differs from this program's → refused;
  - fewer steps (an older copy) → allowed: the steps are run on a **copy**.
- The preview shows when the copy was made, its size, "Check passed", the
  number of records in each list then and now, and what will happen.

**The restore** (`restore.restore`), in this order:
1. Check the chosen copy again (full check, versions) and that it has not
   changed since the preview (its size and time are sent with the form).
2. Stage it: copy it with SQLite's backup into a new file in the data folder
   (`restore-staging-<random>.db`), run any missing database steps on that
   copy, mark it with the modules in use (as start-up does), turn off any
   helper whose key is no longer in `secrets/` (so the Helpers page tells the
   truth), check it in full and confirm nothing is still pending.
3. Wait until no page is using the data file (see "the gate" below), then,
   while holding it alone: make a **before-restore** backup of the current
   records with the usual checked backup (`backups/before-restore-<time>.db`),
   refuse if SQLite has an unfinished journal next to the data file, and swap
   the staged copy into place with `os.replace` (atomic on the same folder),
   flushing it to disk first.
4. Write the restore journal `restore.json` in the data folder: when, which
   copy, and the name of the before-restore backup. No secrets.
- Any failure before the swap deletes the staged file and leaves the records
  in use exactly as they were; the page says "Nothing was changed."
- **Undo restore** is itself a restore of the before-restore copy, through the
  same steps, which first makes its own `before-undo-<time>.db`. Undo removes
  the journal. **Keep these records** (dismiss) removes the journal too. A new
  restore replaces it, so Undo always goes back one step.
- Only one restore runs at a time.

**The gate** (`db.gate`)
Every web request opens its own connection and closes it at the end. A small
per-data-file gate now counts open connections: requests (and the background
daily backup) enter it as "shared"; a restore waits, for at most 30 seconds,
until it can hold the file "alone", and new requests wait until it is done.
The restore page closes its own connection before asking. Without this, on
Mac and Linux a request still holding the old file would keep writing to a
file that is no longer in use, and on Windows the swap would fail.

**Helper keys** stay in `data/secrets/` and are never part of a backup or a
restore. The pages say so.

## Why we chose it
- A household restores when something has already gone wrong; the one thing
  this must never do is make it worse. Checking read-only, working on a copy,
  making a checked copy of the current records first, and swapping in one
  atomic step means there is no moment when the data file is half-written.
- An Undo stored in a file survives closing the program, which is when people
  most often notice they restored the wrong day.
- Refusing copies from newer versions or with unknown parts avoids silently
  losing records the program cannot understand.

## What else we considered
- **Lane B's "restore into a new folder, compare, then switch"**
  (`workbench/drafts/restore_export/`). Safer for comparing side by side, but
  it needs folder switching, removable-drive handling and a way to open two
  data folders, which are much bigger changes. The before-restore copy plus
  Undo gives the same safety for the common case. Recorded as later work.
- **Copying the backup file over the data file** (plain file copy). Not
  atomic: a crash part-way leaves a broken file.
- **Restoring at the next start-up** (write a "restore this" note, restart).
  Avoids the gate, but asks the household to close and reopen, and a failure
  would only show at start-up.
- **Running database steps on the backup itself.** Never: it is often the
  only good copy.

## What this costs us (the downsides)
- Changes made after the chosen backup are replaced. Nothing is merged; Undo
  puts back the whole set of records, not single changes.
- While a restore holds the gate (normally under a second), other pages wait.
  If a page holds the file for more than 30 seconds the restore is refused.
- Before-restore and before-undo copies are never removed automatically, so
  that Undo's copy cannot be pruned away. Each restore adds one file.
- A backup with a module this program does not have cannot be restored here
  at all, even for the parts it does know. Likewise, if the records in use
  have such a part, a restore is refused, because it could not be undone.
- A helper added after the chosen copy disappears with the restore and needs a
  new key; one turned off since stays off.
- Only one Undo step. Earlier before-restore copies are still in the list
  and can be restored like any backup.
- File time is used as "made at"; a copy moved between computers may show the
  time it was copied.

## Later (out of scope for this first version)
- Restoring into a new folder and switching data folders (Lane B's flow).
- Backups on removable drives or other folders the household picks.
- Attachments (none exist yet; a backup is the database file only).
- A catalogue of backups across computers, matching identical copies in two
  places, and household identity inside each copy.

## How hard it is to undo
Medium. Remove `core/restore.py`, `web/restore.py`, its three templates and
the link in Settings; the gate in `db.py` and the module recording in
`startup.py` can stay. Restore by hand (copying a backup while the program is
closed) still works as before.

## We should revisit this if
- Households restore to look at old records rather than to go back, which
  points to Lane B's "open a copy" flow.
- A restore is refused because the gate timed out.
- Data folders grow large enough that checking every copy makes the list slow.
