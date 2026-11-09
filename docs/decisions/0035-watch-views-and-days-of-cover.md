# 0035. How running low, expiring soon and days of cover are worked out

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The home page shows how many days of water (or any supply) the household has,
and lists what is running low and what is about to expire. Every number shows
how it was worked out, and nothing is sent anywhere.

## What we chose
- A module opts in with a `watch` section in `tables.toml` (DESIGN 5.1); the
  module checker explains mistakes in it like any other.
- **Running low:** quantity below minimum, biggest shortfall first. A blank
  quantity counts as zero; a blank minimum means "not watched".
- **Expiring soon:** dates already past or within `warn_days` (30 by default),
  soonest first, in words ("expires today", "expired 2026-05-30 (2 days ago)").
- **Days of cover:** total of matching rows ÷ (people × daily need per person +
  pets × daily need per pet). People come from the People module (those marked
  as living here) when installed, otherwise from the household size setting.
  The page shows the sum in words and how much more is needed to reach the
  target, and always says the daily figures are a starting point and local
  advice comes first. With no household size yet, it asks for one instead of
  guessing.
- Deleted records never count.

## Why we chose it
- Showing the working builds trust and lets people spot a wrong entry.
- Asking rather than guessing the household size follows "ask, don't assert".
- Keeping it declarative means medication, pet food or seeds can use the same
  views later with no code.

## What else we considered
- Alerts or notifications: out of scope; the program does not send messages.
- Assuming a default household size: a wrong number would look authoritative.

## What this costs us (the downsides)
- Days of cover adds quantities as they are recorded, so units must be
  consistent within a supply (for example every water row in litres).
- Pets count from a setting in M1 until the Pets module exists.

## How hard it is to undo
Low. The calculations are one file, `src/dashboard/core/watch.py`.

## We should revisit this if
- People record supplies in mixed units and the totals mislead them.
- Testers want different warning windows per item.
