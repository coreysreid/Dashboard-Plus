# Review and Inbox: exact screen words

Draft checked against [DESIGN section 8](../../../docs/DESIGN.md) on 17 November 2026. These screens do not ship yet. Miso, Pet diary helper, Receipt helper and all quantities below are invented. This wording treats every helper result as a suggestion until a person decides.

## Home and navigation

| State | Exact words and destination |
|---|---|
| 0 suggestions, 0 unsorted items | No Review or Inbox count badge. Home link “Review suggestions”; opening it says “No suggestions to review.” Inbox says “Nothing to sort.” |
| 1 pending suggestion | Home card “1 suggestion needs a look” → Review. Navigation badge `1`. |
| 12 pending suggestions in two batches | Home card “12 suggestions need a look” → Review. Navigation badge `12`. Count rows, not batches, and exclude rejected, accepted and withdrawn rows. |
| 1 unsorted Inbox item | Separate Home card “1 item to sort” → Inbox; never mix its count into Review. |
| Review empty after a decision | “All caught up. New helper suggestions will appear here.” Link “See review history”. |

## Review list and batch

Heading **Review suggestions**. Intro: “Helpers can suggest changes. Nothing is added to your records until you accept it.” Group newest batches first. Batch card: “Pet diary helper · 1 suggestion”; second line “Why: Copied Miso's paper log”; third “Suggested 17 Nov 2026, 10:45”; button **Review suggestion**. For 12 rows, **Review 12 suggestions**. If the helper has been revoked, say “This helper's access is off. Its earlier suggestions still need your decision.” Do not imply a revoked helper can act.

Within the batch, show source and reason above every row. Example: “Pet diary helper suggests a weigh-in for Miso: 17 Nov 2026, 4.3 kg. Your confirmed records will not change until you accept.” For Stock adjustments, show the current value, proposed change, projected new value and place; recalculate if current data changes. Mark unclear fields “Needs your choice” and disable batch accept until resolved. Actions: **Accept**, **Change then accept**, **Reject**. Batch action: **Accept 10 ready suggestions** with confirmation “This will add 10 suggestions to your records. The 2 needing a choice will stay here.” Buttons **Accept 10**, **Go back**. Never silently accept the unresolved two.

## Decisions and exact aftermath

| Action | Confirmation and result |
|---|---|
| Accept | Button **Accept**. Confirmation “Add this weigh-in for Miso: 17 Nov 2026, 4.3 kg?” Buttons **Add weigh-in**, **Go back**. Success “Added to Miso's weigh-ins.” Pending count decreases by one; history says “Accepted by a household member.” |
| Change then accept | Button **Change then accept** opens editable proposed fields, with old and new side by side. Primary button **Save changes and accept**. Confirmation “Add this changed weigh-in for Miso: 17 Nov 2026, 4.2 kg?” Success “Changed and added to Miso's weigh-ins.” History preserves proposal and person's change; pending count falls. |
| Reject | Button **Reject**. Confirmation “Reject this suggestion? Nothing will be added to Weigh-ins.” Optional reason: **Wrong item**, **Wrong amount**, **Already recorded**, **Other**, **No reason**. Buttons **Reject suggestion**, **Go back**. Success “Rejected. Nothing was added to Weigh-ins.” Pending count falls; history retains it, hidden from ordinary record lists. |
| Reject batch | **Reject all 12** asks “Reject all 12 suggestions from Receipt helper? No Stock records will change.” Buttons **Reject 12**, **Go back**. Result “Rejected 12 suggestions. No Stock records changed.” |
| Helper amends pending row | Card says “Pet diary helper changed this suggestion before you reviewed it. Check the new value.” Show old 4.3 kg and new 4.25 kg, with time. Pending count remains one. |
| Helper withdraws pending row | Remove from pending; history “Withdrawn by Pet diary helper before review. No record changed.” |
| Person or target changed during review | “This suggestion changed since you opened it. Review the latest values before accepting.” Button **Show latest suggestion**. Keep it pending; no stale write. |

History filter labels: **Accepted**, **Changed and accepted**, **Rejected**, **Withdrawn**. Each history row names source, batch, why, original values, later changes, person decision and time. Never show a private value to a helper without its private-field grant. Screen readers must hear the changed pending count as a polite status message after each action, while focus returns to the next suggestion or empty state.

## Inbox: sort an unsorted item

Heading **Inbox**. Intro: “Things you saved but have not sorted yet.” Empty: “Nothing to sort. Add a photo or paste a note when you want to keep it for later.” Example card: “Photo added 17 Nov 2026, 09:00”; “Suggested place: a note on Miso's pet record”; “Why: The file name mentions Miso.” Actions **Save as suggested**, **Choose another place**, **Keep in Inbox**, **Discard**. A proposal is labelled “Suggested place”, not “Filed”. Saving: “Saved as a note on Miso's pet record.” Changing: “Choose where this belongs”; show only destinations the person may use, then “Saved to [destination].” Keeping: “Still in Inbox. Nothing was filed.” Discard confirmation: “Discard this Inbox item? The original file or text saved here will be removed.” Success: “Discarded from Inbox.” Review counts and Inbox counts remain separate; a helper-proposed destination needs a person decision and must obey the same private-field permissions as Review.

## Core needs

Implement independent pending counts, batch grouping, person-only decisions, immutable decision history, stale-value checks and focus/status updates. The current grid's `needs_review` field does not provide these screens. Source: [DESIGN sections 8–9](../../../docs/DESIGN.md), checked 17 November 2026; [helper flow](FLOW.md), checked same date.
