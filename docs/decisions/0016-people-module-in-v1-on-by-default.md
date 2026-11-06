# 0016. People module in v1, on by default

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
Contacts with the important details attached are part of the first release, because people are a pillar of resilience.

## What we chose
Ship a files-only **People** module (people, roles, important information, dates), switched on by default. The wizard's "who lives here" writes into it. Pets and other modules link to people through `requires`. Provide a Who-do-I-call view, an offline printable emergency sheet and a gaps check. Details such as allergies are marked `sensitive`.

## Why we chose it
- Corey identified people as a core pillar of the goal.
- Many other modules need to point at a person (a pet's vet, a stock item's owner), so making it a module they depend on avoids duplicate contact lists.
- A printed emergency sheet is a resilience tool that works with the power and internet off.
- A `sensitive` flag handles medical-type details without making the product a medical system.

## What else we considered
- Put people in the core: rejected, because the core must know nothing about any topic.
- Leave contacts to a later release: rejected, because the wizard and Pets already need them.

## What this costs us (the downsides)
- Other modules depend on People, so it cannot be removed while they are on.
- Holding sensitive details raises the stakes if a USB stick is lost (an optional passphrase for the whole data folder is listed under later work).
- Risk of being mistaken for a medical record.

## How hard it is to undo
Medium. Other modules link to it, so removal needs those links cleared first.

## We should revisit this if
- Households find the module heavier than a plain address book.
- Sensitive-detail handling proves inadequate.
