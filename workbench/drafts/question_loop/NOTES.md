# Core work needed for the question loop

Checked **2026-11-17** against `docs/DESIGN.md` sections 10.1–10.3 and shipped modules.

- **Daily facts and dates:** Store dated measures with stable subject IDs, units, source record IDs, edits and deletions. Detect a change only after at least 20 usable points and show the actual number and period in each question. A monthly count alone cannot justify a daily change-point claim.
- **Events:** Add household-confirmed event/annotation records for food changes, routine, travel, equipment moves and other leads. Do not mine free-text private People or Medical notes for suggestions without an explicit household action.
- **Plausibility:** Declare allowed topics and same-subject rules in each watch. A different pet, unrelated module or unrelated topic is rejected before date proximity. Cross-module links need an explicit allow-list; text similarity cannot override it.
- **Statistics:** Apply the paired-point minimum, excluded-day handling and multiple-comparison correction from DESIGN 10.3. Do not show a question when the finding does not survive those checks. Keep a reason why each candidate was accepted or rejected for review.
- **Answers:** Store Yes, No, Not sure and “That doesn't make sense” with date and links. Yes creates a person-attributed explanatory annotation, not a causal fact. No suppresses that pairing; Not sure can return once with more data; the fourth answer mutes the topic pairing for this household. Cap open questions and expire unanswered ones quietly.
- **Scope gaps:** Shipped Pets has weigh-ins, but no daily food-intake table. Stock has movements but no dated historical water-cover snapshots or confirmed stock-out episodes. Garden, Vehicles, utilities, receipt spending, Home care and readiness answers are not all shipped. The respective example questions must stay inactive until their records and watches exist.

No external source or licence is needed for these invented examples. The product rule source is internal DESIGN, checked on the date above.
