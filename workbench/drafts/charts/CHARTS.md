# Four charts worth opening

**Checked 2026-11-17.** Charts are an optional way to inspect household records. Put the plain answer and date span **above** each chart, then the chart and a linked data table. Draw no line through missing days. A chart offers an observation, not a cause or safety verdict. A confirmed household annotation can mark an event; an unconfirmed nearby event is not labelled as the explanation.

## 1. Drinking water over time

**The household's question:** “Did we keep enough drinking water after last week's shop?”

**Sketch:** A simple line with local dates along the bottom and **days of drinking water** on the side. A horizontal dotted line shows the household's chosen target, labelled with its value; do not colour a day red or call it safe. Mark each Stock in/out event with a small dot whose detail says, for example, **“8 Nov: added 12 litres of drinking water.”** Let the person switch to a table of date, counted litres, household size, calculated days and source movements. On a narrow screen, show a short recent span first and allow scrolling through older dates.

**Data needed:** A dated daily snapshot or reconstructable end-of-day balance of each `stock.items` row where `category = water`, `drinking = true` and the unit converts to litres; dated Stock movements and inventory corrections; number of people living here and pets on each date; the chosen per-person and per-pet daily basis and target; local timezone. The current Stock table provides today's quantity and movements but cannot always reconstruct earlier balances or past household size. Save the inputs used on each day or flag days whose basis changed.

**Plain text:** **“On 8 November: 24 litres counted, about 2.4 days for 3 people and 1 pet, using 10 litres a day. Target: 3 days.”** The example arithmetic is invented. If data are incomplete: **“No reliable history yet. Start recording Stock in and out and a starting count.”** Never show a zero for an unrecorded day.

## 2. What was thrown away each month

**The household's question:** “Which goods keep being wasted?”

**Sketch:** One vertical bar per completed month, height = number of **discard or expired movement entries**, with the value printed on the bar. Selecting a bar opens its dated entries and reasons. A second view groups a single selected unit or item type; it must not add tins, litres and packets into one amount. Show the completeness state immediately below each month. Use a neutral single colour, with patterns or labels for missing/incomplete months rather than relying on colour.

**Data needed:** `stock.movements.reason` (`thrown_away` or `expired`), `amount`, `happened_on`, item ID and movement-time unit/name; household confirmation that discard tracking was complete for the month. See the exact metric and evidence rule in the proposed batch 7 outcomes draft. A deleted or corrected movement rebuilds the bar and its linked table.

**Plain text:** **“October: 3 recorded discard entries; September: 7. Both months were marked complete.”** Do not say waste was prevented. If only one month is complete: **“One complete month recorded. Add another before comparing.”** If a month is not confirmed complete, hatch its bar and label **“Partial records”** without drawing a comparison arrow.

## 3. A pet's weight and confirmed events

**The household's question:** “When did Luna's weight start changing, and what did we record around then?”

**Sketch:** Dots joined only across a normal recorded interval, with local date on the bottom and **kg** on the side. Keep the vertical scale visible and do not exaggerate a small change by hiding the axis range. A household-confirmed annotation, such as “Changed food,” is a labelled vertical marker; a vet visit can appear as a separate dated marker without being called the cause. A table lists each date, weight, and linked note or visit. Do not combine pets on one line by default.

**Data needed:** `pets.weigh_ins.pet`, `day`, `weight`, unit, correction history; `pets.vet_visits` dates; person-confirmed `core__annotations` linked to Luna. The shipped Pets module records weigh-ins and vet visits, but the annotation core is future work. A single weigh-in shows one dot, not a trend. A suspected trend or question-loop prompt waits for the Analysis minimum of about 20 usable points.

**Plain text:** **“Luna: 4.8 kg on 1 September and 4.4 kg on 27 October, from 20 weigh-ins. Your note says food changed on 5 September.”** This is a record summary, not a diagnosis. With few observations: **“3 weigh-ins recorded. Keep the dates visible; there is not enough history to describe a trend.”**

## 4. Readiness questions looked at

**The household's question:** “What have we actually reviewed together?”

**Sketch:** A small stepped line or paired month-end bars showing **questions looked at / questions that fit** for each month-end. Print the numerator and denominator beside every point, such as **“12 of 18 looked at.”** A click opens the list of Yes, Not yet and household-confirmed Not relevant answers with dates; a matching Stock or People record alone never moves the line. If a new prompt version or changed household makes denominators incomparable, separate the spans with a labelled break rather than joining them.

**Data needed:** Versioned readiness prompt IDs, applicability and household answer history, with month-end snapshots and review dates. These are draft records, not shipped. The answer `not_yet` means the question was looked at, not that the household is ready. Store the prompt version with each snapshot and never expose private Medical detail in hover text or a general chart.

**Plain text:** **“12 of 18 questions looked at by 31 October; 7 answered Yes. This shows what you reviewed, not how safe you are.”** Before the first answer: **“No questions reviewed yet. Start with one.”**

## Shared reading rules

- Each chart has a text heading that states the measure, unit, period, data coverage and household scope. A “Show records” table provides the same values and linked evidence without requiring a chart.
- Tooltips work by keyboard focus and touch as well as pointer; never rely on colour alone. Use readable labels, visible focus and a text summary that updates when the selected period changes. Honour reduced-motion preferences; no animated transitions are necessary.
- Missing or excluded dates remain gaps. Do not interpolate, extend a final line to today, or convert an unknown into zero. Show a later correction on both chart and table. Explain any changed calculation basis.
- Let the household choose a period and print/export the table. Keep sensitive pet or readiness details off general Home cards and shared printouts unless the household deliberately opens that chart.

**Source:** Internal graphing and analysis rules in [`docs/DESIGN.md` sections 10.1–10.4](../../../docs/DESIGN.md), checked 2026-11-17. Shipped fields checked against [`modules/stock/tables.toml`](../../../modules/stock/tables.toml) and [`modules/pets/tables.toml`](../../../modules/pets/tables.toml), same date. The example numbers are made up; no outside health or emergency claim is made.
