"""Tests for the Home care module: jobs due on the household's own dates, work logged without inventing the next date, links and privacy.

These follow the checks in Lane B's Home care draft (its NOTES.md, now in git history) that apply today (decision 0063)."""
import re
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5133
BASE = f"http://127.0.0.1:{PORT}"


class HomeCareModuleTests(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "home_care")

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

    def job(self, name="Clean the gutters", **values):
        return self.records.create("home_care__jobs", {"name": name, "kind": "gutters", **values})

    def gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("home_care__")]

    def due(self):
        return {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)
                if i.table.startswith("home_care__")}

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
        self.assertIn("home_care", self.report.modules)

    def test_it_links_to_people_and_stock_places_and_says_so(self):
        module = modules.load_module(ROOT / "modules" / "home_care")
        self.assertEqual(module.requires, ["people", "stock"])
        jobs, work = module.tables["jobs"].columns, module.tables["work_done"].columns
        self.assertEqual((jobs["place"].to, jobs["who_does_it"].to, work["done_by"].to),
                         ("stock.places", "people.people", "people.people"))
        labels = module.labels["tables"]
        self.assertEqual((labels["jobs"]["home"], labels["work_done"]["home"]), ("main", "more"))

    def test_smoke_alarms_and_extinguishers_stay_in_home_layout(self):
        """One source of truth for test dates (Lane B, Home care NOTES)."""
        kinds = {c.key for c in modules.load_module(ROOT / "modules" / "home_care").tables["jobs"].columns["kind"].choices}
        self.assertFalse(kinds & {"smoke_alarm", "co_alarm", "fire_extinguisher", "fire_blanket"}, kinds)

    def test_a_household_with_no_jobs_is_asked_nothing(self):
        self.assertEqual(self.gaps(), [])
        self.assertEqual(self.due(), {})

    def test_where_a_job_is_done_is_asked_until_a_place_is_chosen(self):
        job = self.job()
        self.assertEqual(self.gaps(), ["Where is Clean the gutters done? Choose one of your places."])
        outside = self.records.create("stock__places", {"name": "Outside"})
        self.records.update("home_care__jobs", job, {"place": outside})
        self.assertEqual(self.gaps(), [])

    def test_dates_are_due_or_overdue_never_expired(self):
        self.job("Clean the gutters", next_due=self.day(10))
        self.job("Hot water system service", kind="water_heater", next_due=self.day(-3))
        self.job("Prune the hedge", kind="outside", next_due=self.day(200))
        details = self.due()
        self.assertTrue(details["Clean the gutters"].startswith("job due"), details)
        self.assertIn("overdue", details["Hot water system service"])
        self.assertNotIn("Prune the hedge", details)
        self.assertNotIn("expire", " ".join(details.values()))

    def test_no_date_is_invented_when_the_household_gives_none(self):
        self.job(last_done=self.day(-400))
        self.assertEqual(self.due(), {})
        self.assertIsNone(self.conn.execute("SELECT next_due FROM home_care__jobs").fetchone()["next_due"])

    def test_logging_work_done_does_not_change_the_job_or_invent_the_next_date(self):
        job = self.job(last_done=self.day(-200), next_due=self.day(-5))
        before = dict(self.conn.execute("SELECT last_done, next_due FROM home_care__jobs WHERE id = ?", (job,)).fetchone())
        self.records.create("home_care__work_done", {"job": job, "notes": "Cleared both sides."})
        after = dict(self.conn.execute("SELECT last_done, next_due FROM home_care__jobs WHERE id = ?", (job,)).fetchone())
        self.assertEqual(after, before)
        self.assertIn("overdue", self.due()["Clean the gutters"])  # still due until the household types a new date
        done_on = self.conn.execute("SELECT done_on FROM home_care__work_done").fetchone()["done_on"]
        self.assertEqual(done_on, self.today.isoformat())  # the log defaults to today
        self.records.update("home_care__jobs", job, {"last_done": done_on, "next_due": self.day(90)})
        self.assertEqual(self.due(), {})

    def test_the_form_says_the_next_date_is_typed_by_the_household(self):
        page = self.page("/t/home_care__jobs/new")
        self.assertIn("Do again by", page)
        self.assertIn("Nothing is worked out for you", page)
        self.assertIn("type the next date here each time", page)

    def test_the_tradesperson_lives_in_people_so_one_change_shows_everywhere(self):
        plumber = self.records.create("people__people", {"name": "Example Plumbing", "phone": "0491 570 110"})
        self.job("Hot water system service", kind="water_heater", who_does_it=plumber)
        self.assertNotIn("phone", self.registry["home_care__jobs"].table.columns)
        self.records.update("people__people", plumber, {"name": "New Plumbing"})
        self.assertIn("New Plumbing", self.page("/sheet/home_care/home_care"))

    def test_deleting_the_person_clears_the_link(self):
        plumber = self.records.create("people__people", {"name": "Example Plumbing"})
        job = self.job(who_does_it=plumber)
        work = self.records.create("home_care__work_done", {"job": job, "done_by": plumber})
        self.records.delete("people__people", plumber)
        self.assertIsNone(self.conn.execute("SELECT who_does_it FROM home_care__jobs WHERE id = ?", (job,)).fetchone()[0])
        self.assertIsNone(self.conn.execute("SELECT done_by FROM home_care__work_done WHERE id = ?", (work,)).fetchone()[0])

    def test_a_place_a_job_is_at_cannot_be_deleted(self):
        garage = self.records.create("stock__places", {"name": "Garage"})
        job = self.job(place=garage)
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", garage)
        self.records.update("home_care__jobs", job, {"place": None})
        self.records.delete("stock__places", garage)

    def test_deleting_a_job_takes_its_history_and_restoring_brings_it_back(self):
        job = self.job(next_due=self.day(5))
        self.records.create("home_care__work_done", {"job": job, "done_on": self.day(-30)})
        self.records.delete("home_care__jobs", job)
        self.assertEqual(self.due(), {})
        live = "SELECT COUNT(*) FROM home_care__work_done WHERE deleted_at IS NULL"
        self.assertEqual(self.conn.execute(live).fetchone()[0], 0)
        self.records.restore("home_care__jobs", job)
        self.assertEqual(self.conn.execute(live).fetchone()[0], 1)
        self.assertEqual(len(self.due()), 1)

    def test_work_done_is_named_by_its_job_and_date(self):
        job = self.job()
        self.records.create("home_care__work_done", {"job": job, "done_on": "2026-05-20"})
        page = self.page("/t/home_care__work_done")
        self.assertIn("Clean the gutters", page)
        self.assertNotIn("Work done #", page)

    def test_nothing_private_has_a_field_and_notes_never_print(self):
        """No alarm codes or access instructions; no private column in a name or a question (decisions 0055, 0059)."""
        module = modules.load_module(ROOT / "modules" / "home_care")
        for table in module.tables.values():
            for column in table.columns:
                self.assertNotRegex(column, re.compile("code|access|key|password", re.I))
            private = {n for n, c in table.columns.items() if c.sensitive}
            names = set(re.findall(r"{(\w+)", table.record_name or ""))
            asked = {g["missing"] for g in table.watch.get("gaps", []) if g.get("missing")}
            asked |= {f for g in table.watch.get("gaps", []) for f in re.findall(r"{(\w+)", g["message"])}
            self.assertFalse(private & (names | asked), table.name)
        outside = self.records.create("stock__places", {"name": "Outside"})
        job = self.job(place=outside, next_due=self.day(20), notes="Ladder is behind the shed")
        self.records.create("home_care__work_done", {"job": job, "notes": "Cleared the back gutter"})
        sheet = self.page("/sheet/home_care/home_care")
        self.assertIn("Clean the gutters", sheet)
        self.assertIn("Do again by", sheet)
        for private in ("Ladder is behind the shed", "Cleared the back gutter"):
            self.assertNotIn(private, sheet)

    def test_sheet_shows_the_full_place_and_who_does_it(self):
        backyard = self.records.create("stock__places", {"name": "Backyard"})
        shed = self.records.create("stock__places", {"name": "Garden shed", "inside": backyard})
        helper = self.records.create("people__people", {"name": "Example Gutters"})
        self.job(place=shed, who_does_it=helper, next_due=self.day(30))
        sheet = self.page("/sheet/home_care/home_care")
        for shown in ("Backyard › Garden shed", "Example Gutters", "Clean the gutters"):
            self.assertIn(shown, sheet)

    def test_home_page_has_a_home_care_card_with_its_main_list(self):
        page = self.page("/")
        self.assertIn("Home care", page)
        self.assertIn("/t/home_care__jobs", page)
        self.assertIn("/t/home_care__work_done", page)

    def test_switching_it_on_changes_nothing_in_people_stock_or_home_layout(self):
        before_dir = self.tmp / "before"
        for name in ("people", "stock", "home_layout"):
            shutil.copytree(ROOT / "modules" / name, before_dir / "modules" / name)
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        conn = db.connect(before_dir / "data" / "dashboard.db")
        old = records.Records(conn, records.build_registry(report.loaded))
        old.create("people__people", {"name": "Person A", "phone": "0491 570 110"})
        place = old.create("stock__places", {"name": "Upstairs hall"})
        old.create("home_layout__equipment", {"name": "Hall smoke alarm", "kind": "smoke_alarm", "place": place,
                                              "next_check": self.day(10)})
        tables = ("people__people", "stock__places", "stock__items", "home_layout__equipment")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        conn.close()

        shutil.copytree(ROOT / "modules" / "home_care", before_dir / "modules" / "home_care")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        self.assertEqual(report.module_problems, {})
        self.assertIn("home_care", report.modules)
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        self.assertEqual({t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables},
                         snapshot)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM home_care__jobs").fetchone()[0], 0)

    def test_migration_matches_its_description_and_touches_only_its_own_tables(self):
        from dashboard.core.schema import next_migration_sql
        module = modules.load_module(ROOT / "modules" / "home_care")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "home_care" / "migrations" / "0001_first_tables.sql").read_text(encoding="utf-8")
        created = re.findall(r"CREATE (?:TABLE|INDEX) (\S+)", sql)
        self.assertTrue(created)
        self.assertTrue(all(name.startswith("home_care__") for name in created), created)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")
