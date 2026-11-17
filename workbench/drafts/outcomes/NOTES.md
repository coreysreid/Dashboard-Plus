# Core work needed for outcomes

Checked **2026-11-17** against shipped modules and `docs/DESIGN.md` section 10.4.

- **Completeness:** Add per-measure tracking start, complete-through date and household confirmation/retraction. Without that, absence of rows cannot mean zero. The monthly screen should let people mark a period incomplete, with a plain explanation.
- **Stock history:** Preserve movement-time unit and item label, inventory corrections, and an opening balance/date. Today's `stock.items.quantity` plus movements may not reconstruct earlier stock levels if the first count is unknown or later edits occur. Persist an explicit essential-item set and episode boundaries before claiming shortages.
- **Money:** Reviewed receipts or purchase lines need actual paid total, currency, tax/discount handling, refund links, stable import IDs and coverage. Stock has no money fields; do not estimate cost from catalogue sizes or a stock count. Receipt entry draft is in `workbench/drafts/receipt_entry/`.
- **Readiness:** Implement versioned prompt IDs, applicability, household answers and month-end snapshots from `workbench/drafts/readiness/`. Record matches merely offer an answer for confirmation. Keep source and answer dates distinct.
- **Wins:** Implement `core__outcomes` with proposed/confirmed/dismissed states, linked evidence, household wording, review flags when evidence changes, and user supplied comparison cost for a money saving. Store the person's decision; never auto-confirm.
- **Period engine:** Use household local calendar boundaries; track late-entry revisions and comparability. Allow evidence drill-down and a plain export. Set a small default number of cards and avoid a single aggregate “score.”

The draft needs no additional outside facts or licences. Its one reference is the internal product design checked on the date above.
