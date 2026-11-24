# 0052. Dates are typed and shown the household's way

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decided by:** Claude (technical decision delegated by User 1), at User 1's request

## In plain words
User 1 wants to type a use-by date as 20/05/27. The dashboard now reads and
shows dates the way the household's country writes them: day first in
Australia, the UK, New Zealand and most places (20/05/27), month first in the
United States (05/20/27). Underneath, every date is still saved as 2027-05-20,
so changing the country changes how dates look, not the dates themselves.
While typing, the form shows the date in words ("20 May 2027"), so a mix-up
between day and month is caught before saving.

## What we chose
- The order comes from the country chosen in setup. Unknown or other countries
  get day first, as most of the world writes it. Canada gets 2027-05-20, the
  order its government recommends, because both other orders are common there.
- A date written 2027-05-20 is understood in every country.
- Two-digit years mean 2000 to 2099 (27 is 2027, never 1927). Type four digits
  for other years; those dates are shown with four digits too.
- Impossible dates such as 31/04/27 or 29/02/27 are refused with "Enter a
  real date in DD/MM/YY format", keeping everything else that was typed. They
  are never quietly turned into 1 May.
- Slashes, dots or dashes between the parts all work (20.05.27, 20-5-27).
- Date boxes are now plain text boxes, not the browser's date picker.
- One small module, `core/dates.py`, does all of it. Forms, lists, *Needs
  attention* and printed sheets all use it, so a date never appears two ways
  on one screen. The record service and the future Agent API take 2027-05-20 only.
- This follows Lane B's acceptance checks 8 to 11 in
  `workbench/drafts/stock_lots/ACCEPTANCE.md`.

## Why we chose it
- The browser's date picker follows the computer's language setting, not the
  household's country. A computer set to US English showed Australians
  05/20/2027, which is exactly the confusion that leads to eating something
  out of date or throwing away something good.
- Typing is faster than a calendar for a stocktake of many items.

## What else we considered
- Keeping the browser's date picker: it is inconsistent between browsers and
  follows the computer, not the household.
- A separate setting for date order: one more question in setup; the country
  already answers it. It can be added later if a household needs it.
- Always showing dates in words ("20 May 2027"): clearest, but long in lists
  and slower to type.

## What this costs us (the downsides)
- No pop-up calendar. Someone who prefers clicking a date has to type it.
- A US household's printed sheet and an Australian one write the same date
  differently; that is intended.

## How hard it is to undo
Easy. The stored dates are unchanged; only `core/dates.py` and the form would change back.

## We should revisit this if
- Households ask for a calendar to click, or a date order different from
  their country's.
