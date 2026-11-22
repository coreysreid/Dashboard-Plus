# Batch 21 item 104: exact helper starting-message changes

Checked 21 November 2026 against `src/dashboard/web/helper_guide.py`, `src/dashboard/connector/tools.py`, decision 0102 and **merged decision 0112**, plus [REVIEW.md](REVIEW.md). This is a replacement table for Lane A; no shipped code is edited here. The guide is generated per grant, and the connector tool description is static. Keep the new text near the action it qualifies. The order is worst first.

Decision 0112 already guards three old highest risks: a `may_count_twice` warning, full-path choices for a name sent instead of an ID, and a private-copy flag on Review. The current guide also says to stop for an ungranted link, ask about ambiguous dates/water/unit conversions, and report sent versus accepted versus waiting. Do not add duplicate paragraphs for those.

## 1. A tracker count must not be called a purchase

**Current generated starting-message sentence** in `AMOUNTS IN STOCK ITEMS`: “For a record already in Stock items, send an entry to stock__movements (Stock in and out) with item set to its id, reason `bought`, amount and its other required fields.” This invites an old on-hand count to be sent as bought, adding it on top of the existing count. The helper API supports a movement, but a stocktake needs a chosen batch and the difference from what was already recorded; a tracker total alone does not establish that difference.

**Replace with:** “For an item already in Stock, first ask whether the number is a new purchase, a count of what is on hand, or an amount used. Send `bought` only for a purchase the household confirms, with its actual date and amount. A tracker count is not a Stock in: let the person count the batch in Dashboard Plus, or ask them to confirm the current batch and the difference before suggesting a correction. Never add the whole count on top of what is already there.”

**Connector `dashboard_suggest_new_records` description, add immediately after the new-item starting-amount sentence:** “A tracker balance is not a purchase. Do not send `bought` for it; ask whether the number is stock already on hand, a new purchase or an amount used, and let the person count a batch when the difference is unknown.”

**Check:** Invented tracker says “Rice: 12 tins on shelf,” current record says 5, and no purchase date is supplied. The assistant does not suggest `bought 12` or guess `bought 7`; it asks for a batch count. A separate invented receipt for 2 newly bought tins can use `bought 2` with its date.

## 2. Old tracker and receipt may describe the same goods

**Current guide** explains `receipt_context` possible-repeat checks for the same receipt, but that cannot know whether an old tracker count already includes the receipt. Its `HOW TO SEND` paragraph treats receipts independently.

**Add after the receipt-context sentence:** “Before sending an old list and a receipt for the same goods, ask whether the receipt's purchase is already included in the old count. If the household is unsure, keep the receipt line for the person to check on Review; do not silently add it as another purchase or leave it out.”

**Connector description, add after `receipt_context`:** “A possible-repeat check compares receipts, not an old stocktake with a receipt. Ask whether the purchase is already in the starting count before suggesting both.”

**Check:** An invented move-in count of 12 tins and a receipt for 2 tins on the previous day produce a question; no assertion of 14 tins or automatic deduplication.

## 3. A Review-only price is not saved spending

**Current guide:** “It is shown on Review for checking and never saved in the records.” Correct, but the assistant's finish message may still claim the price was recorded or calculate a spent total.

**Add beside the `source.price` example:** “A source price helps the person check the receipt on Review; it is not purchase-price history. Do not say the price or a spending total was saved, and do not copy it into Stock notes.”

**Connector description, replace its source-price ending** “it is shown on Review for checking and never saved in the records” **with:** “it is shown on Review only, not saved as a Stock price or spending total. Do not claim a cost history was recorded or put the price in Stock notes.”

**Check:** A made-up receipt source price of 3.80 is visible on Review but absent from the accepted Stock item and the assistant's “recorded” tally.

## 4. Refresh changing limits and report row outcomes

**Current guide:** “To read this guide again, with up-to-date limits, use GET /api/v1/guide” and “Count from GET /api/v1/batches, not from memory…” These are sound but do not say when to refresh and can leave an accepted group beside a refused group in one move.

**Replace the first with:** “Before each new batch, and after a limit or validation refusal, call `dashboard_how_to_help` again. The allowance and waiting count in a copied message can be out of date. Use the current answer; do not keep retrying a refused send.”

**Replace the finish sentence with:** “Before you finish, read `GET /api/v1/batches` and the rows in each batch. Tell the person how many were sent, accepted, still waiting and refused; name each unresolved source row and why. If you cannot verify a status, say it is unknown. Sent does not mean accepted or complete.”

**Connector `dashboard_how_to_help` description, add:** “Call again before each batch; its limits and grants may have changed since a copied guide.”

**Check:** Review accepts one of two invented groups and leaves the other waiting. The assistant reports both states and the unresolved source row, not “Move complete.” A daily limit refusal causes a fresh guide read, not a guessed larger allowance.

## Implementation note

These are replacement sentences, not permission to add a helper write path. The assistant still proposes **new** records only; a person accepts, corrects or rejects on their own screen. Keep the guide's grant-specific field list, one-entry new Stock start, private-field exclusions, source line example and one-use `request_key` rule. The connector description has a size cost; if it must be shorter, keep priorities 1 and 2 there and leave the detailed checks in the dynamic guide. Run the invented fixture from `tests/test_helper_starting_amounts.py` to verify the generated words and check that no key or household record appears in the guide.
