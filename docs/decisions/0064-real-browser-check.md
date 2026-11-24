# 0064. A real-browser check that clicks through the program

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
A robot now opens the real program in a real web browser (Chromium), answers the setup questions,
adds stock, records stock in, opens private details and closes the program, the way a person would.
If any step breaks, or the browser shows an error, the check fails and says what went wrong in plain
words. It caught one real problem straight away (below).

## What we chose
- `tools/browser_check.py` makes a throwaway data folder (and a throwaway home folder, so no backup
  lands anywhere real), starts the real program with `python -m dashboard --data … --no-browser`, and
  runs `tools/browser_check.js`, which drives Chromium through Node.js and Playwright. It reuses
  the screenshot tool's approach: the launch link signs in, the setup steps come from
  `make_screenshots.wizard_steps`, and the browser's language and time zone are set per household.
- Two runs:
  1. **Australia (en-AU):** a fresh folder; the setup wizard is answered in the browser and Home must
     show its area cards. Then the made-up Smith household's records are added and the browser checks:
     the drinking-water question follows the category (`show_when`); a use-by date typed `20/05/27`
     shows "20 May 2027" beside it, `05/20/27` shows the "Use DD/MM/YY" hint, and the saved date reads
     back as `20/05/27`; on Stock in, the find box picks the item, "Which batch" lists only that item's
     batches, the blank choice's words follow Reason, "Use by" and "Where you put it" hide once a batch
     is chosen, and saving adds to the item's amount; a private detail is not in the list page or the
     record page until "Show" is pressed, a refused save keeps it closed, and saving another field
     keeps it; the private medical sheet asks first; Save and exit ends on "Saved and closed" and the
     program really stops.
  2. **United States (en-US):** the Garcias, loaded directly; dates are typed and read month first
     (`05/20/27`, "May 20, 2027", hint "Use MM/DD/YY").
- Throughout, any browser console error, script error, or page or form answer of 400 or above fails
  the check (the one save that is meant to be refused, answering 422, is allowed).
- `tests/test_browser_check.py` runs the whole check as part of the normal tests when Node.js,
  Playwright and its Chromium are installed, and **skips with the reason** otherwise. The whole check
  takes about 5 to 10 seconds.
- **CI:** a separate Linux job, "Real-browser check", installs Playwright at an exact version
  (1.63.0, written `playwright@=1.63.0`) with its Chromium and runs `tools/browser_check.py`. On the existing Linux and
  Windows test jobs Playwright is not installed, so the test skips there and Windows can never fail
  because of it.

## Why we chose it
- A security header (`Referrer-Policy: no-referrer`) once made Chromium send `Origin: null` with every
  form, so every save was refused, and the Flask test client could not notice. Only a real browser
  sees that; with that header put back, this check fails on the first save (setup) with a plain message.
- Much of what a household relies on is browser code: the date preview, the batch list following the
  item, find boxes, fields that show for one choice, and private "Show" buttons. Unit tests check the
  server's half; this checks the half that runs in the browser.
- Playwright and Chromium were already used for the screenshots, so nothing new is shipped and the
  program itself gains no dependency.

## Found and fixed by the check
- **A refused save could erase a private detail.** When a record with an unopened private detail was
  saved with a mistake in another answer, the form came back with the private box open and empty.
  Saving again then sent it blank: for a required detail the person saw a confusing "required" error;
  for an optional one (a vehicle's registration) it was quietly erased. Now the box stays closed and
  kept after a refused save (`display.build_fields`, `pages._raw_form`), tested in `tests/test_web.py`.

## What else we considered
- **Selenium or a Python Playwright package:** would add a Python dependency to `requirements.lock`;
  Node Playwright was already in use for screenshots and keeps the program's own libraries unchanged.
- **Running it in every CI job, Windows too:** installing Chromium on Windows is slow and the
  Linux run already proves the browser code; the Windows job keeps its build-and-start smoke test.
- **Driving fixed screenshots and comparing pictures:** brittle (fonts, sizes) and says nothing in
  plain words about what broke.

## What this costs us (the downsides)
- Playwright is a tool fetched by CI from npm (pinned to one exact version, without a checksum lock
  like `requirements.lock`); a future version bump is a deliberate edit to `ci.yml`.
- On a computer without Node.js and Playwright the test skips, so "nothing skipped" in the definition
  of done means installing them (`npm install playwright@=1.63.0` and `npx playwright install chromium`)
  or relying on the CI job.
- The check names records from the example households (Kidney beans with two batches, Emily Smith's
  allergy). If those examples change, `AU`/`US` at the top of `tools/browser_check.py` must follow.
- Browser checks are slower and more fragile than unit tests; they are kept to one pass per locale.

## How hard it is to undo
Easy: delete the two tool files, the test file and the CI job. Nothing in the program depends on them.

## We should revisit this if
- The CI job fails for reasons that are not real problems more than once in a while (flaky timing).
- The check takes much longer than a minute, or a bug reaches a household that a browser would have shown.
