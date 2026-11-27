"""Sync stage 1 extra checks from STAGE1_ACCEPTANCE.md: Utilities and Pets values, held People details, corrupt IDs and links, confinement, Set up my home rows."""
import sqlite3

from support import TempDirTestCase
from dashboard.core import db, startup, sync
from test_sync_stage1 import MODULES_DIR, SyncTestCase, fingerprints, make_old


class ExtraCheckTests(SyncTestCase):
    """S1-04, S1-08, S1-11 and S1-12: the highest-value cases the first tests left open (decision 0106)."""

    def snap(self):
        return {r["id"]: r for r in sync.snapshot(self.conn, self.registry)["records"]}

    def test_utilities_private_fields_stay_here_and_the_pets_microchip_travels(self):  # S1-12
        sentinels = {"account": "••••5227", "notes": "SENTINEL-UTILITY-NOTES-9e10"}
        service = self.records.create("utilities__services", {
            "name": "Invented water", "kind": "water", "account_last4": sentinels["account"],
            "notes": sentinels["notes"]})
        pet = self.records.create("pets__pets", {"name": "Invented dog", "species": "dog",
                                                 "microchip": "INVENTED-CHIP-0042"})
        self.records.update("utilities__services", service, {"name": "Invented water, renamed"})
        self.records.delete("utilities__services", service)
        self.records.restore("utilities__services", service)
        text = self.snapshot_text() + self.log_text()
        for label, value in sentinels.items():
            self.assertNotIn(value, text, label)
            for derived in fingerprints(value):
                self.assertNotIn(derived, text, label)
        row = self.snap()[self.gid("utilities__services", service)]
        self.assertEqual(row["withheld"], ["account_last4", "notes"])
        self.assertNotIn("account_last4", row["values"])
        entries = [e for e in self.log() if e["table_name"] == "utilities__services"]
        self.assertEqual([e["action"] for e in entries], ["create", "update", "delete", "restore"])
        self.assertEqual(entries[0]["withheld"], ["account_last4", "notes"])
        for entry in entries:
            self.assertTrue(set(entry["patch"]) <= {"name", "kind", "provider", "fault_contact", "meter"}, entry["patch"])
        local = self.records.get("utilities__services", service)  # still kept here, and in the local history
        self.assertEqual((local["account_last4"], local["notes"]), (sentinels["account"], sentinels["notes"]))
        self.assertTrue(any(sentinels["account"][-4:] in (r[7] or "") for r in self.conn.execute("SELECT * FROM core__audit")))
        pet_row = self.snap()[self.gid("pets__pets", pet)]
        self.assertEqual(pet_row["values"]["microchip"], "INVENTED-CHIP-0042")
        self.assertEqual(pet_row["withheld"], [])
        self.assertIn("INVENTED-CHIP-0042", self.log_text())
        self.assertEqual(sync.check(self.conn, self.registry), [])

    def held(self):
        return sorted(tuple(r) for r in self.conn.execute(
            "SELECT table_name, global_id, column_name FROM core__sync_held"))

    def test_a_held_people_detail_is_listed_and_cleared_only_by_typing_it_again(self):  # S1-11
        person = self.records.create("people__people", {"name": "Invented Person"})
        access = self.records.create("people__important_info", {"person": person, "kind": "access",
                                                                "detail": "SENTINEL-ASK-THE-NEIGHBOUR"})
        key = self.gid("people__important_info", access)
        self.assertEqual(self.held(), [])
        self.records.update("people__important_info", access, {"kind": "medication"})
        self.assertEqual(self.held(), [("people__important_info", key, "detail")])
        self.records.update("people__people", person, {"notes": "An ordinary edit"})
        self.assertEqual(self.held(), [("people__important_info", key, "detail")])  # an unrelated edit frees nothing
        start = self.last_seq()
        self.records.update("people__important_info", access, {"detail": "Invented evening tablet"})
        self.assertEqual(self.held(), [])
        self.assertEqual(self.log(start)[-1]["patch"], {"detail": "Invented evening tablet"})
        self.assertNotIn("SENTINEL-ASK-THE-NEIGHBOUR", self.snapshot_text() + self.log_text())
        self.assertEqual(self.records.get("people__important_info", access)["detail"], "Invented evening tablet")
        allergy = self.records.create("people__important_info", {"person": person, "kind": "allergy",
                                                                 "detail": "Invented nut allergy"})
        akey = self.gid("people__important_info", allergy)
        self.records.update("people__important_info", allergy, {"kind": "access"})
        self.records.update("people__important_info", allergy, {"kind": "allergy"})
        self.assertEqual(self.held(), [("people__important_info", akey, "detail")])
        self.assertEqual(self.snap()[akey]["withheld"], ["detail"])
        self.records.update("people__important_info", allergy, {"detail": "Invented nut allergy"})  # same words: no change
        self.assertEqual(self.held(), [("people__important_info", akey, "detail")])  # the safe side: still held
        self.records.update("people__important_info", allergy, {"detail": "Invented nut and egg allergy"})
        self.assertEqual(self.held(), [])
        self.assertEqual(self.snap()[akey]["values"]["detail"], "Invented nut and egg allergy")

    def break_then_repair(self, why, expected, repair):
        self.assertIn(expected, sync.check(self.conn, self.registry), why)
        repair()
        self.assertEqual(sync.check(self.conn, self.registry), [], why)

    def test_check_names_a_missing_or_repeated_id_and_a_link_to_nothing(self):  # S1-04
        first = self.records.create("wine__wines", {"name": "Invented red"})
        second = self.records.create("wine__wines", {"name": "Invented white"})
        shelf = self.records.create("stock__places", {"name": "Shelf"})
        item = self.records.create("stock__items", {"name": "Invented rice", "place": shelf})
        self.assertEqual(sync.check(self.conn, self.registry), [])
        keep, spare = self.gid("wine__wines", first), self.gid("wine__wines", second)
        self.conn.execute("UPDATE wine__wines SET global_id = NULL WHERE id = ?", (first,))
        self.break_then_repair("missing", "wine__wines has records without a permanent ID.",
                               lambda: self.conn.execute("UPDATE wine__wines SET global_id = ? WHERE id = ?", (keep, first)))
        self.conn.execute("DROP INDEX wine__wines__global_id__idx")  # the unique index would refuse a repeat
        self.conn.execute("UPDATE wine__wines SET global_id = ? WHERE id = ?", (keep, second))
        self.break_then_repair("repeated", "wine__wines has two records with the same permanent ID.",
                               lambda: self.conn.execute("UPDATE wine__wines SET global_id = ? WHERE id = ?", (spare, second)))
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute("UPDATE stock__items SET place = 99999 WHERE id = ?", (item,))
        self.break_then_repair("dangling", "stock__items.place points at a record that is not there.",
                               lambda: self.conn.execute("UPDATE stock__items SET place = ? WHERE id = ?", (shelf, item)))

    def test_check_names_a_relation_pair_that_points_at_nothing(self):  # S1-04, relation endpoint
        blue = self.records.create("documents__copy_places", {"name": "Blue USB drive"})
        doc = self.records.create("documents__documents", {
            "name": "Invented lease", "kind": self.first_choice("documents__documents", "kind"), "copies": [blue]})
        self.assertEqual(sync.check(self.conn, self.registry), [])
        join = "documents__documents__copies"
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute(f"UPDATE {join} SET to_id = 99999 WHERE from_id = ?", (doc,))
        self.break_then_repair("pair", f"{join} has a pair that points at a record that is not there.",
                               lambda: self.conn.execute(f"UPDATE {join} SET to_id = ? WHERE from_id = ?", (blue, doc)))

    def test_set_up_my_home_connections_are_logged_with_places_as_permanent_ids(self):  # decision 0103
        hall = self.records.create("stock__places", {"name": "Hallway"})
        kitchen = self.records.create("stock__places", {"name": "Kitchen"})
        start = self.last_seq()
        link = self.records.create("stock__connections", {"place": hall, "connects_to": kitchen, "kind": "door"})
        outside = self.records.create("stock__connections", {"place": hall, "kind": "outside_door"})
        entries = [e for e in self.log(start) if e["table_name"] == "stock__connections"]
        self.assertEqual([e["action"] for e in entries], ["create", "create"])
        self.assertEqual(entries[0]["global_id"], self.gid("stock__connections", link))
        self.assertEqual(entries[0]["patch"]["place"], self.gid("stock__places", hall))
        self.assertEqual(entries[0]["patch"]["connects_to"], self.gid("stock__places", kitchen))
        self.assertEqual(entries[0]["patch"]["kind"], "door")
        self.assertIsNone(entries[1]["patch"]["connects_to"])
        self.assertEqual(entries[1]["global_id"], self.gid("stock__connections", outside))
        self.records.delete("stock__connections", link)
        self.assertEqual(self.log(start)[-1]["action"], "delete")
        row = self.snap()[self.gid("stock__connections", link)]
        self.assertTrue(row["deleted"])
        self.assertEqual(row["values"]["place"], self.gid("stock__places", hall))
        self.assertEqual(sync.check(self.conn, self.registry), [])


