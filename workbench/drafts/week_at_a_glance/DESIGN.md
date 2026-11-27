# Week at a glance: a Home panel (batch 23 item 121)

Written 27 November 2026 against `main` at `2d9fca8`. It draws only on calendars that already exist:
- Things to do's combined month (`together_view`, decision 0122)
- the per-subject calendars of Pet feeding, Routines and Home care (0119, 0125)
- private calendars such as Medicine doses (0121), which give counts only

Nothing new is stored. User 1's priority is seeing results visually, so the panel turns this week into seven
small columns on Home.

## What it shows

One row of seven days, starting on the household's first weekday, as Things to do's This week does. Today is
outlined. Each day has up to three stacked marks using the calendars' fixed looks and symbols (0119), with how many:

| Mark | Look | Comes from |
|---|---|---|
| ✓ n | Done | every non-private calendar's done marks (Routines, Home care, Garden, Vehicle services, kit checks, loans returned) |
| ○ n | Due | the one next open date of each due list (shown once, on its day; a late one only on today, as "due since") |
| ● n | Recorded | pet feedings and other recorded entries, summed across pets; private lists add only their count |

A blank day has no marks and one sentence below the row: **"A blank day has nothing recorded or due. It does not
mean anything was missed."**

### Phone, 320px (sketch in words)

```
This week · 23 to 29 Nov                      [Open Things to do]
 Mon  Tue  Wed  Thu  Fri  Sat  Sun
  23   24   25   26  [27]  28   29
       ○1   ●2   ✓1   ○2   ◇1
            ✓1   ●3   ●1
 Done 3 · Due 3 · Recorded 6 · Planned 1
 ▸ This week in words
```

The seven columns are about 40px each, with the day number above. Marks are 1.1rem chips with the count beside
them. With more than three kinds of mark, the column shows the first two and **"+1"**, and the words list has the
rest. Under 340px wide the weekday names shorten to one letter, and the screen-reader name stays the full day.

### Desktop (sketch in words)

The same row, wider. Each column also lists up to three short lines under its marks, the same lines as Things to
do's day list, cut at 28 characters: "Routines · Put the bins out", "Home care · Gutters". A day with more lines says
**"and 2 more"**. The panel sits under Things to do's card, full width.

## The text version (always on the page)

A `<details>` under the row, closed on screen and opened in print (`data-print-open`, 0131):

> **This week in words**
> - **Monday 23 November:** nothing recorded or due.
> - **Tuesday 24 November:** due: Routines · Put the bins out (due since 24/11/26, not recorded as done yet).
> - **Wednesday 25 November:** 2 feedings recorded (Rex, Whiskers); done: Home layout · Kitchen smoke alarm test.
> - **Thursday 26 November:** done: Routines · Water the pot plants; 3 feedings recorded; 2 doses recorded.
> - **Friday 27 November (today):** due today: Routines · Water the pot plants; Vehicles · Small car registration.
> - …

Each day name links to that day on Things to do's Calendar tab (`/to-do/calendar?month=2026-11#…`). In the grid,
each column is one link with the full words as its name, and the marks are `aria-hidden`, as calendar cells are.

## Rules

- **Only existing calendars.** The panel calls the same functions as Things to do's Calendar tab and the
  per-subject calendars for the 7 days, so its counts always match theirs. A check compares them.
- **Private lists** (Medicine doses and any later private list): a count only, with no name, medicine or person,
  even in the words list ("2 doses recorded"). The panel never has a Show button; Show stays on the list's own
  page.
- **Pets' feedings** show as a count across pets in the grid, and by pet name in the words (not private).
- **Due dates** are shown once, as on Things to do: a late one shows on today as "due since", never on every day.
- **Never** "missed", "late" in red, streaks or a score. Colour is never the only signal: every look has its symbol.
- **Modules switched off** contribute nothing. With no dated lists at all, the panel is not shown.
- **Household choice:** Settings, Home, **"Show this week on Home"**, on by default once any dated list has
  entries. It is off for a household with no dated lists.

## Empty states

| Case | Words |
|---|---|
| A week with nothing at all | **"Nothing recorded or due this week. Things to do shows later dates."** (the grid is still drawn, so the week is visible) |
| Only private entries | the counts show, and the words say "2 doses recorded" per day; nothing more |

## Checks

1. The panel's counts for each day equal Things to do's Calendar tab plus the per-pet feeding and private
   calendars for the same days.
2. A late routine appears once, on today, as "due since …", not on its own earlier day as well.
3. No private name, medicine or amount is in the panel's HTML (item 108's markers).
4. At 320px the panel is no wider than the screen, and each column's link has the full day in its name.
5. Dark mode and print keep every symbol; print opens "This week in words".
6. A week starting on Sunday (US household) starts the row on Sunday.
7. A household with Routines only shows only routine marks, and with nothing dated the panel is not shown.
8. Turning the setting off removes the panel and changes nothing else.
9. No word "missed" or "overdue" appears (search the HTML).
10. A day with five kinds of marks shows two plus "+3" in the grid and all five in words.

## What the core must add

- A **week view function** over the calendars (`together_view` gives a month today), returning per-day counts by
  look across all calendars, private ones as counts only.
- A Home panel slot with the setting.
- Nothing else: no table, no migration.
