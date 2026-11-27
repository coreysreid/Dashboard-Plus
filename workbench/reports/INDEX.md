# workbench/reports/  (summary: Lane B's findings and suggestions, one dated file per report)
Name files YYYY-MM-DD-topic.md. Each finding: what, where, how to see it,
expected, actual, severity (blocker, important, minor), suggested change.

| Entry | What it is | Open it when |
|---|---|---|
| 2026-11-09-m1-check.md | Linux household journey check, with findings and limits. | planning M1 fixes |
| 2026-11-09-module-wording.md | Exact wording and form suggestions for People and Stock. | refining the shipped modules |
| 2026-11-13-product-swot.md | Evidence-based product SWOT, priorities and expansion ideas. | deciding what to improve after M1 |
| 2026-11-16-ux-check.md | J1–J5 screen check after catalogue merge, with exact wording suggestions. | reviewing current UX |
| 2026-11-17-nested-places-ux.md | J1–J5 screen check after nested Places, including a long-list path failure. | improving Places UX |
| 2026-11-17-picking-water-ux.md | Batch 4 stock picking and drinking-water check in four temporary households. | reviewing picker and water defaults |
| 2026-11-17-accessibility.md | WCAG 2.2 review of all example screens, with live keyboard and narrow-view checks. | fixing screen access and reflow |
| 2026-11-17-medical-dates-ux.md | J1–J5 check after Medical and local dates, including a car-only kit gap. | refining Medical and date entry |
| 2026-11-18-print-check.md | 84 A4/Letter light/dark checks including Our home, Vehicles and First aid at home. | reviewing print output |
| 2026-11-18-print-matrix.csv | PDF layout and path evidence across the three fictional households. | reproducing print results |
| 2026-11-18-sensitive-detail-recheck.md | Checks decisions 0055/0059 and ranks remaining private-detail risks. | reviewing current privacy behavior |
| 2026-11-17-print-check.md | A4/Letter light/dark results for three fictional households. | checking printable sheets |
| 2026-11-17-print-matrix.csv | Sixty route and PDF combinations, including four expected unavailable routes. | reproducing print results |
| 2026-11-18-translation-readiness.md | 14-template, six-module extraction plan for other languages. | preparing localization |
| 2026-11-18-translation-inventory.csv | 1,992 visible string locations and picker search terms. | extracting messages |
| 2026-11-17-translation-readiness.md | Screen-grouped extraction plan for shipped template and module words. | preparing other languages |
| 2026-11-17-translation-inventory.csv | 1,845 literal locations, picker names and search aliases. | extracting locale messages |
| 2026-11-18-wording-consistency.md | Six-module wording pass after Home layout, Vehicles, batches and private reveal. | applying exact replacements |
| 2026-11-18-wording-inventory.csv | 472 current strings and twelve exact proposed changes. | reviewing wording locations |
| 2026-11-17-wording-consistency.md | Exact shipped-module wording replacements and term rules. | polishing module words |
| 2026-11-17-wording-inventory.csv | All 310 authored or rendered module strings with exact proposals. | applying the wording table |
| 2026-11-18-current-build-ux.md | Batch 12 three-household UX check with exact findings and 320px pass. | refining current screens |
| 2026-11-18-ux-route-matrix.csv | 39 route, status and phone-width measurements. | reproducing the phone pass |
| ux_2026_11_18/ | Seven invented-household 320px screenshots. | seeing the current UI |
| 2026-11-17-sensitive-detail-audit.md | Read-only audit of private fields in shipped screens, history and backups. | tightening privacy before M2 helpers and export |
| 2026-11-18-print-check.md | A4/Letter light/dark results including Home layout, Vehicles and Medical sheets. | checking printable sheets |
| 2026-11-18-print-matrix.csv | 84 route and PDF combinations, four expected unavailable. | reproducing print results |
| 2026-11-18-translation-readiness.md | Screen-grouped extraction plan including Home layout and Vehicles. | preparing other languages |
| 2026-11-18-translation-inventory.csv | 1,983 literal locations, picker names and search aliases. | extracting locale messages |
| 2026-11-18-wording-consistency.md | Exact replacement table across six shipped modules. | polishing household words |
| 2026-11-18-wording-inventory.csv | 472 module strings with current and proposed words. | applying wording replacements |
| 2026-11-18-sensitive-detail-recheck.md | Decision 0055 verification and remaining private-detail findings. | reviewing privacy after security fixes |
| 2026-11-19-agent-api-skeleton-ux.md | Live key, curl, suggestion and Review journey, including duplicate-grant finding. | refining the merged Agent API |
| 2026-11-19-batch14-household-ux.md | Three-household loan, batch-count and Garden check at phone and desktop widths. | refining new household flows |
| 2026-11-19-batch14-ux-matrix.csv | Ninety route, response and document-width observations. | reproducing batch 14 UX results |
| ux_2026_11_19/ | Smith phone and desktop captures of stocktake wording. | seeing the singular-unit finding |
| 2026-11-19-agent-api-abuse-recheck.md | All 22 misuse cases checked against shipped code; concurrent cap race reproduced. | hardening the Agent API |
| 2026-11-19-new-screens-wording.md | Exact replacements for Count, Review, Helpers and Mark returned. | polishing new screen words |
| 2026-11-20-mcp-connector-acceptance.md | Shipped connector run against twelve checks, worst-first partials and exact probes. | accepting the MCP connector |
| 2026-11-20-restore-export-import-ux.md | Three-household phone and desktop recovery, CSV and Review run, with exact import wording. | refining M2 data flows |
| 2026-11-20-sharing-option-a-ready-check.md | Unselected shared-folder option A blockers and two-device acceptance checks. | reconsidering sharing A after 0089 |
| 2026-11-20-not-a-vault-wording.md | Exact help and setup replacements for document, access and private fields. | applying User 1's not-a-vault wording |
| 2026-11-20-batch18-ux.md | Three-household phone and desktop checks of Mark done, copies, import and Helpers. | fixing 20 November build UX |
| 2026-11-20-helper-address-rotation-run.md | Live MCP connector through two restarts and one-step key rotation. | checking helper continuity |
| 2026-11-20-wine-final-check.md | Shipped Wine against all 15 old checks, including the Garcia example correction. | reviewing Wine promotion |
| 2026-11-21-receipt-group-review.md | Live connector receipt rerun with source lines and dependent new-item Review decisions. | refining grouped receipt Review |
| 2026-11-21-mac-preview-readthrough.md | Exact household wording changes and physical-Mac checks for the unsigned preview. | improving Mac preview guidance |
| 2026-11-21-routine-checklists-ux.md | Three-household, four-tab phone and desktop walk of Things to do, including done and Undo. | fixing the year-view overflow |
| 2026-11-21-drills-ux.md | Three complete 320px drills, exact missing words, local numbers and private-answer checks. | accepting the shipped Think it through screens |
| 2026-11-27-read-me-check.md | Windows and Mac read-me, README and Getting started sentences against today's app, with replacements. | updating the read-me files |
