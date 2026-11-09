# 0039. What the People module records, and its two emergency sheets

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
People holds everyone around the household, who to call in what order, and
private details such as allergies. It prints two emergency sheets: one safe to
leave on the fridge, and one with medical details for responders and carers.

## What we chose
- Three tables: **People** (name, lives here, relationship, phones, email,
  address, birthday, notes), **Who to call** (a person, their role, the order to
  call them) and **Important details** (a person, what kind, and the detail,
  which is private and hidden in lists until shown).
- Deleting a person also deletes their roles and details (they can be restored).
- Two sheets: **Emergency sheet** (who lives here, who to call with phone
  numbers) and **Emergency sheet with medical details** (the same plus
  important details, clearly marked as private).
- Meets the People contract in `docs/WORKSTREAMS.md` that the wizard uses.
- Not yet: a separate dates table and the "gaps" check (for example, an
  emergency contact with no phone number); birthdays live on the person for now.

## Why we chose it
- Separating roles from people lets one person be both neighbour and key holder,
  and lets the call order be set per role.
- Two sheets let a household decide whether private details go on the fridge.

## What else we considered
- Roles as a choice on the person: cannot express two roles or an order.
- One sheet with medical details always included: puts private details on the
  fridge by default.

## What this costs us (the downsides)
- Adding someone's role takes a second form.
- The gaps check waits for a small core feature.

## How hard it is to undo
Medium once households have data; additions are easy, removals need a migration.

## We should revisit this if
- Testers find the separate "Who to call" form awkward.
- Households want recurring dates (appointments) before M4.
