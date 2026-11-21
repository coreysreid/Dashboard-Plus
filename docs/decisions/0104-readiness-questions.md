# 0104. Readiness is switched on: "Have you thought about…?" questions, answers a person chooses, and records offered, never assumed

- **Status:** Accepted
- **Date:** 2026-11-21
- **Decided by:** Claude (technical decision delegated by Corey)
- **Builds on:** DESIGN.md 10.5 (prompts), 0026 (Medical and Readiness in v1), 0054 (places), 0055 (modules confined to their own tables), 0100 (permanent IDs, revisions, change log, travel rules), Lane B's draft `workbench/drafts/readiness/` (now removed; its NOTES, SCREENS, ACCEPTANCE and examples are in git history)

## In plain words
There is now a **Readiness** module. It asks calm questions such as "If the stairs were
blocked, have you thought about how everyone upstairs would leave?", 49 in all, in seven
groups: fire, flood, storm, heat, power cuts, medical needs and leaving home quickly. Each
shows why it may matter and the official page it was written from, with the date that page
was checked. You answer **Yes**, **Not relevant** or **Not yet** (and say when to bring it
back), or open **Tell me more**. Only questions that fit what you told Settings are asked.
If one of your records may already answer a question, such as a first aid kit with its
place, it is offered as "You already recorded this. Does it answer the question?" and you
decide. If that record later changes, or a year passes, the question comes back and your
earlier answer is kept. The Questions page counts how many you have looked at. It never
says your household is safe or ready.

