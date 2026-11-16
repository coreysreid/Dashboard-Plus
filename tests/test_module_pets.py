"""Tests for the Pets module: it loads beside People, counts pets for water, asks about vets and shows what is due."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5128
BASE = f"http://127.0.0.1:{PORT}"


class PetsModuleTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("people", "pets", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertIn("pets", self.report.modules)

    def test_pets_recorded_count_towards_days_of_water(self):
        settings.put(self.conn, "household.pets", 5)  # the number from setup no longer counts once Pets is on
        self.records.create("pets__pets", {"name": "Rex", "species": "dog"})
        self.assertEqual(watch.household(self.conn, self.registry).pets, 1)

    def test_asks_for_the_vet_and_the_vets_phone(self):
        pet = self.records.create("pets__pets", {"name": "Rex", "species": "dog"})
        messages = lambda: [g.message for g in watch.gaps(self.conn, self.registry) if "vet" in g.message]  # noqa: E731
        self.assertEqual(messages(), ["Who is Rex's vet? Their vet is not filled in yet."])
        vet = self.records.create("people__people", {"name": "Riverside Vet Clinic"})
        self.records.update("pets__pets", pet, {"vet": vet})
        self.assertEqual(messages(), ["What is the phone number for Riverside Vet Clinic, Rex's vet?"])
        self.records.update("people__people", vet, {"phone": "555 0150"})
        self.assertEqual(messages(), [])

    def test_treatments_and_vaccinations_show_as_due(self):
        today = date.today()
        pet = self.records.create("pets__pets", {"name": "Rex", "species": "dog",
                                                 "vaccinations_due": (today - timedelta(days=2)).isoformat()})
        self.records.create("pets__treatments", {"pet": pet, "name": "Flea chew", "kind": "flea",
                                                 "next_due": (today + timedelta(days=3)).isoformat()})
        details = {i.name: i.detail for i in watch.expiring(self.conn, self.registry, today)}
        self.assertTrue(details["Rex"].startswith("vaccinations overdue since"))
        self.assertTrue(details["Flea chew"].startswith("due "))
        self.assertIn("(in 3 days)", details["Flea chew"])

    def test_pet_details_sheet_prints(self):
        vet = self.records.create("people__people", {"name": "Riverside Vet Clinic", "phone": "555 0150"})
        self.records.create("pets__pets", {"name": "Rex", "species": "dog", "microchip": "900000000123456",
                                           "vet": vet})
        page = self.client().get("/sheet/pets/pets", base_url=BASE).get_data(as_text=True)
        self.assertIn("900000000123456", page)
        self.assertIn("Riverside Vet Clinic", page)

    def test_setup_asks_for_each_pets_name_and_kind(self):
        client = self.client()
        settings.put(self.conn, "setup.done", False)
        page = client.get("/setup", base_url=BASE).get_data(as_text=True)
        self.assertIn('name="pet_1"', page)
        self.assertNotIn('name="pets"', page)  # no bare count when Pets is on
        app_csrf = client.application.config["CSRF_TOKEN"]
        client.post("/setup", data={"_csrf": app_csrf, "name_1": "Person A", "pet_1": "Rex", "pet_kind_1": "dog",
                                    "pet_2": "Whiskers", "pet_kind_2": "cat",
                                    "modules": ["people", "pets", "stock"]}, base_url=BASE)
        rows = self.conn.execute("SELECT name, species FROM pets__pets ORDER BY name").fetchall()
        self.assertEqual([tuple(r) for r in rows], [("Rex", "dog"), ("Whiskers", "cat")])
        self.assertEqual(settings.get(self.conn, "household.pets"), 2)

    def test_a_gap_naming_a_column_people_lacks_is_explained(self):
        folder = self.tmp / "modules" / "pets"
        text = (folder / "tables.toml").read_text(encoding="utf-8").replace('missing = "vet.phone"',
                                                                           'missing = "vet.fax"')
        (folder / "tables.toml").write_text(text, encoding="utf-8")
        _, failures = modules.discover(self.tmp / "modules")
        self.assertIn("'vet.fax' names a column 'fax'", " ".join(failures["pets"]))

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "pets")))
