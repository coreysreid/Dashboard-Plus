# 0015. Household stock module and watch views in v1

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (scope change requested by Corey; technical shape chosen by Claude)

## In plain words
The first version centres on a resilient home: pantry stock with reorder
levels, shopping receipts, emergency water, and tools and hardware. Wine is
only a small example.

## What we chose
Add a files-only **Household stock** module to v1, and add a small, generic
"watch views" feature to the core (running low, expiring soon, days of
supply). Wine stays, but is described as a minor example.

## Why we chose it
- It is what Corey set out to build and what makes the product worth using.
- "Below a minimum" and "past a date" are generic, so they belong in the core
  once rather than being rebuilt per topic. This keeps the core free of any
  topic-specific knowledge.
- It is a stronger test of the design than wine: if files alone can express
  stock, locations, receipts and supply cover, the platform idea holds.

## What else we considered
- Put the low-stock and expiry logic inside the Household stock module only:
  simpler, but every other module (medication, pet food) would have to copy it.
- Wait until after v1: rejected, because it is the main selling point.

## What this costs us (the downsides)
- The v1 core grows slightly (three declarations and two shared views).
- More to build before the first release.
- Default daily-need figures could be taken as official advice; the interface
  must say they are a starting point and local advice comes first.

## How hard it is to undo
Low to medium. The views are read-only features driven by declarations;
removing them would not alter stored data.

## We should revisit this if
- Households do not use the watch views, or find "days of cover" confusing.
- The declarations needed for supply cover become too complicated for files alone.
