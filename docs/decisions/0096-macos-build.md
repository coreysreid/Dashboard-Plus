# 0096. An unsigned Mac app preview, with records in Application Support

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by User 1), from Lane B's research `workbench/drafts/macos/MACOS.md`

## In plain words
There is now a Mac version for testing: a normal-looking `Dashboard Plus.app`
that GitHub builds and starts on an Apple silicon Mac for every change. It is
not signed by Apple yet, so a Mac warns before opening it, and nobody has tried
it on a real Mac yet. Its records live in your Mac account's own private folder
for program data, not inside the app, so replacing the app never touches them.

## What we chose
- **Where the records live.** With no `--data`, a program running from inside a
  `.app` on a Mac keeps its data folder in
  `~/Library/Application Support/Dashboard Plus/` (`src/dashboard/data_location.py`),
  made with permissions 0700 (only this account). Everything already in that
  folder works as on Windows: `run/dashboard.json`, `run/helper-address.json`
  (so on a Mac the connector's address file is
  `~/Library/Application Support/Dashboard Plus/run/helper-address.json`),
  `config.toml`, backups and reports. A `--data` that points inside the app is
  refused, in plain words, without writing anything there. A given `--data`
  always wins. Today the program reads no data path from `config.toml` (that
  file lives inside the data folder, so it cannot choose it); `paths.data_dir` in
  `config.example.toml` is not used, and this decision does not change that.
- **Only inside the app, not on every Mac.** Running from source on a Mac
  (`python -m dashboard`) keeps the old default, `./data`, so nobody who already
  runs it that way finds their records "missing". The app is detected from the
  program's own location (a folder named `<name>.app` with `Contents` inside),
  which tests fake on any system.
- **`tools/build_macos.py`**, run on a Mac, builds `Dashboard Plus.app` for that
  Mac's processor (`arm64` or `x86_64`, or `--arch`) and zips it with a read-me
  and the licence as `Dashboard-Plus-<version>-macos-<arch>-unsigned.zip`:
  - The Python is python-build-standalone's relocatable CPython 3.12.10 (the
    same version as the Windows folder, release 20250409), one download per
    processor, pinned with sha256 in `tools/macos.toml`. The checksums are the
    ones published in that release's `SHA256SUMS`, and matched our own download
    on 20 November 2026. The build always refuses a file that does not match.
    pip is removed from the copy.
  - The locked libraries are installed for macOS 11 on that processor with
    every checksum verified (MarkupSafe's wheel is universal; the rest are pure
    Python). A `dashboard-plus.pth` file points the bundled Python at the app's
    own `lib` and `src` only; the launcher uses `python3 -I`, which ignores any
    Python settings and user folders on the Mac.
  - `Contents/MacOS/Dashboard Plus` is a short `/bin/sh` launcher: it starts the
    server in the background, waits until it reports it is running (up to 20
    seconds) and ends, so opening the app again reopens the browser page through
    the program's existing "already open" path. If start-up fails, a macOS alert
    shows the last lines of the message. `Info.plist` sets `LSUIElement`, so
    there is no Dock icon or menu; *Save and exit* on the page closes it.
  - On a Mac the zip is made with Apple's `ditto`; elsewhere (tests) it keeps
    permissions and links.
- **CI:** a `macos-latest` job (Apple silicon) installs the locked libraries,
  runs `tools/check_all.py`, builds the app, starts it through its own launcher
  with `tools/smoke_test_portable.py` (wizard shown, browser without the launch
  link and forged host refused, safe close, default data folder is Application
  Support), and keeps the zip for 14 days. It uses no secrets.

## Why we chose it
- Application Support is where macOS expects a program's per-account data, and
  Lane B's research recommends it. Keeping records out of the app means the app
  can be replaced, and it still works when macOS runs a freshly downloaded app
  from a temporary read-only copy ("app translocation"). Writing inside a signed
  app would also break its signature later.
- python-build-standalone is the closest Mac match to decision 0003's
  embeddable Python: a plain, inspectable folder, no freezing tool, no new
  library. The Windows build and the Mac build ship the same Python version.
- A shell-script launcher needs no compiler and no new dependency, and its every
  line is readable. Building on the Mac it runs on is the only way to get the
  right native pieces, and CI proves it on every change.

## What else we considered
- **Application Support on every Mac, also when run from source:** rejected for
  now, because it would silently move existing source users' records.
- **PyInstaller or py2app:** rejected as in decision 0003 (a new tool, harder to
  inspect); either could replace the launcher later without moving data.
- **A universal (both-processor) app now:** python-build-standalone ships the
  two processors separately, so this needs merging every native file with
  `lipo` and testing both. Two clearly labelled builds come first; CI builds the
  Apple silicon one because `macos-latest` is Apple silicon.
- **A USB-stick style Mac folder with data beside the app:** not offered first
  (Lane B's research); a removable data folder can still be given with `--data`.
- **Ad-hoc signing the app in the build:** left out. Without a Developer ID it
  does not stop the Gatekeeper warning, and the bundled Python's program and
  library already carry the ad-hoc signature Apple silicon needs to run any
  code (checked in the download; CI shows it starts).

## What this costs us (the downsides)
- **Unsigned and not notarised.** macOS warns on first open; testers must use
  *Open Anyway* in System Settings, Privacy & Security (or Control-click, Open on
  macOS 14 and earlier). We must not ask households to do this for a release.
- **Which Macs were tested:** none by a person. Only GitHub's `macos-latest`
  Apple silicon runner builds and starts the app, from the build folder (not a
  downloaded, quarantined zip). The Intel build and the launcher's failure
  alert have never run. This session could not run macOS at all; the CI job is
  the proof. Here the Apple silicon app was assembled from the real download
  (on Linux, so not started), and the same layout and launcher were started,
  checked and closed with a Linux copy of the same Python.
- No app icon (the plain default icon), no Dock icon or Quit menu, and no Mac
  menu-bar way to close it: only *Save and exit* on the page.
- The launcher waits up to 20 seconds on a slow start before leaving the server
  to finish; a failure after that has no alert (the log and report files in the
  data folder still record it).
- The second backup copy on a Mac stays where it already was,
  `~/.local/share/dashboard-plus/backups` (a hidden folder), not
  Application Support; moving it is a separate decision.
- The app is about 46 MB unzipped (a 15 MB zip), mostly Python's standard
  library (Tk and other unused parts included).
- **Left for a real release:** a Developer ID Application certificate (kept as a
  CI secret, never in the repository), hardened-runtime signing of every nested
  file, `notarytool` notarisation and stapling, a decision on Intel versus
  universal, and User 1 testing a downloaded zip on a real Mac: install, first
  open, setup, Save and exit, reopen, update by replacing the app, and the
  records still there afterwards.

## How hard it is to undo
Easy. The build is one script, one settings file and one CI job. The data
folder default applies only inside a Mac app; anyone with records there can
keep them by passing `--data` with that folder.

## We should revisit this if
- A tester's Mac refuses to open the app even with *Open Anyway*, or the bundled
  Python will not start from a downloaded zip.
- Mac testers want a Dock icon or a Quit menu.
- We get an Apple Developer ID: then sign, notarise and publish.
