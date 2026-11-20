# 0094. Import pauses on duplicates and unclear dates

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by Corey)
- **Refines:** decision 0080 (the "read the household's way without asking" and "every row adds a new record"
  downsides); acts on `workbench/reports/2026-11-20-restore-export-import-ux.md`

## In plain words
Before "Send to Review", the import page now stops and tells you about four things it used to let through quietly.
A row whose name is already in the list ("Rice is already in Stock items. This row would add a second one.") is
skipped unless you tick "Add anyway". A date like 1/2/27 that could mean 1 February or 2 January is shown with how it
will be read, and you tick once to say that is right. If a column of places or other links matches nothing, you are
told once at the top, with the first few names. If you skip a column, you are told how many rows lose a value.

## What we chose
- **Same name.** On the check page, a ready row whose name matches a record already in the list (ignoring case and
  extra spaces) is listed under "Already in your list" with an unticked "Add anyway" box. Unticked rows are not sent;
  the Send button counts only the rows that will go. Where records nest (places) the same name under another parent
  is a different record, so "Top shelf" in the Garage and in the Kitchen do not clash. Only lists that name their
  own records are checked (a required text column, no name template); batches and movements are not. Review shows
  "Already exists" beside such a row if it was added anyway (for Stock items it also points to Stock in and Count
  this batch, as Lane B proposed).
- **Unclear dates.** A typed date with a day and month both 12 or less and different, in a household that does not
  write year first, is flagged on the check page with the long form: "Read as 1 February 2027 (day first). Change it
  in the spreadsheet if that's wrong." (month first in the US). The person ticks one box ("These dates are read the way
  I meant") before sending; one tick covers all of them so a 200-row file is not 200 questions. Dates such as
  20/05/27, 5/5/27 and anything in the 2027-05-20 form are never flagged. The rule lives in `core/dates.py`
  (`ambiguous`), used by the import only; forms are unchanged.
- **Links that match nothing.** One line per link field at the top of the results: how many different values and rows
  matched nothing, and the first three values as typed. The per-row problems stay below it. The "no match" advice for
  places is now "Use the full path of a place saved in this household, or add the place first" (the old example path
  was not in the household).
- **Skipped columns.** When a column's heading names a field but the person chose "Skip this column", the page says
  "Skipping Place leaves it blank on N rows. These values will not be added." above Send, counting only ready rows
  that had a value. A heading that names no field is ignored silently.
- **Review wording.** The page is titled "Review", the empty state is "Nothing is waiting on Review.", and the
  results read "Rejected N rows", "Added N records", "This row was already accepted or rejected." and "Nothing is
  waiting on Review." (from the 19 November wording report).
- **Nothing new is stored.** The choices travel in the page as ticked boxes; the check of the file is repeated at
  Send as before.

## Why we chose it
- The three-household run showed an existing Rice could be staged and accepted as a second item with no warning, and
  a day-first household silently read 1/2/27 as 1 February. Both are mistakes people notice weeks later.
- Skipping by default for names and one tick for dates matches how often each is wrong: a repeated name is usually a
  re-import, while a file full of short dates is usually all in one order.
- Saying what a skipped or unmatched column costs lets the person fix the spreadsheet before sending, when it is cheap.

## What else we considered
- **Merging into the existing item.** Two goods can share a name and an import cannot change an existing amount
  (decision 0080), so we warn instead.
- **Holding every unclear-date row until ticked one by one.** Safer, but tiresome for files that are all one order.
- **Refusing unclear dates.** Would force everyone to rewrite dates that are usually right.
- **A ticked "Add anyway" on Review rather than on the check page.** The warning on Review is still shown, but the
  better moment to decide is before the rows are staged.

## What this costs us (the downsides)
- Two rows with the same name inside the file itself are not flagged against each other, only against the list.
- A name that differs by spelling ("Tinned tomatoes" and "Tomatoes, tinned") is not noticed.
- The count on the Send button follows the boxes as last checked: after ticking, press Check again to update it.
- A date written the other way round with a day of 12 or less is still read the household's way once the person ticks
  the box; we only make sure they were asked.
- One tick covers every unclear date, so a person can tick without reading them.
- Whether a skipped column "names a field" is a guess from its heading.

## How hard it is to undo
Easy. The flags are computed on the check page and Review from existing data; nothing in the database changed.

## We should revisit this if
- People still end up with second copies of items after the warning, or find it noisy on lists where repeated names
  are normal (then limit it to Stock items, or add a per-list switch).
- Someone imports a file with mixed date orders and the single tick lets a wrong reading through.
