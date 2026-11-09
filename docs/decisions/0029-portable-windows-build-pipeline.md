# 0029. How the portable Windows folder is built

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
GitHub builds the unzip-and-click folder automatically, then starts it on a real
Windows machine, checks that it answers, and closes it safely. Every downloaded
file is checked against a known checksum.

## What we chose
- `tools/build_portable.py` downloads the official embeddable Python 3.12.10,
  checks its checksum against `tools/portable.toml`, installs the locked Windows
  libraries with their checksums verified, copies our code and modules, and
  writes `Open Dashboard.bat`, `Close Dashboard safely.bat` and `READ ME FIRST.txt`.
- The bundled Python's `._pth` file lists only its own standard library, our
  `lib` folder and our `src` folder, so it ignores any Python installed on the
  computer and does not read environment settings.
- The data folder sits beside `app/` and is passed explicitly by the launchers;
  it is never shipped in the zip.
- CI builds the zip on `windows-latest`, runs `tools/smoke_test_portable.py`
  (start, home page, forged-host refusal, safe close), and keeps the zip for 14
  days for testers.
- In M1 the launcher shows a small console window that explains the program is
  running. Hiding it is a later polish once closing from the page is proven.
- Release builds (`--release`) refuse to run without a pinned checksum. The
  Python checksum was pinned from the first CI downloads (two independent
  Windows builds produced the same value), because python.org is not reachable
  from the development environment. Every build now verifies it.

## Why we chose it
- Building and testing on Windows in every change finds packaging problems in
  week one, not at the end (see decision 0027).
- Checksums stop a tampered or corrupted download from being shipped.
- Python 3.12.10 is the last 3.12 release with official Windows downloads and
  matches the Python version CI tests with.

## What else we considered
- PyInstaller: rejected in decision 0003.
- Building only when a release is tagged: rejected, because problems would be
  found late.

## What this costs us (the downsides)
- The console window looks less polished than a desktop app.
- Python 3.12 receives security fixes only as source after 3.12.10; moving to a
  newer Python needs a new pinned version and checksum.

## How hard it is to undo
Low. The build is one script and one CI job.

## We should revisit this if
- Antivirus software flags the folder for testers.
- Start-up from a USB stick is slow enough to annoy people.
