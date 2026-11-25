# 0123. Private calendars name nobody until Show, Record a dose copies nothing, and Show is a POST

- **Status:** Accepted
- **Date:** 2026-11-25
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0059 (private details sent only on Show), 0071 (a pressed button, never a link), 0120 (medicine doses and
  their Record a dose link), 0121 (private lists and the dose calendar). It closes three gaps 0121 listed as downsides.

## In plain words
Private history now stays private on the calendar too. Before you press **Show**, a dose calendar says only how many
doses were recorded each day ("2 doses recorded") and "this person"; it does not say who received them. The people
you can choose between are listed as "Given to #1", "Given to #2". After **Show**, the names appear on that page only.
The **Record a dose** button no longer remembers the last medicine or the last person who gave a dose, so the address
and the form it opens hold nothing private. And pressing **Show** beside one private detail (an account number, the
amount of a dose, your own words in a drill) is now a pressed button the browser sends privately, not an address, so
it cannot be saved in the browser's history, a bookmark or a log. It works with no script, with the keyboard and with
a screen reader, and the page that shows the detail is never kept by the browser.

## What we chose
- **Generic for every `private = true` table, naming no module.** A calendar or day page on a private table, before
  its Show, calls the person it is for "this person" in its heading, summary, caption and empty-month words, and the
  person chooser lists each person as the link column's label and number (for doses, "Given to #3"), in number order
  so the order does not spell out who. The link back says "Open the person's page". After Show (the same POST as in
  0121) the ordinary names, lines and giver come back. The count, the ● and "See this day" are unchanged.
- **Record a dose copies nothing from earlier doses.** `private_daily.add_link` now carries only the person whose
  page it is on and the household's time now. The medicine and giver of the last dose are not in the address, so they
  are not in history or logs, and the form no longer says "Filled in from a recent entry". The medicine and giver are
  chosen on the form each time. The one medication detail a person has is no longer chosen for them either, because
  its number in the address would say they have exactly one.
  - Filling from a page's **own explicit context** stays allowed in principle (the person's page already puts
    `recipient=<number>` in the address, because that page is the context). No private page offers such a link
    today, so nothing else is prefilled. A future link from a medicine's page after Show could carry that
    medicine's number, since the household opened it on purpose; it would need its own line in this record.
- **Show on one private detail is a POST.** `POST /t/<table>/<id>/reveal` takes `column` and the page's session token
  (`_csrf`), the check every other write already uses; the old GET answers 405.
  - Every Show button is a real submit button joined (by its `form` attribute) to one hidden form in `base.html`
    that holds the token, so it works inside an edit form without nesting forms. With a script, the page sends the
    POST in the background asking for JSON, swaps the words in and moves keyboard focus to them. Without a script,
    the browser submits the form and gets a small page ("Account number", the words, a link back) that says it is
    not kept.
  - Every reveal answer, page or JSON, carries `Cache-Control: no-store` (the app already sets it on every response;
    the reveal route now sets it itself so it cannot be lost).
  - The medicine-words button on the dose form (0120) also POSTs. It is a script-only convenience today and stays so;
    without a script the form says to open the person's page.
- **Tests:** `tests/test_private_reveal.py` (names absent before Show and present after, on the calendar, the chooser,
  the day page and the person's page; the Record link and the form it opens carry nothing private; GET refused, POST
  without the token refused, POST with it works, no-store, and a no-script page); the old GET calls in other tests
  became POSTs; 0120's prefill test now expects only the person and the time. The browser check also looks for the
  person's name inside the calendar before Show.

## Why we chose it
- A heading that says "Dose calendar for Rosa" on a shared screen answers "who takes medicine" as plainly as a list.
- An address is copied, logged and remembered; a form POST is not. 0071 already settled that for Show elsewhere.
- Prefilling the last medicine is a convenience that stores private history in a place nobody thinks to clear.
- One hidden form is smaller and safer than a form around every Show button.

## What else we considered
- **Hiding the person's name on their own page:** refused; the page is theirs and its address and heading name them.
  Only the calendar panel on it stopped naming them.
- **A one-time token in the Show link (still a GET):** still lands in logs and history; refused.
- **Dropping the no-script fallback:** simpler, but 0059's Show worked as a button on any page and a household may
  block scripts; kept.
- **Keeping the prefill but encrypting it in the address:** more machinery for a convenience; refused.

## What this costs us (the downsides)
- Recording a dose now needs the medicine chosen each time (two taps); the giver defaults to "I do not know".
- Before Show the calendar chooser is numbers, so a carer must remember or Show first to tell people apart.
- Without a script, Show opens a separate page and Back returns to the hidden one; with a script nothing changes.
- A reload of the no-script reveal page asks the browser to resend the form.

## How hard it is to undo
Easy. Put the old GET route and `?column=` addresses back in `pages.py` and the templates (`_reveal.html` is the
only place the buttons are made), restore the `last` lines in `private_daily.add_link`, and drop `private_subject_name`
and the `hidden` branches in `calendar_pages.py`, `daily_pages.py` and `private_daily.view`. No stored data changed.

## We should revisit this if
- Households say they cannot tell people apart on the calendar chooser before Show.
- A medicine's own page gets a Record a dose link (it can carry that medicine's number once the page was opened).
- A private name or value is ever found in the HTML of a calendar or day page before Show.
