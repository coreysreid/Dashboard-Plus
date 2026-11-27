# Batch 22 item 110: confirmed prices and Spent per month, checked

Checked **27 November 2026** against `main` at `2d9fca8`, decisions 0097, 0128, 0133 and 0134, the shipped Stock price/refund declarations, and disposable copies of the invented Smith (AU), Garcia (US) and Taylor (UK) households. The figures below are invented. This is recorded Stock-in spending, not a household budget or proof of everything purchased.

## Findings, worst first

**No new defect confirmed in the checked flow.** The remaining core gap matters before member sync: a confirmed price stays on the computer where it was typed (`travels = "never"`). Once member computers can add Stock ins, a chart on either computer may count an accepted purchase yet lack its price. Its total must say which computer's prices it covers, or mark coverage incomplete; it must never imply a complete household total. Decision 0128 already names this gap. There is no member sync stage 2 to run yet.

## What held against the records

| Invented household | Before Show | After the pressed Show | Missing-price and refund words |
|---|---|---|---|
| Smith (AU) | 3 Stock ins, no amounts | **19.50 AUD spent, from 3 Stock ins, less 1.20 refunded (18.30 AUD after money back)** | The refund is said beside the gross spending, not silently taken from the bar. |
| Garcia (US) | 3 Stock ins, no amounts | **6.07 USD spent, from 2 Stock ins** | **1 Stock in has no price, so it is counted but not added.** |
| Taylor (UK) | 2 Stock ins, no amounts | **3.30 GBP spent, from 1 Stock in** | **1 Stock in has no price, so it is counted but not added.** |

- **Phone and desktop:** Chromium opened the Stock bars in each household at **320px** and **1280px**: six views. Each page returned 200, fit its viewport and kept the same address through Show. A GET, including `?show=1`, showed counts only; the pressed Show response carried the amounts with `no-store`. The chart's table repeated the amounts and month labels in words.
- **No-price month:** In an extra disposable Smith copy, an invented unpriced Stock in dated 15 October made October's row say **“no price recorded · 1 Stock in recorded · 1 with no price”**. November kept its 19.50 AUD gross and 1.20 AUD refund. A month with no Stock in said **“nothing recorded”**. No unknown price became zero.
- **Refunds and currencies:** A refund has its own date and original Stock-in link; the bar reports gross paid and says money back separately. The focused tests cover a refund in a later month, another currency and an over-refund confirmation. Amounts in different currencies are never converted or added together. A Stock out does not subtract spending.
- **Receipt to Review:** A helper's receipt line may carry a price as `source` text for a person to inspect, but accepting the Stock in does not copy it into a confirmed price. The person must type **What you paid** and choose whether it is the total or for each one. The focused Review tests passed this boundary; the helper cannot suggest a private price field directly.
- **Local-only values:** `price`, `price_basis`, `paid_total` and `currency`, plus refund amounts and notes, are sensitive and absent from ordinary Stock lists, sheets, spreadsheet export and helper reads. The sync change log keeps field names but not price values. Local backups still contain them, as expected for recovery.

`tests/test_purchase_prices.py` and `tests/test_refunds_and_review_price.py` ran **47 focused tests, all passing**. The browser run used disposable invented data and the Stock chart only. It did not test a real receipt reader, a paired computer, or another person's browser profile. No shipped code was edited.
