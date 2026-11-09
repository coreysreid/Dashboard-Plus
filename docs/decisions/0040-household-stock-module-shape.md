# 0040. What the Household stock module records, and how water is counted

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Household stock keeps a list of things with how many you have, how many to
keep, where they are and when they expire. Water is recorded in litres so the
dashboard can say how many days it would last.

## What we chose
- Two tables: **Places** and **Stock items** (name, category, how many, unit,
  keep at least, place, use by, notes). Categories cover pantry, water, first aid
  and medical, toiletries, cleaning, batteries and power, fuel, tools, screws and
  hardware, pet supplies, garden and other.
- Quantities are plain numbers with a free unit (tins, kg, packs), except water,
  which the help text asks to record in litres.
- The `watch` section turns on running low, use-by within 30 days, and days of
  water: 3 litres per person and 1 litre per pet a day, aiming for 3 days. These
  are starting figures; the page always says local advice comes first, and they
  will be revisited with the country pack research in M3.
- A place cannot be deleted while things are kept there.
- An **Emergency supplies checklist** sheet prints water, first aid, power and
  food with where they are and their use-by dates.
- Not yet: a "stock in and out" record with reasons (bought, used, expired,
  thrown away). Today people change the quantity directly. Recording movements
  needs a small core feature to update the quantity, planned before M1 is done.

## Why we chose it
- A free unit keeps entry quick for very different things (screws, tins, fuel).
- Counting water in litres is what makes days of cover possible.

## What else we considered
- A fixed unit per category: too rigid for real households.
- Recording only movements and calculating quantity: needs the core feature
  first, and makes the first entries slower.

## What this costs us (the downsides)
- Water entered in bottles rather than litres gives wrong days of cover; the help
  text guards against this.
- The daily figures are not yet backed by cited local sources.
- No waste figures until movements exist.

## How hard it is to undo
Medium once households have data.

## We should revisit this if
- Testers record water in other units.
- The country pack research gives different daily figures.
