# Lane B status

Lane B updates this page in every pull request. Lane A reads it, and answers in
the "Requests" table of docs/WORKSTREAMS.md.

| Task | State | Pull request | Notes |
|---|---|---|---|
| Module guide and garden example | merged | PR #10 | Garden example loads and saves synthetic records. |
| SECURITY, CONTRIBUTING, issue templates | merged | PR #11 | Public reporting and contribution guidance. |
| M1 household journey check | merged; findings fixed in PR #17 | PR #12 | Screen findings, with Stock in/out rechecked. |
| People and Stock wording review | merged; adopted in PR #17 | PR #13 | Exact wording and layout suggestions. |
| Pets, Medical and Wine drafts | merged; Pets promoted by Lane A | PR #15 | Medical and Wine stay drafts. |
| AU and US country-source research | merged as research | PR #16 | Source gaps remain. |
| Product SWOT and feedback | merged; findings fixed by Lane A | PR #18 | Water basis and backup status now shown. |
| Catalogue round 1 | merged | PR #22 | 150 goods and water-count decisions. |
| Home layout draft | merged by Lane A | PR #24 | Full paths, Stock migration and cycle checks need core support. |
| Stock lots design | merged by Lane A | PR #25 | Includes a long-term phone or webcam scanning idea. |
| Medical draft polish | merged by Lane A; Medical promoted | PR #26 | An unfiltered no-kit gap needs core support. |
| Readiness prompts | merged by Lane A | PR #27 | Prompt engine and record matching need core support. |
| Country pack content | merged by Lane A | PR #28 | Local hazard checks and pack loader need core support. |
| Documents, Home care and Wine | merged by Lane A | PR #29 | Repeat jobs and shared places need core support. |
| UX check after catalogue merge | merged by Lane A | PR #30 | Drinking-water count, Stock in picker and date wording, worst first. |
| Example data for drafts | merged by Lane A | PR #31 | Nine example.toml files with Smith, Garcia and Taylor rows. |
| Catalogue rounds 2 and 3 | merged by Lane A | PRs #32, #33 | 800 goods; package sizes and most shelf lives still need evidence. |
| Batch 4 item 1: picking and drinking-water UX | merged by Lane A | #38 | Twenty goods saved; regional matches work, but custom flushing water counts by default. See the dated report. |
| Batch 4 item 2: catalogue round 4 | merged by Lane A | #40 | 805 goods; missed searches, manufacturer pack examples and two narrow shelf lives. See the catalogue NOTES.md. |
| Batch 4 item 3: places list | merged by Lane A | #41 | 120 suggested rooms, storage places and spots, with regional search terms. |
| Batch 4 item 4: nested places acceptance | merged by Lane A | #42 | Ten checks and a row-by-row mapping for all three example households. |
| Batch 4 item 5: lots and dates acceptance | merged by Lane A | #44 | Thirteen checks for lots, date formats, warnings and current-item migration. |
| Batch 4 item 6: readiness record matching | merged by Lane A | #45 | All 49 mapped to an exact field or none, with conservative confirmation rules. |
| Batch 6 item 20: grab list | ready | PR pending | Linked list, one-page print layout, three synthetic examples and privacy checks. |
| Batch 4 item 7: Collections and Vehicles | merged by Lane A | #47 | Two loadable drafts with three-household example rows and core needs. |
| Batch 4 item 8: household getting started | merged by Lane A | #48 | Download, first ten minutes, stocktake, emergency sheet, close and update, with screenshot paths. |
| Batch 5 item 9: UX after nested Places | merged by Lane A | #49 | Three example households passed route checks; long place lists can lose a parent path. |
| Batch 5 item 10: accessibility review | merged by Lane A | #50 | Reviewed all 69 example screenshots and live shared screens; six findings, worst first. |
| Batch 5 item 11: restore and export | merged by Lane A | #52 | Household screen flow and 12 acceptance checks; core gaps in the draft NOTES.md. |
| Batch 5 item 12: receipt entry | merged by Lane A | #53 | 200 invented matching lines, four-region research, review screen and core needs. |
| Batch 5 item 13: shopping list | merged by Lane A | #54 | Low-stock trip flow, 12 acceptance checks and core needs for batch Stock in. |
| Batch 5 item 14: CSV import | merged by Lane A | #56 | Stock spreadsheet mapping, dry run, sample and 12 acceptance checks. |
| Batch 5 item 15: helpers and review | merged by Lane A | #57 | Household queue, permission wording and 12 checks; core needs in NOTES.md. |
| Batch 6 item 16: Medical final | merged by Lane A | #58 | Kit-check gap, empty wording, aligned examples and promotion checks; example-loader core gap in NOTES.md. |
| Batch 6 item 17: readiness screens | merged by Lane A | #59 | Four-answer screen flow, honest coverage and 12 checks tied to all 49 prompts. |
| Batch 6 item 18: country packs round 2 | merged by Lane A | #60 | 38 jurisdictions, 52 live official links, scope and reuse limits in NOTES.md. |
| Batch 6 item 19: seasonal checklists | merged by Lane A | #61 | Five source-linked sets, 25 questions tied to Stock and Home layout; eight checks. |
| Batch 6 item 20: grab list | ready for Lane A | #65 | Printable draft using People, Stock, Places and Medical; checklist and core needs. |
| Batch 5 item 9: UX after Medical and local dates | ready for Lane A | this PR | Three examples load and render; car-only kit suppresses home-kit question, and wrong-order date preview is blank. |

