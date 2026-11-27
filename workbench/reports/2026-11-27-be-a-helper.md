# Batch 23 item 114: being a helper with only the generated guide

Checked 27 November 2026 on Lane A's branch at `eeb6eac` (decision 0138's guide is on `main`). A "Look and suggest"
key for every module was made for the invented Taylor household (UK). The helper's 40,947-character guide was read
from `GET /api/v1/guide`, and then only that guide, plus the records the API lists, was used to move in these
invented notebook notes:

> Spare loo roll x12 in the hall cupboard · Paracetamol 2 packs, use by 03/04/27 · Sam's dentist: Example Dental
> 020 7946 0999 · Recycling every other Tuesday, last done 18/11 · Car MOT due 14 March; odometer 48,210 miles on
> 20 Nov · Bought 6 tins of beans 21/11 £3.60 · Alarm code 4321 · Grandma takes warfarin 3mg nightly

Four sends were made. Two of them deliberately broke the guide's rules, to see what stops a helper that misreads it.
The Review page was then read as the household would see it.

## What was clear

- **Links by id, new records by `{"ref": N}`.** Example Dental plus its Who to call row, and a new routine plus its
  Done row, went in one send and showed on Review as **"Added together"**, with **"Accept Who to call and its new
  People"**.
- **Amounts for a new Stock item go in one entry** ("Do not also send a Stock in and out entry"). Toilet roll went
  in as one entry with quantity 12 and the Hall › Hall cupboard place.
- **Prices only in `source`.** Review showed **"BEANS x6 · Price: 3.60. Shown for checking only; it is not saved
  in your records."**
- **Units never converted.** The odometer went in as 48,210 with `mi`.
- **Done or skipped does not move the routine's dates.** This was said twice, clearly.

## What a helper would misread, worst first

### Important: the guide never says which way round this household writes dates

- **What the guide says:** "Never guess … a date whose day and month could be either way round (1/2/27)". It never
  says the household is in the United Kingdom, or that its screens show day first.
- **What happens:** a careful helper must ask about every short date where both numbers are 12 or less
  ("03/04/27", "6/5"). A hasty helper used to month-first dates silently reads "03/04/27" as 4 March. The
  household's own Settings already know the order.
- **Suggested sentence** under HOW TO SEND: **"This household writes dates day first (DD/MM/YY), so its 03/04/27
  means 3 April 2027. Still send dates as 2027-04-03."** For a US household: **"…month first (MM/DD/YY), so its
  04/03/27 means April 3, 2027."**

### Important: nothing stops an alarm code or a medicine typed into a note

- **Sends 2 and 3** put **"Alarm code 4321"** in a Stock item's notes, and **"takes warfarin 3mg nightly"** in a new
  People record's notes. Both were accepted as waiting suggestions. Review showed them as ordinary rows with no
  warning: **"Move-in helper suggests adding to People: Name: Grandma · Notes: takes warfarin 3mg nightly"**.
- The guide forbids both ("Do not copy private facts into names, notes, why…"). A helper that misreads it, or a
  notebook pasted in whole, puts them in plain view on Home, sheets, export and helpers once accepted.
- **Suggested change:** decision 0141's checks (codes, card and bank numbers) should also run on helper
  suggestions. Review should then add, under such a row: **"This note looks like it has an alarm or door code.
  Codes are never kept in Dashboard Plus: reject this, or accept it and remove the code."** A medicine name in an
  ordinary note cannot be detected reliably, so the guide's sentence should name the place it belongs: **"A
  person's medicines go in their private medical details, which only they type."**

### Important: a future date is accepted for a Stock in

- **Send 4** read "use by 03/04/27" as the purchase date. Review showed **"Add 2 packs of Paracetamol on 03/04/27"**
  with a price box, and no warning, although that date is four months away.
- **Suggested words** on Review: **"This date is after today. A Stock in is for something already bought: check the
  date before accepting."** The guide could add to the Stock in and out line: **"happened_on is the day it was
  bought or used, never a use-by date."**

### Important: a UK MOT has nowhere obvious to go

- The guide's only vehicle date is **"registration_due: Registration or vehicle tax due"**. An MOT is a yearly test,
  not tax, so a careful helper has to stop and ask; a hasty one puts the MOT in the tax date.
- **Suggested change:** in a UK household, add to that field's help: **"For the MOT, add a Vehicle service or check
  called MOT with its next date."** (Vehicle services and checks already exist.)

### Minor: the guide never names the send itself

The guide says "You reach it through the "dashboard-plus" tools" and names `GET /api/v1/guide` and
`GET /api/v1/batches`. It never says **`POST /api/v1/proposals` with `{"request_key", "why", "entries": [...]}`**. A first
guess with `"records"` got **"This request could not be read. Check the fields and try again."**, which does not say
what was missing. Suggested: one line under HOW TO SEND: **"Send with POST /api/v1/proposals (the dashboard_suggest_new_records
tool): {"request_key": "...", "why": "...", "entries": [{"table": "...", "values": {...}}]}."** The refusal should
then say **"The body needs an "entries" list."**

### Minor: Routines lists `last_done`, then says to leave it out

The field list offers `last_done: Last done (date)`, and later: "Leave last_done out: earlier times go in the Done
or skipped list." Mark the field in the list itself: **"last_done: Last done (date). Helpers: leave this out."**

## What Review showed, and its words

| Row on Review | Suggested words |
|---|---|
| "Repeat every: 2 · Days, weeks, months or years: Weeks" | **"Repeats every 2 weeks"** |
| "Odometer showed: 48210" | **"48,210"**, as the timeline shows "62,100 mi" |
| Baked beans as a new item with a receipt price | The price box is offered only for a Stock in. Say under the row **"To keep what you paid, add it as a Stock in after accepting."** |
| "Accept all 7 … If one of them cannot be added, its whole group stays waiting with …" | Clear, but long at 320px; keep the first sentence visible and fold the rest. |

## Limits

The MCP connector was not used; its tools call the same `/api/v1` routes. Nothing was accepted, so each suggestion
was seen only as it waits on Review.
