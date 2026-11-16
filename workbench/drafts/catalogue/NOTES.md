# Common goods catalogue — rounds 1 and 2

This is a **draft of 400 names** after round 2, for Corey to review. It is not installed. The first 150 rows remain the round-one set; 250 more rows extend pantry choices, first aid, toiletries, cleaning, power, pets, hardware, tools, garden, fuel and other household items. Names, aliases and units are editorial search aids, not claims about what a household owns. `typical_sizes` is blank pending product and region-specific evidence; the picker must never assume a package size or quantity. The catalogue has no personal data. Stock's category keys are used exactly as declared in `modules/stock/tables.toml`.

Round 2 was checked against the three made-up example households. It adds generic matches for their missing terms, including paracetamol, glucose test strips, N95 respirators, a hand-crank radio, power station, furniture straps, wall plugs, bike inner tubes and picture hooks. Personalised medicines such as “Metformin 500 mg (Rosa)” stay household-owned records and are **not** prefilled from the catalogue. Existing water rows gained search aliases for bottles, casks, jugs and pouches; the stored-tap and bottled distinctions still require the person to confirm potable status. Generic Rice, Pasta, Lentils and Pain relief tablets no longer claim aliases that should point to a more specific choice. There was no substantive Corey comment on the merged round-one PR when this round was prepared on 2026-11-16; these additions are proposed for feedback, not a claim of approval.

## What a household should see

In a stocktake, typing `kid` immediately offers **Kidney beans** near the top; selecting it fills the name, category and suggested unit, and leaves quantity, place, package size and use-by date for the household. Match the start of the name first, then other words in the name, then aliases; ignore case, accents, spaces and punctuation, and handle singular/plural forms. Search `canned kidney beans` and `tinned kidney beans` as aliases of the same good. Regional terms such as capsicum/bell pepper, nappies/diapers and torch/flashlight must work in either locale. Show **Add “xyz” as a new item** after matches, always available. Never silently replace what someone typed with a catalogue entry.

An added name belongs to that household, stays in its local data and is offered next time before a generic catalogue result when the text matches. The household can edit its own name and aliases without changing the shared catalogue. The catalogue's key is stable across releases; don't overwrite a household's edited name, unit, category or dates when the catalogue updates. If a household picks the same catalogue good again, offer its existing stock item or a new lot, rather than silently making a duplicate. A catalogue choice is a template, not an inventory record.

The current core has only a free-text stock name and one `category = "water"` supply rule. Lane A needs to add a type-ahead picker, local additions and stable catalogue-key provenance; a clear existing-item action; and a drinking-water flag on stock items or lots. The water supply watch must filter on that flag and use **litres**, rather than sum every row in the water category. The form needs to confirm potable status when someone adds custom water. A `yes` template is a proposed default only; warnings and local water advisories can change whether it is drinkable.

**Long-term scanning idea from Corey:** Let a household use a phone camera or ordinary webcam as a scanner. A barcode could search a product database; the camera could propose the package size, quantity and printed date for review. The barcode alone does not reveal a lot's use-by date or how many packages the household owns. Any OCR or AI reading should show what it found and ask the person to correct or approve it before changing stock. Keep manual entry available, use a local or opt-in product database, and make image upload explicitly opt-in. This may be a large technical lift, but could make repeated stocktakes and weekly shopping much more convenient. The [lots design](../stock_lots/NOTES.md) records the corresponding lot and movement requirements.

## Water decisions and sources

Checked **2026-11-16**. `counts_as_drinking_water` means an item may count *when its actual contents are potable and its amount is entered in litres*. It is not a guarantee that a particular bottle, filter or stored container is safe. A household should follow local advisories and its product's instructions. CDC warns that boiling or filtering cannot make chemically contaminated water safe [3].

| Catalogue row | Count | Sourced reason |
|---|---|---|
| Bottled drinking water | yes | CDC calls unopened commercially bottled water the most reliable emergency source [1]. |
| Stored tap drinking water | yes | CDC permits clean water in sanitized food-grade containers labelled as drinking water and says to replace home-filled water every six months [1]. |
| Filtered drinking water | yes, conditional | CDC says filters vary by contaminant and cannot remove everything [2]. Count only water already potable or made potable by a suitable, verified treatment. |
| Boiled drinking water | yes, conditional | CDC says boiling can make microbiologically contaminated water safe to drink, following local advice; chemical contamination is an exception [3]. |
| Sparkling drinking water | yes | CDC describes sealed bottled or canned sparkling water as typically safe to drink [4]. Confirm it is labelled drinking water. |
| Distilled water | no for this planning default | WHO discusses potential consequences of *long-term* consumption of demineralized water [5]. This is a conservative planning exclusion for appliance water, **not** a claim that distilled water is poisonous or that an occasional drink is unsafe. If a product is sold as drinking water, a household needs a deliberate override. |
| Stored non-drinking water | no | CDC says storage containers intended for drinking water must be cleaned, filled with clean water and labelled accordingly [1]; this row is explicitly for flushing or washing. |
| Water purification tablets | no | CDC lists disinfection as a way to treat water [3]; tablets themselves add no litres of potable water. |

