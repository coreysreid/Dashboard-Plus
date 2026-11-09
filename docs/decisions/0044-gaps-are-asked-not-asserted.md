# 0044. Gaps are declared in module files and asked as questions

- **Status:** Accepted
- **Date:** 2026-11-09
- **Decided by:** Claude (technical decision delegated by Corey)

## In plain words
The Needs attention page now has a *Worth filling in* list: things the household
would want written down before an emergency, such as "What is Neighbour B's
phone number? They are in Who to call (Emergency contact), but no number is
saved." Each comes with a *Fill this in* link straight to the right form, and
it disappears once filled in. The home page counts them.

## What we chose
- A general core feature, declared in a table's `watch` section as `gaps`
  (DESIGN 5.4), not code in the People module. Two kinds: `none` (nothing
  recorded yet, such as no emergency contact) and `missing` (a detail left
  blank, such as a contact's phone, including on a linked record).
- People asks four things: who lives here, who the emergency contact is,
  whether there is a doctor, and the phone number of anyone in Who to call.
  Someone in several roles is asked about once.
- Every message is a question, then the fact behind it.

## Why we chose it
- The emergency sheet (journey J3) is only as good as its phone numbers; a gap
  found now beats one found during a power cut.
- Declared in files, so Pets (a vet with no number) and Medical (a kit with no
  check date) can reuse it without code, and the second agent can draft them.
- "Ask, don't assert, and ask sensibly": the four People questions apply to
  nearly every household, so none of them is a dumb question.

## What else we considered
- Hard-coding the checks in People: quicker today, but every module would need
  code, which breaks the "modules are files" rule.
- Making gaps part of prompts (M3): prompts need profiles and answers that are
  not built yet; gaps are simpler and needed for M1.
- Allowing "not relevant" on gaps: needs stored answers, which come with
  prompts. Until then, gaps are limited to questions nearly everyone should
  answer.

## What this costs us (the downsides)
- A household with no doctor sees that question until prompts can record "not
  relevant".
- Messages are plain text with `{column}` slots only; no plurals or grammar
  rules.

## How hard it is to undo
Easy. Remove the `gaps` sections; nothing is stored in the database.

## We should revisit this if
- Testers find a gap question irrelevant to them: move it to prompts.
- Modules need conditions beyond "nothing matches" and "this is blank".
