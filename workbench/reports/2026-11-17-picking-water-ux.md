# Picking and drinking water: batch 4 UX check

Checked **2026-11-17** against `main` at `1ba6559`. Used temporary copies of all three example households and a fresh empty household. For the fresh household, sent the same suggestion queries and 20 consecutive add-form submissions used by the local web UI; all 20 saved. This checked the web routes and saved records, not keyboard or screen-reader interaction in a browser. No real household data was used. Journey links: [J2 and J3](../../docs/JOURNEYS.md).

## Findings, worst first

### 1. Important — a custom non-drinking water item counts by default (J3)

**Did:** In the fresh household, added 2 litres each of *Bottled drinking water*, *Distilled water*, and *Stored non-drinking water* by choosing catalogue suggestions. Then typed a new name, *Flushing water*, selected the Water category, entered 2 litres, and left the form's initially ticked **Safe to drink** box as it was.

**Expected:** A newly named water item should ask the person to confirm whether it is safe to drink before adding it to the days-of-water figure. Water described as flushing water should not be counted by default.

**Happened:** The first three suggestions filled the drinking flag correctly: 2 litres counted and 4 litres excluded. Adding *Flushing water* raised the counted amount to **4 litres** and the estimate from about **0.7** to **1.3 days** for one person. The 4 excluded litres stayed excluded. The Water category exposes **Safe to drink**, but the box begins ticked even when the person has typed an unknown name. The form's help says to untick it for washing or flushing, yet the current default makes a missed click change a preparedness number.

**Suggested change and exact words:** When a person chooses Water for a name that did not come from a catalogue suggestion, require an explicit answer before Save: **“Is this water safe to drink now?”** Choices **“Yes, count these litres as drinking water”** and **“No, keep it out of days of water”**, with neither preselected. Keep the catalogue's yes/no suggestions as proposed answers that the person can change. On the home page, keep the existing **“Not counted: …”** line. This is a core form behaviour change; a catalogue edit cannot make a newly typed name safe.

### 2. Important — the water calculation trusts a quantity even when its unit is not litres (J3)

**Did:** Followed the form and supply rule from the same fresh stocktake. The form lets a person change the Unit on a Water item to `bottles`, `packs`, or any text while **Safe to drink** is ticked. The supply rule sums the numeric amount and labels the result litres. The UI help asks for litres but does not check them.

**Expected:** Days of drinking water should only use amounts entered in litres, or ask for a confirmed conversion from a package size.

**Happened:** The route accepts arbitrary units, while `counts_only` checks only the drinking flag. A person entering 6 bottles as amount 6 would be shown 6 litres. This is a code and form contract finding; the 20-item run used litres for its actual water submissions.

**Suggested change and exact words:** For Water, label the amount **“Total litres on hand”** and keep the unit as litres, or provide a separate **“Number of bottles”** and **“Litres per bottle”** calculation that the person confirms. If an existing water item has another unit, show **“Enter this water's total litres before we count it in days of drinking water.”** Do not silently treat a bottle or pack as one litre.

### 3. Minor — several everyday searches have no suitable catalogue result (J2)

**Did:** Typed each of the 20 stocktake searches before choosing or keeping a name. Thirteen found the intended catalogue entry first, including `canned tom` → **Tinned tomatoes**, `bell pepper` → **Capsicum**, `flashlight` → **Torch**, and `diapers` → **Nappies**. The bottled, distilled, and non-drinking water suggestions filled category, litres and drinking status correctly. `glucose test strips`, `shelf-stable oat milk`, `black garlic`, `gochujang`, and `injera` returned no match. `flushing water` offered **Stored non-drinking water** through its alias, but a person keeping their own name received no water fill. All six names could be saved as custom items.

**Expected:** The close catalogue terms should be offered. Less common foods should still have a clear path to a new item.

**Happened:** **Blood glucose test strips** and **Oat milk** are already in the catalogue, but their search words omit the two phrases above. The other three foods have no matching row. When there is no match, the suggestion list disappears entirely, so it does not say how to keep the typed name; Save still works. Custom goods inherit Pantry and have a blank or manually entered unit.

**Suggested change and exact words:** In catalogue round 4, add `glucose test strips` to **Blood glucose test strips** and `shelf-stable oat milk` to **Oat milk**; review whether Black garlic, Gochujang and Injera merit entries. When the list is empty, show **“No match. Keep ‘Injera’ as a new item.”** For a new item, follow with **“Choose its kind and unit.”**

### 4. Minor — partial stock names can rank less helpful variants first (J2)

**Did:** Typed `batteries` in the fresh household. The first three results were **C batteries**, **D batteries**, and **9V batteries**; **AA batteries** appeared fourth. In the Smith household, `torch` offered its existing **Torches** before the catalogue **Torch**, as intended. In Sam Taylor's household, the existing **Distilled water (for the iron)** appeared before the generic **Distilled water**.

**Expected:** The household's own records should come first. For a generic search, a broad good or a common specific good should be easy to see.

**Happened:** The eight-result cap and the current short-name ordering can put an arbitrary battery size ahead of a likely AA choice. There is no generic Batteries row. This is a ranking suggestion, not a failed save.

**Suggested change and exact words:** Consider **“Batteries — choose a size”** as a heading or a generic entry before sizes, and show size choices together. Keep **“You already have this: open it”** on household-owned results.

## Coverage and limits

The 20 saved fresh-household goods were Kidney beans, Tinned tomatoes, Capsicum, Torch, Nappies, Rice, Pasta, Oats, Bottled drinking water, Distilled water, Stored non-drinking water, AA batteries, Adhesive bandages, Dry dog food, Glucose test strips, Shelf-stable oat milk, Black garlic, Gochujang, Injera and Flushing water. These are fictional stock records, each entered with amount 2. The first 14 used catalogue fills; the final six were kept as typed. All add-form submissions returned the next-item page.

The existing Smith, Garcia and Taylor households were read in temporary data folders. Their initial drinking-water figures were **34.4 litres** for the Smiths, **24.7 litres** for the Garcias, and **12 litres counted plus 1 litre excluded** for Sam Taylor. The own-item priority appeared in each household where a name matched; no example data was changed. The check did not time manual entry or exercise the browser's live suggestion menu, so its interaction speed and keyboard accessibility remain to be checked in a browser.

The product facts above come from the checked local form, catalogue, suggestions route and supply calculation on 2026-11-17. No external preparedness advice was used.
