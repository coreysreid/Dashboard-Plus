# 0057. "Which batch" follows the item, and says what leaving it blank does

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
On the "Stock in and out" form, "Which batch" used to list the batches of
every item, and its blank choice read "(none)". It now lists only the batches
of the item chosen, and changes as soon as a different item is picked. The
blank choice says what will happen: "Start a new batch" for stock in, "Use the
batch with the earliest use-by date" for taking stock out. "Use by" and "Where
you put it" disappear once a batch is chosen, because they only describe a new
batch.

## What we chose
- **The list follows the item.** Every batch is still sent with the page, each
  marked with the item it belongs to. A few lines of script in the form show
  only the chosen item's batches and update when the item changes. No page
  reload, no extra request, no script library.
- **The form works this out from the module's files.** A link whose table has
  a `total` rule (batches add up into items) is related to the other link on
  the same form that points at the same table (the movement's item). Nothing
  names "stock" or "lots" in the program, so another module with batches gets
  the same behaviour.
- **With no item chosen, no batches are offered** and one line says "Choose the
  item first to see its batches." An item with none says "This item has no
  batches yet."
- **Picking a different item clears a batch chosen for the previous item.** A
  batch that was already saved, or sent back by a refused save, stays in view
  when the page opens, so nothing is dropped unseen.
- **The blank choice is worded from the `adjusts` rule:** reasons listed in
  `adds` start a new batch (`new_batch`); the others take from the earliest
  date (`oldest_first`). The words follow "Reason" as it changes. A module can
  change them in labels.toml with
  `blank = { adds = "…", takes = "…" }`; Household stock uses this only to
  write "use-by" with its hyphen. When changing a saved record the blank
  choice reads "Keep the batch it has", which is what the program does.
- **"Use by" and "Where you put it" are hidden when a batch is chosen**, rather
  than left on show with a note. They apply to a new batch only (they are the
  columns named in `new_batch`), and a box that does nothing is clearer gone
  than explained. Their help now reads "For the new batch."
- **The program still checks when saving.** With scripts switched off the
  full list is shown, and a batch of another item is refused as before: "is a
  batch of a different item. Choose one of this item's batches, or leave it
  blank."
- The find box above a long list only searches the chosen item's batches, and
  only appears when that item has more than 8. It no longer offers to "add a
  new one" for batches: a new batch is started by leaving the box blank.

## Why we chose it
- A household picking a batch of kidney beans should not scroll past every
  other item's batches, and could previously pick the wrong one and be refused.
- "(none)" said nothing; the program's actual behaviour differs by reason, so
  the words must too.
- Filtering in the page is instant and needs no new route to keep safe.
- Working it out from `total` and `adjusts` keeps modules as plain files
  (decision 0053) with nothing new to declare.

## What else we considered
- **Ask the program for the item's batches each time the item changes.** More
  moving parts and a new route, for lists that are small on one computer.
- **Reload the page when the item changes.** Loses what was typed and feels
  slow.
- **Declare the relationship in labels.toml** (`filter_by = "item"`). One more
  thing for module writers to get wrong, when the files already say it.
- **Keep "Use by" and "Where you put it" on show with a note** ("ignored when
  a batch is chosen"). More reading, and an invitation to type something that
  is then thrown away.
- **Keep a batch of the previous item selected after the item changes.** The
  save would be refused; clearing it is kinder.

## What this costs us (the downsides)
- All batches that still hold something (up to 500) are sent with the form,
  as before. A household with more than that would need a search instead.
- Hiding choices in a drop-down relies on the browser; they are also switched
  off so a browser that still shows them will not let them be picked.
- A use-by date typed before a batch is chosen stays in the hidden box and is
  saved on the stock-in record, though it does not change the batch.
- With scripts off the list is the old full one; the check on saving is the
  safeguard.
- The core's default words mention "batch", so a module using this for
  something not called a batch should set its own with `blank`.

## How hard it is to undo
Easy. Remove the script and the `data-` marks in `form.html` and the three
small functions in `web/display.py`; no stored data changes.

## We should revisit this if
- A household has so many batches that the form is slow to open.
- Another module's form has two links that could both be "the owner" and the
  wrong one is followed.
