"""Tests for running low, expiring soon and days of cover, and for checking `watch` sections."""
from datetime import date

from support import TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
import make_migration

TABLES = '''[tables.items]
title = "Items"
columns.name = { type = "text", required = true }
columns.category = { type = "choice", choices = ["food", "water"] }
columns.quantity = { type = "measure", unit = "litres", min = 0 }
columns.minimum = { type = "measure", min = 0 }
columns.expires = { type = "date" }

[tables.items.watch]
running_low = { quantity = "quantity", minimum = "minimum" }
expiring = { date = "expires", warn_days = 30 }
supply = { quantity = "quantity", per_person_per_day = 3, per_pet_per_day = 1, target_days = 3, unit = "litres", where = { category = "water" } }
'''
PEOPLE_MODULE = '''name = "people"
title = "People"
version = "1.0.0"
description = "Synthetic people module for tests."
core_api = "1"
kind = "declarative"
'''
PEOPLE_TABLES = '''[tables.people]
title = "People"
columns.name = { type = "text", required = true }
columns.lives_here = { type = "boolean" }
'''


class WatchRulesTests(TempDirTestCase):
    def problems(self, watch_text):
        folder = self.make_module(tables=TABLES.split("[tables.items.watch]")[0] + "[tables.items.watch]\n" + watch_text,
                                  labels=None)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " | ".join(caught.exception.problems)

    def test_valid_watch_section_loads(self):
        module = modules.load_module(self.make_module(tables=TABLES, labels=None))
        rules = module.tables["items"].watch
        self.assertEqual(rules["expiring"], {"date": "expires", "warn_days": 30})
        self.assertEqual(rules["supply"]["where"], {"category": "water"})
        self.assertEqual(rules["supply"]["per_pet_per_day"], 1)

    def test_mistakes_are_explained(self):
        self.assertIn("Did you mean 'quantity'", self.problems('running_low = { quantity = "quantty", minimum = "minimum" }\n'))
        self.assertIn("must be a date column", self.problems('expiring = { date = "name" }\n'))
        self.assertIn("warn_days", self.problems('expiring = { date = "expires", warn_days = 0 }\n'))
        self.assertIn("target_days", self.problems('supply = { quantity = "quantity", per_person_per_day = 3, target_days = 0 }\n'))
        self.assertIn("not one of the choices", self.problems(
            'supply = { quantity = "quantity", per_person_per_day = 3, target_days = 3, where = { category = "juice" } }\n'))
        self.assertIn("Did you mean 'running_low'", self.problems('runing_low = { quantity = "quantity", minimum = "minimum" }\n'))


class WatchResultsTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        make_migration.make(self.make_module(tables=TABLES, labels=None), "first_tables")
        self.conn = None

    def open(self, with_people=False):
        if with_people:
            make_migration.make(self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None),
                                "first_tables")
        startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual(failures, {})
        self.registry = records.build_registry(found)
        self.records = records.Records(self.conn, self.registry)

    def add(self, **values):
        return self.records.create("demo__items", values)

    def test_running_low_lists_shortest_first_and_ignores_deleted(self):
        self.open()
        self.add(name="Rice", quantity=1, minimum=2)
        self.add(name="Beans", quantity=0, minimum=4)
        self.add(name="Salt", quantity=5, minimum=1)
        gone = self.add(name="Flour", quantity=0, minimum=9)
        self.records.delete("demo__items", gone)
        items = watch.running_low(self.conn, self.registry)
        self.assertEqual([i.name for i in items], ["Beans", "Rice"])
        self.assertIn("0 left, keep at least 4 litres", items[0].detail)

    def test_expiring_includes_expired_and_window_only(self):
        self.open()
        today = date(2026, 6, 1)
        self.add(name="Old milk", expires="2026-05-30")
        self.add(name="Bread", expires="2026-06-01")
        self.add(name="Cheese", expires="2026-06-20")
        self.add(name="Tins", expires="2027-06-01")
        items = watch.expiring(self.conn, self.registry, today)
        self.assertEqual([i.name for i in items], ["Old milk", "Bread", "Cheese"])
        self.assertEqual(items[0].detail, "expired 2026-05-30 (2 days ago)")
        self.assertEqual(items[1].detail, "expires today")
        self.assertIn("in 19 days", items[2].detail)

    def test_days_of_cover_needs_a_household_size(self):
        self.open()
        self.add(name="Water", category="water", quantity=20)
        result = watch.supplies(self.conn, self.registry)[0]
        self.assertTrue(result.needs_household)
        self.assertIsNone(result.days)

    def test_days_of_cover_from_settings_with_working_shown(self):
        self.open()
        settings.put(self.conn, "household.people", 3)
        settings.put(self.conn, "household.pets", 1)
        self.add(name="Water 10 L", category="water", quantity=10)
        self.add(name="Water 10 L", category="water", quantity=10)
        self.add(name="Rice", category="food", quantity=50)
        result = watch.supplies(self.conn, self.registry)[0]
        self.assertEqual(result.total, 20)
        self.assertEqual(result.daily_need, 10)
        self.assertAlmostEqual(result.days, 2)
        self.assertEqual(result.shortfall, 10)
        self.assertIn("20 litres on hand ÷ 10 litres a day for 3 people and 1 pet = about 2 days", result.working)
        self.assertIn("local authority", result.notes[0])

    def test_people_marked_as_living_here_set_the_household(self):
        self.open(with_people=True)
        settings.put(self.conn, "household.people", 9)
        for name, here in (("Person A", True), ("Person B", True), ("Visitor", False)):
            self.records.create("people__people", {"name": name, "lives_here": here})
        home = watch.household(self.conn, self.registry)
        self.assertEqual((home.people, home.source), (2, "people marked as living here"))
