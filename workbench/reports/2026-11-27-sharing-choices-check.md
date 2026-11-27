# Batch 23 item 115: sharing choices, checked

Checked 27 November 2026 on Lane A's branch `claude/eloquent-hypatia-0gw2qn` at `eeb6eac`, where decision 0140 is
built. It is **not yet on `main`**; this report is for Lane A before it merges. The page was **Settings → What
your other computers get** (`/settings/sharing`) in the invented Garcia household, at 320px. I read every list and
detail on it and ran four journeys: keeping a detail here, starting to share a private list, Undo, and starting to
share a private detail on an ordinary list.

## Is every list and detail there?

Yes, for every module that is switched on. The page offers a choice for all 45 of Garcia's lists. Documents' copy
places appear as the detail **"Copies also kept at"**. Wine is off in Garcia, so it is not listed; it will start
on its usual rule when switched on. There are 320 choices (649 radio buttons), each a fieldset with a legend.

## Findings, worst first

### Important: medicines and doses start Shared, and nobody was asked

- **What the page shows:** Medicine doses, **"Usual: Shared with your other computers."**, with every detail
  checked Shared, the amount included. Important details' **Detail (private)** is checked **"Shared only for
  allergy, condition, medication, care or mobility need or dietary"**.
- **Why it matters:** User 1's rule is "consent based". Decision 0140 keeps 0089's choice that medical safety
  details travel, so these private things travel to the first paired computer without anyone saying yes. Money
  back, by contrast, starts Only on this computer and asks before sharing.
- **Suggested change** (no change to today's log, since nothing is sent yet): the first pairing (item 122) must
  show, before the first full copy: **"These private things are set to go to <computer name>: Medicine doses
  (with amounts) and medical details (allergies, conditions, medicines, care needs, diet). Keep them, or keep
  them on this computer?"**, with **Share them** and **Keep them here**. Until a household answers, the page
  could say beside those lists: **"Shared when you pair a computer; you will be asked first."**

### Important: the page is very long at 320px, with no way to jump

The page shows about 1,160 lines of words at 320px. It has one form, so **Save sharing choices** repeats after each
part, but there is no list of parts at the top. A household looking for "Money back" scrolls past People, Stock and
every Stock detail.

- **Suggested change:** a short contents list at the top, **"Jump to: People · Household stock · Vehicles · …"**,
  and under it a summary of what is not usual: **"You have changed 2 things from the usual: People, Notes (Only on
  this computer); Money back (Shared)."**

### Minor: "(private) (private)" on codes

Home layout's code lines read **"Codes or access details (private) (private): always only on this computer."** The
column's own label already ends in "(private)". Suggested: **"Codes or access details (private): always only on
this computer. Codes work like passwords, so they never leave the computer where they were typed."**

### Minor: the confirmation names fields, not things

**"Money back: that its records exist, and Which Stock in, Date the money came back."** Suggested words: **"Money
back: that money came back, for which Stock in, and on what day. The amounts stay on this computer."** For a
detail: **"Vehicles: each car's registration or plate number."** in place of "Vehicles: Registration or plate
number (private)."

### Minor: "Usual" is said for lists, not for details

Each list says "Usual: …", but a detail only shows which radio is checked. After a change, nothing on the detail
says what the usual was. Suggested: after a detail that differs from usual, **"(usual: Shared)"**.

## What held

- **Keeping here is immediate.** People → Notes → Only on this computer → Save: **"Saved. From now on: People,
  Notes: Shared with your other computers → Only on this computer"**, with no question asked.
- **Consent before something private travels.** Money back → Shared asked **"Start sharing these private
  things?"**. It listed what would go, and said **"Anyone using those computers will be able to see them. A copy
  another computer gets cannot be taken back later. Undo stops sharing them again from then on."**, with **Yes,
  start sharing these** and **Go back without sharing**. A private detail on an ordinary list (Vehicles,
  Registration or plate number) asked the same way.
- **Undo.** After yes, the notice and **Earlier sharing choices** both offered Undo (**"Undo this"**). Pressing it
  said **"Undone. Those things are kept on this computer again."**, and Money back was back to Only on this
  computer. The tightening (People Notes) had no Undo, which is right: keeping something here needs no consent.
- **History:** "11/27/26: Money back: Only on this computer → Shared with your other computers", in the household's
  date style.
- **The words around it are honest:** "Nothing is sent yet. Pairing your computers is not built yet"; "Anything
  another computer already has is not taken back from it."; and helper keys are named as a separate permission.
- **Width:** 320px, with no sideways scroll.

## Limits

The change log itself (what `sync.record` writes after a choice) is covered by Lane A's tests and was not read
directly. No real pairing exists to test what another computer receives.
