# People and Stock wording review — 2026-11-09

I read the two shipped modules as a household member would encounter their forms, lists and printable sheets. These are proposed words and layouts for Lane A to review; no module files changed. All examples below are invented.

## Important — make the two emergency sheets distinct at the point of printing

- **Did:** Compared the available People sheet titles and intros in `modules/people/sheets.toml`.
- **Expected:** Someone quickly picking a sheet knows which copy contains private medical and care details.
- **Actual:** “Emergency sheet” and “Emergency sheet with medical details” are close together; the plain sheet's intro says to leave it on the fridge, while the medical sheet's intro warns to keep it somewhere sensible. The privacy difference appears only after reading the longer title and intro.
- **Suggested change:** Title the ordinary sheet **“Who to call — fridge copy”** and the other **“Who to call and private care details”**. Put **“Contains private health and care details. Print only when needed and keep it out of public view.”** first in the private sheet's intro. Keep the actual section columns as they are.

## Important — explain stock quantities in the form before a person enters them

- **Did:** Read the Stock item form labels and help in `modules/stock/labels.toml`.
- **Expected:** A person can record water consistently enough for the days-of-water view to mean something.
- **Actual:** “How many” and a separate free-text “Unit” field make it easy to enter a count of bottles under Water, even though the view treats the quantity as litres. The existing help mentions litres, but it is attached to “How many” and can be missed.
- **Suggested change:** Label `quantity` **“Amount on hand”** and give it help **“For water, enter the total number of litres, not the number of bottles.”** Give `unit` help **“Use litres for water; for other items, use a unit such as tins, kg or packs.”** Keep the existing watch calculation contract.

## Minor — make People contact choices easier to scan

- **Did:** Read the People form and list order in `modules/people/labels.toml`.
- **Expected:** A person adding someone they may need to call sees the main phone field early and understands the call order.
- **Actual:** The form asks whether the person lives here and their relationship before the main phone. “Call order” is clear only after reading the help “1 is called first.”
- **Suggested change:** For the People form use `form = ["name", "phone", "other_phone", "lives_here", "relationship", "email", "address", "birthday", "notes"]`. Keep the list order. In the Roles form, label `priority` **“When to call”** with help **“Enter 1 for the first person to call, 2 for the next, and so on.”**

## Minor — give the supplies printout a clearer boundary

- **Did:** Read `modules/stock/sheets.toml`. The sheet lists Water, First aid and medical, Batteries and power, and Food.
- **Expected:** A printed “Emergency supplies checklist” makes clear that it shows only selected categories.
- **Actual:** Toiletries, fuel and other stock categories are omitted, while the title sounds complete.
- **Suggested change:** Rename it **“Selected emergency supplies”** and change the intro to **“Water, first aid, power items and pantry food recorded here. Other stock categories are not shown. Check dates and quantities when you print a new copy.”** The four sections can stay as they are.

These suggestions change wording and field order only. The People sheets already print linked phone numbers, the sensitive detail column appears only on the private sheet, and the Stock list includes quantity, minimum, place and use-by date, which are the most useful columns for a quick check.
