# 0144. Batch 23 checks acted on: Bring in dates, skip links, read-me words, agreed words

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
Lane B's fourth round of checks found one crash and several places where the words or the keyboard path were wrong.
A spreadsheet row with no date can no longer break Bring in earlier entries, record pages no longer drop the cursor
into the Name field, the read-me files stop promising things that are no longer true, and one word is now used for
each idea.

## What we chose
- **A date is always required when bringing in earlier entries (item 113).** A row whose date (or date and time) is
  empty is listed under "Rows that need fixing": "Date is empty. Every earlier entry needs its own date; it is never
  filled in as today." The other rows carry on. A date after today is also listed ("is after today ... check the
  date order"), because it is almost always a day-first or month-first mix-up. "120g", "120 g" and "0.5 pouch" are
  read as an amount plus one of the list's own units when no column is matched to Unit; any other unit ("1 cup") is
  a row problem and is never converted. When no row is ready the page says "Nothing is ready to bring in yet." and
  shows no button.
- **Record pages start at the top (item 112).** The cursor goes into the first field only on an Add page and after a
  failed save. Every page starts with a "Skip to main content" link, and a record page lists "Skip to" its own parts
  (charts, calendars, bars, What happened, linked lists). After "Not a done day" the notice takes focus so Undo is the
  next Tab stop. Home's card names are inside their headings ("Things to do: 2 due today or before ..."), the focus
  mark on a chart dot is a 3px ring, and a history line shows the time the household's way and says "added" when
  the old value was empty.
- **Read-me words (item 124).** The Windows and Mac read-me files and README.md use the exact replacements in
  `workbench/reports/2026-11-27-read-me-check.md` (no more "Nothing is sent anywhere", how to unblock the zip, what an
  update backs up, moving to a new computer, the second backup copy). The Getting started draft is Lane B's and
  item 117 rewrites it, so it is not touched here.
- **Agreed words (item 126).** "Next 50 rows" (not "Show more", which looks like the private Show), "From before today"
  and "due today or before" (not "Late" or "due or late"), "Mark done" (not "Mark this occurrence done"), "Open to
  update", "All entries in this list", "See what is in it" for a backup, "Done" for Garden's column, a fixed Readiness
  heading, and Settings' "Bring in earlier entries: added at once, with one Undo".

## Why we chose it
- A blank date silently becoming today would put wrong dates into a household's history; refusing it keeps the
  record honest, and the same rule covers every list that opts in.
- A person who cannot see the page, or who only uses the keyboard, should land on what the page is about.
- A read-me that overpromises is worse than a short one: the connector means "nothing is sent" is no longer true.

## What else we considered
- Dating a blank row today with a warning: rejected, because the warning is easy to miss and the date is wrong.
- Hiding the Name focus only with a script: rejected; the page should be right with no script.
- Renaming every word in the audit now: several need a design (a Food for rows without one choice, Given to limited
  to people with medicines, Person 1 of 2) and are left for later.

## What this costs us (the downsides)
- A file with a few future dates now needs fixing before anything is added (that is the aim).
- The Skip to list is another line on record pages.
- Not done yet: "Food for rows without one" and a narrower "Given to" in Bring in, month-name and no-year date help,
  guessing a heading such as Dog or Patient, the 60-character medicine choice, and the one-word empty states.

## How hard it is to undo
Easy. Each change is a few lines in one template, label or check, with a test in
`tests/test_lane_b_batch23_fixes.py`.

## We should revisit this if
- A household reports that a legitimate future-dated entry is being refused, or the Skip to line is noisy.
