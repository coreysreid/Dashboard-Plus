# 0045. Three made-up households, and screenshots made from them automatically

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The project now has three invented households (the Smith family in Australia,
the Garcia household in the United States and Sam Taylor in the United Kingdom)
and a gallery, `docs/EXAMPLES.md`, that shows each of them at every stage, from
the first welcome page to closing safely. One command remakes all 60
screenshots, so they always match the current program.

## What we chose
- Each household is one readable file in `examples/households/`: the setup
  answers, then every person, contact, place, stock item and stock movement.
  Dates are written as "today+12", so use-by warnings always look current.
- Amounts in the file are what is on hand today; the loader works backwards
  through the stock in and out, so each item has a true history.
- `tools/load_example.py` saves everything through the program's normal save
  path, refuses a folder that already has a database (so made-up records are
  never mixed with real ones), and can be used for demos and testing.
- `tools/make_screenshots.py` starts the real program for each household, fills
  in the real first-run wizard in a browser, loads the rest of the household,
  and visits each stage. The browser part is a short Node script
  (`tools/screenshots.js`) using the Playwright already on the build computer.
- Folder names on screen are shown as they would be on Windows, and dates in
  each household's own country format; the gallery says so.
- The screenshots are committed (about 7 MB), so the gallery works on GitHub
  and in the release notes with no build step.
- Tests check each household's exact numbers (days of water, what is running
  low, what expires, how many gaps), which doubles as the M1 check that these
  views are correct for test data.

## Why we chose it
- Corey asked for plenty of example screenshots for the launch, using typical
  made-up details.
- Three different households show different parts of the program: a busy
  family with pets, three generations with care needs and medication, and one
  person just starting out with gaps still to fill.
- Generating screenshots from the real program keeps them honest; hand-made
  images go out of date with every change.
- Fiction-reserved phone ranges and `example.com` emails mean no real person
  can be reached by mistake, and the privacy check accepts them.

## What else we considered
- Hand-taken screenshots: quick once, wrong after the next change.
- Python Playwright: not installed on the build computers; installing it
  would mean a second browser download.
- Leaving screenshots out of the repository and building them in CI: the
  gallery would not show on GitHub without an extra hosting step.

## What this costs us (the downsides)
- About 7 MB of images in the repository, and more each time they are remade.
- Making screenshots needs Node and Playwright, which ordinary contributors may
  not have; the tests only check the images exist, not that they are current.

## How hard it is to undo
Easy. Delete `docs/screenshots/`, `docs/EXAMPLES.md` and the two tools.

## We should revisit this if
- The repository grows uncomfortably large: move the images to release assets.
- A screenshot shows something misleading because of the Windows-style paths.
