# 0013. A short INDEX.md in every folder, checked by CI

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Every folder has a one-page summary so an AI agent or newcomer can skim the project without reading everything.

## What we chose
Nested `INDEX.md` files (25 lines or fewer), a one-line summary at the top of each code file, a root `AGENTS.md`, and a checker script in CI that keeps them complete and current.

## Why we chose it
- Corey asked for context-friendly layout for agents.
- Automatic checking is the only way such documents stay true.

## What else we considered
- One big project map: becomes long and stale.
- Relying on agents to search: wastes context.

## What this costs us (the downsides)
- A small writing chore with every new file; the checker generates the skeleton to reduce it.

## How hard it is to undo
Low. They are documents plus one script.

## We should revisit this if
- Contributors find the indexes burdensome.
- Agents ignore them.
