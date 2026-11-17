"""Tests for the Medical module: kits and where they are, checks shown as due, training renewals, and the sheet.

These follow Lane B's promotion checks (the Medical draft's ACCEPTANCE.md, now in git history)."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5129
BASE = f"http://127.0.0.1:{PORT}"


class MedicalModuleTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("medical", "people", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)
        self.today = date.today()

    def day(self, offset):
        return (self.today + timedelta(days=offset)).isoformat()

    def medical_gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("medical__")]

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertIn("medical", self.report.modules)

    def test_asks_about_a_kit_at_home_until_one_is_recorded_there(self):
        """A kit in the car is not there when the car is out (Lane B, Medical and dates UX check)."""
        at_home = "No first aid kit is recorded at home. Add one, or check where your kits are kept."
        self.assertEqual(self.medical_gaps(), [at_home])
        car = self.records.create("medical__kits", {"name": "Car kit", "kept": "vehicle"})
        self.assertIn(at_home, self.medical_gaps())
        self.records.update("medical__kits", car, {"kept": "home"})
        self.assertEqual(self.medical_gaps(), ["Which place is Car kit in? Choose where to find it.",
                                               "When do you plan to check Car kit again?"])

    def test_a_kit_saved_before_the_question_existed_is_asked_about(self):
        self.conn.execute("INSERT INTO medical__kits (name, created_at, updated_at) VALUES ('Old kit', '', '')")
        self.assertIn("Is Old kit kept at home, in a vehicle or somewhere else?", self.medical_gaps())

    def test_a_kit_check_is_due_or_overdue_never_expired(self):
        self.records.create("medical__kits", {"name": "Car kit", "kept": "home", "next_check": self.day(20)})
        self.records.create("medical__kits", {"name": "Hall kit", "kept": "home", "next_check": self.day(-2)})
        details = {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)}
        self.assertTrue(details["Car kit"].startswith("kit check due"), details["Car kit"])
        self.assertIn("overdue", details["Hall kit"])
        self.assertNotIn("expire", " ".join(details.values()))

    def test_a_blank_renewal_date_invents_nothing(self):
        person = self.records.create("people__people", {"name": "Person A"})
        self.records.create("medical__training", {"person": person, "course": "cpr", "completed_on": self.day(-10)})
        self.assertEqual(watch.expiring(self.conn, self.registry, self.today), [])

    def test_sheet_shows_the_full_place_path_and_leaves_out_check_notes(self):
        car = self.records.create("stock__places", {"name": "Car"})
        boot = self.records.create("stock__places", {"name": "Car boot", "inside": car})
        kit = self.records.create("medical__kits", {"name": "Car first aid kit", "kept": "home", "place": boot})
        self.records.create("medical__kit_checks", {"kit": kit, "checked_on": self.day(0),
                                                    "notes": "Plasters running out"})
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        page = client.get("/sheet/medical/first_aid", base_url=BASE).get_data(as_text=True)
        self.assertIn("Car › Car boot", page)
        self.assertNotIn("Plasters running out", page)

    def test_a_place_holding_a_kit_cannot_be_deleted(self):
        place = self.records.create("stock__places", {"name": "Hall closet"})
        self.records.create("medical__kits", {"name": "Hall kit", "kept": "home", "place": place})
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", place)

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "medical")))
