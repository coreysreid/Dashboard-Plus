# 0077. Home layout gets a private place for codes and access details

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Home layout's "How to get there" and "How to find it" boxes print on the *Our
home* sheet, yet people were typing alarm codes and key-safe numbers into them.
Each Home layout list now has a separate box, "Codes or access details
(private)". It is hidden until you press Show and is never printed. The help
text on the printed boxes now points people to it.

## What we chose
- A new optional private text column, `access_details`, on all four Home
  layout lists: ways out (a key safe or door keypad), shut-offs (a locked
  cupboard), alarms and safety equipment (an alarm panel) and meters (a locked
  meter box). Marked `sensitive = true`, so it follows the rules from decisions
  0055 and 0059: hidden on lists and record pages until Show, left out of
  Needs attention, never in a record's name or a question.
- Label "Codes or access details (private)"; help "Kept private: shown only
  when you press Show, never printed."
- **Not in any sheet.** `sheets.toml` is unchanged and never names the new
  column (the core would let a sheet carry a private column, but only behind a
  Show button; *Our home* must stay an ordinary sheet to hand to a helper). A
  test checks the file and the printed sheet.
- The help on "How to get there" and "How to find it" now says to put alarm
  codes or key-safe numbers in the private box; the meter one says it prints.
- One new numbered migration, `0002_private_access_details.sql`, made with
  `tools/make_migration.py`: four `ADD COLUMN` statements, so no existing
  record changes. The module version is 1.1.0.
- No example household is given a code: the example files stay free of anything
  that looks like one.

## Why we chose it
- Lane B found that people do type codes into printed fields. A warning alone
  ("don't write codes here") leaves them nowhere to put the thing they need
  to remember; giving it a private home is kinder and safer.
- It reuses the private-detail machinery already tested for Vehicles and
  People, so no core change was needed.

## What else we considered
- **One column on one table only.** Simpler, but a locked meter box and an
  alarm panel are as likely as a front door.
- **Making "How to find it" private.** Would stop the printed sheet doing its
  job of telling a helper where things are.
- **Detecting codes in the printed boxes and refusing them.** Unreliable and
  unfriendly; a household could not write "behind the grey shelves, 3 steps".

## What this costs us (the downsides)
- Households who already typed a code into "How to get there" must move it by
  hand. The dashboard does not scan for it, and the old text still prints until
  they do.
- Four more boxes on four forms, most of which will stay empty.
- A code in the private box is kept in the database like other private
  details: the backup holds it, and it is not encrypted on disk until the
  optional data-folder passphrase exists (M3).
- Someone at the computer who presses Show can read it. The sheet being free
  of codes does not make the computer safe.

## How hard it is to undo
Easy. Remove the column from `tables.toml` and write a migration, or leave it
unused. Records without a value are unaffected.

## We should revisit this if
- Households still type codes into the printed boxes (then add a gentle
  reminder on save).
- Other modules need a private place for codes too (then offer one shared
  pattern).
