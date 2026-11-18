# Documents promotion acceptance checks

Checked against shipped module contracts and the three fictional example households, **18 November 2026**. Use a temporary data folder; enable Stock and Documents together. Never use real document identifiers or private papers.

1. **Load and dependency:** A module loader accepts the draft tables, labels, sheet and regenerated 0001 migration with Stock enabled. Without Stock, Documents remains off with a clear dependency message; it does not create an orphaned place link.
2. **Places:** Add a document at `stock.places` **Kitchen › Pantry › Shelf 3**. Its form and list show the full path. Find it by a middle path segment. Moving the place changes the displayed path without changing the document's link ID.
3. **Restrict deletion:** Refuse deletion of a linked place while a nondeleted Document points to it. After moving or deleting the Document, allow the place operation under the normal soft-delete and restore rules; restoring the Document restores its same place link.
4. **Private values:** Save an invented holder and note. Initial list, edit HTML, Home, Needs attention, suggestion responses, ordinary sheet and review queue omit their saved values. Only an explicit Show on the record reveals the requested field. Do not use `holder` or `notes` in a `record_name`, gap question, unit or print column.
5. **Ordinary title warning:** The name is visible in lists, questions and the sheet. Its help says to use a generic title and never a document number. Verify that a private holder's name in `holder` does not flow into the displayed record name.
6. **Sheet:** **Document review dates** prints only name, kind and `renew_by`. It omits place, holder and notes; a household must verify that even a generic name is suitable to share before printing.
7. **Missing place:** A saved document without a place asks **“Where is {name} kept? Add a broad location without a document number.”** It never asks the household whether it owns a passport or will. Filling a place clears the gap.
8. **Due date:** A date the household types shows with **due** in Needs attention within 30 days. A blank date does not invent a deadline; an overdue date stays due until edited or removed. Dates follow the household's AU/UK/NZ `20/05/27` or US `05/20/27` display and wrong-order validation.
9. **Smith:** Both invented Smith documents link to **Front hall**, which exists in `examples/households/smith.toml`; the insurance reminder uses `today+90`, and Family passports has no inferred date.
10. **Garcia:** Apartment insurance links **Hall closet** and Care papers **Main bedroom**, both existing Garcia places. The latter's private holder and note do not appear on the sheet.
11. **Taylor:** Tenancy agreement and Bicycle warranty link **Hall cupboard**, an existing Taylor place. Only the warranty has the invented `today+120` reminder.
12. **Delete and restore:** Soft-deleting a document removes it from current lists, due questions and the sheet; restoring it brings back the same link and household-entered date. Audit and backups still retain old private values, so Restore is not permanent erasure.

These are promotion checks for Lane A; there is no shipped Documents module yet. Sources: `modules/stock/tables.toml`, shipped renderer and privacy guards, decisions 0054/0055/0059, and the three example TOMLs, checked 18 November 2026.
