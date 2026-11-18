# Wording pass: shipped People, Stock, Pets, Medical, Home layout and Vehicles

Checked 18 November 2026 against each shipped module's `module.toml`, `tables.toml`, `labels.toml` and `sheets.toml`, plus the renderer's fallback field and choice labels. [The exact inventory](2026-11-18-wording-inventory.csv) has 472 visible strings with module, file and TOML path: table and module titles/descriptions, field labels, help, empty text, answers, choices, Needs attention questions and sheet/section titles. Its `current` and `proposed` cells form the replacement table. It is a read-only proposal; shipped files are untouched.

## Terms to keep consistent

| Idea | Use | Why |
|---|---|---|
| A food or supply deadline | **Use by** | Current Stock labels use this for both an item and a batch; avoid “expiry” on household screens. |
| An amount in one batch | **Amount in this batch** | Distinguish a batch count from item **Amount on hand** and an in/out amount. |
| A movement | **Amount to add or use** | A movement can add or subtract and is not current stock. |
| Where a record sits | **Where it is**; for a kit, **where this kit is kept** in help | Distinguish physical place from whether a kit is **Usually kept** at home, in a vehicle or elsewhere. |
| A reminder deadline | **Check again by**, **Give again by**, **Vaccinations due by** | State the action and that this is a deadline, not a completed date. |
| A completed event | **Checked on**, **Date given**, **Completed on** | These are history dates, not deadlines. |

## Twelve exact changes

| Module and field | Current → proposed | Finding |
|---|---|---|
| Stock, items `expires` help | “For several use-by dates, add the item with one, then add a batch for each of the others.” → “For several use-by dates, add one batch for each date.” | The new lots design gives each batch its own date. |
| Stock, lots `quantity` label | “How many” → “Amount in this batch” | Clarifies scope. |
| Stock, movements `amount` label | “How many” → “Amount to add or use” | Clarifies direction and scope. |
| Pets, pets `vaccinations_due` label | “Vaccinations due” → “Vaccinations due by” | Deadline form. |
| Pets, treatments `next_due` label | “Next due” → “Give again by” | Names action and deadline. |
| Medical, kits `place` help | “Choose a place recorded in Household stock. Keep first aid supplies in Stock too.” → “Choose the place where this kit is kept. Keep first aid supplies in Stock too.” | Stock Places is the shared place list after Home layout promotion; help should describe the task. |
| Medical, kit checks `next_check` label | “Next check planned” → “Check again by” | Same deadline words as the current kit, but history remains a separate record. |
| Medical, kit checks `next_check` help | “For this check record only. Also update the kit's current Check again by date.” → “The date planned at this check. Also update the kit's current Check again by date.” | Explains historic versus live date. |
| Home layout, exits `route` help | “In your own words, including the way from upstairs if you have one. Keep it current if the layout changes.” → “In your own words, including the way from upstairs if you have one. Do not put access or alarm codes here; this route can be printed.” | Our home prints routes. |
| Home layout, shut-offs `how_to_find` help | “A landmark helps someone who has never looked for it, such as: behind the grey shelves.” → “A landmark helps someone who has never looked for it, such as: behind the grey shelves. Do not put access or alarm codes here; this hint can be printed.” | Our home prints this hint. |
| Vehicles, registration help | “Private: hidden on lists and never printed. Leave blank if you would rather keep it with the vehicle's papers.” → “Private: hidden until you choose Show, and never printed. Leave blank if you would rather keep it with the vehicle's papers.” | Decision 0059 now hides the edit value until Show. |
| Vehicles, services `next_due` label | “Next due” → “Service or check by” | Names the action and deadline. |

The other 460 strings have identical current/proposed values in the CSV. They either already match these terms or name distinct concepts. The inventory includes generated fallback labels; for example, the code derives a label from a column key if no explicit label exists. It does not audit general core templates or future module drafts; item 39 inventories translation strings separately. New Home layout and Vehicles words are included, and the Home layout privacy hints follow the item 31 recheck.

**Water sheet recheck:** Decision 0059 and the later supplies-sheet fix now filter the water section to linked items marked safe to drink. The earlier water-title recommendation is withdrawn. Source: shipped `modules/stock/sheets.toml`, checked 18 November 2026.
