# Bills and insurance promotion checks

Written **21 November 2026** against the shipped Utilities and Vehicles models, decisions 0099 and 0100. Use invented data only.

1. Add a bill and each policy category (vehicle, home, contents, health, pet); a row can name an existing People provider and optionally an existing vehicle or Place. An unknown typed link is refused.
2. Leave vehicle and Place blank for a household-wide policy; the row still saves. Deleting a linked People provider, vehicle or Place clears the link and keeps the commitment, without silently changing its name, due date or private details.
3. A next date 31 days away creates no reminder. At 30 days, Needs attention says the saved name and that its **bill or policy check is due** on the household-formatted date. After the date, it says overdue. It never says a payment failed or insurance lapsed.
4. Save `weekly` and a due date; passing that date does not silently create the next one. A person checks a new bill or renewal and types the next date. Blank frequency or date is allowed.
5. Plant invented amount, cover summary, reference and notes sentinels. They are behind Show, absent from list, Needs attention, ordinary sheet, general spreadsheet export and helper read. The local backup keeps them; the portable change log and snapshot contain their field names at most, never value, length or hash.
6. The ordinary name, category, provider and links may travel under decision 0100. Test that a member copy sees a due reminder but no amount, cover summary, reference or notes. Editing a withheld field never sends a blank that erases another computer's own value.
7. Print the sheet at A4 and Letter, 320 px at large text, and with a long provider name. It includes no financial value or policy reference. Check the sheet is not silently truncated before calling it a complete list.
8. Add a vehicle policy while Vehicles already has an insurance renewal. The UI warns about two reminders for the same cover; migration or household choice must leave one authoritative date before promotion. Utilities' electricity service stays the service/contact record, while this bill records its due date and amount.
9. Switch Vehicles off: the draft's current `requires` rule blocks this module. Decide and implement an optional vehicle link or an independent vehicle-policy extension before promoting a general household bill feature.
