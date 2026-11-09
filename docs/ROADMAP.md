# Roadmap

v1 is delivered in five milestones. Each one is something a household can use,
not a pile of half-finished parts. Later milestones may change after we learn
from people using the earlier ones; that is the point of shipping early.

| Milestone | What a household can do | Status |
|---|---|---|
| **M1** | Unzip, run the wizard, record People and Stock, see running low, expiring soon and days of water, print the emergency sheet | **In progress** |
| M2 | Restore and export, review queue, inbox, Agent API, receipt entry | Planned |
| M3 | Medical, Readiness prompts, first country pack, optional data-folder passphrase | Planned |
| M4 | Graphing, Analysis, the question loop, the monthly outcomes screen | Planned |
| M5 | Pets, Garden, Wine, API connector | Planned |

Why this order: M1 proves the riskiest promises (unzip-and-click on Windows,
modules built from files alone) and gives real value on day one. The question
loop and outcomes need weeks of history before they can say anything, so they
come after people have been recording for a while.

## M1: the first usable release

**The promise:** someone unzips the folder on a Windows computer, answers a few
questions, and within ten minutes knows what is in the pantry, what is running
low or expiring, how many days of water the household has, and has a printed
sheet of who to call.

**In M1**
- Portable folder with *Open Dashboard* and *Close Dashboard safely*, built
  automatically by GitHub. Built first, so problems show up early.
- Core: database with the USB-safe settings, migrations, module loader and file
  validator, records with links and history (who changed what), forms and a
  fast grid, watch views (running low, expiring soon, days of cover),
  plain-language errors with *Save a report*, local-only access.
- An automatic daily backup and a backup on safe close. (Restore and export
  screens come in M2; a backup is a plain copy that can be restored by hand.)
- First-run wizard: who lives here, country and type of home, which modules.
- **People:** contacts, roles, important details (masked on screen), *Who do I
  call?*, the one-page emergency sheet, gaps check.
- **Household stock:** items, places, stock levels with minimums and expiry
  dates, stock in and out with a reason, emergency water days of cover.
- Data entry is typing, made fast (keyboard-friendly forms, add-another,
  sensible defaults). Receipt entry, CSV import and photos come later.
- A plain warning that the data folder is not encrypted, so the USB stick should
  be kept safe.

**Still to do for M1 (as of 9 November 2026):** stock in and out with a reason
(a small core feature so movements update the quantity), the People "gaps" check,
README with the Windows warning, and the final checks below.

**Not in M1:** helpers and the Agent API, the review queue and inbox, charts,
analysis, the question loop, prompts, outcomes, other modules, outside sources.

**M1 is done when** (checked on a clean Windows computer with no Python):
- [ ] Unzip, click *Open Dashboard*, and the wizard appears. No install or admin.
- [ ] The wizard creates the household in People without editing any file.
- [ ] Adding 20 stock items takes under ten minutes for someone new to it.
- [ ] Running low, expiring soon and days of water are correct for test data.
- [ ] The emergency sheet prints on one page with no internet.
- [ ] People and Stock are built from module files only, with no module code.
- [ ] *Close Dashboard safely*, unplug, plug in again: nothing is lost.
- [ ] A backup exists after the first day and after each safe close.
- [ ] No screen shows a stack trace; *Save a report* writes a file.
- [ ] It listens on 127.0.0.1 only. CI privacy and index checks pass.
- [ ] Every journey marked M1 in `JOURNEYS.md` works as written.

## How we will know it is working

Measured only on the household's own computer, shared only if they choose.

| Measure | Target |
|---|---|
| Wizard finished and 10 or more records in the first week | most new households |
| Still updating at least weekly after four weeks | more than half |
| Minutes per week to keep it current | under 15 |
| Prompts and insights marked useful (from M3) | more than half |

M1 is first tested by Corey's household and one or two others, with synthetic
data in every screenshot that is shared.

## Decisions still open

| Question | Working answer | Decide by |
|---|---|---|
| Main way data gets in after M1: CSV import, receipt photos via a helper, or both | Typing only in M1 | Start of M2 |
| Product name | "Dashboard Plus" as a working name | Before any public announcement |

## Workstreams beside the code

- **Content:** prompts, country packs and medical links are research and
  writing. Each needs a source list and a reviewer before it ships (M3).
- **Public project basics:** `SECURITY.md`, `CONTRIBUTING.md`, issue
  templates and milestones on GitHub (during M1).
