# 0022. INDEX.md format and the rules the checker enforces

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The exact shape of the folder summaries, so a computer can keep them honest.

## What we chose
Each `INDEX.md` has a heading line starting with the folder name, then one markdown table with the entry in the first column. The checker requires every non-hidden file and subfolder to be listed, rejects entries that no longer exist, rejects the placeholder text, and requires each Python file to start with a one-line docstring that its row quotes. The normal limit is 25 lines. `docs/decisions` has a higher limit (80) because it is a catalogue. A row may use a pattern such as `m*.py` to cover a family of similar files. A markdown link in the first column is accepted.

## Why we chose it
- A fixed shape makes the summaries easy for agents to skim and easy to generate into `PROJECT_MAP.md`.
- Quoting the docstring ties each description to the code, so it cannot drift silently.
- The override and pattern rows keep the 25-line goal for normal folders without making the decision log unreadable.

## What else we considered
- Free-form prose indexes: nicer to read, impossible to verify.
- One limit for every folder: the decision log would have to be split artificially.

## What this costs us (the downsides)
- A small writing chore for every new file (the `--skeleton` option lists the missing rows).
- Exceptions to the limit could creep; each one lives in `tools/check_indexes.py` where it is visible.

## How hard it is to undo
Low. It is one script and documents.

## We should revisit this if
- Contributors keep fighting the checker.
- More than a couple of folders need a limit override.
