# Core work needed for a shopping trip

Checked 17 November 2026. The current core has Stock items, movements, running-low watch and a single Stock-in form. It has no persistent shopping-list/trip record or grouped batch save. The household flow in FLOW.md needs:

1. A trip and trip-line model with the source Stock item ID, a snapshot of its quantity, unit and minimum at list creation, suggested and edited buy amounts, aisle, picked-up state, actual brought-home amount and final movement/lot IDs. Keep a stable distinction between plan and purchase.
2. A calculation service using decimal arithmetic and the item's own unit. Do not convert packages to kg or litres without a confirmed pack size. An item whose minimum or unit changes after list creation must be flagged for review; do not overwrite a person's edited plan.
3. A household-editable aisle mapping that does not alter Stock category. Aisles vary by shop, so no universal aisle claim is made here. A print-friendly view and keyboard-labelled checkboxes use the same trip state.
4. An atomic batch write through the existing Stock movement adjustment service. Save each accepted actual amount once, link all movements to a trip/batch, show new totals, and support an audited undo with conflict detection. Idempotency must survive refresh or restart. Lot allocation and per-lot dates need the future Stock-lots service, not a shopping-list workaround.
5. A safe way to make a manual one-off row without changing an existing item's Keep at least. A new Stock item should use the normal picker and validation before final Stock in.

The list should not be used as an emergency-supply recommendation. It reflects only the household's chosen thresholds. The [Stock labels](../../../modules/stock/labels.toml) and [J2](../../../docs/JOURNEYS.md) are the product sources, checked 17 November 2026.
