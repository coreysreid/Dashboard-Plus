# 0088. Helper limits hold under simultaneous requests; other API versions refuse plainly; "1 tin"

- **Status:** Accepted
- **Date:** 2026-11-19
- **Decided by:** Claude (technical decision delegated by User 1), from Lane B's batch 14 checks (items 55 and 56)

## In plain words
Three small fixes from Lane B's checks. A helper sending two requests at the
same moment can no longer slip past its daily limit or the Review queue cap.
An address such as `/api/v2/me` now gets a plain "not found" answer instead of
a web page. And a stocktake count one more or less than recorded reads
"This adds 1 tin", not "1 tins".

## What we chose
- **Limits under a lock.** The daily limit and the Review queue cap (decision
  0085) are checked twice: once early, so a full helper is refused quickly, and
  again inside the write transaction (`BEGIN IMMEDIATE`), which only one
  request can hold at a time. The second check is the one that decides.
- **Other API addresses.** Any path under `/api/` other than `/api/v1/…`, and
  the program's own `/api/ping` and `/api/shutdown`, answers 404 JSON
  `not_found` ("There is no such helper address. Helpers use /api/v1/.")
  instead of sending the caller to the start page.
- **Singular units on the count pages.** Amounts there go through the same
  `unit_for` as batch names (decision 0053), so 1 reads "1 tin" or "1 litre";
  units the household typed itself are left as typed.

## Why we chose it
- The caps exist to protect the Review screen; a cap that two quick requests
  can pass is not a cap.
- A helper that guesses a newer API version should get an answer it can read.
- "1 tins" reads as a mistake and makes people doubt the amount.

## What else we considered
- A process-wide lock in Python around submit: the database's own write lock
  already serialises writers, including any future second process.
- Lane B's wording "This adds 1 to this batch": kept as the fallback idea; the
  amount with its unit is clearer where a singular is known.

## What this costs us (the downsides)
- Two counts are run for each accepted request (cheap: both use indexes).
- Units outside the known list still read as typed, for example "1 kgs" if a
  household typed "kgs".

## How hard it is to undo
Easy: each change is a few lines in `core/proposals.py`, `web/app.py` and `web/count.py`.

## We should revisit this if
- Helpers routinely hit the caps; the limits themselves may then need a Settings choice.
