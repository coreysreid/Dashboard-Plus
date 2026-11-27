# 0140. What your other computers get: a household sharing choice for every list and detail

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** User 1 (the rule: consent based, safe defaults); Claude (the technical shape, delegated)
- **Builds on:** 0089 (household sync direction), 0100 (sync stage 1: the change log and `travels`), 0111 (quotes), 0120, 0121 and 0123 (private lists), 0128 and 0133 (prices and money back), 0082 (helpers' own permissions)

## In plain words
Settings has a new page, **What your other computers get**. It lists every list,
part by part, and every detail inside it, and lets the household choose for each:
**Shared with your other computers** or **Only on this computer** (and, for a
list with private details, **Shared, but not the amount** or **Shared, but not
the private details**). Until you choose, everything stays exactly as before,
except that Money back now starts as Only on this computer. Keeping something
here happens at once. Starting to share something private asks first, says in
plain words what will start going, and can be undone. Codes and access details
are never shared. Nothing is sent anywhere yet: computers cannot be paired yet.

## What User 1 said
Asked whether a second computer should learn that a refund exists, User 1
answered: "Again all the info should have a sharing permission set up."
(docs/BACKLOG.md, 2026-11-27). Then, clarifying the rule:

> "To clarify the data should be consent based. Share whatever between users,
> but don't store sensitive info in the app - passwords and digital copies of ID
> full credit card or bank account details etc. that way there isn't a direct
> security risk for major fraud. Someone see you medication schedule isn't ideal
> but is far less bad than getting all your legal docs and passwords."

So sharing is consent based: every kind of information the app keeps may be
shared between the household's computers once the household chooses to,
medical details, doses, prices and money back included. Private things keep
their safe defaults and need a confirmation to start travelling. The only things
that can never be shared are things that work like passwords; keeping passwords,
ID copies and full card or bank numbers out of the app altogether is a separate
decision (0141).

## What we chose
1. **Choices, stored only where they differ** (core migration 0011,
   `core__sharing_choices`): one row per list (`column_name = ''`) or detail
   with the household's choice. No row means the module's own rule from
   `tables.toml` (decision 0100), so a household that never opens the page has
   exactly the change log it had. Choosing the usual rule again deletes the row.
   Only table and column names and a choice word are kept, never a value.
2. **The choices** (`src/dashboard/core/sync_sharing.py`, no module named in it):
   - a list: `shared`, `shared_not_private` (offered only where the list has
     private details; worded "Shared, but not the amount" where one of them is
     money) or `local`;
   - a detail: `shared` or `local`; a detail whose module shares it only for
     some kinds (`travels_when`, an Important detail) offers `kinds` ("Shared
     only for allergy, condition, medication, ...") or `local`, never every
     kind, so access instructions stay here;
   - a detail is shared only while its list is, and "but not the private
     details" keeps every private detail here whatever its own choice says.
3. **Defaults are the module rules.** `travels = "always"` starts Shared,
   `"never"` starts Only on this computer, `travels_when` starts Shared only for
   those kinds. New in `tables.toml`:
   - **a whole list can start kept here**: `travels = "never"` on a table. Money
     back (`stock.refunds`) now says so, the option User 1 was recommended:
     another computer does not even learn that money came back until the
     household chooses. This is the one change to today's change log.
   - **a detail can be fixed**: `travels_fixed = "<reason>"`, only with
     `travels = "never"`. It shows as "always only on this computer" with the
     reason and cannot be chosen. Only Home layout's four "Codes or access
     details" say so ("Codes and access details work like passwords, so they
     never leave the computer where they were typed."). A private column whose
     module has not said whether it travels (decision 0100's unreviewed columns)
     is fixed too, with that reason. Nothing is fixed just because it is
     private: prices, money back, doses, medical details, account references,
     registration and notes are all choosable.
4. **Enforced where the change log is written.** `sync.record` asks
   `sharing.rules` for the list's rules and projects each value through them
   (`Rules.allows`); a withheld value is listed by name only, as before. A list
   Only on this computer writes **no line at all** (no record line, no pair
   line, no revision step); a value typed under a kind that stays here is still
   held (`core__sync_held`) in case the list is shared later. `sync.snapshot`
   (the first full copy) uses the same rules and leaves such a list out.
5. **Keeping here is immediate and cleans what is waiting.** A tighter choice is
   saved at once and, in the same transaction, `sharing.scrub` cleans the change
   log: every line of a list now kept here is removed, and a detail now kept here
   is moved from `patch` to `withheld`. Stage 1 has sent nothing, so every line
   is "waiting"; `scrub` takes the sequence number a later stage has sent up to,
   so it never pretends to recall what has left.
6. **Sharing more counts from now on, and private things ask first.** A looser
   choice changes only future lines: an earlier change is not added to the log.
   If what would start travelling includes a private detail, a list of private
   history (decision 0120), or a list with private details starting to be shared
   at all, the page shows **Start sharing these private things?**, listing list
   by list what will start going ("Money back: that its records exist, Which
   Stock in, Day"), that anyone on those computers will see them and that a copy
   cannot be taken back, with **Yes, start sharing these** and **Go back without
   sharing**. The confirmation carries what each choice was when it was shown; if
   it changed meanwhile, nothing changes. Sharing a non-private detail again
   needs no confirmation. A page that mixes both saves the keeping-here part at
   once and asks about the rest.
7. **History and Undo.** Every save is one line in `core__audit`
   (`table_name = core__sharing_choices`, `record_id = 0`, before and after
   choices only, `sharing_choice` or `sharing_undo`). The page lists them under
   **Earlier sharing choices**; a choice that shared more has **Undo** while every
   choice it made is still as it left them. Undo puts the earlier choices back
   (a tightening, so at once, and it cleans the waiting log again).
8. **The page** (`/settings/sharing`, `src/dashboard/web/sharing_page.py`):
   grouped by part of the program, one card per list with its choice and its
   usual rule, the list's details folded in a `<details>`, private details
   marked "(private)", fixed details with their reason. It says plainly that
   nothing is sent yet ("when your computers are paired"), that choices count
   from now on, that what another computer already has is not taken back, and
   that the first full copy at pairing follows the choices then. One line points
   to **Settings, Helpers**: helper keys keep their own tick boxes (0082); the two
   permissions are separate. Plain HTML forms and radio buttons: no script, no
   inline style, nothing wider than a 320px phone (checked in
   `tools/browser_check.js`'s width sweep). Every POST needs the page token.

## Why we chose it
- It is what User 1 asked for: consent based sharing for every kind of
  information, with the household, not the module author, deciding.
- Enforcing it where the change log is written keeps 0100's promise: something
  kept here is never stored in anything that could be sent.
- Storing only differences makes "nothing changes until you choose" true by
  construction, and a module that later tightens its rule tightens it for every
  household that did not choose otherwise.
- Cleaning waiting lines on a tighter choice means the choice protects what was
  typed before it, which is what a person expects from "Only on this computer".

## What else we considered
- **Making every loosening ask first:** safer-sounding but noisy for ordinary
  lists; User 1 asked for confirmation for private things.
- **A third "share every kind" choice for Important details:** it would send
  access instructions, which are like codes. Left out.
- **Fixing every private column** as never travels: User 1 said sharing is
  consent based; only password-like codes are fixed.
- **Recalling lines on Undo of sharing more:** there is nothing to recall yet;
  in stage 2, Undo can only stop future changes, and the page already says so.
- **Rewriting the log on a looser choice** (adding earlier values): that would
  share the past without a change; the first full copy at pairing does that,
  openly, following the choices then.
- **Merging with helper permissions:** helpers are programs with keys, other
  computers are the household's own; different questions, kept apart.

## What this costs us (the downsides)
- Every record change reads the list's choices (one small indexed query).
- A list kept here and later shared again has records whose revisions did not
  move while it was kept here, so a paired computer cannot rebuild them from the
  log alone: stage 2 must send such a list's records from a full copy when it is
  shared again (the history line says when).
- Links from a shared list to a record of a list kept here still name that
  record's permanent ID (random, it reveals nothing); stage 2 must treat it as a
  link to a record it was not given.
- Money back now writes nothing to the change log by default; a household that
  wants it on its other computers must choose and confirm.
- The page is long for a household with every module on; lists are folded but
  it is still one page.

## How hard it is to undo
Easy while nothing is paired: drop `core__sharing_choices`, remove the call in
`sync.record`/`sync.snapshot` and the page; the change log goes back to the
module rules (Money back's `travels = "never"` on the table can stay or go).
History lines stay as harmless local history.

## We should revisit this if
- Households want a choice per person or per computer rather than per household.
- Stage 2 is built: then the "sent up to" mark must feed `scrub`, and pairing
  must show these choices before the first copy.
- Decision 0141 removes the codes columns, making `travels_fixed` unused.
