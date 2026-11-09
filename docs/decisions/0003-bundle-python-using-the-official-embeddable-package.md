# 0003. Bundle Python using the official embeddable package

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
How the 'unzip and click' folder contains everything it needs.

## What we chose
Ship Python's official 'embeddable' distribution plus our pinned libraries copied into the folder, started by a small `.bat` file. Not a single self-extracting `.exe`.

## Why we chose it
- It is a plain folder anyone can inspect, which builds trust and helps debugging.
- Single-file `.exe` builds that unpack themselves are more often flagged by antivirus software, which would hurt the first-run experience.
- Needs no install, admin rights, registry or PATH changes.

## What else we considered
- PyInstaller one-folder build: produces a friendlier `.exe`, but is more often flagged by antivirus and harder for outsiders to debug.

## What this costs us (the downsides)
- A `.bat` launcher looks less polished than an `.exe`.
- The folder is larger than a compressed single file.
- Windows shows an 'unknown publisher' warning on first run (true for both options without paid code signing).

## How hard it is to undo
Low. The folder layout is identical for both approaches, so switching is a change to the release build only.

## We should revisit this if
- Real users report antivirus problems with the launcher.
- The folder is too big for the intended USB sticks.
