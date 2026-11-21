# Exact form and Review words

Designed **21 November 2026**. Invented examples only. Dates and currency format follow the household setting.

## Stock in, by hand

Keep the existing item, batch, amount and date fields. Under an optional **Purchase details** foldout:

- **Where did you buy it? (optional)** — “A short shop name is enough. Leave card and loyalty details out.”
- **What did you pay for this Stock in? (optional)** — choice **Total for these goods** / **Price for each [item unit]**; amount field labelled **Paid [household currency]**. “Use the receipt or what you paid. Leave blank if you are unsure. This will not change the stock amount.”
- **Is this part of a larger receipt?** — **No / Yes, add to this purchase**. For Yes, choose the purchase already in progress, not a name-only match. Show **Receipt total** separately if the person has it.
- Save result: **Added 2 tins to this batch. Saved 3.80 [currency] as the total paid for these 2 tins.** If price blank: **Added 2 tins. No price was recorded.** A failed Stock in saves neither the movement nor its purchase line.

## Helper receipt on Review

The decision 0097 source still says **From the receipt or paper, as [helper] read it: “KIDNEY BEANS 400G x2” · Price: 3.80**. Directly below it: **The helper's price is for checking only. It will not be saved as a purchase price unless you confirm it.** If the line is matched and ready, offer **Save a price with this Stock in?** with **No price**, **3.80 is the total for this line**, **3.80 is the price for each unit**, **Enter another amount**. The unit and bought quantity remain visible. Where the receipt's price basis is ambiguous, default to **No price**, not the guessed interpretation. For a new item plus `{"ref": 0}` Stock in, this confirmation belongs to the dependent movement and accepts atomically with the item. On Accept: **Added Stock in and saved the price you confirmed.** If no price: **Added Stock in. The receipt price stayed on Review only.** On Reject: **Rejected this Stock in. No purchase price was saved.**

For a group, show **Receipt total as read: 14.20 · Confirm as paid total / Leave as checking text**. A source total cannot be inferred by adding line prices, especially when there are skipped or non-Stock lines. Before **Accept all**, show **3 Stock in rows · 2 confirmed line prices · 1 price unknown** and any difference from confirmed receipt total. The duplicate-receipt warning and **Keep this as another purchase** choice remain in force; confirming a price never bypasses them. An unmatched line's **Choose item / Skip line** choice remains on Review; Skip keeps source there until **Finish receipt review** and saves no Stock line or price.

## History and question

On a Stock item's history: **Bought on 20/11/26 · 2 tins · 3.80 [currency] total paid at Example Market**, behind a deliberate **Show purchase details** because price and shop are private. If unknown: **Bought on 20/11/26 · 2 tins · price not recorded**. The cost question labels its date range, included items, confirmed paid total, priced/unpriced line counts, partial receipts and refunds. It never says **You spent 0** for a period with missing entries.
