"""Tests for the data-safety fixes from the November 2026 review: restore, stock counts, decimals and backups."""
import shutil
from datetime import date
from unittest import mock

from support import ROOT, TempDirTestCase
from dashboard.core import backups, db, records, settings, startup


class RecordSafetyTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("people", "pets", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.records = records.Records(self.conn, records.build_registry(report.loaded))

    def amount(self, item):
        return self.conn.execute("SELECT quantity FROM stock__items WHERE id = ?", (item,)).fetchone()[0]

    def test_restoring_a_person_brings_back_what_was_deleted_and_cleared_with_them(self):
        person = self.records.create("people__people", {"name": "Neighbour B", "phone": "555 0199"})
        role = self.records.create("people__roles", {"person": person, "role": "emergency_contact"})
        pet = self.records.create("pets__pets", {"name": "Rex", "species": "dog", "vet": person})
        self.records.delete("people__people", person)
        self.assertIsNone(self.records.get("pets__pets", pet)["vet"])
        self.records.restore("people__people", person)
        self.assertIsNone(self.records.get("people__roles", role)["deleted_at"])
        self.assertEqual(self.records.get("pets__pets", pet)["vet"], person)

    def test_restoring_a_stock_item_does_not_count_its_entries_twice(self):
        item = self.records.create("stock__items", {"name": "Beans", "quantity": 0})
        move = self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 10})
        self.records.delete("stock__items", item)
        self.records.restore("stock__items", item)
        self.records.restore("stock__movements", move)  # already back with the item: nothing changes
        self.assertEqual(self.amount(item), 10)
        self.records.delete("stock__movements", move)
        self.assertEqual(self.amount(item), 0)
        self.records.restore("stock__movements", move)  # deleted on its own: its effect comes back
        self.assertEqual(self.amount(item), 10)

    def test_decimal_amounts_add_up_exactly(self):
        item = self.records.create("stock__items", {"name": "Oil", "quantity": "0.3"})
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": "0.1"})
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": "0.2"})
        self.assertEqual(self.amount(item), 0)

    def test_a_bought_entry_can_be_corrected_after_some_was_used(self):
        item = self.records.create("stock__items", {"name": "Rice", "quantity": 0})
        bought = self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 10})
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 8})
        self.records.update("stock__movements", bought, {"amount": 12})
        self.assertEqual(self.amount(item), 4)

    def test_absurdly_large_numbers_are_refused(self):
        with self.assertRaises(records.ValidationError):
            self.records.create("stock__items", {"name": "Water", "quantity": "1e999"})

    def test_moving_a_branch_cannot_make_places_too_deep(self):
        top = None
        for level in range(6):
            top = self.records.create("stock__places", {"name": f"A{level}", "inside": top})
        branch = None
        first = None
        for level in range(4):
            branch = self.records.create("stock__places", {"name": f"B{level}", "inside": branch})
            first = first or branch
        with self.assertRaises(records.ValidationError):
            self.records.update("stock__places", first, {"inside": top})

    def test_a_record_cannot_be_restored_while_what_it_links_to_is_deleted(self):
        kitchen = self.records.create("stock__places", {"name": "Kitchen"})
        pantry = self.records.create("stock__places", {"name": "Pantry", "inside": kitchen})
        self.records.delete("stock__places", pantry)
        self.records.delete("stock__places", kitchen)
        with self.assertRaises(records.ValidationError) as caught:
            self.records.restore("stock__places", pantry)
        self.assertIn("restore", caught.exception.problems)


class BackupSafetyTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.extra = self.tmp / "computer-copy"

    def folder(self, name):
        data = self.tmp / name
        startup.prepare(data, self.tmp / "modules")
        return data

    def test_two_data_folders_keep_separate_second_copies(self):
        first, second = self.folder("first"), self.folder("second")
        backups.daily(first, self.extra, today=date(2026, 6, 1))
        backups.daily(second, self.extra, today=date(2026, 6, 1))
        copies = sorted(p.relative_to(self.extra).parts[0] for p in self.extra.glob("*/daily-2026-06-01.db"))
        self.assertEqual(len(set(copies)), 2)

    def test_a_backup_that_fails_its_check_leaves_nothing_behind_and_is_tried_again(self):
        data = self.folder("data")
        with mock.patch.object(db, "integrity_ok", return_value=False):
            with self.assertRaises(db.DatabaseError):
                backups.daily(data, today=date(2026, 6, 1))
        self.assertEqual(list((data / "backups").glob("daily-*")), [])
        self.assertEqual(len(backups.daily(data, today=date(2026, 6, 1))), 1)

    def test_a_failed_second_copy_is_tried_again_the_same_day(self):
        data = self.folder("data")
        blocker = self.tmp / "not-a-folder"
        blocker.write_text("x", encoding="utf-8")
        backups.daily(data, blocker, today=date(2026, 6, 1))
        self.assertEqual(backups.status(data)["second"]["state"], "failed")
        made = backups.daily(data, self.extra, today=date(2026, 6, 1))
        self.assertEqual(len(made), 2)
        self.assertEqual(backups.status(data)["second"]["state"], "ok")
