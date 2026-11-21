# 0101. Faster Review: Accept all by group, ticked rows, keys, buttons that never move, and "Allow 200 more today"

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Corey chose all five changes after moving a household in with a helper; the technical choices are Claude's (delegated by Corey)
- **Refines:** 0068 (suggestions wait until a person accepts), 0085 (Review queue cap), 0088 (limits under the write lock), 0097 (grouped suggestions)

## In plain words
Review is quicker when a helper sends a lot. Each send has "Accept all N", which first says how many records it
will add and to which lists, then adds them. Rows can be ticked and accepted or rejected together. On a keyboard,
Up and Down (or J and K) move a highlight, A accepts, R rejects and Space ticks. Accept and Reject now sit in the
same place on every row, so your hand does not have to chase them; rows that go together are shown with a coloured
band labelled "Added together". And when a helper has used (or nearly used) its 200 suggestions for the day, you can
press "Allow 200 more today" for that helper, on Review or in Settings, Helpers, as often as you need. Tomorrow its
limit is 200 again. A helper can never press it itself.

## What we chose
- **Accept all by group.** "Accept all N" opens a check (a fold-out box, no script needed) that names the count and
  the lists ("1 to Stock items and 2 to Stock in and out") with "Yes, accept all N". It then accepts group by group,
  earliest first. A group (rows that point at each other with `{"ref": N}`, decision 0097) is one transaction: if
  any row of it cannot be added, nothing in that group is; the reason is kept on that row, and the others say they
  wait for it. Other groups still go in. Previously each row went separately, so a new item could be added even when
  its Stock in failed.
- **Ticked rows.** Every row has a tick box. "Accept ticked" and "Reject ticked" sit in a bar that stays at the
  bottom of the screen. Ticking one row of a group ticks the whole group, in the page and again on the server, so
  the result is the same without the script. Each group is still all or nothing. These forms use the page's own
  token, like every Review button.
- **Keys** are a small script on the page (no outside files). The hint is shown only when the script runs, so it
  never promises keys that do not work. Keys are ignored while typing in a field and when Ctrl, Alt or Cmd is held.
  Every button works without the script.
- **Fixed buttons.** Every row is three columns: tick, what it adds, and Accept and Reject in a fixed-width column at
  the right edge. A group is a coloured left band and an "Added together" label, never an indent of the buttons. At
  phone width the column narrows and the two buttons stack, still in the same place on every row. A row that cannot
  be accepted (its part is switched off) keeps a greyed-out Accept so Reject does not move. The browser check
  measures this at 1280 and 375 pixels wide.
- **Allow 200 more today.** A new core table, `core__helper_allowances` (core migration 0008), gets one row per
  press: helper, day, 200, when and by whom; the history (`core__audit`, action `helper_allow_more`) says so too.
  Today's limit is 200 plus that day's rows. The button shows on Review (a card above the suggestions) and beside
  the helper in Settings, Helpers, when it has fewer than 50 left today (less than one full request). Each button
  carries a one-use token bound to that helper (like 0093), so a double click adds 200 once; a fresh page gives a
  fresh button. The helper API has no route for it, and a helper's key opens no page (0067).
- **The day.** The daily limit now counts the household's own calendar day (this computer's clock), and the
  allowance uses that same day. Before, the limit counted from midnight UTC.
- **Limits under the lock.** Today's limit, allowance included, is read again inside `BEGIN IMMEDIATE` with the
  count (0088). The Review queue cap stays 500.
- **The refusal.** 429 `daily_limit` now says, for example: "This helper has used all 200 of its suggestions for
  today, so nothing was saved. Stop sending now and ask the household: they can allow more on the Review page in
  Dashboard Plus ("Allow 200 more today"). Otherwise, try again tomorrow." `GET /me` reports today's raised limit.
  The OpenAPI file says the same.

## Why we chose it
- Moving a household in with a helper means hundreds of rows. Clicking each one, with buttons that jump between
  single and grouped rows, made Review the slow part.
- All-or-nothing groups keep the promise of 0097: a Stock in is never added without its item, and an item is not
  left behind half done when its Stock in fails.
- A raised limit for one day only keeps the cap's purpose (a runaway helper cannot flood Review) while letting a
  person who is watching say "keep going". Telling the helper to stop and ask puts the person in charge.
- The household's own day is what "today" means to Corey; UTC midnight falls in the middle of the day in some places.

## What else we considered
- A separate confirmation page for Accept all: one more page load; the fold-out box works without a script too.
- A Settings choice for the daily limit: a permanent change is easier to forget than "200 more, today".
- Letting a helper ask for more through the API: it would let a helper talk itself past the cap.
- Keeping UTC days: the limit and the button would disagree about when "today" ends.

## What this costs us (the downsides)
- Accept all can now leave a good row (a new item) waiting because a row grouped with it failed. Review says why on
  each row, but it is one more thing to read.
- A person in a hurry can press "Allow 200 more today" several times and let a misbehaving helper send a lot; the
  500 Review queue cap still bounds what waits at once.
- Changing the day boundary from UTC to local means the day a household upgrades, its helpers' count for "today"
  may shift by a few hours once.
- Keys can surprise someone who presses A or R by chance on Review; nothing is added or removed except the
  highlighted row, and it shows on the page.
- One more core table and migration (0008), and a script on the Review page to keep working.

## How hard it is to undo
Easy to medium. The keys script and tick boxes can be removed from `review.html`; `accept_batch` can go back to row
by row. To drop the allowance, remove the button and the route and read the limit as 200 again; the table can stay
empty. Going back to UTC days is one line in `proposals.today`.

## We should revisit this if
- People press Allow more many times a day: the standard limit may be too low, or a helper is misbehaving.
- People accept rows by key by mistake (then ask before A, or drop the single-letter keys).
- Accept all leaves groups waiting often enough that people want "add the rest of this group anyway".
