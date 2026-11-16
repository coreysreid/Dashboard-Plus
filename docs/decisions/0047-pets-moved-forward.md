# 0047. Pets is switched on now, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-16
- **Decided by:** Claude (technical decision delegated by Corey), at Corey's request

## In plain words
Pets was planned for the last milestone (M5). Corey found it missing on his
first run, so it is now a shipped module. Setup asks for each pet's name and
kind, and the Pets lists record the vet, microchip, vaccinations, regular
treatments and medicine with when each is next due, weigh-ins and vet visits.
A printable pet details sheet is there for a sitter, kennel or evacuation.

## What we chose
- Promoted from Lane B's draft in `workbench/drafts/pets/`, reshaped:
  - Feeding logs were left out (few households log every meal).
  - "Treatments and medicine" now carries a next due date, so flea, worming
    and medicine appear under *Needs attention* a week before.
  - Vaccinations due appears a month before.
  - Microchip number and cost of vet visits were added.
- The vet and the person who looks after the pet link to People, so the vet's
  phone number lives in one place. Two gap questions ask for a missing vet and a
  vet with no phone number.
- Two small core features make this work from files alone:
  - A gap can follow a link into a module it requires (`vet.phone`). The column
    is checked once all modules have loaded.
  - An `expiring` rule can say "due" instead of "expires"
    ("vaccinations due …", "overdue since …").
- With Pets switched on, days of water counts the pets recorded rather than
  the number typed in setup.
- Pet food stays in Household stock (category "Pet supplies"), where running
  low already works.

## Why we chose it
- Corey asked for it. Pets matter to many households, and in an evacuation
  the vet, microchip and medicine details are exactly what gets forgotten.
- The draft was close; promoting it costs less than leaving the household with
  a bare pet count.

## What else we considered
- Waiting for M5 as planned: the feature would sit unused for months.
- Feeding logs with daily totals: needs the analysis features (M4) to be worth
  the typing.
- Linking pet food in Stock to pet feeding records: a cross-module count needs
  core support; revisit with feeding logs.

## What this costs us (the downsides)
- One more module to maintain from M1 onwards.
- Feeding is not recorded yet; households that want it will notice.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept), or remove the folder.

## We should revisit this if
- Households ask to record feeding or medicine doses in more detail.
- Repeating treatments should move their next due date forward automatically
  when one is given (needs core support for repeating tasks).
