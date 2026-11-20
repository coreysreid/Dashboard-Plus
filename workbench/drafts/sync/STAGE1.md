# Sync stage 1: stable identities, revisions and filtered local change log

Prepared **20 November 2026** for batch 18 item 78 against accepted decision 0089, the **35 shipped module tables**, their migrations, the one `documents__documents__copies` relation table, and current core migrations 0001–0005. This is a core design for Lane A, not a migration or network feature. Stage 0's independent remote-boundary review remains the gate before stage 2 ships. All examples below are invented.

## What stage 1 must leave behind

- A random household ID, a different random device ID per installation, a restore epoch and an exchange-schema version. Neither ID comes from a name, local row number, time or path. A backup moved to another device keeps the household ID but gains a new device ID; a rollback on the same device cannot revive a retired epoch or key.
- Every shipped module record, including soft-deleted records and rows in switched-off modules, has a stable random `global_id` and a local `row_revision`. Local integer `id` and foreign keys stay in SQLite for the existing UI. New saves assign a global ID in the same transaction and increment the revision once for the logical change. The `deleted_at` field already supplies a tombstone source. A duplicate or missing global ID blocks future exchange rather than being guessed by name.
- A separate, append-only **portable change log** written atomically with the local change and `core__audit`. It contains a transaction/operation ID, device sequence, table, row global ID, field patch or tombstone, base and resulting revisions, schema version and affected relation pairs. It excludes local-only field values **before storage**. `core__audit` remains local and may contain private before/after JSON; it must never be reused as a network payload or dumped wholesale into the portable log.
- An outbox view of unsent local operations and a snapshot builder that uses the same versioned, filtered representation. Stage 1 exercises these offline only. Pairing, network listener, member keys, pull, push to Review and conflict resolution remain later stages.

The simplest schema path is new versioned migrations that add nullable `global_id` and `row_revision DEFAULT 0` to each module's record tables, followed by a checked core backfill and unique indexes. Update the generated system-column contract for future module tables. SQLite cannot safely add a non-null value to old rows in one `ALTER TABLE`; backfill and validate first, then enforce non-null in every write path and the sync gate (a later table rebuild may make it a database constraint). A core migration owns the sync metadata/log tables. **Do not edit released migrations.** Decision 0055 still confines a module's own migration to its own tables; the reviewed core backfill is the only cross-module orchestration.

## Table-by-table inventory and link order

Each row below gets `global_id`/`row_revision` unless marked relation or local core. **Shared** means eligible for the filtered exchange when that part is switched on, not that stage 1 sends anything. Foreign keys in future exchange use target **global IDs**, never local integer IDs. Assign all record IDs first, then translate and validate links; this avoids making link targets depend on migration order. Keep the named dependency order for snapshots and apply.

