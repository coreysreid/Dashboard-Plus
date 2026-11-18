"""Tests for the Vegetable garden module: job reminders only while not done, beds at Places, the plan sheet, no growing advice.

These follow the notes in Lane B's draft (now in git history) that apply today (decisions 0072, 0076)."""
import re
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5135
BASE = f"http://127.0.0.1:{PORT}"


class GardenModuleTests(TempDirTestCase):
    MODULES = ("stock", "garden")

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
        self.place = self.records.create("stock__places", {"name": "Backyard"})
        self.bed = self.records.create("garden__beds", {"name": "Raised bed", "place": self.place})

    def day(self, offset):
        return (self.today + timedelta(days=offset)).isoformat()

    def job(self, title="Check bed ties", **values):
        return self.records.create("garden__jobs", {"title": title, "bed": self.bed, **values})

    def due(self):
        return {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)
                if i.table.startswith("garden__")}

    def gaps(self):
        return [g for g in watch.gaps(self.conn, self.registry) if g.table.startswith("garden__")]

    def page(self, path):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client.get(path, base_url=BASE).get_data(as_text=True)

    def test_module_loads_and_requires_stock_for_places(self):
        self.assertEqual(self.report.module_problems, {})
        module = modules.load_module(ROOT / "modules" / "garden")
        self.assertEqual(module.requires, ["stock"])
        self.assertEqual(module.tables["beds"].columns["place"].to, "stock.places")

    def test_a_job_reminds_only_while_it_is_not_done(self):
        job = self.job(due_on=self.day(3))
        self.job("Water the pots", due_on=self.day(-2))
        self.job("Order seeds", due_on=self.day(60))
        details = self.due()
        self.assertTrue(details["Check bed ties"].startswith("job due"), details)
        self.assertIn("job overdue since", details["Water the pots"])
        self.assertNotIn("Order seeds", details)  # a long way off
        self.records.update("garden__jobs", job, {"done": True})
        self.assertNotIn("Check bed ties", self.due())
        self.records.update("garden__jobs", job, {"done": False})  # reopened by mistake: it is back
        self.assertIn("Check bed ties", self.due())

    def test_a_job_never_marked_done_still_reminds(self):
        self.job(due_on=self.day(1), done=None)
        self.assertIn("Check bed ties", self.due())

    def test_a_job_without_a_date_is_never_a_reminder(self):
        self.job()
        self.assertEqual(self.due(), {})

    def test_a_bed_with_no_place_is_asked_about_and_a_household_with_no_beds_is_asked_nothing(self):
        self.assertEqual(self.gaps(), [])
        self.records.create("garden__beds", {"name": "Balcony pot"})
        self.assertEqual([g.message for g in self.gaps()], ["Where is Balcony pot? Choose one of your places."])

    def test_a_place_with_a_bed_cannot_be_deleted(self):
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", self.place)

    def test_harvests_link_to_a_named_planting(self):
        crop = self.records.create("garden__crops", {"name": "Tomato"})
        planting = self.records.create("garden__plantings", {
            "name": "Tomatoes 2026", "bed": self.bed, "crop": crop, "planted_on": self.day(-30)})
        harvest = self.records.create("garden__harvests", {
            "planting": planting, "harvested_on": self.day(-1), "amount": 1.5, "unit": "kg"})
        self.assertEqual(self.records.get("garden__harvests", harvest)["amount"], 1.5)
        with self.assertRaises(records.ValidationError):
            self.records.delete("garden__plantings", planting)  # a harvest still points at it

    def test_the_plan_sheet_lists_beds_and_jobs_not_done_and_no_notes(self):
        self.records.update("garden__beds", self.bed, {"notes": "Soil came from a neighbour"})
        self.job("Check bed ties", due_on=self.day(3), notes="Use the blue cord")
        self.job("Mend the edge", due_on=self.day(-9), done=True)
        sheet = self.page("/sheet/garden/plan")
        for shown in ("Garden plan", "Raised bed", "Backyard", "Check bed ties"):
            self.assertIn(shown, sheet)
        self.assertNotIn("Mend the edge", sheet)
        self.assertNotIn("Use the blue cord", sheet)
        self.assertNotIn("Soil came from a neighbour", sheet)

    def test_home_page_has_a_jobs_card(self):
        page = self.page("/")
        self.assertIn("/t/garden__jobs", page)

    def test_nothing_private_and_no_growing_advice(self):
        module = modules.load_module(ROOT / "modules" / "garden")
        for table in module.tables.values():
            self.assertEqual([n for n, c in table.columns.items() if c.sensitive], [])
        text = " ".join(p.read_text(encoding="utf-8").lower()
                        for p in (ROOT / "modules" / "garden").glob("*.toml"))
        for advice in ("should plant", "best time to", "water every", "fertili", "frost", "yield"):
            self.assertNotIn(advice, text)

    def test_switching_it_on_changes_nothing_in_stock(self):
        before_dir = self.tmp / "before"
        shutil.copytree(ROOT / "modules" / "stock", before_dir / "modules" / "stock")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        conn = db.connect(before_dir / "data" / "dashboard.db")
        old = records.Records(conn, records.build_registry(report.loaded))
        old.create("stock__places", {"name": "Backyard"})
        tables = ("stock__places", "stock__items", "stock__movements")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        conn.close()
        shutil.copytree(ROOT / "modules" / "garden", before_dir / "modules" / "garden")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        self.assertEqual(report.module_problems, {})
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        self.assertEqual({t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables},
                         snapshot)

    def test_migration_matches_its_description_and_touches_only_its_own_tables(self):
        from dashboard.core.schema import next_migration_sql
        module = modules.load_module(ROOT / "modules" / "garden")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "garden" / "migrations" / "0001_first_tables.sql").read_text(encoding="utf-8")
        created = re.findall(r"CREATE (?:TABLE|INDEX) (\S+)", sql)
        self.assertTrue(created)
        self.assertTrue(all(name.startswith("garden__") for name in created), created)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")
