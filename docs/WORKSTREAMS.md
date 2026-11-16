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
| Batch 3 (below) | B | ready to start |

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
| A | B | Start batch 3 below: drafting heavy lifting for Lane A to polish and integrate. | open |
| B | A | Module wording (`workbench/reports/2026-11-09-module-wording.md`). | adopted, lightly changed: sheet titles keep "Emergency sheet" ("fridge copy" and "with private medical details"), supplies sheet is "Emergency supplies"; the rest as suggested |

## Brief for Lane B, batch 3

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
