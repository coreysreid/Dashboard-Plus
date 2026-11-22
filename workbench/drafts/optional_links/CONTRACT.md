# Core contract proposed

Keep `requires` for real hard dependencies. Add a declared `optional_requires` list to `module.toml`; a cross-module link may name a module in either list. It is nullable. Example promotion shape:

```toml
# Utilities
requires = ["people"]
optional_requires = ["home_layout"]
# services.meter = link to home_layout.meters, nullable

# Bills and insurance
requires = ["people"]
optional_requires = ["stock", "vehicles"]
# commitments.place and commitments.vehicle are nullable links
```

The loader must validate the named optional module and target table **when installed**, but may load the referring module without that target enabled or installed. A missing optional target does not block the referring module's own migration or ordinary records. Module migrations stay confined to their own tables. Do not add a foreign-key rule that makes a link to a temporarily off module fail or clears its value. Module-off is a view/permission state, not a delete. On a later enable, resolve saved permanent IDs; never match by name or room path.

The form renderer should include a link field only when its target module is active and the caller may see it. If hidden, a POST of the other fields preserves the saved link server-side; an attacker cannot forge an off-module ID in a form, import or helper suggestion. If the target is active, validate the ID, the grant, and the target's live state at save time. An explicit clear is allowed only when the field is visible and the person chooses it. A dangling historic ID remains as repair state; it is never an offered candidate.

Lists, sheets and helper schemas must distinguish **blank** from **saved but unavailable**. The former says “No meter place linked”; the latter says “Meter link saved; switch on Our home to see it.” Avoid resolving a name from an off module. Export should preserve stable IDs for recovery while marking a link unresolved; ordinary household print sheets should show only neutral words. Search and sorting cannot follow a hidden target. A grant to Utilities alone does not grant Home layout, and a grant to Bills does not grant Vehicles. Local private fields keep their existing travel rules.

The core can generalize this for a future optional `utilities.services` link from Bills. That link should not be added until it has its own deduplication and reminder ownership decision.
