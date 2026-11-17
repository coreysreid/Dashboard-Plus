"""Tests for the Vehicles module: dates shown as due, who to call asked and kept in People, private numbers, the sheet.

These follow the checks in Lane B's Vehicles draft (its NOTES.md, now in git history) that apply today (decision 0058)."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5132
BASE = f"http://127.0.0.1:{PORT}"
PLATE = "DEMO-123"


class VehiclesModuleTests(TempDirTestCase):
    MODULES = ("people", "stock", "vehicles")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
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

    def gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("vehicles__")]

    def due(self):
        return {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)}

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, path):
        return self.client().get(path, base_url=BASE).get_data(as_text=True)

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertIn("vehicles", self.report.modules)

    def test_it_links_to_people_and_stock_and_says_so(self):
        module = modules.load_module(ROOT / "modules" / "vehicles")
        self.assertEqual(module.requires, ["people", "stock"])
        columns = module.tables["vehicles"].columns
        self.assertEqual((columns["roadside_contact"].to, columns["parked_at"].to, columns["emergency_kit"].to),
                         ("people.people", "stock.places", "stock.items"))

    def test_a_household_with_no_vehicle_is_asked_nothing(self):
        self.assertEqual(self.gaps(), [])
        self.assertEqual(self.due(), {})

    def test_who_to_call_is_asked_for_each_vehicle_until_someone_is_chosen(self):
        car = self.records.create("vehicles__vehicles", {"name": "Family car"})
        question = "Who would you call if Family car broke down? It can be a roadside service, a garage or someone you know."
        self.assertEqual(self.gaps(), [question])
        helper = self.records.create("people__people", {"name": "Example Roadside", "phone": "1800 975 707"})
        self.records.update("vehicles__vehicles", car, {"roadside_contact": helper})
        self.assertEqual(self.gaps(), [])

    def test_roadside_assistance_is_a_part_someone_can_play_in_who_to_call(self):
        helper = self.records.create("people__people", {"name": "Example Roadside", "phone": "1800 975 707"})
        self.records.create("people__roles", {"person": helper, "role": "roadside_assistance", "priority": 5})
        sheet = self.page("/sheet/people/emergency")
        self.assertIn("Roadside assistance", sheet)
        self.assertIn("1800 975 707", sheet)

    def test_the_number_lives_in_people_so_one_change_shows_everywhere(self):
        helper = self.records.create("people__people", {"name": "Example Roadside", "phone": "1800 975 707"})
        self.records.create("vehicles__vehicles", {"name": "Family car", "roadside_contact": helper})
        self.assertNotIn("phone", self.registry["vehicles__vehicles"].table.columns)
        self.records.update("people__people", helper, {"name": "New Roadside"})
        self.assertIn("New Roadside", self.page("/sheet/vehicles/vehicles"))

    def test_deleting_the_contact_clears_the_link_and_the_question_comes_back(self):
        helper = self.records.create("people__people", {"name": "Example Roadside"})
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "roadside_contact": helper})
        self.records.delete("people__people", helper)
        row = self.conn.execute("SELECT roadside_contact FROM vehicles__vehicles WHERE id = ?", (car,)).fetchone()
        self.assertIsNone(row["roadside_contact"])
        self.assertEqual(len(self.gaps()), 1)
        self.records.restore("people__people", helper)  # and restoring brings the link back with it
        self.assertEqual(self.gaps(), [])

    def test_dates_are_due_or_overdue_never_expired(self):
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "registration_due": self.day(12)})
        self.records.create("vehicles__vehicles", {"name": "Trailer", "registration_due": self.day(200)})
        self.records.create("vehicles__insurance", {"vehicle": car, "name": "Car cover", "renew_by": self.day(-2)})
        self.records.create("vehicles__services", {"vehicle": car, "name": "Routine service", "next_due": self.day(5)})
        details = self.due()
        self.assertTrue(details["Family car"].startswith("registration or vehicle tax due"), details)
        self.assertIn("overdue", details["Family car: Car cover"])
        self.assertTrue(details["Family car: Routine service"].startswith("service or check due"), details)
        self.assertNotIn("Trailer", details)
        self.assertNotIn("expire", " ".join(details.values()))

    def test_no_date_is_invented_when_the_household_gives_none(self):
        car = self.records.create("vehicles__vehicles", {"name": "Family car"})
        self.records.create("vehicles__insurance", {"vehicle": car, "name": "Car cover"})
        self.records.create("vehicles__services", {"vehicle": car, "name": "Routine service", "last_done": self.day(-400)})
        self.assertEqual(self.due(), {})
        row = self.conn.execute("SELECT next_due FROM vehicles__services").fetchone()
        self.assertIsNone(row["next_due"])

    def test_the_plate_number_is_private_and_stays_off_the_list_the_sheet_and_needs_attention(self):
        module = modules.load_module(ROOT / "modules" / "vehicles")
        self.assertTrue(module.tables["vehicles"].columns["registration"].sensitive)
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "registration": PLATE,
                                                         "registration_due": self.day(3),
                                                         "notes": "Papers are in the desk"})
        self.records.create("vehicles__insurance", {"vehicle": car, "name": "Car cover", "renew_by": self.day(40),
                                                    "notes": "Excess is high"})
        client = self.client()
        for path in ("/t/vehicles__vehicles", "/sheet/vehicles/vehicles", "/attention", "/"):
            with self.subTest(path=path):
                self.assertNotIn(PLATE, client.get(path, base_url=BASE).get_data(as_text=True))
        sheet = client.get("/sheet/vehicles/vehicles", base_url=BASE).get_data(as_text=True)
        for shown in ("Family car", "Car cover", "Registration or vehicle tax due"):
            self.assertIn(shown, sheet)
        for private in ("Papers are in the desk", "Excess is high"):
            self.assertNotIn(private, sheet)
        self.assertIn(PLATE, client.get(f"/t/vehicles__vehicles/{car}", base_url=BASE).get_data(as_text=True))

    def test_sheet_shows_who_to_call_the_full_place_and_the_kit(self):
        garage = self.records.create("stock__places", {"name": "Garage"})
        bay = self.records.create("stock__places", {"name": "Left bay", "inside": garage})
        kit = self.records.create("stock__items", {"name": "Car emergency kit", "category": "tools", "quantity": 1})
        helper = self.records.create("people__people", {"name": "Example Roadside"})
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "roadside_contact": helper,
                                                         "parked_at": bay, "emergency_kit": kit})
        self.records.create("vehicles__services", {"vehicle": car, "name": "Routine service", "next_due": self.day(30)})
        sheet = self.page("/sheet/vehicles/vehicles")
        for shown in ("Example Roadside", "Garage › Left bay", "Car emergency kit", "Routine service"):
            self.assertIn(shown, sheet)

    def test_choosing_a_kit_does_not_change_how_much_stock_there_is(self):
        kit = self.records.create("stock__items", {"name": "Car emergency kit", "category": "tools", "quantity": 1})
        before = [tuple(r) for r in self.conn.execute("SELECT id, quantity FROM stock__items")]
        moves = self.conn.execute("SELECT COUNT(*) FROM stock__movements").fetchone()[0]
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "emergency_kit": kit})
        self.records.delete("vehicles__vehicles", car)
        self.assertEqual([tuple(r) for r in self.conn.execute("SELECT id, quantity FROM stock__items")], before)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM stock__movements").fetchone()[0], moves)

    def test_a_place_a_vehicle_is_kept_at_cannot_be_deleted(self):
        """Never show a vehicle at a place that no longer exists (Lane B, Vehicles NOTES)."""
        garage = self.records.create("stock__places", {"name": "Garage"})
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "parked_at": garage})
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", garage)
        self.records.update("vehicles__vehicles", car, {"parked_at": None})
        self.records.delete("stock__places", garage)

    def test_deleting_a_vehicle_takes_its_reminders_and_restoring_brings_them_back(self):
        car = self.records.create("vehicles__vehicles", {"name": "Family car", "registration_due": self.day(5)})
        self.records.create("vehicles__insurance", {"vehicle": car, "name": "Car cover", "renew_by": self.day(5)})
        self.records.create("vehicles__services", {"vehicle": car, "name": "Routine service", "next_due": self.day(5)})
        self.assertEqual(len(self.due()), 3)
        self.records.delete("vehicles__vehicles", car)
        self.assertEqual(self.due(), {})
        self.assertEqual(self.gaps(), [])
        self.records.restore("vehicles__vehicles", car)
        self.assertEqual(len(self.due()), 3)

    def test_switching_it_on_changes_nothing_in_people_or_stock(self):
        before_dir = self.tmp / "before"
        for name in ("people", "stock"):
            shutil.copytree(ROOT / "modules" / name, before_dir / "modules" / name)
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        conn = db.connect(before_dir / "data" / "dashboard.db")
        old = records.Records(conn, records.build_registry(report.loaded))
        person = old.create("people__people", {"name": "Person A", "phone": "1800 975 707"})
        old.create("people__roles", {"person": person, "role": "other"})
        place = old.create("stock__places", {"name": "Car"})
        old.create("stock__items", {"name": "Car emergency kit", "category": "tools", "quantity": 1, "place": place})
        tables = ("people__people", "people__roles", "stock__places", "stock__items", "stock__lots", "stock__movements")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        conn.close()

        shutil.copytree(ROOT / "modules" / "vehicles", before_dir / "modules" / "vehicles")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        self.assertEqual(report.module_problems, {})
        self.assertIn("vehicles", report.modules)
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        self.assertEqual({t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables},
                         snapshot)

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "vehicles")))
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "people")))  # a new role needs none
