# 0134. A privacy and security review of decisions 0119 to 0133

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Claude (technical decision delegated by User 1; three questions left for User 1 below)
- **Builds on:** 0059, 0071 and 0123 (Show is a pressed button, never an address), 0100 (what travels), 0119 to 0133
  (calendars, doses, bars, timelines, earlier done days, prices and money back)

## In plain words
Privacy comes first in this project, so every page, button and file added in decisions 0119 to 0133 was checked
for ways a private detail could slip out: into a page before you press **Show**, an address, a message, the history,
an export, the list of changes kept for other computers, a helper, the browser's memory, or an error. Six things
were wrong and are fixed. The most important: the **Doses recorded** chart named the person (and its chooser listed
everyone who takes medicine by name) before Show, unlike the Dose calendar; and when a price you typed on Review
could not be saved, a helper could read why. Everything else held. Three questions are left for User 1.

## What we chose
Every check below was made by reading each record and its code and then trying it in a test household (the
invented ones of the 0121 and 0133 tests). Each fix has a test that failed first, in
`tests/test_privacy_review_0134.py`; the checks that held are kept as tests too, so they keep holding.

### Found and fixed, worst first
1. **The dose bars named the person before Show.** `/bars/medicine_doses__doses/doses` said "Doses recorded for
   (the person's name)" in its title and heading, and its chooser listed every person with a medicine by name, in
   name order. 0123 made the Dose calendar say "this person" and "Given to #1" for exactly this reason (who takes
   medicine), and 0124 said its bars follow the Dose calendar. Now, before Show, the bars page and the bars panel on
   the person's page say "this person", the chooser lists people by number in number order, and the link back says
   "Open the person's page". After the pressed Show the names come back on that page only (`web/bar_pages.py`,
   `templates/bars.html`).
2. **A helper could read why a typed price was not saved.** When the price a person typed on Review was wrong, the
   reason ("Nothing was added: the price was not saved. Currency must be a three-letter code…") was written on the
   waiting row, and a helper reads each row's reason through `GET /api/v1/batches/<id>` (and so through the
   connector). It told the helper that the person was typing a price and what was wrong with it. Now a helper sees
   "Still waiting for the household to decide." for such a row; the person still sees the full reason on Review
   (`core/proposals.py`, `core/receipt_prices.py`).
3. **A module could put a private date or link on a calendar, bars or timeline.** The module checker refused a
   private column in a timeline's words, but not a private (`sensitive = true`) `when` date, `per` link or bars
   `group` link, which would be drawn on the page before any Show. No shipped module does this; the checker now
   refuses it in plain words (`core/modules.py`).
4. **Browsers could remember what was typed in private fields.** A browser keeps a history of words typed into
   form fields and offers them again. Private fields (prices, money back, dose amounts, medicine words, account
   numbers) did not ask it not to. Every private field now says `autocomplete="off"`; ordinary fields keep the
   browser's help (`templates/_field.html`).
5. **A saved private number, choice, date or tick looked like an empty field.** On a Stock in's page with a saved
   price, the price box showed empty under "Private detail saved"; anything typed in it was quietly ignored, because
   the saved price is kept until Show. Worse, a saved private tick ("This is more than was paid", 0133) showed as not
   ticked, so saving the money back page unchanged was refused (or, below the amount paid, would have cleared the
   tick). Each now stays closed behind its Show and is kept exactly as saved; Show opens it with its saved value
   (`templates/_field.html`, the Show script in `templates/base.html`).
6. **An address asking for a far-back period gave the "Something went wrong" page.** Bars with `end=0001-01-01`
   and a day page with `day=0001-01-01` crashed. They now read such a date as 1 January 1900 (as the calendars
   already do) or today (`web/bar_pages.py`, `web/daily_pages.py`).

### Checked and found nothing wrong
- **Pages before Show:** the Dose calendar, its day page, the dose list and record, the person's timeline, Spent per
  month, the money back list and record, a Stock in's page, Home, Needs attention, Things to do and its Calendar tab,
  and Review hold no medicine word, amount, giver, price or refund before Show.
