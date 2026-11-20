# Mark done for a Home care job

Batch 14 item 57, drafted **19 November 2026** against shipped `modules/home_care/`, `docs/DESIGN.md` §5.8 and the Smith, Garcia and Taylor examples. All names and dates below are invented. A repeat is a household choice, never a maintenance recommendation. The dashboard should not say how often gutters, filters or boilers need work.

## From the job page

Show **Mark done** on every live Home care job. Pressing it opens a short form; **nothing is saved yet**. This form is the normal way to record the latest completion. The existing **Add Work done** path remains for an older history entry and continues to leave the job dates alone.

Suggested screen words:

> **Mark “Clean the gutters” done**  
> Record the work and choose when you want a reminder to do it again. Nothing changes until you save.

| Field | Exact words and behavior |
|---|---|
| Date | **Done on**. Prefill today's date in the household's date order; it is editable. Help: “The day the work was finished.” Refuse a future date. For this latest-completion action, refuse a date before the job's current Last done; use Add Work done for older history. |
| Person | **Who did it (optional)**. Start blank even when **Who usually does it** is filled; that person might not have done this job. Choose a People record if known. |
| Note | **What was done (optional)**. Help: “This is saved in Work done. Do not include alarm or access codes.” It is ordinary record text under the shipped module's privacy rules, not a private field. |
| Existing reminder | If set, show **“Current reminder: [date]. Saving will replace it.”** Do not quietly carry it forward after the work is done. |
| Next reminder | Heading **“When do you want to do it again?”** Require one explicit choice: **“Choose a date”** (date field labelled **Do again by**), **“Use [date] from your repeat”** (only if this job has a household-chosen repeat), or **“No date yet — remove the current reminder.”** Show no default choice. Help: “You choose the date. A blank reminder will not be guessed.” |

The action buttons are **Save work done** and **Cancel**. If **Choose a date** is selected, the date is required and must not be before Done on; the same day is allowed. If the chosen date is already past today, explain before saving: **“This date has passed, so the job will appear as overdue.”** Choosing **No date yet** deliberately clears the existing `next_due` and its reminder. Cancel leaves both tables unchanged.

After saving, show: **“Marked done on [date]. Work done was saved. Do again by [date].”** If no next date: **“Marked done on [date]. Work done was saved. No next reminder is set.”** Offer **Undo this completion** while it can safely undo. Keep **Add Work done** visible for older entries, labelled **“Add an older Work done entry (does not change the job dates)”** so its different effect is clear.

## A repeat the household chose

A job may optionally store **Repeat every [1–99] [weeks/months/years]** on its ordinary edit page. It is off by default, and selecting a job kind never chooses a repeat. Explain there: **“After you mark this job done, we will offer one next date. You can change or skip it.”** Changing the rule does not rewrite the current `next_due` or old Work done entries.

On the Mark done form, calculate one offered date from the entered Done on date. Recalculate when that date changes, and recompute on the server before saving. Weeks mean seven calendar days each; months and years use calendar addition, clamping to the last valid day when needed: 31 January + one month is 28 February (29 in a leap year), and 29 February + one year is 28 February. The household must select **Use [date] from your repeat** to take the offer. Choosing another date changes this reminder only; the repeat rule remains for the next completion. The date is a reminder, not a claim that work is safe or due under a manual or law.

## One saved operation, and a way back

One successful **Save work done** must, in one transaction:

1. Add exactly one `home_care.work_done` row linked to the job, with Done on, the optional actual person and note.
2. Set `home_care.jobs.last_done` to Done on and `next_due` to the chosen date or null. Leave **Who usually does it**, the place and the repeat rule unchanged.
3. Write one named completion operation in history, including the prior and new job dates and the new Work done ID. Needs attention and the Home care sheet then read the new dates; neither changes on opening or cancelling the form.

The form carries a one-use operation ID. A double click or identical retry returns the first saved result; it cannot add another Work done row. Check a monotonic job revision under the write lock before creating anything. If another window edited the job, changed its repeat, recorded a later completion or deleted it while the form was open, show **“This job changed while you were marking it done. Check its dates and try again. Nothing was saved.”** Keep the typed note/date for review. Another *new* Mark done form for the same day should warn **“Work done is already recorded for this job on [date]. Add an older Work done entry if you need another note.”** It must not silently duplicate a completion.

**Undo this completion** is available for the latest completion while the job and that Work done entry still have the exact after-values and revisions from this operation. In one transaction it soft-deletes that one Work done row, restores the exact prior `last_done` and `next_due`, and audits the reversal. Do not erase the audit or a backup. If either record has since been edited, another completion was saved, or the job is deleted, refuse automatic Undo: **“This job has changed since that completion. Nothing was undone. Check the job dates and Work done history before changing them.”** Restoring a backup never replays a completion or invents a due date.

## Three invented walk-throughs

| Household | Mark done example | What the person chooses |
|---|---|---|
| Smith (AU) | Clean the gutters, Done on `19/11/26`. | John Smith is chosen as the actual person; a household repeat of three months offers `19/02/27`, which they explicitly select. This is invented test data, not a gutter schedule. |
| Garcia (US) | Air conditioner filter, Done on `11/19/26`. | Carlos Garcia is chosen; the household types `01/15/27` instead of using a repeat. The previous reminder is replaced only on Save. |
| Taylor (UK) | Boiler service, Done on `19/11/26`. | The person chooses **No date yet** while waiting for the letting agent; the old reminder disappears. No provider date is inferred. |

## Current boundary

The shipped `[[tables.*.actions]]` contract in DESIGN §5.8 only sets fields on the **same** record and makes its button go away by changing `show_when`. Home care Mark done adds a Work done record and leaves the job eligible to be done again, so it needs a new atomic core action. [`NOTES.md`](NOTES.md) records that dependency; this document does not ask the household to perform two separate saves as a workaround.
