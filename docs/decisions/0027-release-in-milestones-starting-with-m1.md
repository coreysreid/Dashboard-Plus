# 0027. Release in milestones, starting with M1

- **Status:** Accepted
- **Date:** 2026-11-08
- **Decided by:** Corey (M1 scope), Claude (sequencing)

## In plain words
Instead of building all of v1 before anyone can use it, we ship five smaller
releases. The first (M1) covers People and Household stock, the shared
"running low" and "expiring soon" views, days of water, the emergency sheet and
the portable folder.

## What we chose
The milestones M1 to M5 in `docs/ROADMAP.md`, each with its own done list. The
portable Windows build is the first M1 task. M1 includes a simple automatic
backup and backup on safe close, because a USB stick without a backup is a risk
from the first day; restore and export screens follow in M2. Data entry in M1 is
typing only.

## Why we chose it
- v1 had grown to ten modules and fifteen core features; nothing would be usable
  for a long time.
- The question loop and outcomes need weeks of data, so building them first
  would ship features that stay silent.
- The portable build is the riskiest promise; finding problems in week one is
  far cheaper than at the end.
- Early use by real households tells us what to build next.

## What else we considered
- Build all of v1, then release: rejected for the reasons above.
- Start with the question loop as the distinctive feature: rejected, because it
  needs history that does not exist yet.

## What this costs us (the downsides)
- Early users see a narrower product than the vision describes.
- Some core work is revisited as later milestones add needs.
- The milestone plan itself needs keeping current.

## How hard it is to undo
Easy. It is a plan; later milestones can be reordered.

## We should revisit this if
- M1 testers do not keep using it after four weeks.
- A later milestone turns out to be a prerequisite for M1 value.
