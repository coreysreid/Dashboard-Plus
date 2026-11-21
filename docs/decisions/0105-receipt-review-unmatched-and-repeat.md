# 0105. Receipts on Review: plainer group words, lines a helper could not match, and a receipt sent twice

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** 0068 (suggestions wait until a person accepts), 0080 and 0094 (Import), 0097 (receipt lines and groups), 0101 (Accept all by group), 0102 (the helper guide)
- **Answers:** Lane B's batch 19 items 82, 83 and 86: `workbench/reports/2026-11-21-receipt-group-review.md`, `workbench/drafts/receipt_entry/UNMATCHED_LINES.md` and `DUPLICATE_RECEIPT.md`

## In plain words
Review now says what each receipt row does in one line: "Add 1 pack of Demo red lentils on 20/11/26". A new item and
its Stock in say exactly what each button does ("Accepting only the Stock item leaves the Stock in waiting"), and
after Accept all the result names what went in ("Added 1 to Stock items and 3 to Stock in and out").

A helper can now send a receipt line it could not match to a Stock item. It waits on Review with **Choose item**
(pick one of your Stock items, or make a new one, then confirm how much and when) and **Skip line**. Only what you
confirm reaches your Stock. A skip can be undone until you press **Finish receipt review**.

If a receipt looks like one already sent (by a helper or a spreadsheet import marked as one receipt), Review says
so, shows what happened to the earlier one (still waiting, added, partly added or undone) and waits until you choose
**Reject this copy** or **Keep this as another purchase**. It never refuses anything by itself: two shops for the
same goods on the same day are allowed.

