"""Tests for the timeline on a vehicle's, a home care job's and a routine's page, the dose wording after Show, and the declaration checks they needed (decision 0130)."""
import re
import shutil
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard.core import daily, db, modules, records, settings, startup
from dashboard.web.app import create_app
from test_module_medicine_doses import AMOUNT, SECRET, INFO, DoseTestCase

PORT = 5152
BASE = f"http://127.0.0.1:{PORT}"
SYDNEY_NOON = datetime(2026, 11, 25, 1, 0, tzinfo=timezone.utc)
READINGS, ESTIMATES = "vehicle_running__readings", "vehicle_running__estimates"
VEHICLES, SERVICES = "vehicles__vehicles", "vehicles__services"
JOBS, WORK = "home_care__jobs", "home_care__work_done"
ROUTINES, TIMES = "routines__routines", "routines__times"
PRIVATE_AMOUNT, PRIVATE_SCOPE, PRIVATE_NOTE = 987654, "Invented scope sentinel 5521", "Invented private note 8830"


def plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def section(page: str) -> str:
    begin = page.index('<section class="timeline"')
    return plain(page[begin:page.index("</section>", begin)])


class ShippedTimelineCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "vehicles", "vehicle_running", "home_care", "routines")

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
        settings.put(self.conn, daily.ZONE_KEY, "Australia/Sydney")

    def page(self, path, status=200):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: SYDNEY_NOON
        app.config["TODAY"] = lambda: date(2026, 11, 25)
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        response = client.get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)


class VehicleTimelineTests(ShippedTimelineCase):
    def setUp(self):
        super().setUp()
        self.car = self.store.create(VEHICLES, {"name": "Family car"})
        self.other = self.store.create(VEHICLES, {"name": "Work van"})
        self.service = self.store.create(SERVICES, {"vehicle": self.car, "name": "Routine service"})
        self.van_service = self.store.create(SERVICES, {"vehicle": self.other, "name": "Van brakes"})

    def reading(self, distance, at, unit="km", vehicle=None):
        return self.store.create(READINGS, {"vehicle": vehicle or self.car, "read_at": at, "distance": distance,
                                            "unit": unit})

    def test_readings_say_the_change_since_the_reading_before_and_nothing_more(self):
        self.reading(48500, "2026-10-02T09:00:00")
        self.reading(49740, "2026-11-20T09:00:00")
        self.reading(61000, "2026-11-01T09:00:00", vehicle=self.other)
        text = section(self.page(f"/t/{VEHICLES}/{self.car}"))
        self.assertIn("Odometer reading · Fri 20 Nov · 9:00 am · 49,740 km", text)
        self.assertIn("up 1,240 km since 2 Oct, from 48,500 km to 49,740 km", text)
        self.assertEqual(text.count(" since "), 1)
        self.assertNotIn("61,000", text)
        for inferred in ("per month", "a month", "per day", "average", "overdue"):
            self.assertNotIn(inferred, text)

    def test_a_reading_in_another_unit_is_never_compared(self):
        self.reading(48500, "2026-10-02T09:00:00", unit="km")
        self.reading(30100, "2026-11-20T09:00:00", unit="mi")
        text = section(self.page(f"/t/{VEHICLES}/{self.car}"))
        self.assertIn("30,100 mi", text)
        self.assertIn("48,500 km", text)
        self.assertNotIn(" since ", text)

    def test_estimates_show_their_words_but_never_a_private_value(self):
        self.store.create(ESTIMATES, {"service": self.service, "kind": "dealer", "quoted_on": "2026-11-18",
                                      "amount": PRIVATE_AMOUNT, "scope": PRIVATE_SCOPE, "notes": PRIVATE_NOTE})
        self.store.create(ESTIMATES, {"service": self.van_service, "kind": "independent", "quoted_on": "2026-11-19"})
        text = section(self.page(f"/t/{VEHICLES}/{self.car}"))
        self.assertIn("Service estimate · Wed 18 Nov · Family car: Routine service · Dealer", text)
        for secret in ("9,876", "987654", PRIVATE_SCOPE, PRIVATE_NOTE, "Van brakes", "Independent"):
            self.assertNotIn(secret, text)
        full = self.page(f"/timeline/{VEHICLES}/{self.car}")
        for secret in ("9,876", "987654", PRIVATE_SCOPE, PRIVATE_NOTE):
            self.assertNotIn(secret, full)

    def test_a_deleted_service_takes_its_estimate_off_the_timeline(self):
        self.store.create(ESTIMATES, {"service": self.service, "kind": "dealer", "quoted_on": "2026-11-18"})
        self.conn.execute(f"UPDATE {SERVICES} SET deleted_at = '2026-11-24T00:00:00+00:00' WHERE id = ?", (self.service,))
        self.conn.commit()
        self.assertIn("Nothing recorded yet for Family car.", section(self.page(f"/t/{VEHICLES}/{self.car}")))

    def test_vehicle_running_switched_off_takes_the_lines_away(self):
        self.reading(48500, "2026-10-02T09:00:00")
        settings.set_module_enabled(self.conn, "vehicle_running", False)
        self.assertNotIn("What happened", self.page(f"/t/{VEHICLES}/{self.car}"))
        self.page(f"/timeline/{VEHICLES}/{self.car}", status=404)


