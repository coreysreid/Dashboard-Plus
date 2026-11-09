# 0041. The tests folder index may be longer than 25 lines

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The summary page of the tests folder may list up to 40 entries instead of 25,
because both agents add tests there and it is a list of similar things.

## What we chose
`tools/check_indexes.py` allows 40 lines for `tests/`, as it already allows 80
for `docs/decisions/` (decision 0022). Families of similar tests still use one
pattern row, such as `test_module_*.py`.

## Why we chose it
- Combining Lane A's and Lane B's work took `tests/INDEX.md` to 26 lines.
- Splitting tests into sub-folders would change how every test is run, for no
  benefit to a reader.

## What else we considered
- More pattern rows: loses the one-line description of each test file.
- Sub-folders for tests: more churn than value now.

## What this costs us (the downsides)
- One more exception to the 25-line rule.

## How hard it is to undo
Easy. One number in one file.

## We should revisit this if
- The tests index passes 40 lines; then group tests into folders.
