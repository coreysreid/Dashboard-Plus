# Sync stage 1: exact test cases for the shipped offline foundation

Prepared **21 November 2026** for batch 19 item 85 against decision 0100 and `tests/test_sync_stage1.py` (19 tests passed locally). This refines the twelve broad checks in [STAGE1.md](STAGE1.md). It is a test plan Lane A can turn into assertions; it changes no shipped code. Stage 1 keeps everything on this computer: a snapshot and change-log reader are **offline representations**, not evidence of a network exchange. Use only invented names and unique test sentinels.

The current registry has **12 modules, 36 record tables** (the earlier draft counted 35 before Utilities was promoted) and one Documents copies relation. The implementation differs from the older proposal in two important ways: core adds IDs after each module's migrations under that module's confinement rule, and an access/other → medical People kind change is held locally until the text itself is typed again. Tests below use decision 0100's behavior, not the older proposal's “block kind edit” expectation.

A test should inspect both the ordinary database state and `sync.changes(conn)` / `sync.snapshot(conn, registry)`. For privacy cases, scan the **serialized bytes** of both offline outputs as well as parsed fields: absence from one parsed `patch` does not prove a value was not copied into an error, length, hash or other field. Never print a sentinel value in a CI failure message.

## Upgrade and identity

### S1-01 — existing household upgrades once, without rewriting records

**Fixture:** Load Smith, Garcia and Taylor separately with invented `today=2026-06-01`. In each, create one soft-deleted People row, disable Wine, add an invented Utilities service with a linked meter, and save a checked backup. Make a disposable copy shaped like core 0006 (no `global_id`, `row_revision` or `core__sync_*`) as the existing test's `make_old` helper does. Capture every module row's local `id`, fields, `deleted_at`, link IDs, audit count, Stock Lot sums, sheet text and relation pairs.

**Action:** Run `startup.prepare` twice on the old copy, closing the connection between starts.

**Assert:** First start creates `before-update-` backup, applies core 0007, gives every row in all **36** tables a nonempty parseable UUID version 4 (including deleted and switched-off rows), and sets `row_revision=0`. Local IDs, values, links, pair rows, audit count, Lot sums and sheet text match the before capture. One epoch starts at 1 with `new_ids` equal to the number of existing record rows; `sync.changes` is empty, because migration is a baseline, not invented history. `sync.check` is empty. Second start changes no ID, revision, row, epoch or backup count. Existing coverage: `UpgradeTests.test_each_example_household_gets_permanent_ids_once_and_no_record_changes`; **add** explicit Utilities fixture, UUID version assertion, Lot/sheet comparison and 36-table inventory assertion.

### S1-02 — interrupted large upgrade rolls back the affected module

**Fixture:** A true pre-stage-1 database with 3,000 invented People rows and 3,270 Stock Places. Inject a failure at ID allocation 1,500, after some People rows would have been touched.

**Action:** Run startup with the failure, inspect DB, then remove it and run startup twice.

**Assert:** First run reports People left out, no partly added identity columns/index/IDs in any People table, and no cross-module or core table was changed by that module's failed step. Dependent modules report their dependency failure. Retry gives all 6,270 rows unique IDs, one baseline epoch, no historical log; third run is a no-op. Check a generous bounded duration (the current fixture target is under 60 seconds) without requiring one machine's exact timing. Existing coverage: `UpgradeTests.test_a_large_household_is_upgraded_quickly_and_an_interrupted_upgrade_leaves_nothing_half_done`; **add** explicit cross-module/core before/after fingerprints for the failed step.

### S1-03 — module confinement during the core ID step

**Fixture:** In a disposable module migration, add a trigger on its own table that tries to update `core__settings` or a different module's table when backfill writes `global_id`. Put a sentinel in that other table.

**Action:** Run `startup.prepare` on an old household that needs this module upgraded.

**Assert:** The module is left out with a problem; its ID step rolls back and the other table/core sentinel is unchanged. No portable log line is made. This is a **new focused test** for decision 0055 applied to `sync.prepare`; it must not change shipped migrations to construct the fixture.

### S1-04 — ID integrity and unknown schema fail closed

**Fixture:** One clean upgraded household. In separate disposable copies, remove a global ID, drop its unique index and duplicate an ID, break a link with foreign-key checks off, add an undeclared `module__table`, and define a new sensitive column with no travel classification.

**Action:** Call `sync.check` and `sync.snapshot` on each copy.

**Assert:** `sync.check` names the exact table/field problem for each. The snapshot never silently treats the undeclared table or unreviewed private column as shared. A repaired copy returns an empty problem list. Existing tests cover unknown tables/columns and an unreviewed private column; **add** missing/duplicate ID and dangling-link corruption cases, including a relation endpoint.

### S1-05 — same names, different IDs; time cannot order operations

**Fixture:** Two People with the same invented display name, and a clock stub that alternates past and future timestamps.

**Action:** Edit the first person three times with different ordinary notes.

