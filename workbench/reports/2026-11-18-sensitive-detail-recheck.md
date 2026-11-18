# Sensitive-detail recheck after decisions 0055 and 0059

Read-only check on **18 November 2026** against main `e188229`. I loaded the invented Smith household into a temporary folder and checked People, Stock batches, Medical, Home layout, Vehicles and grouped Home. Synthetic values were **“Peanut allergy…”**, plate **`DEMO-AU-001`** and an added **`DEMO-CODE-123`** location hint. No real records or shipped files were changed. This follows [the earlier audit](2026-11-17-sensitive-detail-audit.md) and checks the subsequent fixes rather than repeating its original assumptions.

## Remaining findings, worst first

### 1. Important — the private-sheet interstitial can be skipped by URL

**Steps:** Open `/sheet/people/emergency_medical`; its interstitial contains no allergy text and asks the person to choose **Show private sheet**. Open `/sheet/people/emergency_medical?show=1` directly with the same local browser session; the full invented allergy text is returned immediately. A bookmarked or shared local link with `show=1` bypasses the intended first-click warning. The normal emergency sheet still omits the detail.

**Suggested fix:** Treat the warning as a server-side decision, not a query-parameter shortcut. A CSRF-protected **Show private sheet** action could grant one short-lived reveal for that sheet in the current session; a direct GET, including one with `?show=1`, should show the interstitial until that action. Keep **Back to Home** and the warning on the revealed printout. Test raw HTML from both URLs before and after confirmation.

### 2. Important — Home layout prints a code entered as a location hint

**Steps:** Add a made-up shut-off with `how_to_find = "DEMO-CODE-123 for test only"`. The grouped Home response omits it, but `/sheet/home_layout/our_home` prints it because the field is deliberately a sheet column. `how_to_find` is not marked private. The meter hint already tells a household not to enter access codes; the shut-off hint and ways-out `route` do not.

**Suggested fix:** Beside shut-off `how_to_find` and exit `route`, say **“Describe where to go. Do not put access or alarm codes here; this can be printed.”** If codes become a supported record, give them a separate private field and an explicit print choice. Keep full place paths visible on Our home.

### 3. Retention disclosure — private values remain in audit and backups

The synthetic allergy text remained in `core__audit` after load; the SQLite file was mode `0600` here. Decisions 0055 and 0059 intentionally retain private values in current records, history and backups for recovery. Removing a record from the dashboard is not permanent erasure. The proposed separate erase design is batch 12 item 45. Until then, delete wording should say **“Remove from the dashboard? This can be restored, and older copies may remain in backups.”** Future export/helper work must name its private-field and audit inclusion policy.

## What held in this recheck

| Surface | Evidence |
|---|---|
| Decision 0055 migration boundary | `tests/test_module_confinement.py` rejects nine invented attempts to touch core or other-module tables, install a trigger/view, attach a file or change database settings; the focused module/gap/batch/Home/Vehicles run passed 61 tests. |
| Private names, questions and units | Loader guards in `modules.py` reject sensitive `record_name` and gap placeholders and a sensitive supply `unit_from`. The batch name and grouped Home page returned neither synthetic private value. |
| People list and paged rows | `/t/people__important_info` and `/rows` returned 200 without the allergy text. A single-field `/reveal?column=detail` returned it only to the active local session. The old preload finding is fixed by decision 0059. |
| Edit forms and Vehicles | Opening the Important detail or Vehicle record returned neither saved allergy nor plate in initial HTML. The private reveal endpoint returned only the requested field. The old immediate-edit finding is fixed. |
| Sheets | Ordinary emergency, Our home, First aid at home and Vehicles sheets omitted the invented allergy and plate. The private emergency interstitial omitted the allergy; the revealed sheet included it. Finding 1 concerns direct bypass of that interstitial. |
| Suggestions and Home | Requests to suggest People `detail` or Vehicle `registration` returned 404. Home and Needs attention contained neither invented private value; grouped module headings and links did not add a leak. |
| Batches | The Stock batch list and paged rows contained neither invented private value. A batch name still includes ordinary item and place names; a household should not put a secret in those visible names. |

**Scope:** These are local synthetic route and code checks, not an external penetration test. The Agent API and CSV export still do not ship. Decision 0055 notes an unresolved session-cookie scope issue across local ports; it is outside this specific value-display probe. Sources: [decisions 0055](../../docs/decisions/0055-modules-confined-and-security-review-fixes.md) and [0059](../../docs/decisions/0059-private-details-only-when-asked.md), shipped module schemas, `src/dashboard/web/{pages,sheets,home}.py`, templates and focused tests, checked 18 November 2026.
