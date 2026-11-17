# Wine collection draft — promotion decisions

This compact module records wines, a bottle count and tasting notes. A new user sees “Add a wine you want to remember.” Forms and lists use familiar wording, and an optional printed collection sheet shows what is recorded.

- **Purchases and openings as movements?** For this compact version, the household edits “Bottles on hand” directly. A movement history would help if people repeatedly forget to change the count; add it only after testing that need. The current draft must not imply automatic count changes when a tasting is logged.
- **Currency?** The existing `money` type uses the household's configured currency. The form says this and makes price optional. Do not add a separate currency field without a real multi-currency use case.
- **Place link?** Keep free text for now. Requiring Household stock would burden a small optional collection. If Home layout later supports a shared place picker, offer it as an optional migration with confirmation for ambiguous names.

No due-date watch is useful for every wine collector. The one gap asks for a missing bottle location, for findability only; a collector can leave it unanswered. The module does not claim an ideal drinking date or value. A fuller collection could add stock movements and charts after household feedback; it needs no custom code or external source now.
