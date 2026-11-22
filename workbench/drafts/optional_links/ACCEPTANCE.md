# Acceptance checks

Use invented records in disposable households. These are behavior checks for a future core feature, not checks the current build can pass.

1. With Our home off and People on, enable Utilities. Add an internet service; no Meter field or meter gap appears, and the exact explanatory sentence in FLOW.md is visible before Save at 320px and desktop.
2. Add an electricity service without a meter. Show says “No meter place linked.” The service and fault contact are usable. No other module is enabled.
3. Enable Our home, add a meter in Kitchen › Cupboard and link it. Show and sheet show the full path. Switch Our home off: the link ID remains in storage, but no name, path or access detail appears on Utilities HTML, sheets or a Utilities-only helper response.
4. While Our home is off, edit the electricity service's provider and notes. The link ID does not change; a crafted POST with a different meter ID is refused. Re-enable Our home and see the same chosen meter.
5. Delete that meter through an allowed, explicit flow, then open Utilities. The ID is flagged missing and is never replaced by a same-named meter; the person chooses another or clears it.
6. With Vehicles and Stock off, enable Bills. Add an electricity bill and a policy with no vehicle. Both save and show their own due dates. The form has the exact optional-link explanation and no broken picker or module-install prompt.
7. Link a vehicle to a policy, switch Vehicles off, and edit the amount. The vehicle ID survives; Show/sheet use neutral saved-link words, and a Bills-only helper cannot read the vehicle name. Turn Vehicles on and the same vehicle reappears.
8. Repeat case 7 for a Stock Place, including a nested full path when Stock is on. A deleted place is repair state, never a guessed replacement.
9. A helper with both grants can suggest a link by live permanent ID. With only the referring-module grant or the target off, the helper schema omits that writable field and a forged link is refused. An import cannot assign an off-module target ID.
10. Switching a target module off/on, restarting, restoring a backup and syncing two household computers never clear or change the referring link. An optional module not installed at all also leaves the referring module loadable.
11. No current or future duplicate Vehicle insurance renewal appears because Vehicles was switched off. Item 105 defines the single authoritative policy row and migration before Bills promotion.
12. Keyboard focus reaches the explanation, Save and repair message; at 320px there is no sideways scroll and no unlabeled placeholder picker.
