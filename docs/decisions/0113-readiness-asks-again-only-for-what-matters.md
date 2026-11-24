# 0113. Readiness asks again only for what matters: field-level "ask again" rules with a versioned field stamp; This year fits a 320px phone

- **Status:** Accepted
- **Date:** 2026-11-22
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0104 (Readiness questions), 0108 (Think it through drills), 0100 (permanent IDs, history, change log), 0107 (Things to do), Lane B's `workbench/drafts/readiness_review/` (batch 21 item 100, now removed; in git history) and report `workbench/reports/2026-11-21-routine-checklists-ux.md` (batch 21 item 98)
- **Narrows:** the "ask again on any change" rule of 0104 (point 6) and 0108 (a chosen record that changed asks for the step again). Everything else in those decisions stands.

## In plain words
When you answered **Yes** and picked one of your records (a first aid kit, a water batch, a doctor), the
question used to come back after *any* edit to that record, even ticking the kit's last-checked date or using
one litre of water. Now it comes back only when something the question is about changes: where the kit is
kept, the water batch running out, the doctor's phone number. It still comes back on the date you chose, when
the record is deleted, when it no longer fits, or when its part of the program is switched off. Things to do,
This year now fits a 320px phone: each month is one line of labelled numbers.

## What we chose
1. **Each record-backed question says what matters, in `prompts.toml`.** Schema 3 adds `ask_again` beside
   every `match`: `fields` (compared by value) and `states` (compared only by whether they still meet the
   match: a positive amount, a unit of the listed kind). It is checked when the module loads: every field the
   match reads must be listed, a linked field needs its link listed, a state must be a `where` or `positive`
   field, every path must exist (one link deep) and a several-records link is refused. A link field also covers
   the record it reaches; a link to a nested place covers every place around it (each one's name and what it
   sits inside, never its notes). Schema 1 and 2 files still load and ask again for whatever their match reads.
   The core stays generic: it knows nothing about kits or water.
2. **Lane B's exact rules for all eight questions** (`fire-alarm-location`, `flood-flood-utilities`,
   `heat-heat-water`, `medical-kit-location`, `medical-prescriptions`, `medical-care-contact`,
   `medical-special-food`, `leaving-contact-away`), and the same style for the 17 drill steps that point at
   records (a shared step uses its question's rule). Examples: a kit asks again for `name`, `kept`, `place`
   (and the place path), never `last_checked`, `next_check`, its checks or notes; drinking water asks again for
   the lot's `item` and `place`, the item's `category`, `drinking` and `name`, and only the *states* of
   `quantity` (crossing zero) and `item.unit` (still litres); a contact asks again for `role`, `person`,
   `priority` and the person's `name` and `phone`, never email, birthday, address or notes.
3. **A versioned field stamp replaces the revision fingerprint.** The check kept with an answer is now
   `2:` and a hash of: permanent IDs, and for each listed field *how many times its value really changed* in the
   record's own history (and how often each record was deleted). For a state, the count is of times it flipped
   (positive to empty and back). Counts only ever go up, so undoing an edit, putting water back, or restoring a
   deleted record never silently clears a review: the person must answer again. Several edits while nobody looks
   still give one review. No value, private or not, and no digest of a value is in the stamp; the history it is
   counted from stays on this computer as before.
4. **Module switched off.** Before Settings switches a module off, any answer (or drill step) kept with a
   record that module holds or reads through is marked `2:module-off` (a history entry by "system"), so it
   keeps asking once the module is back until a person answers. While the module is off it shows as "The record
   you used for this answer is no longer available." (a new generic reason, also used for a deleted record or one
   that no longer matches); a change shows the existing "changed" sentence. Neither ever names what the record says.
5. **Upgrade.** At start-up and after a restore, every answer and drill step still kept with 0104's revision
   fingerprint is compared with that old fingerprint first. Only one whose record still matches and whose
   fingerprint still fits gets a field stamp, written straight in place: no answer, date, chosen record, history
   entry or change-log line changes, and nobody is asked again. One that had already changed, was deleted, no
   longer matches or whose module is off keeps its old check and stays in Review again. A paired computer (sync
   stage 2) will run the same step on its own copy.
6. **This year at 320px.** Below 30rem the month summary turns each month into one row: the month name, then
   "Due: 2  Done: 1  Skipped: 0", with the column names as visible labels (the header row stays for screen
   readers). The browser check now opens `/to-do/year` at 320px and fails if the page is wider than 320px, if
   it does not list twelve months or if the numbers are unlabelled.

## Why we chose it
- User 1 worried that questions coming back after any small edit would feel chatty; Lane B named exactly which
  edits matter for each question, and these rules follow them word for word.
- Counting changes in history needs no new table and no copy of any value; a hash of counts and IDs reveals
  nothing a guess could recover, unlike a hash of a short medicine name.
- Counts that only rise make "review once raised stays until answered" automatic, without writing on every page view.

## What else we considered
- **A hash of the field values.** Simplest, but a short private detail could be recovered by guessing, and
  restoring an old value would silently clear a review. Rejected (the draft forbids it).
- **A salted hash of the values.** Hides the text, but the salt would have to travel with the answers and the
  restore problem remains.
- **Per-field revision columns on every table.** Would need a migration of every module's tables.
- **A horizontally scrolling month table.** Works, but scroll regions are easy to miss on a phone; labelled rows read in order.

## What this costs us (the downsides)
- The stamp is counted from this computer's history. A change made outside the program's write path (a module
  migration that updates rows directly) is not seen; sync stage 2 must carry field changes in its log or rerun
  the upgrade rule, or a paired computer could ask again once.
- An answer marked when its module was switched off asks again even if nothing changed meanwhile, as the
  draft wanted; the mark is a "system" history entry on the answer.
- The stamp reveals, to someone with the database, roughly how often a listed field was edited (metadata, never content).
- Each question page reads the history of the records it offers; fine for a household, slower for a huge one.
- New questions need an `ask_again` list someone has thought about; a missing one stops the module loading.

## How hard it is to undo
Easy to Medium. Remove `ask_again` and set `schema = 2`: the default rule asks again for whatever the match
reads. Going back to whole-record revisions means restoring the old fingerprint in `questions.candidates`;
stamped answers would then each ask once. The 320px layout is a few CSS lines in `checklist.html`.

## We should revisit this if
- Households say a question did not come back when they expected it to (a field should be added to a list).
- Sync stage 2 is designed: field changes must reach the other computer, or answers will ask once there.
- A new question needs a rule that is not "this field changed" or "still meets the match".
