# Batch 22 item 106: every calendar, checked

Checked 27 November 2026 against `main` at `2d9fca8` (decisions 0119 to 0138 merged). The three invented example
households (Smith AU, Garcia US, Taylor UK) were loaded into throwaway folders with `tools/load_example.py`. Chromium
(Playwright) opened every calendar the households have at 320px and 1280px, in light and dark colour schemes, and
in print media at 1280px:

- Things to do → Calendar, with each **Show:** choice and Previous/Next month;
- each list's own calendar at `/calendar/<list>` (Bills and policies, Important documents, Garden, Home care Work
  done, Home layout equipment, Things lent out, Medical kit checks, Medicine doses, Pet feeding, Routines, Vehicle
  registration, insurance and services), with October and December;
- the calendar panel on each pet's, person's, routine's and Home care job's own page.

That is about 170 page views per household. For each the walk recorded the page width, the summary, caption,
legend, the day list in words, every sentence with "miss", the first 60 keyboard stops at 320px, chip colours and,
in print, whether the month navigation, the day list and any Show button are on paper.

## Findings, worst first

### Important: a calendar on a record's own page prints without its day list in words

- **Where:** the calendar panel on a pet's page (Smith's Rex, `/t/pets__pets/1`), a person's page (Garcia's Rosa,
  dose calendar), a routine's page and a Home care job's page, in all three households.
- **How to see it:** Open Rex's page and print it (or print preview). The month grid prints with its symbols
  (●, ✓, ○) and legend, but "November 2026 in words, day by day" stays folded, so the paper has no dates or names
  in words. Checked by firing the page's own `beforeprint` handler in print media: the list stays closed.
- **Expected:** Paper never depends on the symbols alone. The full calendar pages already print the list open,
  because they render it open.
- **Actual:** The panel's `<details class="cal-list">` is rendered closed (`open_list = false` in `form.html`) and
  has no `data-print-open`, so decision 0131's "opened while printing" rule does not reach it.
- **Suggested change:** Add `data-print-open` to the calendar's `<details class="cal-list">` in `_calendar.html`
  (every calendar, so a private one prints only the "how many" words it already shows before Show). Keep it folded
  on screen.

### Minor: a private calendar names the person by database number: "Given to #4"

- **Where:** Garcia, `/calendar/medicine_doses__doses` and `?subject=4`, before Show.
- **How to see it:** The page heading reads **"Given to #4 · November 2026"**, while the summary and caption say
  **"this person"**. With two people taking medicine the choice list reads "Given to #2", "Given to #4": the
  numbers have gaps and mean nothing to a household.
- **Expected:** Names wait for Show (decision 0123), but the words are household words and agree with the summary.
- **Suggested words:** number people in the order shown, not by ID: **"Person 1 of 2 · November 2026"**, and on
  the choice list **"Person 1"**, **"Person 2"**. If one person only: **"This person · November 2026"**. Keep the
  ID in the link only.

### Minor: a private calendar's Show button is printed

- **Where:** Garcia's dose calendar, print media at 1280px.
- **What happens:** The "Show" button and "Shows each day's entries, on that page only." are on paper, where they
  do nothing. The month navigation is correctly hidden in print.
- **Suggested change:** Hide the calendar's Show form in print, as `.cal-nav` already is. Paper keeps the existing
  sentence above it, **"Private history — press Show to see it."**; on paper add **"(on screen)"** after "Show" or
  print **"Private history: shown on screen only."** instead.

### Minor: a loan's due line says "not recorded as done yet"

- **Where:** Taylor, Things to do → Calendar, 25 November: **"Things lent out · Spare bike pump, lent to Chris
  Taylor: return due since 25/11/26, not recorded as done yet"**. Smith's 9 November reads **"Things lent out ·
  Garden trowel, lent to Dave Wilson: Return done"** for a returned trowel.
- **Why it matters:** A loan is not "done"; the household's action is **Mark returned**.
- **Suggested words:** **"return due since 25/11/26, not marked returned yet"**, and on a returned loan
  **"Returned"** instead of "Return done". Other lists keep "not recorded as done yet".

### Minor: screen-reader day names ignore a US household's date order

- **Where:** Garcia (US). The day list reads **"Thu Nov 26"**, but the hidden label on the same grid cell reads
  **"26 November: 2 doses recorded"**.
- **Suggested change:** Build the hidden cell label with the household's own order: **"November 26: 2 doses
  recorded"** for month-first households, keeping "26 November" for day-first ones.

### Minor: Show: with a list that has no due dates silently shows All

- **Where:** Things to do → Calendar with `?only=pet_feeding` (Taylor and Smith). Pet feeding has no due dates, so
  it is not offered as a choice, and the page shows every list with no word that the choice was not used.
  Decision 0122 says an unknown or switched-off module shows All; this is by design, so only a sentence is needed.
- **Suggested words** above the calendar when the asked list is not offered: **"Pet feeding has no dates to
  plan, so it is not on this calendar. Its own calendar is on each pet's page. Showing all lists."**

## What held

- **Width:** no calendar page or panel was wider than 320px in any household, in light or dark. The Show pills on
  Things to do wrap onto several lines; there was no sideways scroll.
- **Blank days never read as missed.** Every sentence with "miss" in it was one of the reassurances: "A blank day
  has nothing recorded or planned. Only each one's next open date is shown as due, once; earlier times are never
  filled in as missed.", "A blank day has no feeding entry recorded. It does not mean anything was missed." and the
  bars' "it does not mean anything was missed". Late dates appeared once, on their own day, as "due since …, not
  recorded as done yet".
- **The counts agree.** Smith's Things to do summary, "November 2026 · Done: 5 · Due, not recorded as done yet: 2",
  matched the day list (2 + 1 + 1 + 1 done; 24 and 27 November due). Taylor's "Done: 1 · Due …: 1 · Planned: 1"
  matched too. Each line starts with its list ("Home layout · Kitchen smoke alarm: Test done").
- **Legend:** every calendar had a legend in words that also says what a blank day means, and only the looks that
  list can have (Bills and Vehicles offer no ✓).
- **Keyboard order:** at 320px, Tab went header → tabs → Show choices → Previous month: October 2026 → Next month →
  each marked day ("7 November: Done: 2") → "November 2026 in words, day by day" → each entry. A day link
  opened its folded list and moved to the right day. On a record's page the edit form comes first and the calendar
  is about 25 stops down, which is the page's normal order.
- **Screen-reader labels:** symbols are hidden from screen readers; each marked cell has a label in words, and
  Previous/Next month say which month.
- **Dark mode:** chip text measured 10:1 or better against its fill; chip borders 6:1 or better against the chip,
  so each look stays distinct without colour.
- **Print:** month navigation and the Show choices are hidden; legends print; full calendar pages print the day list.
- **Private values:** no dose name, amount, a bill's amount or a registration number appeared on any calendar page
  before Show (item 108 audits this route by route).

## Limits

The screen-reader pass read the accessibility labels and order from the page; it did not use NVDA, VoiceOver or
TalkBack. Print was checked in Chromium print media, not on paper. The example households are dated relative to
today, so the days above are as of 27 November 2026.
