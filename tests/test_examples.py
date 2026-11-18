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
                "expiring": [i.name.partition(", ")[0] for i in watch.expiring(conn, registry, TODAY)],  # the item, not the batch detail
                "gaps": len(watch.gaps(conn, registry)), "conn": conn, "registry": registry}

    def test_smith_family(self):
        result = self.summary("smith")
        self.assertEqual((result["days"], result["need"]), (2.5, 14))  # 4 people x 3 L + 2 pets x 1 L
        self.assertEqual(result["low"], ["AA batteries", "Baked beans", "Dog food (Rex)", "Reliever puffer (Jack)",
                                         "Tinned tomatoes"])
        self.assertEqual(result["expiring"], ["Muesli bars", "Monthly flea and tick chew", "Long-life milk",
                                              "Upstairs hall smoke alarm", "Family car: Routine service", "Sunscreen SPF 50", "Rex", "Adrenaline auto-injector (Emily)",
                                              "Home insurance policy", "Kidney beans"])  # the 3 tins on Shelf 3, not the 10 in the garage
                                              "Upstairs hall smoke alarm", "Family car: Routine service", "Clean the gutters", "Sunscreen SPF 50", "Rex", "Adrenaline auto-injector (Emily)",
                                              "Kidney beans"])  # the 3 tins on Shelf 3, not the 10 in the garage
        beans = result["conn"].execute("SELECT quantity FROM stock__items WHERE name = 'Kidney beans'").fetchone()
        self.assertEqual(beans[0], 13)
        self.assertEqual(result["gaps"], 2)  # their only first aid kit is in the car; Home layout is filled in
        details = {i.name: i.detail for i in watch.expiring(result["conn"], result["registry"], TODAY)}
        self.assertTrue(details["Upstairs hall smoke alarm"].startswith("check due"), details)
        self.assertTrue(details["Family car: Routine service"].startswith("service or check due"), details)
        self.assertTrue(details["Home insurance policy"].startswith("review or renewal due"), details)
        self.assertTrue(details["Clean the gutters"].startswith("job due"), details)  # Home care, their own date
        self.assertNotIn("Hot water system service", details)  # due in 65 days: not yet worth a reminder
        gaps = [g.message for g in watch.gaps(result["conn"], result["registry"])]
        self.assertIn("No first aid kit is recorded at home. Add one, or check where your kits are kept.", gaps)

    def test_garcia_household(self):
        result = self.summary("garcia")
        self.assertEqual((result["days"], result["need"]), (1.9, 13))
        self.assertIn("Metformin 500 mg (Rosa)", result["low"])
        self.assertEqual(result["expiring"], ["Hand sanitizer", "Luna", "Kidney support tablets", "Tortillas",
                                              "Blood glucose test strips", "Apartment first aid kit",
                                              "Household car: Auto insurance", "Earthquake go-bags"])
        self.assertEqual(result["gaps"], 1)
        self.assertTrue(settings.get(result["conn"], "household.mobility_needs"))

    def test_sam_taylor(self):
        result = self.summary("taylor")
        self.assertEqual((result["days"], result["need"]), (4.0, 3))
        self.assertEqual(result["low"], ["AA batteries", "Tinned soup"])
        self.assertEqual(result["gaps"], 8)  # Home layout asks about the rest; nobody to call for the car; one paper's place
        self.assertEqual(result["gaps"], 8)  # Home layout asks about the rest; nobody to call for the car yet;
        # and where the radiators are bled
        self.assertEqual(result["expiring"], ["Oat milk", "Small car: MOT test"])
        gaps = [g.message for g in watch.gaps(result["conn"], result["registry"])]
        for question in ("Where is the water shut-off? It is not written down yet.",
                         "Where is the power board (switchboard or fuse box)? It is not written down yet.",
                         "Where are your smoke alarms? None is written down yet."):
            self.assertIn(question, gaps)
        self.assertIn("When do you plan to check Small first aid kit again?", gaps)
        self.assertIn("Where is Bleed the radiators done? Choose one of your places.", gaps)
        self.assertIn("Who would you call if Small car broke down? It can be a roadside service, a garage or "
                      "someone you know.", gaps)
        self.assertIn("Where is Bicycle warranty kept? Choosing one of your places is enough.", gaps)

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
            uses = load_example.read(household)["setup"]["modules"]
            for name, title, _, action in make_screenshots.STAGES:
                if title and (not action.get("module") or action["module"] in uses):
                    self.assertIn(f"screenshots/{household}/{name}.png", gallery)
                    self.assertTrue((ROOT / "docs" / "screenshots" / household / f"{name}.png").exists(),
                                    f"{household}/{name}.png is missing; run tools/make_screenshots.py")


class NamelessHistoryTableTests(TempDirTestCase):
    """A history table with no short text column (like Medical's kit checks) still loads (Lane B, medical NOTES)."""

    TABLES = '''[tables.kits]
title = "Kits"
columns.name = { type = "text", required = true }

[tables.checks]
title = "Checks"
columns.kit = { type = "link", to = "kits", on_delete = "cascade" }
columns.checked_on = { type = "date", required = true }
'''

    def setUp(self):
        super().setUp()
        import make_migration
        from dashboard.core import startup
        make_migration.make(self.make_module(tables=self.TABLES, labels=None), "first_tables")
        startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        found, _ = modules.discover(self.tmp / "modules")
        self.registry = records.build_registry(found)

    def test_rows_load_and_link_by_the_kit_name(self):
        data = {"demo": {"kits": [{"name": "Car kit"}], "checks": [{"kit": "Car kit", "checked_on": "today-3"}]}}
        self.assertEqual(load_example.load_records(self.conn, self.registry, data, today=TODAY), 2)
        row = self.conn.execute("SELECT checked_on FROM demo__checks").fetchone()
        self.assertEqual(row["checked_on"], "2026-05-29")

    def test_linking_to_a_nameless_table_says_why_it_cannot(self):
        with self.assertRaises(load_example.ExampleError) as caught:
            load_example._find(self.conn, self.registry["demo__checks"], "anything")
        self.assertIn("no name column", str(caught.exception))
