# Eight short drills in the household's own words

Designed **21 November 2026**. These are calm practice runs for invented situations, **not active-incident instructions**. The first screen says: **If anyone is in immediate danger, call the local emergency service first: 000 in Australia, 911 in the United States, 999 in the United Kingdom. Follow the operator, current warnings and your building's instructions.** Those numbers are sourced in [SOURCES.md](SOURCES.md), key B/F; no number is presumed for a different country. For a country without a checked source, show **Use your local emergency number** instead. Each row below is one question, the exact record offered, and the exact empty-state words. A record is never accepted as an answer on its own. The user chooses an answer and a review date under [STATE.md](STATE.md).

## 1. Water behind the bathroom wall

**Applies:** any household, as a pipe-leak thought exercise. No claim that a leak is happening. **Source:** P and L; no pipe-repair instruction is supplied.

| Question | Offer from records | If missing |
|---|---|---|
| “What sign might tell you water had been leaking before you noticed it, and how long could that have gone unseen?” | The person's own answer; no sensor or inference exists. | “No leak-check plan is recorded. Think about how you would notice and whom you would ask.” |
| “Where is the water shut-off you would check, and could everyone who needs it find it?” | `home_layout.shutoffs` with `kind = water`, linked `stock.places` full path; Show private access detail only on its own record. | “You haven't recorded where your water shut-off is.” |
| “Who would you contact for help with the leak or damaged wall?” | `people.roles` for tradesperson, with linked `people.people.phone`; never invent a plumber. | “You haven't recorded a person to call about a leak.” |
| “What would you want to check or photograph once the situation is safe?” | Own answer only; optional Home care job or Important document place if entered. | “No follow-up is recorded yet.” |

**Save:** four own answers, any chosen record IDs, practised date and chosen review date. Do not record an estimated leak duration as a measured fact.

## 2. Bedroom fire at night, alarm sounding

**Applies:** all home types, with a shared-building-plan branch for flats. **Source:** F and London flat guidance.

| Question | Offer from records | If missing |
|---|---|---|
| “Which alarm would alert people near this sleeping room, and when did you last check it?” | `home_layout.equipment` with `kind = smoke_alarm`, `place`, `last_tested`; offer, do not certify working status. | “You haven't recorded a smoke alarm near this room or a check date.” |
| “If the usual doorway could not be used, what other way would your household check in person?” | `stock.places` sleeping room and `stock.connections` to other rooms/outside; `home_layout.exits.route` if recorded. A graph line is not a safe route. | “You haven't recorded another possible way from this room.” |
| “Where would everyone meet outside, and who might need help getting there?” | Meeting-place answer and People roster; no medical/private detail shown in prompt. | “You haven't written down an outside meeting place or help plan.” |
| “If this is a shared building, what does its own fire plan tell your household?” | Household's confirmed building-plan note, if later built; do not infer from room graph. | “You haven't checked your building's fire instructions here.” |

**Save:** own plan/unknown answers and practice/review dates. Do not mark two independent exits confirmed from connections alone. Fire-service advice to leave and stay out, and flat-specific limits, are in F.

## 3. Kitchen fire while dinner is being made

**Applies:** households with a kitchen or cooking area. **Source:** K and F. This drill asks about alerting and leaving; it does not teach firefighting or decide whether a fire is small enough to tackle.

| Question | Offer from records | If missing |
|---|---|---|
| “Who is likely to be in the kitchen or nearby at dinner, and how would you alert them?” | `people.people` marked `lives_here`; own plan. | “You haven't recorded who is usually at home; add or check People.” |
| “Which ways from the kitchen lead outside without relying on the cooking area?” | Kitchen `stock.places`, `stock.connections`, and `home_layout.exits`; no route safety inference. | “You haven't recorded a way out from the kitchen area.” |
| “Where is the outside meeting place, and how would you check everyone is there?” | Own meeting-place answer and household People list. | “You haven't recorded an outside meeting place.” |
| “Which alarm is recorded near this area, and when did someone last check it?” | `home_layout.equipment` smoke-alarm rows. | “You haven't recorded an alarm and check date near the kitchen.” |

**Save:** own answers, chosen records and dates. USFA's cooking-risk fact is in K; no appliance, extinguisher or blanket is presented as a reason to delay calling for help.

## 4. Someone breaking in at 2 am

**Applies:** any household; security details stay private. **Source:** B for emergency numbers only. The questions do not give confrontation or legal advice.

| Question | Offer from records | If missing |
|---|---|---|
| “If you believed someone was entering while people were home, who would call the local emergency service and what address would they give?” | `people.people` household roster and the household's own address if recorded; never put it in a notification. | “You haven't recorded who would call or the address to give.” |
| “How would you account for children, visitors or anyone who needs help without assuming where they sleep?” | People roster and private own answer, not a displayed bedroom map. | “You haven't discussed who may need help at night.” |
| “What part of your plan still depends on a lock, door or phone you have not checked?” | Own answer; `stock.connections` can show doors but not security or access. | “You haven't checked those parts of the plan here.” |
| “Who would you contact after the immediate danger has passed?” | `people.roles` emergency contact or neighbour with phone. | “You haven't recorded a follow-up contact.” |

