# The Nguyen household: notes (batch 23 item 125)

An invented fourth example household, so the charts, calendars and timelines can be shown with years of records
instead of two entries. Everything is made up. Phones use the Australian fiction range 0491 570 110 to 114; there
are no emails except example.com, and there are no real places beyond the state. `make_demo.py` writes
`nguyen.toml` with a fixed seed, so the same file comes out every time. Edit the script, not the file.

Checked 27 November 2026 on Lane A's branch at `eeb6eac`: it loads with `tools/load_example.py` in about 7 seconds.
Home, both pets' pages, Bao's page, Biscuit's timeline, the feeding bars by month, Spent, the vehicle, the
Calendar tab, a routine and Needs attention each answered 200 in under 0.15 seconds.

## What is in it

| Records | How many | The story they tell |
|---|---|---|
| Biscuit's weigh-ins, monthly for 4 years | 49 | Slow gain to about 27 kg, then a vet-advised diet 18 months ago brings it down |
| Pepper's weigh-ins, quarterly | 17 | A steady cat, small ups and downs |
| Feedings, twice daily for Biscuit and once for Pepper, 2 years | about 2,000 | Biscuit's portions drop from 260 g to 210 g at the diet; about 6% of feedings were never written down |
| Bao's doses: two medicines (separate details), 1 year | about 700 | Morning tablet and night drops; about 5% have no entry, never called missed |
| Bins weekly for 3 years, vegetable patch every 2 days for 2 years | about 460 | A few "skipped" bins; gaps in watering |
| Odometer readings, monthly for 4 years | 49 | 800 to 1,500 km a month |
| Gutters twice a year, air conditioner yearly, 5 years of work done | 15 | Earlier done days on the calendar |
| Priced shopping, 5 items, 2 years | about 290 movements | Prices creep up about 8%; dog food bought every 6 weeks |

## Use it for

- **Item 132 (correlations, done honestly):** Biscuit's food put out per week against his weight. The example
  deliberately has smaller portions starting the same month the weight turns down. A chart must still say food put
  out is not food eaten, and that this is not proof of cause.
- Bars by month and week with real gaps, and the "so far" period.
- The timeline's paging, with hundreds of lines.
- Spent per month with rising prices, and Show.
- Dose calendar and bars with two medicines, each its own detail (item 107's grouping problem does not arise here).

## Checks before promotion to `examples/households/`

1. `python tools/load_example.py --data <empty> nguyen.toml` loads all records with no warning.
2. No real name, place below state level, real phone number or email (the privacy check passes).
3. Every chart and calendar page opens in under a second (`tools/time_pages.py` style).
4. No page says "missed" for a gap.
5. The file is about 590 KB; if that is too large for the repository's examples, keep `make_demo.py` and generate
   the file at test time instead.

## What Lane A needs to promote it

- Decide whether a 590 KB example belongs in `examples/households/`, or whether the generator should run in
  `tools/make_screenshots.py` and tests instead.
- Screenshots for `docs/EXAMPLES.md`: Biscuit's weight over all dates, feedings by month, Bao's dose calendar
  before and after Show, and Spent per month.
