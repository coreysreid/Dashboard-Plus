# 0131. A hands-on check of the pages built in 0119 to 0130, and the small fixes it led to

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0119 to 0130 (calendars, bars, timelines, private lists, prices), 0129 (one bars section is enough for
  Vehicle services)

## In plain words
The checker lane has not reviewed anything built since 22 November, so the builder lane opened every new visual page
in a real browser, in all three example households, and looked for faults. The pages held up well. The few real
problems were wording and length, not broken layouts, and they are fixed: a pet's page is shorter, two different links
no longer both say "This month", and a person's "Add to pets" buttons say which link they fill in. Vehicle services also
gained **Services done per month** bars.

## How it was checked
Each example household (Smith, Garcia, Taylor) was started on made-up data and driven with Playwright and Chromium at
320 px and 1280 px, in light and dark mode (the browser's own colour setting), and with print emulation (A4 width).
About 600 pages per household were found by following every link from Home (a cap of four pages per kind, so a
hundred stock items count as four), with these checks on every one: sideways scrolling, text or boxes cut off (also
inside scroll boxes), text contrast under 4.5 to 1 in both colour modes, heading order and one main heading, a legend
entry for every mark on every calendar, a name for every drawing, link or button, repeated page ids, the same words
leading to different places, overlaps inside calendar days, and the words missed, overdue, failed and forgot. Every
link returned 200 (no 404 or 405 turned up among the links; forms that send data were not sent). Keyboard Tab order and a visible focus were
walked on a pet, vehicle, routine, Garden and calendar pages. Private values were looked for in the HTML of every page
(Garcia's doses, with and without Show) by comparing every private value in the database with the page source.

## What was found, worst first
1. **A pet's page was very long and said things twice (fixed).** Rex's page ran to about 5,100 px on a desktop: the
   form, weights (chart and table), food today, a feeding calendar, 14 one-line "nothing recorded" bars, a timeline.
   The calendar and the bars both answer "when was he fed". Now, on a page that already has a calendar, the bars fold
   under **"Show the bars: Rex · 14 days … 240 g put out, from 2 feedings"** (the heading stays above it). Nothing is
   removed: the drawing, its table, its links and its words are all inside, and the page opens the fold for printing and closes it
   again afterwards. Home care jobs, routines and a person's page (doses) get the same shorter shape. The calendar,
   weights and timeline stay open. A bars page of a whole list, or with no calendar beside it, is not folded.
2. **Two different "This month" links on Things to do's Calendar (fixed).** The tab "This month" means the coming
   weeks' list; the calendar's own "This month" jumped back to the current month. Same words, different places. The
   calendar's link now reads **Go to the current month** everywhere a calendar shows it.
3. **Two identical "Add to pets" (and "Add to utilities and household accounts") buttons on a person's page
   (fixed).** A person can be both a pet's vet and who looks after it, and the page showed the same words twice. When two buttons lead to the same
   list they now add the link's own name: "Add to pets (vet)", "Add to pets (looked after by)". A single button is unchanged.
4. **Vehicle services lacked bars (done, as asked in 0129).** A `[[tables.services.bars]]` declaration
   named `Services done` (count, `history = true`, by month and week) was added in `modules/vehicles/tables.toml`. It uses the same
   whole-list shape as Garden's Jobs done: linked from the list and shown under the Vehicle services calendar.

## Checked and fine (nothing to change)
- No sideways page scroll, no clipped text, no overlap and no text under 4.5 to 1 contrast on any page in any mode; no
  missing legend; headings never skip a level; print had no overflow.
- The words "missed", "overdue" and so on appear only in the sentences that say a blank is **not** missed, and in
  Needs attention's "overdue since" for a past due date (the established word since 0107). No blank is ever called missed.
- Before Show, no private value is in the page source: Garcia's dose pages name nobody (the person shows as "#4" until
  Show, deliberately, test_private_reveal) and give only counts; "Spent per month" gives counts, never an amount, until
  Show, and after Show gives the total plus each category's own bars. After Show nothing overflows at 320 px.
- After Show the dose calendar still reads "(Medication #3)" while the timeline reads the plain medicine words. That
  is the earlier decision: the calendar and day page group by medicine, so they keep its number. Left alone.
- Wide tables scroll inside their own box at 320 px, which is by design; Chromium makes such boxes reachable by keyboard.
- Dots and bars in the drawings can be tabbed to; the focus is a thicker outline on the mark and an underlined label.
  Visible, if subtle. A stronger ring would need drawing one around each mark. Not done.

## What was not fixed
- "Look at this" and "Fill this in" repeat on Home and Needs attention, each going to a different record. Each is
  in its own row with the record's name beside it, so it reads in context; a link label that names the record would
  be better for a screen reader. Left for a later pass.
- "Door to Hallway" appears twice in the way-out sketch's text with different targets (doors on different floors that
  share a name). Left; it is a data wording matter in the sketch.
- The person's page has about 17 "Add to ..." buttons. They are all genuine, but a folded list would be tidier.
- Lane B should re-run its walk over calendars (item 106 of the workstreams page) on this branch once merged.

## What else we considered
- **Folding the calendar as well, or every secondary panel.** Rejected: the calendar is what a household looks at first;
  folding everything would hide the page's point.
- **Folding bars on every page.** Rejected: on its own page, or without a calendar beside it, they are the main thing.
- **Renaming the Things to do tab instead.** Rejected: User 1 already knows "This month" there, and it is used in
  decision 0107's words.

## What this costs us (the downsides)
- One more press to see the bars on a pet's, job's, routine's or person's page. Printing opens the fold by itself, but a
  browser with scripts turned off prints it closed.
- A different word for the calendar's current-month link.

## How hard it is to undo
Easy. Each is a few lines in `form.html`, `_calendar.html` and `pages.py`, or one declaration in `modules/vehicles/tables.toml`.

## We should revisit this if
- User 1 would rather see the bars open, or finds the fold hides something wanted.
- A page gets a third kind of panel and is long again.
