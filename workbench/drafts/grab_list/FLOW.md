# A list for leaving in a hurry

Drafted 17 November 2026 for M3. This is a household-authored list of what **they** decide to take, where to find it and who carries it. The app does not choose an evacuation route, override instructions from officials or claim the list is complete. [NZ Get Ready's household-plan page](https://getready.govt.nz/prepared/household/make-a-plan) and [US CDC's personal-needs page](https://www.cdc.gov/prepare-your-health/take-action/personal-needs.html), checked 17 November 2026, explain why a plan and personal needs are worth considering; the rows here are invented.

## Build the plan

Home → **Leaving quickly** → **Make a grab list**. First screen: “Write down what your household would take and who would carry it. You can change this any time. Check current local instructions if you need to leave.” Create a plan with a household name, date last reviewed and optional link to its Home layout exit/meeting plan. Rows can be a person, pet, kit, document, Stock item or a custom item. The picker offers the household's own records, with full place paths where available. Every row has: **What to take**, **Where it is**, **Who carries it**, **Ready?** (a planning checkbox), and optional private notes kept off the ordinary printout. A carrier is a People link or “Not assigned yet”; a person may carry their own things. Do not assume a pet can carry an item or that every household has a car.

Links are to `people.people`, `pets.pets`, `medical.kits`, `documents.documents`, optional `stock.items`, and `home_layout.places`. A Medical kit link supplies its name and current place. A Documents link supplies its name, but its current draft has a **text** place, not a shared place link; the person must review that description. Medical notes and sensitive People details are never copied into a grab row. If Medical or Documents is off, offer a custom row and say “No linked record available”; do not invent a record. If a linked record is renamed, its displayed name refreshes. If deleted, flag the row “Linked record missing — choose another or keep as text” without erasing the household's own words.

The list can be grouped as **People and pets**, **Health and kits**, **Documents**, and **Other things**. These are editing aids, not mandatory categories. To avoid a long checklist while leaving, show a short **Take first** section chosen by the household; all other rows remain available below. The screen shows unassigned carriers and missing locations before printing, without marking them as safety failures. Exact prompt: “Three rows still need a carrier or place. Review them before printing.” A household can print anyway after choosing to continue.

## Keep it current

After a person changes a Pet's keeper, moves a kit, or edits a document location, mark the affected row “Review this place or carrier.” Do not silently rewrite a household-edited location or carrier. A **Review list** action shows linked record changes side by side and updates the `last_reviewed` date only when a person confirms. A paper copy carries its printed date and a reminder to replace it if plans change. A printed copy might expose where valuables or medical items are kept; the person chooses **Include private locations on this copy** before printing, default off.

## References

- [Shipped People](../../../modules/people/tables.toml), [Pets](../../../modules/pets/tables.toml), [Stock](../../../modules/stock/tables.toml) and [Medical](../../../modules/medical/tables.toml), and draft [Documents](../documents/tables.toml) and [Home layout](../home_layout/tables.toml), checked 17 November 2026 for exact fields and link targets.
- [Get Ready household plan](https://getready.govt.nz/prepared/household/make-a-plan) and [CDC personal needs](https://www.cdc.gov/prepare-your-health/take-action/personal-needs.html), checked 17 November 2026. The list is a way to record the household's choice, not a substitute for the authorities' current advice.