**Assert:** Both UUIDs differ and remain stable; local integer IDs remain separate. The edited row's revisions are 2, 3, 4, log sequence numbers strictly increase, and log patches appear in save order despite timestamp order. Existing coverage: `ChangeLogTests.test_same_names_get_different_ids_and_order_follows_saving_not_the_clock`.

## Everyday operations and links

### S1-06 — one logical Stock action, one revision per touched row

**Fixture:** One new invented rice item with unit kg and zero batches; record its ID/revision and current log sequence.

**Action:** Buy 5 kg; count its chosen batch as 3 kg; retry the same correction; Undo the correction through the normal action.

**Assert:** Purchase creates one movement and one Lot, updates Item total to 5 kg, and produces three log rows with the same operation ID: movement and Lot direct, Item `effect=1`. Each touched row gets one revision increment, even if reached twice in the transaction. Count creates one correction movement and a single grouped operation. Exact retry makes no extra row, delta, revision or log entry. Undo returns Lot/Item to 5 kg through a new operation rather than deleting log history. Existing coverage: `ChangeLogTests.test_a_stock_in_is_one_operation_and_totals_are_marked_as_worked_out`; **add** a forced failure between row save and log write and assert both roll back.

### S1-07 — Mark done and Undo are each atomic

**Fixture:** One invented Home care job with a chosen date and repeat, no Work done. Capture job revision and current log sequence.

**Action:** Mark done with an explicit next-date choice, retry the same operation token, then Undo.

**Assert:** Mark done adds exactly one Work done and edits the job, with one operation ID and one revision increment per affected record. Retry writes nothing. Undo deletes that Work done row and restores the prior job date in a **different** operation; log history grows rather than being erased. Existing coverage: `ChangeLogTests.test_mark_done_and_its_undo_are_one_operation_each_and_a_retry_adds_nothing`; **add** repeat-date and resulting job field assertion.

### S1-08 — links and Documents copies use permanent IDs

**Fixture:** Nested House → Kitchen → Pantry, an Item/Lot, a Home layout meter, Medical kit, Vehicle, Utilities service and Home care job linked through those rows; two Documents copy places, one document linking one of them. Put duplicate *names* on two places to make name matching unsafe.

**Action:** Move Pantry under another valid parent; add, repeat, remove and re-add the second copy place; attempt a Place cycle and an orphan link.

**Assert:** In `sync.snapshot`, every single link points to its target's UUID, never a local integer; the moved Place's `inside` patch is the new parent's UUID. A refused cycle writes no log. Documents pair identities are `(document UUID, copy-place UUID)` and a repeated add writes no extra pair; add/remove/re-add logs link/unlink/link once each. The Utility meter link resolves to Home layout's meter UUID, and that meter's place resolves to Stock Place UUID. Existing coverage spans `test_places_move_and_links_point_at_permanent_ids` and `test_copy_places_are_logged_as_pairs_of_permanent_ids`; **add** Utilities and duplicate-place-name assertions.

### S1-09 — switched-off module and table rebuild

**Fixture:** A Wine row with a known UUID; switch Wine off, then on. Separately simulate a module table rebuild that loses identity columns in a disposable copy.

**Action:** Restart after both cases.

**Assert:** Off/on retains the same UUID, revision and row. A rebuild that loses IDs gives affected records new IDs and starts a new epoch whose reason names the table; it does not pretend the old and new IDs match. Existing coverage: `test_module_off_and_on_keeps_ids_and_unknown_tables_or_columns_are_never_copied` and `test_a_table_rebuilt_without_its_ids_gets_new_ones_and_a_new_epoch`.

## Travel policy and privacy

### S1-10 — five medical kinds travel; access and other stay local

**Fixture:** Seven `people__important_info` rows for one invented person, one each with `kind=allergy, condition, medication, care_need, dietary, access, other`. Give each a unique detail sentinel; keep the People module on. Capture local field values and audit rows.

**Action:** Create all seven, edit an ordinary field on the parent, then edit each detail in place. Read both offline outputs and log records.

**Assert:** Five medical details appear in their rows' snapshot `values.detail` and in the matching change patch; `access` and `other` have `detail` in `withheld` but no value, derived hash, length or encoded value anywhere in serialized snapshot/log. All seven local values and audit entries remain intact. A browser/private reveal still requires Show; stage 1 did not make the UI public. Existing coverage: `TravelRuleTests.test_medical_details_travel_and_stay_private_on_screen` and `test_local_only_values_never_appear_in_the_change_log_or_snapshot`; **add** one exact per-row `patch`/`withheld` assertion after edits and a raw serialized length/encoding scan.

### S1-11 — changing a People kind cannot leak old local text

**Fixture:** An `access` row with a unique invented access-detail sentinel, and a separate `allergy` row with a different invented medical-detail sentinel.

**Action:** On the access row, change only `kind` to `medication`, build snapshot/log, then edit `detail` to new invented medication words. On the allergy row, change only `kind` to `access`, then back to `allergy` without retyping detail.

