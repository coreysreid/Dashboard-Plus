# Shopping-list acceptance checks

Use invented items and amounts; no list value is a recommended emergency supply quantity. Read the exact screen wording in [FLOW.md](FLOW.md).

1. **Threshold and arithmetic.** With 2 tins of Tinned tomatoes and Keep at least 6 tins, Make a shopping list proposes 4 tins. With 6 on hand and minimum 6, it does not propose a row. With minimum 0 or blank, it does not auto-add. Negative and incompatible units cannot enter the calculation.
2. **Fractional amounts.** Rice at 0.5 kg against 2 kg proposes 1.5 kg, without rounding to two packages. The person can change to 2 kg; if selecting two 1 kg bags, the final Stock in is exactly 2 kg.
3. **Grouping.** List items appear under a chosen aisle when configured, otherwise their category or an unassigned group. Moving an item to Fresh food changes its shopping-list aisle only, not its Stock category or place. Separate Stock items with the same visible name remain distinct unless item ID and unit match.
4. **Zero list.** When nothing is below its minimum, show “Nothing is below your chosen minimum. Add items if you want a list for this trip.” The person can add a one-off row without changing a Stock minimum.
5. **Edited proposal.** Change the suggested 4 tins to 3 tins. A later Stock movement changes on-hand from 2 to 1. Reopening the trip alerts that amounts changed; it shows the new suggestion of 5 tins alongside the person's 3-tin choice and does not silently overwrite it.
6. **Ticking is planning.** Tick one row, then untick it; counts and accessible state update. Neither action changes the Stock item or creates a movement. “Could not find it” remains on the trip and is not treated as picked up.
7. **Only what came home.** Tick tomatoes and rice, leave water unticked, then open the home review. Only tomatoes and rice appear. Correct tomatoes from planned 4 to actual 3; Save creates a bought movement of 3 tins, not 4. Water Stock stays unchanged.
8. **Water conversion.** Plan 8 litres, buy four 2-litre bottles, confirm 8 litres. Stock adds 8 litres once. The drinking flag is confirmed under normal Stock rules; the shopping list never turns non-drinking water into drinking water.
9. **Lots and dates.** When lots exist, two tomato packs with different printed dates create two lots but one purchased total of two tins. If no printed date is supplied, leave it unknown; do not infer it from the catalogue's shelf-life hint.
10. **One batch, one save.** Save a trip, reload and press the same action again. The same rows cannot add twice. The resulting bought movements share a batch ID and the list shows `Added to Stock`. A later list edit does not alter those movements.
11. **Undo safely.** Undo this trip's Stock in reverses only its movements. If a person made a later change to one affected Stock item, show the conflict and ask which action to take; do not overwrite the person's change.
12. **Still low.** After three tins come home, tomatoes move from 2 to 5 and still appear under Needs attention for a minimum of 6. Unpicked items remain on the list; closing the trip does not dismiss their alerts.
