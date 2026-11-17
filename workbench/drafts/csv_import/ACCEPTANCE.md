# CSV import acceptance checks

Use `EXAMPLE.csv` and a synthetic household. No imported sample may contain real personal data. The app must show the dry run before a write.

1. **Choose and parse.** Upload UTF-8 with BOM and without, CRLF/LF, quoted commas and a quoted multiline note. The preview shows every field and exact source line; malformed rows are reported by line number. Unsupported encoding never silently changes characters.
2. **Map headers.** Map `Qty` to Amount on hand and `Location` to Place; ignore a foreign-app column. Reopen mapping and change one guess. Nothing is saved during mapping.
3. **No guessed operation.** Enter `4` for an existing item. The UI makes the person choose **Set current amounts** or **Add as Stock in**. Under the first, on-hand 2 becomes 4 by a +2 correction; under the second it becomes 6 by a +4 bought/add movement. It never becomes 8 by doing both.
4. **Catalogue and household first.** A household-owned `Kidney beans` item is offered before the catalogue entry; `TOM TINNED 400G` proposes the stable Tinned tomatoes key. Unknown goods remain a create-or-skip choice, not an automatic new item.
5. **Full place path.** Match `Kitchen › Pantry › Top shelf` and `Garage › Top shelf` to two different place IDs. A source value `Top shelf` alone raises an ambiguity and shows both full paths. A new place path is created only after its parent is explicitly reviewed.
6. **Water answer.** `Flushing water` has a blank Safe to drink cell. The dry run says “Safe to drink needs an answer” and does not project its 12 litres into drinking-water days. An explicit No stays No after import.
7. **Dates.** Show `20/05/27` as 2027-05-20 for AU/UK/NZ. Show the US equivalent `05/20/27` for US. Flag `1/2/27` and a two-digit year for confirmation; a bad date is an error, not today's date. Preserve the approved ISO date.
8. **Duplicates and units.** Two identical input rows are flagged. A Stock item measured in kg is not silently given 2 packs; require a confirmed conversion or another item. Blank amount and zero amount are distinct.
9. **Dry-run counts.** Summary counts and row filters agree with every row's state. The preview lists proposed changes to existing amounts, thresholds, notes, category and place separately. All errors must be corrected or skipped before final import.
10. **Atomic save.** Simulate failure on the last row. No item, movement, place or correction from that batch persists. On success, all imported writes share a source/batch ID and the result matches the preview.
11. **Repeat and undo.** Import the same file twice; the second run warns before saving and does not automatically double-add. Undo reverses only this import's changes, with a conflict review when someone edited an affected record afterward.
12. **Limits and privacy.** An over-limit file gets a plain limit message before import. The file stays local, is not logged with private cell values, and an upload containing an email at `example.com` is treated as data, never as a command or destination.
