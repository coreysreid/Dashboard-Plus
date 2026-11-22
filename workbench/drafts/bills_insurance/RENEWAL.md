# Batch 21 item 105: one vehicle-insurance renewal

Checked 21 November 2026 against shipped `modules/vehicles/tables.toml`, draft `workbench/drafts/bills_insurance/tables.toml`, decisions 0058, 0055, 0100, and this draft's [NOTES.md](NOTES.md). This is a proposed promotion flow, not a live migration. A renewal date is one the household typed. Neither module knows whether a policy is active, paid or adequate; the household checks its own current notice and policy.

## Owner and screen choice

**One policy gets one owner and one due source.** Bills and insurance becomes the owner of a vehicle policy **only if the household chooses to move its reminders there**. Otherwise `vehicles.insurance` stays the owner and Bills must not create a second commitment or warning for it. This is a household-wide choice at first Bills enable, with a per-row preview and the ability to leave an uncertain row for later. Do not silently move all rows merely because Bills is switched on.

The first-enable screen says:

> **Vehicle insurance already in Vehicles**
> You have [N] vehicle insurance record(s) with a date to check. Keep their reminders in Vehicles, or move these records' renewal dates into Bills and insurance. Each policy will have one reminder. We will show the name, vehicle and date before you choose; we will not copy notes, policy numbers or cover details. You can decide later.

Buttons: **“Keep reminders in Vehicles”**, **“Review and move to Bills”**, **“Decide later”**. The first is the safe default if the person skips the screen: Bills opens for ordinary bills but its vehicle-policy category is unavailable until the choice is made. The choice is reversible only through an explicit, backed-up transfer that refuses to create a duplicate; toggling a module off never transfers ownership.

“Review and move” lists each existing Vehicle insurance row by **vehicle, broad policy name, renewal date and permanent ID**, including blank dates. A row asks **“Move this renewal to Bills?”** with **Move / Keep in Vehicles / Decide later**. It makes no name-based match. If the same vehicle has two policies, show both IDs and ask separately. The screen warns **“Check your policy for the actual date and cover. The date shown is the one you recorded. Notes in Vehicles stay there and keep their current sharing and export rules; review them for details you meant to keep private.”**

## What moves and what stays

For a row the household chooses to move, create one `bills_insurance.commitments` row with `kind = policy`, `category = vehicle`, the exact `vehicles.insurance.vehicle` permanent link, the broad `name`, and `next_due = renew_by` unchanged. Leave `provider`, `amount`, `frequency`, `covers`, `reference` and Bills private notes empty for the person to add. Preserve blank `renew_by` as a blank next date; do not invent annual recurrence. Keep the original Vehicles insurance row and its history as a read-only source with a redirect to the new commitment, plus a stable old-ID→new-ID mapping. **Do not copy Vehicles `notes` automatically:** that ordinary field may contain information the household would keep private in Bills. Existing Vehicles notes still have their current ordinary export/travel behavior; the transfer does not make them private retroactively. Tell the person to review and clear or move sensitive notes themselves. The old record is not deleted and remains available under “Earlier Vehicle insurance record”, with a clear link to the active Bills row.

The core must write the new row, ownership mapping and old reminder suppression **atomically** after making a backup. A Vehicles-module migration cannot write a Bills table and a Bills-module migration cannot rewrite Vehicles tables under decision 0055; this needs a core-led, explicit transfer operation. Refuse or roll back the whole row on failure. Save an idempotency key so retry, restart and paired-computer sync cannot create a second commitment. The mapping uses permanent IDs, not titles. Audit history records the person's choice and transfer, never private contents.

Until a row is transferred, Vehicles `renew_by` is its sole watch. Once transferred, only the Bills `next_due` watch fires; the Vehicles detail and sheet may display the active Bills date as a link but may not emit their own due row. If Bills is switched off later, the active commitment and its date remain stored but hidden under the normal module-off rule; **do not reactivate the stale Vehicles watch**. Tell the household **“Vehicle insurance reminders are in Bills and insurance, which is off. Switch it on to see them, or choose Transfer back.”** Transfer back is an explicit reverse operation that copies the currently chosen Bills date to Vehicles, suppresses the Bills watch and preserves both histories. Do not silently use an old date.

The current draft's single `expiring` declaration says “bill or policy check” for every commitment. Promotion needs a category-specific `what`/filter or equivalent core support to say **“Vehicle insurance review or renewal due [household date]”** for vehicle policies while other bills say **“Bill check due [household date]”**. The Vehicles legacy row must not also appear in Home, Needs attention, Things to do or a sheet's due section. “Due” means check the date the household entered, not a claim that insurance remains in force.

## Exact household words after the choice

| Place | Words |
|---|---|
| Vehicle detail, kept in Vehicles | **“Insurance reminder is kept in Vehicles. Renew by [date recorded]. Check your policy for the actual date.”** |
| Vehicle detail, moved to Bills | **“Insurance reminder is in Bills and insurance. Open [broad policy name].”** No second due badge. |
| Bills commitment, moved | **“Vehicle insurance review or renewal due [date recorded]. This is your reminder to check the policy, not proof it is active.”** |
| Review before transfer | **“Move this renewal date to Bills? Vehicles will stop reminding you for this policy. Its earlier record and history stay in Vehicles.”** |
| Transfer complete | **“Moved [broad policy name] to Bills and insurance. One reminder is active there; the Vehicles reminder is off.”** |
| No date | **“No renewal date recorded. Check your policy and add the date you want to be reminded.”** Do not show a due warning. |
| Bills switched off after transfer | **“Vehicle insurance reminders are in Bills and insurance, which is off. Switch it on to see them, or choose Transfer back.”** |

## Acceptance checks

1. With Bills never enabled, existing Vehicles insurance continues to remind exactly once. Enabling Bills with **Keep** or **Decide later** makes no commitment and no second warning.
2. Preview two same-name policies on one vehicle and a policy with a blank date. The screen distinguishes permanent IDs; no name match or guessed date.
3. Move one policy. The new commitment has the same vehicle link, name and exact date; private Bills fields are blank, Vehicles notes remain only in the earlier row. One due row appears in Home, Needs attention and Things to do, with Bills as the source.
4. A second submit, restart, restore or paired-computer replay of the transfer leaves one active commitment and one ownership mapping. A failed transfer leaves the original Vehicles watch active and no partial Bills row.
5. A Vehicle insurance note containing an invented private marker is not copied into the Bills row, a due message or a new transfer log. The old Vehicles row still exports/travels under its existing rules; the preview warns the person of that existing exposure rather than claiming the transfer hid it.
6. Edit the Bills date after moving: the single reminder uses the new date. Turning Bills off does not revive the stale Vehicles date. Transfer back uses the **current** Bills date and again leaves exactly one owner.
7. Delete or turn off Vehicles after a move: the Bills row and its history remain, with the vehicle link in a repair state if the target is unavailable. No automatic deletion or name relink.
8. A non-vehicle bill continues its own date reminder. A newly entered vehicle policy in Bills cannot also create an independent Vehicles insurance row without an explicit ownership choice or duplicate warning.
9. Print's due section shows one active date. Export preserves both the active commitment and the earlier Vehicles row, explicitly marked with the ownership mapping so it cannot be mistaken for a second active reminder; it does not export Bills private notes or make a false paid/covered claim. A4, Letter and 320px use the household's date order.

This design depends on item 102's optional Vehicle link and on core-led transfer, stable cross-module mapping, watch suppression and category-specific reminder wording. Keep Bills unpromoted until those pieces are present; merely removing the `requires` line or hiding one card would leave two sources of truth.
