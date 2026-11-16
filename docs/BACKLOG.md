# Backlog: Corey's feedback and what happened to it

Everything Corey notices while using the dashboard goes here, in his words where
possible, so nothing is lost. Lane A works through it in order; scheduled work
sessions read this page first. Newest at the top of each section.

## Open

| Date | Feedback | Plan |
|---|---|---|
| 2026-11-16 | "Pets is still lacking a lot": only People and Stock are switched on. | Promote the Pets draft (moved forward from M5): pets with name and kind in setup, weigh-ins, food, medicine, vet visits; pet food as Household stock. |
| 2026-11-16 | Stocktake should be: pick "Kidney beans" from a list (type a new one only if missing), location Kitchen › Pantry › Shelf 3, quantity 5, use by 20/05/27. | Lane B batch 3, tasks 1 and 2: a catalogue of common goods (with care over drinking, filtered and distilled water) and a Home layout module with nested places; Lane A then builds type-ahead picking and nested places. |
| 2026-11-16 | Layered use-by dates: 3 tins expire in a month, 10 in six months. | Lane B batch 3, task 3 drafts "lots" (an item's amount split by use-by date and place); Lane A builds the core support. |
| 2026-11-16 | A Home layout module is needed. | Lane B batch 3, task 2 (rooms, storage and spots; exits, shut-offs and safety equipment; an "Our home" sheet). |
| 2026-11-16 | "There is still a lot to add and update, manage." | Lane B batch 3 (docs/WORKSTREAMS.md) drafts the next modules and content; Lane A polishes and integrates; then a UX round with Corey. |

## Done

| Date | Feedback | What changed | Pull request |
|---|---|---|---|
| 2026-11-16 | The Country drop-down worked differently from the other choices. | Country is a normal drop-down; "Somewhere else" lets you type it. | Setup and Save and exit fixes |
| 2026-11-16 | No state was chosen automatically. | State is a drop-down that follows the country, pre-chosen from the computer's time zone where that pins it down (works offline). | Setup and Save and exit fixes |
| 2026-11-16 | "Close safely" is too vague; it should say save and exit. | Renamed "Save and exit" everywhere: the page, the launcher, the README and the docs. | Setup and Save and exit fixes |
