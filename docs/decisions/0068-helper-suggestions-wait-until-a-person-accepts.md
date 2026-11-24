# 0068. Helpers' suggestions wait in their own place until a person accepts them

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by User 1)
- **Refines:** DESIGN sections 3 and 8 (which had suggestions stored as `needs_review` rows in the module's own tables)

## In plain words
When a helper suggests a record, it is kept on a waiting list of its own. Nothing in your real records changes, and no
count or total moves, until a person presses Accept on the Review page. Only then is the record added, in the normal way,
and it counts.

## What we chose
- Suggestions are stored in core tables `core__helper_batches` (one per request: who, why, retry key) and
  `core__proposals` (one per suggested record, with the values exactly as sent, and a status of pending, accepted or
  rejected).
- Before storing, every suggestion is tried for real on the normal create path inside a transaction that is always rolled
  back (a "dry run"), so a suggestion that could not be added is refused straight away, with a plain reason.
- On Accept, the record is created by the normal path in one transaction: stock in and out change the item, batches add up,
  history records the helper as the creator. The new record is marked `edited_by_person` so a helper can never change it.
  If the world has changed so it can no longer be added (for example, stock has since been used), the suggestion stays
  pending with the reason written on it, and nothing is changed.
- `review_status` stays unused by helpers; all records written through Accept are `confirmed`.

## Why we chose it
- Storing suggestions as `needs_review` rows in module tables would have been unsafe: creating a row applies its side
  effects at once (stock counts move, batches add into totals), and lists, watch views, sheets and the home page do not
  filter on review status.
- A separate place cannot leak into any total by accident, and "reject" means "nothing was ever written".

## What else we considered
- `needs_review` rows with every reader taught to skip them: many places to get wrong, now and in every future module.
- Storing the cleaned values: money would be scaled twice on Accept; raw values are re-checked at Accept time instead.

## What this costs us (the downsides)
- A suggestion's values are checked twice (when sent, and again on Accept); the second can fail if things changed.
- Reviewing shows values read from the stored text, not from a real row.

## How hard it is to undo
Medium. The three tables hold only helper suggestions; accepted records live on in the module tables.

## We should revisit this if
- We add suggestions to change or delete existing records: they will need the same waiting place plus a stale-value check.
