# 0074. Agent API hardening: hidden links, one "not found", clean helper text and a limit per minute

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** decisions 0067 and 0068; answers cases 8, 11, 13, 16, 18, 20 and 22 of Lane B's abuse-case catalogue

## In plain words
A helper given one part of your records (say Vehicles) can no longer learn anything about a part it was not given
(say People), not even through a link such as "who to call if the car breaks down". It cannot tell a part it was not
given from one that does not exist. Text a helper writes is shown on Review as the helper's own words, and text with
hidden or back-to-front characters, or something that looks like a helper key, is refused before it is kept. A helper
that sends too many requests in a minute is asked to wait. Clicking Accept twice still adds the record only once.

## What we chose
- **Hidden links (case 8).** A link column whose target table is not in the helper's granted, switched-on parts is
  invisible to that helper: left out of `/tables` (no `to`, no count), left out of every record, and left out of
  `/attention` (a "gap" question about such a link is not asked, so even whether it is filled in stays hidden).
  Suggesting one is refused with `403 not_allowed` and the same message whatever value is sent; the value is never
  looked up. A table where such a link is required shows `can_suggest: false` with the reason "This table needs a link
  to a part of the records this helper was not given, so it cannot add to it."; suggestions into it are refused (422).
  On Accept the link is checked again: a suggestion kept from before that sets one cannot be added, and its reason does
  not name the hidden part. Review is a person's page, so it may show names.
- **One "not found" (case 20).** A table in a part the helper was not given gets exactly the same `404 not_found` reply
  as a table that does not exist, on reads and on suggestions. The message points to `GET /api/v1/tables`. The helpful
  "<helper> may use: …" sentence now lives only in `/me` (as `message`).
- **Helper text (cases 13 and 22).** Every piece of text in a suggestion (reason, request key, table and field names,
  values) is screened. Characters that are invisible or turn text around are refused with
  `400 hidden_characters`: C0 controls except the newline (so tab and carriage return too), DEL, C1 controls,
  U+202A to U+202E and U+2066 to U+2069. Review labels the reason "<helper> says why:" and the values
  "<helper> suggests adding to …", says they were written by the helper and not by Dashboard Plus, and wraps each piece
  in `<bdi>` so it cannot reorder the text around it. As a second net, any such character already kept is shown as the
  replacement mark (U+FFFD). `why` stays required: 1 to 300 characters after trimming.
- **Keys in text (case 18).** Text matching `dph_` followed by 8 or more key characters is refused with
  `400 looks_like_a_key` and the message "That looks like a helper key. Keys belong only in the Authorization header."
  The text is never repeated, logged or stored. This check runs before every other check of the body.
- **Requests per minute (case 11).** Each helper may make 120 requests in any 60 seconds (a sliding window kept in
  memory). The next one gets `429 too_many_requests`, a plain message and `Retry-After` in seconds. Only requests with
  a good key count. `app.config["HELPER_REQUESTS_PER_MINUTE"]` changes the number; `/me` reports it.
- **One decision (case 16).** Accept and Reject now mark the suggestion decided with one statement that only changes a
  suggestion still waiting, inside the same transaction that adds the record. A second click, a second window or a
  reject at the same moment finds nothing to change and reports "already been decided"; nothing is added twice.

## Why we chose it
- A raw ID, a target table name or a "does it exist" answer from another part is exactly what module scope promised a
  helper would not get (decision 0067). Hiding the column outright is simpler to check than hiding parts of it.
- Two answers for "not yours" and "not there" let a helper map what else the household keeps. One answer costs little:
  `/me` and `/tables` already say what it may use.
- Text from a helper is untrusted. Refusing hidden characters at the door is simpler and safer than trying to show them
  safely everywhere they might later appear (Review, history, sheets, backups).
- A key pasted into a reason would be kept in the database and in every backup. Refusing it costs a helper one retry.
- A household computer should not be slowed by one runaway helper; 120 a minute is far above what a person-paced
  assistant needs.
- Two clicks deciding at once was guarded only by a check before the transaction; doing the check inside it closes the gap.

## What else we considered
- Showing hidden links with their value blanked: still tells the helper the link exists and is filled in. Rejected.
- Keeping 403 for parts not given, as the plan said: friendlier, but reveals which tables exist. Rejected.
- Removing hidden characters silently: the helper would not know its text was changed, and the stored text would no
  longer match what it sent (the retry check compares bodies). Refused instead.
- Warning about a key on Review rather than refusing: the key would already be stored and backed up. Rejected.
- A limit kept in the database, or one per IP address: survives restarts, but adds writes to every read and every
  helper is on this computer anyway. In memory is enough for now.

## What this costs us (the downsides)
- A helper given Vehicles but not People can no longer fill in or even read "roadside contact"; the household must
  tick People too, which gives that helper all of People. There is no per-column grant.
- Tables such as Things lent out (borrower is required and in People) cannot be suggested into unless People is also given.
- A helper debugging a typo in a table name gets the same answer as one asking for a part it was not given; it must
  check `/tables` to tell them apart.
- Tabs, carriage returns and Windows line endings in a note are refused, so a helper must send plain newlines. Left-to-
  right and right-to-left marks (U+200E, U+200F) are still allowed, because real right-to-left writing needs them.
- A note that happens to contain `dph_` followed by eight letters is refused even if it is not a key.
- The per-minute count resets when Dashboard restarts and is not shared between two copies of the program on one
  computer (which is not a supported setup).

## How hard it is to undo
Easy. Each part is a few lines in `core/helpers.py`, `core/proposals.py`, `core/watch.py`, `web/api.py` and
`templates/review.html`, with its own tests; none changes stored data or the database layout.

## We should revisit this if
- Households ask for a helper to fill in links into a part it should not otherwise read (a per-column grant).
- Helpers often hit the per-minute limit during ordinary use, or a helper floods Review with suggestions (a queue cap).
- Someone needs tabs or carriage returns kept in suggested text.
