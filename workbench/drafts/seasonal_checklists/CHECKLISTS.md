# Seasonal household checks

Drafted and source-checked 17 November 2026. These are questions for a household to answer, not safety instructions or a claim that a record makes it ready. A Stock category can point to things to inspect but cannot prove that the right item is present or usable. A Home layout link opens a relevant record; its contents still need a person to check. “When” below controls when to *offer a review*, never when an emergency will happen. Ask for the household's location and the local authority before showing a hazard-specific list.

| Key | Checklist and when to offer it | Official source checked |
|---|---|---|
| `bushfire` | Before the locally identified bushfire season, and again if the local fire service asks for review. No single Australian start month is assumed. | [NSW Rural Fire Service, bush fire survival plan](https://www.rfs.nsw.gov.au/plan-and-prepare/bush-fire-survival-plan) and [emergency survival kit](https://www.rfs.nsw.gov.au/plan-and-prepare/prepare-your-family/emergency-survival-kit), 17 Nov 2026. NSW examples; use the local fire authority elsewhere. |
| `cyclone` | Before **1 November** in the Australian tropical cyclone region and whenever official local advice changes. The [Bureau of Meteorology](https://www.bom.gov.au/climate/cyclones/australia/index.shtml) names 1 Nov–30 Apr as the official season, but cyclones can occur outside it. | [Get Ready Queensland, cyclone and storm surge](https://www.getready.qld.gov.au/during/cyclone-and-storm-surge) and [Queensland emergency kit](https://www.getready.qld.gov.au/prepare/kit), 17 Nov 2026. Queensland examples, not all Australian addresses. |
| `winter_storm` | Before locally forecast winter weather or a local winter-preparation campaign; no universal month. | [US National Weather Service, prepare for winter storms](https://www.weather.gov/safety/winter-before) and [UK Met Office, prepare for winter](https://weather.metoffice.gov.uk/warnings-and-advice/seasonal-advice/10-things-you-should-do-now-to-prepare-for-winter), 17 Nov 2026. Use the chosen country's local warning service. |
| `heat` | Ahead of a locally forecast heat event; not every hot day or an invented temperature threshold. | [US CDC, About Heat and Your Health](https://www.cdc.gov/extreme-heat/prevention/) and [National Weather Service heat alerts](https://www.weather.gov/safety/heat-ww), 17 Nov 2026. Health guidance is linked, not reproduced as a household instruction. |
| `hurricane` | Before **1 June** where Atlantic or central Pacific hurricane risk applies, and when official alerts change. [NOAA](https://www.noaa.gov/prepare-before-hurricane-season) states the official 1 Jun–30 Nov season; this date is not a Pacific-wide rule. | [NOAA, prepare before hurricane season](https://www.noaa.gov/prepare-before-hurricane-season) and [assemble disaster supplies](https://www.noaa.gov/assemble-disaster-supplies-hurricane-preparedness), 17 Nov 2026. |

## Bushfire (`bushfire`)

Show only when the household identifies bushfire as locally relevant or selects its fire authority. Source for all five questions: [NSW RFS plan and kit](https://www.rfs.nsw.gov.au/plan-and-prepare/bush-fire-survival-plan), checked 17 Nov 2026.

| Question shown | Open these records for the person to check |
|---|---|
| “Have you reviewed your household's bushfire plan with everyone it affects?” | `home_layout.homes.upstairs_way_out`, `home_layout.exits.route`; a route is a lead, not a survival plan. |
| “Do you know where the kit you would take is kept?” | `home_layout.equipment[kind=go_bag].place`, full path. |
| “Have you checked the water and supplies you chose to keep?” | `stock.items[category=water, drinking=true]` and `stock.items[category=first_aid]`; show amounts and dates, no automatic pass. |
| “Have you checked the ways out and where local warnings will come from?” | `home_layout.exits`, and a locally chosen warning-source link; absence of exits is a question, not proof none exist. |
| “Are the recorded safety items and their check dates still current?” | `home_layout.equipment` with `kind=smoke_alarm` or `fire_extinguisher`, `place`, `last_tested` and `next_check`. |

## Tropical cyclone (`cyclone`)

Show only where a local authority or household says cyclone risk applies. Source for all five: [Get Ready Queensland cyclone guidance](https://www.getready.qld.gov.au/during/cyclone-and-storm-surge), checked 17 Nov 2026.

| Question shown | Open these records |
|---|---|
| “Have you checked your household plan and local cyclone or storm-surge advice?” | `home_layout.homes`, `home_layout.exits` and chosen local authority link. |
| “Can you find the emergency kit and go-bags you recorded?” | `home_layout.equipment[kind=go_bag].place`; full paths. |
| “Have you reviewed your stored drinking water and food?” | `stock.items[category=water, drinking=true]`, `stock.items[category=pantry]`; amounts and dates. |
| “Have you checked the power, lights and first-aid items you chose to keep?” | `stock.items[category=power]`, `stock.items[category=first_aid]`; item names matter, category alone does not prove a torch or charger. |
| “Do you know the recorded shut-off and safe-item locations?” | `home_layout.shutoffs.place`, `home_layout.places` by full path; no instruction to operate a shut-off. |

## Winter storms (`winter_storm`)

Show where winter-storm exposure is confirmed by the household or local authority. Source for all five: [NWS winter preparation](https://www.weather.gov/safety/winter-before) and [Met Office winter preparation](https://weather.metoffice.gov.uk/warnings-and-advice/seasonal-advice/10-things-you-should-do-now-to-prepare-for-winter), checked 17 Nov 2026.

| Question shown | Open these records |
|---|---|
| “Have you checked how you will receive local winter-weather warnings?” | Chosen country/local warning link; no stock item can answer this. |
| “Have you reviewed the lights and power items you actually have?” | `stock.items[category=power]`, with item name, quantity and place. |
| “Have you checked your household's stored water and food?” | `stock.items[category=water, drinking=true]`, `stock.items[category=pantry]`. |
| “Have you reviewed where your winter kit is, including any car kit?” | `home_layout.equipment[kind=go_bag].place` and `home_layout.places` path under Car if recorded. |
| “Have you checked the exits and equipment records that matter in your home?” | `home_layout.exits.route`, `home_layout.equipment.next_check`. |

## Heat (`heat`)

Show ahead of a forecast event where the household chooses to track heat. Source for all five: [CDC heat-health overview](https://www.cdc.gov/extreme-heat/prevention/), checked 17 Nov 2026.

| Question shown | Open these records |
|---|---|
| “Have you thought about somewhere cooler to go if home becomes too hot?” | `home_layout.homes.notes` only as a lead; a dedicated plan field is not shipped. |
| “Have you checked your drinking-water records and where it is kept?” | `stock.items[category=water, drinking=true, quantity>0, unit=litres].place`. |
| “Have you thought about who may need a check-in?” | People roles as a lead; do not show private medical details on this checklist. |
| “Have you checked where pets could be comfortable during heat?” | Pet records as a lead; no Pet field proves a cooling plan. |
| “Do you know where current local heat alerts are issued?” | Chosen local authority or weather-warning link, not a Stock category. |

## Hurricane (`hurricane`)

Show where the household or local authority identifies Atlantic or central Pacific hurricane risk. Source for all five: [NOAA preparation](https://www.noaa.gov/prepare-before-hurricane-season) and [supplies](https://www.noaa.gov/assemble-disaster-supplies-hurricane-preparedness), checked 17 Nov 2026.

| Question shown | Open these records |
|---|---|
| “Have you checked your evacuation plan against your local authority's current information?” | `home_layout.exits.route` plus chosen authority link; route alone does not answer. |
| “Have you checked what you would take and where it is?” | `home_layout.equipment[kind=go_bag].place`, Documents draft only if enabled. |
| “Have you reviewed your drinking water and pantry supplies?” | `stock.items[category=water, drinking=true]`, `stock.items[category=pantry]`; show quantities and actual dates. |
| “Have you checked lights, power and first-aid items?” | `stock.items[category=power]`, `stock.items[category=first_aid]`; require names and positive amounts before showing a candidate. |
| “Do you know how to get local warnings and who issues an evacuation order for your area?” | Chosen local official source; no national pack guesses a county's orders. |
