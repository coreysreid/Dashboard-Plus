# 0117. Bills and insurance beside Utilities, with one reminder per vehicle policy chosen by the household

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Claude (technical decision delegated by Corey). **Corey should confirm the Vehicle insurance
  choice below before this is merged**: it is the first feature that can move where an existing reminder lives.
- **Builds on:** 0058 (Vehicles and its insurance renewals), 0055 (modules stay in their own tables), 0099
  (Utilities), 0100 (what travels), 0107 (Things to do and "due" words), 0111 (gentle checks before saving), 0115
  (optional links), Lane B's draft `workbench/drafts/bills_insurance/` (batch 20 item 88 and batch 21 item 105's
  RENEWAL.md; now removed, in git history)

## In plain words
A household can now keep its bills and insurance policies with the date it wants to check each one: who
provides it (from People), how often it comes, the next date, and, privately, the amount, what it covers, the
account or policy reference and notes. A bill can mention a vehicle or a Place, but needs neither: Vehicles and
Household stock can both be off. Thirty days before the date, Needs attention and Things to do say "bill check
due 16/12/26", "policy check due …" or, for a car, "vehicle insurance review or renewal due …". Nothing works out
the next date from "how often", and nothing says a bill was paid or a policy is in force. Utilities stays the
place for the service itself: its provider, fault line and meter.

Vehicles already reminds about car insurance. So that one policy never gets two reminders, **switching Bills on
moves nothing**. If the household already has Vehicle insurance records, the Bills list shows "Vehicle
insurance already in Vehicles" with three buttons: **Keep reminders in Vehicles**, **Review and move to Bills**
and **Decide later**. Review lists each Vehicle insurance record by its vehicle, name, date and permanent ID, and
each row asks "Move this renewal date to Bills?" with **Move** or **Keep in Vehicles**. Moving copies only the
vehicle, the name and the date. Notes stay in Vehicles. The old record stays, read-only, as "Earlier Vehicle
insurance record", and stops reminding. **Transfer back** moves the reminder back to Vehicles with the date as it
is now in Bills. Every move and move back makes a backup first.

## What we chose
- **A new module, `modules/bills_insurance/`, beside Utilities**, as the draft placed it. One list, Bills and
  policies: name, bill or policy, what it is for (electricity, gas, water, internet, phone, vehicle, home,
  contents, health, pet, other), provider (People), amount, how often, check or pay by, what it covers, vehicle,
  place, reference and private notes. It **requires only People**; Vehicles and Household stock are under
  `optional_requires` (0115), so the vehicle and place links are kept by exact ID while those are off, shown in
  the household's words, and never relinked by name. The draft's migration was generated again because optional
  links have no database rule (0115); nothing was ever released from it. Version 1.0.0.
- **Private fields, as the draft says.** Amount, what it covers, reference and notes are `sensitive` and
  `travels = "never"`: hidden behind Show, left off the list, Needs attention, Things to do, the sheet, the
  spreadsheet export and the helper reading API, and only named (never valued) in the change log and snapshot.
  The backup keeps them. Name, kind, category, provider, how often, date and links are ordinary and may travel.
- **Due words by row.** `watch.expiring` gains `what_when`: a list of `{ where, what }`, the first match winning.
  Bills says "vehicle insurance review or renewal" for a vehicle policy, "bill check" for a bill and "policy
  check" for another policy. Things to do reads the same words.
- **One reminder per vehicle policy: a new core declaration, `takes_over`, and a core table.** Bills declares
  `takes_over = { from = "vehicles.insurance", where = { kind = "policy", category = "vehicle" }, copy = {
  vehicle = "vehicle", name = "name", next_due = "renew_by" } }`. The loader checks both sides: the other module
  is under `requires` or `optional_requires`, the reminder's date is copied, and no private column or many-link is
  copied either way. Core migration 0010 adds `core__reminder_moves`: one row per older record, with both
  records' local numbers and permanent IDs and a state, `moved`, `returned` or `kept`. No name, date or note.
  `src/dashboard/core/reminder_moves.py` holds the rules. The screens are in `src/dashboard/web/moves_pages.py`.
  Neither names a module: the words are in Bills' `labels.toml` (`takes_over`), from RENEWAL.md.