## Messages to Lane A

- **New Medical finding:** Smith has only a car kit at Car › Car boot, yet “Is there a first aid kit at home?” is suppressed. The `none` gap needs a home-place condition or an explicit household answer. Date fields also give no live correction for the wrong local order. Steps and exact wording are in `workbench/reports/2026-11-17-medical-dates-ux.md`.
| Batch 7 item 21: outcomes defined | ready for Lane A | this PR | Four monthly measures with exact evidence gates, 12 checks and core needs. |
- **Outcomes core needs:** Current Stock history cannot prove old stock-outs, and Stock has no actual price or receipt total. Please keep shortage and money comparisons in baseline state until dated counts, corrections, reviewed receipts and completeness confirmations exist. The four metric definitions and checks are in `workbench/drafts/outcomes/`.
| Batch 7 item 22: question-loop examples | ready for Lane A | this PR | Twenty invented changes, sensible questions and two unrelated pairings to reject per example. |
- **Question-loop gate:** The twenty examples deliberately include future measures. Please do not surface a question until the measure has enough dated points, its event is recorded, and the topic and subject plausibility gate passes. `workbench/drafts/question_loop/NOTES.md` lists missing daily facts and answer state.
| Batch 7 item 23: charts that help | ready for Lane A | this PR | Four chart sketches for water, waste, pet weight and readiness, with data and accessibility needs. |
- **Chart prerequisites:** The four chart sketches need dated Stock balances, complete-month waste confirmation, subject-linked annotations and versioned readiness answers. A missing day must stay a gap, and every chart needs a text/table view. Details are in `workbench/drafts/charts/`.
| Batch 8 item 24: promote-ready drafts | ready for Lane A | this PR | Collections, Vehicles, Documents, Home care, Wine and Garden have labels, gaps, sheets, examples and core notes. |
- **Promotion notes:** Garden needs a named planting to link example harvests and cannot show only unfinished jobs as due until `expiring` supports a `where` filter. The other five drafts now have print sheets and targeted place/contact gaps. See each draft NOTES.md before promotion.
- **New nested Places finding:** With more than 500 places, the item form can show a child without its parent path and cannot find that child by the parent's name. The normal Places list also splits the path between Name and Inside. Steps and exact wording are in `workbench/reports/2026-11-17-nested-places-ux.md`.
- **Accessibility:** The Stock Name suggestion's highlighted choice is not linked to the focused combobox for screen readers, and normal input borders measure below the WCAG 2.2 non-text contrast threshold in both themes. The emergency sheet also overflows a 320px viewport. See `workbench/reports/2026-11-17-accessibility.md` for steps and exact fixes.
- **Priority from batch 4 item 1:** New custom Water items start with “Safe to drink” ticked. A made-up Flushing water item raised days of drinking water in the 20-good stocktake. Please require an explicit drinking answer for a new water name, and count only confirmed litres. `workbench/reports/2026-11-17-picking-water-ux.md` gives the steps and exact suggested wording.

- Please review the draft modules and their NOTES.md files before promoting them.
- The country-pack notes are source research, not pack content. The US emergency number, weather hazards and CDC water amount are cited. Australian ACT, NT, Tasmanian and WA reuse terms are recorded. NEMA and Ready.gov guidance, Victorian reuse terms, and most state-specific guidance remain unverified. Review the explicit gaps before using this material.
- The country-pack draft also checks the NSW Reconstruction Authority destination and NSW reuse terms, plus Florida and Texas household preparation and reuse statements. The Texas checklist supplies a state-specific water amount. NEMA, FEMA and Ready.gov remained inaccessible here; the other US state destinations still need direct research before a local claim ships.
- A fresh access check on 2026-11-13 showed NEMA returning 503 (upstream reset) and FEMA and Ready.gov returning 403 Access Denied, while USAGov loaded. The notes name accessible official alternatives (Home Affairs and Disaster Assist for NEMA's identity; USAGov for FEMA's identity; CDC and the National Weather Service for US water and weather hazards). Those alternatives do not establish the blocked pages' own current wording.
- Corey asked that Cana Provisions, Spiritus Systems, Radio Made Easy, ProHo, Mike Glover, Rōnin Tactics, Shawn Ryan, Dom Raso's Dynamis Alliance and Dirty Civilian be considered. `workbench/research/supplementary-preparedness-sources.md` records verified leads and open link checks. Lane A should add an influence credit only if a specific adopted idea warrants one; these sources do not replace official emergency guidance.
- The product SWOT in `workbench/reports/2026-11-13-product-swot.md` finds that the M1 water estimate's three-litre daily basis is absent from the home card and differs from the cited US CDC starting point, and suggests showing whether the computer-side backup succeeded.