- **Addresses and redirects:** no Show is ever an address (`?show=1` does nothing); Record a dose carries only the
  person and the time; the Not a done day notice carries a random operation number; `back` and `month` are checked
  before any redirect, so none leads to another site.
- **Messages and errors:** no notice or refusal repeats a private value; a refused number or date says what is
  wrong, never what was typed.
- **History:** a private record's history appears only after its Show; a private column's old and new values never
  show; Not a done day lines say only the day.
- **Exports and sheets:** private lists and private columns are left out of the zip and every sheet; prices and money
  back are never in them.
- **The change log for other computers (0100):** prices, line totals, currencies and every money back amount, tick
  and note are named only as withheld, never with a value; Not a done day writes no line; a delete marker carries no
  values. Medicine doses travel as 0089 decided.
- **Helpers and the connector:** private lists are not offered; private columns never appear in records or table
  descriptions; the guide names private fields by label only; a price or money back is refused from a helper.
- **Suggestions while typing:** refused for private lists and private columns.
- **Logs:** values are never logged; an unexpected error logs only where it happened.
- **Never kept by the browser:** every page says `Cache-Control: no-store`, and every Show answer sets it itself.
- **Every new button that changes or shows something** is a POST that needs the page's session token and our own
  Origin; the same address as a link answers 405 or shows nothing private; ids, days, months and operations are
  checked; a switched-off module's pages and Show answer 404.
- **Database queries:** table and column names come only from the modules' checked declarations; typed values are
  always passed separately, never written into the query.
- **The print script (0131) and the other page scripts:** written in the page itself, loading nothing from anywhere
  and sending nothing except Show's own POST to this program.

## Why we chose it
- A private detail that leaks once cannot be called back, so the review looked everywhere a value could travel, not
  only at the screens.
- Each fix makes the program follow a promise it already made (0059, 0121, 0123, 0128, 0133); no rule changed.

## What else we considered
- **Removing the price reason from Review altogether:** the person needs it where they typed the price; only the
  helper's copy is replaced.
- **Hiding the person's name on their own page as well:** refused in 0123; only the dose panels on it stop naming
  them, as the calendar panel already did.

## What this costs us (the downsides)
- Before Show, the bars chooser lists numbers, so a carer must Show first to tell people apart (as on the calendar).
- A browser no longer offers earlier typed words in private fields, so a currency or a note is typed again each time.
- A helper waiting on such a row is told less, so it may ask the person why a row still waits.
- A saved private field now needs Show before it can be changed, even to type a new value over it.

## How hard it is to undo
Easy. Each fix is a few lines: the `hidden` branch for names in `bar_pages.bars_view` and `_bars_page`, the
`closed` attributes and the private tick block in `_field.html`, `_helper_reason` in `proposals.py`, the
`sensitive` conditions in `_check_calendar`, `_check_bars` and `_check_timeline`, and the two date limits. No stored
data changed.

## Needs User 1
These would change a privacy or security rule, so they are described and left as they are:
- **A Content-Security-Policy.** The program sends none. One would tell the browser to run only the program's own
  scripts, a second wall if anything were ever slipped into a page. It means moving every script in the pages
  (about ten, plus the Print buttons) into files first. Worth doing as its own piece of work if User 1 agrees.
- **Whether a refund's existence travels.** The change log keeps a money back record's link to its Stock in and its
  day (the amount, currency, tick and notes never travel), and a change to a price is logged as "these private
  fields changed", by name only, as 0100 decided for every private field. Whether another computer should even learn
  that a refund exists is a travel decision for sync stage 2 (0133 already lists it).
- **Confirm the dose bars wording.** 0124 said the bars name the person on their own page "as on the Dose calendar";
  the Dose calendar does not (0123), so the bars now follow it. If User 1 wants the name back on the person's own
  page only, it is one line.

## We should revisit this if
- Any new page, file or helper answer shows a private value before Show: add it to the review's tests.
- Member computers arrive (sync stage 2): repeat the change log checks against what actually leaves.
- User 1 answers one of the three questions above.
