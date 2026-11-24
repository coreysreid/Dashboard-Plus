# 0070. Stocktake corrections: count one batch, save the difference

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
On a batch, **Count this batch** asks how many you counted, shows what will change ("You counted
5 tins; 3 tins are recorded here. This adds 2 tins as a stocktake correction."), and on Save
records the difference as its own line in Stock in and out. The count is never added on top, and
it is never called a purchase, a use or waste.

## What we chose
- Two new Stock in and out reasons, **Stocktake: more than recorded** (`counted_more`, adds) and
  **Stocktake: fewer than recorded** (`counted_less`, takes away). The record holds the positive
  difference, the batch, the item, the day, and a note "Stocktake: counted 5; 3 were recorded."
- A declarative switch in `tables.toml`, checked when the module loads:
  `counts = { more = "counted_more", less = "counted_less", note = "notes" }` in the `adjusts`
  section (needs `belongs_to`; `more` must add, `less` must not; `note` is an optional text column).
- Core support in `records.py`: `check_count` (what a count would change, nothing saved) and
  `count_batch` (save it in one database transaction). A correction reason with no batch chosen
  is refused: it never starts a new batch and never guesses which use-by date was wrong.
- Screens in `web/count.py` and `count.html`: count form, review, and the result on the batch's
  own page; a **Count** link next to each batch on the item. The item total has no count form.
- **Out-of-date reviews:** the review carries the amount the person saw. Saving compares it with
  the batch now, inside the transaction, and refuses with "This batch now shows 4 tins, so the count
  you reviewed is out of date." If the batch already holds the counted amount, nothing is saved, so
  a second click on Save (or a reload) adds nothing.
- Undo, edit, delete and restore use the existing `adjusts` rules: only the difference is
  reversed or reapplied, once, and an undo that would take a batch below zero is refused.
- No migration: choice values are not stored in the table's structure, and old records are
  untouched. A direct edit of a batch's "How many" stays possible and keeps its own history, but
  is not turned into a correction; its help now points to Count this batch.

## Why we chose it
- A difference (delta) keeps every later stock in and out independently reversible; a "set to 5"
  record would have to replay everything after it on undo.
- Comparing the amount seen with the amount now is enough for a count: if it is the same, saving
  the difference yields exactly what was counted, whatever happened in between. It needs no new
  version column and no change to existing tables.
- Declaring the reasons keeps the core topic-neutral; another module with batches can reuse it.

## What else we considered
- **A "set the batch to" reason** whose amount is the count: refused by Lane B's design; undoing
  it is ambiguous once later movements exist.
- **A version number on every batch** plus a one-time token per review: stronger, but needs a
  migration of the batches table for no gain a household could see; the amount check plus "already
  shows" covers stale reviews and double clicks.
- **Before/after columns on Stock in and out:** a migration for data the batch's history and the
  note already show.

## What this costs us (the downsides)
- The list shows the reason ("fewer than recorded") and a positive amount, not "−2"; the signed
  figure appears only in the message after saving.
- The before/after snapshot lives in the note, which a person can edit; the history keeps the
  original.
- Waste or shopping summaries do not exist yet; when they do they must leave out both counted
  reasons.
- A cross-batch stocktake (counting the whole item) is not offered; each batch is counted on its own.

## How hard it is to undo
Easy. Remove `counts` and the two reasons (existing corrections would then need a new reason),
`web/count.py`, `count.html` and the two methods in `records.py`.

## We should revisit this if
- Households want to count everything on a shelf in one go, or need to backdate a count.
- Several people count the same batch at once often enough that a version number is worth it.
