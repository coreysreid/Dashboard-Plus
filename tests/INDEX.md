# tests/  (summary: automatic tests; synthetic data only)
How to run them is in AGENTS.md.
| Entry | What it is | Open it when |
|---|---|---|
| support.py | Shared helpers for tests: temporary folders and made-up (synthetic) modules. | writing a new test |
| test_db.py | Tests for opening the database safely, transactions, statement splitting and backups. | changing the database layer |
| test_migrations.py | Tests for numbered migrations: tracks, checksums, newer databases, rollback and backups. | changing migrations |
| test_csv_import.py | Tests for Import from a spreadsheet: reading a CSV, matching columns, the dry run, staging for Review and Accept. | changing spreadsheet import |
| test_modules.py | Tests for loading module folders and the plain-language problems they report. | changing module rules |
| test_actions.py | Tests for actions: one-step buttons like Mark returned, the date order rule `not_before` (decision 0075), and the checks on actions that add a record (decision 0091). | changing actions or date order |
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
| test_suggest.py | Tests for suggestions while typing: matching, the household's own records first, and module catalogues. | changing picking from a list |
| test_dates.py | Tests for dates the household's way (Lane B's stock lots acceptance checks 8 to 11, decision 0052). | changing how dates are typed or shown |
| test_stock_batches.py | Tests for batches: layered use-by dates in Household stock (decision 0053, DESIGN.md 5.7). | changing batches, stock in and out or use-by warnings |
| test_stocktake_corrections.py | Tests for stocktake corrections: "Count this batch" saves one correction, never the count on top (decision 0070). | changing Count this batch or stocktake corrections |
| test_data_safety.py | Tests for the data-safety fixes from the November 2026 review: restore, stock counts, decimals and backups. | changing delete, restore, stock counts or backups |
| test_robustness.py | Tests for the robustness fixes from the November 2026 review: modules, switching off, long lists, privacy. | changing module loading, settings or long lists |
| test_adjusts.py | Tests for records that change a linked quantity (stock in and out), and the checks on `adjusts`. | changing stock in and out |
| test_sync_stage1.py | Tests for sync stage 1: permanent record IDs, revisions, the filtered change log and the travel rule (decision 0100). | changing record IDs, the change log or what may travel |
| test_backups.py | Tests for automatic backups: daily, on close, in two places, and keeping only recent ones. | changing backups |
| test_home_setup.py | Tests for Set up my home: rooms, storage spots inside them and the connections between rooms (decision 0103). | changing Set up my home or connections between places |
| test_setup.py | Tests for the first-run wizard and the settings page. | changing setup or settings |
| test_sheets.py | Tests for printable sheets: checking sheets.toml and printing the emergency sheet. | changing sheets |
| test_module_confinement.py | A module's database changes may touch only its own tables (security review, decision 0055). | changing how module migrations run |
| test_module_*.py | Tests that run a real module end to end, one file per module | changing a module |
| test_workbench_drafts.py | Check every draft module in workbench/drafts: it loads, its migrations match, and it starts cleanly. | a draft module fails |
| test_web.py | Tests for the screens: sign-in by launch link, grid paging, forms, history and reports. | changing a screen |
| test_units.py | Tests for singular units: "1 tube", not "1 tubes", in batch names and item summaries. | changing unit wording |
| test_browser_check.py | Run the real-browser check (tools/browser_check.py) when Node, Playwright and Chromium are here; skip otherwise. | changing a screen or its browser code |
| test_main.py | Tests for the command-line entry point and its plain-language messages. | changing the command line |
| test_home_page.py | Tests for the grouped home page: one group per area, main lists large, other lists as links, all reachable. | changing the home page or `home` in labels.toml |
| test_build_portable.py | Tests for the portable Windows build, using a stand-in for the Python download. | changing the build |
| test_build_macos.py | Tests for the unsigned Mac app build, using a stand-in for the Python download (runs on any system). | changing the Mac build |
| test_data_location.py | Tests for choosing the data folder: Application Support inside a Mac app, never inside the app (decision 0096). | changing where records are kept by default |
| test_lock_requirements.py | Tests for the requirements lock generator. | changing how libraries are locked |
| test_repofiles.py | Tests for the shared list of repository files, including during a merge with conflicts. | a tool counts a file twice |
| test_repository.py | Tests that this repository passes its own checks. | CI fails on the repo itself |
| test_helper_*.py | Tests for helpers: keys, suggestions waiting for a person, the /api/v1 door, and the Settings and Review screens | changing helpers, the helper API or Review |
| test_mcp_connector.py | Tests for the AI-assistant connector (MCP over stdio) against a real local Dashboard: tools, errors and the key. | changing the connector or the helper API routes |
| test_helper_address.py | Tests for the steady helper address (decision 0092): Dashboard's address file, and the connector reading it each call. | changing how a connector finds Dashboard |
| test_helper_key_rotation.py | Tests for Make a new key (decision 0093): one press, one new key shown once, the old key stopped, the helper kept. | changing how a helper key is replaced |
| test_export.py | Tests for Export my records: every table of an example household, private details, formula safety and the download. | changing the export |
| test_restore.py | Tests for restoring a backup: checks that change nothing, the safe swap, Undo after a restart, and refusals. | changing restore or Undo |
| test_api_contract.py | Tests that the published API description (openapi-v1.json) matches the real /api/v1 routes, errors and replies. | changing a helper route, reply or error code |
| test_helper_starting_amounts.py | Tests for decision 0102: a new Stock item with its starting amount as one suggestion, and the helper's starting message. | changing starting amounts on suggestions or the starting message |
| test_grouped_suggestions.py | Tests for receipt lines on suggestions and for suggestions that point at an earlier one in the same batch (decision 0097). | changing source lines, refs or grouped Review rows |
| test_sync_extra_checks.py | Sync stage 1 extra checks from STAGE1_ACCEPTANCE.md: Utilities and Pets values, held People details, corrupt IDs and links, confinement, Set up my home rows. | changing sync checks or what may travel |
| test_review_speedups.py | Tests for faster Review (decision 0101): Accept all by group, ticked rows, keys, fixed buttons and Allow 200 more today. | changing Accept all, ticked rows, Review keys or the daily limit |
