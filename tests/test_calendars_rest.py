"""Tests for Documents, first aid kit checks, alarm tests and things lent out on the calendar, and Home care bars (decision 0125)."""
import re
import shutil
from datetime import date

from support import ROOT, TempDirTestCase
from dashboard.core import checklist, db, modules, records, settings, startup
from dashboard.web.app import create_app

PORT = 5147
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date(2026, 11, 20)
DOCS, KITS, CHECKS = "documents__documents", "medical__kits", "medical__kit_checks"
EQUIPMENT, LOANS = "home_layout__equipment", "lent_out__loans"
JOBS, WORK = "home_care__jobs", "home_care__work_done"
SECRET = "SECRET-SENTINEL-7731"


def main(page: str) -> str:
    return page[page.index("<main>"):page.index("</main>")]


class RestCase(TempDirTestCase):
    MODULES = ("people", "stock", "documents", "medical", "home_layout", "lent_out", "home_care", "utilities")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.store = records.Records(self.conn, records.build_registry(self.report.loaded))
        settings.put(self.conn, checklist.WEEK_START_KEY, "monday")
        create = self.store.create
        self.passport = create(DOCS, {"name": "Example passport", "kind": "passport", "renew_by": "2026-11-27",
                                      "notes": SECRET})
        self.kit = create(KITS, {"name": "Example kit", "kept": "home", "next_check": "2026-11-30",
                                 "notes": SECRET})
        self.check = create(CHECKS, {"kit": self.kit, "checked_on": "2026-11-05", "notes": SECRET})
        self.alarm = create(EQUIPMENT, {"name": "Hall smoke alarm", "kind": "smoke_alarm", "last_tested": "2026-11-02",
                                        "next_check": "2026-11-22", "access_details": SECRET})
        neighbour = create("people__people", {"name": "Example Neighbour"})
        self.drill = create(LOANS, {"name": "Example drill", "borrower": neighbour, "lent_on": "2026-11-01",
                                    "due_back": "2026-11-25", "status": "out", "notes": SECRET})
        self.job = create(JOBS, {"name": "Clear the gutters", "kind": "gutters"})
        for day in ("2026-09-03", "2026-10-04", "2026-10-20", "2026-11-10"):
            create(WORK, {"job": self.job, "done_on": day})

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["TODAY"] = lambda: TODAY
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, path, status=200):
        response = self.client().get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)


class DeclarationTests(RestCase):
    def test_shipped_declarations(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        tables = {f"{m.name}__{t.name}": t for m in found for t in m.tables.values()}
        for name in (DOCS, EQUIPMENT, LOANS):
            self.assertIsNone(tables[name].calendar["per"], name)
            self.assertTrue(tables[name].calendar["due"], name)
        self.assertEqual(tables[EQUIPMENT].calendar["when"], "last_tested")
        self.assertEqual(tables[LOANS].calendar["when"], "returned_on")
        self.assertEqual((tables[CHECKS].calendar["per"], tables[CHECKS].calendar["when"]), ("kit", "checked_on"))
        self.assertFalse(tables[KITS].calendar, "a kit's next check date is on the Kit checks calendar, once")
        self.assertFalse(tables["utilities__services"].calendar, "Utilities has no dated reminder")
        self.assertEqual(tables[WORK].bars[0]["measure"], "count")
        self.assertEqual(tables[WORK].bars[0]["per"], "job")


class TogetherTests(RestCase):
    def test_every_new_list_is_on_the_month_with_its_own_words(self):
        page = self.page("/to-do/calendar")
        for words in ("Important documents · Example passport: review or renewal planned",
                      "Medical readiness · Example kit: planned",
                      "Medical readiness · Example kit: Kit check done",
                      "Home layout · Hall smoke alarm: check planned",
                      "Home layout · Hall smoke alarm: Test done",
                      "Things lent out · Example drill, lent to Example Neighbour: return planned"):
            self.assertIn(words, page)

    def test_private_details_and_missed_words_never_show(self):
        text = main(self.page("/to-do/calendar"))
        self.assertNotIn(SECRET, text)
        plain = re.sub(r"<[^>]+>", " ", text).replace("earlier times are never filled in as missed", "")
        for word in ("missed", "Missed", "overdue"):
            self.assertNotIn(word, plain)

    def test_a_returned_loan_has_no_due_date_and_shows_the_day_back(self):
        self.store.update(LOANS, self.drill, {"status": "returned", "returned_on": "2026-11-18"})
        page = self.page("/to-do/calendar")
        self.assertIn("Example drill, lent to Example Neighbour: Return done", page)
        self.assertNotIn("Example drill, lent to Example Neighbour: return", page)

    def test_no_script(self):
        self.assertNotIn("<script", main(self.page("/to-do/calendar")))

    def test_modules_switched_off_are_hidden_and_kept(self):
        for name in ("documents", "medical", "home_layout", "lent_out"):
            settings.set_module_enabled(self.conn, name, False)
        page = self.page("/to-do/calendar")
        for words in ("Example passport", "Example kit", "Hall smoke alarm", "Example drill"):
            self.assertNotIn(words, page)
        self.assertIsNotNone(self.store.get(DOCS, self.passport))


class BarsTests(RestCase):
    def test_home_care_work_done_per_month_counts_each_job(self):
        page = self.page(f"/bars/{WORK}/done?subject={self.job}")
        text = re.sub(r"<[^>]+>", " ", main(page))
        for words in ("september 2026: 1", "october 2026: 2", "november 2026 (so far): 1",
                      "august 2026: nothing recorded"):
            self.assertIn(words, text.lower())
        self.assertIn("work done per month", text.lower())
        self.assertNotIn("<script", main(page))
