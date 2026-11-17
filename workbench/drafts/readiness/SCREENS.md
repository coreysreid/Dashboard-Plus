# Readiness questions on screen

Drafted 17 November 2026 for M3 / J6. The 49 questions in `prompts.toml` are editorial content, not live screens. Their `answered_by` fields and exact matching limits are in [NOTES.md](NOTES.md). These screens ask what a household has considered; they never certify a plan or imply that a missing record means the household has no plan.

## Home and coverage

Home shows at most two calm cards at a time under **Have you thought about…?** Each card includes the exact question, a one-sentence reason, and **Look at this** / **Not now**. No red warning or “unsafe” label. “Not now” defers the card without recording an answer. The full **Questions** page offers groups (Fire, Flood, Storm, Heat, Power, Medical, Leaving) and a coverage line such as **“23 of 49 questions looked at”** only when all 49 apply. If household settings make 14 inapplicable, use **“23 of 35 questions that fit your household looked at”** and “14 do not fit the settings you gave.” The count is not a readiness score. Exact caption: “Looked at means someone answered a question. It does not say whether your household is safe or ready.”

The numerator counts applicable prompt IDs with a current, person-selected **Yes**, **Not relevant** or **Not yet** response. **Tell me more** opens detail but is not an answer and does not increment it. An unanswered or snoozed card is never counted simply because it was seen. A dated prior answer whose review is due moves to **Review again**; keep its original answer in history, but remove it from the current numerator until reviewed. A prompt decisively excluded by profile settings is not silently recorded as a person saying Not relevant; the view distinguishes “does not fit settings” from an explicit answer.

## One question

The question page shows the original wording, why it matters, the linked official source and date checked, and the group. Under it are four actions, with these exact labels:

1. **Yes** — “We have thought about this.” Save the date, optional note and any person-confirmed linked record. Do not infer this answer from a record.
2. **Not relevant** — “This does not fit our household.” Ask for an optional reason and save the answer. Keep an edit path if the household changes.
3. **Not yet** — “Remind us later.” Ask when to bring it back, offering the household's review interval as a suggestion rather than a safety deadline. Save the answer date and reminder date. It counts as looked at, but the card may still return when due.
4. **Tell me more** — expand `why`, how to check with a local authority, source title/link and date checked. Leave the answer unset and keep the four actions visible. No external page is opened without a person choosing the link.

For `fire-upper-floor`, a Smith household with two storeys sees: “If the stairs were blocked, have you thought about how everyone upstairs would leave?” If `home_layout.homes.upstairs_way_out` is nonblank, show “You recorded a way out for upstairs. Does it answer this question?” with **Open this record**. Do not auto-select Yes. If no record is present, the same four actions remain; an optional **Record a plan** link may open the relevant form. A future source review may change the guidance; keep the source date distinct from the date the household answered.

For `medical-prescriptions`, any candidate from private People details is shown only as “You have a private record that may relate to this question.” Link to it behind the normal reveal control; never quote its content on Home, in a notification, or on a shared printout. For `heat-heat-water`, a match requires a positive amount in litres, Safe to drink ticked and a linked full-path place. A Water-category item by itself is not an answer.

## Return and change

On answer, say “Saved your answer. You can change it later.” The Questions page has filters **To look at**, **Looked at**, **Review again**, **Not relevant**, and **Does not fit settings**. A person can reopen any answer and see who answered, when, the linked record, and its previous answers. If the linked record changes or is removed, show: “The record you used for this answer changed. Does your answer still fit?” Do not erase the old answer or present the record's contents in the reminder. The prompt returns at the household-selected review date or after a linked-record change; do not create a new Yes automatically.

## References

- [Dashboard Plus design section 10.5](../../../docs/DESIGN.md) and [J6](../../../docs/JOURNEYS.md), checked 17 November 2026: question budget, four actions, coverage language and review behavior.
- The official sources and source dates for the **content** of all 49 prompts are recorded per question in [prompts.toml](prompts.toml), with licence notes in [NOTES.md](NOTES.md). The screen must display the relevant source, not an uncited instruction.
