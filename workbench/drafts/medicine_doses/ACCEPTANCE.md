# Medicine dose acceptance checks

Written **21 November 2026** for invented records only. Before promotion, implement the private link/picker and historical-display contract in [NOTES.md](NOTES.md).

1. A dose links to a real People medication detail for the **same recipient**. A link to an allergy, access detail or another person's medication is refused in form, API, migration and Review acceptance.
2. After opening a person and medication, the form still asks when and by whom; it never prefills a dose amount from the last entry. Unknown giver is explicit, not silently the signed-in user.
3. Two genuine entries close in time trigger a possible-repeat warning but can both be kept. A double tap or retry creates one entry, not two.
4. A member offline save survives restart and stays pending. Main accepts one row and rejects another; only a pulled acceptance appears among accepted history. A rejected row remains available for correction.
5. Edit the linked People medication text after a dose. The old event remains intelligible through an approved private historical label, without leaking either old or new text into ordinary lists, logs or exports.
6. Plant invented private sentinels in amount and historical text. The general list, Home, Needs attention, ordinary sheets, helper read, notification, error, URL and general export contain none. Deliberate Show reveals only to the active household user; backup retains the value.
7. The portable log and snapshot carry accepted medical detail only under an explicit `travels = "always"` decision. Access/other People details remain local. A paired member learns this medical history; the pairing copy says so. No helper grant reads or suggests a dose in v1.
8. Correct and mark a mistaken event without erasing audit history. A change never modifies the People's summary, and a missing event never produces a missed-dose claim.
9. Refuse deletion of a person or medication summary with linked doses until the household chooses a safe history/archive path. A switch-off, restore or epoch change must not make a stale member entry look accepted.
