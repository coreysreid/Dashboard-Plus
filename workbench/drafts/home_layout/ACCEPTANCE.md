# Nested places: acceptance checks for Lane A

Checked against `main` at `f93471e`, `docs/DESIGN.md` section 5.6 and the three made-up example files on **2026-11-17**. These are expected household-visible results that Lane A can turn into tests. The shipped Stock Places table already has an `inside` link, full-path display and cycle checks. The separate Home layout module and its `kind` field are still drafts. The mapping below describes intended kinds; the current Stock table does not store them.

## Numbered checks

1. **Earlier flat data opens intact.** Start from a pre-nesting example with a Stock place named `Kitchen pantry shelf` and a Kidney beans item linked to its ID. Upgrade the module. The place remains one top-level row with that exact name and notes, the item keeps the same place ID and amount, and its displayed place is `Kitchen pantry shelf`. Do not guess separators or split a name on upgrade. A household may later organise it manually.
2. **A full path appears everywhere a place is used.** Make Kitchen, Pantry inside Kitchen, and Shelf 3 inside Pantry; put Kidney beans on Shelf 3. The Places list, Shelf 3 record page, Stock item list and form, Stock in and out's linked item context, and printed Emergency supplies sheet show **`Kitchen › Pantry › Shelf 3`** where a place is named. They must not show only `Shelf 3`. The place dropdown groups it after Kitchen and Pantry by full-path order. Repeat with another `Shelf 3` under Garage; both are distinguishable.
3. **Find by any path part.** With more than eight places, type `Kitchen`, `Pantry`, and `Shelf 3` separately in a Stock item's place find box. Each search offers `Kitchen › Pantry › Shelf 3`; `Garage` excludes that path and offers the Garage shelf. Typing a substring in the middle of a path works. Choosing the result saves the same place ID, not a new place. A household can still add a missing place from the form.
4. **Moving a parent moves its displayed descendants.** Move Pantry from Kitchen to Garage. Pantry, Shelf 3 and every item stored on Shelf 3 now display `Garage › Pantry › Shelf 3`; their IDs, amounts, notes and movement history do not change. Reopen the Stock form and printed sheet to check they show the new path. Move Pantry back and check the original path returns.
5. **Moving a shelf alone changes only its branch.** Move Shelf 3 from Pantry to Laundry. Its item now says `Laundry › Shelf 3`; other Pantry contents still say `Kitchen › Pantry › …`. No stock movement is recorded because only a location changed.
6. **A cycle is refused without partial changes.** Try putting Pantry inside itself, then try putting Kitchen inside Shelf 3. Both saves are refused with **“A place cannot be inside itself or a place it contains.”** Existing paths and item links remain as before. Repeat through form save and any import or API write path; a client-side filter alone is insufficient.
7. **A too-deep path is refused.** Build a path of eight places. Saving a ninth below it is refused with **“This place would make the path too deep. Choose a higher place.”** The original eight and their item links remain intact. This follows DESIGN 5.6's eight-level limit.
8. **Deleting a room that holds places or things is refused.** Put a shelf and an item under Kitchen. Deleting Kitchen is refused while the shelf exists. After moving the shelf away, keep a different item directly in Kitchen: deletion is still refused because the item points to it. Show **“Move the places and things kept here before deleting Kitchen.”** Deleting or moving one branch must not silently delete or strand stock. If the room is empty, deletion follows the normal recoverable delete path.
9. **Names belong to the household.** Create `Top drawer` under Kitchen and another under Bedroom. Both save and remain distinct in the picker and sheets. Rename Kitchen to Galley: only paths beneath that room change. No row in the [suggested places list](places.csv) is created automatically on setup, and no household's chosen name is overwritten by a later list update.
10. **Example households map row by row.** Load each current example into an empty temporary folder. Every row below has the stated full path; linked Stock items keep the indicated count at that exact path. No place is lost or merged with another. A root row has no parent; `room`, `storage` and `spot` are draft kinds for a future Home layout migration. For older saved households, check 1 still applies: their flat places remain roots until a person chooses a parent.

## Current example-place mapping

The number in the last column is the count of Stock items directly linked to that place in the current example file, not all items in its descendants.

| Household | Existing row name | Intended kind | Full path after loading the current example | Direct Stock items |
|---|---|---|---|---:|
| Smith | Kitchen | room | Kitchen | 0 |
| Smith | Laundry | room | Laundry | 0 |
| Smith | Garage | room | Garage | 0 |
| Smith | Bathroom | room | Bathroom | 0 |
| Smith | Car | room | Car | 0 |
| Smith | Backyard | room | Backyard | 0 |
| Smith | Pantry | storage | Kitchen › Pantry | 9 |
| Smith | Laundry cupboard | storage | Laundry › Laundry cupboard | 7 |
| Smith | Garage shelves | storage | Garage › Garage shelves | 5 |
| Smith | Bathroom cabinet | storage | Bathroom › Bathroom cabinet | 3 |
| Smith | Car boot | storage | Car › Car boot | 1 |
| Smith | Garden shed | storage | Backyard › Garden shed | 1 |
| Smith | Shelf 3 | spot | Kitchen › Pantry › Shelf 3 | 1 |
| Garcia | Kitchen | room | Kitchen | 0 |
| Garcia | Hallway | room | Hallway | 0 |
| Garcia | Main bedroom | room | Main bedroom | 0 |
| Garcia | Car | room | Car | 0 |
| Garcia | Basement | room | Basement | 0 |
| Garcia | Kitchen cabinets | storage | Kitchen › Kitchen cabinets | 8 |
| Garcia | Hall closet | storage | Hallway › Hall closet | 8 |
| Garcia | Under the bed | storage | Main bedroom › Under the bed | 1 |
| Garcia | Bathroom | room | Bathroom | 3 |
| Garcia | Car trunk | storage | Car › Car trunk | 0 |
| Garcia | Storage locker | storage | Basement › Storage locker | 4 |
| Taylor | Kitchen | room | Kitchen | 0 |
| Taylor | Hall | room | Hall | 0 |
| Taylor | Outside | room | Outside | 0 |
| Taylor | Kitchen cupboard | storage | Kitchen › Kitchen cupboard | 5 |
| Taylor | Under the sink | spot | Kitchen › Under the sink | 2 |
| Taylor | Hall cupboard | storage | Hall › Hall cupboard | 4 |
| Taylor | Bike shed | storage | Outside › Bike shed | 1 |

**Home layout hand-off:** When Lane A later moves Stock Places into the Home layout module, preserve place IDs or a complete old-ID-to-new-ID mapping and every Stock link in one transaction. Back up first, offer a way back, and compare the row-by-row paths and direct item counts above after migration. The core currently nests Stock places; cross-module shared places and a picker from `places.csv` still need integration as described in `NOTES.md`.
