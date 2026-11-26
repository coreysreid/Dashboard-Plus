# 0138. The helper guide brought up to date with routines, feeding, vehicle running, doses and prices

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0066-0069, 0102, 0105, 0112, 0116 (the helper API, guide and connector), 0110 and 0111 (the
  household's own day, units), 0120, 0128 and 0133 (private doses, prices and money back), 0129 (Garden's done date)

## In plain words
Since decision 0116 the program gained routines, pet feeding, vehicle running, medicine doses, confirmed prices,
money back, Garden's done date, and calendars, bars and timelines. The starting message for an assistant, the
connector's tool descriptions and the published API description had not been told. They now say, in plain words,
which of the new lists an assistant can fill in (with one invented example and a warning each), what it never
may (medicines, prices, what was paid, quotes, money back, codes, readiness answers) and what the household does
instead (types them in Dashboard Plus on its own computer), how units and the household's own day work, and that
the double-counting guards from 0112 and 0116 still apply. Nothing a helper can do has changed: only the words.

## What we chose
- **What a helper can fill, by table** (checked from the real lists with a helper given every part): everything
  with `suggestions` on and no required private, file or hidden-link field. New since 0116 that is: pet weigh-ins,
  feedings (Food given), odometer readings, routines and each time one was done or skipped, Garden jobs
  (including an already-done job with its done day) and vehicle service estimates without their cost.
- **Look only, with the reason already in the guide:** money back (a required private amount), important
  information about a person, and the readiness answers, drill runs and drill steps (a person answers them).
- **Not visible at all:** medicine doses (a private list, decision 0120). The guide names no private list, so it
  tells a helper nothing about what a household keeps; it says only that anything about medicines is never for
  helpers.
- **A new example catalog**, `web/helper_examples.py`: one invented entry and one warning per list with its own
  ways of working. The guide shows only the ones in the lists that helper was given, and only when it may suggest.
  A test sends every example through the real checks, so an example can never go out of date.
- **Fixed new guide sections:** "Lists with their own ways of working", "Never for helpers" (shown to every helper,
  including look-only), and two lines in "How to send" on the household's own day (a time with no offset is the
  household's local time; an offset is an exact moment) and units (the field's unit, never converted, an amount
  with its unit).
- **Moving in:** a suggested routine time does not move the routine's dates; Review does not question an odometer
  reading that is lower or in another unit (only the household's own forms do, decision 0111), so the helper is
  told to read earlier readings first; feedings are marked as possible repeats; the amount-twice and
  full-path guards of 0112 and 0116 are kept.
- **The same words** in `connector/tools.py` (the guide and suggest tools) and `openapi-v1.json` (the guide and
  proposals routes). The published file is edited by hand as it always was; the contract test still holds it
  to the routes. README and DESIGN section 9 say the same in one paragraph.
- **Tests** in `tests/test_helper_guide_0138.py`: the guide names every list a helper may fill; never says a
  private, look-only or person-only list takes suggestions, nor lists a private field as sendable; a price, money
  back or dose sent is refused; the examples are real; connector and published words match.

## Why we chose it
- Without the words an assistant would not know a weigh-in or an odometer reading can be sent, or would try to
  send a price and be refused. Words are the cheapest safe fix, and the guide already comes from the real lists.

## What else we considered
- Writing the new lists only in the fixed text: it would go out of date at the next new module. The examples
  are chosen by list name, so a list that is switched off or not given never appears.
- Letting the guide say which private lists exist: rejected; decision 0120 says a helper reads them as if they
  were not there.

## What this costs us
- Examples must be added by hand for each new list that needs one; a test lists the ones added so far.
- The guide is longer, so an assistant may skim it. Nothing in the core enforces the words, only the refusals
  that already existed (private details, look only, links).

## How hard it is to undo
Easy. Remove `helper_examples.py`, the two fixed sections and the added sentences, and their tests.

## We should revisit this if
- A module with a private list is added whose title should be said to the person but not the helper.
- A helper still sends private fields, which would point to refusing earlier or to a per-table grant.
