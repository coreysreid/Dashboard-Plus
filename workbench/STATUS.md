# Lane B status

Lane B updates this page in every pull request. Lane A reads it, and answers in
the "Requests" table of docs/WORKSTREAMS.md.

| Task | State | Pull request | Notes |
|---|---|---|---|
| Module guide and garden example | merged | PR #10 | Garden example loads and saves synthetic records. |
| SECURITY, CONTRIBUTING, issue templates | ready for a pull request: `lane-b/project-files` | pending | A household can report security issues privately and contributors have clear rules and issue forms. |
| Product SWOT and feedback | in review | PR #18 | Water and backup visibility, M1 release gates, and later expansion ideas. |
| Module guide and garden example | ready for review on `lane-b/module-guide` | pending | Garden example loads and saves synthetic records; checks passed. |
| SECURITY, CONTRIBUTING, issue templates | on branch `lane-b/project-files` | none yet | |
| M1 household journey check | ready for a pull request: `lane-b/m1-check` | pending | First-screen and expiry-summary findings; Stock in/out now works. |

## Messages to Lane A

- Stock in/out now updates the count and the running-low view. Please check the remaining M1 findings in `workbench/reports/2026-11-09-m1-check.md`.
| SECURITY, CONTRIBUTING, issue templates | in review | PR #11 | Public reporting and contribution guidance. |
| People and Stock wording review | ready for a pull request: `lane-b/module-wording` | pending | Four exact wording and layout suggestions. |
- Please review the exact wording suggestions in `workbench/reports/2026-11-09-module-wording.md` before changing People or Stock.
| Pets, Medical and Wine drafts | ready for a pull request: `lane-b/draft-modules` | pending | Three files-only drafts load; open questions in each NOTES.md. |
- Please review the draft modules and their NOTES.md files before promoting them.
| M1 household journey check | in review | PR #12 | Screen findings, with Stock in/out rechecked. |
| People and Stock wording review | in review | PR #13 | Exact wording and layout suggestions. |
| Pets, Medical and Wine drafts | in review | PR #15 | Three files-only drafts. |
| AU and US country-source research | draft for review | Draft PR #16 | Verified official links and licences where available; source gaps remain. |
- The country-pack notes are source research, not pack content. The US emergency number, weather hazards and CDC water amount are now cited. Australian ACT, NT, Tasmanian and WA reuse terms are now recorded. NEMA and Ready.gov guidance, NSW and Victorian reuse terms, and state-specific guidance remain unverified. Review the explicit gaps before using this material.
- Corey asked that Cana Provisions, Spiritus Systems, Radio Made Easy, ProHo, Mike Glover, Rōnin Tactics, Shawn Ryan, Dom Raso's Dynamis Alliance and Dirty Civilian be considered. `workbench/research/supplementary-preparedness-sources.md` records verified leads and open link checks. Lane A should add an influence credit only if a specific adopted idea warrants one; these sources do not replace official emergency guidance.
- The country-pack draft now also checks the NSW Reconstruction Authority destination and NSW reuse terms, plus Florida and Texas household preparation and reuse statements. The Texas checklist supplies a state-specific water amount. NEMA, FEMA and Ready.gov remain inaccessible here; the other US state destinations still need direct research before a local claim ships.
- A fresh access check on 2026-11-13 showed NEMA returning 503 (upstream reset) and FEMA and Ready.gov returning 403 Access Denied, while USAGov loaded. The notes name accessible official alternatives—Home Affairs and Disaster Assist for NEMA's identity; USAGov for FEMA's identity; CDC and the National Weather Service for US water and weather hazards. Those alternatives do not establish the blocked pages' own current wording.
- The product SWOT in `workbench/reports/2026-11-13-product-swot.md` finds that the M1 water estimate's three-litre daily basis is absent from the home card and differs from the cited US CDC starting point. It also suggests showing whether the computer-side backup succeeded. PR #17 appears to resolve the two findings in Lane B's earlier M1 report; finish its three hands-on Windows/USB checks before release.

(none yet)
