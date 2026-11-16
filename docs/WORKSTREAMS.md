# Workstreams: two agents in parallel

Two AI agents build Dashboard Plus. Each owns different files, so they never
overwrite each other, and they talk only through the repository. Corey reviews
pull requests and judges the product. Read this page before any work.

## Who owns what

| Lane | Agent | Owns (may edit) | Role |
|---|---|---|---|
| **A: builder** | the first agent | everything outside `workbench/` | builds the program and the shipped modules; reviews and promotes Lane B's drafts |
| **B: checker and drafter** | the second agent | **only `workbench/`** | tests the product as a household would, reports findings, drafts new modules, researches content |

The one exception: Lane B's two branches already in flight
(`lane-b/module-guide`, `lane-b/project-files`) finish as they are, then all new
Lane B work happens in `workbench/`.

Because Lane B only edits `workbench/`, and `workbench/` is left out of
`PROJECT_MAP.md`, Lane B's pull requests cannot conflict with Lane A's.

## How Lane B works

**The workbench**

| Folder | Put here | Lane A then |
|---|---|---|
| `workbench/STATUS.md` | what you are doing, what is done, messages to Lane A | answers in the Requests table below |
| `workbench/reports/` | findings from checking the product, one dated file per report | fixes them, and records which ones in the Requests table |
| `workbench/drafts/<name>/` | a draft module: module.toml, tables.toml, labels.toml, optional sheets.toml, migrations/, INDEX.md, and NOTES.md (open questions, core features it needs) | reviews it, asks for changes or promotes it into `modules/` or `examples/` |
| `workbench/research/` | sourced research notes | uses them to build content (country packs, prompts) |

**A good finding** says: what you did, what you expected, what happened,
how bad it is (blocker, important, minor), and a suggested change. If you
suggest wording, give the exact new words. Use only made-up data and say which
journey in `docs/JOURNEYS.md` or line in `docs/ROADMAP.md` it relates to.

**A good draft module** loads with no problems, has its migration generated
(`python tools/make_migration.py <name> --modules-dir workbench/drafts`), uses
the contracts below, and passes `tests/test_workbench_drafts.py`, which checks
every draft automatically. You do not write tests in `tests/`.

**Decisions:** if a draft needs a technical decision, write it in the draft's
`NOTES.md`. Lane A turns accepted ones into decision records.

## Definition of done (every pull request, both lanes)

1. Branch from the latest `main`; merge `main` again just before opening the
   pull request.
2. Run `python tools/check_all.py`. Everything passes, nothing skipped.
3. One pull request per task, described in plain language for Corey: what a
   household can now do or what was found, and anything left undone. GitHub
   does not let Lane B create pull requests, so Lane B pushes its branch and
   writes "ready for a pull request: `<branch>`" with a plain-language summary
   in `workbench/STATUS.md`; Lane A checks the branch and opens the pull
   request using that summary.
4. Lane B commit messages start with `Lane B:`; Lane A messages do not.
5. Lane B updates `workbench/STATUS.md` in the same pull request.
6. No real names, places, numbers or data, anywhere.

## Who merges (delegated by Corey on 16 November 2026)

Lane A merges without waiting for Corey:
- its own pull requests, and
- Lane B's pull requests that change only `workbench/`, after checking them,

once every check is green on the current head and there is no conflict. Lane A
then tells Corey in plain words what was merged and what changed for a
household. Corey reviews the result by using the program, not each pull
request.

**Still asks Corey first:** anything published outside the repository (a
release, a public announcement), a change to the licence or the privacy and
security rules, deleting or rewriting history, and any change that could lose
or alter a household's existing records without a backup and a way back.

## Contracts between the lanes

**Watch views:** the `watch` section in `tables.toml`, exactly as in
`docs/DESIGN.md` section 5.1 (including the optional `label` for a supply).

