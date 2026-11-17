# 0059. Private details are sent to the screen only when the person asks

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey), from Lane B's sensitive-detail audit

## In plain words
Details marked private, such as allergies, conditions or a number plate, used
to be hidden on screen behind a "Show" button but were still written into the
page itself. Anyone looking at the page's source, a saved copy of the page, or
a browser add-on could read them. Now a private detail is not in the page at
all until the person presses Show; then just that one detail is fetched from
this computer. Opening a record works the same way, and a printable sheet with
private details first asks "Show it only when you mean to print or share it".

## What we chose
- **Lists:** a private column shows a "Show" button only (and nothing if
  blank). Pressing it fetches that one value from
  `/t/<table>/<id>/reveal?column=<name>`, which answers only for private
  columns and only to this browser's own session. Lists can't be sorted by a
  private column, since the order alone could give values away.
- **Opening a record:** a saved private detail starts as "Private detail
  saved. Show to read or change it." with a **Show private detail** button.
  Saving other changes without opening it leaves it exactly as it was.
- **Sheets with private details:** the first click shows a short page,
  "This sheet includes private health and care details. Show it only when you
  mean to print or share it.", with **Show private sheet** and **Back to
  Home**. That page contains none of the details. The ordinary fridge copy is
  unchanged.
- Not changed here: private details stay in the database, its history and
  backups, as before. That data folder is the household's own and is not
  encrypted; the README says so. A permanent erase needs its own careful
  design (audit, backups and a way back) and is not part of this change.

## Why we chose it
- "Hidden until you choose to show it" should be true of what the browser
  receives, not just what it draws.

## What else we considered
- Leaving the values in the page with a warning: a saved web page or a browser
  add-on would still carry every private detail.
- Encrypting the data folder: a much larger change with its own risks
  (forgotten passphrases); still planned as optional (roadmap M3).

## What this costs us (the downsides)
- One more click to read or edit a private detail.
- The page needs scripts to show a private detail in a list; without them,
  open the record instead (its Show button needs scripts too).

## How hard it is to undo
Easy; the stored data is unchanged.

## We should revisit this if
- Households find the extra click annoying for details they consider
  harmless: let a module mark a column as private-on-sheets-only.
