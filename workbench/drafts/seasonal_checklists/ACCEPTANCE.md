# Seasonal checklist acceptance checks

These checks describe the intended M3 feature. The current core has no checklist engine. All timing and topic sources are linked and dated in [CHECKLISTS.md](CHECKLISTS.md).

1. **Applicability first.** A Smith household with bushfire selected may see Bushfire; Taylor without that hazard does not get it solely because the country is Australia. A Florida household can choose Hurricane; a New York address is not automatically marked at risk merely because the state has a coastline.
2. **Season is a review cue.** Australian cyclone review is offered before 1 November only if cyclone applies; hurricane review before 1 June only for applicable Atlantic/central Pacific exposure. A cyclone or hurricane can still occur outside the named official season, so the UI follows live local alerts and does not call other months safe.
3. **No invented winter or heat date.** Winter and heat lists appear from a household choice or local forecast/event, not a fixed month or temperature invented by the app.
4. **Full-path links.** A kit in `Car › Car boot` opens that path, not an ambiguous `Car boot`. A moved parent place updates the link label. Missing or deleted records are shown as unfilled leads, not as a failed safety check.
5. **Right Stock candidates.** Show drinking-water items with positive litres where the question asks for drinking water. A non-drinking item, zero quantity, or water-purification tablets cannot stand in for drinking litres. A `power` category alone cannot prove there is a torch.
6. **Person answers.** Ticking a seasonal question records who and when, not a safety verdict. New or changed records do not auto-tick it. A person can reopen it after a source or household change.
7. **Source and scope.** Each checklist shows its authority and check date. NSW RFS wording is labelled NSW; Queensland cyclone guidance is labelled Queensland; NWS/Met Office examples are tied to the chosen country. No hazard is inferred from a national topic list or state alone.
8. **No private leak.** Heat and winter questions may point to a People or Medical record but do not copy sensitive text into Home, a shared checklist or printout.
