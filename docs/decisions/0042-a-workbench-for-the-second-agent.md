# 0042. The second agent works only in a workbench folder, as checker and drafter

- **Status:** Accepted (refines decision 0034)
- **Date:** 2026-11-09
- **Decided by:** Claude (direction from Corey: use the second agent to check and draft)

## In plain words
The second agent now has a folder of its own, `workbench/`. It tests the
product like a household would, writes reports, drafts new modules and does
research there. The first agent builds the program and moves finished drafts
into place. Because they never edit the same files, their work cannot clash.

## What we chose
- Lane B edits only `workbench/`: `STATUS.md` (its status and messages),
  `reports/` (findings), `drafts/` (draft modules) and `research/`.
- `workbench/` is left out of `PROJECT_MAP.md`, so Lane B's changes never touch
  a file Lane A also changes.
- `tests/test_workbench_drafts.py` (owned by Lane A) checks every draft module
  automatically, so Lane B never edits `tests/`.
- `tools/check_all.py` runs every check with one command, for both lanes.
- A written "Definition of done" for every pull request, and commit messages
  from Lane B start with `Lane B:`.

## Why we chose it
- Reviewing Lane B's first branches found three avoidable problems: a stale
  project map, a clash in a shared index, and no pull requests.
- A checker who did not build the feature finds different problems from the
  builder, and draft modules with feedback are a fast way to fine-tune modules.

## What else we considered
- Keep shared files with "add rows only": still clashed in practice.
- One agent only: slower, and loses the independent check.

## What this costs us (the downsides)
- Lane A must promote drafts and act on reports, which takes its time.
- The workbench holds unfinished material in the public repository (made-up
  data only, as everywhere).

## How hard it is to undo
Easy. It is a folder and a working agreement.

## We should revisit this if
- Reports go unanswered or drafts pile up unpromoted.
- Lane B needs to change the program to do its job.
