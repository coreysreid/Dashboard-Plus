# 0121. Private lists say only how many until Show, and doses on a month calendar

- **Status:** Accepted
- **Date:** 2026-11-24
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0059 (private details sent only on Show), 0071 (a private page opens from a pressed button, never a
  link), 0119 (the `calendar` declaration and its fixed looks), 0120 (medicine doses, `private = true`, its "list
  of every entry still shows who and when" downside and its calendar hook)

## In plain words
User 1 wants to see medication visually. A person's page now has a **Dose calendar**: the month as a grid where a
day with doses shows ● and how many, with Previous month and Next month and the same days in words ("Thu 19 Nov:
2 doses recorded · See this day"). It never says which medicine, how much, or that anything was missed or due.
**Show** under the calendar (a pressed button) lists each day's times, medicines, amounts and who gave them, on that
page only.

Private history is now private on every page. The list of every dose and each dose's own page used to show who
was given it, when and who gave it. Now they say only how many and "Private history — press Show to see it." with
a **Show** button. The person's page and Dose history still give the times of a day's doses, but name who gave
each one only after Show. An address ending in `?show=1`, a bookmark or the browser's history never opens any of
this.

## What we chose
- **One rule for every `private = true` table, in the core, naming no module.**
  - **The list** `/t/<table>`: the count, the private words and a **Show** button that POSTs (with the page's
    session token) to `/t/<table>/show`. Only that POST lists rows, latest first, 50 at a time, with **Show the
    next entries** as another pressed button and **Hide details** as a link back. There are no sort links (the
    order could give values away), the scroll loader `/t/<table>/rows` and the typing suggestions
    `/t/<table>/suggest` answer 404, and private cells such as the amount keep their own Show (decision 0059).
  - **A record** `/t/<table>/<id>`: only "Medicine doses #4", "(deleted)" if it is, "Saved." after a change, the
    private words and **Show**, which POSTs to `/t/<table>/<id>/show` and shows the ordinary form, its history and
    Delete or Restore. Saving goes back to the hidden page.
  - **A record's name** anywhere is its list and number ("Medicine doses #4"), never a name column or
    `record_name`, so a link to it or a heading carries nothing it holds.
  - **Questions and drills** treat any record of a private table as "a private record may relate", as they already
    do for a private column; a private table's `under` list is never put on another record's page.
- **Doses on a calendar.** Medicine doses declares 0119's `calendar` with `per = "recipient"`, `show = "one"`,
  title "Dose calendar" and entry "dose"/"doses", using the ● recorded look. It shows on the person's page (only for
  someone with a medication detail or a dose, as the dose panel does) and at `/calendar/medicine_doses__doses`,
  whose person chooser lists the same people.
- **The calendar honours `private` itself.** For a private table the grid, legend, summary and day list are the
  same as 0119's, but each day in words says only how many and links to its day page; there are no times, record
  links or amounts in the page. **Show** POSTs to `/calendar/<table>` (with person and month) and lists each entry;
  a table with a private `daily` log uses its after-Show line ("8:00 am · dose · the medicine · 1 tablet · Who gave
  it: ..."). The daily totals 0119 adds to a feeding day are left out, so medicines are never added together. The
  module checker refuses `state`, `due = true` or a look other than "recorded" on a private table's calendar, so
  it can never show which kind of entry or a due date; Things to do's Calendar tab never lists a private table.
- **The dose panel and Dose history** keep 0120's counts and times before Show; the giver now waits for Show too.
  Dose history links to the month's calendar.
- **Tests** in `tests/test_private_lists_and_dose_calendar.py` (11) plant an invented medicine, amount and giver and
  look for them in the HTML of the list, a record, the person's page, the calendar, the day page, Home, Needs
  attention, every Things to do tab, questions, drills, Review and Settings, before Show and with `?show=1`; then
  press Show; and check switching the module off, an empty month's words and the checker. The browser check adds
  the person's Dose calendar, its Show and the list's Show at 320px.

## Why we chose it
- 0120 left the list of every dose showing who and when; for medical history that is the page most likely to be
  opened on a shared screen. One switch in the core closes it for every private list to come.
- A pressed button, not a link, is what 0071 already settled for the private sheet: nothing to bookmark or share.
- A count with one mark is the plainest picture of "how often" that cannot reveal the medicine or suggest a missed
  dose; the day page and Show give the detail when someone means to look.
- Keeping the declaration generic means a future private module gets the same calendar without new code.

## What else we considered
- **A colour per medicine on the calendar:** refused; a colour that encodes which medicine is the medicine, and
  0119's looks are fixed.
- **Given, skipped or refused states:** not now. Nobody records a skipped dose, and a state could read as "missed".
  The checker would have to allow `state` again, with its own review.
- **Hiding the times on the person's page too:** 0120 chose counts and times there, and a carer checking "was the
  8 am dose recorded?" needs them; only the giver moved behind Show.
- **Remembering a Show for a while (a session flag):** refused as in 0071; a link would open it for as long as it
  lasts.

## What this costs us (the downsides)
- One more click to see the list of doses or open one; reloading a shown page asks the browser to resend the form,
  and Back shows the hidden page again.
- The shown list cannot be sorted and goes 50 at a time by button, not by scrolling.
- The calendar, the day page and the person's page still name the person whose calendar it is (it is their page),
  and the person chooser shows who has medication details, as Dose history already did.
- The **Record a dose** link on a person's page carries the last giver's and medicine's record numbers (not their
  names), and the form it opens shows them chosen; that form is opened on purpose to add a dose.
- The reveal address for a private cell (0059) is still a fetch, not a POST, as for every other private detail.
- The Backups preview still counts a private list's rows; backups hold everything, as before.

## How hard it is to undo
Easy. Remove the `calendar` lines from `modules/medicine_doses/tables.toml`; in `web/pages.py` drop
`_private_grid`, the two `/show` routes and the private lines in `grid`, `edit_record`, `more_rows`,
`suggest_names` and `_under`; delete `private_record.html` and the private branch of `grid.html`; in
`web/calendar_pages.py` drop `_private_lines`, `_applies`, the POST route and the `private` keys (and the branch in
`_calendar.html`); drop the private lines in `display.display_name`, `core/questions.py` and the calendar checker
in `core/modules.py`; and put `_links(info)` back without `if show` in `web/private_daily.py`. No migration or
stored data changed.

## We should revisit this if
- A household finds the extra Show on the list annoying or confusing, or asks to sort it.
- People want given, skipped or refused doses on the calendar: that needs a state and its own wording review.
- A private page is ever found carrying a value or name in its HTML before Show.
- Member phones start syncing: a Show on a phone must work the same way.