## Shelf life and package sizes

Only 24 canned-food rows currently have an indicative unopened **best-quality** period. USDA FSIS says commercially canned high-acid tomatoes and fruit retain best quality up to 18 months; low-acid foods, including vegetables and fish, have a 2–5 year best-quality range [6]. The CSV uses **24 months**, the conservative lower end, for the low-acid examples. This is **not** a use-by date or a safety guarantee. Follow the pack label and storage instructions; damaged cans need separate attention. Other shelf-life cells remain empty, including goods where storage and packaging vary. A month value must not auto-fill a lot's use-by date without household confirmation. `typical_sizes` remains empty for the same reason; it could later offer package-size suggestions without determining quantity.

FSANZ says the supplier sets a use-by or best-before date and the manufacturer's storage instructions matter [8, 9]. The UK Food Standards Agency says a food's **use-by** date is a food-safety limit even if it looks and smells fine [10]. The future picker should distinguish an indicative catalogue **best-quality** period from a product's actual **use-by** or **best-before** mark. It must not calculate a substitute use-by date from this CSV.

USDA's official [FoodKeeper dataset](https://catalog.data.gov/dataset/fsis-foodkeeper-data) [7] would support more item-specific values, but its FSIS download returned HTTP 403 from this workspace on 2026-11-16. Populate further values only after checking the actual records, storage conditions and units. Do not infer a shelf life from the word “canned” alone. The catalogue does not contain medical dosing, infant feeding or water treatment instructions.

## Source and reuse record

1. [CDC, Creating and Storing an Emergency Water Supply](https://www.cdc.gov/water-emergency/about/how-to-create-and-store-an-emergency-water-supply.html), checked 2026-11-16. US federal government content; generally public domain, subject to [CDC reuse exceptions](https://www.cdc.gov/other/website-policies.html). Linked and paraphrased.
2. [CDC, Choosing Home Water Filters](https://www.cdc.gov/drinking-water/prevention/about-choosing-home-water-filters.html), checked 2026-11-16. Same CDC terms.
3. [CDC, How to Make Water Safe in an Emergency](https://www.cdc.gov/water-emergency/about/), checked 2026-11-16. Same CDC terms.
4. [CDC Yellow Book, Food and Water Precautions for Travelers](https://www.cdc.gov/yellow-book/hcp/preparing-international-travelers/food-and-water-precautions-for-travelers.html), checked 2026-11-16. Same CDC terms.
5. [WHO, *Nutrients in Drinking Water*](https://www.who.int/publications-detail-redirect/9241593989), checked 2026-11-16. Reuse licence not confirmed from the accessible publication page; paraphrase and link only, do not copy the report.
6. [USDA FSIS, How long can you keep canned goods?](https://ask.fsis.usda.gov/article/How-long-can-you-keep-canned-goods), checked 2026-11-16. US federal government content, generally public domain; paraphrased.
7. [USDA FSIS FoodKeeper dataset listing](https://catalog.data.gov/dataset/fsis-foodkeeper-data), checked 2026-11-16. The catalogue lists the English dataset as [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Dataset not ingested yet.
8. [FSANZ, Use-by and best-before dates](https://www.foodstandards.gov.au/consumer/labelling/dates), checked 2026-11-16. FSANZ website material is generally [CC BY 4.0](https://www.foodstandards.gov.au/legal-policies/copyright), with logo and third-party exceptions. Paraphrased and linked.
9. [FSANZ, Storing food safely](https://www.foodstandards.gov.au/business/food-safety/storing-food-safely), checked 2026-11-16. Same FSANZ terms.
10. [UK Food Standards Agency, Food poisoning](https://www.food.gov.uk/food-safety-and-hygiene/food-poisoning), checked 2026-11-16. UK Crown copyright, generally [Open Government Licence](https://www.food.gov.uk/crown-copyright) for site text, with third-party and image exceptions. Paraphrased and linked.

## Next rounds

After Corey's review of the 400-name set, add toward 800 in round 3 using missing-search feedback and the example households. Keep each round in its own reviewable pull request. Assess regional names, category balance, package sizes and cited shelf-life values as the list grows.
