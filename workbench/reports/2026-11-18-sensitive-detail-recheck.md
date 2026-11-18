# Sensitive-detail recheck after decision 0055

Read-only check on **18 November 2026** against main `95c8754`. I used the invented Smith household in a temporary data folder, the current People, Stock, Medical, Home layout and Vehicles modules, and the shipped route/test code. This follows up the earlier item 31 audit: it checks decision 0055's fixes and retests its open findings against the new screens. No real household data or shipped files were changed. The synthetic strings were **“Peanut allergy…”**, plate **`DEMO-AU-001`** and an added **`DEMO-CODE-123`** location note.

## Findings, worst first

### 1. Important — a closed private People cell still sends its value

**Steps:** Open `/t/people__important_info` or its `/rows` continuation without choosing **Show**. Both 200 responses contained the synthetic allergy text inside a closed `<details class="secret">`. The visual control hides it on screen, but saved HTML and any reader of the response already have it. This was the first finding before decision 0055 and is unchanged; that decision protects names, questions and units, not list response bodies.

**Suggested fix:** Send only **“Private detail — choose Show to view”** in initial and paged HTML. Fetch one field after a deliberate **Show private detail** action. Test the raw response as well as the visible page. Do not sort on a hidden private value if order alone reveals information.

### 2. Important — private sheets and edit forms reveal immediately

**Steps:** The ordinary `/sheet/people/emergency` omitted the allergy; `/sheet/people/emergency_medical` returned it immediately. The grouped Home page links the private sheet in People’s print links. Opening `/t/people__important_info/1` returned the saved value in the edit field. Vehicles similarly keeps its plate off the list, sheet and Home, but `/t/vehicles__vehicles/1` displays the plate without an additional reveal action. These are intentional local editing and printing routes, yet a mistaken click or screen share reveals private details before the existing warning can help.

**Suggested fix:** Show **“This sheet includes private health and care details. Show it only when you mean to print or share it.”** before rendering the private sheet; buttons **Show private sheet** and **Back to Home**. For private edit fields, start with **“Private detail saved. Show to read or change it.”** and preserve the value when other fields are saved without revealing it. Apply the same pattern to Vehicle registration. The normal emergency sheet remains the shareable default.

### 3. Important — Home layout can print a secret entered as a location hint

**Steps:** I added a fictional shut-off whose `how_to_find` was **`DEMO-CODE-123 for test only`**. It did not appear on grouped Home, but it appeared in `/sheet/home_layout/our_home` because that field is included in the printable section. `how_to_find` is not marked sensitive. Ways-out `route` is also printable. The sheet is meant to describe locations, but a household could enter a gate, alarm or lock code there and then share the sheet.

**Suggested fix:** Help beside `route` and `how_to_find` should say **“Describe where to go. Do not put access or alarm codes here; this sheet can be printed.”** If codes become a supported record, give them a separately marked private field with an explicit print choice. Keep full place paths on the sheet.

### 4. Important — deleting a private record does not erase its audit or backups

The synthetic allergy text was again present in `core__audit` after loading Smith, and the local database file was mode `0600`. Soft deletion and backup copies remain part of the recovery design. Decision 0055 tightened file permissions and backup-folder naming; it did not add permanent erasure. Before delete, say **“Remove from the dashboard? This can be restored, and older copies may remain in backups.”** Future exports must state whether private fields and audit history are included. This is a retention disclosure, not a claim that the backup mechanism failed.

## Decision 0055 checks that held

| Surface | Evidence on 18 November | Result |
|---|---|
| Module migration boundary | `tests/test_module_confinement.py` rejects nine invented SQL attempts: reading/writing other tables, triggers, views, ATTACH, PRAGMA, VACUUM and partial COMMIT. Own-table data migration succeeds; refused modules leave household data unchanged. | Held in the focused test run. |
| Private record names | Batch `record_name` cannot refer to a sensitive linked field; the module loader rejects it in `tests/test_stock_batches.py`. | Held. |
| Private gap questions | Loader rejects a `{notes}` placeholder when notes is marked sensitive (`tests/test_gaps.py`). Grouped Home displays gap messages from this checked declaration. | Held. The earlier latent gap-placeholder finding is closed. |
| Private supply unit | `modules.py` rejects a sensitive `unit_from` column. Stock uses a non-sensitive unit; no private value appeared in days-of-water output. | Code path checked; add a dedicated regression test when this rule changes. |
| Vehicles | Plate `registration` is declared sensitive. The invented plate was absent from Vehicle list, Vehicle sheet, Needs attention, grouped Home and `registration` name suggestions (404). It appeared on the opened edit form. | List/search/sheet boundary held; finding 2 remains for immediate edit reveal. |
| Home layout | Our home omitted the example's ordinary `notes` values in the shipped module test; the new probe found a `how_to_find` value on the sheet, as declared. | No unexpected notes leak; finding 3 is a field-guidance gap. |
| Batches and grouped Home | Batch list and paged rows, Home and Needs attention contained neither the synthetic allergy nor the plate. Batch names use item, amount, unit, place and use-by date; no private field is declared in that template. | No new private-column leak observed. A household may still put private meaning in an ordinary item or place name. |
| Basic web protection | Focused robustness tests cover no-cache/no-frame headers, method refusal and private suggestion refusal. | Held in tests. |

The focused module, gap, batch, Home layout and Vehicles suite ran **61 tests, all passing**. Local GET probes returned 200 on the tested pages and 404 for private `detail` and `registration` suggestions. A future helper API and CSV export still do not ship, so field-level exclusion and explicit grants must be tested before either is released. Decision 0055 itself names a separate unresolved session-cookie scope issue across local ports; this recheck did not claim it was fixed.

**Sources:** [decision 0055](../../docs/decisions/0055-modules-confined-and-security-review-fixes.md), the shipped modules, `src/dashboard/core/modules.py`, `src/dashboard/web/{pages,home,sheets}.py`, `src/dashboard/web/templates/{home,rows,form,sheet}.html`, and the named tests, all checked 18 November 2026. This was a local synthetic audit, not an external penetration test.
