# 0062. Important documents is switched on, built from the second agent's draft

- **Status:** Accepted
- **Date:** 2026-11-18
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The household can now write down where each important paper is kept (a
passport, an insurance policy, a will, a lease, a warranty), whose it is, and
a date it wants to review or renew it by. *Needs attention* says "review or
renewal due in 25 days". *Worth filling in* asks "Where is Bicycle warranty
kept?" until a place is chosen. A one-page "Document review dates" sheet
prints the names, kinds and dates, and nothing about where papers are kept.

It is a list of where things are, not a safe for the papers themselves.
There is nowhere to type a passport, licence or policy number.

## What we chose
- A new module, `modules/documents/`, built on Lane B's draft
  (`workbench/drafts/documents/`, now removed; its notes and example rows are
  in git history). One list: Important documents. The draft's working
  migration became one first migration because the draft was never released.
- **It reuses what the household already has.** Where a paper is kept is one
  of the household's Places, shared with Household stock and Home layout, so
  it reads as a full path (Study › Filing drawer). Whose it is, when it is
  one person's, is one of the household's People; it is left blank for papers
  that belong to everyone. The module says so (`requires = ["people",
  "stock"]`); its only database change is one new, empty table.
- **No document numbers at all.** The draft already had no number field. We
  kept it that way rather than adding one marked private: a number is rarely
  needed to *find* a paper, and the safest private detail is one that is never
  stored. Help text on the name and notes asks the household not to type
  numbers or passwords. Because nothing private is stored, no column is
  marked `sensitive`, and the sheet needs no "show it only when you mean to
  print or share it" step.
- **No invented dates.** The review or renew-by date is typed by the
  household from the paper itself or chosen as a reminder. It reads "due",
  never "expired", because it may be a reminder rather than a legal expiry.
  A blank date raises no reminder. Nothing claims to know any country's
  renewal rules.
- **One question, asked gently.** For each paper written down: "Where is
  {name} kept? Choosing one of your places is enough." The household is never
  asked whether it has a will, a passport or insurance, because that depends
  on the household.
- **The sheet leaves out places, holders and notes**, as the draft chose. A
  printed list of where the passports and the will are kept would be a map
  for anyone who finds the page.
- Changes from the draft, each small:
  - "Whose document" and "Where it is kept" are links instead of free text, as
    the draft's notes asked once shared places shipped (decision 0054).
  - A place cannot be deleted while a paper is kept there; deleting a person
    keeps the paper and clears whose it is.
  - Each kind has a plain label ("Deed, lease or tenancy agreement"), and the
    reminder reads "review or renewal due …" next to the paper's name.
  - The list is marked as the module's main list on the home page
    (`home = "main"`, decision 0056).
  - The Smith example household gained a "Study" place to keep its papers in.

## Why we chose it
- "Where is the passport?" and "when does the home insurance renew?" are
  common, costly things to forget, and both are needed in a hurry.
- The draft was finished and every core need its notes listed has shipped:
  shared places with full paths (0049, 0054) and dates the household's way
  (0052).
- Leaving numbers out removes a whole class of privacy risk at no cost to the
  module's purpose.

## What else we considered
- **A private number field.** Refused for now: core support exists
  (decisions 0055, 0059), but storing a passport number in a file that is not
  encrypted adds risk for little gain. It can be added later, marked
  `sensitive`, if households ask.
- **Printing where papers are kept.** Refused, as above. The record's own
  page and the list show the place to the household on screen.
- **Free-text holder and place, as drafted.** Refused: they would drift from
  the names in People and Places and could not show full paths.
- **Attachments (a scan or photo of the paper).** Not part of this change:
  they need their own privacy, backup and encryption decisions.
- **Asking "Do you have a will?"** Refused: it depends on the household and
  cannot yet be answered "not relevant".

## What this costs us (the downsides)
- A household that wants a number to hand must keep it with the paper.
- Important documents needs both People and Household stock switched on.
- One more card on the home page, and one more module to maintain.
- The sheet cannot say where a paper is, even for a household that would
  like it to; it would need a second, opt-in sheet.
- A paper kept with someone outside the home (a solicitor) has no natural
  "place"; the household can add a place for it or leave the question open.

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the
folder. Nothing else in the database changed.

## We should revisit this if
- Households ask to record document numbers (then add one marked
  `sensitive`, with the private sheet step).
- Households want a printable "where our papers are" page for an executor or
  an evacuation (then a separate, private sheet).
- Attachments or an encrypted data folder (roadmap M3) arrive.
