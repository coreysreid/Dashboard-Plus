"""Tests for the example households: each loads cleanly and shows exactly what it was written to show."""
from datetime import date

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, watch
import load_example

TODAY = date(2026, 6, 1)


class ExampleHouseholdTests(TempDirTestCase):
    def open(self, household):
        added = load_example.load(household, self.tmp / household, today=TODAY)
        conn = db.connect(self.tmp / household / "dashboard.db")
        self.addCleanup(conn.close)
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        return added, conn, records.build_registry(found)

    def summary(self, household):
        added, conn, registry = self.open(household)
        supply = watch.supplies(conn, registry)[0]
        return {"added": added, "days": round(supply.days, 1), "need": supply.daily_need,
                "low": sorted(i.name for i in watch.running_low(conn, registry)),
                "expiring": [i.name for i in watch.expiring(conn, registry, TODAY)],
                "gaps": len(watch.gaps(conn, registry)), "conn": conn, "registry": registry}

    def test_smith_family(self):
        result = self.summary("smith")
        self.assertEqual((result["days"], result["need"]), (2.5, 14))  # 4 people x 3 L + 2 pets x 1 L
        self.assertEqual(result["low"], ["AA batteries", "Baked beans", "Dog food (Rex)", "Reliever puffer (Jack)",
                                         "Tinned tomatoes"])
        self.assertEqual(result["expiring"], ["Muesli bars", "Long-life milk", "Sunscreen SPF 50",
                                              "Adrenaline auto-injector (Emily)"])
        self.assertEqual(result["gaps"], 1)

    def test_garcia_household(self):
        result = self.summary("garcia")
        self.assertEqual((result["days"], result["need"]), (1.9, 13))
        self.assertIn("Metformin 500 mg (Rosa)", result["low"])
        self.assertEqual(result["expiring"], ["Hand sanitizer", "Tortillas", "Blood glucose test strips"])
        self.assertEqual(result["gaps"], 1)
        self.assertTrue(settings.get(result["conn"], "household.mobility_needs"))

    def test_sam_taylor(self):
        result = self.summary("taylor")
        self.assertEqual((result["days"], result["need"]), (4.0, 3))
        self.assertEqual(result["low"], ["AA batteries", "Tinned soup"])
        self.assertEqual(result["gaps"], 2)

    def test_amounts_end_where_the_file_says_after_stock_in_and_out(self):
        _, conn, _ = self.open("garcia")
        row = conn.execute("SELECT quantity FROM stock__items WHERE name = 'Metformin 500 mg (Rosa)'").fetchone()
        self.assertEqual(row["quantity"], 20)
        moves = conn.execute("SELECT COUNT(*) FROM stock__movements WHERE deleted_at IS NULL").fetchone()[0]
        self.assertEqual(moves, 6)

    def test_people_from_setup_are_filled_in_not_duplicated(self):
        _, conn, _ = self.open("smith")
        rows = conn.execute("SELECT phone, lives_here FROM people__people WHERE name = 'John Smith'").fetchall()
        self.assertEqual([(r["phone"], r["lives_here"]) for r in rows], [("0491 570 156", 1)])

    def test_never_loads_into_a_folder_that_already_has_data(self):
        self.open("taylor")
        with self.assertRaises(load_example.ExampleError) as caught:
            load_example.load("taylor", self.tmp / "taylor")
        self.assertIn("never mixed", str(caught.exception))

    def test_unknown_household_lists_the_real_ones(self):
        with self.assertRaises(load_example.ExampleError) as caught:
            load_example.read("jones")
        self.assertIn("garcia, smith, taylor", str(caught.exception))

    def test_every_screenshot_stage_is_in_the_gallery(self):
        import make_screenshots
        gallery = (ROOT / "docs" / "EXAMPLES.md").read_text(encoding="utf-8")
        for household in make_screenshots.HOUSEHOLDS:
            for name, title, _, _ in make_screenshots.STAGES:
                if title:
                    self.assertIn(f"screenshots/{household}/{name}.png", gallery)
                    self.assertTrue((ROOT / "docs" / "screenshots" / household / f"{name}.png").exists(),
                                    f"{household}/{name}.png is missing; run tools/make_screenshots.py")
