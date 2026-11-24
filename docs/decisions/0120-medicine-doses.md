# 0120. Medicine doses: one private entry per dose, from that person's own medication details

- **Status:** Accepted
- **Date:** 2026-11-24
- **Decided by:** Claude (technical decision delegated by User 1)
- **Builds on:** 0059 (private details behind Show), 0071 (a private page needs a pressed button, not a link),
  0089 and 0100 (sync: medical safety details travel to members; every private column says whether it travels),
  0104 (`suggestions = false`), 0110 (timed entries, the `daily` declaration, `core/daily.py`, possible repeats),
  0111 (Go back or Save as entered), 0115 (optional links); Lane B's draft `workbench/drafts/medicine_doses/`
  (batch 20 item 90, now removed; its PLAN, FLOW, NOTES and ACCEPTANCE are in git history)

## In plain words
A household can now write down each dose of medicine someone was given. On a person's page, **Medicine given
today** says "1 dose entry recorded today" and lists the times ("8:00 am · dose · Who gave it: Maria Garcia").
**Record a dose** opens a short form with the person, the time now and, for checking, the medicine and the giver
of the last dose already filled in. The medicine is chosen from that person's own medication details in People →
Important details; the list shows "Medication #3", and **Show the chosen medicine** reads it out. The amount is
optional and is never copied from an earlier dose. If the same medicine was already recorded for that person
within two hours, the form asks first: "A dose of this medicine is already recorded for this person near this
time. Check both before saving." with **Go back** or **Keep this as another dose**. **Dose history** goes day by
day; **Show details** (a pressed button) shows each medicine and amount and each medicine's own total for the day.

Doses are private medical history. They are never on Home, on a printed sheet, in the spreadsheet export, in
Needs attention, or visible to a helper, and no helper or spreadsheet can add one. Nothing ever says a dose was
missed or is due.

This is for people only. A pet's medicine already has **Pets → Treatments given**, and Lane B's draft says not to
mix the two.

## What we chose
- **A new module, `modules/medicine_doses/`**, requiring only People. One table, Medicine doses
  (`medicine_doses__doses`): Given to (`recipient`, a person), Medicine (`medication`, a People Important detail),
  When was it given? (`given_at`), Who gave it? (`given_by`, optional, blank reads "I do not know"), and an
  optional Amount and Unit (private). No notes column: free text about medicine is the easiest place for a secret
  to leak. Deleting the person, the giver or the medication detail is refused while doses point at them
  (`on_delete = "restrict"`), so safety history is never silently cascaded away.
- **A generic `link_rule` on a link column**, checked by the record service on every save, never trusted to the
  form: `link_rule = { where = { kind = "medication" }, same = { person = "recipient" }, shows = "detail" }`. The
  linked record must have those choices (`where`) and the same value as this record's own link (`same`); `shows`
  names its private column a person may Show from the form. It is checked on create, change, the dry run Review
  and imports use, and restore (a deleted dose comes back only if it still fits). Changing the linked record so a
  live dose would no longer fit (a medication detail turned into an allergy or moved to another person) is
  refused too; its words can still change. The module checker refuses a rule that compares a private column,
  names a choice that does not exist or a `same` link that points elsewhere. The form lists only allowed records,
  by kind and number, and the list follows the chosen person (the batches code from DESIGN 5.7).
- **A generic table setting `private = true`.** Every record is private history: the table is left out of Home,
  the export (its README names it as left out), the helper API (`allowed_registry` drops it, so it reads exactly
  like a table that does not exist), the helper settings choice (a module with only private tables is not
  offered) and the "Add to" buttons on other records' pages. It must also say `suggestions = false` (helpers and
  imports refused, decision 0104), and may not use `watch`, `chart`, `actions` or `takes_over`, or be printed by
  a sheet, because each would show its records elsewhere.
- **The 0110 `daily` declaration, extended rather than copied.** `group = "medication"` keeps each medicine's
  totals apart ("1 tablet given", never tablets and drops together). On a private table the amount and unit may be
  private; the person's page and the day page then say only how many and when, and the **Show details** button
  (a POST with the session check, like the private sheet of decision 0071, so no link or bookmark opens it) shows
  the medicines, amounts and per-medicine totals on that page only. No sheet exists (404) and no Home line.
  Household days, offsets and late entries work exactly as in 0110.
- **Possible repeats on the form.** `repeat` gains `form` (the question) and `keep` (the button), so a table
  nobody suggests into can still ask before saving: same person and medicine within 120 minutes of an accepted
  dose. It uses 0111's Go back / Save as entered box with the household's words. A double press of Save lands
  here instead of saving twice. Changing an entry never matches itself. It only ever asks.
