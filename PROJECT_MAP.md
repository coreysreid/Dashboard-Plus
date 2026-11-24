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
| CONTRIBUTING.md | Public contribution rules and checks | before contributing |
| SECURITY.md | How to report a problem that could expose household data | reporting security concerns |
| CLAUDE.md | One line pointing to AGENTS.md | never; tools read it for you |
| LICENSE | GNU AGPL v3 or later; Copyright (C) 2026 Corey Reid (README) | checking reuse terms |
| PROJECT_MAP.md | Generated one-page map of every INDEX.md | you want the whole picture |
| config.example.toml | Example settings (the real file lives in the data folder) | adding a setting |
| pyproject.toml | Project name, version and Python version | changing project metadata |
| requirements.txt | The few runtime libraries, pinned to exact versions | adding or updating a library |
| requirements.lock | Generated: those libraries with checksums | never by hand; regenerate it |
| .github/ | CI workflow and pull request checklist | changing the automatic checks |
| docs/ | Vision, core promise, design, decision records | understanding why or how |
| examples/ | Optional worked module examples, not installed by default | learning to write a module |
| modules/ | Optional features, one folder each | adding or changing a topic |
| src/ | The program itself | changing how the app works |
| tests/ | Automatic tests | adding or fixing a test |
| workbench/ | The second agent's own space: drafts, reports, research (not part of the program) | reviewing Lane B's work |
| tools/ | Repository checks and generators | changing CI checks |

## docs/  (summary: the plan and the reasons behind it)
| Entry | What it is | Open it when |
|---|---|---|
| VISION.md | Big picture, principles, non-goals | judging if it fits the product |
| CORE.md | The one-page v1 promise and acceptance list | testing any feature against it |
| DESIGN.md | Object model, modules, API, security, packaging, build order | planning or building |
| ROADMAP.md | Milestones M1 to M5, what M1 includes, success measures, open questions | deciding what comes next |
| BACKLOG.md | User 1's feedback from using it, and what happened to each item | adding feedback or choosing the next fix |
| WORKSTREAMS.md | How two agents split the work: lanes, owned files, contracts, status | before starting any work |
| JOURNEYS.md | Short stories of real use, each an acceptance test | reviewing the experience |
| plans/ | Build plans for larger pieces of work, such as the Agent API | building or reviewing a big feature |
| INFLUENCES.md | Books and ideas we build on, credited, and how we credit | adding or checking a credit |
| MODULES.md | Plain-language guide to writing a module with a garden example | making a module |
| EXAMPLES.md | Three made-up households shown at every stage, welcome to closing (generated) | showing what it looks like |
| screenshots/ | The gallery's images, one folder per household (generated) | using a screenshot elsewhere |
| releases/ | Release checks: what was verified for each milestone, and how | preparing or judging a release |
| decisions/ | One record per technical choice, with downsides | questioning or reversing a choice |

## docs/decisions/  (summary: why each technical choice was made)
One record per decision, from `TEMPLATE.md`. Never deleted; reversed ones are marked Superseded. Each lists downsides, cost to undo, and the sign it was wrong.

