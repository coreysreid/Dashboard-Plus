# Bring a spreadsheet into Dashboard Plus

Drafted 17 November 2026 for M2. The first supported path should import **Stock items and their Places** from a CSV made by a spreadsheet or another app; the same mapping/review pattern can later serve People, Pets and other module tables. The app currently has no CSV import screen. All example records are invented.

## 1. Choose a file

From Stock choose **Import a spreadsheet**. The page says: “Choose a CSV file. We will show what would change before saving anything.” Offer a downloadable sample headed `name,category,amount_on_hand,unit,keep_at_least,place,use_by,safe_to_drink,notes` and explain that `name` is required; other columns can be mapped. Accept common UTF-8 CSV with or without BOM, quoted commas/newlines and CRLF or LF. If another encoding is detected, show a preview and ask the person to choose it; never silently replace characters. Limit file size/rows and say the limit before upload. Do not send the file away.

## 2. Match columns

Show the first five lines and a mapping control for each source header. Offer guesses for `Item`, `Product`, `Description` → Name; `Qty`, `On hand`, `Quantity` → Amount on hand; `Min`, `Target` → Keep at least; `Location`, `Stored in` → Place; `Expiry`, `Best before` → Use by. Preserve an explicit **Ignore this column** choice. Do not infer `Safe to drink=yes` from `category=water` or an empty cell. Show the import action choice separately: **Set current amounts from this spreadsheet** or **Add these amounts as Stock in**. Default to no action until the person chooses, because the same number has different meaning in those cases.

| Destination field | Input rule in this first Stock template |
|---|---|
| Name | Required text; suggest an existing household item first, then a catalogue key/alias, then “Create a new Stock item”. Never rename an existing item automatically. |
| Category | Optional key or displayed label; map only to a shipped Stock category; show unknown values for correction. |
| Amount on hand | Nonnegative decimal in the item Unit. Blank means “not supplied”, not zero. |
| Unit | Text such as tins, kg, litres or packs. Existing item unit mismatch needs explicit conversion or a new item, not arithmetic on unlike units. |
| Keep at least | Optional nonnegative decimal in the same unit; changing an existing threshold requires an explicit choice. |
| Place | Household path such as `Kitchen › Pantry › Shelf 3`, or an unambiguous existing place ID from a Dashboard export. Match any path part for suggestions, then confirm the **full path**. Unknown path can be created only after review; duplicate leaf names under different rooms are never guessed. |
| Use by | Optional actual package date. Interpret with the household's selected AU/UK/NZ or US display convention and show ISO in the dry run. An ambiguous `1/2/27` must be called out. Do not derive dates from catalogue shelf-life hints. |
| Safe to drink | Only relevant to Water. Accept explicit yes/no variants; blank means “needs answer” for a new drinking-water item and never silently counts as safe. |
| Notes | Optional text. Preserve punctuation and line breaks. Warn before merging with an existing person's note. |

If the file resembles an export from another app, display original headers next to target fields. Do not assume its ID numbers are Dashboard IDs. For future generic import, use each module's schema for validation and preserve source labels/keys in the dry run; do not build a separate hard-coded validator per module.

## 3. Dry run: see every proposed change

After mapping, show a summary: “20 rows read. 12 new items, 5 existing items, 2 rows need a choice, 1 row cannot be imported. Nothing has been saved.” Provide filters **All**, **New**, **Existing**, **Needs a choice**, **Errors**, **Skipped**. Each row shows source line number and raw values, proposed item and category, source amount and unit, chosen import action, proposed final amount, full place path, date in both the household display form and ISO, and warnings. Use `EXAMPLE.csv` as a made-up fixture: `TOM TINNED 400G` proposes Tinned tomatoes; `Garage › Top shelf` and `Kitchen › Pantry › Top shelf` must stay distinct. “Flushing water” with blank Safe to drink must be answered before it can count towards drinking-water days.

Exact row actions: **Choose an existing item**, **Use catalogue item**, **Create new item**, **Change place**, **Edit value**, **Skip row**. A duplicate row in the file is flagged; do not add it twice by default. If an existing Stock item has been edited since preview, regenerate the affected preview before save. Require all errors resolved or skipped, then show “Ready to import 18 rows. 2 rows skipped. No records have changed yet.” The final button says **Import 18 rows**.

## 4. Save and review

Save one audited batch. For “Add as Stock in”, create bought/add movements and never set the item quantity directly as well. For “Set current amounts”, show the difference from the current quantity and record an explicit stocktake correction with provenance; do not present it as a purchase. New items and reviewed Places are created in the same atomic batch, with links checked before commit. If any row fails, none of the batch is saved. After success show rows imported, created, linked, skipped and rejected, plus **Review imported items** and **Undo this import**. A repeated file warns “This file looks like one you imported on [date]. Check before importing again.” An undo must not overwrite later person edits.

## References

- [Shipped Stock table and movements](../../../modules/stock/tables.toml), [Stock labels](../../../modules/stock/labels.toml), and [nested Places acceptance draft](../home_layout/ACCEPTANCE.md), checked 17 November 2026. The field behavior above follows the product contract.
- [RFC 4180: CSV format](https://www.rfc-editor.org/rfc/rfc4180), checked 17 November 2026, for quoted fields and line conventions. CSV files in the wild vary; the dry run must show what was actually parsed.