| Module/table | Shared record and link rule for stage 1 |
|---|---|
| `people__people` | Person root; ordinary name, contacts, address and notes are shared under 0089's full-copy rule. Help must discourage secrets in ordinary free text. |
| `people__roles` | `person` → `people__people`; role and call order travel. |
| `people__important_info` | `person` → People; `kind` travels. `detail` is conditional as specified below. |
| `stock__places` | `inside` → same table; retain the full parent chain and reject cycles or missing parents on later apply. |
| `stock__items` | `place` → Places. The item identity and user-entered fields travel; `quantity` and earliest `expires` are totals from Lots and must be recomputed rather than independent outbound edits. |
| `stock__lots` | `item` → Items; `place` → Places. Each physical batch has its own global ID and use-by date. |
| `stock__movements` | `item` → Items, `lot` → Lots, `place` → Places. Each movement is one immutable logical event with one operation ID; the resulting Lot and Item totals are effects, not second purchases or corrections. Legacy movements with no truthful Lot link keep it absent. |
| `pets__pets` | `owner` and `vet` → People. A microchip value is currently an ordinary field; treat the exact shipped schema as shared and flag the product/privacy choice before network release. |
| `pets__treatments` | `pet` → Pets; regimen fields travel. |
| `pets__given` | `treatment` → Treatments; each administration row has its own ID. |
| `pets__weigh_ins` | `pet` → Pets; each dated measurement has its own ID. |
| `pets__vet_visits` | `pet` → Pets, `vet` → People. |
| `home_layout__exits` | `place` → Stock Places; `access_details` stays on its origin. Route and notes are ordinary, printable data. |
| `home_layout__shutoffs` | `place` → Stock Places; `access_details` stays on its origin. |
| `home_layout__equipment` | `place` → Stock Places; `access_details` stays on its origin. |
| `home_layout__meters` | `place` → Stock Places; `access_details` stays on its origin. |
| `medical__kits` | `place` → Stock Places; `kept` (home/vehicle/elsewhere) and kit dates travel. |
| `medical__kit_checks` | `kit` → Kits, `checked_by` → People; each check is a distinct event. |
| `medical__training` | `person` → People; dates and ordinary notes travel. Medical safety detail policy is in People Important details, not a blanket refusal of Medical. |
| `documents__copy_places` | Named locations for copies, such as “Blue USB drive”; no scan or number field. |
| `documents__documents` | `holder` → People, `place` → Stock Places; `copies` is the relation below. Ordinary name, date and notes travel; no document file/number exists in the schema. |
| `documents__documents__copies` | **Relation, no local `id` column:** identity is `(document global_id, copy_place global_id)`. Log add/remove of that pair, not its local `from_id`/`to_id`; repeated add is idempotent. |
| `vehicles__vehicles` | `roadside_contact` → People, `parked_at` → Stock Places, `emergency_kit` → Stock Items; `registration` stays on its origin. |
| `vehicles__insurance` | `vehicle` → Vehicles; ordinary name, date and notes travel; do not invent policy-number fields. |
| `vehicles__services` | `vehicle` → Vehicles; each service row has its own ID. |
| `home_care__jobs` | `place` → Stock Places, `who_does_it` → People; optional repeat and chosen date travel. |
| `home_care__work_done` | `job` → Jobs, `done_by` → People. Mark done makes this row and changes its Job in **one** logged logical transaction; Undo must emit the inverse as another accepted local action, not erase history. |
| `garden__beds` | `place` → Stock Places. |
| `garden__crops` | Crop root. |
| `garden__plantings` | `bed` → Beds, `crop` → Crops. |
| `garden__harvests` | `planting` → Plantings; each harvest has its own ID. |
| `garden__jobs` | `bed` → Beds; completion and chosen due date travel. |
| `lent_out__loans` | `stock_item` → Stock Items, `borrower` → People; status and returned date travel. Mark returned and Undo are one logical row revision each. |
| `wine__wines` | Wine root; label details travel. |
| `wine__bottles` | `wine` → Wines; typed count and free-text place travel. Price paid is ordinary under decision 0095 and travels unless Corey later changes that product rule. |
| `wine__tastings` | `wine` → Wines; tasting notes are ordinary under 0095 and travel. Saving one never changes a bottle count. |

There are **35 record tables and one relation table**. The relation is not a 36th record with a made-up local ID. New modules must declare global-ID behavior and a per-column travel classification before stage 2 allows them in a snapshot.

## Core tables and household settings

| Existing table | Stage 1 treatment |
|---|---|
| `core__settings` | Classify by key, never copy the table wholesale. Household facts (`household.country`, `region`, `home_type`, `storeys`, `mobility_needs`, `hazards`, and fallback people/pet counts when their modules are off) are candidates for one reviewed household-settings record. `household.timezone` needs a decision: display context may differ by device. `setup.done`, `backups.second_copy` and `backups.folder_id` remain local. Unknown keys default local. |
| `core__modules` | Main's enabled parts define what is eligible to copy. Compare installed module **versions** on both devices before later exchange; never overwrite a member's installed code/version with a database row. Module-off records keep IDs locally and are not deleted. |
| `core__audit` | Local human history with local record IDs and possibly private before/after JSON. Never portable. Correlate new portable log with an opaque transaction ID, not raw audit blobs. |
| `core__helpers`, `core__helper_batches`, `core__proposals` | Local helper grants, fingerprints (outside DB), import staging, Review decisions and source names stay local. A person-accepted record change gets a portable operation; pending proposals do not become household records by being copied. Do not reuse helper keys for sync. |
| New `core__sync_*` tables | Household identity/epoch, per-device sequence, filtered changes and later cursors/outbox. Version the serialized fields and keep secrets in a separate protected key store, not in this log or backups. Core owns these migrations. |

