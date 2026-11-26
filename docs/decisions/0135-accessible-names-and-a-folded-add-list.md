# 0135. Link names that include their record, a clearer way-out text, and one folded list of Add buttons

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0131 (its "What was not fixed" list)

## In plain words
Three leftovers from 0131 are fixed and an accessibility pass was run over the main pages.
1. On Home and Needs attention, every "Look at this" and "Fill this in" link now has a hidden full name that adds the
   question or the detail it is about, for example "Fill this in: Add a use-by date for Kidney beans". The words on the
   screen are unchanged. "Not now" on Home names its question too. The name only repeats words already on the page.
2. The text version of the way-out sketch names both ends of each line: "Door from Bedroom 2 to Hallway". Two doors
   to two different rooms that share a name now read differently. The drawing is unchanged.
3. A record with more than four "Add to ..." buttons (a person's page has about 17) shows one summary,
   **Add something linked to <name>...**, that opens the list. It is a plain `<details>`, so it needs no script, works with
   the keyboard and wraps at 320 px. A record with four or fewer keeps its buttons open. No single button is "the
   common one" across households, so none is kept outside the fold.

## The accessibility pass
Playwright and Chromium visited Home, Needs attention, Things to do, Review, a pet, a person and every page reachable
from Home (up to 90) in Smith, Garcia and Taylor. It looked for links with no name, the same name leading to different
places, buttons with no name, form fields with no label, a missing main, navigation or header landmark, a missing page
language, more or fewer than one main heading, drawings with no name, and a visible outline when Tab lands on something.
- **Real, fixed:** on a pet's page the "Open this weigh-in" links in the chart's table (and in the timeline) were identical
  for different weigh-ins. They now add the day and the value (and the time or words in the timeline).
- **Real, fixed in 1 and 2 above.**
- **Found and left:** two lists (Stock movements, Pet feeding) can hold two records with the same label (the sample data
  has two called "Weekly shop." on different dates); their "Open <label>" links then match, which is the data's own wording.
  "Settings" appears twice on Things to do, once to the page and once to a place on it (same page).
- **Clean:** every other check, on every page visited.

## Browser check
`tools/browser_check.js` now fails if on any page of its 320 px sweep the generic words (Look at this, Fill this in, Open,
See this day, Open this ..., Add to ...) lead to two different places under one name.

## What else we considered
- **Visually hidden text instead of `aria-label`.** The app already uses `aria-label` for these links (checklist, timeline,
  rows), and the visible words are the start of the name, so voice control still works. Kept consistent.
- **Making the visible words longer.** Rejected: it crowds the buttons at 320 px.
- **Folding every record's Add buttons.** Rejected: a short row of buttons is clear as it is.

## What this costs us (the downsides)
- One more press to reach an Add button on a person's page.
- The fold's summary is plain text; a screen reader says "collapsed" until it is opened.

## How hard it is to undo
Easy: a few template lines in `home.html`, `attention.html`, `form.html`, `_dot_chart.html`, `_exit_parts.html`, one
`text` field in `exit_sketch.py` and one line in `timeline_pages.py`.

## We should revisit this if
- User 1 would rather have one Add button always in view on a person's page.
- A screen reader user finds the names too long.
