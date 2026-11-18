# Current-build UX check: grouped Home, batches, Home layout and Vehicles

Checked **18 November 2026** against main `e188229` in three separate temporary Smith, Garcia and Taylor households. I opened 13 routes per household in Chromium at **320px**, used the Stock batch picker and private-sheet Show link, and compared the shipped [example screens](../../docs/EXAMPLES.md). The [39-route matrix](2026-11-18-ux-route-matrix.csv) records HTTP status, document width, viewport and title. [Fresh phone screenshots](ux_2026_11_18/INDEX.md) show each Home page, Stock in, the batch picker, Vehicles and the private-sheet warning. All names and records were invented; no shipped files changed.

## Findings, worst first

### 1. Important — a private-sheet link skips its warning

**Where/how:** Open **Emergency sheet with private medical details** from Home. The first screen says, “This sheet includes private health and care details. Show it only when you mean to print or share it.” Its button goes to `?show=1`. Entering that URL directly in the same local session renders the private sheet without visiting the warning. Lists and record forms now keep saved private values out of initial HTML; those decision 0059 fixes held in the [focused recheck](2026-11-18-sensitive-detail-recheck.md).

**Expected:** A direct link should show the warning until this session explicitly asks to reveal the sheet. **Suggested change:** Replace the query switch with a short-lived server-side reveal granted by the warning action. Keep the exact warning above and **Back to Home**. Test an unconfirmed direct link as well as the normal button. This is the same security finding reported in item 31, included here because it is a visible Show journey.

### 2. Important — Our home can print a code typed as a location hint

**Where/how:** The Home layout **How to find it** field for a shut-off accepts ordinary text. A made-up `DEMO-CODE-123` in that field appeared on **Our home** when printed, although the grouped Home card did not display it. The meter version of the field already warns against codes; the shut-off and exit-route help do not. [Item 31](2026-11-18-sensitive-detail-recheck.md) has the synthetic reproduction.

**Expected:** A person entering a location hint should know it can be printed. **Exact suggested help:** “Describe where to go. Do not put access or alarm codes here; this can be printed.” Apply that to shut-off **How to find it** and exit **How to get there**. If codes are later supported, give them a separate private field and an explicit print choice.

### 3. Minor — a one-item batch says “1 tubes”

**Where/how:** In Taylor, open **Stock in and out**, choose **Bike inner tube**, then open **Which batch**. The option says **“Bike inner tube, 1 tubes at Outside › Bike shed”**. The [320px capture](ux_2026_11_18/taylor-batch-picker-320.png) shows it. The unit stored for this item is `tubes`; the picker appends it without singular handling.

**Expected:** One should read “1 tube” or, if the unit is household-authored and cannot be inflected safely, “Bike inner tube — amount 1 (tubes) — Outside › Bike shed”. The latter keeps the unit as entered. Do not rewrite a household's stored unit to solve display grammar.

## What worked

- **Grouped Home:** Smith, Garcia and Taylor show the enabled modules by area. The new Home layout and Vehicles cards have usable links and counts. All three [phone Home captures](ux_2026_11_18/INDEX.md) fit a 320px viewport.
- **Batches and places:** Stock items, Places, Batches and Stock in and out opened in every household. On the live form, choosing an item exposed only that item's batches; **Bought or added** offered **Start a new batch**, while **Used** offered **Use the batch with the earliest use-by date**. Changing the item cleared the chosen batch. The full nested path appeared in the option. The stocktake screen fix from #96 is present, so the old missing-correction-flow report is historical.
- **Home layout and Vehicles:** Ways out, Shut-offs and power board, Our home, Vehicles and its sheet returned 200 in all three households. The printed sheets retained the full places tested in the [print check](2026-11-18-print-check.md). The Vehicle sheet omitted the private plate in the synthetic security check.
- **Private Show:** Important details lists showed 4, 6 and 1 **Show** buttons for Smith, Garcia and Taylor. The private-sheet interstitial appeared for each; choosing **Show private sheet** rendered the sheet. The separate item 31 check verified list and record reveal requests and ordinary-sheet omission.
- **Phone width:** All 39 route responses were 200, and `document.documentElement.scrollWidth` equalled the 320px viewport on every route. This does not prove keyboard, screen-reader or physical-device behavior.

**Scope:** The screenshots and route matrix are Chromium checks on invented local data. No real medical, vehicle or household details were used. Sources for current behavior: shipped templates and six module contracts, decisions 0053–0059, and the three example households, checked 18 November 2026. This is product-screen evidence, not emergency guidance.
