# Roadmap

v1 is delivered in five milestones. Each one is something a household can use,
not a pile of half-finished parts. Later milestones may change after we learn
from people using the earlier ones; that is the point of shipping early.

| Milestone | What a household can do | Status |
|---|---|---|
| **M1** | Unzip, run the wizard, record People, Stock, Pets, first aid kits (Medical), where the ways out and shut-offs are (Home layout, decision 0054), their vehicles with the dates to remember (Vehicles, decision 0058) and their odometer readings and service quotes (Vehicle running log, decision 0111), where important papers are kept (Important documents, decision 0062), jobs around the home with the dates they choose (Home care, decision 0063) things lent out with the date each is due back (Things lent out, decision 0073) and a vegetable garden with its jobs (Vegetable garden, decision 0076), their own repeating tasks and one Things to do page for today, this week, this month and this year (Routines, decision 0107), who provides each utility, who to contact about a fault and where its meter is (Utilities, decision 0099), the dates to check each bill and policy, with one reminder per car insurance policy (Bills and insurance, decision 0117), each pet's food put out with honest daily totals by the household's own day (Pet feeding log, decision 0110), see running low, expiring soon and days of water, print the emergency sheet | **In progress** |
| M2 | Restore and export, review queue, inbox, Agent API, receipt entry, spreadsheet import | Planned. Agent API skeleton built (decisions 0066 to 0069): helpers look and suggest new records, a person reviews. Export my records built (decision 0078): a zip of spreadsheet files, private details left out. Restore from a backup built, with Undo (decision 0079). Import from a spreadsheet built (decision 0080): a CSV into any list, its rows wait on Review |
| M3 | Readiness prompts (Medical moved into M1, decision 0051; built, decision 0104: 49 sourced questions, answers, record matches offered for confirmation, review dates and a coverage count; "Think it through" drills built, decision 0108: eight sourced situations step by step, records offered or missing words, practice runs with private own words), first country pack, optional data-folder passphrase, optional sharing with the household, household sync (decision 0089: one main, members push requests to Review), a macOS build | Planned. Sync direction chosen (0089); built in stages after a security review; stage 1 (permanent record IDs, revisions and a filtered change log, nothing sent) is built (decision 0100). macOS: an unsigned preview app for Apple silicon is built and started by CI on every change, records in Application Support (decision 0096); Apple signing and notarisation, an Intel or universal build and a check on a real Mac are still to come (the README and bundled read-me wording was tightened after a read-through, decision 0106) |
| M3b | Phone apps for Android and iOS, joining the household as sync members (0089) | Planned, near pipeline (User 1, 20 November 2026); design with Lane B |
| M4 | Graphing, Analysis, the question loop, the monthly outcomes screen | Graphing started (decision 0109): the first two charts, drawn on the server with an equal table: today's drinking water by item (the same sum as Home's days of water) and one pet's recorded weights. Time series, annotations, Analysis, the question loop and outcomes are still to come |
| M5 | API connector (Pets moved into M1, decision 0047; Garden switched on, decision 0076; Wine switched on, decision 0095: wines, bottle counts you type, tasting notes) | Planned. The connector for AI assistants is done (decision 0083): assistant apps that support MCP can use a helper's key through `python -m dashboard.connector`. The connector that pulls data from outside services (DESIGN 6.1) is still to come |

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
- Portable folder with *Open Dashboard* and *Save and exit*, built
  automatically by GitHub. Built first, so problems show up early.
- Core: database with the USB-safe settings, migrations, module loader and file
  validator, records with links and history (who changed what), forms and a
  fast grid, watch views (running low, expiring soon, days of cover),
  plain-language errors with *Save a report*, local-only access.
- An automatic daily backup and a backup on safe close. (Restore from a backup,
  with Undo, is built (decision 0079); so are Export my records (0078) and
  Import from a spreadsheet (0080).)
- First-run wizard: who lives here, country and type of home, which modules.
- **People:** contacts, roles, important details (masked on screen), *Who do I
  call?*, the one-page emergency sheet, gaps check.
- **Household stock:** items, places, stock levels with minimums and expiry
  dates, stock in and out with a reason, emergency water days of cover.
- Data entry is typing, made fast (keyboard-friendly forms, add-another,
  sensible defaults). Receipt entry, CSV import and photos come later.
- A plain warning that the data folder is not encrypted, so the USB stick should
  be kept safe.

**Still to do for M1 (as of 9 November 2026):** three checks that need a person
at a clean Windows computer (first start, timing 20 items, unplugging). Everything
a machine can check passes; see [`releases/M1.md`](releases/M1.md).

**Not in M1:** helpers and the Agent API, the review queue and inbox, charts,
analysis, the question loop, prompts, outcomes, other modules, outside sources.

**M1 is done when** (checked on a clean Windows computer with no Python):
- [ ] Unzip, click *Open Dashboard*, and the wizard appears. No install or admin.
- [x] The wizard creates the household in People without editing any file.
- [ ] Adding 20 stock items takes under ten minutes for someone new to it.
- [x] Running low, expiring soon and days of water are correct for test data.
- [x] The emergency sheet prints on one page with no internet.
- [x] People and Stock are built from module files only, with no module code.
- [ ] *Save and exit*, unplug, plug in again: nothing is lost.
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

M1 is first tested by User 1's household and one or two others, with synthetic
data in every screenshot that is shared.

## Decisions still open

| Question | Working answer | Decide by |
|---|---|---|
| Main way data gets in after M1: CSV import, receipt photos via a helper, or both | Typing only in M1 | Start of M2 |
| Product name | "Dashboard Plus" as a working name | Before any public announcement |

## Later ideas, not planned yet

- **A simple map of the way out** ("lego level accuracy", User 1, 21 November 2026): started.
  **Our way-out sketch** draws Set up my home's rooms as boxes and connections as lines, with a
  text version and a printable sheet (decision 0118). Arranging the boxes by hand is a later idea.

## Workstreams beside the code

- **Content:** prompts, country packs and medical links are research and
  writing. Each needs a source list and a reviewer before it ships (M3).
- **Public project basics:** `SECURITY.md`, `CONTRIBUTING.md`, issue
  templates and milestones on GitHub (during M1).
