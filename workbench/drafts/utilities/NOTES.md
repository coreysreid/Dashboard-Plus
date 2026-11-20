# Utilities: promotion pass

Checked **20 November 2026** against shipped People, Home layout, Stock Places and the linked-phone sheet contract (decision 0072). All providers, numbers and account references in this draft are invented. Do not treat them as real fault lines.

## Ready for a deliberate promotion

`services.meter` is now an optional link to `home_layout.meters`; the unreleased first migration stores its foreign key and clears it when a meter is deleted. Utilities therefore requires `home_layout` as well as `people`. There is no second Places table or migration: each meter's place is a shipped `stock.places` link. The sheet now prints `fault_contact.phone` from the chosen People row. Account number and notes remain sensitive and absent from the sheet and general spreadsheet export; the household backup includes them. The form asks for no passwords, login codes or card details.

The draft accepts provider and fault contacts as ordinary People rows without adding People roles. They remain reachable from their Utility service and from the People list, but are not grouped in Who to call by a utility role. That is a product scope choice, not a missing migration. A household should confirm the number against its own provider before using the printed page.

| Household | Utility service | Exact meter row | Meter's existing place | Result |
|---|---|---|---|---|
| Smith | Home electricity | Electricity meter | Garage | Already in shipped example; exact link in draft |
| Garcia | Apartment electricity | Apartment electricity meter | Hall closet | Invented meter added to this draft's example |
| Taylor | Flat water | Flat water meter | Kitchen cupboard | Invented meter added to this draft's example |

The name-to-ID resolution at promotion must use the exact meter row in each household, never copy the typed name to a free-text field. The last two meter rows belong in `home_layout.meters` when the optional examples are loaded. Internet and phone services may leave Meter blank. If a linked meter is removed, the service remains and its meter link clears; a newly selected meter is a household choice. A place with a meter stays protected by Home layout's existing restrict rule.

## Core and promotion limits

- The Utility list and linked picker display the meter record's **name**, whereas the full nested path is shown on **Our home** through `home_layout.meters.place`. Renaming or moving a place updates that sheet, but the Utility list does not show the full path beside the meter name. If Corey wants the path on the Utility form/list too, core needs a linked record label that includes its linked Place path; the draft cannot define that across modules.
- `home_layout` is a hard dependency even for a Utilities household with only internet. Optional cross-module dependencies are not supported by the current module contract. Keep the dependency for truthful meter links; any looser choice needs core design first.
- Sheet phone is a snapshot of the household's People row, not a verified outage number. No automated call, payment or meter reading action is claimed.
- Before promotion, Lane A should load all three invented optional examples beside the shipped modules, exercise the acceptance checks, and confirm the Utility contacts PDF wraps the phone and meter columns at A4 and Letter. The draft loader and matching migration were checked on 20 November; this is not a claim that a physical PDF was visually inspected.

Sources: `modules/home_layout/tables.toml`, `modules/home_layout/sheets.toml`, `modules/people/tables.toml`, `docs/decisions/0072-reminders-skip-finished-rows-and-sheets-print-linked-contacts.md`, `docs/decisions/0078-export-my-records.md`. Checked 20 November 2026.
