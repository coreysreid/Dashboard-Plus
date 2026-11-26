# 0137. Bring in earlier entries: a person's own old tracker, previewed in full, added at once, one Undo

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Claude (technical decision delegated by User 1)
- **Amends:** 0120 ("no helper or spreadsheet can add a dose": a helper still never can, and Import to Review still
  never offers doses; the person's own Bring in earlier entries now can, after Show)
- **Builds on:** 0080 and 0094 (Import from a spreadsheet: reading, matching, unclear dates), 0091 (one-use operation
  numbers), 0110 (the household's own day and time zone), 0111 (units are never converted), 0120, 0121 and 0123
  (private lists, a pressed Show, POST only)

## In plain words
User 1 wants to start tracking pets' weights and medication again, and their old tracker holds about 93 medicine
doses plus weigh-ins and feedings. Until now the doses would have had to be typed one by one: doses are private, so
helpers and Import from a spreadsheet were never allowed to add them. Weigh-ins and feedings could already be
imported, but only through Review, one more step for rows the person typed themselves.

Now **Weigh-ins**, **Food given**, **Medicine doses** and **Odometer readings** each have a **Bring in earlier
entries** button on their list page (Settings, Import from a spreadsheet links to them too). Choose the CSV file,
check which column is which, and see **every** row before anything happens: what is ready, what needs fixing and
why ("Weight is in lb, and this list records kg. Nothing is converted"), names that match nothing ("Medicine
“Mystery pill” for Rosa Garcia": choose one of her own medicines, or leave those rows out), and possible repeats
(the same pet or person at the same time as an entry already recorded, skipped unless you tick **Add anyway**).
**Bring in 93 doses** adds them all at once, each with its own history entry, and the next page offers
**Undo: take all 93 off again**. For Medicine doses you press **Show** first, because the following pages show the
medicines and amounts. The file is read on this computer only, never saved and never sent anywhere; the page says so.

## What we chose
- **A list opts in, in `tables.toml`:** `[tables.<t>.bring_in]` with `when` (a required date or date-and-time column,
  not private) and `per` (a required link, not private: the pet, person or vehicle), and optional `entry` words.
  The module checker refuses anything else at load, and refuses a list whose records change amounts elsewhere
  (`adjusts`, `total`), join two records (`pair`), move reminders (`takes_over`) or keep prices, because one Undo must
  remove exactly what was added. Shipped: pets weigh-ins, pet feeding servings, medicine doses, vehicle odometer
  readings. Pets' Treatments given is left out: its rows point at a treatment, and several pets' "Flea treatment"
  would all look alike in a choice list.
- **Only a person, only on their own pages.** The pages live at `/bring-in/<table>` behind the session cookie and page
  token like every page; the helper API has no route to them, and helpers still cannot suggest doses (the table keeps
  `suggestions = false`, so Import to Review still refuses it).
- **Show first for a private list.** A list that is private, has a private column or links through a `shows` rule
  (decision 0120) starts with a Show button (a POST); the file choice and every later step carry that press and are
  POSTs, so no private value is ever in an address or a bookmark. Before Show the page lists only earlier
  bring-ins by date and count. Its entries' history says "Import 'earlier-entries'" and its summary keeps no file
  name, so a file called after someone's medicine is not written anywhere.
- **The file, in memory only.** The same reader as Import (UTF-8, 1 MB, 2,000 rows, comma or semicolon, refused
  above 3 MB before reading; `UploadRequest` now keeps these uploads in memory too). Between steps the text travels in
  the page, as in 0080, and each step reads and checks it again from the start. Text is kept as words, never worked
  out as a formula; hidden characters are a row problem; every page is `Cache-Control: no-store`. Nothing is
  logged but the address.
- **Matching columns.** As in 0080, by label or key, plus "Date" and "Time" headings for the list's own date; a
  date-and-time field also offers "time of day only" so a separate Time column joins its Date column. Times may be
  "8:00 am", "8am", "20:00" or "7.15 pm".
- **Times and days the household's way (0110).** A time with no offset is the household's own clock, stored as
  typed, exactly as the form does; an ISO time with an offset keeps its offset (an instant) and counts on the
  household's day it happened. A date-and-time field with a date but no time is a row problem, never noon. Short
  dates that could be read either way are listed and must be ticked as right (0094).
- **Units (0111).** A number may carry its column's own unit ("21.3 kg"); any other unit is a row problem and is
  never converted. A unit choice column is read as on the form.
- **Linked records are never created.** A pet, person, vehicle or medicine is matched by its exact name, ignoring
  capitals and extra spaces. A medicine is matched only among that row's person's own medication details, by their
  private words (only after Show). A name that matches nothing or more than one becomes one choice under "Names to
  match": an existing record of the right kind, or "Leave these rows out". A choice is checked against the allowed
  list again on every step.
- **Possible repeats.** The same `per` and the same `when` (the household's minute for a time, the day for a date) as
  a live entry, or as an earlier row of the file, is skipped unless the person ticks Add anyway. Doses' two-hour
  repeat question and the odometer's lower-reading check stay on the form; a bring-in does not ask them.
- **One transaction, one Undo.** Bring in re-checks everything, then needs the page's fingerprint of the file,
  matches, choices and ticks, the same count of rows, and a one-use operation number (a second press opens the
  first result). Every row goes through the ordinary create path with its own history entry, then one history entry
  (`action = "bring_in"`, record 0) lists the new ids, the count and, for an ordinary list, the file's name. If any row
  is refused at that moment nothing is added and the new check is shown. Undo is one transaction that deletes exactly
  those ids (kept in history and restorable, like every delete) and writes `bring_in_undo`; it is refused, changing
  nothing, if any of them was changed or deleted since, or it was already undone. No migration.

## Why we chose it
- 93 doses typed one at a time is the obstacle between User 1 and the charts and calendars that already exist.
- The person has seen every row, so Review would only ask them to approve their own file a second time. A full
  preview plus one Undo gives the same safety with one step.
- Opting in per list keeps a rule on what a bring-in may touch, checked when the module loads, and keeps Import to
  Review exactly as it was for everything else.
- Matching only existing records, and only a person's own medicines, keeps 0120's rule that a medicine's words live
  in one place, typed by the household.

## What else we considered
- **Letting Import to Review take doses.** Review lists waiting rows before Show and is shared with helpers'
  suggestions; it would need a private mode of its own. Rejected.
- **Creating unknown pets or medicines.** Quick, but a typo would make a second "Biscuit" or a medicine nobody
  checked. Rejected; the person adds it on its own page first.
- **Keeping the file on the server between steps.** Rejected as in 0080: the file would outlive the request.
- **Converting lb to kg.** Rejected by 0111: nothing is converted; the person changes the spreadsheet.
- **Noon for a dose with no time.** Rejected: a dose time nobody wrote down is not history.

## What this costs us (the downsides)
- Rows go in without Review, so a wrong column match lands at once; the full preview and Undo are the safety.
- After Undo the rows are deleted, not erased: they stay in history and backups, as every delete does.
- Undo is refused once any one entry is changed; the person then deletes the rest one by one.
- Possible repeats compare the minute only, so the same dose written as 8:00 and 8:01 is not caught.
- The page carries the file back and forth (up to about 1.4 MB as text), slow on an old computer.
- The file name of an ordinary list is kept in its history; a private list's is not, so its history says only
  "Import 'earlier-entries'".
- Lists not shipped with `bring_in` (vet visits, Treatments given, routines) still go through Import to Review or
  their forms.

## How hard it is to undo
Easy. Remove the `bring_in` lines from the four `tables.toml` files, `core/bring_in.py`, `web/bring_in.py`, its
template and blueprint line, the grid and Import page links, and the `bring_in` key in `modules.py`. Entries already
brought in stay as ordinary records; their summary rows in history are harmless.

## We should revisit this if
- A household brings in a file twice or with the wrong match and Undo is refused because they edited one entry.
- Old trackers commonly write times without dates, or units we refuse, and people give up.
- Someone asks to bring in Treatments given or vet visits.
- A private value from a bring-in ever appears before Show, in an address, a log or an export.
