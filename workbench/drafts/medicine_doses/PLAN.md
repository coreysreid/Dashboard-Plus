# Individual medicine doses beside the existing summary

Designed **21 November 2026** for batch 20 item 90. This is a **design draft**, not a loadable module: the current file contract cannot enforce that a linked People detail has `kind = medication`, and the private picker needs a reviewed boundary first. No shipped code or live medical record is changed.

## Ownership

The shipped **Medical readiness** module covers first aid kits, kit checks and first aid training. It has **no per-medicine summary**. The current medicine summary is **People → Important details**, one sensitive `kind = medication` row linked to a person. Design §6 explicitly puts medicines there. A dose history belongs **beside that People summary** in a future Medical extension, because a dose is a dated event about a person and their medication, while Medical is already the household's health/readiness area. Do not copy the medicine text into a second summary table. Do not confuse a human dose with `pets.given`, which is for pet treatments.

## Proposed records

One `medical.doses` row records **who** (`recipient`: `people.people` stable ID), **what** (`medication`: stable ID of `people.important_info`, required to have `kind = medication` and the *same* `person` as recipient), **when** (`given_at`: actual local time plus zone/instant), and **by whom** (`given_by`: `people.people` stable ID, with an explicit **I do not know** state if genuinely unknown). Also record optional `amount_given` exactly as written on the pack or instruction, optional `source` (person or reviewed helper/member), and an immutable created/updated history. There is no inferred dose, schedule, due date, adherence score, missed-dose alert, or advice. A person may record two real doses close together; possible repeats need a warning and a deliberate decision, not automatic collapse.

The medication text remains in People `important_info.detail`; the dose row stores a **link**, not a second free-text medicine name. If the People summary is edited, a historical dose must retain a safe display snapshot of what the person selected at recording time **without exposing it in ordinary lists or logs**. That snapshot is a new sensitive medical value with `travels = "always"` under the decision 0089 medical-safety exception, or the product must explicitly choose a local-only history instead. Do not implement a hidden copy until that choice and its erasure behavior are reviewed. Deleting the person or summary while doses exist should be refused with a path to archive or correct the history; silent cascade would destroy safety evidence.

## Privacy and member travel

Recipient, giver, time and medication link are medical facts even if technically ordinary links. `amount_given` and any medicine snapshot are **sensitive medical details**, explicitly `travels = "always"` if stage 2 is to keep household members' safety information consistent. Decision 0100 says an unreviewed sensitive field stays local and blocks exchange; no implicit default is acceptable. These values must remain hidden behind **Show details** on screens, absent from ordinary lists, notifications, helper reads, public API errors, general spreadsheet export and ordinary sheets. An explicit warned private medical sheet could be designed later; no dose sheet is proposed now. Local backups still contain values; Dashboard is not an encrypted vault. A member pulls accepted medical doses and can save a new one offline, but its row waits on main's Review and must never be counted as accepted before that. This would disclose medical history to a paired household member by design; pairing must say so plainly and require household agreement.

**Helper boundary:** the current helper API never reads private detail and can only suggest new rows. A helper cannot safely choose a medication by its hidden text or verify recipient against it. Do not grant helper dose writes in v1. An assistant may guide a person to the on-device form but must not read a medication summary, invent an amount, or submit an opaque ID guessed from ordinary lists. Revisit only with a separately reviewed, explicit medical permission and consent flow.

## Invented example

For the repository's fictional Garcia household, Rosa Garcia has a `People → Important details` medication row. An invented entry might be **Rosa Garcia · [medicine hidden] · 20/11/26, 8:00 am · given by Maria Garcia**. This is a shape example, **not a claim that a dose was actually given**, a prescription, or a recommended time. No real medicine or dose quantity is in this draft.