- **Who reminds is worked out from that table alone**, on every read: Needs attention, Home, Things to do (and
  its year counts), the helper's attention list and every printed sheet leave out an older record whose
  reminder moved and a newer record whose reminder moved back. This holds while either module is off, so
  switching Bills off never revives the stale Vehicles date. The Vehicles record says "Vehicle insurance
  reminders are in Bills and insurance, which is off. Switch it on to see them, or choose Transfer back."
- **Opt-in per household, row by row, ID-based.** Nothing moves on start-up, on a module being switched on, or by
  a name match. Until the household chooses Keep or Review, and while Vehicle insurance still has a record that
  reminds, Bills refuses a new vehicle policy with "Choose first where vehicle insurance reminders are kept…".
  Ordinary bills and other policies are never held up. Decide later keeps asking. After Keep, a new vehicle
  policy in Bills, or a new Vehicle insurance record for a vehicle that already has one in Bills, asks **Go back**
  or **Save as entered** (0111's gentle check), because a second, different policy is allowed. Helpers and
  imports are refused rather than asked, as for every other refusal.
- **Moving is one core transaction after a backup** (`before-move-….db`, listed under Settings, Backups as
  "Before a reminder was moved"). If the backup fails, nothing moves. The new Bills record, the mapping row and a
  line in each record's history ("moved this reminder between lists", naming the other record by list and
  number only) are written together or not at all. This is the "narrow, reviewed core step" 0055 asks for: no
  module migration writes another module's table, and the older Vehicles record is not changed. A second press,
  retry, restart or restore finds the one mapping row (unique per older record) and changes nothing.
- **The earlier record is kept.** A moved Vehicle insurance record is read-only and cannot be deleted on its own.
  Deleting its vehicle still takes it along, as 0058 says, and restoring brings it back. The Bills record's
  vehicle link is cleared as 0115 says, and never relinked to a vehicle with the same name. Its notes keep their
  existing ordinary export and travel rules, and the review screen says so instead of claiming the move hid them.
- **Transfer back** copies the Bills record's current date into the Vehicles record, marks the move `returned`
  (the Bills record stays, read-only and silent, with its own private details) and writes history on both.
  **Move here again** brings the Vehicles date, vehicle and name back into the same Bills record, never a second
  one. If the Bills record was deleted, Transfer back asks to restore it first. Per-row **Keep in Vehicles** is
  recorded and **Decide later** undoes it.
