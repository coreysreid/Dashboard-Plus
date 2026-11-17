# 0054. Home layout is switched on, and uses the places the household already has

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The household can now write down its ways out, where the water shut-off, power
board and gas shut-off are, where the smoke alarms, extinguishers and go-bags
are, and where the meters are. Each one points at a place the household already
has (Garage › Garage shelves), and a one-page "Our home" sheet prints them
together. *Worth filling in* asks "Where is the water shut-off?" until it is
answered, and *Needs attention* says when a check the household planned is due.

We chose to keep places where they are, in Household stock, because moving them
would have meant rewriting every stock item, batch and first aid kit in a
household's saved data for no change the household could see.

## What we chose
- A new module, `modules/home_layout/`, built on Lane B's draft
  (`workbench/drafts/home_layout/`, now removed; its notes, acceptance checks
  and place-by-place maps are in git history). It has four lists: ways out,
  shut-offs and power board, alarms and safety equipment, and meters.
- **No household data moves.** Home layout `requires = ["stock"]` and every
  "Where it is" links to the existing `stock.places`. Places keep their ids,
  their nesting and their full paths. Stock items, batches, stock in and out
  and Medical kits are not touched: the only database change is four new,
  empty tables.
- A place cannot be deleted while a way out, shut-off, alarm or meter points at
  it, the same rule Stock items and first aid kits already follow.
- **Asking, not asserting.** Questions are asked only where nearly every home
  has an answer: a way out, the water shut-off, the power board, a smoke alarm.
  Gas is not asked about, because many homes have none. First aid kits stay in
  Medical; the sheet says so instead of listing them twice.
- **No invented safety intervals.** "Test or check again by" is a date the
  household types, from the maker's instructions, local fire service advice or
  its own plan. Nothing is worked out from the last test, and a blank date
  raises no reminder. Only smoke alarms are asked "When do you plan to test it
  again?".
- The draft's one-row "Our home" table (number of floors, way out from
  upstairs) was left out. Setup already asks the number of floors, and the way
  out from upstairs is written on each way out ("Floor", "How to get there").

## Why we chose it
- **Nothing a household has entered is put at risk.** The move needed one
  all-or-nothing change across two modules' tables (31 places, 63 stock links
  and 3 kit links in the examples alone, plus batches and history), a backup
  first and a tested way back. Not moving needs none of that.
- **The household sees the same thing either way.** Kitchen › Pantry › Shelf 3
  already shows in full everywhere, can be moved, and refuses loops (decision
  0049). Which module's table holds the row is invisible on screen.
- **It is quick to undo**, because nothing was changed that would need
  changing back.
- We looked for a concrete way this fails a household and found only one small
  one, listed under costs: Home layout cannot be used without Household stock.

## What else we considered
- **Lane B's plan: move places into a shared `home_layout.places`.** Its
  benefit is tidiness: places would belong to the module named after the home,
  and each place could carry a kind (room, storage, spot). It lost because the
  kind changes nothing on screen today, and the cost is a risky rewrite of
  saved data. Lane B's maps remain in git history if this is ever needed.
- **Home layout with its own separate places.** Refused: the household would
  have two "Kitchen"s to keep in step.
- **Typing the place as plain words.** Refused: it would not follow a rename or
  a move, and the sheet could not show the full path.
- **Working out the next smoke alarm test from the last one.** Refused: the
  right interval depends on the device and local advice, and we have no source
  that fits every household.

## What this costs us (the downsides)
- Home layout needs Household stock switched on, even for a household that
  only wants the "Our home" sheet. Places are listed under Household stock,
  which is not where someone might first look for "rooms".
- Places have no "kind" (room, storage, spot), so the dashboard cannot suggest
  "add a room first, then a cupboard" from the data.
- Four more lists in the menu, and one more module to maintain.
- Lane B's readiness draft points one question at the left-out "Our home"
  table; it needs to point at ways out instead before that draft is promoted.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. If places do later need to move, Lane B's promotion maps describe how,
and the Home layout links would be repointed in the same backed-up change as
Stock's and Medical's.

## We should revisit this if
- Households want Home layout without Household stock.
- A feature needs to know whether a place is a room, a cupboard or a spot.
- Several more modules link to `stock.places` and "Places" under Household
  stock starts to confuse people.
