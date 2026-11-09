# 0043. Stock in and out updates the item's count automatically

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
When you record that something was bought, used, expired, thrown away or given
away, the item's "How many" changes by itself. Deleting the entry puts the count
back. You can't take out more than you have; to fix a wrong count, you edit the
item directly.

## What we chose
- A general core feature: a table can declare `adjusts` (DESIGN 5.3). The core
  applies the change inside the same save, records it in the linked record's
  history, corrects it when an entry is changed, undoes it when an entry is
  deleted, and re-applies it when an entry is restored.
- Household stock gains **Stock in and out** (item, reason, how many, date
  defaulting to today, notes). "Bought or added" adds; used, expired, thrown away
  and given away take away.
- Going below zero is refused, with the amount actually left.
- Stocktakes are a direct edit of the item's count, not a movement, so every
  movement can always be undone exactly.
- Each item's page has "Add to stock in and out" with the item filled in, and
  saving returns to the item so the new count is visible.

## Why we chose it
- Journey J2 (the shopping comes home) needs stock to go up without retyping
  totals, and expired or thrown-away entries are what will later measure waste
  (outcomes, M4).
- Making it a core feature declared in files keeps modules code-free; Pets can
  use the same thing for food.

## What else we considered
- Only ever editing the count: quick, but no record of why it changed, so no
  waste figures.
- A "set to" stocktake movement: cannot be undone exactly once later entries
  exist.
- Calculating counts from movements alone: slower, and first entries would need
  an "opening balance" step.

## What this costs us (the downsides)
- Two ways to change a count (a movement or a direct edit); the item history
  shows both.
- A wrong earlier movement can block a later "used" entry until the count is
  corrected.

## How hard it is to undo
Medium. Removing it would leave movements recorded but no longer applied.

## We should revisit this if
- Testers find the refusal below zero frustrating.
- Waste figures need more detail than reasons give.