| Record | Decision | Status |
|---|---|---|
| [0001](0001-write-down-every-technical-decision.md) | Write down every technical decision | Accepted |
| [0002](0002-python-with-server-built-pages-for-the-web-side.md) | Python with server-built pages for the web side | Accepted |
| [0003](0003-bundle-python-using-the-official-embeddable-package.md) | Bundle Python using the official embeddable package | Accepted |
| [0004](0004-apache-echarts-for-charts.md) | Apache ECharts for charts | Superseded by 0109 (for now) |
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
| [0067](0067-agent-api-v1-local-bearer-only-module-scoped.md) | The Agent API v1: local, bearer-only, module-scoped, and never private details | Accepted |
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
| [0078](0078-export-my-records.md) | Export my records: one zip of spreadsheet files for the household, private details left out, text guarded against formulas, read from one moment | Accepted |
| [0079](0079-restore-from-a-backup.md) | Restore from a backup: copies checked read-only, the chosen one prepared on a new file, a checked before-restore copy, an atomic swap while no page holds the file, and an Undo that survives a restart | Accepted |
| [0080](0080-import-from-a-spreadsheet.md) | Import from a spreadsheet (CSV) in Settings: columns matched, every row checked like a helper's suggestion, ready rows wait on Review as one batch by "Import '<file>'"; the file is never kept; private details not imported | Accepted |
| [0081](0081-household-sharing-options.md) | Sharing with the household, three options designed (A: take turns through a shared folder; B: one home base, others use a browser on home Wi-Fi; C: every copy syncs), a mode label on every page, default "On this computer only"; changes the privacy and security rules | Superseded by 0089 |
| [0082](0082-every-page-shows-the-connection-mode.md) | Every page says "On this computer only" and how many helpers can look; the footer no longer says nothing is ever sent | Accepted |
| [0083](0083-local-ai-assistant-connector.md) | A local connector for AI assistants (MCP over stdio, no new library): eight tools, one per helper API route; results labelled as household data, not instructions; address and key only from the person, never echoed; Settings, Helpers shows settings to paste with a placeholder key | Accepted |
| [0084](0084-published-api-description.md) | A published OpenAPI 3.1 description of the helper API, served read-only at /api/v1/openapi.json behind the same key as every route, and held to the real routes, errors and replies by a contract test | Accepted |
| [0085](0085-review-queue-cap.md) | A helper may have at most 500 suggestions waiting on Review (a setting); a batch that would go over is refused whole with 429 `review_queue_full`; imports do not count; accepting or rejecting frees room | Accepted |
| [0086](0086-connector-checks-it-is-really-dashboard.md) | Before every request the connector asks `POST /api/v1/hello` (no key) to prove it is the Dashboard that made its key: an HMAC over a fresh nonce and host:port from the kept fingerprint; only on a match does the key go, down the same connection | Accepted |
| [0087](0087-add-a-helper-form-makes-one-key.md) | An Add a helper form makes one key even if sent twice: a one-use form token, and plain words on a repeat | Accepted |
| [0088](0088-limits-hold-under-simultaneous-requests.md) | Helper limits are checked again inside the write lock; other API versions answer plain 404 JSON; count pages say "1 tin" | Accepted |
| [0089](0089-household-sync-main-and-members.md) | Household sync: one main, members push requests to Review, over a private network (Tailscale or WireGuard); private details never travel in v1 | Accepted (direction; security review before shipping) |
| [0090](0090-documents-record-where-copies-are-kept.md) | Documents record where copies are also kept (a named place such as "Blue USB drive" ticked on each paper); never the paper, a scan or a number | Accepted |
| [0091](0091-home-care-mark-done.md) | Home care Mark done: an action may add a linked record through a small form, saved once in one transaction with the record's revision and a one-use operation number, a deliberate next date (optional household repeat) and an Undo that refuses after any change | Accepted |
| [0092](0092-steady-helper-address.md) | A steady helper address: Dashboard writes `data/run/helper-address.json` (address and run ID only) atomically at start and removes its own on close; the connector reads it for every call via `DASHBOARD_PLUS_ADDRESS_FILE`, then still does the 0086 hello before the key | Accepted |
| [0093](0093-one-step-helper-key-rotation.md) | "Make a new key" for a helper: one press, one-use token, key shown once, old key stopped; same helper, grant and history; pause, file swap, finish in that order, failing closed; in-flight writes rechecked | Accepted |
| [0094](0094-import-pauses-on-duplicates-and-unclear-dates.md) | Import pauses before sending: a name already in the list is skipped unless "Add anyway" is ticked, short dates that read either way need one tick, links that match nothing and skipped columns are summed up; Review wording trimmed | Accepted |
| [0095](0095-wine-promoted.md) | Wine collection is switched on from Lane B's draft: counts typed by hand, free-text place, ordinary price and tasting notes that enter exports (and say so), no reminders or advice, a wine with bottles or notes cannot be deleted; examples in Smith and Taylor | Accepted |
| [0096](0096-macos-build.md) | An unsigned Mac app preview: `tools/build_macos.py` bundles python-build-standalone 3.12.10 (pinned checksums) into `Dashboard Plus.app` for the Mac's processor; inside an app the data folder defaults to `~/Library/Application Support/Dashboard Plus/` (0700), never inside the app; CI builds and starts it on Apple silicon; signing, notarisation and a real-Mac test still to come | Accepted |
| [0097](0097-receipt-lines-and-grouped-suggestions.md) | A suggestion may carry the receipt line and price it was read from (screened, shown on Review as the helper's words, never saved in records); an entry may point at an earlier one with `{"ref": N}`, so a new Stock item and its Stock in are one group: accepting the Stock in adds the item first in one transaction, rejecting the item rejects what needs it | Accepted |
| [0098](0098-empty-pickers-offer-to-add-and-import-waits-for-dates.md) | An empty picker offers to add one in a new tab; Import's Send waits for date choices; Documents Notes help points to the copies field | Accepted |
| [0099](0099-utilities-promoted.md) | Utilities and accounts is switched on from Lane B's draft: services link to People (provider, fault contact) and to an exact Home layout meter; the sheet prints the People fault phone; the account reference and notes stay private and off lists, sheets, exports and helpers; deleting a contact or meter clears the link; examples in all three households | Accepted; needing Home layout replaced by 0115 |
| [0100](0100-sync-stage-1-stable-ids-and-change-log.md) | Sync stage 1, nothing sent: every record gets a random permanent ID and a revision (added by the core after each module's migrations, under that module's own confinement), every change writes a filtered change-log line beside history, `travels`/`travels_when` in tables.toml keep access instructions, Home layout access details and vehicle registration on the computer where they were typed, and a restore starts a new epoch | Accepted |
| [0101](0101-review-speed-ups-and-allow-more.md) | Faster Review: Accept all asks first, then accepts group by group (each group all or nothing); tick boxes with Accept or Reject ticked (a group ticks whole); keys (Up/Down or J/K, A, R, Space) as a small script; Accept and Reject in one fixed column; "Allow 200 more today" per helper from a page with a one-use token (core 0008, history), the day being the household's own; 429 tells the helper to stop and ask | Accepted |
| [0102](0102-helper-starting-prompt-and-stock-with-amount.md) | A starting message for the helper's assistant in Settings, Helpers (copy box) and as `GET /api/v1/guide` and the `dashboard_how_to_help` tool: its lists, fields, private fields by name, links to look up first, the stock model and today's limits, never records or the key; a new Stock item may carry its amount, use-by date and place as one suggestion, added with its first batch on Accept | Accepted |
| [0103](0103-set-up-my-home.md) | Set up my home: one page for rooms and areas (Places), storage spots inside them and which rooms connect (new `stock__connections`, migration 0006 in Household stock); offered after the welcome and always on Home and Settings; `pair` in tables.toml refuses self-links and repeats either way round; doors to outside marked by kind; a deleted room takes its connections; nothing private | Accepted |
| [0104](0104-readiness-questions.md) | Readiness switched on from Lane B's draft: 49 sourced "Have you thought about…?" questions in a module `prompts.toml` (schema 1), fitted only from Settings; exact record matches offered, never assumed; answers Yes / Not relevant / Not yet as ordinary records with the record's permanent ID and a revision fingerprint; back for review on the chosen date, after 12 months or when that record changes; at most two on Home; "looked at", never "safe"; helpers look but never answer (`suggestions = false`); answers travel; drills later reuse the same answers | Accepted |
| [0105](0105-receipt-review-unmatched-and-repeat.md) | Receipts on Review: each Stock in in one line with its unit, group words true under group-by-group Accept, the result names what was added; a receipt line a helper could not match waits for Choose item or Skip line (undoable until Finish receipt review); a receipt that looks sent before (same dated items, amounts and units, never its text) waits for Reject this copy or Keep this as another purchase, rechecked under the write lock; card-shaped numbers refused | Accepted |
| [0106](0106-mac-wording-meter-paths-sync-checks.md) | Mac preview wording follows the 21 November read-through (no absolute "nothing is sent", no "only once", two ZIPs, chip check); a link column may say `with_place` so Utilities shows the meter's full place path; Utilities still requires Home layout; sync check also names a pair pointing at nothing, with six more stage 1 tests | Accepted; needing Home layout replaced by 0115 |
| [0107](0107-routine-checklists.md) | Things to do: Today, This week, This month, This year and No date yet over every table whose reminder says `wording = "due"`, read fresh with no stored ticks; each row finished by its record's own Mark done form, a one-step button that ends the reminder, or Open record to update; a late task shows once as Due since; Routines module (repeat in days to years, Mark this occurrence done, Skip this time, Undo); `adds.copy`, `latest` without `into`, `repeat.from`/`anchor` and `counts_as`; household week start in Settings | Accepted |
| [0108](0108-think-it-through-drills.md) | Think it through: eight calm drills (`[[scenario]]` with ordered steps in `prompts.toml` schema 2, drill-only `[[step]]` with exact missing words, `[[emergency]]` numbers by country), fitted from Settings and `has_records`, country-limited sources marked "Source needs checking" when old or broken; a shared step also saves its Questions answer; practice runs (`drill_runs`, `drill_steps`) with Continue later, practised and look-again dates and history; own words private, `travels = "never"`, never exported or shown to helpers | Accepted |
| [0109](0109-first-charts.md) | The first two charts, drawn on the server as SVG with an equal table: today's drinking water by item from the same `watch.supplies` result as Home (left-out items with their reason), and one pet's recorded weigh-ins as dots (a `chart` line in tables.toml); exact empty words, nothing private, no library | Accepted |
| [0110](0110-pet-feeding-log.md) | Pet feeding log switched on from Lane B's draft: food put out (not eaten), Add food from the pet's page, a generic `daily` declaration adding up accepted entries by the household's own day (the `household.timezone` setting; instants kept as sent) one total per unit, never inferring a missed meal; Home line, day page, a 14-day sheet that is complete or refused, possible-repeat warning on Review; every column travels, the sheet omits notes | Accepted |
| [0111](0111-vehicle-running-log.md) | Vehicle running log beside Vehicles from Lane B's draft: dated odometer readings (lower or mixed-unit ones ask Go back or Save as entered, never refuse; a dots chart in the latest unit) and dealer, independent or other estimates on a service's page, private amount and scope behind Show that never travel; no mileage due logic, the service date stays the only reminder; core gains `confirm`, chart `unit`/`latest`/`caveat`, labels `under` and `add_button`, and a household distance unit | Accepted |
| [0112](0112-done-history-and-move-in-guards.md) | One-press buttons (Garden Mark done, Mark returned, any one-step action) write a named history entry with the day pressed, so they count under Things to do's Done lists and This year and offer Undo straight after (optional `undo` words); move-in guards from Lane B's read-through: a new item's starting amount plus a Stock in for it gets a `may_count_twice` warning on Review and in the answer, a link sent as a name is refused with the exact full-path matches, and private text the household keeps is flagged on Review if copied into a suggestion, never repeated | Accepted |
| [0113](0113-readiness-asks-again-only-for-what-matters.md) | Readiness asks again only for what matters: each record-backed question and drill step lists `ask_again` fields and states in prompts.toml (schema 3, checked at load); a versioned field stamp of IDs and change counts, never values, replaces the revision fingerprint (narrows 0104 and 0108); module off and delete keep asking until answered; older answers upgraded without being re-asked; This year fits 320px | Accepted |
| [0114](0114-bundle-time-zone-data.md) | Ship `tzdata` (pinned and locked) so household days follow the household's time zone on Windows too; the CI Windows run had put pet feedings on the computer's day | Accepted |
| [0115](0115-optional-links-between-modules.md) | Optional links between modules: `optional_requires` in module.toml; a link into an optional module is nullable, hidden with household words while that module is off, kept by exact ID (guarded writes refuse any set, change or clear), neutral on lists, sheets, exports and helpers, a gone record is repair never a same-name guess; Utilities now needs only People, so an internet-only household can switch it on alone; Bills not promoted | Accepted |
| [0116](0116-helper-words-for-moving-in.md) | The helper's starting message, connector descriptions and OpenAPI no longer call an old tracker balance a purchase (it points to Count this batch), ask whether a receipt is already in the old count, say a Review-only price is not saved spending, and say when to refresh the guide and how to report sent, accepted, waiting and refused rows | Accepted |
| [0117](0117-bills-and-insurance.md) | Bills and insurance switched on from Lane B's draft beside Utilities (needs only People; Vehicles and Stock optional): private amount, cover, reference and notes that never travel; due words per row (`what_when`); one reminder per vehicle policy: nothing moves until the household chooses Keep, Review and move (row by row, by ID, after a backup; the old record kept read-only) or Decide later; Transfer back; sheets say when they are not complete | Accepted (User 1 to confirm the move choice) |
| [0118](0118-exit-sketch.md) | Our way-out sketch from Set up my home: a floor, sleeping and checked-window flag per room and a confirmed destination per door out (stock migration 0007), meeting place, help and building-plan answers in Settings; rooms as boxes and connections as lines drawn on the server in a steady grid, a complete text version with the same IDs, a sheet with legend and warnings on numbered continuation pages; only recorded possibilities and gaps, never a safe or independent route; no notes, codes or People details | Accepted |
| [TEMPLATE](TEMPLATE.md) | Blank record to copy for a new decision | recording a decision |

## docs/plans/  (summary: build plans for larger pieces of work, written before building)
| Entry | What it is | Open it when |
|---|---|---|
| agent-api-v1.md | The Agent API skeleton plan: helper keys, read routes, suggestions held for Review, security model, tests | building or reviewing the Agent API |
| household-sharing.md | Sharing with your household: three options (shared folder, home base on Wi-Fi, true sync), the mode label on every page, a recommendation and questions for User 1 | choosing or building household sharing |

## docs/releases/  (summary: release checks, one file per milestone)
| Entry | What it is | Open it when |
|---|---|---|
| M1.md | The M1 checks: what passed, how it was checked, and what needs a person on Windows | judging whether M1 is ready |

## docs/screenshots/  (summary: generated screenshots of the example households)
Made by `python tools/make_screenshots.py`; shown in docs/EXAMPLES.md. Do not edit by hand.
| Entry | What it is | Open it when |
|---|---|---|
| smith/ | The Smith family at every stage | showing a busy family |
| garcia/ | The Garcia household at every stage | showing care needs |
| taylor/ | Sam Taylor at every stage | showing a first week |

## docs/screenshots/garcia/  (summary: screenshots of The Garcia household, made up)
Made by tools/make_screenshots.py from examples/households. Do not edit by hand.
| Entry | What it is | Open it when |
|---|---|---|
| *.png | Each stage of using the dashboard, in order: welcome to closing | showing The Garcia household |

## docs/screenshots/smith/  (summary: screenshots of The Smith family, made up)
Made by tools/make_screenshots.py from examples/households. Do not edit by hand.
| Entry | What it is | Open it when |
|---|---|---|
| *.png | Each stage of using the dashboard, in order: welcome to closing | showing The Smith family |

## docs/screenshots/taylor/  (summary: screenshots of Sam Taylor, made up)
Made by tools/make_screenshots.py from examples/households. Do not edit by hand.
| Entry | What it is | Open it when |
|---|---|---|
| *.png | Each stage of using the dashboard, in order: welcome to closing | showing Sam Taylor |

## examples/  (summary: optional worked examples, not installed modules)
| Entry | What it is | Open it when |
|---|---|---|
| households/ | Three made-up households (people, contacts, stock) for demos, screenshots and tests. | demonstrating the program |
| garden/ | A files-only vegetable garden module to copy and adapt. | learning to make a module |

## examples/garden/  (summary: vegetable garden worked example)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | The garden module's identity and version. | changing its identity |
| tables.toml | Beds, crops, plantings, harvests and jobs. | changing garden records |
| labels.toml | Friendly forms and list columns. | changing screen wording |
| sheets.toml | A printable garden plan. | changing the printed plan |
| migrations/ | Numbered database changes generated from tables. | checking the database shape |

## examples/garden/migrations/  (summary: generated garden database changes)
| Entry | What it is | Open it when |
|---|---|---|
| 0001_update_tables.sql | First garden tables, generated by make_migration.py. | checking the initial database shape |

## examples/households/  (summary: three made-up households for demos, screenshots and tests)
Every name, number and address is invented; phones use ranges set aside for fiction, emails use example.com.
Each file: `title`, `summary`, `[setup]` (the first-run answers), then records as `[[module.table]]` rows.
Links name the record they point at (person = "Mary Smith"). Dates may be "today", "today+12" or "today-3"; a date and time "today-1 09:00" or "today-1T07:15".
Stock amounts are what is on hand today, after the `[[stock.movements]]` rows, which are oldest first.
Load one with: `python tools/load_example.py smith --data <an empty folder>`.
| Entry | What it is | Open it when |
|---|---|---|
| smith.toml | The Smith family: two parents, two children, a dog and a cat; Australia | showing a busy family |
| garcia.toml | The Garcia household: three generations, care needs and medication, a cat; United States | showing care needs |
| taylor.toml | Sam Taylor: one person just starting, with gaps to fill; United Kingdom | showing a first week |

## modules/  (summary: optional features; each folder is one module, made of files only)
Each module has module.toml, tables.toml, labels.toml, optional sheets.toml, and
numbered migrations. See docs/DESIGN.md section 6 for the module contract.

| Entry | What it is | Open it when |
|---|---|---|
| bills_insurance/ | Bills and insurance: dated bills and policies beside Utilities, provider from People, optional vehicle or place, private amount and cover; one reminder per vehicle policy by the household's choice; a dates sheet | changing bills or policies |
| documents/ | Where important papers are kept, whose they are and the review or renewal dates you choose; a review dates sheet | changing document records |
| garden/ | Vegetable garden: beds at your places, crops, plantings, harvests and jobs with a due date; a Garden plan sheet | changing garden records |
| home_care/ | Jobs around the home, where each is, who usually does it, last done and do again by; work done; a Home care sheet | changing home care jobs |
| home_layout/ | Ways out, shut-offs, smoke alarms and safety equipment, meters, each at one of your places; an Our home sheet | changing home layout records |
| lent_out/ | Things lent out: what, to whom (one of your People), lent on, due back and returned on; a Things still lent out sheet | changing loans |
| medical/ | First aid kits and where they are, kit checks, first aid training renewals; a first aid sheet | changing first aid records |
| people/ | Who lives here, who to call, important details, emergency sheets | changing people, contacts or the emergency sheet |
| pet_feeding/ | Pet feeding log: each bowl, refill or treat as food put out (not eaten), honest daily totals by the household's day in matching units, fast Add food, a 14-day sheet | changing feeding records |
| pets/ | Pets, their vet, treatments and medicine with due dates, weigh-ins, vet visits; a pet details sheet | changing pets |
| readiness/ | "Have you thought about…?": 49 questions in seven groups with official sources, the household's answers, and what may already be recorded | changing readiness questions or answers |
| routines/ | Routines: your own repeating tasks with a repeat you choose (days to years), one next date at a time, and each time done or skipped; shown on Things to do | changing routines |
| stock/ | Pantry, water, first aid, tools and hardware, with places (and which rooms connect), minimums and use-by dates | changing stock, running low or days of water |
| utilities/ | Utilities and accounts: each service, its provider, fault contact (from People) and meter (from Home layout, if it is on), a private account reference; a Utility contacts sheet | changing utility records |
| vehicle_running/ | Vehicle running log: dated odometer readings per vehicle and dealer or independent estimates for a Vehicles service, amounts private | changing readings or estimates |
| vehicles/ | Each vehicle, who to call if it breaks down, registration, insurance and service dates; a Vehicles sheet | changing vehicle records |
| wine/ | Wine collection: wines, bottle counts you type, a free-text place, tasting notes; a Wine collection sheet | changing wine records |

## modules/bills_insurance/  (summary: the Bills and insurance module, files only; built on Lane B's draft, beside Utilities)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (provider); Vehicles and Household stock only optionally (decisions 0115, 0117) | changing the module's details |
| tables.toml | Bills and policies with private amount, cover, reference and notes that never travel; due words per kind; `takes_over` of Vehicle insurance | adding a field or changing the reminder |
| labels.toml | Friendly labels and help, the optional vehicle and place words, and the household's words for moving a Vehicle insurance reminder | changing wording or order |
| sheets.toml | Bills and policies to check: names, kinds, providers and dates, nothing private | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/bills_insurance/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py bills_insurance --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_initial.sql | The commitments table and its link and date indexes, generated from tables.toml (optional links without a database rule) | checking how bills and policies are stored |

## modules/documents/  (summary: the Important documents module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (whose paper) and Household stock (places) | changing the module's details |
| tables.toml | Where each paper is kept, whose it is, its review or renewal date and the places copies are also kept (copy_places), with one gap question; no document numbers | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Document review dates sheet: names, kinds, dates and where copies are kept; no original places or numbers | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/documents/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py documents --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first table, generated from tables.toml | checking how the table is stored |
| 0002_copies_also_kept.sql | Places copies are kept, and the link from each paper to them | checking how copies are stored |

## modules/garden/  (summary: the Vegetable garden module, files only; built on Lane B's draft, linking to Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires Household stock (places) | changing the module's details |
| tables.toml | Beds, crops, plantings, harvests and jobs; a job reminder only while not done | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order, jobs main on home | changing wording or order |
| sheets.toml | Garden plan sheet: beds and where they are, plantings, jobs not yet done | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/garden/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py garden --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

## modules/home_care/  (summary: the Home care module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (who does it) and Household stock (places) | changing the module's details |
| tables.toml | Home care jobs with a do-again-by date, an optional household repeat, Mark done and one gap question, and the work done on each | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order, which list is main on home | changing wording or order |
| sheets.toml | Home care sheet: each job, where, who usually does it and its dates, with no notes | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/home_care/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py home_care --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_repeat_choice.sql | Adds the optional household repeat (every N weeks, months or years) to jobs, unset for every job | checking how the repeat is stored |

## modules/home_layout/  (summary: the Home layout module, files only; built on Lane B's draft, using Household stock's places)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires Household stock (for places) | changing the module's details |
| tables.toml | Ways out, shut-offs, alarms and safety equipment, meters, with due checks and gap questions | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Our home sheet: ways out, shut-offs, alarms and meters with full place paths | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/home_layout/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py home_layout --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_private_access_details.sql | Adds a private codes-or-access-details box to ways out, shut-offs, alarms and meters | checking the upgrade |

## modules/lent_out/  (summary: the Things lent out module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (the borrower) and Household stock (the item) | changing the module's details |
| tables.toml | Loans with a due-back reminder only while still out, a Mark returned button, and one question about reaching the borrower | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order, main list on home | changing wording or order |
| sheets.toml | Things still lent out sheet: what, who, their phone from People and the dates, with no notes | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/lent_out/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py lent_out --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

## modules/medical/  (summary: the Medical readiness module, files only; promoted from Lane B's draft)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People and Stock (for who and where) | changing the module's details |
| tables.toml | First aid kits, kit checks and first aid training, with due checks, renewals and gaps | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | First aid at home sheet: where the kits are and who has trained | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/medical/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py medical --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_where_kits_are_kept.sql | Adds whether each kit is kept at home, in a vehicle or somewhere else | checking how the tables are stored |

## modules/people/  (summary: the People module, files only)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description | changing the module's details |
| tables.toml | People, who to call (roles), important details (private), and gaps worth filling in | adding a field, a choice or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Emergency sheet, and a version with medical details | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/people/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py people --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

## modules/pet_feeding/  (summary: the Pet feeding log, files only; built on Lane B's draft, linking to Pets)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires Pets | changing the module's details |
| tables.toml | Food given: one entry per bowl, refill or treat, food put out (not eaten); `daily` totals by the household's day and the possible-repeat rule | adding a field or changing the daily words |
| labels.toml | Friendly labels, help text (put out, not eaten; units never converted), form and list order | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/pet_feeding/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py pet_feeding --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_initial.sql | The Food given table with pet and time indexes, generated from tables.toml (Lane B's draft, unchanged) | checking how feedings are stored |

## modules/pets/  (summary: the Pets module, files only; promoted from Lane B's draft)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (for vets and owners) | changing the module's details |
| tables.toml | Pets, treatments and medicine with next due, treatments given, weigh-ins, vet visits; due dates and gaps | adding a field, a choice or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Pet details sheet for a sitter, kennel or evacuation | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/pets/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py pets --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

## modules/readiness/  (summary: the Readiness module, files only: 49 "Have you thought about…?" questions, eight "Think it through" drills and the household's answers and practice runs)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; needs no other module (record matches into other modules find nothing while those are off) | changing the module's details |
| tables.toml | Your answers (one per question); Practice runs (drill, dates, Continue later or Practised); Practice answers (each step's choice, record chosen and private own words that never travel); helpers may look, never suggest | changing how answers or practice runs are kept |
| labels.toml | Friendly labels and help for Your answers, Practice runs and Practice answers, form and list order | changing wording or order |
| prompts.toml | The questions in seven groups (why, fits, exact record match, interval, source); then emergency numbers by country, drill-only steps with their missing-record words, and the eight drills with their sources | changing a question, a drill, a source or a record match |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/readiness/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py readiness --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The answers table, generated from tables.toml | checking how answers are stored |
| 0002_drill_runs.sql | Practice runs and practice answers for Think it through (decision 0108) | checking how practice runs are stored |

## modules/routines/  (summary: the Routines module, files only; the household's own repeating tasks, promoted from Lane B's routine checklist draft)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (who) and Household stock (places) | changing the module's details |
| tables.toml | Routines with an optional repeat (days, weeks, months, years) and one next date; Done or skipped keeps the planned date; Mark this occurrence done and Skip this time | adding a field or changing the actions |
| labels.toml | Friendly labels, help text, form and list order, routines main on home | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/routines/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py routines --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

## modules/stock/  (summary: the Household stock module, files only)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description | changing the module's details |
| tables.toml | Places (with a floor for the way-out sketch), connections between them (Set up my home), stock items (running low, use-by, days of water) and stock in and out | adding a field, category or rule |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Emergency supplies checklist | changing what prints |
| catalogue.csv | 800 common goods to pick from while typing (from Lane B's catalogue) | adding or correcting a good |
| places.csv | 120 rooms, cupboards and shelves to pick from while typing a place (from Lane B's list) | adding a place name |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/stock/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py stock --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |
| 0002_stock_in_and_out.sql | The Stock in and out table | checking how movements are stored |
| 0004_places_inside_places.sql | Places can sit inside other places ("Inside") | checking how nested places are stored |
| 0003_drinking_water.sql | "Safe to drink" on items; existing water stays counted | checking how drinking water is stored |
| 0006_connections_between_places.sql | Connections between places: which rooms lead into which, and doors to outside (decision 0103) | checking how connections are stored |
| 0007_way_out_sketch_facts.sql | A floor, sleeping and checked-window flag on places, and a confirmed destination on doors to outside, for the way-out sketch (decision 0118) | checking how the sketch's facts are stored |
| 0005_batches.sql | Batches: an item's stock split by use-by date and place; each existing item becomes one batch | checking how the tables are stored |

## modules/utilities/  (summary: the Utilities module, files only; built on Lane B's draft, linking to People and, optionally, Home layout)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (provider and fault contact); Home layout (meter) only optionally (decision 0115) | changing the module's details |
| tables.toml | Services with a private account reference and notes, the meter shown with its place path (`with_place`), and two gap questions about the fault contact | adding a field or a gap question |
| labels.toml | Friendly labels, help text (says what is private), form and list order, and the meter's words while Our home is off | changing wording or order |
| sheets.toml | Utility contacts sheet: service, provider, fault contact, their phone and the meter, with nothing private | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/utilities/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py utilities --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_initial.sql | The module's first table, generated from tables.toml | checking how services are stored |

## modules/vehicle_running/  (summary: odometer readings and service estimates beside Vehicles, files only; built on Lane B's draft)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires Vehicles (vehicles and services) and People (providers) | changing the module's details |
| tables.toml | Odometer readings with their gentle lower and mixed-unit checks and dots chart, and service estimates with private amount and scope | adding a field or a check |
| labels.toml | Friendly labels, help, form and list order, Add a reading, and the Cost estimates list on a service's page | changing wording or order |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/vehicle_running/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py vehicle_running --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_update_tables.sql | The readings and estimates tables with their indexes, generated from tables.toml | checking how the tables are stored |

## modules/vehicles/  (summary: the Vehicles module, files only; built on Lane B's draft, linking to People and Household stock)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires People (who to call) and Household stock (places, car kit) | changing the module's details |
| tables.toml | Vehicles, insurance renewals, services and checks, with due dates and one gap question | adding a field or a gap question |
| labels.toml | Friendly labels, help text, form and list order | changing wording or order |
| sheets.toml | Vehicles sheet: who to call, where each is kept and the dates, with no private numbers | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/vehicles/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py vehicles --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

## modules/wine/  (summary: the Wine collection module, files only; built on Lane B's draft, no links to other modules)
| Entry | What it is | Open it when |
|---|---|---|
| module.toml | Name, version, description; requires nothing | changing the module's details |
| tables.toml | Wines, bottles (a count you type, a free-text place, an ordinary price) and tasting notes; one question about where bottles are kept | adding a field or a gap question |
| labels.toml | Friendly labels, help text (says price and notes enter exports), form and list order | changing wording or order |
| sheets.toml | Wine collection sheet: wine, count, place and bought on, with no price or notes | changing what prints |
| migrations/ | Numbered database changes | after changing tables.toml |

## modules/wine/migrations/  (summary: this module's numbered database changes; never edit a released one)
Generate the next one with: python tools/make_migration.py wine --name <what_changed>

| Entry | What it is | Open it when |
|---|---|---|
| 0001_first_tables.sql | The module's first tables, generated from tables.toml | checking how the tables are stored |

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
| data_location.py | Choose the data folder: --data if given, Application Support inside a Mac app, else ./data. | changing where records are kept by default |
| server.py | Start and stop the local web server, and remember how to reach it. | changing startup, closing or ports |
| core/ | Core services: records, links, review, audit, backups | changing anything topic-neutral |
| web/ | Web layer: pages, forms, Agent API | changing screens or the API |
| connector/ | The local connector an AI assistant's app starts to use the helper API (MCP over stdio) | changing how assistants connect |

## src/dashboard/connector/  (summary: the local connector an AI assistant's app starts to use the helper API; decision 0083)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | The connector for AI assistants: a small local program that lets an assistant use the helper API through MCP. | finding your way in |
| __main__.py | Start the connector: `python -m dashboard.connector [--config FILE]`, launched by an AI assistant's app. | changing how it is started |
| mcp_server.py | The MCP server over stdio: JSON-RPC 2.0, one message per line, turning tool calls into helper API requests. | changing the protocol, errors or what results say |
| tools.py | The nine tools an assistant may use, one per helper API route, with their inputs checked before any request. | adding or changing a tool |
| client.py | Call the helper API on this computer: check it is the real Dashboard first, then send the key down that connection only. | changing how requests are sent or answers read |
| config.py | Where the connector finds Dashboard Plus and its key: environment values or a small file, checked before use. | changing where the address or key come from |

## src/dashboard/core/  (summary: core services, nothing topic-specific)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Core services: database, migrations, modules, records, backups, helpers and their suggestions. | adding a core service |
| backups.py | Automatic backups: one a day, one at every safe close, kept in two places. | changing when or where backups are made |
| restore.py | Restore from a backup: check copies without changing them, put one back safely, and undo it. | changing how a backup is checked, put back or undone |
| db.py | Open the SQLite database with settings that are safe on USB drives. | changing how the data file is opened or backed up |
| dates.py | Dates the household's way: typed and shown as 20/05/27 or 05/20/27, always stored as 2027-05-20. | changing how dates are typed or shown |
| naming.py | What to call a record wherever it appears: its name, or for a batch "Kidney beans, 3 tins". | changing how records are named |
| units.py | Say an amount of 1 with its unit in the singular: "1 tube", not "1 tubes". | changing how amounts and units read |
| migrations.py | Apply numbered migrations, one track for the core and one per module. | changing how database changes are applied |
| migrations/ | The core's own numbered database changes | adding a core table |
| modules.py | Find module folders, check their files, and explain any mistakes in plain words. | changing what module files may say |
| actions.py | Actions that add a linked record through a small form, like Mark done: one saved operation, a one-use number and Undo. | changing Mark done, its checks or Undo (also Undo of a one-press button, decision 0112) |
| records.py | Create, change, delete and read records, checking every value and keeping a history. | changing how records are saved or checked |
| prompts.py | Read and check a module's prompts.toml: "Have you thought about…?" questions, their groups, exact record matches and "Think it through" drills. | changing what prompts.toml may say |
| drills.py | Think it through: which drills fit the household, what each step may find in its records, and the practice runs kept with their dates. | changing how drills fit, cite sources, save runs or keep own words private |
| exit_sketch.py | The way-out sketch's facts: rooms by floor, recorded connections and doors to outside, and what still needs checking. | changing what the way-out sketch reads, its route words or Check together |
| questions.py | Which "Have you thought about…?" questions fit the household, what may already be recorded, and how many were looked at. | changing how questions fit, match records, come back or are counted |
| settings.py | Read and write household settings kept in the database (core__settings). | storing a new setting |
| schema.py | Turn a module's declared tables into SQL, and work out its next migration. | changing how tables are built |
| confirm.py | Gentle checks before a form saves, like an odometer reading lower than the last one: shown, never a block (0111). | changing Go back / Save as entered checks |
| suggest.py | Suggestions while typing: a household's own records first, then a module's list of common things. | changing how picking from a list matches |
| watch.py | Work out what is running low, what expires soon, how many days of supplies are on hand, and what is worth filling in. | changing running low, expiring, days of cover or gaps |
| checklist.py | Things to do: Today, This week, This month and This year over the due dates modules already keep (decision 0107). | changing which tasks show, their windows, week start or what counts as done |
| daily.py | Daily totals by the household's own day: accepted entries only, amounts added only in matching units (decision 0110). | changing the household day, daily totals or the possible-repeat match |
| startup.py | Prepare the database at start-up: load modules, back up if needed, migrate, and give permanent record IDs. | changing what happens at start-up |
| helper_address.py | The small address file a connector reads to find Dashboard after a restart: only the address and a run ID (0092). | changing how a connector finds Dashboard |
| helpers.py | Helpers the household has given a key to: making a key, checking it, replacing it, and turning it off. | changing how helper keys work |
| hello.py | Proof that an address is the real Dashboard Plus, worked out from a key without ever sending it (decision 0086). | changing the check the connector makes before sending a key |
| receipts.py | Receipt lines a helper could not match, and receipts sent twice: kept on Review, decided only by a person (0105). | changing receipt lines, Finish receipt review or the repeat-receipt warning |
| proposals.py | Suggestions from helpers and rows imported from a spreadsheet: checked, kept waiting, added only when a person accepts. | changing suggestions, limits or accepting |
| move_in.py | Move-in checks on helper suggestions: a starting amount counted twice, a link sent as a name, private details copied into text. | changing the double-count warning, name matches in refusals or the private-copy warning on Review |
| export.py | Export my records: one zip with a spreadsheet file for every table, a manifest and a plain-words README. | changing what the export contains |
| optional_links.py | Links into an optional module (decision 0115): kept by exact ID while it is off, shown in neutral words, never guessed. | changing what an optional link shows when its module is off or its record is gone |
| reminder_moves.py | One reminder per policy: a household chooses, row by row and by exact ID, to move an older list's reminder into a newer one, and can move it back (0117). | changing takes_over, Move, Keep, Transfer back or which record reminds |
| sync.py | Permanent record IDs, revisions and the filtered change log (sync stage 1): nothing leaves this computer. | changing record IDs, the change log or what may travel to another computer |
| csv_import.py | Read a spreadsheet saved as CSV, match its columns to a table's fields, and check every row before it goes to Review. | changing how spreadsheets are read or matched |

## src/dashboard/core/migrations/  (summary: the core's numbered database changes; never edit a released one)
Add a new file with the next number instead of changing an old one.

| Entry | What it is | Open it when |
|---|---|---|
| 0001_core_tables.sql | Settings and the list of modules in use | checking the core tables |
| 0002_audit_history.sql | The history of every change to every record | checking how history is stored |
| 0003_helpers.sql | Helpers, their suggestion batches and the suggested records waiting for a decision | checking how helpers and suggestions are stored |
| 0004_import_batches.sql | Batches can come from a spreadsheet import by a person, not only a helper; rows keep their spreadsheet row | checking how imported rows wait for Review |
| 0005_helper_key_rotation.sql | A helper can get a new key and keep its history: when the key was changed, a change still in progress, and a count of keys | checking how a key change is stored |
| 0006_proposal_source_lines.sql | A helper's suggestion can keep the line it was read from (a receipt line and price), shown on Review only | checking how source lines are stored |
| 0007_sync_identity.sql | Sync stage 1: the household ID and epochs, the change log, and values held after a kind change (decision 0100) | checking how permanent IDs and the change log are stored |
| 0008_helper_daily_allowance.sql | "Allow 200 more today": each press adds to one helper's daily limit for that day only, with who and when (decision 0101) | checking how a raised daily limit is stored |
| 0009_receipt_lines_and_repeats.sql | Receipt lines a helper could not match wait on Review as their own kind; a batch can be one receipt, stay open until finished, and be kept as another purchase (decision 0105) | checking how receipt lines and repeat receipts are stored |
| 0010_reminder_moves.sql | One reminder per policy: which older records (Vehicle insurance) were moved to a newer list (Bills and insurance), by exact IDs and a state, never names or dates (decision 0117) | checking how a moved reminder is stored |

## src/dashboard/web/  (summary: the screens: pages, forms and their protections)
| Entry | What it is | Open it when |
|---|---|---|
| __init__.py | Web layer: pages, forms, the Review screen and the helper API. | adding a screen or route |
| app.py | Build the Flask web application and its local-only protections. | changing sign-in, protections or reports |
| pages.py | Pages built from module declarations: the record grid, add and edit forms, and history. | changing the grid or forms |
| setup.py | The first-run wizard and the settings page: who lives here, the home, modules and backups. | changing setup questions or settings |
| home_setup.py | Set up my home: rooms and areas, the storage spots inside them, and which rooms connect, on one page. | changing the Set up my home page |
| action_form.py | An action's small form, such as Mark done: open it, save it once as one operation, and Undo it (decision 0091). | changing Mark done or Undo screens |
| checklist.py | Things to do: the Today, This week, This month, This year and No date yet pages, each row with its record's own action. | changing the Things to do pages or the Home card |
| moves_pages.py | One reminder per policy (decision 0117): the household's choice screen, Review and move row by row, Transfer back, and the notices on each record's page. | changing the Vehicle insurance choice or move screens |
| count.py | Count this batch: a stocktake of one batch, reviewed and then saved as one stocktake correction. | changing the stocktake screens |
| home.py | Group the home page by area: each module's main lists shown large, its other lists as one line of links. | changing how the home page is grouped or ordered |
| questions.py | The "Have you thought about…?" screens: the questions by group, one question with its four answers, and Not now. | changing the question screens |
| drills.py | The "Think it through" screens: the drills that fit, one drill's sources and steps, each step with its records, and saving a practice. | changing the drill screens |
| exit_sketch.py | Our way-out sketch: the drawing with its text version, the few facts it asks for, and the printable sheet and text. | changing the way-out sketch pages or their forms |
| exit_drawing.py | Draw the way-out sketch as SVG on the server: room boxes by floor, labelled lines, doors out and the meeting place, split into pages. | changing how the sketch is laid out, drawn or split into pages |
| sheets.py | One-page printable sheets declared by modules, such as the emergency sheet. | changing printable sheets |
| display.py | Turn declared tables and stored values into friendly labels, form fields and text. | changing how values look |
| templates/ | The HTML pages | changing what a page looks like |
| api.py | The helper API (/api/v1): programs the household gave a key to can look at records and suggest new ones. | changing what helpers can read or send |
| review.py | The Review screen: helpers' suggested new records and imported rows, waiting for a person to accept or reject each one. | changing the Review page |
| receipt_line.py | Review, a receipt line the helper could not match: choose its Stock item or make a new one, then confirm amount and date. | changing Choose item for a receipt line |
| csv_import.py | Settings, Import from a spreadsheet: choose a table, upload a CSV, match its columns, check the rows, send to Review. | changing the import screens |
| helper_guide.py | The starting message for a helper's assistant: what it may use, how to send, and its limits, from list and field names only. | changing the starting message or GET /api/v1/guide |
| helper_settings.py | Settings, Helpers: give an assistant a key, choose what it may do, give it a new key, and turn its access off. | changing the Helpers settings page |
| export_page.py | Settings, Export my records: a page and a button that downloads a zip of spreadsheet files. | changing the Export page |
| chart*.py | Charts drawn on the server as SVG, labelled bars and dated dots (charts), and the pages showing today's drinking water and one pet's recorded weights (chart_pages, decision 0109) | changing a chart or its empty words |
| daily_pages.py | Daily totals pages (decision 0110): one subject's day, a dated sheet, the Home lines, the record panel and Review's repeat note. | changing the feeding log pages, its sheet or its Home card |
| restore.py | Settings, Backups: the list of backups, a preview of one, putting it back, and Undo restore. | changing the restore pages |
| openapi-v1.json | The published OpenAPI 3.1 description of the helper API, served at GET /api/v1/openapi.json. | changing a helper route, reply or error code (edit it too) |

## src/dashboard/web/templates/  (summary: HTML pages; base.html holds the shared look)
| Entry | What it is | Open it when |
|---|---|---|
| base.html | Shared layout, colours (light and dark), header and footer | changing the overall look |
| *chart.html | Charts with their equal tables: today's drinking water by item (supply_chart), one pet's recorded weights with a pet and date picker (dot_chart) and the piece shared with the pet's page (_dot_chart) | changing a chart page's wording |
| *daily*.html | The feeding log: one pet's day with Add food (daily), the piece shared with the pet's page (_daily_panel) and the dated sheet that prints every entry or refuses (daily_sheet) | changing the feeding log's wording |
| home.html | Home page: days of cover, needs attention, tables with counts, backup and data file status | changing the home screen |
| attention.html | Running low, expiring soon, days of cover with the working shown, and gaps worth filling in | changing the attention page |
| count.html | Count this batch: the count, its review and what was saved | changing the stocktake wording |
| import.html | Import from a spreadsheet: choose a list and file, match columns, see which rows are ready, send to Review | changing the import wording |
| grid.html | A table's records, a page at a time, sortable | changing the list of records |
| rows.html | One page of grid rows (also loaded as you scroll) | changing a row |
| form.html | Add and edit forms, delete and restore, and history | changing the form |
| action_form.html | An action's small form, such as Mark done: what it asks, the next-date choice, Save once | changing the Mark done wording |
| checklist.html | Things to do: the tabs, rows with their own button, Done with Undo, and the year by month | changing the Things to do wording |
| _*.html | Pieces shared by both forms: one field (_field), and the forms' styles and browser code (_form_script) | changing every form at once |
| question*.html | "Have you thought about…?": the questions by group with what was looked at (questions), and one question with Yes, Not relevant, Not yet and Tell me more (question) | changing the question wording |
| drill*.html | "Think it through": the drills that fit (drills), one drill with its sources and earlier practice (drill), one step with its records or missing words (drill_step), a practice and Save this practice (drill_run), and the emergency-number box on each (drill_first) | changing the drill wording |
| home_setup.html | Set up my home: add rooms and storage spots, rename, move or delete them, and connect rooms; no scripts needed | changing the Set up my home wording |
| exit_*.html | Our way-out sketch: the page with drawing, text version and forms (exit_sketch), the numbered printable sheet (exit_sheet) and Print as text (exit_text); _exit_parts holds the warnings, legend, Check together and text list they share | changing the way-out sketch wording or print |
| setup.html | First-run wizard and Settings (one form, two modes) | changing setup questions |
| *sheet.html | A printable sheet styled to fit one page (sheet), and the step before one with private details (private_sheet) | changing how sheets print |
| start.html | Shown to a browser that was not opened by the shortcut | changing that message |
| report.html | Shown after saving a report | changing that message |
| close*.html | The "Save and exit" page, and the page shown after a safe close | changing how closing works |
| error.html | Plain-language error page with "Save a report" | changing error wording |
| helpers.html | Settings, Helpers: the helper list with Make a new key and Turn off access, and the form that makes a key | changing the Helpers settings page |
| helper*_key.html | The one page that shows a key: helper_key for a new helper, helper_new_key for a new key for one already made; each with Copy and a warning | changing the key pages |
| helper_connect.html | "Connect an AI assistant": settings to paste into an assistant's app (pointing at the address file), with a placeholder for the key, and Connection details | changing the assistant set-up words |
| helper_start_message.html | "Starting message for your assistant": the guide for one helper to paste into its chat, with a Copy button | changing the starting message box |
| review.html | Review: each helper's waiting suggestions with Accept and Reject | changing the Review page |
| review_line.html | Choose item for a receipt line the helper could not match: pick or make the item, confirm amount and date | changing the Choose item screens |
| review_batch.html | Open earlier receipt: what became of each row of a receipt, read only | changing the earlier receipt page |
| export.html | Settings, Export my records: what is in the export and the download button | changing the Export page |
| moves*.html | One reminder per policy (0117): Review and move with each record's ID, and the Nothing was moved page | changing the reminder move screens |
| restore_*.html | Settings, Backups: the list of backups, the check-and-compare page, the result, and the shared Undo restore box | changing the restore pages |

## tests/  (summary: automatic tests; synthetic data only)
How to run them is in AGENTS.md.
| Entry | What it is | Open it when |
|---|---|---|
| support.py | Shared helpers for tests: temporary folders and made-up (synthetic) modules. | writing a new test |
| test_db.py | Tests for opening the database safely, transactions, statement splitting and backups. | changing the database layer |
| test_migrations.py | Tests for numbered migrations: tracks, checksums, newer databases, rollback and backups. | changing migrations |
| test_csv_import.py | Tests for Import from a spreadsheet: reading a CSV, matching columns, the dry run, staging for Review and Accept. | changing spreadsheet import |
| test_modules.py | Tests for loading module folders and the plain-language problems they report. | changing module rules |
| test_actions.py | Tests for actions: one-step buttons like Mark returned, the date order rule `not_before` (decision 0075), and the checks on actions that add a record (decision 0091). | changing actions or date order |
| test_routine_checklists.py | Tests for Things to do and Routines (decision 0107): the eleven checks in Lane B's routine checklist draft, and more. | changing Things to do, Routines or repeats |
| test_readiness_ask_again.py | Tests for decision 0113: a confirmed Readiness answer comes back only when a field its question lists changed. | changing when a question or drill step asks again |
| test_example_garden.py | Exercise the garden example with a temporary database and synthetic harvest. | changing the garden example |
| test_optional_links.py | Tests for optional links between modules (decision 0115): Utilities works without Our home and keeps an exact meter link while it is off. | changing optional_requires, a link into a switched-off module, or its words |
| test_module_bills_insurance.py | Tests for Bills and insurance (decision 0117): dated bills and policies beside Utilities, private details that never travel, and one reminder per vehicle policy. | changing bills, takes_over, moving a reminder or Transfer back |
| test_records.py | Tests for saving, checking, linking, deleting and restoring records, and their history. | changing how records are saved |
| test_schema.py | Tests for turning declared tables into SQL and generating the next migration. | changing table building |
| test_startup.py | Tests for preparing the database at start-up with the modules found. | changing start-up |
| test_check_privacy.py | Tests for the privacy check. | changing privacy rules |
| test_check_indexes.py | Tests for the index check. | changing index rules |
| test_project_map.py | Tests for the project map generator. | changing the map |
| test_server.py | Tests for starting, protecting and safely closing the local web server. | changing startup or closing |
| test_watch.py | Tests for running low, expiring soon and days of cover, and for checking `watch` sections. | changing watch rules |
| test_charts.py | Tests for the first charts (decision 0109): the drinking-water breakdown, one pet's weigh-ins and the SVG drawing. | changing a chart |
| test_module_vehicle_running.py | Tests for the Vehicle running log: odometer readings and service estimates beside Vehicles (decision 0111). | changing readings, estimates, gentle checks or listed-under sections |
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
| test_exit_sketch.py | Tests for the way-out sketch (decision 0118): Lane B's exit map checks, steady layout, continuation pages and privacy. | changing the way-out sketch |
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
| test_done_history_and_move_in.py | Tests for decision 0112: one-press actions leave a named history entry with Undo, and the move-in traps from Lane B's read-through. | changing one-step actions, their Undo, or the move-in checks |
| test_grouped_suggestions.py | Tests for receipt lines on suggestions and for suggestions that point at an earlier one in the same batch (decision 0097). | changing source lines, refs or grouped Review rows |
| test_sync_extra_checks.py | Sync stage 1 extra checks from STAGE1_ACCEPTANCE.md: Utilities and Pets values, held People details, corrupt IDs and links, confinement, Set up my home rows. | changing sync checks or what may travel |
| test_review_speedups.py | Tests for faster Review (decision 0101): Accept all by group, ticked rows, keys, fixed buttons and Allow 200 more today. | changing Accept all, ticked rows, Review keys or the daily limit |
| test_receipt_review.py | Tests for receipts on Review (decision 0105): clearer group words, lines a helper could not match, and repeat receipts. | changing receipt lines, Finish receipt review or the repeat-receipt warning |

## tools/  (summary: scripts that check, lock and build the project; run by CI)
| Entry | What it is | Open it when |
|---|---|---|
| repofiles.py | Shared helper that lists the files belonging to the repository. | a tool needs the file list |
| check_all.py | Run every check a change must pass before it is pushed, with one command. | before every push |
| check_privacy.py | Fail the build if anything private or machine-specific is committed. | tuning what counts as private |
| check_indexes.py | Check that every folder has a short, complete and current INDEX.md. | changing the index rules |
| lock_requirements.py | Write requirements.lock: every pinned library with the checksums PyPI publishes. | updating a library |
| build_portable.py | Build the portable Windows folder and zip: bundled Python, libraries and launchers. | changing what ships in the folder |
| portable.toml | Pinned Python version, download address and checksum for the build | updating the bundled Python |
| smoke_test_portable.py | Start the built portable folder or Mac app, check it answers, and close it safely. | the Windows or Mac build check fails |
| build_macos.py | Build the unsigned Mac app and zip (Dashboard Plus.app) for this Mac's processor: bundled Python, libraries, launcher. | changing what ships in the Mac app |
| macos.toml | Pinned Mac Python version, downloads and checksums for the Mac build | updating the Mac app's Python |
| make_migration.py | Write a module's next numbered migration from its tables.toml. | a module's tables changed |
| load_example.py | Load a made-up example household into an empty data folder, for demos, screenshots and testing. | demonstrating or testing with realistic data |
| make_screenshots.py | Make the example screenshots: run each example household through every stage of using the dashboard. | the screens changed and the gallery needs remaking |
| screenshots.js | Browser steps for make_screenshots.py (Node and Playwright) | changing how screenshots are taken |
| browser_check.py | Click through the real dashboard in Chromium (setup, Set up my home, dates, stock in, stocktake, Mark returned, Mark done, Things to do, spreadsheet import, Review keys and buttons, readiness questions, Think it through drills, charts, the way-out sketch, pet feeding at 320px, vehicle running log, Bills and a moved car insurance reminder, Utilities with Our home off, private details, closing) and fail loudly. | a screen or its browser code changed |
| browser_check.js | Browser steps for browser_check.py (Node and Playwright): what is clicked and checked | changing what the browser check clicks |
| make_project_map.py | Build PROJECT_MAP.md from every INDEX.md in the repository. | changing the map format |
