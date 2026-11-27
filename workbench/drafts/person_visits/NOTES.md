# Doctor and other visits for people: design notes (batch 23 item 118)

Written 27 November 2026 against `main` at `2d9fca8`, with decision 0140 (sharing choices) read on Lane A's branch.
Pets already have **Vet visits** (`modules/pets`, day, vet, reason, cost, notes, on the pet's timeline as ■). People
have nothing like it: a GP visit, a dentist check-up or an emergency department night can only go in a person's
notes, which are ordinary, travel and print. This draft adds a private **Visits** list for people.

## What a household sees

**On a person's page** (Rosa Garcia), under Medicine given today, a fold like the others: **"Add a visit"** opens the
form.

| Field | Words on the form | Kept |
|---|---|---|
| Who went | the person, already chosen | a link to People |
| Day of the visit | today, changeable | date |
| Kind of visit | GP or family doctor · Dentist · Specialist · Hospital or emergency department · Physio, podiatrist or other allied health · Optometrist · Counsellor or psychologist · Other | choice |
| Who they saw | optional, from People ("Dr Priya Patel", "Bayview Dental"); **Not written down** | a link to People |
| Why, in your words | "A few words, like Check-up or Sore knee. Never test results, scan reports or ID, Medicare, NHS, insurance or card numbers." | private text |
| Go back by | optional: "The date the clinic said to come back or call. It shows once on the person's page; it is never called missed." | date |
| Notes | optional and private: "Keep results and numbers with the clinic's own letters, not here." | private text |

Cost is left out on purpose. It is money (Bills and Stock prices have their own rules), and a person's health
spending is a separate decision for the finance plan (batch 24 item 130).

**Never kept:** test results, scan or pathology reports, diagnoses copied from letters, prescriptions as
documents, ID, Medicare, NHS, insurance or card numbers, photos of letters. The form has no place for them. Under
decision 0141 the core's checks should refuse a long number in Why or Notes, with: **"This looks like an ID or card
number. Dashboard Plus never keeps those: keep it on the clinic's letter."**

## On the person's timeline

- **Before Show:** one line a day, as doses: **"1 visit recorded on Tue 24 Nov · See this day"**, mark ■ (the same
  mark as a pet's vet visit). The kind, reason and who they saw are not on the page.
- **After a pressed Show** (POST, as decision 0121): **"Visit · Tue 24 Nov · GP or family doctor"** per visit, with
  **Open**. The reason is only on the visit's own page, after Show, so a timeline shown across the room says the
  least.
- **Go back by** is not a timeline line: it has not happened yet. It shows on the person's page, folded, as **"Go
  back by Mon 8 Dec (from the visit on 24 Nov)"**, and after the date, once, **"Go back by 8 Dec: not recorded as
  done yet"**. Never "missed" or "overdue". It is done when a later visit is added, or with **"Done, or not
  needed"** on that line. Decision 0121 keeps private tables off Things to do, so this needs a core change to
  appear there; see the core needs below.

## Privacy and sharing defaults

| Where | Default | Why |
|---|---|---|
| Home, Needs attention, Things to do | never, before a core change; then only "1 visit to go back by this week" with no name | private table rule (0121) |
| Printed sheets and the emergency sheet | never | the emergency sheet already has the medical details a helper needs |
| Spreadsheet export | left out, as Medicine doses | private table |
| Helpers and the connector | no read, no suggestions (`suggestions = false`) | as doses |
| Other computers (0140) | **Only on this computer** until the household chooses to share; sharing asks "Start sharing these private things?" | consent based, User 1's rule |
| Bring in earlier entries | could opt in later (`bring_in`, when = day, per = person); not in this draft | old notes are a common source |

Every column says `travels = "never"`. Once 0140 is on `main`, the table should also say `travels = "never"`, so
another computer does not learn that a visit exists until the household shares it. This is unlike Medicine doses,
which starts Shared (item 115 asks for the first pairing to ask about doses too).

## Made-up example rows (Garcia, for an example file)

| Who went | Day | Kind | Who they saw | Why | Go back by |
|---|---|---|---|---|---|
| Rosa Garcia | 2026-11-10 | GP or family doctor | Dr Priya Patel | Blood pressure check | 2027-02-10 |
| Sofia Garcia | 2026-10-02 | Dentist | Not written down | Check-up and clean | 2027-04-02 |
| Carlos Garcia | 2026-08-15 | Physio, podiatrist or other allied health | Not written down | Sore ankle after soccer | (none) |

## Checks a promotion should pass

1. Before Show, no page, address, sheet, export, helper response or search shows a visit's kind, reason, notes or
   who they saw (repeat item 108's marker method with "Zqxreason").
2. The timeline shows "1 visit recorded on …" before Show and "Visit · … · GP or family doctor" after; never the reason.
3. A person with no visits shows no fold and no empty timeline line.
4. Deleting a person with visits is refused (`on_delete = "restrict"`) with words naming visits, not a database error.
5. A follow-up date in the past shows once as "not recorded as done yet", never "missed"; a later visit ends it.
6. A 16-digit number or a Medicare-shaped number in Why or Notes is refused once 0141 exists (no false alarm on a
   phone number in Notes).
7. Other computers get nothing until the household chooses, and choosing asks first.
8. The form fits 320px; the kind choices wrap.

## What the core must add

- **Private dated reminders** (`follow_up` on a private table): a "go back by" line on the person's page and,
  if wanted, a nameless count on Things to do. Today 0121 keeps private tables off Things to do entirely.
- **A form fold "Add a visit"** on the person's page for a private list (as Record a dose is), and the visit page's
  Show for reason and notes.
- **A table-level `travels = "never"`** (in 0140 on Lane A's branch; not on `main` yet).
- **A follow-up ends when a later visit exists**: a small rule (same person, later day) or a "Done, or not needed"
  action that writes history, like 0132's "Not a done day".
- **0141's number checks** on these private text fields.

## Open questions for Lane A

- Should a pet's Vet visits gain the same **Go back by** date? It would reuse the same core rule (item 109 ranked it
  first among visit additions).
- Should a visit link to a dose started that day ("started a medicine")? Not in this draft: it would join two
  private lists and needs its own decision.
