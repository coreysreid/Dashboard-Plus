# Backlog: Corey's feedback and what happened to it

Everything Corey notices while using the dashboard goes here, in his words where
possible, so nothing is lost. Lane A works through it in order; scheduled work
sessions read this page first. Newest at the top of each section.

## Open

| Date | Feedback | Plan |
|---|---|---|
| 2026-11-16 | Stocktake should be: pick "Kidney beans" from a list (type a new one only if missing), location Kitchen › Pantry › Shelf 3, quantity 5, use by 20/05/27. | Lane B batch 3, tasks 1 and 2: a catalogue of common goods (with care over drinking, filtered and distilled water) and a Home layout module with nested places; Lane A then builds type-ahead picking and nested places. |
| 2026-11-16 | A Home layout module is needed. | Lane B batch 3, task 2 (rooms, storage and spots; exits, shut-offs and safety equipment; an "Our home" sheet). |
| 2026-11-16 | "There is still a lot to add and update, manage." | Lane B batch 3 (docs/WORKSTREAMS.md) drafts the next modules and content; Lane A polishes and integrates; then a UX round with Corey. |

## Done

| Date | Feedback | What changed | Pull request |
|---|---|---|---|
| 2026-11-16 | Layered use-by dates: 3 tins expire in a month, 10 in six months. | Stock is kept in batches, each with its own amount, use-by and place. The item adds them up; stock in starts a new batch; using some takes the earliest use-by first; Needs attention warns about each batch. Existing items became one batch each, after a backup (decision 0053). | Batches |
| 2026-11-17 | (Lane B UX check) A first aid kit in the car stopped the question "Is there a first aid kit at home?"; a date typed in the other country's order gave no hint. | Each kit now says whether it is kept at home, in a vehicle or somewhere else; the question stays until a kit is kept at home. A date typed the other way shows "Use DD/MM/YY, for example 20/05/27." | Kit at home, date hint |
| 2026-11-16 | Use by typed as 20/05/27. | Dates are typed and shown your country's way: 20/05/27 in Australia, 05/20/27 in the US, saved the same either way. The form shows the date in words while you type, and impossible dates like 31/04/27 are refused (decision 0052). Layered use-by dates are next. | Dates your way |
| 2026-11-17 | (Lane B) Medical draft ready to promote; the example loader failed on kit checks. | Medical readiness is switched on: first aid kits and where they are, kit checks, training renewals, a "First aid at home" sheet, and "Is there a first aid kit at home?" until one is added (decision 0051). | Medical readiness |
| 2026-11-17 | (Lane B accessibility review and nested-places UX check) Suggestions not announced to screen readers, faint input borders, errors not tied to fields, emergency sheet too wide for a phone, many links all called "Open", unlabelled groups; long place lists losing a parent's path. | All fixed: suggestions and errors are announced, a summary links to each answer to check, borders meet contrast, sheets reflow on a phone, links say what they open, setup groups have names, Places list and search use full paths. | Accessibility and place paths |
| 2026-11-17 | (Lane B UX check) Typed-in water such as flushing water counted as drinking water unless unticked; bottles were counted as litres. | Water now asks "Is this water safe to drink now?" with neither answer picked; water recorded in bottles is left out and named until its litres are entered. Places get suggestions while typing; the catalogue has 805 goods. | Safer water, place suggestions |
| 2026-11-16 | Location as Kitchen, sub location Pantry, sub location Shelf 3. | A place can be inside another; everywhere shows Kitchen › Pantry › Shelf 3; moving a cupboard moves its shelves; a place can't go inside itself (decision 0049). Dates your way and batches followed (decisions 0052, 0053). | Nested places |
| 2026-11-16 | Pick "Kidney beans" from a list while typing, and type a new one only if missing. | Typing a stock item's name offers 800 common goods (and your own items first); picking fills in its kind, unit and whether it's drinking water. Stock in and out gets a find box and "add a new one". Places (Kitchen › Pantry › Shelf 3) and use-by lots are next. | Pick from a list while typing |
| 2026-11-16 | (Lane B UX check) Water kept for flushing counted towards days of drinking water. | Water items have "Safe to drink" (shown only for water); only drinking water counts, and the home card says what wasn't counted. Existing water stays counted. | Drinking water only |
| 2026-11-16 | "Pets is still lacking a lot": only People and Stock were switched on. | Pets is now a shipped module: setup asks each pet's name and kind; vet, microchip, vaccinations, treatments and medicine with due dates, weigh-ins, vet visits, a pet details sheet (decision 0047). | Pets module |
| 2026-11-16 | The Country drop-down worked differently from the other choices. | Country is a normal drop-down; "Somewhere else" lets you type it. | Setup and Save and exit fixes |
| 2026-11-16 | No state was chosen automatically. | State is a drop-down that follows the country, pre-chosen from the computer's time zone where that pins it down (works offline). | Setup and Save and exit fixes |
| 2026-11-16 | "Close safely" is too vague; it should say save and exit. | Renamed "Save and exit" everywhere: the page, the launcher, the README and the docs. | Setup and Save and exit fixes |
