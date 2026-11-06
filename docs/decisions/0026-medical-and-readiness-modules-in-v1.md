# 0026. Medical and Readiness modules in v1

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
First aid and "have you thought about…?" planning are part of the first release, not left for later.

## What we chose
Ship two files-only modules in v1: Medical (first aid kit checks, first aid and CPR training and renewals, medical contacts, built on Household stock and People) and Readiness (prompts, plans, drills, coverage, country packs). Medical uses the shared running-low and expiring-soon views, so it needs no special code.

## Why we chose it
- Corey named medical readiness as a pillar and helping people think as another.
- Both reuse existing core features, so the cost is mostly content.
- They are a strong test of the "files only" design.

## What else we considered
- Defer both until after v1: rejected, because they carry much of the value.
- Fold Medical into Household stock: loses training and kit-check behaviour.

## What this costs us (the downsides)
- v1 grows: ten modules and one more core feature. Sequencing must keep the core first and the modules small.
- Writing good prompts and packs is research-heavy.
- Medical content carries a duty of care: we only record and link, never instruct or diagnose.

## How hard it is to undo
Low. Both are optional modules.

## We should revisit this if
- The v1 schedule slips because of content work, in which case ship a small prompt set first.
- Users treat the program as medical advice.
