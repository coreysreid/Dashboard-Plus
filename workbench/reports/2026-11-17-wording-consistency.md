# Wording pass: shipped People, Stock, Pets and Medical

Checked 17 November 2026 against each shipped module's `module.toml`, `tables.toml`, `labels.toml` and `sheets.toml`, plus the renderer's fallback field and choice labels. [The exact inventory](2026-11-17-wording-inventory.csv) has 310 visible strings with module, file and TOML path: table and module titles/descriptions, field labels, help, empty text, answers, choices, Needs attention questions and sheet/section titles. Its `current` and `proposed` cells form the replacement table. It is a read-only proposal; shipped files are untouched.

## Terms to keep consistent

| Idea | Use | Why |
|---|---|---|
| A food or supply deadline | **Use by** | Current Stock labels use this for both an item and a batch; avoid “expiry” on household screens. |
| An amount in one batch | **Amount in this batch** | Distinguish a batch count from item **Amount on hand** and an in/out amount. |
| A movement | **Amount to add or use** | A movement can add or subtract and is not current stock. |
| Where a record sits | **Where it is**; for a kit, **where this kit is kept** in help | Distinguish physical place from whether a kit is **Usually kept** at home, in a vehicle or elsewhere. |
| A reminder deadline | **Check again by**, **Give again by**, **Vaccinations due by** | State the action and that this is a deadline, not a completed date. |
| A completed event | **Checked on**, **Date given**, **Completed on** | These are history dates, not deadlines. |

## Nine exact changes

| Module and field | Current → proposed | Finding |
|---|---|---|
| Stock, items `expires` help | “For several use-by dates, add the item with one, then add a batch for each of the others.” → “For several use-by dates, add one batch for each date.” | The new lots design gives each batch its own date. |
| Stock, lots `quantity` label | “How many” → “Amount in this batch” | Clarifies scope. |
| Stock, movements `amount` label | “How many” → “Amount to add or use” | Clarifies direction and scope. |
| Stock, supplies sheet water title | “Water (litres)” → “Drinking and other water (litres)” | Sheet query includes **all** water batches, including water not safe to drink. Do not call the entire section drinking water. |
| Pets, pets `vaccinations_due` label | “Vaccinations due” → “Vaccinations due by” | Deadline form. |
| Pets, treatments `next_due` label | “Next due” → “Give again by” | Names action and deadline. |
| Medical, kits `place` help | “Choose a place recorded in Household stock. Keep first aid supplies in Stock too.” → “Choose the place where this kit is kept. Keep first aid supplies in Stock too.” | The place's eventual owner is Home layout; help should describe the task. |
| Medical, kit checks `next_check` label | “Next check planned” → “Check again by” | Same deadline words as the current kit, but history remains a separate record. |
| Medical, kit checks `next_check` help | “For this check record only. Also update the kit's current Check again by date.” → “The date planned at this check. Also update the kit's current Check again by date.” | Explains historic versus live date. |

The other 301 strings have identical current/proposed values in the CSV. They either already match these terms or name distinct concepts. The inventory includes generated fallback labels; for example, the code derives a label from a column key if no explicit label exists. It does not audit general core templates or future module drafts; item 39 inventories translation strings separately.

**Important sheet behavior:** A label alone cannot let the reader tell safe drinking water from other water in the printed section. If Lane A wants separate totals or an emergency drinking-water sheet, the sheet query needs a filter on the linked item's `drinking` value and a visible “safe to drink” indication. Do not sum all water litres as drinking water. The proposed title is the accurate minimal fix for the current query. Source: shipped `modules/stock/sheets.toml`, `modules/stock/tables.toml` and `modules/stock/labels.toml`, checked 17 November 2026.
