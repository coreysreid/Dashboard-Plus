# Home layout design and integration notes

## What a household should see

A place picker should show **Kitchen › Pantry › Shelf 3**, not just “Shelf 3”. Adding a place should start with a room or area, then offer storage inside it, then an optional spot. A household may stop at any level: “Garage” or “Garage › Grey shelves” is useful too. The form should prevent a place being put inside itself or one of its descendants. Rename or move a parent and every displayed child path should update automatically.

“**Our home**” records how many floors there are, the route out from upstairs, every way out, the water main, gas shut-off if there is one, the power board, smoke alarms and their test or battery dates, fire extinguishers and blankets, first aid kits and go-bags. The printable sheet puts exits, shut-offs and safety items together. Dates for a next check are entered by the household based on its device and local guidance; this draft makes no fixed interval claim. It stores locations and household plans, not fire safety instructions.

## One self-link versus fixed levels

| Model | Benefit | Cost |
|---|---|---|
| One `places` table with `parent` pointing to another place | Handles a room, cupboard, shelf, drawer or box at any depth, and Stock can have one place link. Moving a pantry updates all child paths. | Core must traverse the tree, reject cycles, validate hierarchy, sort by path, and make pickers display the full path. |
| Separate room, storage and spot columns or tables | Three-step form is simple when every home fits exactly three levels. | A box inside a cupboard inside a garage shelf needs a fourth level; the same place must be assembled separately for Stock, safety equipment and sheets. |

**Recommend the self-linking table.** The `kind` choice gives a friendly room/storage/spot starting point without a hard depth limit. The current declarative contract accepts the self-link but cannot ensure that a storage place sits under a room or that a spot sits under storage. The UI may guide those choices, while the core must enforce cycle prevention and a sensible maximum path length. The screen should show the full path in every picker, list and printed sheet; using only the linked record's `name` is ambiguous when several rooms have a “Top drawer”. The core's current sheet contract prints `place` as the linked name, so the draft sheet is **not ready to use as an emergency reference** until full paths print. A printable sheet should include a “checked on” date and be reviewed after a move.

The home name table is intended as one household profile. The current core does not enforce a single row; Lane A should either enforce that for `homes` or explain multiple buildings and how their locations are separated. Current `gaps` cannot express “ask for an upstairs escape route only when storeys > 1”, so the draft keeps this as form guidance, not an inaccurate universal gap.

## Moving Household stock places

Lane A should migrate every existing `stock.places` row into a root `home_layout.places` row, preserving its visible name and notes. Keep a mapping from old place ID to new place ID and repoint every `stock.items.place` reference in the same transaction. Do not split names like “Kitchen pantry shelf” automatically; a person can later move the new root under Kitchen and rename it. Where two old places share a name, retain separate IDs and ask the household to sort them out. Only after successful migration should Stock use the shared Home layout place picker. A rollback must restore the original place IDs and item links from a backup or migration mapping. Do not delete the old places table while another module might still link to it (Medical currently does).

## Exact core work requested

1. Support a shared place link from Stock and Medical to `home_layout.places`, and migrate old links without loss.
2. Compute each place's full path, detect cycles on save/import, display it in pickers, lists and printable sheets, and refresh descendant paths after moves.
3. Permit a choice of an existing path or “Add a place” within the Stock entry flow, with room → storage → spot suggestions and no required fixed depth.
4. Render the sheet's linked `place` columns as full paths. Allow a household to confirm its sheet before relying on it.
5. Handle the home profile as one home or explicit multiple homes; conditional upstairs questions need a condition-aware gap/prompt mechanism.

## Example household sketches

The made-up Smith home could have Kitchen › Pantry › Shelf 3 and Garage › Grey shelves; the Garcia apartment could have Apartment › Entry cupboard › Go-bags; Sam Taylor's flat could stop at Kitchen › Cupboard. These are illustrative, not imported into a real household.