- **Export and sync.** A "Reminder" column appears in each affected file ("Earlier record: its reminder moved to
  Bills and policies (ID 7); it does not remind" / "Reminds here (moved from Vehicle insurance, ID 3)"), and the
  README explains it. The sync snapshot gains `reminder_moves` by permanent IDs only.
- **A sheet is never silently cut short.** Any section over 200 rows now says "Not complete: only the first 200
  of N are printed here". Before this, sheets dropped the rest without saying.
- **Examples.** Smith has Home electricity at the Kitchen (Example Energy AU). Garcia has Contents insurance with
  no vehicle or place. Both still have Vehicle insurance in Vehicles, so both are asked. Taylor has Family car
  insurance on the Small car with no Vehicles insurance record, so it is asked nothing. Every reference starts
  DEMO-. All three have `bills_insurance` in their setup modules line.
- Tests: `tests/test_module_bills_insurance.py` automates the draft's nine checks, RENEWAL.md's nine checks
  (no double reminder, move and back both ways, a failed move, a second press, restart and restore), Vehicles off,
  Stock off and Vehicles not installed, privacy and travel, helpers, export, the module off and on, the
  examples, and the loader's new rules. `tools/browser_check.js` drives the choice, Review, Move and Transfer
  back in a real browser at 320 pixels and desktop.

## Why we chose it
- Corey's old tracker had bills and car insurance with nowhere to live here, and a missed renewal is costly.
- One policy with two reminders that drift apart is worse than none. The draft (RENEWAL.md) made this the
  condition for promoting Bills at all.
- Moving a household's record between lists is a data move. Making it opt-in, per row, by ID, after a backup,
  with the old record kept and an exact way back, means nothing can be lost or hidden without the person
  choosing it, and every choice can be undone.
- Working "who reminds" out from one small table on every read, rather than by changing the Vehicles record or
  by module on/off state, keeps the answer right whichever modules are switched on.

## What else we considered
- **Moving every Vehicle insurance record automatically when Bills is switched on.** Simple, but it moves a
  household's data without asking. Refused, as RENEWAL.md says.
- **Matching by name** ("Car insurance" in both lists). Two policies can share a name. Refused.
- **Letting both lists remind and warning on Home.** Two sources of truth. Refused.
- **A Vehicles migration that writes Bills, or the reverse.** Forbidden by 0055 and would run without a choice.
- **Marking the Vehicles row itself** (a "moved" column in Vehicles). It changes a shipped module's table for a
  core concern, and would be lost if Vehicles were reinstalled. The core table is narrower.
- **Copying the Vehicles notes into Bills' private notes.** They may hold something the household would keep
  private, and copying would not make the original private. Refused; the screen tells the person to review them.
- **A setting that forces a choice before Bills opens at all.** Would block a household that only has an
  electricity bill. Only vehicle policies wait.
- **The draft's suggestion to keep Bills unpromoted until core support exists.** The missing pieces (optional
  links, ID mapping, watch suppression, category words) are built here, so it can be promoted.

## What this costs us (the downsides)
- **This can hide an existing reminder from its old place.** After a Move, the Vehicles insurance record no longer
  appears on Needs attention, Things to do or the Vehicles sheet; its reminder is in Bills. If Bills is then
  switched off, that policy has no visible reminder at all until Bills is switched on or Transfer back is chosen.
  The Vehicles record's page says so, but nothing else does.
- If a household deletes the moved Bills record, the Vehicles record stays silent too; the household chose to
  delete the one reminder. Transfer back asks for the Bills record to be restored first.
- The mapping is a core table that sync stage 1 only lists in the snapshot. A later sync stage must carry it
  with the records, or a member copy could show the old Vehicles reminder. Nothing is sent today (0089, 0100).
- Every record write now looks up one row in `core__reminder_moves`, and every reminder read adds a small
  sub-query. Both are indexed and cheap at household sizes.
- A moved policy is named by its Vehicles name ("Comprehensive cover") without the vehicle; the vehicle shows in
  its own column. A household may want to rename it in Bills.
- Bills' private fields are not encrypted; private means kept off screens, files and other computers (0100).
- Removing the Bills module folder after a move leaves the Vehicles record silent and read-only; only Transfer back
  from a copy with Bills installed puts it right.
- The words for the choice live in Bills' labels.toml; a future module that uses `takes_over` without its own
  words gets plainer defaults.

## How hard it is to undo
Medium. Switching Bills off in Settings keeps every record and the mapping; nothing is deleted. To take the
feature out entirely: Transfer back each moved record first (each is one press), then remove `takes_over` from
`modules/bills_insurance/tables.toml`, or remove the module folder; the core code then sits unused. Core
migration 0010 cannot be unreleased, but an empty `core__reminder_moves` changes nothing. A household that wants
the state before a move can also restore the `before-move` backup from Settings, Backups. No Vehicles record is
changed by a Move, so Vehicles itself never needs repair.

## We should revisit this if
- A household is surprised that a Vehicle insurance reminder "disappeared" after a Move, or after switching Bills off.
- Households want the bill amount on another computer of theirs (a new travel rule and review, not a default).
- Another pair of lists needs `takes_over` (home insurance in Documents, for example), or the mapping needs to travel.
- Households ask for a paid or renewed history, or for the next date to be worked out from how often.
