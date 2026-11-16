# Readiness question draft

These 49 questions are **draft content**, grouped by fire, flood, storm, heat, power cuts, medical needs and leaving home quickly. They ask a household to think; they do not assert the household is safe or give emergency instructions. Each question has one plain-language reason, an applicability filter, a proposed record that could answer it, a 12-month review interval and an official source checked **2026-11-16**. The interval is an editorial reminder proposal, not an authority's recommended frequency. A household can say a question does not apply.

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

The brief's fields (`question`, `fits`, `answered_by`, `review_every`, `source`) are editorial. DESIGN 10.5 currently illustrates (`ask`, `applies_when`, `when_missing`, `review_every_days`, `sources`). Lane A should choose one versioned prompt schema, validate field names and source dates, and map a `fits` condition only to known household profile values (`home_type`, `storeys`, `hazards`, `pets`, `mobility_needs`, `country`). The draft uses `storeys_min` as a proposed numeric condition. `answered_by` strings such as `home_layout.exits` mean “inspect a related record”; the engine needs explicit matching conditions and an answer confirmation before suppressing a question. A record's mere existence must not falsely answer a question about its content. Country packs should supply localized wording and local links where needed. Show only a small number of questions at a time, allow “not relevant”, “not yet” and “looked at”, and never label coverage as safety.
