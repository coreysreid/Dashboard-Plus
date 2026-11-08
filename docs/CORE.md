# The v1 promise

This page is the test for every feature. If a proposed change does not help
keep one of these promises, it does not go into the core. It either becomes a
module or waits.

## The promise

**A non-technical person can unzip a folder, click *Open Dashboard*, say who
lives in the house and what they want to track, enter data by hand or approve
what a helper entered, see it in charts, answer a few sensible questions that make
the picture smarter, and see the difference it made (less waste, fewer shortages,
problems caught early). Their data never leaves their computer, can always be
exported, and survives updates, crashes and unplugged USB sticks.**

## What the core provides (and nothing more)

1. **Records and links.** Tables, typed fields, dropdown values, and links
   between records (a vet visit belongs to a pet).
2. **Time.** Dates, recurring events, and a calendar that analysis can use.
3. **Declared in files.** Tables are described in module files; the core builds
   the entry grid, forms, review screen and API from them.
4. **A fast grid.** Large tables load a page of rows at a time.
5. **Review and inbox.** Anything entered by a helper or imported waits as
   "needs review". Unsorted items (photos, notes) get a proposed destination.
6. **Agent API.** Helpers propose rows over a small, token-protected API. They
   never touch the database directly.
7. **Annotations and the question loop.** Changes are noticed, explanations
   are searched for, the person is asked, and answers are remembered.
8. **Migrations.** Numbered, linear, one track per module. The database knows
   its own version.
9. **Audit and undo.** Every change records who or what made it.
10. **Backups and export.** Daily automatic backup, one-click restore, and
    one-click export of everything as CSV and plain files.
11. **Module loader.** A versioned contract (`core_api = "1"`). A broken module
    is switched off with a plain-language message; the rest keeps working.
12. **Settings and first-run wizard** in the browser.
13. **Watch views.** Any table can mark a quantity with a minimum and a date
    column as an expiry. The core then shows "running low" and "expiring soon"
    across all modules, so resilience is not rebuilt per topic.
14. **Outcomes.** Metrics that compare this period with the last, wins that a
    person confirms (money saved, waste avoided, something caught early), and a
    monthly "difference this made" screen. Every figure shows its basis.
15. **Prompts.** "Have you thought about…?" questions chosen from a household
    profile, answered and dated, with a coverage view. They ask and point to
    sources; they never claim a household is safe.

## How we check we kept the promise (the acceptance list)

This is the list for v1.0 as a whole. Each milestone has its own, smaller list
in [`ROADMAP.md`](ROADMAP.md).

A release is not done until every line is true, on a clean Windows machine
with no Python installed:

- [ ] Unzip, click *Open Dashboard*, and the wizard appears. No install, no
      admin rights, no registry or PATH changes.
- [ ] The wizard sets up household members and modules without editing a file.
- [ ] Household stock, Pets and Wine work with no module code at all (files
      only).
- [ ] A household can enter its people and pets, record pantry items with
      minimums, and see "running low", "expiring soon" and "days of water
      on hand" without any setup beyond the wizard.
- [ ] Typing in a weekly shopping receipt (or approving one from a photo)
      raises the right stock levels, all as reviewable proposals.
- [ ] A helper can `POST /api/propose` twice with the same `request_key` and
      only one set of rows appears, flagged "needs review".
- [ ] A helper cannot change a row after the person has edited it.
- [ ] A helper cannot write to a table it has not been allowed.
- [ ] Undoing a batch removes exactly that batch's unreviewed rows.
- [ ] With 20+ days of data, a change in a number produces a question with
      *Yes / No / Not sure*; the answer appears on the chart afterwards.
- [ ] With fewer than about 20 points, analysis shows nothing and says why.
- [ ] Every statistic shows how many days it is based on.
- [ ] Updating (replace the app folder, keep `data/`) backs up first, then
      migrates, and the old data is intact.
- [ ] A question about two things with no plausible connection (car tyre wear
      and the garden hose) is never asked, and answering "that doesn't make
      sense" stops that kind of question for good.
- [ ] The monthly screen shows at least one metric against the previous period,
      says how many days it is based on, and shows nothing until there is
      enough history.
- [ ] A claimed win ("soup kits replaced four takeaway nights") appears only
      after a person confirms it, with the records it rests on.
- [ ] The wizard creates the household in the People module, and a one-page
      emergency sheet prints with no internet.
- [ ] A prompt appears only if it fits the household's profile (a flat is not
      asked about a second storey; a home without pets gets no pet questions),
      and is not asked if the answer is already recorded.
- [ ] Prompts can be answered Yes, Not relevant, Not yet or Tell me more; the
      answer is dated, and it returns for review on its schedule.
- [ ] The coverage view says how many questions were looked at and never says a
      household is safe or prepared.
- [ ] Any country note shows its source, the date it was gathered, and a line
      telling the household to check with their local authority.
- [ ] Sensitive details (such as allergies) are hidden from helpers unless the
      helper was explicitly given access.
- [ ] Pulling the USB stick out after *Close Dashboard safely* loses nothing.
- [ ] A failing outside source shows "unavailable" and the app keeps running.
- [ ] *Export everything* produces CSV and plain files that open without this
      program.
- [ ] The program listens on 127.0.0.1 only.
- [ ] No error screen ever shows a stack trace; *Save a report* writes a file.
- [ ] The repository contains no personal data (checked automatically).
- [ ] Every folder has a current, short `INDEX.md` (checked automatically), so
      the project can be skimmed top-down without reading everything.

## What the core refuses to do

Anything specific to one topic (pets, wine, water, tools, weather). Charts. Statistics.
Fetching from outside. Those are modules. If the core needs to know about cats,
the design has failed.
