# Country pack content draft

These four files are **linked, dated content**, not a live country-pack module. Every emergency number, body, water amount and hazard has its own official source and check date. A hazard list means that the cited body discusses the topic; it does not say the hazard applies to a household's address. Each pack ends with a local-authority question, as decision 0025 requires. Review dates are editorial maintenance targets, not public advice.

## Scope of the water values

- **AU:** NSW Rural Fire Service's emergency kit recommends at least **3 litres per person per day**. This is a NSW source; the pack labels it as such. The existing Queensland research gave no per-day figure. Local and household needs may differ.
- **US:** CDC says at least **1 US gallon per person per day** for a three-day emergency supply. The unit is kept as published, so the program must convert before comparing litre totals.
- **UK:** The UK Be Ready campaign recommends **3 litres of drinking water per person per day for three days** on its water-supply interruption page.
- **NZ:** Get Ready says **3 litres per person per day** without water.

These are source-specific starting figures, not a universal safety threshold. The core should show the source, unit and date beside any calculated days of water. It must count only water the household confirms is drinking water and follow local advice where it differs.

## Reuse and checks

AU links and paraphrases Home Affairs, Queensland Government and NSW Rural Fire Service. Home Affairs material is generally CC BY 3.0 AU; Queensland Government is generally CC BY 4.0, with exceptions; NSW RFS terms for this page were not confirmed. The AU `reuse_source` points to Queensland's copyright page and is **not** a blanket licence for the other authorities. US federal government text is generally public domain under 17 U.S.C. 105, with third-party exceptions. UK GOV.UK content is generally Open Government Licence 3.0, with exceptions. NZ Get Ready Crown content is generally CC BY 4.0, with logos and design excluded; NZ Police and NEMA site terms were not confirmed. All content here is paraphrased and linked, without reproduced guidance or imagery. Checked **2026-11-16**. Existing source notes in `workbench/research/country-packs/` give further regional limitations.

## Core work

The country-pack loader needs a versioned schema, per-value citations, link checks and expiry/review warnings. A household must be able to see the authority behind a value and open the current guidance. Country is not enough to decide local hazards; use household input or an explicitly chosen local authority. Emergency numbers must remain visible offline, with the pack's last-checked date. Do not silently override the household's water basis when a pack is installed. The present four files do not include state or local phone lists; those remain research work, not values to guess.
