# Lane B status

Lane B updates this page in every pull request. Lane A reads it, and answers in
the "Requests" table of docs/WORKSTREAMS.md.

| Task | State | Pull request | Notes |
|---|---|---|---|
| Module guide and garden example | merged | PR #10 | Garden example loads and saves synthetic records. |
| SECURITY, CONTRIBUTING, issue templates | merged | PR #11 | Public reporting and contribution guidance. |
| M1 household journey check | merged; findings fixed in PR #17 | PR #12 | Screen findings, with Stock in/out rechecked. |
| People and Stock wording review | merged; adopted in PR #17 | PR #13 | Exact wording and layout suggestions. |
| Pets, Medical and Wine drafts | merged as drafts; Lane A to review | PR #15 | Three files-only drafts; open questions in each NOTES.md. |
| AU and US country-source research | merged as research | PR #16 | Verified official links and licences where available; source gaps remain. |
| Product SWOT and feedback | merged; water and backup findings being fixed by Lane A | PR #18 | Water and backup visibility, M1 release gates, later expansion ideas. |

| Catalogue round 1 | merged | PR #22 | 150 goods and water-count decisions; type-ahead, local additions and accurate water totals need core support. |
| Home layout draft | ready for a pull request: `lane-b/home-layout-draft` | PR #24 | Nested places and an Our home sheet; full paths, Stock migration and cycle checks need core support. |

| Stock lots design | ready for a pull request: `lane-b/stock-lots-design` | — | Screen-by-screen lot flows and exact core needs; includes a long-term phone or webcam scanning idea. |
| Medical draft polish | ready for a pull request: `lane-b/medical-promotion` | — | First step, due watches, kit place gap and a printable sheet; an unfiltered no-kit gap needs core support. |
| Readiness prompts | ready for a pull request: `lane-b/readiness-prompts` | — | 49 source-linked questions; prompt engine and exact record matching need core support. |

| Country pack content | ready for a pull request: `lane-b/country-packs-content` | — | Four dated, sourced packs; local hazard checks and pack loader need core support. |

| Documents, Home care and Wine | ready for a pull request: `lane-b/household-modules` | — | Two new draft modules and a Wine wording/sheet polish; repeat jobs and shared places need core support. |

| UX check after catalogue merge | ready for a pull request: `lane-b/ux-check-2026-11-16` | — | J1–J5 in three temporary examples; drinking-water count, Stock in picker and date wording, worst first. |

| Example data for drafts | draft PR #31; awaiting draft merges | PR #31 | Nine `example.toml` files with Smith, Garcia and Taylor rows. The examples need to be reviewed alongside the draft modules before promotion. |
| Catalogue round 2 | ready for a pull request: `lane-b/catalogue-round-2` | — | 400 goods total after adding 250 terms. Example-household gaps and regional aliases covered; package sizes and most shelf lives await evidence. |
| Catalogue round 3 | draft PR #33, pending round 2 | PR #33 | 800 goods total after adding 400; search must remain selective. Package sizes and most shelf lives still need item-specific evidence. |

## Messages to Lane A

- Please review the draft modules and their NOTES.md files before promoting them.
- The country-pack notes are source research, not pack content. The US emergency number, weather hazards and CDC water amount are cited. Australian ACT, NT, Tasmanian and WA reuse terms are recorded. NEMA and Ready.gov guidance, Victorian reuse terms, and most state-specific guidance remain unverified. Review the explicit gaps before using this material.
- The country-pack draft also checks the NSW Reconstruction Authority destination and NSW reuse terms, plus Florida and Texas household preparation and reuse statements. The Texas checklist supplies a state-specific water amount. NEMA, FEMA and Ready.gov remained inaccessible here; the other US state destinations still need direct research before a local claim ships.
- A fresh access check on 2026-11-13 showed NEMA returning 503 (upstream reset) and FEMA and Ready.gov returning 403 Access Denied, while USAGov loaded. The notes name accessible official alternatives (Home Affairs and Disaster Assist for NEMA's identity; USAGov for FEMA's identity; CDC and the National Weather Service for US water and weather hazards). Those alternatives do not establish the blocked pages' own current wording.
- Corey asked that Cana Provisions, Spiritus Systems, Radio Made Easy, ProHo, Mike Glover, Rōnin Tactics, Shawn Ryan, Dom Raso's Dynamis Alliance and Dirty Civilian be considered. `workbench/research/supplementary-preparedness-sources.md` records verified leads and open link checks. Lane A should add an influence credit only if a specific adopted idea warrants one; these sources do not replace official emergency guidance.
- The product SWOT in `workbench/reports/2026-11-13-product-swot.md` finds that the M1 water estimate's three-litre daily basis is absent from the home card and differs from the cited US CDC starting point, and suggests showing whether the computer-side backup succeeded.
