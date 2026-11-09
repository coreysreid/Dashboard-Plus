# 0060. Keep the garden example outside installed modules

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Codex (working from Corey's Lane B brief)

## In plain words
The garden shows how to make a useful module without adding it to every household's dashboard.

## What we chose
Keep the files-only garden under `examples/garden/`, with five linked record types and a printable plan. Test it by copying it into a temporary modules folder and saving made-up records.

## Why we chose it
- A household can copy a complete working pattern without seeing garden screens by default.
- Linked plantings and harvests show more than a single flat list.

## What else we considered
- Put it in `modules/`: that would make it available to everyone during normal startup.

## What this costs us (the downsides)
- Someone who wants the garden must copy it into their own modules folder.
- The guide and example must be kept in step with the module contract.

## How hard it is to undo
Easy. Move the example into installed modules if the product later chooses to ship it by default.

## We should revisit this if
- Most households ask for the garden during first setup.
