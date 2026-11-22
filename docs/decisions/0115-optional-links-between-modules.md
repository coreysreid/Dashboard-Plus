# 0115. Optional links between modules: Utilities no longer needs Our home

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Claude (technical decision delegated by Corey)
- **Builds on:** 0099 (Utilities), 0106 (meter place paths; its "Utilities still requires Home layout" is
  replaced here), 0055 (module migrations stay in their own tables), 0074 (helpers see only what they were
  given), 0100 (permanent IDs and the change log), `workbench/drafts/optional_links/` (Lane B, batch 21 item
  102; now in git history)

## In plain words
A household with only internet and a phone can now switch on **Utilities and accounts** with People alone.
Our home (the Home layout list) no longer has to be on. With Our home off, the add form has no meter
picker and says: "Meter places are available if you switch on Our home. You can save this service
without one." A service with no meter says "No meter place linked."

If a service already points at a meter and Our home is switched off, the link is kept exactly as it was.
Lists, the record page, the printed sheet, a spreadsheet export and a helper say only that a meter link is
saved; they show no meter name, room or access detail. Saving other details cannot change or clear the
link. Switch Our home back on and the same meter is shown again. If that meter was deleted meanwhile, the
form says "The linked meter is no longer there. Choose another, or leave it blank." The program never picks
another meter with the same name.

## What we chose
- **`optional_requires` in `module.toml`.** A module lists the modules it may link into but does not need.
  It loads and works while they are off or not installed. Settings only insists on `requires`.
  `modules/utilities/module.toml` now says `requires = ["people"]` and
  `optional_requires = ["home_layout"]` (version 1.1.0). Bills is not promoted: it waits for item 105's
  one-renewal decision, and can use the same contract later.
- **What the loader checks.** A link into a module under `optional_requires` is marked optional. It may not
  be `required` (or `required_when`), may not use `on_delete = "cascade"`, may not be a gap question, and a
  sheet may not print a column through it (`meter.place`): the record must make sense without it. A module
  may not be under both lists. When the optional module is installed it loads first, and the linked table
  (and `with_place` column) must exist there; when it is missing or broken the referring module still
  loads. An optional module that itself requires the referring one is not a loop.
- **Writes are guarded in the record service.** While the linked module is off, any create, change, clear,
  import, helper suggestion or Accept that would set the link to anything other than what is saved is
  refused with a plain reason. Leaving it as saved (or blank on a new record) is fine. The value is never
  looked up in the off module. While it is on, the usual check applies: the ID must be a live record.
- **The form leaves the picker out.** With the module off there is no `<select>`, nothing is read from the
  posted form for that field (a crafted value is ignored), and the field shows one sentence that keyboard
  focus reaches before Save: the "available if you switch on" words for a new record, "No … linked." plus
  those words for a saved record without one, and "A meter link is saved. Switch on Our home to see or
  change it." when one is kept.
- **Reading is neutral.** Lists, the record page, history, sheets and exports show "Meter link saved; switch
  on Our home to see it." for a kept link, and never read the off module's record. Sorting by that column is
  turned off. Helpers were already kept from links into lists they were not given or that are off (0074):
  the field is not in their table description, records or guide, and suggesting it is refused.
- **A missing record is repair, never a guess.** With the module on, a saved ID that is not a live record
  (for example a meter deleted while Utilities was off) shows "The linked meter is no longer there." on
  lists, sheets and exports (with the old ID), and the form offers an empty picker with the repair words.
  Saving with the picker blank is the deliberate clear; choosing a meter saves that one. The gone ID itself
  cannot be saved again. A meter deleted while Utilities is on still clears the link as 0099 says, and
  restoring the meter brings it back.
- **Export and sync keep the exact ID.** The export's "(id)" column keeps the saved ID and its name column
  says the link is saved (or gone); the README explains it. Sync stage 1 keeps the meter's permanent ID in
  the change log and the snapshot while Our home is off, and an edit to another field does not rewrite it.
  Backups and restores copy the value as stored.
- **The household's words** live in the module's `labels.toml` as
  `columns.meter.optional = { off_help, kept_help, kept, none, gone, missing }`. A module that gives none
  gets plain defaults built from the field label and the linked module's title.
- **No database rule for new optional links.** `make_migration.py` writes an optional link without a
  `REFERENCES` clause, so a module whose optional module is not installed can save records. Utilities'
  released migration (0001) is not edited, so its meter column keeps the rule it had.
- Code: `src/dashboard/core/optional_links.py` (states and words), the loader in `modules.py`, the guard in
  `records.py`, the form, list and sort in `web/display.py` and `web/pages.py`, `export.py`, `schema.py` and
  `sync.check`. Tests: `tests/test_optional_links.py`.

## Why we chose it
- A household should not have to switch on a list it does not use to keep a phone number for its internet
  provider. That was the one known reason Utilities forced Our home on (0099, 0106).
- Keeping the saved ID and refusing every change while the module is off means switching a list off is only
  a view, never a quiet loss of a link.
- Words built from the ID alone, never the linked record, mean an off module's names, rooms and private
  access details cannot leak through a placeholder.
- Never matching by name means a deleted meter and a new one with the same name are never confused.

## What else we considered
- **Clearing the link when Our home is switched off.** Simple, but it loses the household's work and the
  link would not come back. Refused.
- **Showing the last known meter name.** Reads an off module and can be stale or private. Refused.
- **Asking again on Needs attention for every service whose meter is gone.** The draft says a quiet repair
  on the form is enough; a reminder per service would be noise.
- **The one-time Settings notice** ("Meter places are available again. Review saved Utilities links when you
  have time.") from the draft is not built: the record page already shows the link again, or the repair
  words, so it is a nice-to-have.
- **Rebuilding Utilities' table to drop its database rule.** A rebuild cannot copy the permanent ID columns
  the core adds afterwards in one static migration, and Home layout ships with every copy, so the rule only
  matters if someone deletes the Home layout folder. Not done.

## What this costs us (the downsides)
- Every page and file that shows a link has one more state to consider; a new surface that reads a link
  directly could miss the neutral words. The record service still refuses the write.
- Utilities' meter column keeps its database rule from migration 0001: if the Home layout module folder were
  removed altogether, Utilities would load but could not save a service. Only switching Our home off is
  supported.
- A meter deleted while Utilities is off leaves a saved ID that only a person can repair; nothing warns
  until the service is opened or listed.
- A spreadsheet export made while Our home is off holds the meter's ID but not its name.
- The household words are per module and per field; a module that gives none gets plainer defaults.
- Helpers with both lists suggest a meter by its local record number, as for every other link, not by its
  permanent ID; that waits for sync.

## How hard it is to undo
Easy. Put `requires = ["people", "home_layout"]` back in `modules/utilities/module.toml` and remove
`optional_requires` and the `optional` words; the core code then sits unused (no module declares
`optional_requires`). No data changes: the meter column was never altered.

## We should revisit this if
- A household is surprised that a link it cannot see is kept, or cannot find how to clear it.
- Bills (or another module) needs an optional link that must be required in some cases.
- A surface is found that shows an off module's name or place through an optional link.
