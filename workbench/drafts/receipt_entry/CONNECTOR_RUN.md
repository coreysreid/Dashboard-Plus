# An invented receipt, through the shipped connector and Review

Checked **20 November 2026** against `main` at `112e64f`, the shipped MCP connector, helper API and Smith example. The [receipt image](EXAMPLE_RECEIPT.jpg) is wholly invented: Example Market, 20/11/26, two 400 g tins of kidney beans at $1.20 each, three 400 g tins of tinned tomatoes at $1.10 each, total $5.70. It has no payment, customer or retailer data. I read this raster image as the assistant's photo-reading step; **Dashboard's connector has no image tool**. A named AI assistant desktop app and its OCR were not tested. Everything after transcription below ran through the actual `python -m dashboard.connector` process and a temporary local Dashboard; a person-like browser session clicked Review at 320px.

## Household journey and observed result

1. Load a fresh **Smith** example into a temporary data folder. Give **Example receipt helper** Look and suggest access to **Household stock**. Start Dashboard and the stdio connector with its current local address and one-time key in process settings. Neither key nor temporary path is recorded here.
2. Read [the invented image](EXAMPLE_RECEIPT.jpg): `KIDNEY BEANS 400G / 2 x $1.20` and `TINNED TOMATOES 400G / 3 x $1.10`. Treat `400G` as package size and `2`/`3` as bought tins; ignore subtotal and total as Stock rows. The photo supplies no use-by date or storage place.
3. Ask the connector what the helper may see, get Stock's table schema, then list existing Stock items. Its `records` contain item fields under **`values`**. In this fresh fixture, Kidney beans is ID **6**, **13 tins** across two batches; Tinned tomatoes is ID **5**, **1 tin** in one batch. These IDs were read from the tool, not assumed from the receipt.
4. Send one suggestion batch with two bought movements. The connector replies **“2 suggestions are waiting for the household to review. Nothing changes until they accept them.”** The item amounts remain **13** and **1**.
5. Open **Review suggestions** in a 320px browser and press **Accept** on each row. The screen returns **“Added to Stock in and out.”** Kidney beans becomes **15 tins** in three batches, and Tinned tomatoes **4 tins** in two batches. Each bought movement made one new batch, because the helper did not choose an existing batch or invent a use-by date or place. The connector's later batch lookup says `state: decided`, both proposals `accepted`, with new movement record IDs **7** and **8** in this temporary fixture. The page had no horizontal overflow at 320px.

## Exact tool calls and relevant replies

The MCP client first sent `initialize` for protocol `2025-06-18`, then these `tools/call` requests. The connector adds its local identity check before every API request. The key is in the connector's process environment, **not** in a tool argument.

```json
{"name":"dashboard_me","arguments":{}}
{"name":"dashboard_tables","arguments":{}}
{"name":"dashboard_list_records","arguments":{"table":"stock__items","limit":200}}
```

`dashboard_me` identified **Example receipt helper**. `dashboard_tables` included granted Stock tables and fields. The relevant `dashboard_list_records` reply was:

```json
{"records":[
  {"id":6,"values":{"name":"Kidney beans","quantity":13,"unit":"tins"}},
  {"id":5,"values":{"name":"Tinned tomatoes","quantity":1,"unit":"tins"}}
]}
```

This is a shortened, reordered excerpt of two records, not the whole response. The actual call returned the other granted Stock items too. The assistant then sent exactly:

```json
{"name":"dashboard_suggest_new_records","arguments":{
  "request_key":"example-market-2026-11-20-1",
  "why":"Invented Example Market receipt: 2 tins kidney beans; 3 tins tinned tomatoes. Check the paper before accepting.",
  "entries":[
    {"table":"stock__movements","values":{"item":6,"reason":"bought","amount":2,"happened_on":"2026-11-20"}},
    {"table":"stock__movements","values":{"item":5,"reason":"bought","amount":3,"happened_on":"2026-11-20"}}
  ]
}}
```

The reply's `structuredContent.data` was:

```json
{"batch_id":1,"state":"waiting","proposals":[
  {"id":1,"position":0,"table":"stock__movements","status":"pending"},
  {"id":2,"position":1,"table":"stock__movements","status":"pending"}
],"message":"2 suggestions are waiting for the household to review. Nothing changes until they accept them."}
```

It also echoed `why` as helper-written text. After both browser decisions, `dashboard_get_suggestion_batch` with `{"batch_id":1}` reported `state: "decided"` and two `accepted` proposals with movement `record_id` values **7** and **8**. The displayed `batch_id`, item IDs and movement IDs are from this temporary fixture only.

## Exact Review words and rough edges

Review said **“Example receipt helper · 2 suggestions”**, labelled the reason as written by the helper, and showed:

> **“Example receipt helper suggests adding to Stock in and out: Item: Kidney beans · Reason: Bought or added · Amount to add or use: 2 · Date: 20/11/26”**

The second row used **Tinned tomatoes** and **3**. Each had **Accept** and **Reject**; the batch also offered **Accept all 2** and **Reject all 2**. The two accepted rows appeared immediately in Stock. No price, original receipt line, confidence, place or use-by date appears per row. The generic “Amount to add or use” label also makes the person check Reason to know this is Stock in. **Suggested exact receipt-aware line:** **“From receipt line ‘KIDNEY BEANS 400G · 2 x $1.20’: add 2 tins of Kidney beans on 20/11/26. No use-by date or place was supplied.”** Show **Accept** / **Reject** below it. This needs source-line provenance in core; it must not claim the $1.20 is a saved Stock price.

The connector itself did not feel slow on this local example, but the handoff is manual: the assistant reads the photo outside Dashboard, checks existing IDs, then the household opens Review and makes two decisions. My first trial script failed because it looked for `record.name` instead of the documented `record.values.name`; correcting the client script worked, with no product error. No receipt/photo tool, per-row source image, price field or receipt-wide Undo ships yet. The helper created two new undated/unplaced batches because the receipt did not supply those facts. A real client should ask the person for any actual use-by dates or places before suggesting them, never infer them from a catalogue shelf-life hint. These are core/product gaps in [NOTES.md](NOTES.md), not reasons to write directly to Stock outside Review.
