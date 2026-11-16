# Product SWOT and next steps — 2026-11-13

This is a review of the current `main` product, [`docs/CORE.md`](../../docs/CORE.md), [`docs/ROADMAP.md`](../../docs/ROADMAP.md), [`docs/JOURNEYS.md`](../../docs/JOURNEYS.md), and Lane A's open M1 release-check pull request #17. I also used Lane B's earlier household and wording reports in pull requests #12 and #13. I did **not** run a new household session or a clean Windows test for this review. The suggestions below are for Lane A to judge; this report changes no program files. All example quantities are invented.

## SWOT

| | What the evidence says | Product implication |
|---|---|---|
| **Strengths** | People and Stock already provide the first useful loop: record supplies, see low and expiring items, see a water estimate, and print contact and supply sheets. The [M1 journey check](../../docs/JOURNEYS.md) in PR #12 exercised these flows. PR #17 reports fixes for the two first-screen findings and checks print pagination with made-up households. | A household can get a useful answer before the later analysis features exist. Keep the first ten minutes simple. |
| **Weaknesses** | Water cover uses a fixed **3 litres per person per day** and **1 litre per pet per day** in [`modules/stock/tables.toml`](../../modules/stock/tables.toml). The home screen shows days and a shortfall but not that daily basis; the full attention page shows the arithmetic. The separate second backup can fail with only a log warning in [`backups.py`](../../src/dashboard/core/backups.py). | The two most reassuring M1 claims, water cover and backup, need their assumptions and failures visible at the point of use. |
| **Opportunities** | The file-only Garden example and three Lane B module drafts let households and helpers add focused topics without expanding the core. The [roadmap](../../docs/ROADMAP.md) already plans restore, export, prompts and country notes. | Promote modules only after real household use shows which fields matter; give upcoming work an observable outcome, such as a successful restore from the second copy. |
| **Threats** | Local safety advice varies by place. The [CDC water guidance](https://www.cdc.gov/water-emergency/about/how-to-create-and-store-an-emergency-water-supply.html), checked for Lane B country research on 2026-11-09, says at least **one US gallon per person per day**, more than the M1 default of three litres. Direct NEMA, FEMA and Ready.gov pages remained inaccessible in this research environment on 2026-11-13. The [M1 release list](../../docs/ROADMAP.md) still needs clean Windows, human timing and physical USB checks. | A universal readiness number or an unreviewed local pack could create false confidence. Publishing before the hands-on checks could hide failures that automated tests cannot see. |

## Feedback to act on, in order

### Important — show the daily water assumption beside the result

- **Did:** Compared the Stock supply rule, the home and attention templates, and the cited CDC guidance for the United States.
- **Expected:** A household reading “about N days of water” can see the daily amount used and tell whether it fits its local guidance and people or pets.
- **Actual:** The home page shows days, a three-day aim and litres short, while the fixed three-litre-per-person basis is on the full attention page. For a made-up three-person household with nine litres, the current rule reports **one day**. Using the CDC's one-gallon amount (about 3.8 litres) gives **less than one day** before any additional needs. The current page says local advice comes first, but that does not reveal the numerical mismatch on the home screen.
- **Suggested change:** On the home card, add **“Estimate based on 3 litres per person per day and 1 litre per pet per day. Check your local authority's advice.”** Place a link beside it to the detailed calculation. Before M3 country packs ship, decide whether the household can set a daily amount or the app should use a cited local starting point. Do not silently change an existing household's basis.
- **Acceptance check:** With three people and nine litres entered, the home page shows the basis and the calculation still agrees with the attention page. A person can identify the source and date of a future country-specific amount.

### Important — show whether the second backup actually succeeded

- **Did:** Read [`backups.py`](../../src/dashboard/core/backups.py) and the M1 backup promise in the roadmap.
- **Expected:** A household that thinks it has a computer-side copy can tell if that copy was written, especially before relying on a USB stick.
- **Actual:** A failure writing the second location is logged and the first copy remains; [`latest()`](../../src/dashboard/core/backups.py) reports only the data-folder backup. The app does not expose the second-copy failure through this path. This is a code-path finding, not a reproduced disk failure.
- **Suggested change:** Show separate status for **“Copy in your data folder”** and **“Second copy on this computer”** in Settings, including the last successful date and a plain warning if the second copy fails. In M2, make a restore drill from the computer-side copy part of release checks.
- **Acceptance check:** Simulate an unwritable second location. The app keeps running, but Settings clearly reports that the second copy failed and identifies the copy that did succeed.

### Important — finish the three hands-on M1 checks before calling it released

- **Did:** Compared the [M1 release list](../../docs/ROADMAP.md) with PR #17's stated status.
- **Expected:** The first-use claim is demonstrated on a clean Windows computer, with a person entering 20 items and a real USB move.
- **Actual:** PR #17 says four of seven release checks pass fully; first start, human entry timing and physical USB handling still require hands-on checks. Its fixes to Lane B's earlier findings are in review, not yet on `main` at the time of this report.
- **Suggested change:** Give a tester the exact J1 to J5 script, a blank data folder and a timer. Record the result, the Windows version and whether a backup on the computer survives removing the USB stick. Make this a release gate, not a claim inferred from server response time.
- **Acceptance check:** The [M1 release checklist](../../docs/ROADMAP.md) records each hands-on result and any failure is fixed or explicitly keeps M1 in test status.

## Expansion ideas after M1

1. **M2: restore rehearsal.** Let a household see and restore a *copy* into a new empty folder before risking its current records. A completed rehearsal proves that the backup can actually be used. This follows the roadmap's restore goal.
2. **M3: local guidance provenance.** Each country-pack card should show its official source, checked date and review-by date, with a direct link. Where a state source has not been reviewed, show a question to check with the local authority instead of a number. This follows decision 0025 and the gaps recorded in Lane B's country research PR #16.
3. **M3: low-effort readiness prompts.** Start with prompts that a household can answer from existing People and Stock records, such as whether a contact has a phone number or whether stored water has a known place. Count a prompt as “looked at,” never “safe,” as the vision requires.

The first two findings are the clearest additions for Lane A to consider now. The M1 release gate remains the priority over expanding the feature list.