## What we chose
- **Wording (item 82).** A Stock in or out on Review, and in Import's ready rows, leads with one sentence built from
  the movement rule (`adjusts`): "Add" or "Take away", the amount, the item's own unit (singular for exactly 1, by
  `units.unit_for`), the item's name (the suggested name for a new item in the same batch) and the date, replacing
  the Item, Amount, Date and default Reason parts. A group's label is worked out from its rows and stays true under
  0101: Accept on one row adds it and the records it needs, never the rows that need it; Reject on a new record
  rejects what needs it; ticking, Accept all and Accept ticked take the whole group or none. Each row names its own
  consequence. The Accept button keeps its fixed width (0101) and carries the longer words ("Accept Stock in and its
  new Stock item") as text read aloud, not as a wider label. The result line after Accept all or Accept ticked names
  each list with its count, from table names checked against the switched-on tables, never from the address text.
- **Unmatched lines (item 83).** An entry may be `{"kind": "unmatched_product_line", "source": {"line", "price"},
  "receipt_date", "quantity_hint", "unit_hint"}`: closed keys, the line required (1 to 200), a real ISO date, a
  quantity that is a number above 0 written as text (20 characters at most), a unit of 1 to 30. A line that starts
  like a total, tax, payment, change, coupon or refund is refused. It counts towards the 50 entries, the daily limit
  and the Review queue. It is stored in `core__proposals` with `entry_kind = 'receipt_line'` (core migration 0009),
  the hints in `values_json` and the line in `source_json`, and its `table_name` is the helper's movement table.
  Helpers whose grant has no movement table get 404. A ref may not point at a line, and the dry run leaves lines out
  (refs are renumbered, and problems are reported by the request's own numbers). The reply marks the row with
  `kind` and says "1 suggestion is ready to check and 1 receipt line needs the household's choice".
- **Deciding a line.** Choose item is two small pages: pick an item (the household's own, by name) or "Make a new
  Stock item" (its name with catalogue suggestions, category and unit), then "How much did you bring home?" in that
  item's unit and the date (the paper's date, or today, for the person to check). A hint is used only when its unit
  is the item's own (tin and tins), never converted. Save runs in one transaction: it claims the line, checks the
  item's revision (refused with "This Stock item changed while you were checking the line ..."), makes the new item
  if asked, then one bought movement through the ordinary create path, as the person. A second press finds the line
  decided and adds nothing. Skip marks it rejected (shown as skipped); Undo skip puts it back while the batch is not
  finished. **Finish receipt review** appears once every row and line is decided, sets `finished_at` and shows the
  outcome ("1 row added; 1 line skipped. No Stock was added for the skipped line."). Accept all, Accept ticked,
  Reject all and Reject ticked never touch a line; Accept all reads "Accept 2 ready rows; 1 line still needs your
  choice". The line and hints are never copied into a record, its history or an export.
- **A receipt sent twice (item 86).** A request may carry `receipt_context: {"purchase_date", "shop_label"}`, and
  Import offers "These rows are from one receipt" with its date for Stock in and out; either stores
  `receipt_json` on the batch. Only such batches are compared. A batch's basket is a multiset of (date, item, amount,
  unit) from its bought rows that are not rejected and from lines a person added; a new item in the batch is
  (its name, unit) and only ever counts as "similar". Price, line text, order, case and spacing are ignored;
  repeated lines count each time. It is compared with up to 1,000 earlier receipt batches, newest first. An exact
  match with an earlier receipt that still has rows waiting or added is a **possible repeat**: every Accept route
  refuses, checked before and again inside the write transaction (`receipts.guard`), until the person rejects this
  copy (only this batch's rows) or keeps it. **Keep** stores the earlier batch's id and its rows' ids and states, and
  this batch's row ids (`repeat_ok_json`); if any of those change, the warning comes back. A partial match ("Some
  lines look like an earlier receipt", with what differs) and an earlier receipt whose Stock in rows were all
  deleted ("Earlier receipt was undone") are shown but hold nothing. "Open earlier receipt" goes to it on Review or
  to a read-only page of what became of each row. Import shows an early notice when ticked rows look like one
  already sent. The same `request_key` retry still returns the first batch, as before.
- **Card numbers.** Any helper text holding a 15 to 19 digit number that passes the card check digit is refused
  with 400 `payment_detail`, so payment details never reach Review or a backup. Barcodes (8 to 14 digits) pass.
- The connector's suggest tool takes the line form as `anyOf` beside the record entry, and `receipt_context`; its
  input checker learned `anyOf` and `enum`. The OpenAPI file gains `RecordEntry`, `UnmatchedLine`,
  `ReceiptContext`, the row `kind`, `payment_detail` and an example the contract test sends. The helper guide says
  how to send one receipt and an unmatched line, and what never to send.

## Why we chose it
- Lane B's live run showed a person reading "Amount to add or use: 1" with the unit two rows away, and a group label
  that could be read as "either Accept adds both". The words now match what the buttons do.
- A line a helper cannot match is real evidence of a purchase; dropping it loses it, and guessing an item puts a
  helper's guess in the records. Holding it for the person keeps "nothing changes until a person accepts" exact.
- Comparing what would be added, not the receipt's text, catches the same shop sent by a second helper or a
  spreadsheet, needs no stored fingerprint of anyone's shopping, and never confuses a re-typed line for a new one.
- Holding Accept (not refusing the batch) leaves the decision with the household, who may truly have shopped twice.

## What else we considered
- **Storing a hash of each basket:** quick lookups, but a low-variety basket hash can be guessed and is a lasting
  record of shopping; we compare live from the waiting rows and records instead.
- **Treating every batch with source lines as a receipt:** a helper's `why` or a few source lines do not prove one
  receipt; an explicit `receipt_context` or tick does.
- **Holding partial matches too:** too many false alarms for staple goods bought every week.
- **A wider Accept button reading "Accept Stock in and new item":** breaks 0101's fixed button column; the words
  are on the row and read aloud with the button instead.
- **A new status for skipped lines:** needs a table rebuild for the status check; "rejected" on a line already
  means "nothing was added", and the page and API say "skipped" through `kind`.

## What this costs us (the downsides)
- One more core migration (0009) with four columns, and a second row kind that every reader of `core__proposals`
  must respect (`entry_kind = 'record'` for anything that adds a record).
- The repeat check runs on every Review page load and every Accept for receipt batches; it is bounded to 1,000
  earlier receipts but costs more with a long history.
- A household that keeps the same weekly shop and marks every one as a receipt will see the warning often and must
  press Keep each time.
- The "Take away" and noun words ("Stock in", "Stock item") are made from table titles; a future module with
  movements and an unusual title may read less well.
- The total and card-number filters are simple patterns: a product named like "Total care toothpaste" is refused as
  a line (the helper can still send it as an ordinary Stock in), and a card number split oddly may pass.
- Lines and receipt data stay in the household backup like other Review data (0097); they are not in exports.

## How hard it is to undo
Medium. Refusing `kind` entries and `receipt_context` again is a few lines in `proposals._read_body`, the OpenAPI
file and the connector schema; waiting lines would need skipping first. Removing the repeat hold is removing
`receipts.guard` from the accept paths. The wording is in `review.py` only. The new columns can stay empty.

## We should revisit this if
- People press Keep on most receipts (the hold is noise) or accept a true repeat anyway (the warning is too quiet).
- Helpers send many unmatched lines that are obviously one item (then offer a helper-suggested match to confirm).
- Households ask for a receipt-wide Undo, which this does not provide.
