# Wine: first promotion candidate

Rechecked **19 November 2026** against the shipped core, `docs/DESIGN.md` §§5–6, decisions 0072/0075/0078 and the draft's loadable tables, labels, sheet and invented examples. This is batch 14 item 58. No outside wine, health or valuation source is used.

**Ready first, for the small manual scope already drafted.** Wines, bottle counts and tasting notes use supported fields and local links; the sheet is a snapshot of the household's own bottle count, place and purchase date. No due-date rule, aggregate card, linked phone or one-step action is needed. Nothing in 0072 or 0075 blocks promotion. Lane A should run the normal load, add/edit/delete/restore, example and print checks before switching it on.

**Counts stay manual.** Opening or tasting a wine does not change Bottles on hand. The form says to update the count yourself. Do not imply that a tasting note consumed a bottle or that the printed list is a live stocktake. A later movement history would need its own household test; it is not required for this small release.

**Place is deliberately free text.** “Where kept” can say a rack or shelf without requiring Household stock. It is not a shared `stock.places` link and will not follow a place move or show a nested path. If households later want a picker, make it optional, add `stock` as a dependency only after that product choice, and review repeated/ambiguous names in a migration. Do not silently convert free text to an ID.

**Privacy choice before promotion:** Tasting notes and Price paid are ordinary fields, so a helper granted Wine can read them and the general spreadsheet export includes them. The sheet omits both but lists places. If the intended promise is private tasting notes or prices, mark those fields sensitive before release and retest initial HTML, helper reads and export; the current draft does not promise privacy. Avoid account, access or health details in notes. The `wine` links on Bottles and Tasting notes default to restrict deletion, preserving linked history until the household deals with it; check the refusal words rather than silently losing notes.

**Promotion order:** Wine first; Utilities next after its meter/phone draft is aligned; Collections and Home inventory need larger core or privacy decisions. Money uses the household's configured currency. No market value, drinking date, health claim or recommended interval is inferred.
