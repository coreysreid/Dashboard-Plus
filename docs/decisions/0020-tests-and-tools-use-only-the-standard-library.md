# 0020. Tests and repository tools use only the standard library

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The automatic checks and tests need nothing installed beyond Python itself.

## What we chose
Use Python's built-in `unittest` for tests and write the repository tools (privacy, index, project map) with the standard library only. No test or tool dependency is added.

## Why we chose it
- Zero dependencies means nothing to pin, update or break, which fits the goal of outliving its maintainer.
- CI and a new contributor's machine need only Python.
- The same tools can run inside the portable build.

## What else we considered
- pytest: nicer output and fixtures, but one more pinned dependency in CI and for contributors.
- Shell scripts: not portable to Windows.

## What this costs us (the downsides)
- `unittest` is more verbose than pytest.
- Features such as parametrised tests are clumsier.

## How hard it is to undo
Low. Tests are plain functions that pytest can also run.

## We should revisit this if
- The test suite grows large enough that missing fixtures slow us down.
