# 0127. Lane B's three open findings checked, and a phone-width check on every example household

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0096 (Mac build), 0097 and 0105 (receipt Review), 0113 (This year at 320px); Lane B reports
  `2026-11-21-routine-checklists-ux.md`, `2026-11-21-receipt-group-review.md`, `2026-11-21-mac-preview-readthrough.md`

## In plain words
Lane B's checker left three findings marked open: This year too wide on a small phone, wording on the receipt
Review page, and wording in the Mac read-me. We looked at each one against the program as it is now. All three were
already fixed by earlier work, so no wording or layout changed. What is new is a guard: the browser check now opens
the main pages of all three example households at phone width (320 pixels) and fails if any is wider than the screen,
so the problem cannot quietly come back.

## What we checked, and what we found
1. **Batch 21 item 98, This year 344px wide.** Already fixed by decision 0113: under 30rem each month is one row
   of labelled numbers (Due, Done, Skipped). A new browser sweep measured 320px wide on `/to-do/year` in Smith, Garcia
   and Taylor. Skipped as a change.
2. **Batch 19 item 82, receipt group wording.** Already shipped (0097, 0101, 0105): the group says "Accepting only the
   Stock item leaves the Stock in waiting"; the dependent button reads "Accept" with the spoken words "Stock in and
   its new Stock item"; a bought movement reads "Add 1 pack of Demo red lentils on 20/11/26" (existing test); after
   Accept all the line names each table and count ("Added 1 to Stock items and 3 to Stock in and out."). We kept this
   wording rather than the report's "3 movements and 1 new item", which says the same thing in the table's own names.
   The visible button still says only "Accept" so a phone row stays short.
3. **Batch 19 item 84, Mac read-me words.** Already replaced in `tools/build_macos.py` and `README.md`: a connected helper
   is named, "each new unsigned preview build" may warn again, and the account claim is "Someone with access to this
   Mac account or its backups may be able to read them". Nothing about real Mac behaviour was changed or claimed; the
   six real-Mac checks stay with User 1.
4. **A 320px sweep.** A throwaway crawl followed links from Home in each example household (1,500 pages each, no
   limit reached by the useful pages) and found no page wider than 320px.

## What we chose
- `tools/browser_check.js` gains `checkWidths`: set the window to 320px, follow links from Home (skipping
  Save and exit, exports, restores, helper keys and buttons that change records), and fail naming every page whose
  width is over 320 pixels. It also requires that `/to-do/year` was reached. The existing This year assertion stays.
- `tools/browser_check.py` runs it for Smith (AU) and Garcia (US) after their other checks, and adds a short Taylor (UK)
  run that does the dates check and the sweep only.
- `tests/test_polish_0127.py` pins the three sets of words and the narrow layout rules.
- `workbench/STATUS.md` rows for the three items now say they were already fixed.

## Why we chose it
- Checking first avoided changing working wording again and risking the 0097/0105 tests.
- A sweep of many pages catches the next too-wide page without a person looking at each one.

## What else we considered
- Making the Accept button's full words visible: longer buttons on a 320px row for a small gain, since the spoken
  name already contains the visible word. Left as is.
- Sweeping every page: the household crawls reach 1,500 pages and took minutes; 60 pages from Home keeps the browser
  check about as long as before.

## What this costs us (the downsides)
- The browser check is a little longer (three sweeps of up to 60 pages).
- The sweep reads only the page's overall width; a single clipped control inside a scroll box would not be caught.
- The Taylor run is short: it does not repeat the full checks done for Smith and Garcia.

## How hard it is to undo
Easy. Remove `checkWidths` and the Taylor run; nothing else depends on them.

## We should revisit this if
- A page is found too wide at 320px that the sweep did not reach (raise the page count or add its link to Home), or
  Lane B finds the Review button words still confuse a household.
