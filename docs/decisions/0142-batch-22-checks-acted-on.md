# 0142. Acting on the batch 22 checks

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** Claude (technical decision delegated by User 1)

## In plain words
Lane B checked every calendar, bar chart and timeline and the private lists. This fixes what was really wrong, worst first: pages that printed badly, a private calendar that said a record number, a few clumsy sentences, a chart that opened on an empty subject, and an example Stock item that named a medicine and a person.

## What we chose
- **Printing.** The "in words, day by day" list under every calendar now opens for paper (`data-print-open`), also on a record's own page, and stays folded on screen. On paper the calendar's Show button and Hide details link are left out. A shown dose timeline stacks its private lines under a full-width day line instead of squeezing the day into vertical letters, and the timeline's Hide details, Open and See this day links are left out because they do nothing on paper.
- **No database numbers.** A private calendar, bars page or day page, before Show, calls people "Person 1", "Person 2" in the order listed (new `display.private_subject_names`), not "Given to #4". The record number stays only in the link address, as before. What the page reveals is unchanged: nothing but how many people there are.
- **Due words from the list.** A calendar of a table's own records can carry `not_done` words. Things lent out says "not marked returned yet". Other lists keep "not recorded as done yet".
- **Spoken day names follow the household.** A calendar cell's hidden label says "November 26" for month-first households and "26 November" otherwise.
- **Bars.** With no subject chosen the page opens on the one with the most recent accepted entry (not for private lists, which keep their order), and says so; if nobody has one it opens on the first, as before. Home care's Work done counts say "work done". A period with only a suggestion waiting on Review says "Nothing accepted yet; 1 waiting on Review" (a period that also has entries says it beside them); the waiting suggestion is never counted. Dose bars say "Each medication detail on its own" and "Medication detail #3", because one detail can name several medicines.
- **Timeline and links.** Back links say "Back to herbs", never "herbs's page". A weigh-in after another on the same day says "since the earlier one that day". A day of feedings with no amounts says "no amount written down".
- **Stock names.** The Garcia example item is "Prescription tablets (blister packs)" with notes "Refill at 30.". The Stock item name field now says Stock is ordinary information (Home, printed sheets, the spreadsheet, helpers) and that a medicine's name, strength and who takes it belong in the person's medication details. Typing is never blocked.

## Why we chose it
- Paper is where a household shows a page to someone else, so it must never lose its words or print buttons that do nothing.
- A database number tells a reader how the program counts records and means nothing to a household; "Person 1" says the same thing in household words.
- A due word that is wrong for the list ("done" for a loan) makes a household doubt the page.
- A hint on the form teaches the safe habit without a blocking rule that would also stop honest names like "Aspirin" for a first aid cupboard.

## What else we considered
- A warning only when the category is First aid or the name matches a medication detail: it needs the form to react as you type and would miss names it cannot match. A plain hint always shown is simpler and honest.
- Choosing the Person number by name order: that would spell out an order of names before Show. Record order reveals nothing.
- Splitting a combined medication detail into one medicine per bar: never done by guessing at free text.

## What this costs us (the downsides)
- "Person 1" can change if someone earlier is deleted, so a bookmark to a private page is by record number, not by that label.
- The Stock hint shows to everyone, not only those typing a medicine.
- The waiting count reads the suggestions' own date, so a date with a time zone offset near midnight is counted by the household's day, the same way entries are.
- Not done here: the same marks meaning different things on calendars and timelines (a legend), the same-day order of two weigh-ins, "3 times done recorded" and the technical done-day sentence, a visit follow-up design, and a sharing choice for Stock First aid items (decision 0140's area).

## How hard it is to undo
Easy. Each change is words, a style rule or a short function; the `not_done` key is optional and harmless if unused.

## We should revisit this if
- A household reads "Person 1" as a real name or ranking, or prints a private page and finds a missing word.