**Assert:** The access-origin sentinel never appears in portable output; after first kind change the snapshot lists `detail` in `withheld` and `core__sync_held` has the row/field. Only the newly typed medication words enter the patch and snapshot, and held status clears. The allergy→access log changes `kind` without a `detail: null` clear; switching back holds the old detail and does not resend it merely because the kind changed. All local detail values remain as typed. Existing coverage: `TravelRuleTests.test_kind_changes_across_the_boundary_never_move_an_old_private_value`; **add** explicit held-table and retype-clear assertions. **Stage 2 gate:** a receiving copy that saw the earlier allergy must get a deliberate replacement flow; stage 1 has no receiver, so do not assert remote erasure here.

### S1-12 — every other local-only field stays out, including Utilities

**Fixture:** Unique invented sentinels in each of the four Home layout `access_details`, Vehicle `registration`, Utilities `account_number` and `notes`. Put a distinct ordinary Pets `microchip` value in a Pet. Capture local records and audit.

**Action:** Create, edit an ordinary field on each row, delete/restore one record, read serialized `sync.changes` and `sync.snapshot`, and call `sync.check`.

**Assert:** All seven local-only values are absent from both outputs in raw and derived form and appear only as field names in `withheld`; they remain in local records and audit. The Pets microchip **does** appear because Corey confirmed it travels under 0089. `sync.check` is empty for the shipped declarations. Existing tests cover Home layout, Vehicle and the Pets declaration; **add** actual Utilities sentinels and Pets value projection. Do not log sentinels in test failure output.

### S1-13 — no local helper, settings or audit payload in portable output

**Fixture:** An invented sentinel in `core__audit` before/after JSON, a helper grant and pending proposal with separate sentinels, a backup folder ID in settings, and an ordinary row edit to trigger a portable line.

**Action:** Read all offline changes and snapshot.

**Assert:** No audit blob, helper key/fingerprint, proposal source, backup path or setting value appears; only the accepted record edit is represented. `core__audit` itself is unchanged. `sync.check` reports an unknown private column instead of exporting it. Existing coverage: `TravelRuleTests.test_history_keeps_the_private_value_but_is_never_the_change_log`; **add** a helper-grant sentinel and explicit serialized-output scan for its fingerprint-shaped value.

## Restore and release gate

### S1-14 — restoring a post-upgrade backup advances the epoch

**Fixture:** An upgraded Smith example, its checked daily backup, and one later invented People edit. Capture household ID, epoch, permanent IDs, revisions, log and row counts.

**Action:** Restore the checked backup, then Undo restore.

**Assert:** Restored rows keep the backup's UUIDs/revisions and household ID; epoch becomes greater than both the live and backed-up epoch, reason “Restored a backup.” Undo returns the later edit and advances epoch again with reason “Undid a restore.” No old operation is replayed as current. Existing coverage: `RestoreEpochTests.test_restore_and_undo_keep_ids_and_raise_the_epoch`; **add** log sequence/content comparison around restore.

### S1-15 — restoring a pre-upgrade backup does not match old IDs

**Fixture:** Upgrade an invented household, capture UUIDs and epoch, and make a checked backup converted to the pre-0007 schema in a disposable copy.

**Action:** Restore that old backup.

**Assert:** Every restored row gets a newly random UUID; none equals the former upgraded UUID for the same local integer ID. Household identity remains consistent with the restore workflow, epoch rises and its reason says the backup predated permanent IDs. Baseline records do not acquire fictitious historical log entries. Before stage 2, any previously paired member would have to pause for a new snapshot instead of matching by name. Existing coverage: `RestoreEpochTests.test_a_backup_from_before_permanent_ids_gets_new_ones_and_a_new_epoch`; **add** explicit empty-baseline-log assertion.

### S1-16 — offline release gate is honest about stage 1

**Fixture:** A clean upgraded household and one copy with each failure from S1-04. Check the Backups page text and inspect the loaded module declarations.

**Action:** Call `sync.check` on each and examine that no stage-1 scheduler, pairing listener, member key or send route is active.

**Assert:** Clean data yields `[]`; each corrupt/unreviewed copy yields a named blocker and no exchange is attempted. The page says records have permanent IDs and **nothing is shared yet**. This is a negative stage-1 boundary check; it does not test Tailscale, WireGuard, pairing or conflict resolution. Add a focused UI assertion if the Backups page wording changes.

## Priority for additional automated coverage

The current 19 tests cover the main behavior. The most valuable additions are **S1-12 Utilities values and Pets microchip projection**, **S1-11 held-table transitions**, **S1-04 corruption checks**, **S1-03 confinement trigger**, then the narrower assertions marked above. Keep fixtures in temporary folders and run the actual startup/record path; avoid tests that merely inspect implementation strings. Do not add a network test to stage 1. Pairing, the deliberate People-detail replacement action, member-local withheld values and remote security review are gates for stage 2 in decision 0089 and [SECURITY_REVIEW.md](SECURITY_REVIEW.md).

Sources checked 21 November 2026: decision 0100, `src/dashboard/core/sync.py`, `tests/test_sync_stage1.py`, shipped `modules/*/tables.toml`, and the older [STAGE1.md](STAGE1.md). No real household data is used.
