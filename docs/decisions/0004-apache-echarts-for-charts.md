# 0004. Apache ECharts for charts

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The library that draws the graphs.

## What we chose
Use Apache ECharts, bundled as a single local file so charts work with no internet.

## Why we chose it
- Handles time series, marking events on a line (the heart of the question loop), large data and light/dark themes well.
- Widely used and actively maintained, which matters for longevity.
- Our brief says to use a well-trodden library, not to invent rendering.

## What else we considered
- Chart.js: smaller and simpler but weaker at annotated time series without add-ons.
- Plotly: very capable but large.

## What this costs us (the downsides)
- A sizeable file (a few hundred kilobytes) in the bundle.
- A big library with more options than we use.

## How hard it is to undo
Low to medium. Charts are only in the Graphing module. Saved chart settings would need translating to a different library.

## We should revisit this if
- The library is abandoned.
- File size or performance becomes a problem on older computers.
