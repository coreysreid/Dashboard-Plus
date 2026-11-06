# 0001. Write down every technical decision

- **Status:** Accepted
- **Date:** 2026-11-06
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
This is the rule that every other record follows.

## What we chose
Every technical decision gets a short record in `docs/decisions/` before or when it is built, using `TEMPLATE.md`. Records are never deleted; a reversed decision is marked *Superseded* and points to its replacement.

## Why we chose it
- Corey judges the product by what he sees and uses, not by the technology. He needs a way to question a choice later without reading code.
- A future maintainer needs to know whether a choice was deliberate or accidental.
- Writing the downsides and the 'revisit if' trigger at the time means a decision can be judged as good or bad later, not just defended.

## What else we considered
- Decisions only in commit messages or chat: lost quickly.
- Long design essays: not skimmable, and they go stale.

## What this costs us (the downsides)
- A small amount of writing for every real decision.
- Records can drift if people forget to add them (mitigation: the pull request checklist asks for one).

## How hard it is to undo
Easy. It is just files.

## We should revisit this if
- Records go unread or unmaintained for a long period.
