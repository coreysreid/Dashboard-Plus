# 0114. Bundle the time zone data so household days work on Windows

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Windows does not come with the world's time zone list that Python needs, so
the Pet feeding log could put a bowl filled at 7am Brisbane time on the wrong
day. We now ship that list (the `tzdata` package) inside Dashboard Plus, so
"today" is the household's own day on every computer.

## What we chose
Add `tzdata==2025.2` to `requirements.txt`, locked with its PyPI checksums in
`requirements.lock`. The Windows and Mac builds already install every locked
library, so the data travels inside the app. Python's own `zoneinfo` uses the
computer's list where there is one (Linux, Mac) and falls back to `tzdata`.

## Why we chose it
- The CI Windows run failed three pet feeding tests (decision 0110): a time
  in Sydney or New York landed on the computer's day instead.
- `tzdata` is published by the Python core developers, is data only (no code
  runs at install), and is the documented fallback for `zoneinfo`.
- The household's day matters beyond feeding: dates with times (0111) and any
  later daily totals use the same rule.

## What else we considered
- Using the computer's clock on Windows: wrong whenever the household's time
  zone setting differs from the computer's, and silently so.
- Writing our own offset table: daylight saving rules change; we would fall
  behind.

## What this costs us (the downsides)
- About 1.5 MB more in the download.
- The rules are only as new as the pinned version; a government that changes
  its daylight saving dates needs a `tzdata` update and a new build.

## How hard it is to undo
Easy: remove the line and relock. Windows would go back to the computer's
clock for household days.

## We should revisit this if
- A household reports a feeding or reading on the wrong day after a daylight
  saving change, or `tzdata` stops being maintained alongside Python.
