# 0051. Medical readiness is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The household can now record its first aid kits and where each one is kept,
log when a kit was checked, and note first aid or CPR training with its renewal
date. *Needs attention* says when a kit check or a renewal is due. *Worth
filling in* asks "Is there a first aid kit at home?" until one is added, then
asks where each kit is kept and when it will next be checked. A printable
"First aid at home" sheet shows the kits, their full places (Car › Car boot) and
who has trained.

## What we chose
- Promoted from Lane B's final draft (`workbench/drafts/medical/`, now removed;
  its notes and acceptance checks are in git history). Tables, wording and the
  sheet are unchanged; the draft's two working migrations became one first
  migration because the draft was never released.
- No medical advice and no fixed check interval: the household chooses its own
  next check date. Checks are history; the kit's own "Check again by" date is
  the one reminder, so old checks never raise stale reminders.
- Allergies, conditions and medicines stay in People; kit supplies, minimums and
  use-by dates stay in Household stock. Medical links to both.
- Two small core changes:
  - A gap can use `none = {}` to ask when a table has nothing in it at all.
  - The example loader accepts a history table with no short text column
    (kit checks are only links, dates and a note).

## Why we chose it
- Medical was planned for M3 and the draft was finished and checked against the
  shipped People and Stock modules. "Where is the first aid kit?" is a question
  every household should be able to answer quickly.

## What else we considered
- Adding a compulsory "check name" so the loader could name kit checks: refused,
  it adds typing for the household only to suit a tool.
- Linking each kit to its Stock items: duplicates Stock and needs a new
  cross-module rule; revisit if households ask.
- Working out the next check date automatically: there is no single right
  interval, and inventing one would be asserting, not asking.

## What this costs us (the downsides)
- After logging a check, the household also has to update the kit's dates by
  hand until a one-step "Complete check" exists.
- One more module to maintain.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept), or remove the folder.

## We should revisit this if
- Households find the two-step check (log it, then update the kit) annoying.
- Home layout's shared places replace Stock places: kit places must move with
  Stock's in one backed-up change.
