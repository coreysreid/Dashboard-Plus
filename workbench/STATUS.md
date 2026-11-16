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
| Medical draft polish | merged by Lane A | PR #26 | An unfiltered no-kit gap needs core support. |
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
| Batch 4 item 7: Collections and Vehicles | ready for a pull request: `lane-b/batch4-collections-vehicles` | pending | Two loadable drafts with three-household example rows and core needs. |
| Batch 4 item 8: household getting started | ready for a pull request: `lane-b/batch4-getting-started` | pending | Download, first ten minutes, stocktake, emergency sheet, close and update, with screenshot paths. |

## Messages to Lane A

- **Priority from batch 4 item 1:** New custom Water items start with “Safe to drink” ticked. A made-up Flushing water item raised days of drinking water in the 20-good stocktake. Please require an explicit drinking answer for a new water name, and count only confirmed litres. `workbench/reports/2026-11-17-picking-water-ux.md` gives the steps and exact suggested wording.
- Please review the draft modules and their NOTES.md files before promoting them.
- The country-pack notes are source research, not pack content. The US emergency number, weather hazards and CDC water amount are cited. Australian ACT, NT, Tasmanian and WA reuse terms are recorded. NEMA and Ready.gov guidance, Victorian reuse terms, and most state-specific guidance remain unverified. Review the explicit gaps before using this material.
- The country-pack draft also checks the NSW Reconstruction Authority destination and NSW reuse terms, plus Florida and Texas household preparation and reuse statements. The Texas checklist supplies a state-specific water amount. NEMA, FEMA and Ready.gov remained inaccessible here; the other US state destinations still need direct research before a local claim ships.
- A fresh access check on 2026-11-13 showed NEMA returning 503 (upstream reset) and FEMA and Ready.gov returning 403 Access Denied, while USAGov loaded. The notes name accessible official alternatives (Home Affairs and Disaster Assist for NEMA's identity; USAGov for FEMA's identity; CDC and the National Weather Service for US water and weather hazards). Those alternatives do not establish the blocked pages' own current wording.
- Corey asked that Cana Provisions, Spiritus Systems, Radio Made Easy, ProHo, Mike Glover, Rōnin Tactics, Shawn Ryan, Dom Raso's Dynamis Alliance and Dirty Civilian be considered. `workbench/research/supplementary-preparedness-sources.md` records verified leads and open link checks. Lane A should add an influence credit only if a specific adopted idea warrants one; these sources do not replace official emergency guidance.
- The product SWOT in `workbench/reports/2026-11-13-product-swot.md` finds that the M1 water estimate's three-litre daily basis is absent from the home card and differs from the cited US CDC starting point, and suggests showing whether the computer-side backup succeeded.
