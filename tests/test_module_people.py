"""Tests for the People module: its files load, meet the wizard contract, and print the emergency sheets."""
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5126
BASE = f"http://127.0.0.1:{PORT}"


class PeopleModuleTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "people", self.tmp / "modules" / "people")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertEqual(self.report.modules, ["people"])

    def test_meets_the_contract_the_wizard_relies_on(self):
        people = self.registry["people__people"].table.columns
        self.assertTrue(people["name"].required)
        self.assertEqual(people["lives_here"].type, "boolean")
        self.assertEqual(people["relationship"].type, "choice")
        roles = self.registry["people__roles"].table.columns
        self.assertEqual((roles["person"].type, roles["person"].on_delete), ("link", "cascade"))
        self.assertTrue({"emergency_contact", "neighbour", "doctor", "vet"} <= {c.key for c in roles["role"].choices})
        self.assertEqual(roles["priority"].type, "integer")
        self.assertTrue(self.registry["people__important_info"].table.columns["detail"].sensitive)

    def test_people_living_here_set_the_household_size(self):
        for name, here in (("Person A", True), ("Person B", True), ("Visitor C", False)):
            self.records.create("people__people", {"name": name, "lives_here": here})
        self.assertEqual(watch.household(self.conn, self.registry).people, 2)

    def test_deleting_a_person_removes_their_roles_and_details(self):
        person = self.records.create("people__people", {"name": "Person A"})
        role = self.records.create("people__roles", {"person": person, "role": "neighbour", "priority": 1})
        info = self.records.create("people__important_info", {"person": person, "kind": "allergy",
                                                              "detail": "Synthetic allergy"})
        self.records.delete("people__people", person)
        self.assertEqual(self.records.count("people__roles"), 0)
        self.assertEqual(self.records.count("people__important_info"), 0)
        self.records.restore("people__roles", role)
        self.records.restore("people__important_info", info)

    def test_both_emergency_sheets_print(self):
        settings.put(self.conn, "setup.done", True)
        home = self.records.create("people__people", {"name": "Person A", "lives_here": True, "phone": "555 0101"})
        neighbour = self.records.create("people__people", {"name": "Neighbour B", "phone": "555 0199"})
        self.records.create("people__roles", {"person": neighbour, "role": "key_holder", "priority": 1})
        self.records.create("people__important_info", {"person": home, "kind": "allergy",
                                                       "detail": "Synthetic allergy note"})
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        plain = client.get("/sheet/people/emergency", base_url=BASE).get_data(as_text=True)
        self.assertIn("Person A", plain)
        self.assertIn("Key holder", plain)
        self.assertIn("555 0199", plain)
        self.assertNotIn("Synthetic allergy note", plain)
        medical = client.get("/sheet/people/emergency_medical", base_url=BASE).get_data(as_text=True)
        self.assertIn("Synthetic allergy note", medical)
        self.assertIn("includes private details", medical)

    def test_gaps_are_asked_until_filled_in(self):
        messages = lambda: [g.message for g in watch.gaps(self.conn, self.registry)]
        self.assertEqual(len(messages()), 3)
        self.assertTrue(messages()[0].startswith("Who lives here?"))
        home = self.records.create("people__people", {"name": "Person A", "lives_here": True, "phone": "555 0101"})
        neighbour = self.records.create("people__people", {"name": "Neighbour B"})
        self.records.create("people__roles", {"person": neighbour, "role": "emergency_contact", "priority": 1})
        self.records.create("people__roles", {"person": home, "role": "doctor"})
        self.assertEqual(messages(), ["What is Neighbour B's phone number? They are in Who to call "
                                      "(Emergency contact), but no number is saved."])
        self.records.update("people__people", neighbour, {"phone": "555 0199"})
        self.assertEqual(messages(), [])

    def test_needs_attention_page_lists_gaps_with_a_link_to_fill_them_in(self):
        settings.put(self.conn, "setup.done", True)
        self.records.create("people__people", {"name": "Person A", "lives_here": True})
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        page = client.get("/attention", base_url=BASE).get_data(as_text=True)
        self.assertIn("Worth filling in", page)
        self.assertIn("Nobody is listed as an emergency contact yet.", page)
        self.assertIn('href="/t/people__roles/new?role=emergency_contact"', page)
        self.assertNotIn("Who lives here?", page)
        home = client.get("/", base_url=BASE).get_data(as_text=True)
        self.assertIn("2 to fill in", home)
        form = client.get("/t/people__roles/new?role=emergency_contact", base_url=BASE).get_data(as_text=True)
        self.assertRegex(form, r'value="emergency_contact"\s+selected')

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "people")))
