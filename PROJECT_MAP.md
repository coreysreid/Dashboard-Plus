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
| pyproject.toml | Python version and (no) dependencies | changing dependencies |
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
| __main__.py | Command-line entry point: prints the version while the program is still being built. | changing how it starts |
| core/ | Core services: records, links, review, audit, backups | changing anything topic-neutral |
| web/ | Web layer: pages, forms, Agent API | changing screens or the API |

## src/dashboard/core/  (summary: core services, nothing topic-specific)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Core services: records, links, time, review, audit and backups (not built yet). | adding a core service |

## src/dashboard/web/  (summary: pages, forms and the Agent API)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Web layer: pages, forms and the Agent API (not built yet). | adding a screen or route |

## tests/  (summary: automatic tests; synthetic data only)
Run: PYTHONPATH=src python -m unittest discover -s tests

| Entry | What it is | Open it when |
|---|---|---|
| test_check_privacy.py | Tests for the privacy check. | changing privacy rules |
| test_check_indexes.py | Tests for the index check. | changing index rules |
| test_project_map.py | Tests for the project map generator. | changing the map |
| test_repository.py | Tests that this repository passes its own checks. | CI fails on the repo itself |

## tools/  (summary: scripts that keep the repository safe and tidy; run by CI)
| Entry | What it is | Open it when |
|---|---|---|
| repofiles.py | Shared helper that lists the files belonging to the repository. | a tool needs the file list |
| check_privacy.py | Fail the build if anything private or machine-specific is committed. | tuning what counts as private |
| check_indexes.py | Check that every folder has a short, complete and current INDEX.md. | changing the index rules |
| make_project_map.py | Build PROJECT_MAP.md from every INDEX.md in the repository. | changing the map format |
