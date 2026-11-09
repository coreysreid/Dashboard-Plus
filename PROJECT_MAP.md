# Project map

Every part of the project in one page. Generated from the `INDEX.md` in each
folder by `tools/make_project_map.py`; do not edit by hand. To change a
description, edit the folder's `INDEX.md` and run the tool again.

## ./  (summary: Dashboard Plus, a local-first home dashboard; start here)
Follow the INDEX.md in a folder before opening its files. Hidden files are not listed.

| Entry | What it is | Open it when |
|---|---|---|
| README.md | Friendly introduction, status and how to run the checks | first meeting the project |
| AGENTS.md | How an AI agent should work here | before changing anything |
| CLAUDE.md | One line pointing to AGENTS.md | never; tools read it for you |
| LICENSE | MIT licence, Copyright (c) 2026 Corey Reid | checking reuse terms |
| PROJECT_MAP.md | Generated one-page map of every INDEX.md | you want the whole picture |
| config.example.toml | Example settings (the real file lives in the data folder) | adding a setting |
| pyproject.toml | Project name, version and Python version | changing project metadata |
| requirements.txt | The few runtime libraries, pinned to exact versions | adding or updating a library |
| requirements.lock | Generated: those libraries with checksums | never by hand; regenerate it |
| .github/ | CI workflow and pull request checklist | changing the automatic checks |
| docs/ | Vision, core promise, design, decision records | understanding why or how |
| modules/ | Optional features, one folder each | adding or changing a topic |
| src/ | The program itself | changing how the app works |
| tests/ | Automatic tests | adding or fixing a test |
| tools/ | Repository checks and generators | changing CI checks |

## docs/  (summary: the plan and the reasons behind it)
| Entry | What it is | Open it when |
|---|---|---|
| VISION.md | Big picture, principles, non-goals | judging if it fits the product |
| CORE.md | The one-page v1 promise and acceptance list | testing any feature against it |
| DESIGN.md | Object model, modules, API, security, packaging, build order | planning or building |
| ROADMAP.md | Milestones M1 to M5, what M1 includes, success measures, open questions | deciding what comes next |
| WORKSTREAMS.md | How two agents split the work: lanes, owned files, contracts, status | before starting any work |
| JOURNEYS.md | Short stories of real use, each an acceptance test | reviewing the experience |
| INFLUENCES.md | Books and ideas we build on, credited, and how we credit | adding or checking a credit |
| decisions/ | One record per technical choice, with downsides | questioning or reversing a choice |

## docs/decisions/  (summary: why each technical choice was made)
One record per decision, from `TEMPLATE.md`. Never deleted; reversed ones are
marked Superseded. Each lists downsides, cost to undo, and the sign it was wrong.

