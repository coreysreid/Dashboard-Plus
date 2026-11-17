# Sensitive-detail audit: shipped screens and storage

Read-only check on **2026-11-17** against `main` at `4f181da` (after the Medical and date fixes). Loaded the invented Smith example into a temporary folder and fetched local pages with the normal session cookie. The probe used the fake People detail beginning **“Peanut allergy. Adrenaline auto-injector…”**; no real household data was opened. Read the shipped templates, record and backup services, People/Pets/Medical declarations and current screenshots. This is a code and route audit, not a third-party penetration test or a browser extension test. The examples' synthetic details are public demo data; the findings concern what would happen to a real household's entries.

## Findings, worst first

### 1. Important — a closed private list cell still sends the full detail (J4, private People details)

**Where and steps:** Open **Important details** (`/t/people__important_info`) without choosing **Show**. The `detail` column is marked `sensitive = true`, but `src/dashboard/web/pages.py` formats it into `cell.text`, and `src/dashboard/web/templates/rows.html` puts that text inside a closed `<details class="secret">`. The page response and `/t/people__important_info/rows` response both contained the complete synthetic allergy sentence before any reveal. The list's **Show** only changes what is visible on screen. A saved page, copied HTML, browser tool or future helper reading the response would already receive it.

**Expected:** “Hidden in lists until you choose to show it” should mean the list response contains no private value until that deliberate action, if the product intends this as a privacy boundary.

**Suggested change and exact words:** Render only **“Private detail — choose Show to view”** in the grid and paged rows. After an explicit **“Show private detail”** action, fetch only that record's field with the local session and a short-lived reveal state; never preload all private cells in the list HTML. Keep a clear warning that a person with access to the unencrypted data folder can still read the database. Verify the initial HTML, paged HTML, saved page and print preview contain no detail text before reveal. Also avoid sorting by a hidden private field if the sorted order could disclose it.

### 2. Important — opening a private record displays its value in the edit form without a reveal step (J4)

**Where and steps:** Open `/t/people__important_info/1`. `pages.edit_record` sends the saved record to `display.build_fields`, and `form.html` fills the `detail` input with its value. The raw response and visible form contained the full fake allergy detail. The help line says **“Private: hidden in lists until you choose to show it”**, but the opened record immediately shows it. This is useful for editing, yet easy to expose while screen sharing or looking up which person has a detail.

**Expected:** The person should be able to open the record and choose when to display the private value. The interface should explain that opening/editing it reveals it locally.

**Suggested change and exact words:** Start the detail field collapsed with **“Private detail saved. Show to read or change it.”** A deliberate **“Show private detail”** action can reveal the existing value in the edit input. Make clear that saving other fields does not clear an unrevealed detail. Keep the explicit medical print sheet available for a household that chooses to share it.

### 3. Important — the full private medical sheet is one ordinary Home link away (J3, J4)

**Where and steps:** Home includes **“Print: Emergency sheet with private medical details”** alongside ordinary sheets. Opening `/sheet/people/emergency_medical` immediately returns and displays the full sensitive `important_info.detail`; `sheet.html` warns **“This sheet includes private details”** on the same rendered page. The ordinary `/sheet/people/emergency` correctly omitted the detail. A household may want the private sheet, but a mistaken click or print preview reveals every saved health/access detail at once.

**Expected:** A distinct, intentional reveal before the private values are rendered or printed. The normal fridge copy must remain free of them.

**Suggested change and exact words:** On the first click show a short interstitial: **“This sheet includes private health and care details. Show it only when you mean to print or share it.”** Buttons: **“Show private sheet”** and **“Back to Home”**. Do not render the sensitive table in the interstitial HTML. Keep the existing warning and a printed date on the revealed sheet. Test the Home link, direct URL and browser print preview. This is a local privacy control, not a claim of protection from someone who has the data folder.

### 4. Important — deleted private values remain in current storage, audit history and backup copies (J4)

