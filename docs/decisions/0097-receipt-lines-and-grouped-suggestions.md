# 0097. Receipt lines on suggestions, and a new item with its Stock in as one group

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** 0068 (suggestions wait until a person accepts), 0074 (helper text is screened), 0084 (the published API description)
- **Answers:** Lane B's receipt findings in `workbench/drafts/receipt_entry/` (HELPER_FLOW.md, CONNECTOR_RUN.md, NOTES.md)

## In plain words
When an assistant reads a receipt, each row it puts on Review can now show the receipt line it came from and its
price ("From the receipt or paper, as Pantry helper read it: “KIDNEY BEANS 400G x2” · Price: 3.80"), so the
household can check it without the paper beside them. That text is the helper's words, shown for checking only;
it is never saved in the records. A good the household has never stocked can now arrive as a new Stock item and
its first Stock in together. Review shows them as one group: accepting the Stock in adds the item too, in one step,
and rejecting the item rejects the Stock in with it. Any single row can still be rejected on its own.

## What we chose
- **Source line.** Each entry of `POST /api/v1/proposals` may carry `source`: `{"line": ..., "price": ...}`, at
  least one of the two, both text (line 1 to 200 characters, price 1 to 20), no other keys. It is screened with the
  rest of the request (no key-shaped text, no hidden or text-reversing characters, decision 0074), kept in the new
  column `core__proposals.source_json` (core migration 0006), and shown on Review with the helper's name, through
  the same replacement-mark net as other helper text. It is never passed to the create path, so it cannot reach a
  record, its history or an export. Anything worth keeping goes in a real field in `values`.
- **Pointing at an earlier entry.** In a `link` field, `{"ref": N}` means "the record entry N of this request would
  add". N must be a whole number for an earlier entry (0 to this entry's position minus 1), and entry N must add to
  the table the link points at. Anything else (itself, a later entry, the wrong table, a text "0", a `links` list,
  a non-link field) refuses the whole request with 422 `invalid`, naming the entry and field. The dry run (0068)
  swaps each ref for the record the earlier entry made inside the rolled-back transaction, so a Stock out after a
  new item's Stock in is checked against that amount; a ref to an entry that failed is refused too.
- **Stored as sent.** Values are kept with the ref in place. A batch reply lists `depends_on` (the positions a
  suggestion points at) only when there are any, so earlier replies are unchanged.
- **Accept.** Accepting a row first adds every waiting row it needs, earliest first, then itself, all in one
  transaction; each needed row is decided, audited and marked `edited_by_person` as if accepted by itself. A ref to
  a row already accepted uses that row's record. If any of them cannot be added, nothing is added; the reason is
  kept on the row that failed and a pointer to it on the row asked for. A row whose needed row was rejected cannot
  be accepted.
- **Reject.** Rejecting a row also rejects every waiting row in its batch that needs it, directly or through
  another, in the same transaction, with the reason "Rejected with entry N, which it needed." Rejecting a Stock in
  alone leaves its new item waiting.
- **Accept all and Reject all** go in position order, so an item is always added before its Stock in. A row whose
  needed row could not be added is not tried and says so. Reject all counts each row once.
- **Review** shows rows that point at each other inside one bordered group ("These 2 rows go together ..."), the
  link as "Red lentils (new, suggested above)" until the item is accepted and as the real name after, and on each
  row what Accept or Reject will also do. Imports (0080) never carry a source or a ref and behave as before.
- The connector's `dashboard_suggest_new_records` schema takes `source` (closed, the same limits) and its
  description explains refs. The OpenAPI file gains `Source`, the ref form of `Value`, `depends_on`, and a receipt
  example that the contract test sends for real.

## Why we chose it
- Lane B's live run showed the person had to keep the paper beside the screen, and a clear new good took two Review
  visits with a helper polling in between. Both are now one look and one decision.
- Positions inside one request are the simplest reference a helper can get right: it cannot know a future record
  id, and nothing outside the request can be pointed at, so a ref can never reveal or reach another record.
- Accepting dependencies in the same transaction keeps "nothing changes until a person accepts" exact: there is
  never a Stock in without its item, or an item half added.
- Keeping the source out of `values` means the households' records hold only what a person accepted into real
  fields. A receipt price is not a Stock price (Stock movements have no price field).

## What else we considered
- A separate `depends_on` list beside each entry: two ways to say one thing, and a link field would still need a
  placeholder value.
- Temporary names (`"item": "@lentils"`): readable, but a second namespace to validate, and easy to clash with real
  text values.
- Saving the receipt line in the record's notes: it would put helper text in the records without a person typing
  it, and it would repeat payment-shaped text into exports.
- A whole "receipt" batch type with Choose item and Skip line for unmatched lines: larger, and still needs these two
  pieces first. Left for later.

## What this costs us (the downsides)
- Accepting one row can add more than one record. Review says so on the row and in the result line, but a person
  who does not read it may be surprised.
- A ref only works within one request; a helper that splits a long receipt must keep each item with its Stock in in
  the same request.
- `values_json` can now hold `{"ref": N}`; anything that reads stored suggestions must resolve it (only
  `proposals.py` and the Review page do).
- The source line is the helper's reading of the paper, not the paper. It can be wrong, and it is labelled as such.
- One more core column and migration (0006).

## How hard it is to undo
Medium. Refusing `source` and `ref` in new requests is a small change in `proposals.py`, the OpenAPI file and the
connector schema. Suggestions already stored with refs would need to be decided (or rejected) before the resolving
code is removed; the `source_json` column can stay empty.

## We should revisit this if
- People report accepting a Stock in without noticing it added an item (then ask before adding the item).
- Helpers need to point at a record from an earlier request that is still waiting (refs across batches).
- Households want the receipt line kept as history; that needs its own privacy design and a way to discard it.