| Record | Decision | Status |
|---|---|---|
| [0001](0001-write-down-every-technical-decision.md) | Write down every technical decision | Accepted |
| [0002](0002-python-with-server-built-pages-for-the-web-side.md) | Python with server-built pages for the web side | Accepted |
| [0003](0003-bundle-python-using-the-official-embeddable-package.md) | Bundle Python using the official embeddable package | Accepted |
| [0004](0004-apache-echarts-for-charts.md) | Apache ECharts for charts | Accepted |
| [0005](0005-statistics-with-the-standard-library-only-v1.md) | Statistics with the standard library only (v1) | Accepted |
| [0006](0006-second-automatic-backup-on-the-computer-itself.md) | Second automatic backup on the computer itself | Accepted |
| [0007](0007-two-trust-levels-for-modules-with-an-honest-warning.md) | Two trust levels for modules, with an honest warning | Accepted |
| [0008](0008-local-network-addresses-allowed-only-when-typed-in-exactly.md) | Local-network addresses allowed only when typed in exactly | Accepted |
| [0009](0009-sqlite-in-delete-journal-mode-with-full-syncing.md) | SQLite in delete-journal mode with full syncing | Accepted |
| [0010](0010-one-real-sqlite-table-per-declared-table.md) | One real SQLite table per declared table | Accepted |
| [0011](0011-the-program-listens-on-this-computer-only.md) | The program listens on this computer only | Accepted |
| [0012](0012-each-module-has-its-own-migration-track.md) | Each module has its own migration track | Accepted |
| [0013](0013-a-short-index-md-in-every-folder-checked-by-ci.md) | A short INDEX.md in every folder, checked by CI | Accepted |
| [0014](0014-mit-licence.md) | MIT licence | Accepted |
| [0015](0015-household-stock-and-watch-views-in-v1.md) | Household stock module and watch views in v1 | Accepted |
| [0016](0016-people-module-in-v1-on-by-default.md) | People module in v1, on by default | Accepted |
| [0017](0017-only-ask-plausible-questions.md) | Only ask plausible questions | Accepted |
| [0018](0018-outcomes-wins-and-monthly-screen.md) | Outcomes, confirmed wins and a monthly screen | Accepted |
| [0019](0019-vegetable-garden-as-the-worked-example.md) | Vegetable garden as the worked example module | Accepted |
| [0020](0020-tests-and-tools-use-only-the-standard-library.md) | Tests and repository tools use only the standard library | Accepted |
| [0021](0021-ci-on-windows-and-linux-with-lf-line-endings.md) | CI runs on Windows and Linux, files use LF line endings | Accepted |
| [0022](0022-index-file-format-and-rules.md) | INDEX.md format and the rules the checker enforces | Accepted |
| [0023](0023-credit-the-ideas-we-build-on.md) | Credit the ideas we build on, in our own words | Accepted |
| [0024](0024-prompt-engine-in-core-content-in-modules.md) | Prompt engine in the core, content in modules | Accepted |
| [0025](0025-country-packs-are-sourced-dated-and-link-first.md) | Country packs: sourced, dated, and link-first | Accepted |
| [0026](0026-medical-and-readiness-modules-in-v1.md) | Medical and Readiness modules in v1 | Accepted |
| [0027](0027-release-in-milestones-starting-with-m1.md) | Release in milestones, starting with M1 | Accepted |
| [0028](0028-flask-and-waitress-for-the-web-layer.md) | Flask and Waitress for the web layer | Accepted |
| [0029](0029-portable-windows-build-pipeline.md) | How the portable Windows folder is built | Accepted |
| [0030](0030-plain-sqlite-with-numbered-sql-migrations.md) | Plain SQLite access and numbered SQL migrations | Accepted |
| [0031](0031-module-files-are-checked-and-migrations-generated.md) | Module files are checked strictly, and their migrations are generated | Accepted |
| [0032](0032-one-checked-path-for-every-record-change.md) | One checked path for every record change, with soft deletes and history | Accepted |
| [0033](0033-screens-generated-from-declarations.md) | Screens generated from declarations, with a launch-link sign-in | Accepted |
| [0034](0034-two-agents-work-in-separate-lanes.md) | Two agents work in separate lanes with fixed contracts | Accepted |
| [0035](0035-watch-views-and-days-of-cover.md) | How running low, expiring soon and days of cover are worked out | Accepted |
| [0036](0036-automatic-backups-in-two-places.md) | Automatic backups: daily and on close, in two places | Accepted |
| [TEMPLATE](TEMPLATE.md) | Blank record to copy for a new decision | recording a decision |

## modules/  (summary: optional features; each folder is one module)
No modules are built yet. Each module will be a folder with its own INDEX.md.
Planned for v1: people, stock, medical, readiness, pets, garden, wine, graphing,
analysis, api_connector.
See docs/DESIGN.md section 6 for the module contract.

| Entry | What it is | Open it when |
|---|---|---|

## src/  (summary: the program's Python code)
| Entry | What it is | Open it when |
|---|---|---|
| dashboard/ | The program package | changing how the app works |

## src/dashboard/  (summary: the program package)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Dashboard Plus: a local-first home dashboard (package root). | checking the version |
| __main__.py | Command-line entry point: open the dashboard, or close a running one safely. | changing how it starts |
| errors.py | Errors whose message is written for the person using the program, not a programmer. | adding an error people will see |
| server.py | Start and stop the local web server, and remember how to reach it. | changing startup, closing or ports |
| core/ | Core services: records, links, review, audit, backups | changing anything topic-neutral |
| web/ | Web layer: pages, forms, Agent API | changing screens or the API |

## src/dashboard/core/  (summary: core services, nothing topic-specific)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Core services: database, migrations, modules and records; review and backups come next. | adding a core service |
| backups.py | Automatic backups: one a day, one at every safe close, kept in two places. | changing when or where backups are made |
| db.py | Open the SQLite database with settings that are safe on USB drives. | changing how the data file is opened or backed up |
| migrations.py | Apply numbered migrations, one track for the core and one per module. | changing how database changes are applied |
| migrations/ | The core's own numbered database changes | adding a core table |
| modules.py | Find module folders, check their files, and explain any mistakes in plain words. | changing what module files may say |
| records.py | Create, change, delete and read records, checking every value and keeping a history. | changing how records are saved or checked |
| settings.py | Read and write household settings kept in the database (core__settings). | storing a new setting |
| schema.py | Turn a module's declared tables into SQL, and work out its next migration. | changing how tables are built |
| watch.py | Work out what is running low, what expires soon, and how many days of supplies are on hand. | changing running low, expiring or days of cover |
| startup.py | Prepare the database at start-up: load modules, back up if needed, and migrate. | changing what happens at start-up |

