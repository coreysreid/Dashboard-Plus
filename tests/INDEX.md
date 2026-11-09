# tests/  (summary: automatic tests; synthetic data only)
How to run them is in AGENTS.md.
| Entry | What it is | Open it when |
|---|---|---|
| support.py | Shared helpers for tests: temporary folders and made-up (synthetic) modules. | writing a new test |
| test_db.py | Tests for opening the database safely, transactions, statement splitting and backups. | changing the database layer |
| test_migrations.py | Tests for numbered migrations: tracks, checksums, newer databases, rollback and backups. | changing migrations |
| test_modules.py | Tests for loading module folders and the plain-language problems they report. | changing module rules |
| test_example_garden.py | Exercise the garden example with a temporary database and synthetic harvest. | changing the garden example |
| test_records.py | Tests for saving, checking, linking, deleting and restoring records, and their history. | changing how records are saved |
| test_schema.py | Tests for turning declared tables into SQL and generating the next migration. | changing table building |
| test_startup.py | Tests for preparing the database at start-up with the modules found. | changing start-up |
| test_check_privacy.py | Tests for the privacy check. | changing privacy rules |
| test_check_indexes.py | Tests for the index check. | changing index rules |
| test_project_map.py | Tests for the project map generator. | changing the map |
| test_server.py | Tests for starting, protecting and safely closing the local web server. | changing startup or closing |
| test_watch.py | Tests for running low, expiring soon and days of cover, and for checking `watch` sections. | changing watch rules |
| test_gaps.py | Tests for gaps: details worth filling in, declared in a table's `watch.gaps` and asked as questions. | changing gaps |
| test_examples.py | Tests for the example households: each loads cleanly and shows exactly what it was written to show. | changing an example household |
| test_adjusts.py | Tests for records that change a linked quantity (stock in and out), and the checks on `adjusts`. | changing stock in and out |
| test_backups.py | Tests for automatic backups: daily, on close, in two places, and keeping only recent ones. | changing backups |
| test_setup.py | Tests for the first-run wizard and the settings page. | changing setup or settings |
| test_sheets.py | Tests for printable sheets: checking sheets.toml and printing the emergency sheet. | changing sheets |
| test_module_*.py | Tests that run a real module end to end, one file per module | changing a module |
| test_workbench_drafts.py | Check every draft module in workbench/drafts: it loads, its migrations match, and it starts cleanly. | a draft module fails |
| test_web.py | Tests for the screens: sign-in by launch link, grid paging, forms, history and reports. | changing a screen |
| test_main.py | Tests for the command-line entry point and its plain-language messages. | changing the command line |
| test_build_portable.py | Tests for the portable Windows build, using a stand-in for the Python download. | changing the build |
| test_lock_requirements.py | Tests for the requirements lock generator. | changing how libraries are locked |
| test_repofiles.py | Tests for the shared list of repository files, including during a merge with conflicts. | a tool counts a file twice |
| test_repository.py | Tests that this repository passes its own checks. | CI fails on the repo itself |
