# 0100. Sync stage 1: permanent record IDs, revisions and a filtered change log (nothing leaves the computer)

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical shape delegated by User 1 under decision 0089); product rules from User 1 in 0089
- **Builds on:** 0089 (household sync, stage 1), 0055 (modules confined to their own tables), 0032 (one checked path for every record change), 0079 (restore), `workbench/drafts/sync/STAGE1.md`

## In plain words
Every record now has a permanent ID that never changes, and a number that goes
up each time it is changed. Every change is also written in a separate list of
changes, ready for a later step that shares records with another computer of
the household. Things that must never leave the computer where they were typed
(access instructions, Home layout access details, vehicle registration numbers)
are never written in that list, not even in disguise. Nothing is sent anywhere
yet: there is no network code in this step.

## What we chose
1. **A permanent ID for every record.** Every row of every module table, deleted
   rows and rows of switched-off modules included, gets `global_id`: a random
   UUID (version 4) made with the row and never changed. Its local number `id`
   and every link between records stay exactly as they were.
2. **A revision for every record.** `row_revision` starts at 0 for records that
   existed before this change and at 1 for a new record, and goes up by one for
   each *operation* that changes the record. One operation is one saved
   transaction: saving a Stock in, which also starts a batch and changes the
   item's amount, is one operation, and each record it touched goes up once.
3. **How the columns get there (and why it respects decision 0055).** The core
   adds the two columns, fills in IDs and adds a unique index **after each
   module's own migrations, at every start-up** (`src/dashboard/core/sync.py`,
   `prepare`). It runs once per module, in one transaction, **under that
   module's own confinement rule** from decision 0055, so even this core step
   can only touch that module's own tables. Modules still cannot touch core
   tables, and no module migration writes these columns. Because it is driven
   by each module's declared tables, it works for every declarative module,
   including ones added later, with no change to any module. It is safe to run
   every time: once done it changes nothing. If records already exist and need
   IDs, start-up makes a `before-update-` backup first (the same backup as for
   migrations). A module whose tables cannot be upgraded is left out and
   reported, like a module whose migration failed, and its records are not
   changed. `global_id` and `row_revision` are now reserved names a module may
   not declare.
