# 0116. Helper words for moving in: an old balance is not a purchase

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
When a household moves an old tracker in with an assistant, the assistant is now told that a number like "Rice:
12 tins on shelf" is not something bought. It must ask whether the number is a new purchase, stock already on
hand or an amount used, and let the person count the batch in Dashboard Plus when the difference is unknown. It
is also told to ask whether a receipt is already inside the old count, that a price read from a receipt is for
checking only, to read the guide again before each batch, and to report sent, accepted, waiting and refused rows
honestly. Only words changed; no new record type, reason or permission.

## What we chose
- The generated starting message (`web/helper_guide.py`, `GET /api/v1/guide`) no longer tells a helper to send
  `bought` for any item already in Stock. It sends `bought` only for a purchase the household confirms with its
  real date and amount, and points a starting or corrected balance at the path that already exists: Count this
  batch (decision 0070, `counted_more` / `counted_less` need a chosen batch), done by the person or suggested only
  after they confirm the batch and the difference.
- Added sentences: tracker plus receipt may be the same goods (ask; if unsure, leave the line for Review); a source
  price is not purchase-price history or a saved spending total; read the guide again before each batch and after
  a refusal; before finishing, read the batches and their rows and say sent, accepted, waiting, refused, unknown.
- The connector's `dashboard_suggest_new_records` and `dashboard_how_to_help` descriptions and `openapi-v1.json`
  carry the same four points. Tests hold the new sentences and check the old misleading one is gone.

## Why we chose it
- Sending an old balance as `bought` adds it on top of what is already recorded: a wrong count, quietly.
- The paths needed already exist; wording is the smallest safe fix (Lane B's checked draft, batch 21 item 104).

## What else we considered
- Refusing `bought` for an existing item in the core: it would also block real purchases.
- Letting the helper suggest stocktake corrections freely: it cannot know the batch or the difference alone.

## What this costs us (the downsides)
- The guide and connector text are longer, so an assistant may skim past them; nothing in the core enforces them.
- An assistant that ignores the words can still send a wrong `bought`; the person sees it on Review.
- Wording only: no check yet compares a receipt with an old count.

## How hard it is to undo
Easy. Revert the sentences in `helper_guide.py`, `connector/tools.py`, `openapi-v1.json` and their tests.

## We should revisit this if
- Households still see doubled Stock counts after a move, which would point to a core check instead of words.
