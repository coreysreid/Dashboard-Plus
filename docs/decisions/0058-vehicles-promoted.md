# 0058. Vehicles is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The household can now write down each vehicle, who it would call if the vehicle
broke down, where it is usually kept, its car emergency kit, and the dates it
wants to be reminded of: registration or vehicle tax, insurance, and services
or checks. *Needs attention* says "service or check due in 12 days". *Worth
filling in* asks "Who would you call if Family car broke down?" until someone
is chosen. A one-page "Vehicles" sheet prints it without plate or policy
numbers.

Vehicles was chosen over Documents because nothing in its notes needs a core
feature that is missing today.

## What we chose
- A new module, `modules/vehicles/`, built on Lane B's draft
  (`workbench/drafts/vehicles/`, now removed; its notes and example rows are in
  git history). Three lists: vehicles, vehicle insurance, vehicle services and
  checks. The draft's working migration became one first migration because the
  draft was never released.
- **It reuses what the household already has.** Who to call is one of the
  household's People, so the phone number is kept and changed in one place.
  Where the vehicle is kept is one of its Places, and the car emergency kit is
  a Household stock item. The module says so (`requires = ["people",
  "stock"]`) and its only database change is three new, empty tables.
  Choosing a kit never changes how much stock there is.
- **A new part in Who to call: "Roadside assistance"** (People). The draft's
  notes asked for it so the contact also shows on the Emergency sheet with its
  number. It is one more choice in a list; no database change was needed.
- **No invented dates.** Registration, insurance and service dates are typed
  by the household from its own notice, policy or service book. Nothing is
  worked out from "last done", and a blank date raises no reminder.
- **One question, asked gently.** For each vehicle written down: "Who would
  you call if {name} broke down? It can be a roadside service, a garage or
  someone you know." The household is never asked whether it has a vehicle,
  insurance or a kit, because many do not.
- **Private numbers.** The registration or plate number is marked private: it
  is left off the list, the sheet and every reminder, and shows only on the
  vehicle's own page. There is no field for a policy number; the help text says
  to keep it with the household's own papers.
- Changes from the draft, each small:
  - The question no longer assumes paid roadside cover (see above).
  - The label reads "Registration or vehicle tax due", because in the United
    Kingdom the yearly renewal is vehicle tax, and the MOT fits under
    "Service or check".
  - A place cannot be deleted while a vehicle is kept there (the draft cleared
    the link). This is the rule Stock, Medical and Home layout already follow.
  - Deleting a vehicle deletes its insurance and service reminders with it, and
    restoring it brings them back (the draft refused the delete).
  - Reminders are named with their vehicle ("Family car: Routine service").

## Why we chose it
- A lapsed registration or insurance is a common, costly thing to forget, and
  "who do I call?" on the roadside is exactly the kind of answer this
  dashboard exists to have ready.
- The draft was finished and checked against the shipped People and Stock
  modules. What its notes listed as missing has since shipped: dates shown the
  household's way (decision 0052) and Home layout keeping places where they
  are (decision 0054).
- Keeping the number in People avoids two copies that drift apart.

## What else we considered
- **Promoting Documents instead.** Not needed: Vehicles had no blocker.
- **A phone number typed on the vehicle.** Refused: it would not follow a
  change made in People.
- **Requiring the contact to have the roadside role and a phone number.** The
  draft's notes asked for this check. The core cannot check across modules
  today, and People already asks "What is {person}'s phone number?" for anyone
  listed in Who to call without one. Left as it is.
- **Asking for a registration date or insurance on every vehicle.** Refused: a
  trailer or bicycle may have neither, and these questions cannot be answered
  "not relevant" yet.
- **Working out the next service from the last.** Refused: the interval
  depends on the vehicle and how it is used, and we have no source that fits
  every household.
- **One list with three date columns.** The core watches one date per list, so
  insurance and services stay as their own lists, as drafted.

## What this costs us (the downsides)
- The Vehicles sheet shows the contact's name but not the number, because a
  sheet cannot yet print a detail from another module's record. The sheet
  points to the Emergency sheet, which prints the number when the contact is
  listed in Who to call.
- Vehicles needs both People and Household stock switched on.
- Three more lists in the menu, and one more module to maintain.
- Nothing stops a household choosing a contact with no phone number saved,
  unless that person is also in Who to call.
- "Registration or vehicle tax" is a compromise wording until country packs
  can give each country its own words.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. The roadside assistance role can stay in People without harm; removing
it would need existing roles using it changed to "Other" first.

## We should revisit this if
- Households ask for the number on the Vehicles sheet (then let sheets print a
  linked record's detail across modules).
- Households want reminders that repeat by themselves, or by distance driven.
- Country packs arrive and can supply local words for registration and
  inspections.
