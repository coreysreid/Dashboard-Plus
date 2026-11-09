# 0025. Country packs: sourced, dated, and link-first

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
Where we ship local safety information for a country, every fact names its official source and date, and we never invent statistics.

## What we chose
Country notes are data packs with cited, dated sources, a review-by date, and reuse of text only where the licence allows. No statistic is included unless a citable source says it. Every pack tells the household to check their local authority. Countries without a pack get generic prompts that help people research their own address. A weekly check flags broken links and out-of-date packs. Start with countries that publish official, openly usable guidance (recommended first: Australia and the United States).

## Why we chose it
- Hazards differ by country and by street; confident-sounding unsourced figures could mislead or harm.
- Citing official bodies is honest, lets readers verify, and shares the maintenance with those bodies.
- Dating and a review-by date acknowledge that guidance changes.

## What else we considered
- Hard-code statistics from memory: rejected, because we cannot verify them.
- No local content at all: safe, but loses the help that people who live there would value.
- Scrape live data: rejected, because it breaks the works-offline, local-only promise.

## What this costs us (the downsides)
- Packs take research and ongoing review, ideally by someone who lives there.
- A pack goes stale if nobody reviews it (the weekly check flags it).
- Reused text may carry licence obligations; linking is the fallback.
- The program is not an authority and says so.

## How hard it is to undo
Low. Packs are optional data files.

## We should revisit this if
- Packs are rarely reviewed.
- A source changes its licence or disappears.
