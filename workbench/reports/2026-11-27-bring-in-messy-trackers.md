# Batch 23 item 113: bringing in a messy old tracker

Checked 27 November 2026 on Lane A's branch at `eeb6eac` (decision 0137 is on `main`). Three invented old trackers,
in `workbench/reports/bring_in_2026_11_27/`, were run through **Bring in earlier entries** in Chromium:

1. **Phone notes export** of feedings for Smith's Rex and Whiskers: dates "3/11/26", "Tue 4 Nov", "2026-11-05",
   "8/11"; times "7am", "7.15pm", "19:30", "noon", "6:45 PM"; amounts "120g", "120 g", "1 cup", "half pouch";
   "rex", "Rexy", "Wiskers"; a repeat from a phone sync; no Food column. A tidied copy splits the amount and unit,
   adds Food, and keeps a cup, a repeat, a row already in the app and a future date.
2. **Hand-kept spreadsheet** of Rex's weigh-ins: "19.4 kg", "43 lb", "20,3", "20.9kgs", "15 Aug 2026", one blank
   date, a row typed twice; the column is headed "Dog".
3. **Typed-up printout of doses** for Garcia's Rosa: US dates, "8:00 AM", "20:00", "8am", one ISO time with Z,
   "Metformn", "Metformin 500mg", "Lisinopril", "Rosa", and one row for Carlos, who has no medicines.

## Findings, worst first

### Blocker: one row with a blank date crashes the whole check

- **How to see it:** Weigh-ins → Bring in earlier entries → a file with `Day,Pet,Weight` and a row `,Rex,21.0`
  → Read the file → Check the rows.
- **What happens:** **"Sorry, that did not work. Something went wrong. Your data is safe."** The server log shows
  `KeyError: 'day'` in `core/csv_bring_in.py` `plan()`, at `values[when_column.name]` in the repeat check.
- **Why:** Weigh-ins' Date has `default = "today"`, so the row passes the record check without a day. The repeat
  step then reads a day that is not there. If the crash were only caught, the row would quietly be dated **today**,
  which is worse.
- **Expected:** the row is listed under "Rows that need fixing": **"Row 9: Date is empty. Every earlier entry
  needs its own date; it is never filled in as today."** The other rows carry on.
- **Suggested change:** in bring-in, treat the `when` column as required with no default, before
  `check_create`. Add this file as a test.

### Important: a feeding amount with its unit typed in is refused

- **Where:** phone notes, "120g" and "120 g": **"Row 2: Amount put out must be a number."**
- **Why it matters:** "120g" is how almost everyone writes it, and the list has a Unit field. Every row of a
  phone-notes export fails, so the household must split columns in a spreadsheet first.
- **Suggested change:** when the Unit column is not matched, read "120g", "120 g" and "0.5 pouch" as an amount
  plus one of the list's own units. Never convert anything ("1 cup" stays a row problem). The row problem
  becomes: **"Row 5: “1 cup” is not one of this list's units (g, ml, pouch, scoop, piece). Nothing is converted:
  change it in your spreadsheet, or leave this row out."**

### Important: every row needs a Food column the old tracker never had

- **Where:** phone notes: **"Every row needs Food. Match one of the columns to it."** There is no way to say "the
  same food for every row".
- **Suggested change:** under the matches, offer **"Food for rows without one: [ Example dry dog food ▾ ]"**, from
  the foods already used for this pet (or typed). The same is needed for Unit ("Unit for rows without one: g").

### Important: a date in the future is brought in as an "earlier" entry

- **Where:** tidied phone notes, "11/12/26" (read day first as 11 December 2026, two weeks after today) was listed
  under "Every row ready to bring in". The note said "future date": a US-style 12 November typed in an AU file.
- **Suggested words:** under "Rows that need fixing": **"Row 9: 11/12/26 is after today. Earlier entries must
  be on or before today: check the date order."**

### Important: "Given to" offers every person and business

- **Where:** doses, "Given to “Rosa”": the choice lists all 16 People records, including **Bayview Pharmacy**,
  **Globex Corporation**, **Lincoln High School** and **Example Power Faults US**.
- **Suggested change:** offer only people with a medication detail (here Rosa Garcia), then "Leave these rows
  out". Carlos's rows already say **"There is nothing to choose from yet."** Better words: **"Carlos Garcia has no
  medicines in his private medical details. Add one on his page first, or leave these rows out."**

### Minor: medicine choices show the whole detail and its number

- **Where:** "Medicine “Lisinopril” for Rosa Garcia → **Metformin 500 mg twice a day with meals; lisinopril 10 mg
  each morning. Pill organiser on the kitchen counter. (#3)**".
- **Why:** Rosa's two medicines are one detail in the example, so Metformin and Lisinopril can only map to the
  same record (also in item 107). "(#3)" is a database number.
- **Suggested change:** show the detail's first 60 characters, end with "…", and drop the number. The example
  should keep one medicine per detail.

### Minor: unit words are capitalised wrongly

**"Unit must be one of: G, Ml, Pouch, Scoop, Piece."** and **"Unit: G"** in the ready rows. Suggested: **"g, ml,
pouch, scoop, piece"**, as on the form.

### Minor: month-name dates are refused without help

"Tue 4 Nov" and "15 Aug 2026": **"Date must be a date like 20/05/27 or 2027-05-20."** Suggested: accept "15 Aug
2026" (a month name cannot be read either way), and for a date with no year ("8/11", "Tue 4 Nov") say **"“8/11”
has no year. Write it like 08/11/26."**

### Minor: a heading the page could guess is left as "Skip this column"

"Dog" (weigh-ins) and "Patient" (doses) were not matched to Pet and Given to. Suggested: when every value in a
column is a name of a pet (or person) here, guess that field and say **"Guessed from the names in it."**

### Minor: smaller words

- An empty Notes leaves **"Weight: 19.4 kg · ."**: drop the trailing " · ".
- Ready rows show **"03/11/26 07:00"**, while the form shows "7:00 am": use the household's own time style.
- **"Bring in 0 feedings"** is still a button; when nothing is ready, say **"Nothing is ready to bring in yet."**
  with no button.

## What held

- The file stayed in the page, and "Nothing has been added yet" was true at every step.
- "7am", "7.15pm", "6:45 PM", "19:30", "8:00 AM" and "20:00" were all read; "noon" was refused clearly (**"When has
  a time that could not be read. Write it like 8:00 am or 20:00."**). A date without a time was refused, never
  noon.
- **Repeats:** the phone-sync copy (**"Row 5 has the same pet and the same time."**) and a feeding already in the
  app (**"A feeding with the same pet and the same time is already recorded."**) were skipped unless ticked.
- **Ambiguous dates** were each listed: **"“3/11/26” could be read either way. Read as 3 November 2026 (day first)."**,
  with one tick for all.
- **Units:** "43 lb" was refused (**"Weight is in lb, and this list records kg. Nothing is converted…"**); "20,3"
  got **"Weight uses a comma. Write decimals with a full stop, like 1.5."** Nothing was converted.
- **Names:** "Rexy" and "Wiskers" became choices, never new pets. "Metformin" rows were grouped ("Rows 2, 7, 8").
- Doses needed Show first, and nothing private was in any address.

## Limits

The final **Bring in** and **Undo** were not pressed for these files (decision 0137's tests cover them); the
findings are about the check page, which is where a messy file fails.
