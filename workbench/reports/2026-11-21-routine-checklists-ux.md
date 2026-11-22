# Batch 21 item 98: Things to do, checked

Checked 21 November 2026 against decision 0107 on main (`dbd5aab`). All data was loaded from the three invented example households into disposable folders. Chromium opened Today, This week, This month and This year at 320px and 1280px for Smith (AU), Garcia (US) and Taylor (UK): 24 live page views. Each answered 200. The browser's calendar date was 22 November in each chosen household timezone; relative example dates therefore reflect that date.

## Findings, worst first

### Important: This year is wider than a 320px phone

- **Where:** `/to-do/year`, all three households, 320px viewport.
- **How to see it:** Open Things to do → This year at 320px. The document is 344px wide; the month summary table is wider than the viewport. Today, This week and This month each measured 320px. The same four pages fit at 1280px.
- **Expected:** The entire page, including Month / Due / Done / Skipped, fits at 320px or the table scrolls within its own clearly labelled region.
- **Actual:** The page itself scrolls sideways by 24px. This can clip the right edge and makes the tabs and task controls move with the table.
- **Suggested change:** Give the month summary its own horizontal scroll container with an accessible label and a visible scroll cue, or stack the four values per month below the narrow breakpoint. Keep the rest of the page at 320px.

### Minor: a one-step Mark done has no Done row or Undo here

- **Where:** The Garden action “Mark done” on `Check bed ties` in Smith's This month; decision 0107 already calls out this limitation.
- **How to see it:** The row has “Mark done”, while routine rows have “Mark this occurrence done” and “Skip this time”. The one-step Garden action ends its reminder but does not make a Done history row or offer Undo on Things to do.
- **Expected:** A person can see the result and reverse an accidental tick from the same list, as they can for a routine.
- **Actual:** The list's Done and Undo path covers saved action-form operations, not one-step actions. This is a consistency gap, not evidence of data loss.
- **Suggested change:** After a one-step Mark done, say exactly where to review or change it; if safe Undo is added later, include it in the same Done section without manufacturing an event for an unrecorded day.

Lane A's open PR #191 (decision 0112) adds one-step Done history and Undo. This finding describes main at the check time; recheck it after that PR merges.

## What held

- Smith's `Put the bins out` appeared once as **“Due since 19/11/26”** on Today. Garcia's late pet vaccination said **“Vaccinations due since 11/17/26”**; Taylor's late loan said **“Return due since 20/11/26”**. The local date order held. Late rows appeared once per view, not once per missed interval.
- At 320px, Smith's `Put the bins out` action, Garcia's `Sort the recycling` action and Taylor's `Water the windowsill herbs` action each opened a form with **no repeat option preselected**. Choosing repeat and saving gave one Done row, with **“Marked done on … Next date …”** and **“Undo this tick”**. Undo said **“Undone. The done or skipped entry was removed, and Last done and Next date are back to what they were.”** Each original due label returned.
- Month and year views exposed the future dates and source-specific actions: a record update link for vaccinations and insurance, “Mark returned” for a loan, and “Mark done” for a Garden job. The year summary showed twelve months. No duplicate task rows were seen.

The repository's broader `tools/browser_check.py` run reached its final browser-console check but reported a 404 resource error (also on its AU-only run). This report relies on the separate 24-view Chromium walk and the three live action/Undo runs above; it does not claim the full browser check passed. The required `tools/check_all.py` is a separate gate.
