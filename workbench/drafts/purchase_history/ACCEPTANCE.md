# Purchase and price checks

Written **21 November 2026** using invented receipts and currency only.

1. Save Stock in of 2 tins with no price; Stock and batch rise once, and the history says price not recorded. A price is optional.
2. Confirm `3.80` as total for 2 tins and separately as price per tin in two fixtures. Persist the chosen basis and show distinct resulting line totals; never guess from the raw source string.
3. Send an invented decision 0097 receipt with a new item ref and 3 bought lines. Confirm 2 prices, leave 1 unknown. Accept all: 3 movements and 2 price lines commit together, with the unknown count visible. Reject a dependent item: its movement and price line do not save.
4. Choose and later skip an unmatched line. No price is persisted until a person links and accepts a movement; the receipt total can remain a separately confirmed fact.
5. Record a receipt total including non-Stock goods and a discount. Show the difference from confirmed line totals as incomplete; never spread it across item prices silently or add receipt total to line totals.
6. Submit the same receipt with a new key and via CSV import. The possible-repeat warning from the receipt design still requires a decision; a different shop or price alone is not proof of a different purchase.
7. Fail the Stock movement validation during Accept. No purchase or price record commits. Retry an accepted request key: the same permanent movement and line IDs return, with no duplicate cost.
8. Correct a confirmed price without changing the movement quantity; keep revision and audit. Undo the movement: exclude its price from current cost totals while retaining historical evidence. A Stock out without a linked refund never subtracts money.
9. Ask the cost question over a selected item set and range with one unpriced line. Show the known paid total, counts and incomplete coverage, never a complete spending total. Different currencies are separate, with no automatic conversion.
10. Put invented shop and price sentinels in purchase facts. General list/export, helper read, notification, Needs attention and stage 1 portable log expose neither. Local backup retains them. Member copies show a Stock movement with price unavailable and mark cost coverage incomplete.
11. At 700 purchase lines across 12 months, history and cost drill-down paginate with a stable order; an export or print never silently truncates the selected range.