## src/dashboard/core/migrations/  (summary: the core's numbered database changes; never edit a released one)
Add a new file with the next number instead of changing an old one.

| Entry | What it is | Open it when |
|---|---|---|
| 0001_core_tables.sql | Settings and the list of modules in use | checking the core tables |
| 0002_audit_history.sql | The history of every change to every record | checking how history is stored |

## src/dashboard/web/  (summary: the screens: pages, forms and their protections)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Web layer: pages, forms and the Agent API (not built yet). | adding a screen or route |
| app.py | Build the Flask web application and its local-only protections. | changing sign-in, protections or reports |
| pages.py | Pages built from module declarations: the record grid, add and edit forms, and history. | changing the grid or forms |
| display.py | Turn declared tables and stored values into friendly labels, form fields and text. | changing how values look |
| templates/ | The HTML pages | changing what a page looks like |

## src/dashboard/web/templates/  (summary: HTML pages; base.html holds the shared look)
| Entry | What it is | Open it when |
|---|---|---|
| base.html | Shared layout, colours (light and dark), header and footer | changing the overall look |
| home.html | Home page: days of cover, needs attention, tables with counts, backup and data file status | changing the home screen |
| attention.html | Running low, expiring soon and days of cover, with the working shown | changing the attention page |
| grid.html | A table's records, a page at a time, sortable | changing the list of records |
| rows.html | One page of grid rows (also loaded as you scroll) | changing a row |
| form.html | Add and edit forms, delete and restore, and history | changing the form |
| start.html | Shown to a browser that was not opened by the shortcut | changing that message |
| report.html | Shown after saving a report | changing that message |
| close.html | The "Close Dashboard safely" page | changing how closing works |
| closed.html | Shown after a safe close | changing that message |
| error.html | Plain-language error page with "Save a report" | changing error wording |

## tests/  (summary: automatic tests; synthetic data only)
Run: pip install --require-hashes -r requirements.lock, then
PYTHONPATH=src python -m unittest discover -s tests

| Entry | What it is | Open it when |
|---|---|---|
| support.py | Shared helpers for tests: temporary folders and made-up (synthetic) modules. | writing a new test |
| test_db.py | Tests for opening the database safely, transactions, statement splitting and backups. | changing the database layer |
| test_migrations.py | Tests for numbered migrations: tracks, checksums, newer databases, rollback and backups. | changing migrations |
| test_modules.py | Tests for loading module folders and the plain-language problems they report. | changing module rules |
| test_records.py | Tests for saving, checking, linking, deleting and restoring records, and their history. | changing how records are saved |
| test_schema.py | Tests for turning declared tables into SQL and generating the next migration. | changing table building |
| test_startup.py | Tests for preparing the database at start-up with the modules found. | changing start-up |
| test_check_privacy.py | Tests for the privacy check. | changing privacy rules |
| test_check_indexes.py | Tests for the index check. | changing index rules |
| test_project_map.py | Tests for the project map generator. | changing the map |
| test_server.py | Tests for starting, protecting and safely closing the local web server. | changing startup or closing |
| test_watch.py | Tests for running low, expiring soon and days of cover, and for checking `watch` sections. | changing watch rules |
| test_backups.py | Tests for automatic backups: daily, on close, in two places, and keeping only recent ones. | changing backups |
| test_web.py | Tests for the screens: sign-in by launch link, grid paging, forms, history and reports. | changing a screen |
| test_main.py | Tests for the command-line entry point and its plain-language messages. | changing the command line |
| test_build_portable.py | Tests for the portable Windows build, using a stand-in for the Python download. | changing the build |
| test_lock_requirements.py | Tests for the requirements lock generator. | changing how libraries are locked |
| test_repository.py | Tests that this repository passes its own checks. | CI fails on the repo itself |

## tools/  (summary: scripts that check, lock and build the project; run by CI)
| Entry | What it is | Open it when |
|---|---|---|
| repofiles.py | Shared helper that lists the files belonging to the repository. | a tool needs the file list |
| check_privacy.py | Fail the build if anything private or machine-specific is committed. | tuning what counts as private |
| check_indexes.py | Check that every folder has a short, complete and current INDEX.md. | changing the index rules |
| lock_requirements.py | Write requirements.lock: every pinned library with the checksums PyPI publishes. | updating a library |
| build_portable.py | Build the portable Windows folder and zip: bundled Python, libraries and launchers. | changing what ships in the folder |
| portable.toml | Pinned Python version, download address and checksum for the build | updating the bundled Python |
| smoke_test_portable.py | Start the built portable folder, check it answers, and close it safely. | the Windows build check fails |
| make_migration.py | Write a module's next numbered migration from its tables.toml. | a module's tables changed |
| make_project_map.py | Build PROJECT_MAP.md from every INDEX.md in the repository. | changing the map format |