4. **The change log** (`core__sync_changes`, core migration 0007). Written in the
   same transaction as the record and its history entry, by the one write path
   every change already goes through (`Records._audit`, decision 0032). Each
   line has: a per-computer sequence number (the order changes were saved,
   never the clock), the epoch, the operation ID, the action (create, update,
   delete, restore, or link/unlink for a many-to-many pair), the table, the
   record's permanent ID, the revision before and after, the names of the
   changed fields, the values that may travel (`patch`), the names of changed
   fields whose values stay here (`withheld`), whether the change was worked out
   from another record (an item's amount from its batches: `effect`), the
   exchange format version and the time (for display only). A record touched
   twice by one operation keeps one line. Links are written as the other
   record's permanent ID, never its local number. A document's copy places are
   logged pair by pair as the two records' permanent IDs; adding a pair that is
   already there writes nothing. Local columns (`review_status`, `source`,
   helper `batch_id`, `edited_by_person`, the actor) are not in the log.
   `core__audit` stays the local history, unchanged, and is never this format.
5. **The travel rule, declared per column** in `tables.toml`, checked when the
   module loads:
   - `travels = "never"`: the value stays on the computer where it was typed.
   - `travels = "always"`: it may travel (the default for ordinary columns).
   - `travels_when = { kind = ["allergy", ...] }`: it travels only while the
     named choice column of the same table (which must itself always travel)
     holds one of the listed choices.
   - A private (`sensitive`) column that says none of these **stays local** and
     is listed by `sync.check` as not yet reviewed, so a later exchange refuses
     to start until someone decides. Mistakes in the rule are load errors.
   Applied to the shipped modules exactly as User 1 chose in 0089: People
   "Important details" `detail` travels for allergy, condition, medication,
   care or mobility need and dietary, and stays local for access instructions
   and "other"; all four Home layout `access_details` and Vehicles
   `registration` are `travels = "never"`; Pets `microchip` is marked
   `travels = "always"`; Utilities `account_number` and `notes` (switched on
   in parallel, decision 0099) are `travels = "never"` until User 1 says otherwise. A withheld field appears in the log by **name only**:
   never its value, length, hash or anything worked out from it.
6. **A kind changed across the line (the safe minimum).** If an Important
   detail changes from a kind that stays local (access, other) to one that
   travels (a medication) without its text being typed again, the old text is
   **held on this computer** (`core__sync_held`) until the text itself is
   changed; only then does it travel. The other way (medication to access)
   simply stops the text travelling; no "clear" is sent, so a copied medical
   value is never silently erased. Neither direction is refused yet, because
   nothing is paired in stage 1. Before stage 2 pairs a computer, a deliberate
   "replace this detail" action and its wording must exist, with a warning that
   a copy already made cannot be erased remotely (STAGE1.md).
7. **Household ID and epochs.** `core__sync_state` keeps a random household ID,
   the current epoch and the exchange format version; `core__sync_epochs` keeps
   one line per epoch saying why it started. Epoch 1 starts with the first IDs.
   **Restoring a backup or undoing a restore** (decision 0079) starts a new
   epoch above both the restored copy's and the records-in-use's, so it never
   goes back, and a change log or a later copy from before the restore can never
   be mistaken for now. A restored copy keeps its IDs and revisions, which are
   consistent with its own change log. A backup from **before** stage 1 gets
   new IDs and a new epoch whose note says so; those IDs are never matched to
   the old ones. A module update that rebuilds a table without carrying its
   IDs across is noticed: its records get new IDs and a new epoch starts.
8. **Offline readers, no network.** `sync.changes` reads the log in order (what
   a later stage would send), `sync.snapshot` builds the first full copy with
   the very same filter, and `sync.check` lists everything that would stop an
   exchange (a table without IDs, a missing or repeated ID, a link to nothing,
   a table no module declares, an unreviewed private column). Nothing calls
   them on a schedule and nothing is sent.
9. **On screen**, only one line under Settings → Backups says records now have
   permanent IDs and that nothing is shared yet.

## Why we chose it
- It is the base 0089 needs: records can only be matched across computers by
  an ID that is the same everywhere, a revision, and deletes kept as markers.
- Putting the filter in front of the log, not in front of the network, means a
  value that must stay home is never stored in anything that could be sent.
- One core step, driven by the declarations, covers all 35 shipped tables and
  any module added later (another one is being promoted right now) without
  editing any module or its released migrations.
- Running it under each module's own confinement rule keeps 0055's promise
  that work on a module's tables cannot reach anything else.
- Random IDs reveal nothing: not a name, a row number, a time or a path.

## What else we considered
- **A new migration in every module** adding the two columns (STAGE1.md's first
  suggestion): every module, and every future module, would have to remember
  it; a module promoted in parallel would miss it; and the backfill still needs
  core code. Lost to the one core step.
- **Adding the columns to the generated `CREATE TABLE`** for new tables: it would
  give future tables the columns in a different position from old tables, and
  the core step is still needed for existing households. Left out.
- **UUID version 7** (time-ordered): it puts the creation time in the ID, and
  STAGE1.md asks for IDs that are not made from a time. Version 4 is fully
  random and in the standard library.
- **Reusing `core__audit` as the change log:** it holds private before/after
  values and local numbers by design; filtering it on the way out would be
  one mistake away from sending them.
- **Refusing a kind change across the line now:** it would change what
  households can do today, for a risk that only exists once a computer is
  paired. Holding the old value locally is safe now; refusing is stage 2's gate.
- **A device ID now:** a device ID kept in the data file would be cloned by a
  copied backup or USB stick. It belongs with pairing keys in stage 2, kept
  outside the database like helper keys.

## What this costs us (the downsides)
- Every record change does a few more small database reads and writes (the
  revision, the log line), and the log grows with every change. Nothing prunes
  it yet; a later stage must decide how long to keep it.
- SQLite cannot add a "not empty, unique" column in one step, so `global_id` is
  enforced by a unique index, by the one write path and by `sync.check`, not by
  a NOT NULL constraint.
- A module's own **data migration** that adds or changes rows (like Stock's
  0005) writes no log lines; new rows get IDs at the next start-up with
  revision 0. Stage 2 relies on both computers running the same module
  versions (0089) and on the first full copy, not on matching such rows.
- A hand-written table **rebuild** in a module migration must copy `global_id`
  and `row_revision` across, or its records get new IDs (noticed, with a new
  epoch, but still new IDs).
- Changes worked out from other records (an item's amount) are logged as
  effects and bump that record's revision; a later receiver must recompute them
  rather than apply them, or totals would count twice.
- There is no device ID yet, and nothing stops a restored database from being
  opened on two computers at once; both are stage 2 questions.

## How hard it is to undo
Easy while nothing is paired. The two columns are ignored by every screen,
export and the helper API; a core migration could drop `core__sync_*` and the
columns (SQLite 3.35+ `DROP COLUMN` after dropping the `__global_id__idx`
indexes), and the call in `Records._audit` and in start-up and restore removed.
No record value depends on them. Once stage 2 ships and households pair
computers, undoing it would break sync: high.

## We should revisit this if
- The change log grows enough to matter on a USB stick (then: keep only what
  members still need, with a fresh snapshot for anyone further behind).
- A module needs a table rebuild (then: a core helper that carries the IDs).
- Households want to see a record's permanent ID, or User 1 changes what travels.
