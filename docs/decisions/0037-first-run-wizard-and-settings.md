# 0037. One first-run wizard that doubles as the settings page

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The first time the dashboard opens, it asks a few questions on one page: who
lives here, about the home, what to track, and backups. The same page, later,
is Settings, so every answer can be changed without editing a file.

## What we chose
- Until setup is finished, the home page leads to `/setup`. Four short sections:
  who lives here (names, pets, mobility or care needs), the home (country,
  region, kind of home, storeys, hazards that can happen there), what to track
  (modules on or off) and backups (the second copy on this computer, on by
  default, with both folders shown).
- When the People module is on, names become People records marked as living
  here, through the normal record service so they appear in history. Without
  it, the wizard asks for a number instead.
- Answers are stored as settings in the database (`household.*`,
  `backups.second_copy`, `setup.done`). The browser's time zone is recorded
  automatically.
- Switching a module off hides it everywhere; its records are kept and come
  back when it is switched on again.
- Mistakes are explained next to each answer and nothing is saved until all
  answers are valid.
- The page states plainly that records stay on this computer, that the data
  folder is not encrypted, and that the second backup copy means records are
  also stored on the computer.

## Why we chose it
- One page is quicker for a first visit than a multi-step wizard, and reusing
  it as Settings means one set of questions to keep correct.
- The home profile (storeys, hazards, mobility needs) is what the M3 prompts
  will use to ask only sensible questions (decision 0017).
- Being plain about privacy and backups at the start builds trust.

## What else we considered
- A multi-page wizard: gentler pacing, more screens to build and test.
- Asking only for names and leaving the rest for later: the household
  size and home profile would then be missing when they are needed.

## What this costs us (the downsides)
- One long page; some people may skip the optional questions.
- Countries are free text with suggestions, so spelling may vary until country
  packs need an exact match (M3).

## How hard it is to undo
Low. The wizard is `src/dashboard/web/setup.py` and one template.

## We should revisit this if
- M1 testers find the page too long or confusing.
- Country packs need a fixed list of countries.
