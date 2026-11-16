# A helper may suggest; a person decides

Drafted 17 November 2026 for M2. The roadmap says to use DESIGN 7; in the current numbered design, section 7 covers migrations and the relevant helper contract is in [sections 8 and 9](../../../docs/DESIGN.md). These screens are proposals, not shipped features. All names and rows here are made up.

## Give narrow access

Settings → **Helpers** shows each helper's name, allowed tables, whether it may see private fields, last activity, and **Turn off access**. Adding one first asks: “What may this helper suggest?” Check only specific tables, such as Stock in and out or Pet weights; default all other tables and private fields to off. Show a one-time key and say: “This key lets the helper suggest changes on this computer. Keep it private. You can turn it off here.” A helper connects only while the local app is open; no household data is sent out by the app itself. If a person gives the key to an outside service, explain separately what that service may receive. Revoke access immediately when the person chooses Turn off access.

Allowed proposal: add up to 12 Stock-in lines from Saturday's receipt, with a source line and reason for each. Another helper may suggest a Pet weight entry in a table it was granted. A helper may correct or withdraw **its own unreviewed proposal**. It may read only permitted tables, never private fields without separately granted access. It cannot approve itself, change an approved row, change a person-edited row, silently delete a row, or propose into a table outside its grant. A helper's proposal remains labelled as a proposal until a person accepts it.

## Review queue

Home shows “12 suggestions need a look” linking to **Review**. The queue groups by source and batch, newest first. Example card:

> **Receipt helper: 12 Stock items from Saturday's receipt**  
> Suggested 17 Nov at 10:45 · Why: “Read the paper receipt you added”  
> 10 look ready · 2 need a choice  
> **Review 12 suggestions** / **Reject all 12**

Inside the batch, each row shows original source or note, proposed action and item, old value (if any), new value, quantity and unit, place, and any uncertainty. Wording: “A helper suggested **Tinned tomatoes, 4 tins**. Your Stock currently says **2 tins**. If you accept, it will say **6 tins**.” Keep “suggested by Receipt helper” visible. A helper cannot mark this as confirmed. For each row: **Accept**, **Change then accept**, **Reject**. A batch action may accept only the rows with no outstanding choices, after showing the full count and result. A rejected row is hidden from ordinary lists but remains in history; it never changes Stock. Exact confirmation: “Accepted 10, changed 1, rejected 1. Stock changed only for the 11 accepted rows.”

When the household says no, show “Rejected. Nothing was added to Stock.” Give an optional reason: Wrong item, Wrong amount, Already recorded, Other; do not require an explanation. Rejected proposals must not reappear merely because the helper retries the same request key. A new proposal for the same receipt should be marked as a possible duplicate.

## Protect a person's edit

Suppose a person changes a Stock item from 2 to 3 tins while its helper proposal is waiting. On opening Review, show both the new 3 and the proposed 4 added tins; recalculate the projected result as 7, or ask the person to recheck if the proposal was an absolute value. Do not apply a stale before-value. Once a person edits or accepts a row, set its person-edited lock. If the helper later sends an amendment or withdrawal for that row, refuse it and leave the person's version intact. Exact helper-facing response: “This row was already reviewed or edited by a person. It cannot be changed by this helper.” The queue says: “This suggestion changed since you opened it. Review the latest values before accepting.”

For an entire helper batch, **Undo accepted batch** is a person-only action, audited and preceded by a conflict check. If someone later edited one accepted row, show which row conflicts; do not erase their edit to make the batch disappear. Revoking a helper key prevents new API calls but does not delete the review history or accepted records.

## References

- [Dashboard Plus design, sections 8 and 9](../../../docs/DESIGN.md), checked 17 November 2026: review statuses, API grants, sensitive-field rule, limits, request key and person-edit lock. This is the product's own proposed contract, not a claim that those routes ship today.
- [Receipt-entry draft](../receipt_entry/FLOW.md), checked 17 November 2026: the household receipt example is a proposal source; receipt content and numbers are invented.
