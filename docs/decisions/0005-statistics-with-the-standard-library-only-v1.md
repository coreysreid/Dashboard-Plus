# 0005. Statistics with the standard library only (v1)

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The maths behind 'is this related' uses only what comes with Python.

## What we chose
Implement Pearson, Spearman, lagged correlation, RMSE, change-point detection, day-of-week averages and false-discovery correction using the Python standard library. Significance for correlations uses a permutation test.

## Why we chose it
- Keeps the portable folder small and the dependency list short, which suits the longevity goal.
- These are short, well-known formulas that we can test against hand-computed answers.
- Fewer pieces that can break when Python or Windows changes.

## What else we considered
- Add a pinned numerical library: faster and a wider choice of methods, but heavier and one more thing to keep working.

## What this costs us (the downsides)
- Slower on very large series (not expected in a household).
- We maintain the formulas ourselves, so tests must be strong.
- Fancier methods (seasonal decomposition, forecasting) would be harder.

## How hard it is to undo
Low. The Analysis module hides the implementation behind its own functions.

## We should revisit this if
- Analysis is visibly too slow.
- We want forecasting methods that are impractical without a library.
