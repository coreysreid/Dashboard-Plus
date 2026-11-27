# Batch 22 item 107: bar charts, checked, and the next three charts

Checked 27 November 2026 against `main` at `2d9fca8` (decisions 0124, 0128 and 0129 merged). The pages were the
seven bar charts the modules declare: Food put out (Pet feeding), Times done (Routines), Work done (Home care),
Jobs done (Garden), Services done (Vehicles), Doses recorded (Medicine doses) and Spent (Stock). Each was opened
with its default, By day, By week and By month, at 320px and 1280px, in Smith, Garcia and Taylor, and in a fourth
copy of Smith ("bars") with made-up rows added to test the arithmetic. Spending is checked in depth in item 110.

## The arithmetic, against the records

Rows added to the "bars" copy for Rex (household time zone set to Australia/Sydney), and what the 14-day chart said:

| Row added | Expected | Chart said | |
|---|---|---|---|
| 13 Nov 23:30, 100 g | outside the 14 days; in the week from 09/11 | not in the 14 days; week from 09/11/26 "200 g put out, 2 feedings" | ✓ |
| 14 Nov 00:10, 100 g | 14 Nov | "Saturday 14/11/26 · 100 g put out" | ✓ |
| 20 Nov, 2 pouches | not added to grams, said | "none in g · also 2 pouches, not in this chart"; In pouch link | ✓ |
| 21 Nov, no amount | counted, not added | "no amount recorded · 1 with no amount" | ✓ |
| 22 Nov, 500 g, deleted | not counted | "Nothing recorded" | ✓ |
| 23 Nov, 300 g, waiting in Review | not counted | "Nothing recorded" | ✓ (see finding 3) |
| 24 Nov, 1.5 g and 0 g | 1.5 g, 2 feedings | "1.5 g put out · 2 feedings recorded" | ✓ |
| 25 Nov 23:30 **UTC** (a helper's time with offset) | 26 Nov in Sydney | "Thursday 26/11/26 · 340 g put out, 3 feedings" | ✓ |
| Total | 441.5 g from 6 feedings in g | "441.5 g put out, from 6 feedings"; "1 feeding has no amount…"; "Also recorded in another unit… 2 pouches" | ✓ |

Routines: a skipped time on 10 Nov was not counted; done on 31 Oct, 1 Nov and 26 Nov gave "October 2026: 1",
"November 2026 (so far): 2". Week bars began on the household's first weekday. No page was wider than 320px; every
chart had an SVG title and description naming the same values as the table, and every empty period said
"nothing recorded" or "Nothing recorded", never "missed".

## Findings, worst first

### Important: a chart page opens on an empty subject while others have records

- **Where:** `/bars/routines__times/done` in all three households, `/bars/home_care__work_done/done` in Taylor.
- **What happens:** The page picks the first name A to Z: Smith opens on **"No times done recorded for Check the
  fridge seals yet."**, Garcia on "Sort the recycling", Taylor on "Defrost the freezer" and "Bleed the radiators",
  while other routines and jobs on the chooser have bars. A household following "Times done" from a menu sees an
  empty chart first and may decide the feature does not work.
- **Suggested change:** With no `subject` chosen, open on the subject with the most recent entry; if none has one,
  keep A to Z. Above the chooser say **"Choose a routine. Showing the one done most recently."**

### Minor: Home care's Work done page says "times done"

- **Where:** Taylor, `/bars/home_care__work_done/done`: **"No times done recorded for Bleed the radiators yet."**
  The job's own page uses "Work done per month". Two declarations (the jobs table's, decision 0129, and Work done's)
  use different `entry` words.
- **Suggested words:** **"No work done recorded for Bleed the radiators yet."**; in counts **"Done 2 times"**.

### Minor: a period with an entry waiting in Review says "Nothing recorded"

- **Where:** "bars" copy, Rex, 23 November, a 300 g feeding a helper suggested, not yet accepted.
- **Expected:** Not counted (correct), but the household should not be told nothing was written down.
- **Suggested words** in the table's More column: **"1 waiting in Review, not counted yet"**, and no change to the bar.

### Minor: count words read awkwardly

- "Water the pot plants · 12 months, 01/12/25 to today · **3 times done recorded**" → **"done 3 times"**.
- "Vehicles · 12 months … · **1 service done recorded**" → **"1 service recorded as done"**.
- Back link **"Water the pot plants's page"** → **"Back to Water the pot plants"** (and "Back to Rex"), which also
  avoids wrong possessives on names ending in s.

### Minor: the done-day explanation is technical

- **Where:** every count chart reading done days from history (Vehicles, Garden, Home care, Routines).
- **Now:** "Each bar counts the days each was recorded as done, earlier ones from each one's history; a date typed
  back, a date cleared the day it was typed, an undone press and a day taken off the calendar are never counted."
- **Suggested words:** **"Each bar counts the days something was marked done. Undone presses and days you took off
  the calendar are not counted."**

### Minor: a person's own page calls them "This person"

- **Where:** Garcia, Rosa's page: the dose bars say **"This person · 12 weeks …"** and the chart page heading says
  **"Given to #4"**. Decision 0124 says the person's own name shows on their own page before Show.
- **Suggested change:** on the person's own page use their name ("Rosa Garcia · 12 weeks …"); on the shared chart
  page use the wording from item 106 ("Person 1 of 2").

### Minor: a `by` the chart does not offer is ignored silently

`?by=day` on Times done (offered: month, week) shows months with no word. Acceptable; no change needed unless
links ever offer it.

## The next three charts a household would most want

Ranked by how often a household would look, and whether the records already exist.

1. **Garden harvests per month** (count and amount). Records: `garden__harvests` (`harvested_on`, `amount`,
   `unit`, `planting` → crop). Declaration: `measure = "sum"`, `amount = "amount"`, `unit = "unit"`,
   `per` = the planting's bed or crop, `by = ["month", "week"]`, `verb = "picked"`. One unit at a time, as Food put out.
   Why: the garden household's question is "was it worth it?", and the data is already typed.
2. **Distance driven per month** for each vehicle. Records: `vehicle_running__readings` (`vehicle`, `read_at`,
   `distance`, `unit`). Needs a new measure: the **difference between two readings**, split across the months
   between them in proportion to days, or said as "between 02/10 and 15/11: 1,240 km" when readings are far apart.
   Never guess before the first reading or after the last. Why: service is due by distance, and the readings are
   now brought in from spreadsheets (decision 0137).
3. **Drinking water on hand, week by week.** Records: `stock__movements` (`happened_on`, `amount`, `reason`)
   for items with `drinking = true`, plus each item's present `quantity`, worked backwards. Needs: a balance
   measure (closing amount per week), the household size on each date (not stored today: say "using today's
   household size"), and items' units converted only where the catalogue gives litres. Why: it is the first
   promise of the app (days of water), and today Home shows only the current number.

Considered and placed lower: Stock used per month by category (useful, but "used" amounts are in many units);
meter readings (no meter readings table exists; Home layout meters are locations only).

## Limits

Spending (0128) was opened at both widths but its prices, refunds and currencies are left to item 110. No real
screen reader was used; the SVG names and table were read from the page.
