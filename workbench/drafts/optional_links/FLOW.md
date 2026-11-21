# Batch 21 item 102: optional links from the household's side

Checked 21 November 2026 against shipped Utilities and Vehicles, the Bills and insurance draft, `docs/DESIGN.md` sections 5–6 and `src/dashboard/core/modules.py`. A link is optional only if the *record* makes sense without it. It does not install or switch on another list behind the household's back.

## Utilities when Our home is off

The household can switch on **Utilities and accounts** with People. Add an internet service shows Name, kind, provider, fault contact and private account details, with the usual privacy help. It does **not** show a broken Meter picker. Below the form, one quiet sentence says: **“Meter places are available if you switch on Our home. You can save this service without one.”** The service's Show page says **“No meter place linked.”** For internet and phone services, do not show a meter gap or imply every service has one.

If an electricity service already linked a meter and the household later switches Our home off, the link ID stays saved. Add/Edit hides the picker and says **“A meter link is saved. Switch on Our home to see or change it.”** Show and the Utilities sheet show the same neutral state; they do not reveal a stale room name from an off module. Saving another Utilities field cannot clear or rewrite the meter link. The household can remove the saved link only after switching Our home back on (or through an explicit, protected repair flow). It is not a hidden required field.

When Our home is switched on again, the Meter picker appears on relevant Utilities forms. A live saved link shows its name and full place path. A service with no link says **“Meter place (optional)”**. A saved ID whose meter was deleted says **“The linked meter is no longer there. Choose another, or leave it blank.”** Clearing it is a deliberate save; the core never chooses a same-named meter. A one-time Settings notice can say **“Meter places are available again. Review saved Utilities links when you have time.”** It is a link to the list, not a new Needs attention warning for every service.

## Bills and insurance when Vehicles is off

A household with only an electricity bill can switch on **Bills and insurance** without Vehicles or Household stock. Add/Edit asks for bill name, category, provider, amount (private), frequency and the date the person chooses. The optional Vehicle and Place fields are absent, with the short help **“Vehicle and place links appear when those lists are on. You can save this bill now.”** No extra module is silently enabled. The bill remains a dated commitment and does not assert it was paid.

If a policy has a Vehicle link and Vehicles is switched off, keep that ID. Show and the bill sheet say **“Vehicle link saved; switch on Vehicles to see it.”** Edit hides the Vehicle picker and preserves the link while other fields are saved. When Vehicles comes back, the exact linked vehicle appears; if it was deleted, offer an empty picker and the explicit repair sentence above, with **vehicle** in place of **meter**. A person may leave the link blank. The same rule applies to the optional Stock Place link. The provider link still requires People under this design.

This only solves the link dependency. Vehicles already owns insurance renewal. Until item 105 decides one authoritative reminder and a migration, Bills must not create a second warning for the same vehicle policy. Switching Vehicles off must not make a duplicate Bills reminder appear.

## What is visible where

| Surface | Linked module on and record live | Linked module off | Linked module on, target missing |
|---|---|---|---|
| Add/Edit | Optional picker, never preselected | Picker absent; short explanation | Empty picker; explicit repair text if an ID was saved |
| Show/list | Name and full path when appropriate | “Link saved; switch on [module] to see it” or “No [link] linked” | “Linked [kind] is no longer there” |
| Print/export | Only show a target name when target is on and permitted; an off-module sheet uses the neutral saved-link words | Preserve the opaque ID in a data export if needed for restore/import, label it unresolved, never guess a name | Preserve the ID and flag unresolved; do not silently erase it |
| Helper/connector | May use an exact ID only with access to both lists | Field unavailable to suggest; no off-module target name or picker values | Refuse a new dangling ID; show the member a repair prompt |

The neutral sentence must not leak an off module's private fields or expose a hidden value in page HTML. A helper cannot turn an optional dependency on. On a 320px form the explanation sits next to the missing picker, before Save, and can be reached by keyboard.
