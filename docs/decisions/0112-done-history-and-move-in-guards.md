# 0112. One-press buttons leave a named history entry with Undo; three move-in traps guarded

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
Pressing a one-press button such as Garden's **Mark done** or Things lent out's **Mark returned** is now
remembered by name. It shows under **Done today**, **Done this week** and **Done this month** on Things to do,
counts in This year's done numbers, and straight afterwards offers **Undo Mark done** (or **Undo Mark
returned**), as long as nothing has changed since.

Moving records in with a helper is also safer in the three places Lane B found worst. If a helper sends a new
item that already has an amount *and* a Stock in for the same new item, Review says "This would count the
amount twice" on the Stock in, and the helper is told too. If a helper names a place or person instead of
giving its number, the refusal lists the exact full-path matches ("Garage › Shelf 3 (id 5); Kitchen › Pantry ›
Shelf 3 (id 4)") and tells it to ask which is meant. If a suggestion's text contains a private detail the
household already keeps (such as a car's registration), Review says which private field it looks like, without
repeating it.

## What we chose
- **A named press.** `Records.action` (decision 0075) now writes, in the same transaction as the change, one
  `action` history entry like Mark done's (decision 0091): the action's key, a one-use operation number, the
  fields before and after, `one_step: true`, no added record, and `on`, the day it was pressed on the
  household's computer. The page makes the number for each press; a number already used, or not shaped like
  one, is refused and nothing changes. A second press still finds nothing to do (`show_when`), as before.
- **Undo for a press** uses decision 0091's rules exactly: allowed while the record's newest history entry is
  that press (so any later change, a later press or a delete and restore refuses it with the table's own or
  the default words, changing nothing), once only, and only from the notice straight after (on the record's
  page or on Things to do). It puts the set fields back through the ordinary change path and writes an `undo`
  entry. A one-step action may name its Undo words with `undo = "..."` in `tables.toml` (and reword them in
  `labels.toml`); without them the button says **Undo**. Garden says **Undo Mark done**, Things lent out
  **Undo Mark returned**.
- **Things to do** reads these entries the same way as Mark done's, dated by `on`; undone presses and deleted
  records are left out. No module is named in the code: any `[[tables.<t>.actions]]` button on a table with a
  due date takes part. History reads "used Mark returned" and "undid Mark returned".
- **Counted twice** (`src/dashboard/core/move_in.py`, `count_twice`): a Stock in (a movement that adds, with
  `belongs_to`) whose item is `{"ref": N}` to a new item in the same send that carries a starting amount
  (decision 0102). It is **not refused**: two on hand and one more bought that day is real, and an existing test
  relies on it. Instead the send's answer (and `GET /api/v1/batches/{id}`) carries `warnings` with code
  `may_count_twice` and a plain message, and Review shows the message on the Stock in and a line in the Accept
  all confirmation ("1 Stock in below may count a new item's starting amount twice: check it first"). The same
  amount says "This would count the amount twice ... reject this Stock in and accept only the new item"; a
  different amount says "Check the amount". The warning is worked out from the stored rows each time, so a
  retry gets the same answer, and it goes once the Stock in is rejected.
- **A name instead of an id** (`name_hint`): a link sent as text is still refused (422 `invalid`, all or
  nothing), and the message now names every record in the linked list whose full path ends with what was
  typed (case and the separators `›`, `>` and `/` do not matter), with its id: one match says "Send its id";
  several say they are different records and to ask the household; none says not to guess. Only lists the
  helper may already read are searched, using their public name field.
- **Private details in ordinary text** (`private_values`, `private_copies`): when Review is opened, the
  household's own private text values of five or more letters and digits are compared in memory with each
  waiting suggestion's text, its receipt line and its why, ignoring case, spaces and punctuation. A match shows
  "This may hold a private detail you keep in Vehicles (Registration or plate number). ... Reject this, or
  accept it and then remove that text." The value is never repeated, stored, logged or put in a helper's
  answer.
- **Guide and connector words** (the starting message, `GET /api/v1/guide`, the connector's tool
  descriptions and `openapi-v1.json`, each held by its tests): a helper can only add, never correct; match by
  full path, never by name; stop and ask when a needed list is not granted; never guess an either-way date, a
  drinking-water answer or a unit conversion; keep codes, account, card and registration numbers and private
  medical details out of names, notes, why and receipt lines; read the answer's warnings; when a helper may
  suggest into nested places and connections, a shelf inside a room is not a door and connections are never
  invented; and report sent, accepted and waiting from `GET /api/v1/batches`, never "the move is done".

## Why we chose it
- Decision 0107 left this open: Garden and loan presses vanished from the list with no Done line, no count and
  no Undo. Reusing 0091's operation entry means one set of rules for every kind of action.
- Lane B's read-through (batch 20 item 94) ranked a doubled Stock count, a wrong same-name link and private
  facts in notes as the three worst move-in mistakes left after the starting message. Each check here follows
  its suggested gate: a warning for the doubled count (the draft's own wording), exact full-path matches, and
  the guide sentence.
- Warnings rather than refusals keep real cases working and leave the decision with the household on Review.

## What else we considered
- **Refusing a new item with an amount plus a Stock in for it.** Rejected: it breaks a real purchase on the day
  of counting, and a refusal teaches the helper to split them across sends, where nothing would warn.
- **Holding Accept all for a batch with a possible double count**, like a repeated receipt (0105). Not now:
  the warning sits on the row and in the confirmation, and rejecting the Stock in alone keeps the item.
- **Guessing the link from a name when only one matches.** Rejected: the draft says never auto-merge by name;
  the helper sends the id after looking.
- **Telling the helper about private text in its answer.** Rejected: it would let a helper test guesses of a
  private value. Review alone shows it.
- **A warning whenever text mentions a private field's label** ("registration"). Rejected as noisy and not in
  the draft; comparing with the household's own values is quieter and catches the actual copy.

## What this costs us (the downsides)
- Every one-press button now writes two history entries (the change and the named press), so history lists
  grow a little faster, and a test that read the last entry had to look one further back.
- Undo for a press is only offered straight after it, as for Mark done; later, changes are made by editing.
- The private comparison only catches a value copied whole (spacing and punctuation aside) and only private
  text of five letters or digits or more, so a short code or a reworded medical note is missed; and a private
  value that is an ordinary phrase ("Spare key") can flag an innocent note. It reads every private text field
  each time Review is opened with something waiting, which is fine for a household and would want caching at
  a much larger size.
- The name matching reads up to 5,000 records of the linked list on a refused send only.
- The double-count check knows the stock shape (`total.starts_from` and `adjusts.belongs_to`); a different
  "starts with an amount" design would need its own check.
- `warnings` is a new optional field in two replies; a helper that ignores it misses the message, which is
  why the guide and the connector say to read it. The Lane B draft stays in `workbench/` until Lane B moves
  it; its checklist has no natural home in the shipped docs yet.

## How hard it is to undo
Easy to Medium. Removing the named entry means deleting its `_audit` call in `Records.action` and the
one-step branches in `actions.py`, `checklist.py` and `action_form.py`; old entries would then show as plain
history lines, and Things to do would stop counting presses. The move-in checks are one file
(`core/move_in.py`) plus their calls in `proposals.py` and `review.py`; removing them changes no stored data.
The `undo` words in Garden and Things lent out would have to go with the loader change.

## We should revisit this if
- Households ask to undo a press later than straight after it.
- Helpers keep sending names instead of ids despite the refusal, or the private warning flags innocent notes
  often enough to be ignored.
- A module other than Household stock gives new records a starting amount.
