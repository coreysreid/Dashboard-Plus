# 0132. Not a done day, a cleared date kept, and a press with its typed date counted once

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0091 and 0112 (Mark done in history, with Undo), 0119 (calendars, never "missed"), 0122 (a calendar
  of a table's own records), 0129 (earlier done days from history), whose three named downsides this resolves

## In plain words
Decision 0129 put each earlier done day back on the calendar from a record's history, but left three gaps. Now:
if an earlier day is wrong (1 September typed, changed to 10 September a week later), the line for it has a
button, **Not a done day — remove from the calendar**, with **Undo**; the record's history keeps a line saying so,
with **Put back on the calendar**. Clearing a "Returned on" to lend the thing again no longer loses the earlier
return: a date that stood for a day or more and is then cleared stays as a done day. And an old Garden Mark done
with a Done on typed by hand afterwards counts once, on the typed day, instead of twice.

## What we chose
- **(a) Not a done day.** On a calendar of a table's own records with `history = true` (0129's shape), each line
  read from history (an earlier date, or an old press that kept no date) gets a small POST form under it, with the
  session token and no script, like Mark done. Pressing it adds **one history entry** for the record
  (`not_done_day`, its `after` holding only `calendar_day` and a one-use `operation`); `done_days` leaves that
  (record, day) out of the calendar, Things to do's Calendar tab and the bars. **Undo** on the calendar's notice,
  or **Put back on the calendar** on the history line on the record's page, adds one more entry
  (`done_day_back`, same `operation`), and the day shows again if its history still says so. Nothing in the record
  or in any earlier history entry is changed or deleted. The date a record keeps now is never offered (it is
  changed on the record's own page) and is never left out, even if it was once taken off. Pressing twice gives the
  first entry back; a stale press ("that day is not from history any more") changes nothing and says so. The
  entries do not count towards a record's revision, so taking a day off never blocks a Mark done's Undo, and they
  never enter the sync change log (they stay in this computer's history, like every history line). The button is
  on the list's own calendar page only, not the Things to do Calendar tab, to keep that page short.
- **(b) A cleared date stands when it stood a day.** A date cleared on a later household day than it was typed
  now counts as an earlier done day (a thing returned, then lent again; a job done, then needing doing again).
  Still never counted: a date cleared the same day it was typed (a slip fixed at once), and a clear made by an
  Undo of Mark done or Mark returned, whatever the day (read from history: the record's history line just before
  an `undo` entry is the Undo putting the fields back). A wrong one can be taken off with (a).
- **(c) A press and the date typed after it are one completion.** A one-step press that did not set the
  calendar's date (saved before the table kept one, 0129) and the **first date saved for that record after it**
  are the same completion when, until that date is saved, every field the press set still holds the value the
  press gave it (the job still shows done), and no other press came between. Then only the typed date counts, and
  only while it still counts itself. If a field the press set changed on the way (the job ticked not done again),
  it is a new round: the press keeps its own day and the date is its own completion.
- **Generic and checked.** The code is in `core/calendars.py` (`_history`, `done_days`) and a new small
  `core/calendars_corrections.py`; neither names a module. It needs no new declaration: every calendar that
  already passes 0129's load checks (`history = true`, own records, `when` a date column, never private) has it.
  The page route refuses any table that is not such a calendar, switched on, and never private. Every 0119 rule
  stays: the fixed looks and symbols, never "missed", no script, 320px (the button wraps), private columns never
  read (only the record's name and a day are shown or stored). **No migration**: the entries go in the history
  table the program already keeps.
- **Tests** in `tests/test_done_days_corrections.py` (14): a forward fix taken off and put back (history only
  grows, the record is unchanged, the notice, the history lines and Put back), pressing twice, the date kept now and
  an unknown day refused, the session check and unknown lists, the calendar rules, a loan lent again, a same-day
  clear and a late Undo, a wrong cleared date taken off, a press with its typed date, a new round, an old press
  taken off, Mark done's Undo still working, the core naming no module, and nothing private stored or sent to the
  change log. One 0129 test changed: a cleared date counts now unless it was cleared the same day.

## Why we chose it
- **It keeps 0129's honest record and only adds to it.** History stays the one place every date was saved; the
  household's "this wasn't a done day" is one more dated line in it, so it can be seen, explained and undone, and
  nothing is lost if it was pressed by mistake.
- **Most of the wrong days 0129 could show were ones it could not fix.** With a way to take a day off, the rules
  can lean less towards leaving days out: a cleared date that stood a day was usually real, and if not, it is one
  press to remove. A same-day clear and an Undo still never count, because those are nearly always mistakes.
- **The press rule follows what the household did.** An old press said "done" with no date; the first date typed
  while the job still showed done answers "when?" for that same press. Anything that reset the job in between
  means a second time.

## What else we considered
- **A done-log table** with its own Delete (0129's alternative): a core migration and a second copy of history,
  for the same result. The marker in history is smaller and cannot drift.
- **A separate corrections table:** would need a migration and its own lines on the history page; the history
  table already gives both.
- **Editing or deleting the history line that held the wrong date:** destroys the record of what was typed, and
  cannot be undone. Refused.
- **Taking off the date a record keeps now:** two ways to change one date. Refused: change it on the record's page.
- **Counting every cleared date, including Undo and same-day:** brings back the slips 0129 rightly left out.
- **Joining a press and a typed date when they are within some days of each other:** an arbitrary window; the
  "nothing reset in between" rule needs no number.
- **The button on Things to do's Calendar tab too:** every list's lines are there; it would lengthen a page that
  is for planning. The list's own calendar is one link away.

## What this costs us (the downsides)
- A day taken off stays off even if the history later shows it again for another reason, until it is put back
  (the household said so; the history line says so too).
- Taking a day off and putting it back adds history lines; the record's history gets longer.
- The entries stay on this computer: if records are ever exchanged with another computer (sync, decision 0100),
  a day taken off here still shows there.
- A date cleared a day after a wrong entry (typed on Monday, cleared on Tuesday because it was a mistake) now shows
  until it is taken off.
- The join in (c) reads every history line of the table once per calendar or bars view; fine for a household.
- The button adds a line of text under each earlier day at 320px.
- An old press joined to a typed date that is later typed back is not shown at all (neither counts); rare, and the
  date can be typed again.

## How hard it is to undo
Easy. Remove `calendars_corrections.py`, the routes and `_fix_notice` in `calendar_pages.py`, the form in
`_calendar.html`, the notice in `calendar.html`, the Put back form in `form.html` and its lines in `pages.py`, and
the `removed` filter and the press join in `done_days`; put back 0129's cleared-date rule in `_history`. The
history entries already saved stay (nothing reads them any more); no household data is changed.

## We should revisit this if
- Households take many days off: the rules in (b) or (c) are counting the wrong days.
- Someone asks to take off the date a record keeps now, or to remove days in bulk.
- Sync starts exchanging records: the entries would need to travel too.
