# 0102. A starting message for the helper's assistant, and a new Stock item with its amount as one suggestion

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** 0067 (the helper API), 0083 (the connector), 0084 (the published API description), 0097 (grouped suggestions)
- **Answers:** feedback from an AI assistant that moved a household's records in through the connector

## In plain words
When Corey's assistant moved his household in, it only found out how stock works when its first try was refused.
Every counted item then took two suggestions (the item, then a "Stock in" for its amount), so about 138 things
became about 273 suggestions against a limit of 200 a day. It also did not know that private details such as a
vehicle registration cannot be sent by helpers, learned the limits late, and never used Places.

Now each helper in Settings, Helpers has a **Starting message for your assistant** to copy into the chat. It is
made from the household's own lists: which lists that helper may use, their fields, which are required, links
to look up first, which details are private (the person types those), how stock amounts work, how to send, and
today's limits. It never holds a record, a private value or the key. The assistant can read the same words itself
with the new `dashboard_how_to_help` tool.

A new Stock item can now arrive as **one** suggestion carrying its amount on hand, unit, use-by date and place,
exactly like the person's own Add form. Accepting it adds the item and its first batch together. It counts as one
suggestion.

## What we chose
- **The guide** (`src/dashboard/web/helper_guide.py`) is plain text built from the helper's grant: for each table
  it may use, the same field list as `GET /api/v1/tables` (name, label, kind, required, choices, link target, help),
  plus the labels of private fields ("Private, never for helpers: Registration or plate number. Leave it out; the
  person types it in after accepting."). Links into parts the helper was not given stay invisible, as in 0074.
  It explains looking up linked records (Places, People) first and `{"ref": N}` for one that is truly missing;
  the stock model, worked out from the module's own `total` and `adjusts` rules; at most 50 entries a send, small
  batches and reading each answer, a new `request_key` per send and the same one on a retry; dates, money and
  choices; the receipt `source`; today's daily allowance and that the person can allow more on Review; the 500
  waiting cap and how many are waiting; requests a minute; never asking for or repeating the key; and telling the
  person what it could not fit. A look-only helper gets the lists without the sending parts.
- **Where it is shown.** Settings, Helpers: a "Starting message for your assistant" box (folded under each active
  helper's card, and open on the new-key and changed-key pages beside the connection settings), with a Copy button.
  The text is in the page, so it can be selected and copied without JavaScript. The Copy buttons now share one
  listener for the page.
- **For the assistant:** `GET /api/v1/guide` returns `{"text", "limits", "message"}` behind the same key as every
  route, and the connector's ninth tool, `dashboard_how_to_help`, calls it. Its result is labelled as Dashboard
  Plus's own guide, holding no household records, instead of the household-data label. The connector's start-up
  instructions say to call it first. The OpenAPI file gains the path, `Guide`, a shared `Limits` schema and a
  `counted_item` request example that the contract test sends for real.
- **Starting amounts on helper suggestions.** `proposals.submit` runs its dry run with `starting_amounts=True`, the
  same switch Import uses (0080). A suggestion for a new Stock item may carry `quantity`, `expires` and `place`
  (the module's `starts_from`) beside `unit` and its other fields. On accept the ordinary create path makes the item
  and its first batch in one transaction, as the Add form does, credited to the helper. The amount, date and place
  are checked exactly as the form checks them; `GET /api/v1/tables` now marks those fields `can_suggest` with a note
  that they apply only to a new record. Review already shows them with their form labels ("Amount on hand: 2 ·
  Unit: kg · Where it is: Shelf 3 · Use by: 20/09/27").
- **A link that points nowhere** (a Place id that is not there, or a place sent as a name) is refused with the next
  step: "Look up Places first (GET /api/v1/tables/stock__places/records, or the dashboard_list_records tool) and
  send the id of the one that matches. If it is not there, suggest it earlier in this request and point at it with
  {"ref": N}."
- Two-entry groups (a new item and its Stock in, 0097) work as before.

## Why we chose it
- The assistant's own feedback: it would have needed none of its refused tries, and half as many suggestions, had it
  been told at the start. A message the person pastes works with any assistant; a tool works when the assistant
  calls it. Both come from one function, so they never disagree.
- One entry for one counted thing is what a person does in the Add form, so a helper doing the same is easy to
  check on Review and fair against the daily limit.
- Reusing the Import switch and the ordinary create path means no new way to make a batch, and no new checks to
  keep in step with the form.

## What else we considered
- **Raising the daily limit for moving in:** treats the symptom; a household would still review twice as many rows.
- **Making the two-entry group count as one:** keeps the extra Review rows and the extra rule.
- **Putting the guide only in the connector's instructions:** not every assistant shows them, and the person could
  not see or copy them.
- **Naming no private fields, as `/tables` does (it gives only a count):** the assistant then cannot tell the person
  what is left for them to type. The labels come from the module files, which are public; values never appear.

## What this costs us (the downsides)
- The message can be long for a helper given many parts (every field and choice is listed). Assistants handle that,
  but a person reading it may find it a lot.
- Private field *labels* are now told to helpers (never their values). A household that wrote a private field's
  label as something revealing would expose that label.
- The numbers in a copied message (left today, waiting now) are right only when copied; the message says to copy it
  again, and the tool always gives current ones.
- "The person can allow more on Review" relies on the Review page offering that; if it does not, the sentence must
  change with it.
- An item suggested with an amount and also a Stock in for it counts the amount twice, exactly as in the form. The
  guide warns against it; Review shows both rows.

## How hard it is to undo
Easy. Remove `starting_amounts=True` in `proposals.submit` and the `starts` lines in `api.table_spec` to refuse
starting amounts again (suggestions already waiting with one would then be refused on Accept with the old "worked
out" reason). Remove the `/guide` route, the `dashboard_how_to_help` tool, `helper_guide.py`,
`helper_start_message.html`, its includes, and the OpenAPI entries to drop the guide; nothing else depends on them.

## We should revisit this if
- Assistants still send a Stock in beside an item with an amount (then refuse that pair, or ask on Review).
- People find the message too long to paste; then offer a short form that points the assistant at the tool.
- Another module gains amounts worked out from batches; check that the guide's stock wording still reads well.
