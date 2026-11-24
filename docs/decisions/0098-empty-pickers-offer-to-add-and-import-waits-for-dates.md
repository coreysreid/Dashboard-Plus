# 0098. An empty picker offers to add one; Import's Send waits for date choices

- **Status:** Accepted
- **Date:** 2026-11-20
- **Decided by:** Claude (technical decision delegated by User 1), from Lane B's batch 18 UX check

## In plain words
When a form asks you to choose something there are none of yet (for example
"Copies also kept at" before any copy places exist), it now says "No places
copies are kept yet. Add one in a new tab, then reload this page; what you
typed here stays." On Import, the Send button stays greyed out until you tick
that the unclear dates are read the way you meant. Documents' Notes help now
points to "Copies also kept at" instead of suggesting copy places in Notes.

## What we chose
- Any link or multi-link field with no options (and not a batch picker that
  follows another field) shows a link to the target list's Add form, opening
  in a new tab so the half-filled form is kept.
- On the Import check page, while dates that could be read either way are
  not confirmed, a status line says how many rows wait for that choice and
  "Nothing has been sent", and Send is disabled. The server already refused
  such a send (decision 0094); this makes the page say so before pressing.
- Lane B's exact Notes help replacement for Important documents.

## Why we chose it
- A dead end with no way forward is the worst kind of empty state.
- A button that looks ready but is refused feels broken.
- Two places to write copy locations would drift apart.

## What else we considered
- Adding a place inside the form (inline create): bigger, and the add form
  already handles names, paths and checks.

## What this costs us (the downsides)
- The new tab must be reloaded by hand to see the new choice.
- Without page scripts, Send only enables after Check again.

## How hard it is to undo
Easy: template and label changes.

## We should revisit this if
- People lose the first tab, or ask to add a choice without leaving the form.
