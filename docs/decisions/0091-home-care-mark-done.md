# 0091. Home care Mark done: actions that add a record, saved once, with Undo

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
Every Home care job now has a **Mark done** button. It opens a short form:
the day the work was finished (today, already filled in), who did it if you
know, a note, and "When do you want to do it again?", where you choose a
date, the date your own repeat offers, or "No date yet". One press of **Save
work done** records the work, sets Last done and sets the new reminder, all
together. Pressing twice saves once. If the job was changed in another window
while the form was open, nothing is saved and the page says so. Straight
afterwards, **Undo this completion** puts everything back, as long as nothing
else has changed since.

A job can also have a repeat, such as every 3 months. It is off unless the
household sets it, and it only ever *offers* a date; nothing is chosen for you.

## What we chose
- **A new kind of action in `tables.toml`:** an action with `adds` (DESIGN.md
  5.8). It names the linked table it adds to (`work_done`), the link (`job`),
  the fields its small form asks (`done_on`, `done_by`, `notes`) and optional
  fixed `values`. `latest = { date = "done_on", into = "last_done" }` copies the
  asked date onto the job; `next_date = { into = "next_due", question = ...,
  repeat = { count, unit } }` asks for the next date. `title`, `intro`, `undo`,
  per-field `help`, `add_button` (the words for the ordinary add button) and
  three `messages` (stale form, same day, Undo refused) are optional words.
  `show_when` and `set` become optional for this kind.
- **Checked when the module loads**, with plain messages, like every other
  declaration: the added table and link are real; asked fields are public,
  typed in and not the link; every required field is asked, fixed or has a
  default; dates are dates; the repeat's unit only offers weeks, months or
  years; words name only what they can (`{record}` in the title, asked fields
  in `done`, `{date}` in the same-day message); unknown settings are named.
- **One save is one transaction** (`src/dashboard/core/actions.py`): the Work
  done row through the ordinary create path (so a missing or deleted person
  is refused like anywhere else), the job through the ordinary change path
  (history, `not_before`), and one named `action` entry in history with the
  job's dates before and after and the new Work done id. If anything is
  refused, nothing is written.
- **A revision instead of a new column.** A record's revision is the id of its
  newest history entry; every change already writes one, so it only goes up.
  The form carries it; under the write lock a different revision means "This
  job changed while you were marking it done. Check its dates and try again.
  Nothing was saved." and the typed answers stay on the form.
- **A one-use operation number** (random, carried by the form and kept in the
  operation's history entry). The same number sent again, by a double click
  or a retried connection, returns the first result; nothing new is saved.
  The page also refuses a second submit while the first is on its way.
- **Dates:** Done on may not be after today, nor before the job's current Last
  done (older work goes through "Add an older Work done entry (does not change
  the job dates)", which is the existing form and still changes no dates), nor
  a day that already has Work done for the job ("Work done is already recorded
  for this job on 20/11/26. ..."). The next date needs one choice, none
  preselected; a typed date may not be before Done on (the same day is fine);
  a date already past says "This date has passed, so the job will appear as
  overdue." and is kept only on a second Save. **No date yet** clears the
  reminder. Dates are typed and shown the household's way (decision 0052).
- **The repeat:** two new, optional job fields, Repeat every (1 to 99) and
  weeks, months or years, added by migration 0002 with every existing job
  left unset. On the form the repeat offers one date worked out from the
  Done on entered (and again on the server when saving): weeks are 7 days;
  months and years are calendar steps that use the month's last day when the
  day does not exist (31 January + 1 month = 28 February, 29 in a leap year;
  29 February + 1 year = 28 February). A typed date changes only this
  completion; the repeat stays.
- **Undo** is offered on the notice after saving while the job and that Work
  done entry still have exactly the revisions the operation left. In one
  transaction it deletes that Work done entry (kept in history and in the
  deleted list, as every delete is), puts back the exact previous Last done
  and Do again by, and writes an `undo` history entry. Otherwise: "This job has
  changed since that completion. Nothing was undone. Check the job dates and
  Work done history before changing them." A second Undo says it was already
  undone and changes nothing.
- **History** shows "You used Mark done: added Clean the gutters, done
  20/11/26" and "You undid Mark done: removed ...". Restoring the job or a
  backup never repeats a completion: nothing replays history.
- **Screens:** the button is a link to `/t/<table>/<id>/do/<key>` (GET shows the
  form; POST to the same address saves, as for one-step actions); Undo is
  `POST /t/<table>/<id>/undo/<operation>`. The form reuses the ordinary field
  template, so dates, lists of people and help look the same as everywhere.
- **Home care wording** changed where it said logging work done never changes
  dates: Do again by now says "Mark done records the work and lets you choose
  the next date. Adding an older Work done entry changes no job dates." The
  repeat's help says it is the household's own choice, not a maintenance
  schedule. Notes keep the warning against codes and are still not printed.

## Why we chose it
- Decision 0063's downside came true by design: two steps (log the work, then
  edit the job) that a household can half-finish. One save removes that.
- The design (Lane B, `workbench/drafts/home_care_mark_done/`) asks for exactly
  this: a deliberate next date, no guessed person, a way back, and nothing
  saved twice. Using the ordinary create and change paths means every
  existing check still applies.
- Declaring it keeps modules files-only; the same core works for any "log it
  and move the date" job later (a vehicle service, a pet's treatment).
- The revision comes from history that already exists, so no table needed a
  new column and no core migration was needed.

## What else we considered
- **Two separate saves, or a button that only adds Work done.** Rejected: the
  job dates would still drift, which is the problem.
- **A revision column on every table.** Cleaner to read, but a migration for
  every module's tables; the newest history id already behaves the same way.
- **A separate table for operations.** Would make lookups simpler; history
  already holds the same facts and is backed up and exported with everything
  else. Revisit if lookups ever become slow.
- **Working out the next date automatically.** Rejected (as in 0063): a
  schedule depends on the equipment and local rules; the household chooses.
- **Offering Undo for as long as it is safe, on every visit.** Rejected for
  now: an Undo button weeks later would surprise; it is offered on the notice
  straight after saving.

## What this costs us (the downsides)
- A bigger action section for module authors to learn, and more code to keep
  correct: a second kind of action with its own form, two more routes, and a
  history-based revision that every write must keep writing (all writes go
  through `Records`, so they do).
- Finding an operation by its number reads the history entries of that kind
  with a JSON lookup and no index. Fine for a household's history; would need
  an index or a table at a much larger size.
- The form's repeat offer is worked out twice (in the page, and on the server
  when saving); the two must stay the same. The server's answer is what is
  saved and shown afterwards.
- "Today" is the computer's date, as with every `default = "today"`.
- A Done on before Last done is refused here, so correcting a wrongly typed
  latest date means editing the job and the Work done entry by hand (or Undo,
  straight away).
- Undo is only offered on the page right after saving; going back later means
  editing by hand.
- The Lane B draft folder stays in `workbench/` until Lane B removes it.

## How hard it is to undo
Medium. Removing the `[[tables.jobs.actions]]` section turns Mark done off;
the repeat columns can stay (unused) or be dropped by a new migration. Work
done rows and job dates already saved stay as they are. Removing the core
feature means removing `actions.py`, the form routes and template and the
loader checks; history entries of kind `action` and `undo` would then show as
plain lines.

## We should revisit this if
- Households ask to undo a completion later than straight after saving.
- Another module wants "log it and move the date" with a different shape (two
  added records, or a link into another module), which `adds` does not allow.
- History grows large enough that operation lookups are noticeably slow.