Current module rows also have `created_at`, `updated_at`, `review_status`, `source`, local `batch_id`, `edited_by_person` and `deleted_at`. Define a deliberate exchange projection: `deleted_at` becomes a tombstone, user-facing provenance can be represented only after review, and local helper batch IDs never travel as foreign keys. Wall-clock timestamps may display but cannot choose a winning edit. Preserve the local columns and current UI while adding the projection.

## “Travels to members” rule, evaluated before logging

| Shipped field | Travel decision |
|---|---|
| `people__important_info.detail`, `kind` = `allergy`, `condition`, `medication`, `care_need` or `dietary` | **Yes.** Safety information remains behind Show on screen and may print on an emergency sheet. The `sensitive` display flag stays true. |
| Same `detail`, `kind` = `access` or `other` | **No.** Value remains on the computer where typed. `other` defaults local until an explicit product classification. |
| `home_layout__{exits,shutoffs,equipment,meters}.access_details` | **No**, on both main and member. |
| `vehicles__vehicles.registration` | **No**, on both main and member. |
| New field marked `sensitive` without a travel classification | **No** by default; fail the exchange-schema gate until reviewed. |
| Ordinary shipped fields | Eligible under 0089's full-copy rule; “ordinary” does not guarantee the user avoided typing a secret in free text. Keep the not-a-vault wording and revisit special fields such as Pets microchip before network release. |

Store the rule in the versioned exchange schema rather than inferring it from `sensitive`. The stage 1 logger receives a **logical operation** and current row kind, constructs an allowlisted patch, and validates that no excluded byte, derived hash, length, search token or raw audit JSON reaches its portable table. Snapshot and future outbox must use the same projection. A withheld marker is distinct from `null` and from a deliberate clear; applying it must **never** overwrite the receiving computer's local value. The UI's later “Kept on main” wording must not claim a value exists when only the field's policy is known.

**Kind transitions need an explicit stop:** an in-place `important_info` change between travel-yes and travel-no kinds must not let an old detail flow with the new kind, or make an old copied medical value vanish by ordinary sync. Before stage 2, design a deliberate “replace this detail” action: a new global row for the new classification, a tombstone for the old shared row only where appropriate, and a warning that an earlier copy or backup cannot be remotely erased. Block a cross-boundary kind edit in syncable state until that action and wording are implemented. A change of kind among the five medical kinds can keep the same row ID after normal validation. This is a product/core gate, not a field-filter workaround.

## Upgrade order for an existing household

1. **Preflight and backup:** close any other process, verify SQLite integrity, module migration state and enough disk space; make a checked backup with its existing restore/Undo path. Do not switch on a network listener. Capture counts of every active and soft-deleted table row, relation pair, Lot sum, movement, linked target, helper and audit row. Preserve existing keys outside backups.
2. **Migrate schemas in a controlled order:** core creates sync state/log metadata; each installed module gets its new versioned identity-column migration, including switched-off modules. Keep old migrations unchanged and 0055 confinement active. Use an explicit registry of the 35 record tables and the one relation table; unknown tables halt the sync gate rather than being copied raw.
3. **Backfill record IDs:** in one recoverable core operation, assign random unique IDs to every existing record, including deleted rows. Keep the current integer IDs, `created_at`, fields and link values unchanged. Validate uniqueness and non-null IDs before logging starts. Set `row_revision=0` for this accepted baseline; a snapshot contains it, but do not fabricate one historical change per old audit entry.
4. **Map links:** build an integer-ID → global-ID map per table. Check each single link and every `documents__documents__copies` pair against its target, including Stock's nested Places and current Lots. Cross-module links are translated in a checked core reader, not rewritten by a module migration. Missing targets, cycles, or a link into a part absent on a member are explicit errors for later snapshot/pairing.
5. **Start atomic logging:** every subsequent create/edit/delete/restore/Undo passes a logical operation through the filtered serializer under the same write transaction as local rows and audit. Verify derived Stock totals and grouped Mark done effects do not become duplicate independent operations. A crash before commit leaves no partial IDs or log; a retry uses one operation ID.
6. **Verify and release locally:** compare captured counts, values, links, sheet output and an ordinary restore/Undo on invented fixtures. Run a snapshot builder offline and scan its bytes and the portable log for unique local-only sentinels. Keep sync unavailable if any null/duplicate ID, version mismatch, unsupported module, unclassified sensitive field or failed integrity check remains. Stage 2 then adds pairing and a checked first pull; it must not infer matching IDs between two pre-existing independent copies by equal names.

