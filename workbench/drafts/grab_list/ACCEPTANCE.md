# Grab-list acceptance checks

Use the three fictional example blocks and the screen/sheet text in [FLOW.md](FLOW.md) and [SHEET.md](SHEET.md). No example data is a prescribed emergency kit.

1. **Links resolve.** Smith's Rex link opens Pets, Garcia's Apartment first aid kit opens Medical, and Taylor's Tenancy agreement opens Documents when that draft is enabled. Each carrier opens the named People record. With Medical or Documents off, show a custom-row path instead of a broken picker.
2. **Full places.** Garcia's `Hall closet` prints `Hallway › Hall closet` from the linked place. `Under the bed` prints `Main bedroom › Under the bed`. A same-named spot under another room is never chosen by leaf text alone.
3. **Person owns the plan.** Adding or ticking a row does not change People, Pets, Medical, Documents or Stock records. A source record is a suggestion, not an automatically required item. A household can choose no pets, no car or no document row.
4. **Who carries it.** A row with no carrier shows “Not assigned yet”; the print preview counts it. Assigning a carrier records a People link, not a copied phone or private detail. A pet cannot be selected as a carrier.
5. **Review after change.** Move the kit to a new place or change Luna's keeper. The linked row asks for review and shows old/new values. It does not silently replace a household-edited place or carrier. Only person confirmation updates the plan's review date.
6. **Deleted target.** Delete a linked document or pet. Keep the grab row with “Linked record missing — choose another or keep as text”; never drop it from the printout without a person's choice.
7. **Print privacy.** The default one-page preview hides document locations and all sensitive People/Medical details. The optional private-location choice shows exactly which places will print; it never reveals document numbers or secrets. The printed page matches preview.
8. **Legible overflow.** Fit a short plan on A4 and US Letter. For a longer plan, continue to page 2 with a clear marker; do not omit rows or shrink to unreadable text. Each page carries household name and printed date.
9. **Offline use.** A printed list is usable without the app or internet, with item, place or “Check location”, carrier and checkboxes. It does not present a saved source link as an active warning service.
