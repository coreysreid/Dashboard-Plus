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
| Core M1 steps 1 to 6, printable sheets | A | merged |
| People and Household stock modules, stock in and out | A | merged |
| Gaps check, README for households | A | merged |
| M1 release checks, example households and screenshots | A | in review; three checks need Corey on Windows |
| Module guide and garden example | B | merged (pull request #10) |
| SECURITY, CONTRIBUTING, issue templates | B | branch `lane-b/project-files`, needs a pull request |
| Batch 2 (below) | B | ready to start |

## Requests between lanes

| From | To | Request | State |
|---|---|---|---|
| A | B | Finish both in-flight branches: merge `main`, run `python tools/check_all.py` (it will ask you to regenerate `PROJECT_MAP.md`), resolve `docs/decisions/INDEX.md` by keeping every row in number order, start the commit message with `Lane B:`, then mark each "ready for a pull request" in `workbench/STATUS.md`. | module guide merged (pull request #10); project files: merge `main` again (it is missing #9 and #10), then mark it ready |
| A | B | Start batch 2 below, all inside `workbench/`. | done: pull requests #12, #13, #15 |
| B | A | M1 check findings (`workbench/reports/2026-11-09-m1-check.md`): J1 first step, J5 home summary. | fixed in the M1 release checks pull request |
| B | A | Module wording (`workbench/reports/2026-11-09-module-wording.md`). | adopted, lightly changed: sheet titles keep "Emergency sheet" ("fridge copy" and "with private medical details"), supplies sheet is "Emergency supplies"; the rest as suggested |

## Brief for Lane B, batch 2

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
