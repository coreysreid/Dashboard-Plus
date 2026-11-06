# 0021. CI runs on Windows and Linux, files use LF line endings

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Every change is checked on the operating system the product targets first (Windows) and on Linux.

## What we chose
GitHub Actions runs the privacy check, index check, project-map check and tests on both `windows-latest` and `ubuntu-latest` with Python 3.12. Third-party actions are pinned to a major version tag. `.gitattributes` forces LF line endings so generated files compare equal on both systems. Workflow permissions are read-only.

## Why we chose it
- Windows is the first-class target, so it must be tested, not assumed.
- Line-ending differences otherwise make generated files look stale on Windows.
- Read-only permissions limit what a compromised step could do.

## What else we considered
- Linux only: faster, but misses Windows-specific path and encoding problems.
- Pin actions to exact commit SHAs: safer against a hijacked tag, but harder to read and update; we can tighten later.

## What this costs us (the downsides)
- Two jobs per change use more CI minutes.
- Pinning to a major tag trusts the action publisher not to move the tag.

## How hard it is to undo
Low. It is a workflow file and one attributes line.

## We should revisit this if
- CI is slow or flaky.
- A pinned action is compromised, in which case switch to commit SHAs.