A restored backup that already contains global IDs preserves them. A backup from **before** stage 1 has none: rerun the upgrade under a **new restore epoch**; if any member was ever paired, pause and require a fresh comparison/snapshot rather than matching the newly generated IDs to old member rows. Device identity and revocation state must not roll back with a database restore; the exact protected local ledger and backup manifest need review before stage 2. A backup moved to a new computer must not clone the original device identity. No household is asked to repair IDs by hand.

## Acceptance checks before stage 1 is called complete

1. Upgrade fresh and existing invented Smith, Garcia and Taylor copies, including disabled modules and soft-deleted rows. Every one of the 35 table types present gets non-null, unique random IDs. Run the upgrade twice: the second changes no IDs, row counts or values.
2. Upgrade the 6,270-record speed fixture. Compare record counts, original integer IDs, links, Lot sums, dates and sheet text before/after; memory and time stay bounded. Interrupt and rerun backfill at several points without duplicate IDs or half-written records.
3. Verify the documents copy-place relation by adding, removing and re-adding one pair. Its portable identity is the two endpoint global IDs; duplicate add does not make another pair. Deleting either endpoint yields the documented relation removal, not an orphan.
4. Move a Stock Place, reject a cycle, and verify all place/item/Lot/Home layout/Medical/Vehicles/Home care/Garden links still resolve through global IDs. Missing targets block exchange and leave local rows intact.
5. Create a Stock movement, count a Lot, Undo it, and Mark done/Undo a Home care job. Each logical action has one operation ID and atomic affected-row group; no double Stock delta or duplicate Work done on retry. Existing local audit remains intact.
6. Put unique invented sentinel strings in People `kind=access` and `kind=other` details, all four Home layout `access_details` fields and Vehicle registration. Edit ordinary fields on those rows, build snapshots and portable changes, and scan bytes, error text and debug logs. No sentinel or derived length/hash appears. The origin's local values survive the edit and a simulated withheld apply.
7. Put invented allergy, condition, medication, care_need and dietary detail in People. Their filtered snapshots and changes include the detail; opening the receiving record still requires Show. Test an unknown/new private column: the exchange gate fails closed.
8. Try medical→access and access→medical kind changes on a row with an existing value. The cross-boundary operation is blocked until the deliberate replacement flow exists; it never exports a prior access value or silently clears a copied medical value.
9. Create two records with identical names and different local IDs. Their global IDs differ; neither snapshot nor migration matches by name. Change local clocks drastically: operation ordering and revisions still follow the transaction sequence.
10. Restore a post-upgrade backup and Undo, then a pre-upgrade backup. IDs are preserved in the first case; the second gets new IDs and epoch, with sync paused if it was ever paired. Revoked helper/member identity cannot be revived by restoring a database.
11. Switch a module off/on and install an older or unknown module version. Existing IDs and records survive. No raw SQLite table or unknown column is silently serialized; pairing waits for compatible exchange schemas.
12. Review a `core__audit` entry containing an invented local-only sentinel while the portable log does not. Helper grants, pending proposals, backup folder ID, session key and local paths are absent from snapshot/outbox. The `core__audit` row itself is unchanged and never used as a wire payload.

**Source and limit:** Decision 0089, decision 0055, shipped `modules/*/tables.toml`, module migrations, `src/dashboard/core/{schema,settings,records,restore}.py` and core migrations 0001–0005 were checked **20 November 2026**. This file proposes the stage 1 implementation boundary and tests; it does not claim a database migration has run or that a remote security review is complete.
