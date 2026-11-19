# 0075. One-step actions (Mark returned) and a date order rule

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
A record's page can now have a one-press button for a common change. On a
loan still out, **Mark returned** sets "Is it back?" to Yes and Returned on to
today, and the page says "Marked as returned today." The button only shows
while the loan is out, so pressing it twice changes nothing. Separately, a date
can be kept from coming before another one: Returned on can't be before Lent
on, and the form says so in those words.

## What we chose
- **`actions` in `tables.toml`.** A table may declare buttons:

  ```toml
  [[tables.loans.actions]]
  key = "returned"
  label = "Mark returned"
  show_when = { status = "out" }
  set = { status = "returned", returned_on = "today" }
  done = "Marked as returned today. If it came back on another day, change Returned on below."
  ```

  All five settings are needed. `show_when` uses the same equality filters as
  `where` elsewhere (choices must be real choices; yes/no is true or false).
  `set` fills in fixed values; `"today"` (date) and `"now"` (date and time)
  mean the date or time on the household's computer, exactly as `default =
  "today"` already does.
- **Checked when the module loads**, with plain messages, as every other
  declaration is. Refused: an unknown column (with "Did you mean"), a private
  column in `set` or in `show_when`, a column worked out from other records (an
  item's total or earliest use-by from its batches, or a batch's amount changed
  by stock in and out), a choice that is not one of the column's choices, a
  value of the wrong kind, links and files, a `set` that does not change a
  `show_when` column (so the button always goes away once pressed), and a `set`
  that makes a `required_when` field necessary without filling it in.
- **Words can be changed in `labels.toml`**:
  `actions.returned = { label = "Back now", done = "Marked as back." }`. Only
  declared actions may be reworded; unknown settings are reported.
- **On the record's page only**, as a row of buttons above the form; not on the
  list. Each button is its own small POST form with the page's token, like
  Delete and Restore. The address is `/t/<table>/<id>/do/<key>`.
- **Saved through the ordinary change path**, in one transaction: the same
  value checks, `required_when`, the new date order rule, history ("You
  changed: Is it back? from “No, still out” to “Yes, returned”"), batches and
  totals. After saving, the page reloads with the `done` words as a notice
  (the address carries only the action's key, never the words).
- **Refused, with nothing changed**, if the record no longer matches
  `show_when` (a double click, or a page left open after someone else changed
  it): "That was already done, or the record changed since this page was
  opened. Nothing was changed." Any other refusal (such as the date order
  below) also changes nothing and is shown in plain words at the top of the page.
- **`not_before` on a date column**: `columns.returned_on = { type = "date",
  not_before = "lent_on" }`. On adding, editing and actions, a date earlier
  than the other is refused with "Returned on can't be before Lent on.", using
  the labels from `labels.toml`. The same day is fine; if either date is blank
  there is nothing to compare. Both must be date columns of the same table,
  checked when the module loads.
- **Used straight away** in Things lent out: Mark returned, and Returned on
  not before Lent on.
- **Vegetable garden jobs get Mark done** (added when Garden was switched on
  in the same session, decision 0076): it only ticks "done", which ends the
  job's reminder.
- **Home care gets no button.** Its natural one-press action, "Mark done", must
  add a separate Work done record (and leave the job's dates for the household
  to type, decision 0063). An action that *creates another record* is a
  different and larger feature, so it is out of scope here. No other module
  has a status whose change is a pure field set, so none got a button.

## Why we chose it
- "It came back" is the most common change to a loan, and it took opening
  the form, choosing Yes, typing a date and saving. One press is what a
  household expects, and it was the open item on the Things lent out backlog row.
- Declaring buttons in files keeps modules declarative: no code, the same
  loader checks, the same plain errors.
- Going through the ordinary update means a button can never skip a check or
  leave history out. A second press finds nothing to do instead of saving
  twice or moving a date.
- A date order rule catches a real typing slip (a return dated before the
  loan) that no other check would.

## What else we considered
- **A button on each row of the list.** Quicker for many loans, but the list is
  also a scrolling, page-at-a-time grid; buttons there would need more care
  with focus and confirmation. Left for later if households ask.
- **Actions that run module code.** Not allowed for declarative modules, and
  not needed for setting fields.
- **A general comparison rule** (`after`, `within`, between tables). More than
  any module needs; `not_before` covers the case in front of us and is easy to
  explain in an error.
- **Asking the date in a small box before saving.** Most things come back the
  day you notice; the notice says how to change the date if not.

## What this costs us (the downsides)
- One more section in `tables.toml` for module authors to learn, and one more
  route to keep secure (it uses the same token and local-only checks as every
  other write).
- "Today" is the computer's date. A household whose computer clock or time
  zone is wrong gets the wrong date, as with every `default = "today"`.
- An action can only set fixed values. "Mark done" in Home care, which needs a
  new Work done record, still has to be done by hand.
- The refusal for a second press cannot tell "already done" from "someone else
  changed it"; it says both.
- `not_before` compares two dates of the same record only. A rule across
  records (a service date after the vehicle was bought) would need more work.

## How hard it is to undo
Easy. Remove the `actions` section and `not_before` from Things lent out; the
loader would then refuse them in any other module until the code was removed
too. Nothing new is stored in the database: no migration, no new column.

## We should revisit this if
- Households ask for the button on the list, or for "Mark done" on home care
  jobs (actions that add a record).
- Module drafts start needing `set` values worked out from other fields, or
  date rules across records.
