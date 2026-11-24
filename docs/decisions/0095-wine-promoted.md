# 0095. Wine collection is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
A household can now keep a small wine list: each wine, how many bottles it has
and where they are kept, and tasting notes. You type the bottle count yourself.
Opening a bottle or saving a tasting note does not change it until you do. There
is no advice about when to drink, how to store or what anything is worth. The
price you paid and your tasting notes are ordinary details: they appear in a
spreadsheet export and to a helper you allow Wine, and the forms say so.

## What we chose
- A new module, `modules/wine/`, built on Lane B's draft
  (`workbench/drafts/wine/`, now removed; its notes, acceptance checks and
  example rows are in git history). Three lists: wines, bottles and tasting
  notes. It needs no other module. The draft's one migration was renamed
  `0001_first_tables.sql` like the others; its contents did not change.
- **Counts stay manual.** "Bottles on hand" is a number you type, zero is
  allowed, and a tasting note never takes a bottle away. A test checks that
  saving, deleting or restoring a note or a bottle row leaves the count alone.
  Two rows for the same wine (a shelf and a rack) stay two rows; nothing adds
  them up.
- **Where kept is free text.** It is not a link to Household stock Places, so
  it never follows a place that is renamed or moved. A gap asks "Where are the
  bottles of Evening Red kept? Write a shelf or rack if it would help you find
  them." until something is written.
- **Price paid and Tasting notes are ordinary fields, not private.** This is
  the small first release Lane B scoped. A helper granted Wine can read them
  and the general export includes them. The form help says so and nothing says
  they are secret. A test checks that the help words make no promise of
  privacy, and that the sheet leaves both out.
- **A wine with bottles or tasting notes cannot be deleted** (the links restrict
  deletion), so history is not lost by accident. The refusal says which lists
  still point at it. After they are deliberately removed, the wine can be
  deleted and restored as usual.
- **Dates use the household's order**, and an impossible date or the other
  order is refused, never swapped. No order between "Bought on" and "Tasted on"
  is enforced: they are in different lists and a bottle may be tasted before it
  is recorded, or be a gift.
- **No reminders, no advice.** There is no drink-by date, so nothing is added to
  Needs attention except the one place question. No growing, storage, buying,
  drinking, health or value wording is stored; a test checks the files.
- **A Wine collection sheet** prints wine, count, place and bought on, with an
  intro saying it is a snapshot to check against the bottles. No price, notes,
  producer or value.
- **Home page:** Wines is the main list and the other two are links
  (decision 0056). Bottles and tasting notes are named after their wine
  ("Evening Red, 2 at Pantry shelf") wherever they are listed.
- **Example households:** the Smiths ("Evening Red", 2 bottles in the Pantry)
  and Sam Taylor ("Weekend Rosé", 1 bottle in the Kitchen cupboard). The
  Garcias do not use Wine, so the example that shows it switched off stays.
  The draft's Garcia rows were not used. All names and notes are invented.
- Tests: `tests/test_module_wine.py` covers each of Lane B's 15 checks that a
  computer can run (loading, required fields, edits, counts, the gap, number and
  date refusals, text shown as text, export and helper reads, the sheet, deleting
  and restoring, switching off and on, the examples, and restoring a backup with
  Undo). Reading a screen at 320 pixels and printing on A4 and Letter are
  checked in the browser check and screenshots.

## Why we chose it
- It is the smallest of the waiting drafts and uses only features that are
  already shipped, so it proves a module can be switched on with no core change.
- Typing the count keeps the record honest. A tasting note that quietly took a
  bottle away would give a wrong number that looks right.
- Saying plainly that price and notes are exported, instead of hiding them
  half-way, lets the household decide what to type, and keeps the page from
  promising more privacy than it gives.

## What else we considered
- **A "Mark opened" button that takes one bottle off.** The one-step actions
  shipped so far only set fields (decision 0075), and "one fewer" is a
  calculation, not a field. A later movement history needs its own household
  test. Refused for now.
- **Link Where kept to Household stock Places.** Neat, but it would make Wine
  need Stock and force a choice of Place for every rack. Free text matches how
  people write "top shelf, left". If households ask, it can be added as an
  optional link with a migration that reviews repeated names.
- **Private price and notes.** Needs a schema change and tests of the first page,
  helper reads and export. Not promised by this release.
- **A drink-by date with a reminder.** It would be the household's own date, but
  the draft deliberately has none and it invites the "drink within" advice we
  do not want to hold. Not added.
- **Putting Wine in every example household.** Garcia stays without it so one
  example shows an ordinary household that never switched it on.

## What this costs us (the downsides)
- The count can be wrong. Nobody is told when a bottle is opened and the count
  is not updated; the sheet says it is a snapshot.
- Free-text places are not shared. "Rack A" and "rack a" are different words and
  moving a Place in Stock does not change them.
- Price paid and tasting notes are readable by a helper granted Wine and are in
  every export. A household that wants them private cannot have that yet.
- Nothing checks that a tasting is not dated before the wine was bought.
- A wine that has been drunk completely still needs its bottle rows and notes
  removed before it can be deleted.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the folder.
Nothing in any other module was changed. The only edits outside the module are
the example files, a test that used "wine" as a made-up missing part (now
"stargazing"), and the screenshot stages.

## We should revisit this if
- Households keep forgetting to update the count (a one-bottle action or a
  movement history).
- Households want to find a wine by a shared place, or hide price and notes.
