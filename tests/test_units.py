"""Tests for singular units: "1 tube", not "1 tubes", in batch names and item summaries."""
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, records, startup
from dashboard.core.naming import record_name
from dashboard.core.units import unit_for


class UnitWordTests(TempDirTestCase):
    def test_singular_only_when_the_amount_is_exactly_one(self):
        self.assertEqual(unit_for(1, "tubes"), "tube")
        self.assertEqual(unit_for("1.0", "Bottles"), "Bottle")
        self.assertEqual(unit_for(2, "tubes"), "tubes")
        self.assertEqual(unit_for(0, "tins"), "tins")
        self.assertEqual(unit_for(1.5, "boxes"), "boxes")

    def test_common_household_units(self):
        for plural, one in [("tubes", "tube"), ("bottles", "bottle"), ("tins", "tin"), ("packs", "pack"),
                            ("boxes", "box"), ("litres", "litre")]:
            self.assertEqual(unit_for(1, plural), one)

    def test_unknown_units_are_left_as_typed(self):
        for unit in ["kg", "L", "sheets of paper", "mystery", ""]:
            self.assertEqual(unit_for(1, unit), unit)
        self.assertEqual(unit_for(None, "tins"), "tins")
        self.assertEqual(unit_for("lots", "tins"), "tins")


class BatchNameTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)

    def name_of_batch(self, unit, amount):
        item = self.records.create("stock__items", {"name": "Bike inner tube", "unit": unit, "quantity": amount})
        lot = self.conn.execute("SELECT * FROM stock__lots WHERE item = ?", (item,)).fetchone()
        return record_name(self.conn, self.registry, self.registry["stock__lots"], lot)

    def test_batch_name_uses_the_singular_for_one(self):
        self.assertEqual(self.name_of_batch("tubes", 1), "Bike inner tube, 1 tube")
        self.assertEqual(self.name_of_batch("tubes", 3), "Bike inner tube, 3 tubes")
        self.assertEqual(self.name_of_batch("kg", 1), "Bike inner tube, 1 kg")
