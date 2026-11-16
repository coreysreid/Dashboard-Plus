# 0049. Places can sit inside other places, and show their full path

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey), from Corey's stocktake request and Lane B's Home layout draft

## In plain words
A place can now be inside another place: Shelf 3 inside the Pantry, inside the
Kitchen. Wherever a place appears (the stock list, the drop-down when you add an
item, a place's own page, the printed supplies sheet) it reads **Kitchen ›
Pantry › Shelf 3**. Move the Pantry and everything on its shelves moves with it.
You can stop at any level: "Garage" is fine on its own.

## What we chose
- One Places list where each place may name the place it is "Inside", as
  Lane B recommended, instead of fixed room, storage and spot levels. A box on a
  shelf in a cupboard in the garage needs a fourth level.
- A general core feature declared in a module's files (`parent` in
  tables.toml, DESIGN 5.6), so Home layout and other modules can nest records
  too.
- Saving refuses a place inside itself (or inside something it contains) and
  more than eight levels.
- A room with places still inside it can't be deleted; move or delete those
  first.
- Built into Household stock's existing Places for now (migration 0004).
  Existing places stay as they are, as top-level places; nothing is split
  or renamed automatically.

## Why we chose it
- Corey's stocktake: "kidney beans, location kitchen, sub location pantry, sub
  location shelf 3". Several rooms have a "Top drawer"; only the full path
  says which.
- Putting it in the core means the path shows the same everywhere with no
  module code.

## What else we considered
- Three fixed columns (room, storage, spot): simpler forms, but it breaks on
  a fourth level and repeats the same place in every module.
- Moving places into a new Home layout module first: the right long-term home
  (with exits, shut-offs and safety equipment), but it means moving every
  item's place link between modules. Doing nesting first gives Corey the
  result now; the move to Home layout can follow with a backup and a way back.

## What this costs us (the downsides)
- Showing a path looks up each parent; fine for a household's few hundred
  places, worth caching if that grows.
- Nothing yet guides "room, then storage, then spot" when adding places.

## How hard it is to undo
Easy. Removing `parent` leaves places as a flat list; the "Inside" values stay
stored.

## We should revisit this if
- Home layout is promoted: Places should move there, shared by Stock, Medical
  and the "Our home" sheet.
- Households want to add a whole path in one go ("Kitchen › Pantry › Shelf 3"
  typed and created at once).