**Save:** private own answers and dates. Never display an access code, hiding place, key location or detailed route in the general drill list, export or helper view.

## 5. Car stops 150 km from home

**Applies:** households with a recorded vehicle; UK motorway safety facts in R apply only when on that road type. **Source:** R and B; local road authority advice is needed elsewhere.

| Question | Offer from records | If missing |
|---|---|---|
| “Which vehicle is this, and how would you describe your location to help?” | `vehicles.vehicles` name; the person supplies current road/location, never a guessed GPS position. | “You haven't recorded this vehicle or a way to describe your location.” |
| “Who would you call about the breakdown, and is the number current?” | `vehicles.vehicles.roadside_contact` → `people.people.phone`; ordinary emergency service first if immediate danger. | “You haven't recorded who to call if this vehicle breaks down.” |
| “What is in the vehicle now that you would rely on, and what might have been moved out?” | `vehicles.vehicles.emergency_kit` → `stock.items`/lots, plus Medical kits with `kept = vehicle`; last recorded amounts only. | “You haven't recorded a vehicle kit here; check the vehicle itself.” |
| “How would someone at home know where you are and whether you need collection?” | `people.roles` emergency contact with phone; own answer. | “You haven't recorded a contact or collection plan.” |

**Save:** own answers and dates; 150 km is fictional scenario context, not a distance trigger or coverage promise. Do not show a UK motorway procedure to an AU/US/NZ household.

## 6. Power stays off for 72 hours

**Applies:** any household, especially where power-dependent care is recorded. **Source:** E (US CDC; local advice first elsewhere).

| Question | Offer from records | If missing |
|---|---|---|
| “Which people, pets or equipment in your home need power, and what would you check first?” | People medical Important details only as **private record may relate**; `stock.items` power category; own answer. | “You haven't recorded power-dependent needs here.” |
| “Where are torches, batteries and any other recorded light sources, and are their amounts current?” | `stock.items` power category, positive `stock.lots`, full Places paths. | “You haven't recorded where your light supplies are.” |
| “What would you do about food that needs refrigeration, using current local health advice?” | Stock items/batches are an inventory, not proof of food safety; own answer. | “No food plan is recorded; check local health advice.” |
| “Where would you get official outage updates and whom would you contact if you needed help?” | Utilities service/fault contact if present, `people.roles` emergency contact; own official-source choice. | “You haven't recorded an outage contact or update source.” |

**Save:** own answers and dates. Do not claim that food stays safe for 72 hours or that a generator is safe indoors; CDC cautions about carbon monoxide in E.

## 7. A region-wide unsafe-tap-water warning

**Applies:** a *hypothetical* authority warning in a household's region, such as South East Queensland; **no current warning is asserted**. **Source:** W (US CDC principles); the live local water authority's exact advisory controls AU/UK/NZ actions.

| Question | Offer from records | If missing |
|---|---|---|
| “Which authority issued the warning, what area and uses does it cover, and when will you check for an update?” | Person-chosen official warning source; do not derive from household postcode or an old link. | “You haven't recorded the current official warning or its update source.” |
| “Which water you have already recorded is separate from the tap supply and answered safe to drink now?” | `stock.items` `category = water`, `drinking = true`, unit litres, positive `stock.lots`; show last count and Place. Do not automatically bless stored water. | “You haven't recorded drinking water in litres that you marked safe to drink now.” |
| “Who in the household and which pets need that water, and what is the recorded days estimate?” | Setup person/pet counts and Stock's drinking-water calculation; show basis/date, not guarantee. | “A days estimate cannot be shown until people, pets and safe litres are checked.” |
| “What will you do for uses not covered by your stored water, following the actual advisory?” | Own answer and authority text only. | “You haven't decided how to follow this warning yet.” |

**Save:** source URL/title as checked by person, their own answers and dates. Do **not** offer a generic boil instruction: W says chemical contamination cannot be made safe by ordinary boiling/disinfection.

## 8. Cyclone or hurricane forecast near the suburb

**Applies:** AU where cyclone is a selected local hazard; US where hurricane is a selected local hazard. Other regions need their own sourced wording. A forecast track is not a claim that a suburb will be hit. **Source:** C for AU warnings; US version uses the checked National Weather Service page in C and still needs the household's current local authority warning.

| Question | Offer from records | If missing |
|---|---|---|
| “Which official forecast or warning covers your area, and when will you check it again?” | Person's chosen BOM/state source for AU; US official source only after verified. | “You haven't recorded which official warning source to check.” |
| “Who might need help with a change of plan, and how will you reach them?” | `people.roles` emergency contact and People phone, pet roster; private care details remain behind Show. | “You haven't recorded a contact and help plan for everyone.” |
| “Which ways out, go-bags and drinking water are currently recorded, and what would you check in person?” | `home_layout.exits`, `home_layout.equipment` `go_bag`, Stock lots and safe drinking-water estimate; accepted records only. | “You haven't recorded a way out, go-bag or checked drinking-water amount here.” |
| “If local authorities change the warning or advise leaving, what would need to change in your household's plan?” | Own answer, current official warning, vehicle and contact records if present. | “You haven't practised how you would update the plan.” |

**Save:** own answers, official source checked, date practised and chosen review date. Never infer evacuation from a forecast line or replace live authority advice with stored household records.
