# Readiness question draft

These 49 questions are **draft content**, grouped by fire, flood, storm, heat, power cuts, medical needs and leaving home quickly. They ask a household to think; they do not assert the household is safe or give emergency instructions. Each question has one plain-language reason, an applicability filter, an exact existing field that may help answer it or `none`, a 12-month review interval and an official source checked **2026-11-16**. The interval is an editorial reminder proposal, not an authority's recommended frequency. A household can say a question does not apply.

## Exact `answered_by` mapping, checked 2026-11-17

The mapping was checked against shipped People, Pets and Household stock tables and the Home layout and Medical draft tables. All 49 entries have either a valid `module.table.field` or `none`; nine have a field and 40 have `none`. **A field is a lead for a conversation, not proof that a household has a plan.** None of the Pets fields alone answers a question about travel, shelter, cooling or supplies, so Pets is deliberately not used as a shortcut. A category such as `power` alone likewise cannot tell a torch from a battery.

| Prompt | Field | Conditions before offering “already recorded” |
|---|---|---|
| `fire-upper-floor` | `home_layout.homes.upstairs_way_out` | A nonblank route in the active home; household confirms it still works for everyone upstairs. |
| `fire-alarm-location` | `home_layout.equipment.last_tested` | A `smoke_alarm` row has both `place` and `last_tested`; household confirms it covers the alarms they mean. |
| `flood-flood-utilities` | `home_layout.shutoffs.place` | At least one relevant shut-off row has a place; show which kinds are recorded and ask if those answer the question. Do not infer a shut-off exists just because the home has gas or electricity. |
| `heat-heat-water` | `stock.items.place` | A Water row has `drinking = true`, `quantity > 0`, `unit = litres` and a linked place; show the row and ask whether this is the hot-weather source. |
| `medical-kit-location` | `medical.kits.place` | At least one nondeleted kit has a linked place; show its full path and ask if it is current. |
| `medical-prescriptions` | `people.important_info.detail` | A nonblank private detail has `kind = medication` and belongs to someone in the household; ask privately whether it contains current prescription details. Never quote it on the general home page. |
| `medical-care-contact` | `people.roles.person` | A Doctor or Pharmacist role points to a person with a phone number; ask whether this is the right contact for the specific care need. A generic contact is not enough by itself. |
| `medical-special-food` | `people.important_info.detail` | A nonblank private detail has `kind = dietary` and belongs to someone in the household; ask whether it covers food or feeding needs. Do not imply the needed food is stocked. |
| `leaving-contact-away` | `people.roles.person` | An Emergency contact role points to a person with a phone number; ask whether everyone knows to contact this person after leaving. |

For every `none`, the current records cannot establish the specific answer. Examples: an exit route does not prove two ways out of each sleeping room; a neighbour contact does not describe a flood check-in plan; a power-category stock item may be batteries rather than a light; a go-bag's place does not list what each person carries; a training record does not say whether someone wants future training. Keep asking those questions until the household answers a prompt or a future purpose-built field is added. Do not use unstructured notes, keywords or a different module's vague record as an automatic match.

### Rules the core needs for “already answered”

1. Evaluate `fits` from the household's own settings first. A country or hazard must not be inferred from an address or from another country's source. If a prompt does not fit, mark it **Not relevant** only when the person says so or the condition is decisively false; do not call the household safe.
2. Resolve the exact `module.table.field`. If the module is off, the row is deleted, the field is blank, a linked record is missing, or the conditions in the table above fail, there is no record match. `none` never triggers record matching.
3. A match can offer **“You already recorded this. Does it answer the question?”**, with a link to the record. It does not silently mark the prompt Yes. The person must choose **Yes**, **Not relevant**, **Not yet**, or **Tell me more**. Store the prompt ID, answer, date, and linked record ID used for confirmation. A yes answer means the household has looked at it, not that the plan is safe.
4. If a confirmed linked record is changed, removed, loses its required field, or becomes stale under the chosen 12-month review interval, ask the household to review that answer again. Do not erase the prior answer or expose sensitive medical text in the reminder.
5. For questions about *everyone*, one person or one pet's record is not enough. For amounts, use a positive current quantity and the right unit. For locations, require a linked full-path place. If several candidates exist, show them to the household for selection; never choose one by name similarity alone.
6. Keep source dates and the household's answer date separate. Review due dates are editorial reminders; do not turn an old source date into a household answer or a safety verdict.

## Sources and reuse

| Group | Official source and date checked | Licence |
|---|---|---|
| Fire | [US Fire Administration, Home Fire Escape Plans](https://www.usfa.fema.gov/prevention/home-fires/prepare-for-fire/home-fire-escape-plans/), 2026-11-16 | US federal government material is generally public domain; site marks third-party material separately. We paraphrase and link. |
| Flood | [NZ Civil Defence Get Ready, Floods](https://getready.govt.nz/emergency/floods), 2026-11-16 | [Get Ready copyright page](https://getready.govt.nz/about-this-site/) says Crown material is CC BY 4.0 unless marked otherwise; logos and design excluded. We paraphrase and link. |
| Storm | [NZ Civil Defence Get Ready, Storms](https://getready.govt.nz/emergency/storms), 2026-11-16 | Same Get Ready terms. |
| Heat | [US CDC, About Heat and Your Health](https://www.cdc.gov/extreme-heat/prevention/), 2026-11-16 | US federal government material is generally public domain, subject to [CDC exceptions](https://www.cdc.gov/other/website-policies.html). We paraphrase and link. |
| Power cut | [US CDC, What to Do to Protect Yourself During a Power Outage](https://www.cdc.gov/natural-disasters/response/what-to-do-protect-yourself-during-a-power-outage.html), 2026-11-16 | Same CDC terms. |
| Medical | [US CDC, Personal Needs](https://www.cdc.gov/prepare-your-health/take-action/personal-needs.html), 2026-11-16 | Same CDC terms. |
| Leaving | [NZ Civil Defence Get Ready, Make a Plan](https://getready.govt.nz/prepared/household/make-a-plan), 2026-11-16 | Same Get Ready terms. |

These sources explain why the topics may be worth considering. They do **not** establish a country-specific hazard for a particular address. An applicability filter must be a household answer or local authority setting, not a guessed risk from country alone. A missing record is not proof of missing preparedness; `answered_by` is only a place to check and confirm, never an automatic “safe” state.

## Core mapping needed

The brief's fields (`question`, `fits`, `answered_by`, `review_every`, `source`) are editorial. DESIGN 10.5 currently illustrates (`ask`, `applies_when`, `when_missing`, `review_every_days`, `sources`). Lane A should choose one versioned prompt schema, validate field names and source dates, and map a `fits` condition only to known household profile values (`home_type`, `storeys`, `hazards`, `pets`, `mobility_needs`, `country`). The draft uses `storeys_min` as a proposed numeric condition. The core needs the matching and confirmation rules above before it can use `answered_by`. Country packs should supply localized wording and local links where needed. Show only a small number of questions at a time, allow “not relevant”, “not yet” and “looked at”, and never label coverage as safety.
