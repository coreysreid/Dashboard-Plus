# 0109. The first two charts, drawn on the server as SVG

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0004 (charting library, superseded here for now), 0015 (days of water), 0047 (Pets), 0059 (private details), `workbench/drafts/charts/FIRST_TWO.md` and `FIRST_TWO_ACCEPTANCE.md` (Lane B, batch 20 item 97)

## In plain words
Two charts, picked by Lane B because they need no history that we do not keep.
**Drinking water counted today** shows which water items make up the "days of
water" on Home, one bar each, and lists every water item that is left out and
why (not safe to drink, or recorded in bottles rather than litres). **Recorded
weights** shows one pet's weigh-ins as dots by date, on the pet's own page and
on a page where you can choose the pet and the dates. Each chart has a table
with the same values underneath it, works without the picture, and prints.
Nothing is sent anywhere and no new library is added.

## What we chose
- **One calculation for water.** `watch.supplies` (Home's days of water) now
  sorts every record its `supply` rule looks at into counted or left out, in
  one pass (`watch.supply_rows`), and keeps that list on the result. Home, the
  Needs attention page and the new page all read the same result, so the bars
  always add up to Home's total. The helper API's reply is unchanged.
- **Where they live.** `/supplies/<table>` for the water breakdown, linked from
  Home's water card ("What is counted") and from Needs attention. A pet's page
  shows its recorded weights; `/charts/<table>?subject=…&from=…&to=…` chooses
  the pet and an optional date range. A module switched off has no page (404)
  and no link.
- **Declared, not hard-coded.** A table may say
  `chart = { kind = "dots", x = "day", y = "weight", per = "pet", what = [...], entry = [...], subject = "pet" }`
  in `tables.toml`; the module checker explains a wrong one in plain words.
  Pets' Weigh-ins declares it. Only `dots` exists for now.
- **Drawing.** `dashboard/web/charts.py` writes small SVG on the server: a
  `<title>` and `<desc>` named by `aria-labelledby`/`aria-describedby`, every
  bar or dot a link with its value, unit (and date) in words that goes to its
  table row, values printed beside bars, scales from zero, dots never joined,
  two readings on the same day side by side. No script, no animation, nothing
  fetched. It is sized to stay readable at 320px, has rules for print and
  Windows high contrast, and on a phone each table row becomes a card in the
  same order.
- **Exact words from the draft** for every empty and uncertain state: no water,
  only left-out water, no person count (litres but no days), a missing amount
  (unknown, never zero), no pet, a pet with no weigh-ins, one weigh-in, and a
  period with none. The chart shows at most 12 bars and says so when more items
  are counted; the table always lists every item.
- **Kept out:** pet notes, weigh-in notes, microchip numbers and vet-visit
  reasons are not on the chart or its table. A changed date or weight says
  "Corrected on"; a restored reading says "Restored on". No trend line, healthy
  range or cause is drawn or worded.

## Why we chose it
- The household needs to see *why* Home says "about 2.5 days"; a second formula
  could quietly disagree, so the page reads the very same result.
- Server-drawn SVG fits a local, offline program (decision 0002): no library to
  bundle, update or audit, and the page works with scripts off, in print and
  with a screen reader. Two simple charts do not need ECharts' features.
- A declaration lets later modules get a dots chart without new screens.

## What else we considered
- Apache ECharts (decision 0004): capable, but a few hundred kilobytes of
  script, drawn in the browser, harder to make equal to a table and to print;
  not needed for bars and dots. It may still suit annotated time series later.
- A separate water sum for the chart: rejected; two formulas drift apart.
- Drawing a water line over time: the draft explains why not yet: no dated
  balances or household-size history are kept.
- Showing vet visits as markers: left for a later, opt-in step, as the draft
  suggests, so no visit is read as the reason for a change.

## What this costs us (the downsides)
- Hand-written drawing code to maintain; zooming, hovering and panning that a
  library gives are absent.
- The water page reads every water item and each batch's place one by one;
  fine for hundreds, slow for many thousands.
- "Corrected on" looks at the change history; a correction made by editing the
  database by hand would not show.
- The empty sentences about drinking water use the supply rule's words; a
  future non-water supply rule would need its own wording.
- The `supply` result now carries every row behind it, a little more memory on
  each Home view.

## How hard it is to undo
Easy. Remove `chart_pages.py`, `charts.py`, the three chart templates, the
`chart` line in `modules/pets/tables.toml` and its checker, and the two links.
`watch.supply_rows` can stay; it gives the same totals as before.

## We should revisit this if
- People want to compare periods, zoom or mark events: bring back a charting
  library (0004) or extend the helper deliberately.
- The water total on the page and on Home ever differ, or a left-out item has
  no row.
- Households with very large stock lists find the water page slow.