## What we chose
1. **A small generic core feature, the content in a module.** A module may ship
   `prompts.toml` (format version `schema = 1`, checked when the module loads by
   `core/prompts.py`). The core knows nothing about fire or floods: it reads questions,
   matches them to the household's settings, offers records, stores answers and works out
   what is due (`core/questions.py`, screens in `web/questions.py`). The draft's field names
   are kept (`question`, `why`, `fits`, `answered_by`, `review_every` in months, `source`)
   with three additions: a `title` for each source (from the draft's NOTES), a `match` that
   spells out exactly what a record must hold, and an optional `write_in` (a list where a
   plan can be written, never an answer). Groups are declared in the same file.
2. **The 49 questions are Lane B's, word for word**, with the 16 November 2026 sources and
   12-month intervals. The interval is an editorial reminder, not an authority's deadline,
   and the page says so.
3. **What fits comes only from Settings.** `storeys_min` (a home with fewer storeys is left
   out; storeys not given keeps the question), `hazards` (only hazards ticked under "Things
   that can happen where you live"; never guessed from a country or address), `pets` (pets
   recorded, or the pet count from setup), `mobility_needs` (the Settings tick),
   `country` and `home_type` (supported, unused today). A question that does not fit is
   shown as "Does not fit your settings", with the reason, and is never stored as a Not
   relevant answer. Changing settings recounts without touching any answer.
4. **Record matches are exact and only ever offered.** Eight questions have a field; the
   other 41 are `none` and never match. Each `match` names a table and lists conditions
   (`where` values, `filled` fields that must not be blank, and `positive` amounts), one
   link deep, as in the draft's NOTES: a smoke alarm with a place and a last-tested date; a
   water, power or gas shut-off with a place; a batch of drinking water in litres with a
   positive amount and a place; a first aid kit with a place; a medication or dietary
   detail of someone who lives here; a doctor or pharmacist, or an emergency contact,
   whose person has a phone number. A linked place must still exist and so must every place
   it sits inside (a full path). A deleted record, a blank field or a module switched off
   (or not installed) matches nothing. Several matches are all listed for the person to
   choose from. A match never sets an answer; a record is kept only with a Yes, and only one
   the match offers at that moment.
5. **Answers are ordinary records** in the module's own table `readiness__answers`: question
   ID, answer, answered on, look again on, an optional note, the record used (its table and
   permanent ID from decision 0100, never its words) and a fingerprint of the revisions of
   every record the match looked at (a hash of IDs and revision numbers, never content).
   One record per question: a new answer changes it and the record's history keeps every
   earlier answer, who gave it and when. "Tell me more" and "Not now" save no answer.
6. **When a question comes back ("Review again").** On the date the household chose (for
   Not yet), or, for Yes and Not relevant, the date they chose or twelve months after the
   answer; or at once when the record used for a Yes changed, moved (its place or a place
   around it), was deleted or stopped matching. The earlier answer stays in history and the
   question leaves the looked-at count until answered again. The reminder always says the
   same thing ("The record you used for this answer changed. Does your answer still fit?"),
   never what the record says.
7. **Private medical text never leaves its record.** A match on a private People detail is
   shown only as "You have a private record that may relate to this question", with a link
   to the record, where the detail stays behind Show. Home, Needs attention, the Questions
   page, sheets and the answers list never show it, and tests plant a made-up medicine name
   and search all of them.
8. **Calm by design.** Home shows at most two questions ("Have you thought about…?", the
   question, why, **Look at this**, **Not now** for a week); ones to look at again come
   first. Needs attention lists three, under "A few questions to think about when you have
   time", and never the number left unanswered. The Questions page says "23 of 49 questions
   looked at", or "23 of 35 questions that fit your household looked at" and "14 do not fit
   the settings you gave", per group too, with the caption "Looked at means someone answered
   a question. It does not say whether your household is safe or ready." Filters: To look
   at, Looked at, Review again, Not relevant, Does not fit settings.
9. **Helpers may look, never answer.** A new table setting, `suggestions = false`, means a
   person fills the table in on its own screens: helpers given Readiness can read answers
   like any table, but `/tables` says they cannot suggest, a suggestion is refused, and a
   spreadsheet cannot be imported into it. `prompts.toml` requires it on the answers table.
   The helper `/attention` reply does not include questions.
10. **Answers travel.** They are ordinary household planning, so every column travels to the
    household's other computers later (`travels` default, decision 0100), appears in the
    change log, the spreadsheet export and every backup, and a restore brings back the
    answers of the chosen backup.
11. **Example households:** Smith (upstairs route and pets in heat: Not yet; contact after
    leaving: Yes), Garcia (equipment that needs power, go-bags: Not yet) and Taylor (storm
    warnings, contact after leaving: Not yet), from the draft's example rows, each with a
    date to bring it back. `readiness` is added once to each setup `modules` line.
12. Tests: `tests/test_module_readiness.py` covers every one of Lane B's 12 acceptance checks
    a computer can run, plus the prompt file checks, module off and on, the examples,
    privacy, the change log, export, helpers and restore. The browser check opens the
    Questions page and a question and answers one.

### The shape for "Think it through" drills (not built)
A drill is a short ordered run of questions for one situation (a burst pipe in a wall, a
bedroom fire at night, a 72-hour power cut). It will be a `[[scenario]]` in `prompts.toml`
(`id`, `title`, `intro`, `fits`, `source`, and `steps = ["prompt-id", …]`). Steps reuse
ordinary prompts, so each has its own wording, source, `match` pointing at the household's
records and answer; a drill-only question is a prompt with a `group` and a flag so it is not
listed on its own. Answers stay one per question in the same table, so answering inside a
drill also counts on the Questions page and vice versa. A "date practised" will be one more
column (or a small drills table) with its own review date. Nothing else in this decision
needs to change.

## Why we chose it
- The draft's rules are mostly about not over-claiming: an exact, declared match is the only
  way to be sure a record is not used as proof by keyword or similarity.
- Answers as ordinary records get history, backups, export, the change log and helper
  reading for free, through the one write path every record already uses.
- Fingerprints of revisions notice any change to the record (or its place) without keeping
  a copy of anything private.

## What else we considered
- **Answers in a core table.** It would need its own export, sync and history handling.
- **Letting helpers suggest answers through Review.** Allowed by the brief, but an accepted
  "yes" would carry no confirmed record and invites accepting many at once; looking is
  enough for now.
- **Using Set up my home's rooms and doors (0103) to answer "two ways out".** Tempting, but
  a recorded door is not a plan for everyone when one route is blocked; the draft says a
  purpose-built field must be reviewed first.
- **Matching more than one link deep, or by text.** Not needed for these eight; text
  matching is exactly what the draft forbids.

## What this costs us (the downsides)
- Any edit to a matched record, even one unrelated to the question (a kit's last-checked
  date, water used from a batch), brings the question back. Honest but sometimes chatty.
- Switching off a module whose record was used (Medical, say) brings that question back.
- A Yes or Not relevant comes back after a year even when nothing changed.
- Questions fit only on what Settings say; a household that never ticks a hazard never sees
  those 21 questions until it does.
- Not now is kept on this computer only (a setting), and lasts a week.
- The answers list (Your answers) shows the question's short ID, not its words; answering
  from the Questions page is the easy way.
- A note on an answer is ordinary text: it is exported and will travel. The form says to keep
  medical details in People.

## How hard it is to undo
Easy for the content: switch Readiness off in Settings (answers are kept) or remove the
folder. Medium for the core: `prompts.py`, `questions.py`, the question screens and the
`suggestions` table setting would be removed together; no other module uses them, and no
existing record changes.

## We should revisit this if
- Households find questions coming back too often after small edits.
- A country pack needs local wording or links (the `country` fit is ready for it).
- Lane B's drill scenarios need something the shape above cannot hold.
- A purpose-built field (for example "everyone can leave when the stairs are blocked") is
  added; its match must be reviewed before use.
