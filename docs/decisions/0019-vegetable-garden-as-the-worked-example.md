# 0019. Vegetable garden as the worked example module

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (direction from Corey; technical shape chosen by Claude)

## In plain words
The garden module is the one we use to teach people how to build a module of their own.

## What we chose
Ship a files-only Vegetable garden module as an optional v1 module and base the "build your first module" guide on it.

## Why we chose it
- It touches every feature a module can use: stock (seeds), time (seasons), weather (connector), recurring jobs (events), and a money-saved outcome.
- It is relatable and easy to explain to a non-technical author.
- Corey chose it as the perfect example.

## What else we considered
- Wine as the teaching example: too narrow, with no recurring jobs or outside data.
- A synthetic toy module: less motivating and does not match a real use.

## What this costs us (the downsides)
- It is one more module to keep working through changes in the core.
- The guide must stay in step with the module.

## How hard it is to undo
Low. It is an optional module and a document.

## We should revisit this if
- Authors find the example too complicated to copy, or the module is rarely used.
