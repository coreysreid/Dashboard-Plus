"""Tests for the first-run wizard and the settings page."""
from support import TempDirTestCase
from dashboard.core import backups, db, settings, startup
from dashboard.web.app import create_app
import make_migration

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
PORT = 5124
BASE = f"http://127.0.0.1:{PORT}"


class SetupTests(TempDirTestCase):
    def start(self, with_people=True):
        make_migration.make(self.make_module(tables='[tables.things]\ntitle = "Things"\ncolumns.name = { type = "text" }\n',
                                             labels=None), "first_tables")
        if with_people:
            make_migration.make(self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None),
                                "first_tables")
        self.data = self.tmp / "data"
        report = startup.prepare(self.data, self.tmp / "modules")
        self.app = create_app("t", lambda: None, report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def post(self, path, data):
        return self.client.post(path, data=dict(data, _csrf=self.app.config["CSRF_TOKEN"]), base_url=BASE)

    def setting(self, key, default=None):
        conn = db.connect(self.data / "dashboard.db")
        try:
            return settings.get(conn, key, default)
        finally:
            conn.close()

    def query(self, sql):
        conn = db.connect(self.data / "dashboard.db")
        try:
            return [tuple(r) for r in conn.execute(sql)]
        finally:
            conn.close()

    def test_new_household_is_taken_to_the_wizard(self):
        self.start()
        response = self.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/setup", response.headers["Location"])
        page = self.get("/setup").get_data(as_text=True)
        self.assertIn("Person 1", page)
        self.assertIn("not encrypted", page)

    def test_finishing_the_wizard_adds_people_and_saves_the_profile(self):
        self.start()
        response = self.post("/setup", {"name_1": "Person A", "name_2": "Person B", "pets": "1",
                                        "country": "New Zealand", "home_type": "house", "storeys": "2",
                                        "hazards": ["flood", "nonsense"], "modules": ["demo", "people"],
                                        "second_copy": "yes", "timezone": "Pacific/Auckland"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.query("SELECT name, lives_here, source FROM people__people ORDER BY id"),
                         [("Person A", 1, "person"), ("Person B", 1, "person")])
        self.assertEqual(self.setting("household.people"), 2)
        self.assertEqual(self.setting("household.storeys"), 2)
        self.assertEqual(self.setting("household.hazards"), ["flood"])
        self.assertEqual(self.setting("household.timezone"), "Pacific/Auckland")
        self.assertTrue(self.setting("setup.done"))
        self.assertEqual(self.get("/").status_code, 200)
        self.assertIn("2 people live here", self.get("/settings").get_data(as_text=True))

    def test_without_a_people_module_it_asks_for_a_number(self):
        self.start(with_people=False)
        page = self.get("/setup").get_data(as_text=True)
        self.assertIn("How many people live here?", page)
        response = self.post("/setup", {"people": "", "modules": ["demo"]})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Number of people is needed.", response.get_data(as_text=True))
        self.post("/setup", {"people": "3", "storeys": "1", "modules": ["demo"]})
        self.assertEqual(self.setting("household.people"), 3)

    def test_mistakes_are_explained_and_nothing_is_saved(self):
        self.start()
        response = self.post("/setup", {"name_1": "Person A", "storeys": "two", "pets": "-1", "home_type": "castle"})
        self.assertEqual(response.status_code, 422)
        page = response.get_data(as_text=True)
        self.assertIn("Number of storeys must be a whole number.", page)
        self.assertIn("Number of pets must be between 0 and 50.", page)
        self.assertIn('value="Person A"', page)
        self.assertEqual(self.query("SELECT COUNT(*) FROM people__people"), [(0,)])
        self.assertFalse(self.setting("setup.done", False))

    def test_switching_a_module_off_hides_it_but_keeps_records(self):
        self.start()
        self.post("/setup", {"name_1": "Person A", "modules": ["demo", "people"]})
        self.post("/t/demo__things/new", {"name": "Kept thing", "then": "done"})
        self.post("/settings", {"modules": ["people"], "second_copy": "yes"})
        self.assertNotIn("Things", self.get("/").get_data(as_text=True))
        self.assertEqual(self.get("/t/demo__things").status_code, 404)
        self.assertEqual(self.query("SELECT name FROM demo__things"), [("Kept thing",)])
        self.post("/settings", {"modules": ["people", "demo"], "second_copy": "yes"})
        self.assertIn("Kept thing", self.get("/t/demo__things").get_data(as_text=True))

    def test_settings_can_be_saved_before_anyone_is_added(self):
        self.start()
        self.post("/setup", {"people": "2", "modules": ["demo", "people"]})
        response = self.post("/settings", {"modules": ["demo"], "storeys": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.setting("household.storeys"), 1)

    def test_turning_off_the_second_backup_copy(self):
        self.start()
        self.post("/setup", {"name_1": "Person A", "modules": ["demo", "people"]})  # second_copy unticked
        extra = self.tmp / "computer-copy"
        made = backups.on_close(self.data, extra)
        self.assertEqual(len(made), 1)
        self.assertFalse(extra.exists())
