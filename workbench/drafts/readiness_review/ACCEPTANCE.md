# Acceptance checks for field-level review

Use disposable invented records. For each case, save **Yes** with the named record chosen, a future look-again date, and confirm the question is initially Looked at. Check both the Questions page and Home/Needs attention; review prompts use only generic words there.

1. Change a kit's `last_checked`, `next_check` and notes separately. No review. Change `kept` from home to vehicle, then its place; each change calls for one review after the previous Yes is reconfirmed. A kit with no place is no longer offered.
2. Use one litre from a selected drinking-water batch that still has litres left: no review. Use its last litre: review. Restore a positive amount: do not silently clear the review; the person must choose Yes again. Change item `drinking` to No or unit to packs: review. Add another water lot: no review.
3. Change an alarm's battery date, next check and notes: no review. Change its last-tested date or move its place inside another room: review. Rename an ancestor room: review. Change that room's notes: no review.
4. Change a shut-off's private access details: no review and no private words in any reminder. Change `how_to_find`, its kind or full place path: review. An unrelated meter change does nothing.
5. Change the private text of a selected medication detail: review with no detail on Home, Needs attention, Questions list, helper attention or sheets. Change its person's birthday: no review. Change `lives_here` to No: review, and the record is no longer offered.
6. Repeat case 5 for a dietary detail. Changing only that person's phone does not ask the food question again.
7. Change the chosen care contact's phone or role from doctor to neighbour: review. Change email only: no review. Changing `priority` asks again; editing another doctor's priority does not.
8. Repeat case 7 for an emergency contact. Delete the chosen Who to call row while another emergency contact exists: review and require an explicit new choice.
9. For each of the eight, Not yet, Not relevant and Yes without a record follow only the chosen date; new matching records do not silently rewrite those answers. A selected Yes also returns on its date if its record did not change.
10. After multiple relevant edits before a person returns, show one review, not a counter. Undoing an edit to its old value does not silently revalidate an answer once review was raised. An unrelated edit during that time does not clear it.
11. On upgrading from the shipped revision fingerprint, preserve every already-due or already-changed review. For an unchanged chosen record, initialize the field check without inventing a review. No answer date, history entry or chosen record changes during this migration.
12. The same result holds after save, restart, restore and a paired-computer sync. A private-field change is detected without writing its value or a guessable digest into a public answer, helper response, sheet, export or sync metadata. A deleted link or disabled module remains review-needed until the person answers again.