class ConfinementTests(TempDirTestCase):
    """S1-03: the core's ID step runs under the module's own confinement rule (decisions 0055 and 0100)."""

    def test_an_id_step_that_reaches_another_modules_table_is_refused_and_rolled_back(self):
        data = self.tmp / "data"
        startup.prepare(data, MODULES_DIR)
        make_old(data / "dashboard.db")
        stamp = "2026-06-01T00:00:00+00:00"
        conn = sqlite3.connect(data / "dashboard.db")
        conn.execute("INSERT INTO stock__places (created_at, updated_at, name) VALUES (?, ?, 'Untouched shelf')", (stamp, stamp))
        conn.execute("INSERT INTO wine__wines (created_at, updated_at, name) VALUES (?, ?, 'Invented red')", (stamp, stamp))
        conn.execute("CREATE TRIGGER wine_reaches_out AFTER UPDATE ON wine__wines BEGIN "
                     "UPDATE stock__places SET name = 'TAMPERED'; END")
        conn.commit()
        conn.close()
        report = startup.prepare(data, MODULES_DIR)
        self.assertTrue(any("permanent IDs" in p for p in report.module_problems.get("wine", [])), report.module_problems)
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("SELECT name FROM stock__places").fetchone()[0], "Untouched shelf")
        self.assertFalse(sync.has_identity(conn, "wine__wines"))  # rolled back whole: no column, no IDs
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM core__sync_changes").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM core__sync_held").fetchone()[0], 0)
