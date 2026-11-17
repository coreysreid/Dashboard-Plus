# Evidence and core needs for receipt entry

Checked 17 November 2026. Retailer pages describe **features to allow for**, not a universal receipt grammar. The example lines in FLOW.md and `match_table.csv` are entirely invented and carry no retailer text, prices or customer information. The 200 candidates are selected for plausible household shopping coverage from the catalogue, not verified by a national frequency dataset. Lane A should test actual receipts with the owner's consent and avoid treating this vocabulary as a guarantee.

## Regional evidence

| Region | Source checked | What it supports; what it does not establish |
|---|---|---|
| AU | [Woolworths Everyday Rewards app](https://www.woolworths.com.au/shop/everyday/app) and [value explanation](https://www.woolworths.com.au/shop/articles/value), 17 Nov 2026 | Digital or paper receipts and multibuy promotions exist. Exact till abbreviations and line order are not specified. |
| US | [Kroger pickup and delivery terms](https://www.kroger.com/i/terms/pickup-and-delivery), 17 Nov 2026 | Receipts may show weight, coupons/discounts, tax, service charge and total. This does not define every store's printed layout. |
| UK | [Tesco guide prices](https://www.tesco.com/help/pages/online-grocery-faqs/ordering-online/guide-prices) and [Sainsbury's Nectar Prices](https://help.sainsburys.co.uk/help/products/nectarprices), 17 Nov 2026 | Loose fruit and veg can be charged by weight; a price offer can appear on an e-receipt. No universal abbreviation list is given. |
| NZ | [New World online terms](https://www.newworld.co.nz/shop/terms-and-conditions) and [Woolworths NZ app](https://www.woolworths.co.nz/services/woolworths-nz-app), 17 Nov 2026 | Variable-weight food is charged by actual picked weight; paper receipts are still offered in store. The pages do not fix a line format. |

The `sample_receipt_line` field deliberately varies spelling and abbreviation (including `TOM TINNED 400G`, `CANNED TOMATOES`, capsicum/bell pepper, courgette/zucchini and bicarb/baking soda). It tests normalisation, not whether a named retailer prints those exact words. No retailer page contents or imagery are copied. These short facts are paraphrased; no reuse licence for retailer copy was found, and none is needed for the synthetic samples. The catalogue's own source and licence notes are in `workbench/drafts/catalogue/NOTES.md`.

## What Lane A needs from the core

The current Stock forms accept one movement at a time. For this flow the core needs: a local-only receipt text parser and optional local image/OCR path; extraction of product lines separately from totals, tax and promotions; quantity/unit parsing with a distinction between purchased quantity, package size and weighed amount; catalogue candidate ranking using aliases, region and existing household items; a staged review record that saves nothing until confirmed; a batch write/undo transaction with conflict detection; and duplicate-receipt detection without retaining payment details. Store only the approved line text needed for an audit trail, with a household option to discard it. The app must not contact a remote OCR service without a separate opt-in and privacy design.

Do not add inferred use-by dates, locations or drinking-water flags just because text matched a catalogue entry. Confirm those through the normal Stock/lots rules. For food bought by weight, compare compatible units before proposing a movement. If the parser cannot separate `2 for $7` from `2L`, show the whole line for a person to fix instead of guessing.
