"""Tests for sync stage 1: permanent record IDs, revisions, the filtered change log and the travel rule (decision 0100)."""
import hashlib
import itertools
import json
import logging
import shutil
import sqlite3
import time
from datetime import date
from unittest import mock

from support import ROOT, TempDirTestCase
from dashboard.core import actions, backups, db, migrations, modules, proposals, records, restore, settings, startup
from dashboard.core import sync
from dashboard.core.schema import table_name
import load_example
import make_migration

MODULES_DIR = ROOT / "modules"
SYNC_TABLES = ("core__sync_state", "core__sync_epochs", "core__sync_tables", "core__sync_changes", "core__sync_held")
LATER_CORE_TABLES = ("core__helper_allowances",  # core 0008 (decision 0101), released after stage 1
                     "core__reminder_moves",  # core 0010 (decision 0117)
                     "core__sharing_choices")  # core 0011 (decision 0140)
LATER_CORE_COLUMNS = {"core__proposals": ("entry_kind",),  # core 0009 (decision 0105), released after stage 1
                      "core__helper_batches": ("receipt_json", "finished_at", "repeat_ok_json")}
MEDICAL = ("allergy", "condition", "medication", "care_need", "dietary")


def make_old(path):
    """Turn a data file back into the shape every household had before stage 1: no permanent IDs, no
    revisions, no sync tables, core at step 6. Used to test the upgrade of an existing household."""
    conn = sqlite3.connect(path)
    try:
        for name in SYNC_TABLES + LATER_CORE_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {name}")
        for name, later in LATER_CORE_COLUMNS.items():
            for column in later:
                conn.execute(f"ALTER TABLE {name} DROP COLUMN {column}")
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
            columns = {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}
            if sync.ID in columns:
                conn.execute(f"DROP INDEX IF EXISTS {name}__{sync.ID}__idx")
                conn.execute(f"ALTER TABLE {name} DROP COLUMN {sync.ID}")
                conn.execute(f"ALTER TABLE {name} DROP COLUMN {sync.REVISION}")
        conn.execute("DELETE FROM core__migrations WHERE track = 'core' AND number >= 7")
        conn.execute("PRAGMA user_version = 6")
        conn.commit()
    finally:
        conn.close()


