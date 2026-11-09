"""Tests for the Household stock module: running low, use-by dates, days of water and the supplies checklist."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5127
BASE = f"http://127.0.0.1:{PORT}"


class StockModuleTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("people", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)

    def item(self, **values):
        return self.records.create("stock__items", values)

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertEqual(sorted(self.report.modules), ["people", "stock"])
        self.assertEqual(self.registry["stock__items"].table.watch["supply"]["where"], {"category": "water"})

    def test_new_items_default_to_pantry(self):
        self.assertEqual(self.records.get("stock__items", self.item(name="Rice"))["category"], "pantry")

    def test_running_low_and_use_by(self):
        soon = (date.today() + timedelta(days=5)).isoformat()
        self.item(name="AA batteries", category="power", quantity=2, minimum=8, unit="each")
        self.item(name="Bandages", category="first_aid", quantity=20, minimum=10, expires=soon)
        self.item(name="Rice", quantity=4, minimum=2)
        low = watch.running_low(self.conn, self.registry)
        self.assertEqual([i.name for i in low], ["AA batteries"])
        self.assertEqual([i.name for i in watch.expiring(self.conn, self.registry)], ["Bandages"])

    def test_days_of_water_for_the_people_living_here(self):
        for name in ("Person A", "Person B", "Person C"):
            self.records.create("people__people", {"name": name, "lives_here": True})
        settings.put(self.conn, "household.pets", 1)
        self.item(name="Bottled water", category="water", quantity=20, unit="litres")
        self.item(name="Water container", category="water", quantity=10, unit="litres")
        self.item(name="Juice", category="pantry", quantity=6)
        supply = watch.supplies(self.conn, self.registry)[0]
        self.assertEqual(supply.total, 30)
        self.assertEqual(supply.daily_need, 10)  # 3 people x 3 litres + 1 pet x 1 litre
        self.assertAlmostEqual(supply.days, 3)
        self.assertEqual(supply.shortfall, 0)
        self.assertEqual(supply.label, "water")

    def test_a_place_cannot_be_deleted_while_things_are_kept_there(self):
        garage = self.records.create("stock__places", {"name": "Garage shelf"})
        self.item(name="Torch", category="power", place=garage)
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", garage)

    def test_supplies_checklist_prints_by_category(self):
        settings.put(self.conn, "setup.done", True)
        shelf = self.records.create("stock__places", {"name": "Garage shelf"})
        self.item(name="Bottled water", category="water", quantity=20, place=shelf)
        self.item(name="Antiseptic cream", category="first_aid", quantity=1, unit="tube")
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        page = client.get("/sheet/stock/supplies", base_url=BASE).get_data(as_text=True)
        self.assertIn("Water (litres)", page)
        self.assertIn("Garage shelf", page)
        self.assertIn("Antiseptic cream", page)

    def test_stock_in_and_out_from_the_item_page(self):
        settings.put(self.conn, "setup.done", True)
        rice = self.item(name="Rice", quantity=1, minimum=2, unit="kg")
        self.assertEqual([i.name for i in watch.running_low(self.conn, self.registry)], ["Rice"])
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        item_page = client.get(f"/t/stock__items/{rice}", base_url=BASE).get_data(as_text=True)
        self.assertIn(f'href="/t/stock__movements/new?item={rice}"', item_page)
        form = client.get(f"/t/stock__movements/new?item={rice}", base_url=BASE).get_data(as_text=True)
        self.assertRegex(form, rf'<option value="{rice}"\s+selected>Rice</option>')
        self.assertRegex(form, r'<option value="bought"\s+selected>Bought or added</option>')
        self.assertIn(f'value="{date.today().isoformat()}"', form)
        response = client.post("/t/stock__movements/new", base_url=BASE, data={
            "_csrf": app.config["CSRF_TOKEN"], "item": str(rice), "reason": "bought", "amount": "3",
            "happened_on": "2026-11-09", "then": "back", "back": f"/t/stock__items/{rice}"})
        self.assertEqual(response.headers["Location"], f"/t/stock__items/{rice}")
        self.assertEqual(self.records.get("stock__items", rice)["quantity"], 4)
        self.assertEqual(watch.running_low(self.conn, self.registry), [])
        refused = client.post("/t/stock__movements/new", base_url=BASE, data={
            "_csrf": app.config["CSRF_TOKEN"], "item": str(rice), "reason": "used", "amount": "9",
            "happened_on": "2026-11-09", "then": "back", "back": f"/t/stock__items/{rice}"})
        self.assertEqual(refused.status_code, 422)
        self.assertIn("only 4 left", refused.get_data(as_text=True))

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "stock")))
