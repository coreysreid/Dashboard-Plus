# docs/decisions/  (summary: why each technical choice was made)
One record per decision, from `TEMPLATE.md`. Never deleted; reversed ones are marked Superseded. Each lists downsides, cost to undo, and the sign it was wrong.

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
| [0014](0014-mit-licence.md) | MIT licence | Superseded by 0065 |
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
| [0037](0037-first-run-wizard-and-settings.md) | One first-run wizard that doubles as the settings page | Accepted |
| [0038](0038-printable-sheets-from-module-files.md) | Printable sheets are declared by modules and printed by the browser | Accepted |
| [0039](0039-people-module-shape.md) | What the People module records, and its two emergency sheets | Accepted |
| [0040](0040-household-stock-module-shape.md) | What the Household stock module records, and how water is counted | Accepted |
| [0041](0041-tests-index-may-be-longer.md) | The tests folder index may be longer than 25 lines | Accepted |
| [0042](0042-a-workbench-for-the-second-agent.md) | The second agent works only in a workbench folder, as checker and drafter | Accepted |
| [0043](0043-records-that-change-a-count.md) | Stock in and out updates the item's count automatically | Accepted |
| [0044](0044-gaps-are-asked-not-asserted.md) | Gaps are declared in module files and asked as questions | Accepted |
| [0045](0045-example-households-and-generated-screenshots.md) | Three made-up households, and screenshots made from them automatically | Accepted |
| [0046](0046-show-the-water-basis-and-backup-status.md) | Show the water estimate's daily amount, and whether the second backup worked | Accepted |
| [0047](0047-pets-moved-forward.md) | Pets is switched on now, built from the second agent's draft | Accepted |
| [0048](0048-pick-from-a-catalogue-while-typing.md) | Pick goods from a list while typing, with your own items first | Accepted |
| [0049](0049-nested-places.md) | Places can sit inside other places, and show their full path | Accepted |
| [0050](0050-restore-brings-back-what-went-with-it.md) | Restoring brings back what went with it; backups and counts made safer | Accepted |
| [0051](0051-medical-promoted.md) | Medical readiness switched on from Lane B's draft; `none = {}` gaps | Accepted |
| [0052](0052-dates-the-households-way.md) | Dates typed and shown the household's way (20/05/27 or 05/20/27), stored as 2027-05-20 | Accepted |
| [0053](0053-batches-for-layered-use-by-dates.md) | Stock kept in batches, each with its own use-by date and place | Accepted |
| [0054](0054-home-layout-uses-the-places-you-already-have.md) | Home layout switched on, using the places the household already has; no data moves | Accepted |
| [0055](0055-modules-confined-and-security-review-fixes.md) | Modules confined to their own tables; security review fixes | Accepted |
| [0056](0056-home-page-grouped-by-area.md) | Home page grouped by area: main lists large, other lists as links (`home` in labels.toml); forms save again in current browsers | Accepted |
| [0057](0057-batch-picker-follows-the-item.md) | "Which batch" lists only the chosen item's batches and says what leaving it blank does | Accepted |
| [0058](0058-vehicles-promoted.md) | Vehicles switched on from Lane B's draft, linking to People and Household stock; a roadside assistance role | Accepted |
| [0059](0059-private-details-only-when-asked.md) | Private details sent to the screen only when the person asks (lists, records, private sheets) | Accepted |
| [0060](0060-garden-example-outside-installed-modules.md) | Keep the worked garden outside installed modules | Accepted |
| [0061](0061-public-reporting-and-contribution-rules.md) | Public contribution and private security reporting routes | Accepted |
| [0062](0062-documents-promoted.md) | Important documents switched on from Lane B's draft: places and people linked, no document numbers stored | Accepted |
| [0063](0063-home-care-promoted.md) | Home care switched on from Lane B's draft: jobs at your places, done by your People, on dates you type; no repeats invented | Accepted |
| [0064](0064-real-browser-check.md) | A real-browser check clicks through setup, dates, stock in, private details and closing in Chromium (Linux CI job); a refused save keeps a private detail | Accepted |
| [0065](0065-agpl-licence.md) | Licence changed to GNU AGPL v3 or later (from MIT) | Accepted |
| [0066](0066-helper-keys-shown-once-kept-as-a-fingerprint.md) | Helpers get a key from Settings: shown once, kept only as a fingerprint outside the database | Accepted |
| [0067](0067-agent-api-v1-local-bearer-only-module-scoped.md) | The Agent API v1: local, bearer-only, module-scoped, and never private details | Proposed, awaiting Corey's OK |
| [0068](0068-helper-suggestions-wait-until-a-person-accepts.md) | Helpers' suggestions wait in their own place until a person accepts them | Accepted |
| [0069](0069-no-module-called-core-or-with-double-underscores.md) | A module may not be called "core" or use double underscores in its name | Accepted |
| [0070](0070-stocktake-corrections.md) | Count this batch saves the difference as one stocktake correction in Stock in and out; never the count on top; an out-of-date review is refused | Accepted |
| [0071](0071-private-sheet-opens-only-by-choice.md) | The private sheet opens only from its Show button (a POST), never from a link such as ?show=1 | Accepted |
| [0072](0072-reminders-skip-finished-rows-and-sheets-print-linked-contacts.md) | Due-date reminders can skip finished rows (`where` on `expiring`); sheets print a linked contact's phone from a required module, never a private column | Accepted |
| [0073](0073-lent-out-promoted.md) | Things lent out switched on from Lane B's draft: borrowers in People, reminders only while still out, Stock count untouched | Accepted |
| [0074](0074-agent-api-hardening.md) | Agent API hardening: links into parts a helper was not given are invisible, one 404 for "not yours" and "not there", hidden characters and key-like text refused, 120 requests a minute, one decision per suggestion | Accepted |
| [0075](0075-one-step-actions-and-date-order.md) | One-step buttons declared in tables.toml (Mark returned), saved through the ordinary change path and refused when pressed twice; `not_before` keeps one date from coming before another | Accepted |
| [0076](0076-garden-promoted.md) | Vegetable garden switched on from Lane B's draft: beds at your Places, job reminders only while not done, no growing advice | Accepted |
| [0077](0077-home-layout-private-access-details.md) | Home layout gets a private "Codes or access details" box, hidden until Show and never printed | Accepted |
| [0079](0079-restore-from-a-backup.md) | Restore from a backup: copies checked read-only, the chosen one prepared on a new file, a checked before-restore copy, an atomic swap while no page holds the file, and an Undo that survives a restart | Accepted |
| [TEMPLATE](TEMPLATE.md) | Blank record to copy for a new decision | recording a decision |