**Where and steps:** `records._audit` writes unredacted `before` and `after` JSON to `core__audit` on create and update. The invented allergy sentence appeared in its create audit row. Deleting a record marks `deleted_at`; the row and audit survive for restore. A daily backup copied both the sensitive table value and audit JSON into `data/backups` and, when enabled, the second computer-side backup. The example's data and backup files were mode `0600` inside mode `0700` folders on this Linux check; README and setup disclose that the data folder is unencrypted. This is recoverable storage by design, but “deleted” is not “erased from every copy.”

**Expected:** The household understands retention before it deletes or shares a data folder, report bundle or future export. Any erase action must cover audit and backups or state its limits.

**Suggested change and exact words:** On a private record's delete action say **“Remove from the dashboard? This can be restored, and older copies may remain in backups.”** Document a separate, carefully designed **“Permanently erase private detail”** flow only when the core can handle audit, backups and a way back consistently. For future export, default to excluding private details and audit values unless a person explicitly includes them. Do not silently rewrite existing household backup history.

### 5. Minor — future gap wording could put a sensitive field on Home (latent rule path)

**Where and steps:** `watch._message` substitutes any named field from a gap rule through `_show`, without checking `column.sensitive`. No shipped People gap currently names `{detail}`, so the fake allergy text did **not** appear on Home or Needs attention in this check. A future module rule such as `message = "Review {detail}"` would place that value in a gap, including the Home summary and Needs attention. This is a core rule guard to add before more private drafts are promoted.

**Suggested change and exact words:** Reject a gap message placeholder for a sensitive column at module load, or substitute **“private detail”** rather than its value. A private gap should ask **“Is this detail still current? Open the private record to review it.”**, with no quoted content on Home, Needs attention, sheets or notifications.

## Surface-by-surface result

| Surface | What shipped code does now | Audit result / next gate |
|---|---|---|
| Ordinary emergency sheet | Lists People and calls, no `important_info.detail` | Confirmed absent in local response. Keep as the shareable default. |
| Private medical sheet | Includes all saved `detail` values and a private warning | Confirmed present; finding 3. |
| Important details grid and Show more | Wraps the value in closed `<details>` but includes it in HTML | Confirmed present before reveal; finding 1. |
| Opened record and validation retry | Fills the text input/textarea with the saved or submitted value | Confirmed on opened record; finding 2. A failed save returns the typed value by design, so do not put it in a URL or log. |
| Name suggestions and link find boxes | `pages.suggest_names` refuses a `sensitive` text column with 404; `display.name_column` excludes sensitive text | Confirmed `?column=detail` returned 404. Preserve this when adding new search. |
| History on the edit page | Formats sensitive before/after in memory but template prints only `(private)` | No sensitive update values observed in the rendered history; raw audit still retains them. Avoid sending them to the template at all when not needed. |
| Needs attention and Home | Current watches choose a non-sensitive name and current gaps do not interpolate `detail` | No current People detail leak observed; latent gap path is finding 5. |
| Database and backups | Store current private values and old audit values in readable SQLite copies | Confirmed, with restrictive Linux file permissions; finding 4 covers retention and disclosure. |
| Saved problem reports | Copy the last 200 log lines or a startup traceback; routine log code does not log form values | No current detail-value path found in normal logs. Before promising **“It does not contain what you have recorded”** for every failure, add a synthetic fault test for exception messages and private paths. |
| Future CSV export and helper API | No household CSV export or helper record routes ship yet; DESIGN section 9 describes future sensitive permission | No present leak to test. Require field-level exclusion by default, explicit sensitive permission, reviewed proposals and tests for lists, searches, linked fields and audit export before release. |
| Other private-by-meaning fields | People phones/addresses, Pets microchips, Medical notes and Stock names can be personal even when not marked `sensitive` | Review field classification during module promotion; do not assume a non-sensitive flag means a sheet or helper response is safe to share. |

**Source and scope:** All observations come from local shipped code and made-up example routes checked 2026-11-17. Relevant contracts are `docs/DESIGN.md` sections 9 and 12, the People module's private field and two sheet declarations, and the local `README.md` data-folder disclosure. No external privacy or medical claim is made. The read-only audit made no changes outside `workbench/`.
