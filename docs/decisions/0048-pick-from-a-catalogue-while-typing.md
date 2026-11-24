# 0048. Pick goods from a list while typing, with your own items first

- **Status:** Accepted
- **Date:** 2026-11-16
- **Decided by:** Claude (technical decision delegated by User 1), from User 1's stocktake request and Lane B's catalogue

## In plain words
When you add a stock item, typing "kid" offers **Kidney beans**. Picking it fills
in the kind (Pantry) and usual unit (tins). If you already have Kidney beans, that
comes first, marked "you already have this: open it", so you don't end up with
two. You can always keep exactly what you typed. On *Stock in and out*, the
long list of items gets a box to type into, and offers to add a new item when
nothing matches.

## What we chose
- Lane B's 800-good catalogue ships as `modules/stock/catalogue.csv`. Modules
  name a CSV with `suggest_from` in `labels.toml`; it stays plain text that a
  household or helper can read and extend.
- Matching runs on this computer, with no internet: the household's own
  records first, then the start of a name, then any word, then other names
  (tinned/canned, capsicum/bell pepper). Case, accents and punctuation are
  ignored; a simple plural is tried.
- Picking fills only empty text fields, and sets choice fields and
  yes/no fields such as "Safe to drink", so distilled water is not counted as
  drinking water by accident.
- Lane B keeps improving the list in `workbench/drafts/catalogue/`; Lane A
  copies it into the module when a round is accepted.

## Why we chose it
- User 1's stocktake is "pick Kidney beans, Kitchen › Pantry › Shelf 3, 5, use by
  20/05/27". Typing names by hand is slow and creates near-duplicates
  ("kidney beans", "Kidney Beans 400g").
- Lane B's UX check found the Stock in form started with a long, unfiltered
  list (J2).

## What else we considered
- The browser's built-in suggestion list (`datalist`): no way to show "you
  already have this" or fill other fields, and it behaves differently in
  each browser.
- Making every item come from the catalogue: households have their own
  things, and names differ by country.

## What this costs us (the downsides)
- A little script in the form, and a 60 KB list loaded with the module.
- The catalogue and the workbench draft can drift until Lane A copies a round
  across.

## How hard it is to undo
Easy. Remove `suggest_from` from labels.toml; typing works as before.

## We should revisit this if
- Households add many of their own goods: they could be offered as their own
  list across all their items.
- Barcode or camera scanning arrives (Lane B noted the idea).
