# 0046. Show the water estimate's daily amount, and whether the second backup worked

- **Status:** Accepted
- **Date:** 2026-11-16
- **Decided by:** Claude (technical decision delegated by User 1), from Lane B's product review

## In plain words
The home page's water estimate now says what it assumes ("Based on 3 litres
per person a day, 1 per pet. Check your local authority's advice."). Settings
now says when each backup was last made, and if the copy on the computer
failed, both Settings and the home page say so plainly, with the reason and
when the last good copy was made.

## What we chose
- The days-of-water card on the home page shows its daily amounts. The full
  working was already on the Needs attention page; the home card is where people
  actually read the number.
- Every backup writes a small `status.json` in the data folder's `backups`
  folder: when the main copy was made, and whether the second copy worked
  ("ok", "failed" with a plain reason, or "off"). The last good second copy is
  remembered across failures.
- Settings shows "Copy in your data folder" and "Second copy on this computer"
  separately. A failure appears there and as a short warning on the home page.
- The 3 litres a day figure itself is not changed in this step.

## Why we chose it
- Lane B's review (workbench/reports/2026-11-13-product-swot.md) found that the
  two most reassuring numbers, days of water and "backed up", hid their
  assumptions and failures. US guidance (CDC) is about one gallon, roughly 3.8
  litres, a person a day, so a US household was shown more cover than local
  advice would give.
- A failed second copy was only written to a log file nobody reads, which is
  worse than no second copy: the household believes it is protected.

## What else we considered
- Changing the water figure per country now: it needs cited country data
  (country packs, M3) and must not silently change an existing household's
  numbers. Showing the basis is the honest first step.
- Checking the second folder by looking at its newest file: simpler, but the
  folder can be shared by more than one copy of the program, so it could be
  fooled; recording the outcome is exact.

## What this costs us (the downsides)
- One more line on the home card.
- A small extra file in the backups folder.

## How hard it is to undo
Easy. Remove the line and the status file; nothing else depends on them.

## We should revisit this if
- Country packs arrive: the basis line should then name its source and date.
- Households want to set their own daily water amount.