- **Fast entry.** Record a dose fills in the person, the household's time now and the last medicine (only if it is
  still one of theirs) and giver, with "Filled in from a recent entry. Check each answer before you save."; a person
  with exactly one medication detail has it chosen. Save returns to the person's page. Someone with no medication
  detail and no doses gets no panel; the day page lists only people it applies to.
- **Travel (decision 0089 and 0100).** Medical safety details travel to members, so every column says
  `travels = "always"`, the private amount and unit included. The change log carries the dose's permanent ID, the
  recipient's, medicine's and giver's permanent IDs, the time and the amount; the medicine's words travel only
  through People's own rule for medication details. Pairing is not built yet; when it is, its screen must say
  plainly that a paired member learns this history.
- **Examples:** Garcia (Rosa, two doses yesterday from her medication detail, one with "1 tablet" and Maria as
  giver, one with no amount and no giver). Smith and Taylor do not switch the module on.
  `tools/load_example.py` now accepts a link written as `{ person = "Rosa Garcia", kind = "medication" }` for a
  record that has no name of its own.

## A later calendar view
The calendar hook is `daily.days(conn, info, subject_id, start, end, zone)` with `daily.by_group(rule, day)`: it
already returns every household day in a range (empty days stay empty, never "missed") with each medicine's
entries and totals. A calendar for doses should be a private page like Dose history: counts and times by day
until a pressed **Show details**, no colours or marks that encode which medicine, never on Home or a sheet, and
no "missed" or "due" state. It needs only a template and a route that call those two functions.

## Why we chose it
- User 1's old tracker had about 93 individual medicine doses with nowhere to live, and User 1 wants to track
  medication again, visually later. A per-dose record linked to the existing People summary keeps one source for
  the medicine's words, as the draft asked.
- The draft could not ship as files because a link could not be limited to the same person and the medication
  kind. A rule in the record service closes that on every path, including ones a form never sees.
- One `private` switch covers every place a list can surface, so a later private module cannot forget one.
- Reusing `daily` keeps one meaning of the household's day and one possible-repeat match for feedings and doses.

## What else we considered
- **Adding the table to Medical readiness.** That module requires Stock too; doses need only People, and a separate
  module can be switched off on its own.
- **Copying the medicine's words into each dose** for history. Refused as in the draft: a hidden second copy of
  medical text with its own erasure questions. A dose points at the detail; if its words change, old doses show the
  new words after Show. A reviewed historical label is left open.
- **Showing the medicine's words in the picker.** They are private; the list says "Medication #3" and Show reads it.
- **Refilling the last amount.** Refused: the draft says an amount is copied from the pack, never from memory.
- **Show details as a link (`?show=1`).** Refused like the private sheet (0071): a link can be shared or bookmarked.
- **Warning only on Review**, as feedings do. Doses never reach Review, so the question is asked on the form.
- **Pets.** Pets already record treatments given; folding them in would mix two models, so this is people only.

## What this costs us (the downsides)
- If a medication detail's words are edited, earlier doses show the new words after Show; there is no snapshot of
  what was chosen at the time.
- A medication detail with doses cannot be turned into another kind or moved to another person; the household adds
  a new detail instead. A person, giver or medicine with doses cannot be deleted until the doses are dealt with.
- Two medicines written in one detail ("A and B") count as one medicine in the day's totals.
- The repeat window (two hours) is a guess. Someone given the same medicine more often than that is asked each time.
- The list of every entry (`/t/medicine_doses__doses`) still shows who, when and "Important details #3"; it hides
  only the amount. The Backups preview counts its rows. Backups hold everything, as before.
- Times show as "8:00 am" whatever the household's date order, as in 0110; the form's default "now" is this
  computer's clock when the form is opened directly rather than from Record a dose.
- Members, offline saves on a phone, "waiting for main" and the pairing notice wait for sync stage 2. Marking an
  entry mistaken is an ordinary delete (kept in history, restorable), not a separate state.
- A household that switches People off cannot record or see doses (the module requires People).

## How hard it is to undo
Easy. Switch the module off in Settings (records are kept) or remove the folder. To remove the core parts: the
`link_rule` and `private` checks in `modules.py`, the rule checks in `records.py`, `web/private_daily.py` and its
panel template, the `group`/`form`/`keep` daily keys, the private-table lines in `helpers.py`, `proposals.py`,
`export.py`, `home.py`, `export_page.py`, `helper_settings.py` and `pages.py`, and the picker lines in
`display.py`. No core table or migration was added.

## We should revisit this if
- A household edits a medicine's words and is confused by what old doses show.
- People want a calendar or a chart of doses (use the hook above), or reminders, which need a separate, checked
  schedule and explicit consent.
- Member phones start syncing: the pairing screen must say medical history travels.
- A dose is ever shown on Home, a sheet, an export or to a helper.
