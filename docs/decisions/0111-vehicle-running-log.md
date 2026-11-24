# 0111. Vehicle running log: odometer readings and service estimates beside Vehicles

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by User 1)
- **Amended 2026-11-24 by User 1:** quote amounts and what a quote includes now travel to the household's paired
  computers (`travels = "always"`); they stay private (hidden until Show, off lists, sheets, export and helpers).
  Notes still stay on the computer where they were typed.
- **Builds on:** 0058 (Vehicles), 0059 (private details), 0075 (`not_before`), 0100 (what travels), 0109 (dots
  charts), Lane B's draft `workbench/drafts/vehicle_running/` (batch 20 item 91; now removed, in git history)

## In plain words
A household can now write down what a vehicle's odometer showed and when, and keep the quotes it got for a
service already on its Vehicles schedule: one from the dealer, one from an independent workshop, or another.
The vehicle's page says **Last recorded: 48,500 km on 20/11/26** with the readings as dots and a table. A reading
lower than the last one, or in miles after kilometres, asks **Go back** or **Save as entered** before it is saved;
it never refuses, because odometers get replaced and records get corrected. A service's page lists its
**Cost estimates** with the dates and who quoted, and **Show estimated cost and scope** reveals the private amounts.
They are estimates, never a bill, a total or the cheapest choice. The service date the household typed stays the
only service reminder: nothing works out a distance due point or a distance travelled.

## What we chose
- **A new module, `modules/vehicle_running/`, beside Vehicles**, as the draft placed it; Vehicles is unchanged.
  Two lists: Odometer readings (vehicle, read on, odometer showed, unit, notes) and Service estimates (service,
  who quoted it, provider from People, quoted on, estimated cost, quote good until, what it includes, notes).
  It requires Vehicles and People. The draft's generated migration is kept unchanged; a test checks it still
  matches `tables.toml`. Choices of unit read "km" and "mi"; a reading is named "Family car, 48500 km" and an
  estimate "Family car: Routine service, Dealer estimate".
- **No mileage due logic.** The draft names a `due_at_distance` field as later work and does not build it, so
  none is built: no watch rule, no distance warning, no interval worked out from readings, and Needs attention
  shows only the existing Vehicles date reminder. The draft's optional extra detail lines on Needs attention
  ("Last odometer reading recorded …", "2 estimates recorded") are not added; the vehicle and service pages carry them.
- **Deleting is deliberate.** A reading restricts its vehicle and an estimate its service, so a vehicle or service
  with history cannot be deleted (even through Vehicles' cascade from vehicle to services) until the household
  deletes or moves those records itself.
- **Privacy and travel (0100), as the draft says.** Estimated cost, what the quote includes and notes are private
  (`sensitive`, `travels = "never"`): hidden until Show, left off lists, Needs attention, sheets, the spreadsheet
  export, the helper API and the change log's values, kept in backups. Their help says **only on this computer**.
  Readings, and an estimate's existence, kind, provider, dates and service link, are ordinary and may travel. A
  helper may suggest a reading or an estimate without its private fields; a private field is refused as today.
- **Examples:** Smith (two readings in km, a dealer and an independent quote for the Routine service), Garcia
  (62,100 mi, an independent quote) and Taylor (70,200 mi, an MOT quote). Every amount is invented.
- **Generic core support the draft needed, small and declared:**
  1. `[[tables.<t>.confirm]]` in tables.toml (`core/confirm.py`): a gentle check before a form saves.
     `when = "lower"` compares a number with the same subject's nearest earlier record in `order` (and the
     nearest later one, with `later` words), only among records with the same `among` value; `when = "different"`
     says when a value differs from the record before (`{before}` names it). The form shows **Nothing is saved
     yet**, the sentence, **Go back** (to the field) and **Save as entered**, which carries a fingerprint of the
     checked values so a changed value is checked again. Only the household's own forms ask; Review and imports
     do not.
  2. `chart` (0109) may use a date-and-time `x`, a `unit` choice column (only readings in the latest reading's
     unit are drawn, others stay in the table as "Not drawn: recorded in km, not mi"), `latest` words for the
     summary and its own `caveat`. A record's own page reads only the latest 50 readings and counts them all.
     Whole numbers show with thousands separators (48,500).
  3. labels.toml `under = { link, title, intro, columns, order, reveal }` lists a table's records on the page of
     the record they link to (latest 50, then a link to the list), private cells as Show buttons, `reveal` one
     button that presses them all; `add_button` renames the "Add to …" button (**Add a reading**, **Add estimate**).
  4. A household distance unit in Settings (**Odometers usually show**, km or mi; until chosen, miles in the
     United States and the United Kingdom, km elsewhere), used by a choice column's `default_from = "distance_unit"`
     to start a new reading. Nothing is converted.
  5. A date and time reads the household's way ("20/11/26 09:00"); an example may write "today-1 09:00".

## Why we chose it
- A reading is an observation and a quote is a promise of a price: neither is evidence of a due service or of
  work done, so the only reminder stays the date the household chose from its own schedule.
- Asking rather than refusing keeps a true record when an odometer rolls over or is replaced, and never erases
  either reading; history shows any correction.
- Declaring the checks, the per-reading unit and the listed-under section keeps them usable by later modules and
  out of hand-written screens.

## What else we considered
- **Folding the two tables into Vehicles by migration.** Possible later with stable IDs; a separate module needs
  no change to a shipped module and can be switched off on its own.
- **A mileage target with warnings now.** The draft says it needs a household-entered target, same-unit rules and
  stale-reading wording first; building it without those would make confident claims from uncertain readings.
- **Letting quotes travel.** The draft asks for local-only quotes; User 1 can reverse it by changing `travels`.
- **A hard block on lower readings.** Refused: real rollovers and replaced odometers would be impossible to record.

## What this costs us (the downsides)
- On a member computer later, a quote shows without its price and scope, so comparing quotes across devices is
  incomplete; there is no member screen yet, so the "only on this computer" wording for a copy received from
  main is still to be written with sync stage 2.
- The amount is shown without a currency name; no household currency setting exists yet.
- The lower and mixed-unit checks are asked only on the household's own forms, not when accepting a helper's
  suggestion on Review or an imported row.
- A date and time is stored as typed, with no time zone; phone members will need a rule (the draft's open note).
- The odometer chart starts at zero (0109's rule), so close readings sit near the top.
- The full chart page still reads every reading of a vehicle; only the vehicle's own page is limited to 50.
- A household that changes country after saving Settings keeps its chosen unit.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the folder and its example rows. The core
additions are opt-in declarations: removing `confirm.py`, the `under`, `add_button`, `default_from` and chart
`unit`/`latest`/`caveat` handling and the Settings field changes no other module.

## We should revisit this if
- Households ask for a distance-based reminder: build the draft's `due_at_distance` with same-unit rules.
- People record many quotes and want to compare them across devices, or expect a currency name.
- Lower-reading warnings are needed on Review too.