class HomeCareAndRoutineTests(ShippedTimelineCase):
    def test_a_jobs_page_lists_work_done_newest_first_and_who_did_it(self):
        sam = self.store.create("people__people", {"name": "Sam Example"})
        job = self.store.create(JOBS, {"name": "Clean gutters", "kind": "gutters"})
        other = self.store.create(JOBS, {"name": "Service boiler", "kind": "water_heater"})
        self.store.create(WORK, {"job": job, "done_on": "2026-10-03", "done_by": sam})
        self.store.create(WORK, {"job": job, "done_on": "2026-11-21"})
        self.store.create(WORK, {"job": other, "done_on": "2026-11-22"})
        text = section(self.page(f"/t/{JOBS}/{job}"))
        self.assertLess(text.index("Work done · Sat 21 Nov"), text.index("Work done · Sat 3 Oct · Sam Example"))
        self.assertNotIn("22 Nov", text)

    def test_a_routines_page_lists_done_and_skipped_never_missed(self):
        routine = self.store.create(ROUTINES, {"name": "Water the plants"})
        self.store.create(TIMES, {"routine": routine, "outcome": "done", "done_on": "2026-11-20"})
        self.store.create(TIMES, {"routine": routine, "outcome": "skipped", "done_on": "2026-11-10"})
        text = section(self.page(f"/t/{ROUTINES}/{routine}"))
        self.assertIn("Routine outcome · Fri 20 Nov · Done", text)
        self.assertIn("Routine outcome · Tue 10 Nov · Skipped this time", text)
        self.assertNotIn("missed", text.lower().replace("does not mean anything was missed", ""))


class DoseWordsTests(DoseTestCase):
    def shown(self):
        client = self.client()
        reply = self.post(client, f"/timeline/people__people/{self.rosa}")
        self.assertEqual(reply.status_code, 200)
        page = reply.get_data(as_text=True)
        return plain(page[page.index("<main>"):page.index("</main>")])

    def test_after_show_a_dose_reads_in_the_medicines_own_words_with_no_id(self):
        self.dose(at="2026-11-24T08:00:00", amount=AMOUNT, unit="drop")
        text = self.shown()
        self.assertIn(f"8:00 am · {SECRET}", text)
        self.assertNotIn("#", text)
        self.assertNotIn(AMOUNT, text)
        self.assertNotIn("Maria Garcia", text)

    def test_two_medicines_with_the_same_words_are_told_apart_plainly(self):
        twin = self.records.create(INFO, {"person": self.rosa, "kind": "medication", "detail": SECRET.upper()})
        self.dose(at="2026-11-24T08:00:00")
        self.dose(med=twin, at="2026-11-24T09:00:00")
        self.dose(med=self.med2, at="2026-11-24T10:00:00")
        text = self.shown()
        self.assertIn(f"8:00 am · {SECRET} (1 of 2 with the same words)", text)
        self.assertIn(f"9:00 am · {SECRET.upper()} (2 of 2 with the same words)", text)
        self.assertIn("10:00 am · Invented eye drops", text)
        self.assertNotIn("Invented eye drops (", text)

    def test_another_persons_medicine_or_another_kind_with_the_same_words_is_not_a_twin(self):
        self.records.create(INFO, {"person": self.sofia, "kind": "medication", "detail": SECRET})
        self.records.create(INFO, {"person": self.rosa, "kind": "allergy", "detail": SECRET})
        self.dose(at="2026-11-24T08:00:00")
        self.assertNotIn("with the same words", self.shown())

    def test_before_show_nothing_changed(self):
        self.dose(at="2026-11-24T08:00:00")
        page = self.page(f"/timeline/people__people/{self.rosa}")
        main = page[page.index("<main>"):page.index("</main>")]
        self.assertIn("1 dose recorded on Tue 24 Nov", plain(main))
        self.assertNotIn(SECRET, main)


class DeclarationTests(TempDirTestCase):
    TABLES = '''[tables.cars]
title = "Cars"
columns.name = { type = "text", required = true }

[tables.reads]
title = "Reads"
columns.car = { type = "link", to = "cars", required = true, on_delete = "cascade" }
columns.at = { type = "datetime", required = true }
columns.km = { type = "integer", required = true }
columns.unit = { type = "choice", required = true, choices = ["km", "mi"] }
columns.maybe = { type = "choice", choices = ["km", "mi"] }
columns.secret = { type = "choice", required = true, sensitive = true, choices = ["km", "mi"] }
'''

    def load(self, extra: str):
        return modules.load_module(self.make_module(tables=self.TABLES + extra, labels=None))

    def test_a_change_may_take_its_unit_from_a_choice_column(self):
        rule = self.load('[tables.reads.timeline]\nwhen = "at"\nper = "car"\nentry = ["a", "b"]\nchange = "km"\n'
                         'change_unit = "unit"\n').tables["reads"].timeline
        self.assertEqual((rule["change"], rule["change_unit"]), ("km", "unit"))

    def test_wrong_change_units_are_explained(self):
        base = '[tables.reads.timeline]\nwhen = "at"\nper = "car"\nentry = ["a", "b"]\n'
        for extra, said in (('change = "km"\n', "with its own unit"),
                            ('change = "km"\nchange_unit = "maybe"\n', "must name a required choice column"),
                            ('change = "km"\nchange_unit = "secret"\n', "not private"),
                            ('change_unit = "unit"\n', "goes with 'change'")):
            with self.assertRaises(modules.ModuleError) as caught:
                self.load(base + extra)
            self.assertIn(said, str(caught.exception))

    def test_a_link_through_another_module_is_checked_once_both_are_loaded(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        by_name = {m.name: m for m in found}
        estimates = by_name["vehicle_running"].tables["estimates"]
        self.assertEqual((estimates.timeline["link"], estimates.timeline["through"]), ("service", "vehicle"))
        by_name["vehicles"].tables["services"].columns["vehicle"].required = False
        problems = modules._cross_module_timeline_problems(by_name["vehicle_running"], by_name)
        self.assertEqual(len(problems), 1)
        self.assertIn("'vehicles.services' must have a required link column 'vehicle'", problems[0])
