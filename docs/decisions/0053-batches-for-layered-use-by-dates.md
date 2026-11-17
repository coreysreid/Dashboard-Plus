# 0053. Stock is kept in batches, each with its own use-by date and place

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey), at Corey's request

## In plain words
Corey asked for layered use-by dates: 3 tins of kidney beans that expire next
month and 10 that expire in six months. An item's stock is now kept in
batches. Each batch has its own amount, use-by date and place (3 tins on
Kitchen › Pantry › Shelf 3, 10 on the garage shelves). The item's amount is
the batches added up, and its Use by is the earliest batch that still holds
something. *Needs attention* warns about each batch separately, so the 3 tins
are flagged next month while the 10 stay quiet.

## What we chose
- **Adding an item** works as before: name, amount, place and use-by. That
  becomes its first batch.
- **Stock in** starts a new batch with its own use-by date and place, unless a
  batch is chosen; adding to an existing batch is a deliberate choice.
- **Using some** takes from the batch with the earliest known use-by date. A
  batch with no date comes after dated ones, never assumed fresh. If that
  batch holds too little, the household is asked to record it batch by batch,
  rather than the dashboard silently splitting the amount.
- **A stocktake** that finds a different count changes that batch; the item's
  total follows. Both changes are in the history.
- **A thrown-out batch** drops to zero and stays as history; it no longer warns
  or prints.
- **The item's own amount can't be typed over** once it has batches; it is
  always the sum, so the two can never disagree.
- **Upgrading:** every item already recorded becomes one batch with its amount,
  use-by date and place. Earlier stock in and out is linked to that batch and
  not replayed, so no amount changes. Items with nothing on hand and no date
  need no batch. The update makes a backup first, and the change runs all at
  once or not at all.
- Built as three small declarations any module can use (`total`,
  `record_name`, and batch picking in `adjusts`; DESIGN 5.7), following Lane
  B's lots design and acceptance checks.

## Why we chose it
- One use-by date per item hid the very thing a household needs to know: which
  tins to eat first, and where they are.
- Keeping the total worked out from the batches means it can never drift.
- Asking before splitting across batches keeps every change easy to read and to
  undo.

## What else we considered
- Several date fields on one item: no place per date, and no way to say which
  were used.
- Letting the item's amount be edited as well as the batches: the two would
  disagree after the first mistake.
- Splitting a large "used" amount across batches automatically: quicker, but
  harder to check and to undo; revisit with the shopping and receipt work.
- Waiting for Home layout's shared places: batches use Stock's nested places
  now and will move with them when Home layout ships.

## What this costs us (the downsides)
- One more list (Batches), and one more choice on Stock in and out ("Which
  batch"), though it can be left blank.
- Using more than the first batch holds takes two entries.
- The batch picker lists every batch; it does not yet narrow to the chosen item.

## How hard it is to undo
Moderate. The batches can be added back up into one amount per item, but the
separate dates and places would be lost. The pre-update backup restores the
old layout exactly.

## We should revisit this if
- Households find recording a split use awkward: offer to split it for them
  with the amounts shown first.
- The batch list gets long: narrow it to the chosen item while typing.