**Gaps worth filling in:** `gaps` in the `watch` section, as in
`docs/DESIGN.md` section 5.4 (for example a vet with no phone number). Ask only
what nearly every household would want answered.

**Records that change a count:** the `adjusts` section, as in `docs/DESIGN.md`
section 5.3, for drafts that track amounts going in and out (for example pet food).

**Printable sheets:** `sheets.toml`, exactly as in `docs/DESIGN.md` section 5.2,
including `link.column` columns such as `person.phone`.

**People tables the wizard writes to** (module `people`, now in `modules/`):

| Table | Column | Type |
|---|---|---|
| `people` | `name` | text, required |
| `people` | `lives_here` | boolean |
| `people` | `relationship` | choice |
| `people` | `phone` | text |
| `roles` | `person` | link to `people`, on_delete = "cascade" |
| `roles` | `role` | choice, including `emergency_contact`, `neighbour`, `doctor`, `vet` |
| `roles` | `priority` | integer |
| `important_info` | `person` | link to `people`, on_delete = "cascade" |
| `important_info` | `detail` | text, sensitive |

Draft modules may link to these with `requires = ["people"]` and
`to = "people.people"`.

## Status

| Item | Lane | State |
|---|---|---|
| M1: core, People, Household stock, gaps, README, release checks, examples | A | merged; three hands-on checks are with Corey |
| Water basis on the home page, second backup status | A | merged |
| Setup country and state drop-downs, "Save and exit" | A | in review |
| Pets module (moved forward from M5, from Lane B's draft) | A | in review |
| Batch 2: M1 check, wording, Pets/Medical/Wine drafts, AU/US research, SWOT | B | merged |
| Batch 3: catalogue, Home layout, lots, Medical, readiness, country packs, Documents, Home care, Wine, examples, UX check | B | merged (#22, #24 to #33) |
| Drinking water only; pick from a list while typing (catalogue) | A | merged (#35, #36) |
| Nested places | A | in review |
| Dates shown the household's way, then lots | A | next |
| Batch 4 (below), then the Lane B roadmap (batches 5 to 8) | B | ready to start |

## How the lanes work together: draft, polish, test

1. **Lane B drafts** the heavy material in `workbench/`: modules, prompts,
   country content, example data, test scripts.
2. **Lane A polishes and integrates**: reviews each draft, fixes what the core
   needs, promotes it into `modules/` or `docs/`, adds tests and screenshots.
3. **Corey tests the result** as a household would (UX and UI), and his notes go
   into [`BACKLOG.md`](BACKLOG.md). Lane B also runs the journeys after each
   Lane A merge and reports what it finds.

Then round again. Lane B should always have a brief with more drafting than one
session can finish; Lane A keeps it stocked.

## Requests between lanes

| From | To | Request | State |
|---|---|---|---|
| A | B | Finish both in-flight branches: merge `main`, run `python tools/check_all.py` (it will ask you to regenerate `PROJECT_MAP.md`), resolve `docs/decisions/INDEX.md` by keeping every row in number order, start the commit message with `Lane B:`, then mark each "ready for a pull request" in `workbench/STATUS.md`. | module guide merged (pull request #10); project files: merge `main` again (it is missing #9 and #10), then mark it ready |
| A | B | Start batch 2 below, all inside `workbench/`. | done: pull requests #12, #13, #15 |
| B | A | M1 check findings (`workbench/reports/2026-11-09-m1-check.md`): J1 first step, J5 home summary. | fixed in the M1 release checks pull request |
| B | A | Product review (`workbench/reports/2026-11-13-product-swot.md`): show the water basis; show whether the second backup worked; finish the hands-on M1 checks. | first two done (decision 0046); hands-on checks are with Corey |
| A | B | Start batch 3 below: drafting heavy lifting for Lane A to polish and integrate. | done (#22, #24 to #33) |
| A | B | Start batch 4 below: check the new picking, fill the catalogue from evidence, a places list, acceptance checks for nested places and lots, tie readiness questions to records, Collections and Vehicles drafts, a getting-started guide. | open |
| B | A | Module wording (`workbench/reports/2026-11-09-module-wording.md`). | adopted, lightly changed: sheet titles keep "Emergency sheet" ("fridge copy" and "with private medical details"), supplies sheet is "Emergency supplies"; the rest as suggested |

## Brief for Lane B, batch 4

> You are Lane B, the checker and drafter. You have full internet access.
> Pull the latest `main` and read `AGENTS.md`, this page (including "Who
> merges": Lane A now merges your workbench pull requests itself once checks
> pass), [`BACKLOG.md`](BACKLOG.md), [`DESIGN.md`](DESIGN.md) sections 5 and
> 6 (new since batch 3: 5.5 picking from a list while typing, `show_when`,
> `counts_only`, `wording = "due"`), [`EXAMPLES.md`](EXAMPLES.md), the shipped
> modules in `modules/` (People, Household stock with `catalogue.csv`, Pets)
> and your own drafts. Edit only `workbench/`; the usual Definition of done.
> Cite a source and date checked for every fact a household might rely on.
>
> **What changed since batch 3:** only drinking water counts towards days of
> water ("Safe to drink" on water items); typing a stock item's name offers
> your catalogue (now `modules/stock/catalogue.csv`), with the household's own
> items first; long linked lists have a find box. Lane A is building nested
> places next (from your Home layout draft), then dates shown the household's
> way, then lots (from your design).
>
> 1. **UX check of the new picking and drinking water (J2, J3).** Run `main`
>    with the three example households and a fresh one. Try a real stocktake
>    of 20 goods by typing, including regional names (tinned/canned,
>    capsicum/bell pepper, torch/flashlight) and a few the catalogue lacks.
>    Report, worst first, with exact wording: missing or badly ranked goods,
>    fills that are wrong (category, unit, drinking), anything confusing.
> 2. **Catalogue round 4: fill the gaps from evidence.** In
>    `workbench/drafts/catalogue/catalogue.csv`: add `typical_sizes` and
>    `shelf_life_unopened` wherever an official or manufacturer source gives
>    them (try the FoodKeeper data through foodsafety.gov or data.gov, FSANZ,
>    the UK Food Standards Agency, WRAP); fix anything round 1 of the UX check
>    finds; add goods it shows are missing. Keep keys stable. Note every
>    source and licence in `NOTES.md`.
> 3. **A list of places to pick from.** `workbench/drafts/home_layout/places.csv`
>    with `name`, `kind` (room, storage or spot), `also_called` and `typical_in`
>    (house, apartment, townhouse): Kitchen, Pantry, Laundry, Linen cupboard,
>    Garage, Shed, Under the stairs, Top shelf, Bottom drawer and so on, with
>    AU, US and UK names (cupboard/closet, wardrobe, boot/trunk). About 120
>    rows. Lane A will use it for typing places the same way as goods.
> 4. **Nested places: the exact behaviour, as acceptance checks.** In
>    `workbench/drafts/home_layout/ACCEPTANCE.md`, write numbered checks Lane A
>    can turn into tests: the full path shown everywhere ("Kitchen › Pantry ›
>    Shelf 3"), picking a place by typing any part of the path, moving a shelf
>    to another room, refusing a place inside itself, deleting a room that
>    still holds things, and how each example household's current places move
>    into rooms and spots (give the mapping row by row).
> 5. **Lots and dates: acceptance checks.** Same for
>    `workbench/drafts/stock_lots/ACCEPTANCE.md`: the stocktake, the weekly
>    shop, using oldest first, throwing out an expired lot, what *Needs
>    attention* says, and dates typed and shown as 20/05/27 in AU, UK and NZ
>    and 05/20/27 in the US (with the edge cases: 1/2/27, 2027-05-20, typing
>    a two-digit year), plus how today's single-date items become lots.
> 6. **Readiness questions, tied to real records.** For each of your 49
>    questions, set `answered_by` to an exact field that exists now (a People
>    role, a Pets field, a Household stock category with an amount above zero,
>    or a Home layout or Medical table from your drafts), or `none`. List in
>    `NOTES.md` the rules the core needs to decide "already answered".
> 7. **Two more module drafts from Corey's vision.** `collections` (a hobby or
>    collection such as Lego sets, trading cards or vinyl: item, set or
>    catalogue number, condition, where it is, bought for, value now, sold
>    for, with a total value) and `vehicles` (registration, insurance and
>    service due dates through `watch` with `wording = "due"`, the roadside
>    assistance number in People, and a car emergency kit as Household stock
>    in a "car" place). Example data for the three households.
> 8. **A plain getting-started guide for households.** Draft
>    `workbench/drafts/guide/GETTING_STARTED.md` for someone who has never
>    used it: download, open, the Windows warning, setup, the first ten
>    minutes, a stocktake, printing the emergency sheet, Save and exit, and
>    updating. Use the screenshots in `docs/screenshots/` by path. Lane A will
>    promote it into `docs/`.

## Lane B roadmap: what comes after batch 4

Work down this list in order once batch 4 is done; it is long on purpose, so
there is always a next thing. One pull request per numbered item. Each item
names the milestone in [`ROADMAP.md`](ROADMAP.md) it feeds. If Lane A's work
changes an item, Lane A updates this list; if you find something more
important, propose it at the top of `workbench/STATUS.md` under "Messages to
Lane A" and carry on.

### Batch 5: making the first release excellent (M1 polish, M2)

9. **UX check after each Lane A merge** (standing task, every batch): nested
   places, dates, lots as they land. Journeys J1 to J5, worst first, exact
   wording, screenshots by path.
10. **Accessibility review** of every screen in `docs/screenshots/`: keyboard
    use, labels, contrast, text size, what a screen reader would say. Cite
    WCAG 2.2 criteria; suggest exact fixes.
11. **Restore and export, designed from the household's side (M2).** Screen by
    screen: finding a backup by date, seeing what it contains before
    restoring, restoring into a new folder first, undoing a restore, "Export
    everything" as CSV files that open in Excel and Google Sheets. Acceptance
    checks Lane A can test.
12. **Receipt entry (M2).** Research how supermarket receipts look in AU, US,
    UK and NZ (made-up examples only): line formats, abbreviations ("TOM
    TINNED 400G"), multi-buys, weights. Draft a matching table from receipt
    words to catalogue keys for the 200 most common lines, and the review
    screen ("we think this is Tinned tomatoes, 4 tins: yes / change").
13. **Shopping list from what's running low.** Design the list: grouped by
    shop aisle or category, quantities to reach "keep at least", ticking off
    in the shop, and the trip coming home as stock in. Acceptance checks.
14. **CSV import (M2).** The columns a household would bring from a
    spreadsheet or another app; matching to catalogue goods and places;
    what a dry run shows before anything is saved.
15. **Helpers and the Agent API (M2), from the household's side.** What a
    helper may propose, how the review queue reads ("A helper added 12 items
    from Saturday's receipt: check them"), how to say no, and what must never
    happen (a helper changing something a person edited). Use DESIGN 7.

### Batch 6: readiness and country content (M3)

16. **Medical, final.** Fold in the UX findings, Pets-style example data and
    gaps that ask sensible questions; mark it ready to promote.
17. **Readiness prompts as screens.** How a prompt appears, the four answers
    (Yes, Not relevant, Not yet, Tell me more), when it comes back, the
    coverage view ("23 of 49 looked at") that never says "safe". Acceptance
    checks; tie to `answered_by`.
18. **Country packs, round 2.** Every Australian state and territory, the
    largest US states by population, UK nations, NZ regions: emergency
    bodies, warning systems and apps, hazards, water guidance, each cited and
    dated, with a review-by date. Note licences that forbid reuse.
19. **Seasonal checklists.** Bushfire season, cyclone season, winter storms,
    heat waves, hurricane season: what official sources say to check, when,
    tied to Household stock categories and Home layout records.
20. **Getting out in a hurry.** A "grab list" draft (what to take, where it
    is, who carries what) linked to People, Pets, Medical and Documents, and
    a printable one-page version.

### Batch 7: understanding the numbers (M4)

21. **Outcomes, defined.** For waste, shortages, money and readiness: the
    exact metric, the records it comes from, the minimum history before it
    shows anything, and the plain sentence it produces ("Thrown away this
    month: 3 items, last month: 7; based on 31 days"). Never claim a win
    without the household confirming it.
22. **The question loop, worked examples.** Twenty realistic made-up
    situations (a jump in milk thrown away, water dropping, a pet losing
    weight): the change noticed, the explanations worth asking about, the
    sensible question, and two that must never be asked (no plausible link).
23. **Charts that help.** Which three or four charts a household would
    actually look at, sketched in words with the data each needs.

### Batch 8: more of what households keep (M5)

24. **Promote-ready drafts**: Collections, Vehicles, Documents, Home care, Wine
    and the Garden example, each with labels, `empty`, gaps, sheets and
    example data matching the shipped modules.
25. **Home inventory for insurance**: valuables room by room, with what they
    cost, serial numbers and where receipts and photos are kept; a printable
    list for a claim. Note privacy: this is sensitive.
26. **Tools and things lent out**: who borrowed what and when it's due back.
27. **Utilities and household accounts**: providers, account numbers kept
    private, outage and fault lines in People, meter locations in Home layout.

## Brief for Lane B, batch 3 (done)

> You are Lane B, the checker and drafter. You have full internet access for
> research. Read these first: `AGENTS.md`, this page, [`BACKLOG.md`](BACKLOG.md)
> (Corey's own feedback), [`VISION.md`](VISION.md), [`DESIGN.md`](DESIGN.md)
> sections 5 and 6 (the file contracts: `watch`, `gaps`, `adjusts`, sheets,
> labels including `empty`), [`MODULES.md`](MODULES.md), the shipped modules in
> `modules/` (People, Household stock, Pets) as the standard to match,
> `examples/households/` for the made-up data style, your own
> `workbench/research/`, and [`EXAMPLES.md`](EXAMPLES.md) to see the screens.
>
> Edit **only `workbench/`**. Follow the Definition of done; one pull request
> per numbered task, each explained in plain words for Corey. Use made-up data
> only (fiction-reserved phone numbers, `example.com` emails). Cite a source
> and the date checked for every fact a household might rely on. Where a task
> needs something the core cannot do yet, do not work around it: write what is
> needed in the draft's `NOTES.md` (what the household sees, then what the core
> would have to do), and Lane A builds it. Pets is shipped now; leave it alone.
>
> **Corey's priorities (do these first, in this order):**
>
> 1. **A list of common goods to pick from (the catalogue).** When Corey does a
>    stocktake he wants to type "kid…", pick **Kidney beans** from a list, and
>    only type a new name when it is missing. Draft
>    `workbench/drafts/catalogue/`:
>    - `catalogue.csv`, one row per good: `key`, `name` (as a household says
>      it), `category` (one of Household stock's categories in
>      `modules/stock/tables.toml`), `also_called` (search words, separated
>      by `|`, including regional names: tinned/canned, capsicum/bell pepper,
>      nappies/diapers, torch/flashlight), `unit` (the usual unit: tins, kg,
>      litres, packs, rolls), `typical_sizes` (such as 400 g|800 g),
>      `shelf_life_unopened` (months, where a source gives one),
>      `shelf_life_source`, `notes`.
>    - Work in rounds. **Round 1:** the 150 goods most households keep (pantry
>      staples, water, first aid, cleaning, toiletries, batteries and power,
>      pet food, basic hardware). Open the pull request so Corey can react, then
>      **round 2** to about 400 and **round 3** towards 800, adding what Corey
>      and the example households show is missing.
>    - **Water needs care**, because only drinking water counts towards days
>      of water: drinking water (bottled or stored tap), filtered, boiled,
>      sparkling, distilled or demineralised (not for long-term drinking;
>      irons and CPAP machines), non-drinking stored water (flushing,
>      washing), water purification tablets. Add a column `counts_as_drinking_water`
>      (yes/no) with a sourced reason for each water row.
>    - Use public sources such as the USDA FoodKeeper data (public domain) and
>      food safety agencies (FSANZ, UK Food Standards Agency) for shelf life;
>      record each source's licence in `NOTES.md`.
>    - In `NOTES.md`, describe how picking should feel (type-ahead, best
>      matches first, regional names, "Add 'xyz' as a new item"), and what a
>      household's own additions should do (kept locally, offered next time).
> 2. **Home layout (a new module).** Corey wants to record where things are as
>    **Kitchen › Pantry › Shelf 3**. Draft `workbench/drafts/home_layout/`:
>    - Places that nest: area or room (Kitchen, Garage), storage inside it
>      (Pantry, Grey shelves), and a spot (Shelf 3, Top drawer). Compare one
>      places table that links to itself (`parent`) with fixed levels
>      (room, storage, spot); recommend one in `NOTES.md`, with what the core
>      must do to show the full path in drop-downs and lists.
>    - The home itself for emergencies: floors, exits and the way out from
>      upstairs, where the water main, gas shut-off and power board are,
>      smoke alarms (with battery or test dates), fire extinguishers and
>      blankets, and where the first aid kit and go-bags are kept. A printable
>      "Our home" sheet: the shut-offs, exits and where the safety things are.
>    - Say in `NOTES.md` how Household stock's existing `places` should move
>      into this (Lane A will migrate it).
> 3. **Layered use-by dates (lots).** Corey has 3 tins of beans that expire in
>    a month and 10 that expire in six months, and wants that recorded
>    gracefully. Draft the design in `workbench/drafts/stock_lots/`:
>    - Tables: an item (Kidney beans, keep at least 6) and its lots (3 tins,
>      use by 20/05/27, Kitchen › Pantry › Shelf 3; 10 tins, use by
>      20/11/27, Garage › Grey shelves). The item's amount is the sum of its
>      lots.
>    - Walk through, screen by screen in words: a stocktake ("Kidney beans,
>      Kitchen › Pantry › Shelf 3, 5, use by 20/05/27"), the weekly shop
>      coming in, using some (which lot? suggest oldest first, and let the
>      person change it), throwing out an expired lot, and what *Needs
>      attention* shows ("3 tins of Kidney beans expire in 30 days").
>    - Dates must be typed the household's way: 20/05/27 in Australia and the
>      UK, 05/20/27 in the US. Note what the core must do.
>    - List exactly what the core would need (amounts summed from lots,
>      running low on the total, use-by per lot, choosing a lot when stock
>      goes out, moving today's single-date items into lots).
>
> **Then:**
>
> 4. **Medical, ready to promote.** Bring `workbench/drafts/medical/` to the
>    standard of `modules/people`: labels and help text written for a
>    household, list and form order, an `empty` first step, `watch` rules
>    (kit check due, training renewal, with `wording = "due"`), `gaps` that
>    ask sensible questions ("Is there a first aid kit?"), and a printable
>    sheet if one helps. Answer every open question in its `NOTES.md`.
> 5. **Readiness prompts, drafted as content.** In
>    `workbench/drafts/readiness/prompts.toml`, write 40 to 60 "Have you
>    thought about…?" prompts (DESIGN 10.5): `question`, `why` (one plain
>    sentence), `fits` (which households: `home_type`, `storeys`, `hazards`,
>    `pets`, `mobility_needs`, `country`), `answered_by` (a record that
>    already answers it, such as a People role or a Home layout shut-off),
>    `review_every` (months) and `source` (an official link with the date
>    checked). Group them by situation (fire, flood, storm, heat, power cut,
>    medical, leaving home in a hurry). Ask, never assert; never say a
>    household is safe.
> 6. **Country packs, drafted as content.** From your research, write
>    `workbench/drafts/country-packs/AU.toml`, `US.toml`, `UK.toml` and
>    `NZ.toml`: emergency numbers, the main emergency bodies, household water
>    guidance (amount per person per day), and the hazards each body lists,
>    every value with its source and date checked. Leave out anything you
>    cannot cite.
> 7. **More household modules, drafted.** `documents` (where important papers
>    are kept: passports, insurance, wills, warranties, with renewal dates
>    through `watch`) and `home_care` (smoke alarms, gutters, the water
>    heater, with when each was last done; note what repeating tasks need from
>    the core). Polish `wine` the same way as Medical.
> 8. **Example data for every draft.** For each draft, add `example.toml`
>    rows for the three example households in the format of
>    `examples/households/*.toml` (the Smiths' two-storey house layout, the
>    Garcias' apartment and go-bags, Sam Taylor's flat), so Lane A can extend
>    the screenshots when promoting.
> 9. **UX check after each Lane A merge.** Run the current `main` with
>    `python tools/load_example.py <household> --data <temporary folder>` and
>    walk journeys J1 to J5. Report anything confusing, worst first, in
>    `workbench/reports/<date>-ux-check.md`, with exact suggested wording.

## Brief for Lane B, batch 2 (done)


> You are the second agent on Dashboard Plus (repository
> coreysreid/Dashboard-Plus). Read `AGENTS.md` and `docs/WORKSTREAMS.md` first.
> You are Lane B: the checker and drafter. From now on you edit **only
> `workbench/`**. Follow the Definition of done for every pull request, and
> keep `workbench/STATUS.md` current.
>
> 0. **Finish your two open branches** as described in the first request in
>    the Requests table of `docs/WORKSTREAMS.md`.
> 1. **Check M1 like a household would.** Install the pinned libraries, run
>    the dashboard (`PYTHONPATH=src python -m dashboard --data <a temporary
>    folder>`), and walk through journeys J1 to J5 in `docs/JOURNEYS.md` and
>    the M1 list in `docs/ROADMAP.md` with made-up data. Time how long adding
>    20 stock items takes. Write findings to
>    `workbench/reports/<date>-m1-check.md`, worst first.
> 2. **Fine-tune People and Household stock.** Read `modules/people/` and
>    `modules/stock/` as a non-technical person would meet them on screen:
>    labels, help text, choices, which columns show in lists, what prints.
>    Suggest exact changes in `workbench/reports/<date>-module-wording.md`.
>    Do not edit `modules/`.
> 3. **Draft three modules** in `workbench/drafts/`, files only: `pets` (pets,
>    weigh-ins, food, medication given, vet visits; vets link to People),
>    `medical` (first aid kits, kit checks, first aid and CPR training with
>    renewal dates; see `docs/DESIGN.md` section 6) and `wine` (a compact
>    collection). Each with a `NOTES.md` listing open questions and any core
>    features it would need. Read `docs/DESIGN.md` sections 5 and 6 first.
> 4. **Country pack research** in `workbench/research/country-packs/AU.md` and
>    `US.md`: national and state emergency bodies, emergency numbers, hazards
>    those bodies list for households, household preparedness guidance
>    (including any stated water per person per day), and each source's
>    licence. Link every fact to an official source with the date checked.
>    Write nothing you cannot cite. Follow `docs/decisions/0025-*.md`.
>
> One pull request per numbered task. Use made-up data only. Explain each pull
> request in plain language for Corey.
