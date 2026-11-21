# Move-in checklist checks

Written **21 November 2026** with invented Smith, Garcia and Taylor rows only.

1. Generate a guide for a Stock/Vehicles helper and one for a look-only People helper. Each lists only its grant, names private fields but no private values, has no key, and shows current limits. Change the grant and daily allowance; a fresh guide changes accordingly.
2. Feed the assistant a tracker with an existing item, a new item with starting amount, two same-name Places under different parents, one private registration, and an unsupported section. It reuses the correct full-path ID, sends the new item once, omits registration, and reports the unsupported section.
3. Attempt a new item with amount plus dependent Stock in for that same starting amount. Review warns about possible double count and the household can stop before both are accepted.
4. Give a date `1/2/27`, a water item of uncertain drinkability and a unit mismatch. The assistant asks or leaves allowed values blank; it does not guess the date order, drinking status or unit conversion.
5. Plant invented code/payment/medical sentinels in source tracker text. None enters `name`, `notes`, `why`, receipt `source`, general export or helper final chat; the person enters permitted private fields on the app only.
6. Send 20 entries, then a 422 and an exact timeout retry. The refused send stages nothing; retry keeps one batch. Read result before sending more and stop when daily or waiting cap is reached.
7. A receipt repeats stock already moved, with an unmatched product line. Review warns, offers Choose item/Skip line, and Accept all does not declare a partial group complete. The final helper summary distinguishes sent, accepted and waiting.
8. The person uses Set up my home to distinguish a shelf nested in a cupboard from a door between rooms; the helper does not invent a way outside or a room link from a label.
9. Turn the helper off after the move. Its key stops, Review history remains, and a checked backup plus unresolved-item list exists. The old tracker remains readable until the household reconciles the move.
