# UK and New Zealand: deeper local choices

Checked 17 November 2026. This is pack research, not a live warning feed or an address-level risk assessment. The four national pack files are drafts and the pack loader is not shipped. `ROUND2.csv` already identifies **all four UK nations and all 16 NZ CDEM areas**; retain its source and review dates. Round 3 adds named local routes and hazard topics to `UK.toml` and `NZ.toml`. All URLs below returned HTTP 200 on this check (the Wales page redirects to a Welsh/English choice screen).

## United Kingdom

The common pack has both **999 and 112** for emergency services, UK Emergency Alerts, Be Ready water guidance of **3 litres of drinking water per person per day for three days**, and eight UK-wide hazard topics. These are national statements; do not infer that each hazard applies at an address. The household must choose its nation and local authority. Source: [UK Emergency Alerts](https://www.gov.uk/alerts), [Be Ready water interruptions](https://beready.campaign.gov.uk/be-informed-about-hazards/water-supply-interruptions-or-outages/) and [Be Ready hazard topics](https://beready.campaign.gov.uk/be-informed-about-hazards/), all checked 17 November 2026.

| Nation | Local coordination and finding current flood advice | Scope |
|---|---|---|
| England | [Local Resilience Forums](https://www.gov.uk/guidance/local-resilience-forums-contact-details); [Check for flooding](https://www.gov.uk/check-flooding) | Find the household's own forum and area; a UK-wide alert is not a local flood warning. |
| Scotland | [Scottish resilience partnerships](https://ready.campaign.gov.scot/publications/2026/march/foundations-emergency-management-scotland/pages/lesson-3-who-responds-scotland); [SEPA flooding](https://www.sepa.org.uk/environment/water/flooding/) | SEPA link redirects to its flooding service; check the actual local warning. |
| Wales | [Local Resilience Forums](https://www.gov.wales/local-resilience-forums); [Natural Resources Wales flooding](https://naturalresources.wales/flooding/) | Flood page presents a language choice; select a local area before acting. |
| Northern Ireland | [Civil Contingencies Group](https://www.executiveoffice-ni.gov.uk/articles/civil-contingencies); [nidirect flood risk](https://www.nidirect.gov.uk/articles/check-risk-flooding-your-area) | Risk information is not a live household warning. |

For weather warnings in any nation, the [Met Office warnings page](https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-warnings) is a separate current service. The pack must link out rather than cache a warning. Every link in this table was checked 17 November 2026.

## New Zealand

The national pack has **111** for police, fire and ambulance; [Emergency Mobile Alert](https://getready.govt.nz/prepared/ema), at least **3 litres of drinking water per person per day** from [Get Ready water storage](https://getready.govt.nz/prepared/household/supplies/storing-water), and eight [Get Ready hazard topics](https://getready.govt.nz/emergency/). These are national topic and supply sources, not local safety advice. The [Civil Defence directory](https://www.civildefence.govt.nz/about/contact-us/find-your-emergency-management-committee) identifies the household's own CDEM group. `ROUND2.csv` has one row per group: Northland, Auckland, Waikato, Bay of Plenty, Tairāwhiti, Hawke's Bay, Taranaki, Manawatū-Whanganui, Wellington, Nelson Tasman, Marlborough, West Coast, Canterbury, Otago, Southland and Chatham Islands. The pack should offer that group list, then let the household confirm its own local authority and current alerts. Volcanic activity and landslides now have direct [volcanic](https://getready.govt.nz/emergency/volcanic-activity) and [landslide](https://getready.govt.nz/emergency/landslides) topic links. All listed links were checked 17 November 2026.

## Reuse and maintenance

The pack files and this note use brief facts, paraphrases and links. [GOV.UK terms](https://www.gov.uk/help/terms-conditions), checked 17 November 2026, generally apply Open Government Licence 3.0 to Crown content, with exceptions and third-party material; do not assume the Scottish, Welsh, Northern Irish, SEPA or Met Office pages share that licence. [Get Ready site terms](https://getready.govt.nz/about-this-site/), checked 17 November 2026, state CC BY 4.0 for Crown content unless noted, excluding logos and design. NZ Police, NEMA and local CDEM terms are not confirmed. Link only to these services until their own reuse terms are checked. No maps, alerts, logos, full instructions or page text are copied. Recheck both countries by **17 February 2027**, sooner if a service changes. The household's chosen water setting must stay authoritative for the app's count; pack figures are attributed guidance.

Core work: load packs by country and subregion, store local-authority selection, display source, scope and checked date beside a claim, follow live warning links without implying an automatic alert, and let a household change its selected region. See [NOTES.md](NOTES.md) for the shared pack-loader gap.
