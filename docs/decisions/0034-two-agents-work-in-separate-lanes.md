# 0034. Two agents work in separate lanes with fixed contracts

- **Status:** Accepted (refined by decision 0042)
- **Date:** 2026-11-09
- **Decided by:** Claude (direction from Corey to use a second agent)

## In plain words
Two AI agents now build the project at the same time. Each owns different
folders, so they never overwrite each other, and they agree in writing on the
few places where their work meets.

## What we chose
`docs/WORKSTREAMS.md` splits the work into Lane A (core program: `src/`,
`tools/`, CI, design docs) and Lane B (modules and project files: `modules/`,
the module guide, `SECURITY.md`, `CONTRIBUTING.md`, issue templates). It fixes
three contracts (watch views, printable sheets, the People tables the wizard
uses), gives each lane its own range of decision numbers, and lets shared index
files only gain rows. Each agent has its own branch and pull requests.

## Why we chose it
- Splitting by folder is the simplest way to avoid merge conflicts between two
  agents that cannot always talk to each other directly.
- Writing the contracts down first lets Lane B build the People and Stock
  modules while Lane A builds the core features they rely on.
- Separate number ranges stop both agents writing decision 0035.

## What else we considered
- Both agents on everything, taking turns: constant conflicts and waiting.
- Splitting by milestone (one agent on M2 now): M2 depends on M1 core work
  still in progress, so it would stall.

## What this costs us (the downsides)
- Gaps in decision numbering.
- A contract mistake is found later, when both halves meet.
- Corey has two streams of pull requests to review.

## How hard it is to undo
Easy. It is a working agreement.

## We should revisit this if
- The lanes keep needing each other's files.
- One lane runs out of work while the other is overloaded.