def old_schema() -> dict:
    """{table: [columns]} as the released migrations before stage 1 make them (core 0001-0006, then modules)."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(migrations.BOOTSTRAP)
        core = migrations.load_track(migrations.CORE_TRACK, migrations.CORE_FOLDER)[:6]
        found, _ = modules.discover(MODULES_DIR)
        for migration in core + [m for module in found for m in module.migrations]:
            for statement in db.split_statements(migration.sql):
                conn.execute(statement)
        return schema_of(conn)
    finally:
        conn.close()


def schema_of(conn) -> dict:
    return {name: [r[1] for r in conn.execute(f"PRAGMA table_info({name})")]
            for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND "
                                        "name != 'sqlite_sequence' ORDER BY name").fetchall()}


def contents(conn, registry) -> dict:
    """Every row of every module table (deleted ones too), without the stage 1 columns."""
    found = {}
    for name in registry:
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {name} ORDER BY id")]
        found[name] = [{k: v for k, v in row.items() if k not in (sync.ID, sync.REVISION)} for row in rows]
    return found


def fingerprints(text: str) -> list[str]:
    data = text.encode("utf-8")
    return [hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest(), hashlib.sha1(data).hexdigest()]


class SyncTestCase(TempDirTestCase):
    """A fresh data folder with every shipped module."""

    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, MODULES_DIR)
        self.assertEqual(self.report.module_problems, {})
        self.open()

    def open(self):
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)

    def log(self, after=0):
        return sync.changes(self.conn, after, limit=100000)

    def last_seq(self):
        return self.conn.execute("SELECT COALESCE(MAX(seq), 0) FROM core__sync_changes").fetchone()[0]

    def log_text(self) -> str:
        return json.dumps([list(r) for r in self.conn.execute("SELECT * FROM core__sync_changes")])

    def snapshot_text(self) -> str:
        return json.dumps(sync.snapshot(self.conn, self.registry))

    def gid(self, table, record_id):
        return self.conn.execute(f"SELECT global_id FROM {table} WHERE id = ?", (record_id,)).fetchone()[0]

    def first_choice(self, table, column):
        return self.registry[table].table.columns[column].choices[0].key


class UpgradeTests(TempDirTestCase):
    """STAGE1.md check 1 (and 2): existing households are upgraded once, safely, without changing a record."""

    def household(self, name):
        data = self.tmp / name / "data"
        load_example.load(name, data, MODULES_DIR, today=date(2026, 6, 1))
        report = startup.prepare(data, MODULES_DIR)
        conn = db.connect(data / "dashboard.db")
        try:
            registry = records.build_registry(report.loaded)
            store = records.Records(conn, registry)
            visitor = store.create("people__people", {"name": "Deleted visitor", "lives_here": False})
            store.delete("people__people", visitor)
            settings.set_module_enabled(conn, "wine", False)
        finally:
            conn.close()
        make_old(data / "dashboard.db")
        return data

    def test_each_example_household_gets_permanent_ids_once_and_no_record_changes(self):
        expected_old = old_schema()
        for name in ("smith", "garcia", "taylor"):
            with self.subTest(household=name):
                data = self.household(name)
                path = data / "dashboard.db"
                conn = sqlite3.connect(path)
                conn.row_factory = sqlite3.Row
                self.assertEqual(schema_of(conn), expected_old)  # truly the shape before stage 1
                found, _ = modules.discover(MODULES_DIR)
                registry = records.build_registry(found)
                before = contents(conn, registry)
                audit_before = conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
                conn.close()
                backups_before = set((data / "backups").glob("before-update-*.db"))

                report = startup.prepare(data, MODULES_DIR)
                self.assertEqual(report.module_problems, {})
                self.assertIn("core 0007 (sync_identity)", report.applied)
                self.assertEqual(len(set((data / "backups").glob("before-update-*.db")) - backups_before), 1)

                conn = db.connect(path)
                self.addCleanup(conn.close)
                registry = records.build_registry(report.loaded)
                self.assertEqual(contents(conn, registry), before)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0], audit_before)
                total, ids = 0, {}
                for table in registry:
                    rows = conn.execute(f"SELECT id, global_id, row_revision, deleted_at FROM {table}").fetchall()
                    total += len(rows)
                    self.assertTrue(all(r["global_id"] and r["row_revision"] == 0 for r in rows), table)
                    ids[table] = {r["id"]: r["global_id"] for r in rows}
                    self.assertEqual(len(set(ids[table].values())), len(rows), table)
                self.assertTrue(any(r["deleted_at"] for r in conn.execute(
                    "SELECT deleted_at FROM people__people")))  # soft-deleted rows got one too
                self.assertEqual(sync.changes(conn), [])  # the baseline is not invented history
                self.assertEqual([(e["epoch"], e["new_ids"]) for e in sync.epochs(conn)], [(1, total)])
                self.assertEqual(sync.check(conn, registry), [])
                conn.close()

                again = startup.prepare(data, MODULES_DIR)  # a second start changes nothing
                self.assertEqual(again.applied, [])
                conn = db.connect(path)
                self.addCleanup(conn.close)
                for table in registry:
                    self.assertEqual({r[0]: r[1] for r in conn.execute(f"SELECT id, global_id FROM {table}")},
                                     ids[table])
                self.assertEqual(contents(conn, registry), before)
                self.assertEqual(len(sync.epochs(conn)), 1)
                self.assertEqual(len(set((data / "backups").glob("before-update-*.db")) - backups_before), 1)

    def test_a_large_household_is_upgraded_quickly_and_an_interrupted_upgrade_leaves_nothing_half_done(self):
        data = self.tmp / "data"
        startup.prepare(data, MODULES_DIR)
        path = data / "dashboard.db"
        make_old(path)
        conn = sqlite3.connect(path)
        stamp = "2026-06-01T00:00:00+00:00"
        conn.executemany("INSERT INTO people__people (created_at, updated_at, name) VALUES (?, ?, ?)",
                         [(stamp, stamp, f"Invented person {n}") for n in range(3000)])
        conn.executemany("INSERT INTO stock__places (created_at, updated_at, name) VALUES (?, ?, ?)",
                         [(stamp, stamp, f"Invented shelf {n}") for n in range(3270)])
        conn.commit()
        conn.close()
        calls, real = [0], sync.new_id

        def failing_once():
            calls[0] += 1
            if calls[0] == 1500:
                raise sync.SyncError("Invented interruption part-way through.")
            return real()

        with mock.patch.object(sync, "new_id", side_effect=failing_once):
            report = startup.prepare(data, MODULES_DIR)
        stopped = [name for name, problems in report.module_problems.items()
                   if any("permanent IDs" in p for p in problems)]
        self.assertEqual(len(stopped), 1)
        found = {m.name: m for m in modules.discover(MODULES_DIR)[0]}
        conn = db.connect(path)
        self.addCleanup(conn.close)
        for table in found[stopped[0]].tables:  # rolled back whole: no column, no ID, no index
            self.assertFalse(sync.has_identity(conn, table_name(stopped[0], table)))
        conn.close()

        started = time.monotonic()
        report = startup.prepare(data, MODULES_DIR)
        self.assertLess(time.monotonic() - started, 60)
        self.assertEqual(report.module_problems, {})
        conn = db.connect(path)
        self.addCleanup(conn.close)
        registry = records.build_registry(report.loaded)
        self.assertEqual(sync.check(conn, registry), [])
        for table, count in (("people__people", 3000), ("stock__places", 3270)):
            ids = [r[0] for r in conn.execute(f"SELECT global_id FROM {table}")]
            self.assertEqual((len(ids), len(set(ids))), (count, count))


class ChangeLogTests(SyncTestCase):
    """STAGE1.md checks 3, 4, 5, 9 and 11: the change log on everyday changes."""

    def test_a_new_record_gets_its_id_and_revision_1_and_each_change_adds_one(self):
        person = self.records.create("people__people", {"name": "Alex Example"})
        gid = self.gid("people__people", person)
        self.assertEqual(len(gid), 36)
        self.records.update("people__people", person, {"name": "Alex Sample"})
        self.records.delete("people__people", person)
        self.records.restore("people__people", person)
        entries = [e for e in self.log() if e["global_id"] == gid]
        self.assertEqual([(e["action"], e["base_revision"], e["revision"]) for e in entries],
                         [("create", 0, 1), ("update", 1, 2), ("delete", 2, 3), ("restore", 3, 4)])
        self.assertEqual(entries[1]["columns"], ["name"])
        self.assertEqual(entries[1]["patch"], {"name": "Alex Sample"})
        self.assertEqual(self.gid("people__people", person), gid)  # never changes
        self.assertEqual(self.records.get("people__people", person)["row_revision"], 4)
        self.assertEqual(len({e["operation_id"] for e in entries}), 4)

    def test_copy_places_are_logged_as_pairs_of_permanent_ids(self):
        blue = self.records.create("documents__copy_places", {"name": "Blue USB drive"})
        cloud = self.records.create("documents__copy_places", {"name": "Family cloud folder"})
        kind = self.first_choice("documents__documents", "kind")
        doc = self.records.create("documents__documents", {"name": "Invented lease", "kind": kind, "copies": [blue]})
        start = self.last_seq()
        self.records.update("documents__documents", doc, {"copies": [blue, cloud]})
        self.records.update("documents__documents", doc, {"copies": [blue, cloud]})  # the same again: nothing
        self.records.update("documents__documents", doc, {"copies": [blue]})
        self.records.update("documents__documents", doc, {"copies": [blue, cloud]})
        pairs = [(e["action"], e["global_id"], e["target_id"]) for e in self.log(start)
                 if e["table_name"] == "documents__documents__copies"]
        d, c = self.gid("documents__documents", doc), self.gid("documents__copy_places", cloud)
        self.assertEqual(pairs, [("link", d, c), ("unlink", d, c), ("link", d, c)])
        joins = self.conn.execute("SELECT COUNT(*) FROM documents__documents__copies").fetchone()[0]
        self.assertEqual(joins, 2)
        self.records.delete("documents__documents", doc)  # its pairs go with it as one tombstone, never orphans
        snap = sync.snapshot(self.conn, self.registry)
        ids = {r["id"]: r for r in snap["records"]}
        for pair in [p for p in snap["pairs"] if p["table"] == "documents__documents__copies"]:
            self.assertIn(pair["from"], ids)
            self.assertIn(pair["to"], ids)
        self.assertTrue(ids[d]["deleted"])
        self.assertEqual(sync.check(self.conn, self.registry), [])

    def test_places_move_and_links_point_at_permanent_ids(self):
        house = self.records.create("stock__places", {"name": "House"})
        kitchen = self.records.create("stock__places", {"name": "Kitchen", "inside": house})
        shed = self.records.create("stock__places", {"name": "Shed"})
        start = self.last_seq()
        self.records.update("stock__places", kitchen, {"inside": shed})
        moved = self.log(start)[-1]
        self.assertEqual(moved["patch"], {"inside": self.gid("stock__places", shed)})
        with self.assertRaises(records.ValidationError):  # a place inside itself is refused, as before
            self.records.update("stock__places", shed, {"inside": kitchen})
        self.assertEqual(self.last_seq(), moved["seq"])  # a refused change writes nothing
        item = self.records.create("stock__items", {"name": "Invented torch", "place": kitchen})
        self.records.create("home_layout__exits", {"name": "Back door", "place": kitchen})
        self.records.create("medical__kits", {"name": "Invented kit", "place": kitchen, "kept": "home"})
        self.records.create("vehicles__vehicles", {"name": "Invented car", "parked_at": shed, "emergency_kit": item})
        self.records.create("home_care__jobs", {"name": "Invented job", "place": shed,
                                                "kind": self.first_choice("home_care__jobs", "kind")})
        self.records.create("garden__beds", {"name": "Invented bed", "place": shed})
        snap = sync.snapshot(self.conn, self.registry)
        ids = {r["id"] for r in snap["records"]}
        for row in snap["records"]:
            info = self.registry[row["table"]]
            for column, value in row["values"].items():
                if info.table.columns[column].type == "link" and value is not None:
                    self.assertIn(value, ids, (row["table"], column))
        self.assertGreaterEqual(len(snap["records"]), 9)
        self.assertEqual(sync.check(self.conn, self.registry), [])

    def test_a_stock_in_is_one_operation_and_totals_are_marked_as_worked_out(self):
        item = self.records.create("stock__items", {"name": "Invented rice", "unit": "kg"})
        start = self.last_seq()
        self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": "5"})
        entries = self.log(start)
        self.assertEqual(len({e["operation_id"] for e in entries}), 1)
        by_table = {e["table_name"]: e for e in entries}
        self.assertEqual(set(by_table), {"stock__movements", "stock__lots", "stock__items"})
        self.assertEqual(len(entries), 3)  # one line per record, even when touched twice
        self.assertEqual((by_table["stock__movements"]["effect"], by_table["stock__items"]["effect"]), (0, 1))
        self.assertEqual(by_table["stock__lots"]["action"], "create")
        lot = self.conn.execute("SELECT id FROM stock__lots WHERE item = ?", (item,)).fetchone()[0]
        self.assertEqual(self.records.get("stock__lots", lot)["row_revision"], 1)

        start = self.last_seq()
        counted = self.records.count_batch("stock__lots", lot, "3", "5")
        entries = self.log(start)
        self.assertEqual(len({e["operation_id"] for e in entries}), 1)
        self.assertEqual(sorted(e["table_name"] for e in entries), ["stock__items", "stock__lots", "stock__movements"])
        again = self.last_seq()
        self.assertEqual(self.records.count_batch("stock__lots", lot, "3", "3")["status"], "same")  # a retry
        self.assertEqual(self.last_seq(), again)

        start = self.last_seq()
        self.records.delete("stock__movements", counted["movement"])  # undo the correction
        entries = self.log(start)
        self.assertEqual(len({e["operation_id"] for e in entries}), 1)
        self.assertEqual(float(self.records.get("stock__lots", lot)["quantity"]), 5.0)  # no double change
        self.assertEqual(sorted((e["table_name"], e["action"], e["effect"]) for e in entries),
                         [("stock__items", "update", 1), ("stock__lots", "update", 1),
                          ("stock__movements", "delete", 0)])

    def test_mark_done_and_its_undo_are_one_operation_each_and_a_retry_adds_nothing(self):
        jobs = "home_care__jobs"
        job = self.records.create(jobs, {"name": "Invented gutters", "kind": self.first_choice(jobs, "kind")})
        info = self.registry[jobs]
        op = actions.new_operation()
        start = self.last_seq()
        answers = {"done_on": "2026-11-19", "done_by": None, "notes": None}
        actions.complete(self.records, jobs, job, "done", answers, actions.revision(self.records, info, job), op,
                         next_choice="none", today=date(2026, 11, 19))
        done = self.log(start)
        self.assertEqual(len({e["operation_id"] for e in done}), 1)
        self.assertEqual(sorted((e["table_name"], e["action"]) for e in done),
                         [("home_care__jobs", "update"), ("home_care__work_done", "create")])
        middle = self.last_seq()
        repeated = actions.complete(self.records, jobs, job, "done", answers, 0, op, next_choice="none",
                                    today=date(2026, 11, 19))
        self.assertTrue(repeated.get("repeated"))
        self.assertEqual(self.last_seq(), middle)
        actions.undo(self.records, jobs, job, op)
        undone = self.log(middle)
        self.assertEqual(len({e["operation_id"] for e in undone}), 1)
        self.assertNotEqual(undone[0]["operation_id"], done[0]["operation_id"])
        self.assertEqual(sorted((e["table_name"], e["action"]) for e in undone),
                         [("home_care__jobs", "update"), ("home_care__work_done", "delete")])
        self.assertEqual(len(self.log(start)), 4)  # history is added to, never erased

    def test_same_names_get_different_ids_and_order_follows_saving_not_the_clock(self):
        a = self.records.create("people__people", {"name": "Sam Example"})
        b = self.records.create("people__people", {"name": "Sam Example"})
        self.assertNotEqual(self.gid("people__people", a), self.gid("people__people", b))
        times = itertools.cycle(["2031-01-01T00:00:00+00:00", "1999-01-01T00:00:00+00:00", "2040-01-01T00:00:00+00:00",
                                 "1970-01-02T00:00:00+00:00"])
        odd = records.Records(self.conn, self.registry, clock=lambda: next(times))  # a clock jumping about
        start = self.last_seq()
        odd.update("people__people", a, {"notes": "first"})
        odd.update("people__people", a, {"notes": "second"})
        odd.update("people__people", a, {"notes": "third"})
        entries = self.log(start)
        self.assertEqual([e["patch"]["notes"] for e in entries], ["first", "second", "third"])
        self.assertEqual([e["revision"] for e in entries], [2, 3, 4])
        self.assertEqual([e["seq"] for e in entries], sorted(e["seq"] for e in entries))

    def test_module_off_and_on_keeps_ids_and_unknown_tables_or_columns_are_never_copied(self):
        wine = self.records.create("wine__wines", {"name": "Invented red"})
        gid = self.gid("wine__wines", wine)
        settings.set_module_enabled(self.conn, "wine", False)
        self.conn.close()
        self.report = startup.prepare(self.data, MODULES_DIR)
        self.open()
        settings.set_module_enabled(self.conn, "wine", True)
        self.assertEqual(self.gid("wine__wines", wine), gid)
        self.conn.execute("CREATE TABLE wine__invented_extra (id INTEGER PRIMARY KEY, secret TEXT)")
        self.conn.execute("ALTER TABLE wine__wines ADD COLUMN invented_extra TEXT")
        self.conn.execute("UPDATE wine__wines SET invented_extra = 'SENTINEL-RAW-COLUMN-5e2' WHERE id = ?", (wine,))
        self.records.update("wine__wines", wine, {"name": "Invented red, renamed"})
        self.assertNotIn("SENTINEL-RAW-COLUMN-5e2", self.snapshot_text() + self.log_text())
        self.assertIn("wine__invented_extra is not declared by any module in use, so it cannot be shared.",
                      sync.check(self.conn, self.registry))


    def test_a_table_rebuilt_without_its_ids_gets_new_ones_and_a_new_epoch(self):
        self.records.create("wine__wines", {"name": "Invented white"})
        self.conn.execute("DROP INDEX wine__wines__global_id__idx")
        self.conn.execute("ALTER TABLE wine__wines DROP COLUMN global_id")  # as a careless rebuild would
        self.conn.close()
        self.report = startup.prepare(self.data, MODULES_DIR)
        self.open()
        self.assertEqual(sync.check(self.conn, self.registry), [])
        last = sync.epochs(self.conn)[-1]
        self.assertEqual((last["epoch"], last["new_ids"]), (2, 1))
        self.assertIn("rebuilt wine__wines", last["reason"])


class TravelRuleTests(SyncTestCase):
    """STAGE1.md checks 6, 7, 8 and 12: values that stay on this computer never reach the change log."""

    def make_private_rows(self):
        sentinels = {}
        person = self.records.create("people__people", {"name": "Invented Person"})
        self.person = person
        info_ids = {}
        for kind in ("access", "other"):
            sentinels[f"people {kind}"] = f"SENTINEL-{kind.upper()}-7f3a"
            info_ids[kind] = self.records.create("people__important_info",
                                                 {"person": person, "kind": kind, "detail": sentinels[f"people {kind}"]})
        rows = {}
        for table in ("exits", "shutoffs", "equipment", "meters"):
            name = f"home_layout__{table}"
            values = {"name": f"Invented {table}"}
            if "kind" in self.registry[name].table.columns:
                values["kind"] = self.first_choice(name, "kind")
            rows[name] = self.records.create(name, values)
            sentinels[name] = f"SENTINEL-{table.upper()}-c41d"  # a code saved before decision 0141, now retired
            self.conn.execute(f"UPDATE {name} SET access_details = ? WHERE id = ?", (sentinels[name], rows[name]))
        rows["vehicles__vehicles"] = self.records.create("vehicles__vehicles", {"name": "Invented van",
                                                                              "registration": "SENTINEL-REG-44d1"})
        sentinels["vehicles__vehicles"] = "SENTINEL-REG-44d1"
        return sentinels, rows, info_ids

    def assert_absent(self, sentinels):
        text = self.snapshot_text() + self.log_text()
        for label, value in sentinels.items():
            self.assertNotIn(value, text, label)
            for derived in fingerprints(value):
                self.assertNotIn(derived, text, label)

    def test_local_only_values_never_appear_in_the_change_log_or_snapshot(self):
        captured = []
        handler = logging.Handler()
        handler.emit = lambda record_: captured.append(record_.getMessage())
        logging.getLogger().addHandler(handler)
        self.addCleanup(logging.getLogger().removeHandler, handler)
        sentinels, rows, info_ids = self.make_private_rows()
        for name, record_id in rows.items():
            self.records.update(name, record_id, {"name": "Renamed " + name})
        self.records.update("people__important_info", info_ids["access"], {"kind": "other"})  # both stay local
        self.records.delete("vehicles__vehicles", rows["vehicles__vehicles"])
        self.records.restore("vehicles__vehicles", rows["vehicles__vehicles"])
        self.assert_absent(sentinels)
        self.assertFalse([m for m in captured if any(v in m for v in sentinels.values())])
        for name, record_id in rows.items():  # still kept, unchanged, on this computer
            column = "registration" if name.startswith("vehicles") else "access_details"
            self.assertEqual(self.conn.execute(f"SELECT {column} FROM {name} WHERE id = ?", (record_id,))
                             .fetchone()[0], sentinels[name])
        for entry in self.log():
            columns = self.registry[entry["table_name"]].table.columns if entry["table_name"] in self.registry else {}
            self.assertTrue(all(isinstance(w, str) and w in columns for w in entry["withheld"]))
        withheld = {(e["table_name"], tuple(e["withheld"])) for e in self.log() if e["action"] == "create"}
        self.assertIn(("vehicles__vehicles", ("registration",)), withheld)
        self.assertIn(("people__important_info", ("detail",)), withheld)

    def test_history_keeps_the_private_value_but_is_never_the_change_log(self):
        sentinels, rows, _ = self.make_private_rows()
        audit = [tuple(r) for r in self.conn.execute("SELECT * FROM core__audit ORDER BY id")]
        self.assertTrue(any(sentinels["vehicles__vehicles"] in (r[7] or "") for r in audit))  # local history has it
        settings.put(self.conn, "backups.folder_id", "SENTINEL-FOLDER-ID-0a9")
        proposals.stage_import(self.conn, "invented.csv", [(2, "people__people", {"name": "SENTINEL-PROPOSAL-77"})])
        self.records.update("vehicles__vehicles", rows["vehicles__vehicles"], {"notes": "Ordinary note"})
        self.assert_absent(dict(sentinels, folder="SENTINEL-FOLDER-ID-0a9", proposal="SENTINEL-PROPOSAL-77"))
        self.assertEqual([tuple(r) for r in self.conn.execute("SELECT * FROM core__audit ORDER BY id")][:len(audit)],
                         audit)  # the history itself is not changed

    def test_medical_details_travel_and_stay_private_on_screen(self):
        person = self.records.create("people__people", {"name": "Invented Patient"})
        for kind in MEDICAL:
            self.records.create("people__important_info", {"person": person, "kind": kind,
                                                           "detail": f"Invented {kind} detail"})
        text = self.snapshot_text() + self.log_text()
        for kind in MEDICAL:
            self.assertIn(f"Invented {kind} detail", text)
        self.assertTrue(self.registry["people__important_info"].table.columns["detail"].sensitive)

    def test_kind_changes_across_the_boundary_never_move_an_old_private_value(self):
        person = self.records.create("people__people", {"name": "Invented Person"})
        access = self.records.create("people__important_info", {"person": person, "kind": "access",
                                                                "detail": "SENTINEL-KEY-UNDER-POT-31"})
        self.records.update("people__important_info", access, {"kind": "medication"})  # label changed only
        self.records.update("people__people", person, {"notes": "An ordinary edit"})
        self.assertNotIn("SENTINEL-KEY-UNDER-POT-31", self.snapshot_text() + self.log_text())
        gid = self.gid("people__important_info", access)
        snap = {r["id"]: r for r in sync.snapshot(self.conn, self.registry)["records"]}
        self.assertEqual(snap[gid]["withheld"], ["detail"])  # held here until it is typed again
        self.records.update("people__important_info", access, {"detail": "Invented daily tablet"})
        self.assertIn("Invented daily tablet", self.log_text())
        snap = {r["id"]: r for r in sync.snapshot(self.conn, self.registry)["records"]}
        self.assertEqual(snap[gid]["values"]["detail"], "Invented daily tablet")

        medical = self.records.create("people__important_info", {"person": person, "kind": "allergy",
                                                                 "detail": "Invented bee sting allergy"})
        start = self.last_seq()
        self.records.update("people__important_info", medical, {"kind": "access"})
        entry = self.log(start)[-1]
        self.assertEqual(entry["patch"], {"kind": "access"})  # no clear of the copied value is sent
        self.assertEqual(entry["withheld"], [])
        self.assertEqual(self.records.get("people__important_info", medical)["detail"], "Invented bee sting allergy")
        self.records.update("people__important_info", medical, {"kind": "allergy"})  # back again: held, not sent
        snap = {r["id"]: r for r in sync.snapshot(self.conn, self.registry)["records"]}
        self.assertEqual(snap[self.gid("people__important_info", medical)]["withheld"], ["detail"])


class TravelDeclarationTests(TempDirTestCase):
    """The per-column travel rule in tables.toml, checked when a module loads (decision 0100)."""

    TABLES = '''[tables.notes]
title = "Notes"
columns.name = { type = "text", required = true }
columns.kind = { type = "choice", required = true, choices = ["plain", "secret"] }
columns.body = { type = "text", sensitive = true%s }
'''

    def load(self, extra):
        return modules.load_module(self.make_module(tables=self.TABLES % extra, labels=None))

    def problems(self, extra):
        with self.assertRaises(modules.ModuleError) as caught:
            self.load(extra)
        return " | ".join(caught.exception.problems)

    def test_rules_load_and_mistakes_are_explained(self):
        body = self.load(', travels_when = { kind = ["plain"] }').tables["notes"].columns["body"]
        self.assertEqual((body.travels, body.travels_when, body.travels_reviewed), ("when", {"kind": ["plain"]}, True))
        self.assertEqual(self.load(', travels = "never"').tables["notes"].columns["body"].travels, "never")
        self.assertIn('travels must be "always" or "never"', self.problems(', travels = "sometimes"'))
        self.assertIn("either travels or travels_when", self.problems(', travels = "never", travels_when = { kind = ["plain"] }'))
        self.assertIn("travels_when must name", self.problems(', travels_when = { name = ["plain"] }'))
        self.assertIn("travels_when must name", self.problems(', travels_when = { kind = ["missing"] }'))
        self.assertIn("travels_when names one choice column", self.problems(', travels_when = { kind = [] }'))
        with self.assertRaises(modules.ModuleError):
            modules.load_module(self.make_module(tables=self.TABLES.replace("columns.name", "columns.global_id") % ""))

    def test_a_private_column_that_does_not_say_stays_here_and_fails_the_exchange_check(self):
        body = self.load("").tables["notes"].columns["body"]
        self.assertEqual((body.travels, body.travels_reviewed), ("never", False))
        make_migration.make(self.tmp / "modules" / "demo", "first_tables")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "modules")
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        registry = records.build_registry(report.loaded)
        store = records.Records(conn, registry)
        store.create("demo__notes", {"name": "Invented", "kind": "plain", "body": "SENTINEL-UNREVIEWED-12"})
        self.assertNotIn("SENTINEL-UNREVIEWED-12", json.dumps(sync.snapshot(conn, registry)) +
                         json.dumps(sync.changes(conn)))
        self.assertIn("demo__notes.body is private and does not say whether it travels.", sync.check(conn, registry))

    def test_shipped_modules_follow_decision_0089(self):
        found, failures = modules.discover(MODULES_DIR)
        self.assertEqual(failures, {})
        registry = records.build_registry(found)
        detail = registry["people__important_info"].table.columns["detail"]
        self.assertEqual((detail.travels, sorted(detail.travels_when["kind"])), ("when", sorted(MEDICAL)))
        for table in ("exits", "shutoffs", "equipment", "meters"):
            self.assertEqual(registry[f"home_layout__{table}"].table.retired["access_details"].travels, "never")
        self.assertEqual(registry["vehicles__vehicles"].table.columns["registration"].travels, "never")
        self.assertEqual(registry["pets__pets"].table.columns["microchip"].travels, "always")
        self.assertEqual(sync.unreviewed(registry), [])


class RestoreEpochTests(TempDirTestCase):
    """STAGE1.md check 10: restoring keeps IDs, an older copy gets new ones, and the epoch only goes up."""

    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        load_example.load("smith", self.data, MODULES_DIR, today=date(2026, 6, 1))
        self.report = startup.prepare(self.data, MODULES_DIR)
        backups.daily(self.data, today=date(2026, 6, 1))

    def ids(self):
        conn = db.connect(self.data / "dashboard.db")
        try:
            return ({r[0]: r[1] for r in conn.execute("SELECT id, global_id FROM people__people")},
                    sync.read_state(conn), sync.epochs(conn))
        finally:
            conn.close()

    def test_restore_and_undo_keep_ids_and_raise_the_epoch(self):
        before, state, _ = self.ids()
        conn = db.connect(self.data / "dashboard.db")
        records.Records(conn, records.build_registry(self.report.loaded)).create("people__people", {"name": "Visitor"})
        conn.close()
        copy = restore.get({"data": self.data / "backups"}, "data", "daily-2026-06-01.db")
        restore.restore(self.data, copy, self.report.loaded)
        after, restored, epochs = self.ids()
        self.assertEqual(after, before)
        self.assertEqual(restored["household_id"], state["household_id"])
        self.assertEqual(restored["epoch"], state["epoch"] + 1)
        self.assertEqual(epochs[-1]["reason"], "Restored a backup.")
        restore.undo(self.data, self.report.loaded)
        undone, again, epochs = self.ids()
        self.assertEqual(len(undone), len(before) + 1)
        self.assertEqual(again["epoch"], restored["epoch"] + 1)  # never goes back
        self.assertEqual(epochs[-1]["reason"], "Undid a restore.")

    def test_a_backup_from_before_permanent_ids_gets_new_ones_and_a_new_epoch(self):
        before, state, _ = self.ids()
        old = self.data / "backups" / "daily-2026-05-31.db"
        shutil.copyfile(self.data / "backups" / "daily-2026-06-01.db", old)
        make_old(old)
        copy = restore.get({"data": self.data / "backups"}, "data", old.name)
        restore.restore(self.data, copy, self.report.loaded)
        after, restored, epochs = self.ids()
        self.assertEqual(set(after), set(before))
        self.assertTrue(set(after.values()).isdisjoint(before.values()))  # never matched to the old IDs
        self.assertEqual(restored["epoch"], state["epoch"] + 1)
        self.assertEqual(restored["household_id"], state["household_id"])
        self.assertIn("from before permanent IDs", epochs[-1]["reason"])
        self.assertGreater(epochs[-1]["new_ids"], 0)
