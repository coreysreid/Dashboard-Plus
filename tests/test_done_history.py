"""Tests for earlier done days from a record's own history, and Garden's done date and jobs done per month (decision 0129)."""
import inspect
import re
import shutil
from datetime import date

from support import ROOT, TempDirTestCase
from dashboard.core import actions, bars, calendars, db, modules, records, settings, startup
from dashboard.web.app import create_app

PORT = 5148
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date(2026, 11, 20)
CARS, SERVICES = "vehicles__vehicles", "vehicles__services"
EQUIPMENT, LOANS, GARDEN = "home_layout__equipment", "lent_out__loans", "garden__jobs"
SECRET = "SECRET-SENTINEL-5520"
EARLIER = "(an earlier time, from its history)"


def main(page: str) -> str:
    return page[page.index("<main>"):page.index("</main>")]


def done_days(conn, registry, table, column, start=date(2026, 1, 1), end=date(2026, 12, 31)):
    return [(d.record_id, d.day.isoformat(), d.kind)
            for d in calendars.done_days(conn, registry, registry[table], column, start, end)]


class DeclarationTests(TempDirTestCase):
    """`history` on a calendar and bars without `per` are checked at load, in plain words, naming no module."""
    TABLES = '''[tables.jobs]
title = "Jobs"
columns.name = { type = "text", required = true }
columns.last_done = { type = "date" }
columns.next_due = { type = "date" }
columns.secret_day = { type = "date", sensitive = true, travels = "never" }
columns.amount = { type = "integer", unit = "g" }

[tables.jobs.watch]
expiring = { date = "next_due", warn_days = 7, wording = "due" }

[tables.done]
title = "Done"
columns.job = { type = "link", to = "jobs", required = true, on_delete = "cascade" }
columns.on = { type = "date", required = true }
'''

    def load(self, extra: str):
        return modules.load_module(self.make_module(tables=self.TABLES + extra, labels=None))

    def problems(self, extra: str) -> str:
        with self.assertRaises(modules.ModuleError) as caught:
            self.load(extra)
        return str(caught.exception)

    def test_good_declarations_are_kept(self):
        table = self.load('[tables.jobs.calendar]\ntitle = "J"\nentry = ["job", "jobs"]\nwhen = "last_done"\n'
                          'history = true\ndue = true\n\n[[tables.jobs.bars]]\nkey = "done"\ntitle = "Jobs done"\n'
                          'when = "last_done"\nhistory = true\nmeasure = "count"\nby = ["month"]\n'
                          'entry = ["job done", "jobs done"]\n').tables["jobs"]
        self.assertTrue(table.calendar["history"])
        self.assertEqual((table.bars[0]["per"], table.bars[0]["history"]), (None, True))

    def test_mistakes_are_explained(self):
        text = self.problems('[tables.jobs.calendar]\ntitle = "J"\nentry = ["a", "b"]\nhistory = true\ndue = true\n')
        self.assertIn("'history = true' shows each earlier date the 'when' column was moved on from, so it needs "
                      "'when'", text)
        text = self.problems('[tables.jobs.calendar]\ntitle = "J"\nentry = ["a", "b"]\nwhen = "last_done"\n'
                             'history = "yes"\ndue = true\n')
        self.assertIn("'history' must be true or false", text)
        text = self.problems('[tables.done.calendar]\nwhen = "on"\nper = "job"\nshow = "all"\ntitle = "D"\n'
                             'entry = ["a", "b"]\nlook = "done"\nhistory = true\n')
        self.assertIn("'history' is only for a calendar of a table's own records (no 'per')", text)
        base = '[[tables.jobs.bars]]\nkey = "k"\ntitle = "T"\nby = ["month"]\nentry = ["a", "b"]\n'
        text = self.problems(base + 'when = "secret_day"\nhistory = true\nmeasure = "count"\n')
        self.assertIn("with history = true, 'when' must name a date column of this table that says when each was "
                      "last done", text)
        text = self.problems(base + 'when = "last_done"\nhistory = true\nmeasure = "sum"\namount = "amount"\n'
                             'verb = "used"\n')
        self.assertIn("with history = true the bars count done days only", text)
        text = self.problems(base + 'when = "last_done"\nmeasure = "count"\n')
        self.assertIn("'when' must name a required date or date-and-time column", text)
        text = self.problems(base + 'when = "last_done"\nhistory = true\nmeasure = "count"\nsubject = "job"\n')
        self.assertIn("'subject' names the record each chart is for, so it needs 'per'", text)

    def test_shipped_declarations(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        tables = {f"{m.name}__{t.name}": t for m in found for t in m.tables.values()}
        for name, column in ((SERVICES, "last_done"), (EQUIPMENT, "last_tested"), (LOANS, "returned_on"),
                             (GARDEN, "done_on")):
            self.assertEqual((tables[name].calendar["when"], tables[name].calendar["history"]), (column, True), name)
        rule = tables[GARDEN].bars[0]
        self.assertEqual((rule["per"], rule["when"], rule["history"], rule["by"]),
                         (None, "done_on", True, ["month", "week"]))
        self.assertEqual(tables[GARDEN].actions[0]["set"], {"done": True, "done_on": "today"})

    def test_the_garden_migration_only_adds_an_empty_column(self):
        sql = (ROOT / "modules" / "garden" / "migrations" / "0002_done_on.sql").read_text(encoding="utf-8")
        self.assertIn("ALTER TABLE garden__jobs ADD COLUMN done_on TEXT;", sql)
        for word in ("UPDATE", "INSERT", "DELETE", "DROP"):
            self.assertNotIn(word, sql.upper())

    def test_core_names_no_module(self):
        text = "".join(inspect.getsource(f) for f in (calendars.earlier_done, calendars.done_days,
                                                         calendars.DoneDay, bars.done_days)).lower()
        for module in ("vehicle", "garden", "lent_out", "home_layout", "alarm", "loan"):
            self.assertNotIn(module, text)


class HistoryCase(TempDirTestCase):
    MODULES = ("people", "stock", "vehicles", "home_layout", "lent_out", "garden")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        settings.put(self.conn, "household.time_zone", "UTC")
        self.saved_on = "2026-01-05"
        self.store = records.Records(self.conn, records.build_registry(self.report.loaded),
                                     clock=lambda: f"{self.saved_on}T12:00:00+00:00")
        self.registry = self.store.registry
        self.car = self.store.create(CARS, {"name": "Example hatchback", "registration": SECRET})
        self.service = self.store.create(SERVICES, {"vehicle": self.car, "name": "Oil change",
                                                    "last_done": "2026-03-02", "next_due": "2026-12-01",
                                                    "notes": SECRET})

    def on(self, day: str, table: str, record_id: int, values: dict):
        """Save a change as if it were made on `day`."""
        self.saved_on = day
        self.store.update(table, record_id, values)

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


class EarlierDaysTests(HistoryCase):
    def test_each_date_moved_on_to_a_later_one_is_an_earlier_done_day(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-09"})
        self.on("2026-11-03", SERVICES, self.service, {"last_done": "2026-11-02"})
        self.assertEqual(done_days(self.conn, self.registry, SERVICES, "last_done"),
                         [(self.service, "2026-03-02", "earlier"), (self.service, "2026-07-09", "earlier"),
                          (self.service, "2026-11-02", "now")])
        july = self.page(f"/calendar/{SERVICES}?month=2026-07")
        self.assertIn(f"Example hatchback: Oil change: Service or check done {EARLIER}", july)
        november = self.page(f"/calendar/{SERVICES}?month=2026-11")
        self.assertIn("Example hatchback: Oil change: Service or check done</a>", november)
        self.assertNotIn(EARLIER, november)

    def test_a_date_typed_back_is_a_correction_and_never_a_done_day(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-19"})  # a typing slip, found later
        self.on("2026-07-12", SERVICES, self.service, {"last_done": "2026-07-09"})
        days = done_days(self.conn, self.registry, SERVICES, "last_done")
        self.assertNotIn("2026-07-19", [d for _, d, _ in days])
        self.assertEqual([d for _, d, _ in days], ["2026-03-02", "2026-07-09"])
        july = main(self.page(f"/calendar/{SERVICES}?month=2026-07"))
        self.assertIn("Thu 9 Jul</strong>", july)
        self.assertNotIn("Sun 19 Jul</strong>", july)

    def test_a_date_fixed_the_same_day_it_was_typed_does_not_count(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-01"})
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-09"})  # fixed straight away
        self.assertEqual([d for _, d, _ in done_days(self.conn, self.registry, SERVICES, "last_done")],
                         ["2026-03-02", "2026-07-09"])

    def test_a_cleared_date_never_counts(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": None})
        self.on("2026-08-10", SERVICES, self.service, {"last_done": "2026-08-09"})
        self.assertEqual([d for _, d, _ in done_days(self.conn, self.registry, SERVICES, "last_done")],
                         ["2026-08-09"])

    def test_a_deleted_record_has_no_done_days_and_comes_back_with_its_history(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-09"})
        self.store.delete(SERVICES, self.service)
        self.assertEqual(done_days(self.conn, self.registry, SERVICES, "last_done"), [])
        self.store.restore(SERVICES, self.service)
        self.assertEqual(len(done_days(self.conn, self.registry, SERVICES, "last_done")), 2)

    def test_alarm_tests_show_every_earlier_test(self):
        alarm = self.store.create(EQUIPMENT, {"name": "Hall smoke alarm", "kind": "smoke_alarm",
                                              "last_tested": "2026-05-04", "next_check": "2026-12-04",
                                              "access_details": SECRET})
        self.on("2026-08-05", EQUIPMENT, alarm, {"last_tested": "2026-08-04"})
        self.on("2026-11-05", EQUIPMENT, alarm, {"last_tested": "2026-11-04"})
        may = self.page(f"/calendar/{EQUIPMENT}?month=2026-05")
        self.assertIn(f"Hall smoke alarm: Test done {EARLIER}", may)
        self.assertNotIn(SECRET, may)
        together = self.page("/to-do/calendar?month=2026-08")
        self.assertIn(f"Home layout · Hall smoke alarm: Test done {EARLIER}", together)
        self.assertIn(f"Vehicles · Example hatchback: Oil change: Service or check done", self.page(
            "/to-do/calendar?month=2026-03"))

    def test_rules_of_the_calendar_still_hold(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-09"})
        text = main(self.page(f"/calendar/{SERVICES}?month=2026-07"))
        self.assertNotIn("<script", text)
        self.assertNotIn(SECRET, text)
        self.assertIn('<span class="cal-chip cal-done" title="', text)
        self.assertIn("✓", text)
        plain = re.sub(r"<[^>]+>", " ", text).replace("earlier times are never filled in as missed", "")
        plain = plain.replace("does not mean anything was missed", "")  # the bars under the calendar (decision 0131)
        for word in ("missed", "Missed", "overdue", "late"):
            self.assertNotIn(word, plain)


class LoanTests(HistoryCase):
    def setUp(self):
        super().setUp()
        neighbour = self.store.create("people__people", {"name": "Example Neighbour"})
        self.drill = self.store.create(LOANS, {"name": "Example drill", "borrower": neighbour, "lent_on": "2026-11-01",
                                               "due_back": "2026-11-25", "status": "out"})

    def test_an_undone_return_never_counts(self):
        self.saved_on = "2026-11-20"
        op = "0b5f3c1e-1111-4a6b-9e7d-000000000101"
        self.store.action(LOANS, self.drill, "returned", op=op, today=TODAY)
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"),
                         [(self.drill, "2026-11-20", "now")])
        actions.undo(self.store, LOANS, self.drill, op)
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"), [])
        self.assertNotIn("Example drill, lent to Example Neighbour: Return done",
                         self.page(f"/calendar/{LOANS}?month=2026-11"))

    def test_a_return_moved_back_to_the_real_day_shows_once_on_that_day(self):
        self.saved_on = "2026-11-20"
        self.store.action(LOANS, self.drill, "returned", op="0b5f3c1e-1111-4a6b-9e7d-000000000102", today=TODAY)
        self.on("2026-11-21", LOANS, self.drill, {"returned_on": "2026-11-18"})
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"),
                         [(self.drill, "2026-11-18", "now")])


class GardenTests(HistoryCase):
    def setUp(self):
        super().setUp()
        self.weed = self.store.create(GARDEN, {"title": "Weed the beds", "due_on": "2026-11-18", "notes": SECRET})
        self.garlic = self.store.create(GARDEN, {"title": "Plant garlic", "due_on": "2026-11-27"})

    def test_mark_done_fills_in_done_on_today_and_undo_clears_it(self):
        self.saved_on = "2026-11-20"
        op = "0b5f3c1e-1111-4a6b-9e7d-000000000201"
        self.store.action(GARDEN, self.weed, "done", op=op, today=TODAY)
        self.assertEqual(self.store.get(GARDEN, self.weed)["done_on"], "2026-11-20")
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [(self.weed, "2026-11-20", "now")])
        actions.undo(self.store, GARDEN, self.weed, op)
        self.assertIsNone(self.store.get(GARDEN, self.weed)["done_on"])
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [])

    def test_a_press_from_before_done_on_still_counts_on_its_day_and_is_never_backfilled(self):
        self.saved_on = "2026-11-19"
        op = "0b5f3c1e-1111-4a6b-9e7d-000000000202"
        # A press saved before decision 0129: it set only the tick, so the job keeps no done date.
        self.conn.execute(f"UPDATE {GARDEN} SET done = 1 WHERE id = ?", (self.weed,))
        self.conn.execute(
            "INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) VALUES "
            "(?, 'person', 'action', ?, ?, ?, ?)",
            ("2026-11-19T12:00:00+00:00", GARDEN, self.weed, '{"done": false}',
             '{"key": "done", "operation": "%s", "one_step": true, "added_table": null, "added": null, '
             '"before": {"done": false}, "after": {"done": true}, "next": null, "answers": {}, "copied": {}, '
             '"counts_as": "done", "missed": false, "on": "2026-11-19"}' % op))
        self.conn.commit()
        self.assertIsNone(self.store.get(GARDEN, self.weed)["done_on"])
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [(self.weed, "2026-11-19", "press")])
        page = self.page(f"/calendar/{GARDEN}?month=2026-11")
        self.assertIn(f"Weed the beds: Job done {EARLIER}", page)
        self.assertNotIn(SECRET, main(page))

    def test_jobs_done_per_month_counts_each_done_day(self):
        self.on("2026-09-02", GARDEN, self.weed, {"done": True, "done_on": "2026-09-01"})
        self.on("2026-10-01", GARDEN, self.weed, {"done": False, "due_on": "2026-10-20"})  # needs doing again
        self.on("2026-10-21", GARDEN, self.weed, {"done": True, "done_on": "2026-10-20"})
        self.on("2026-10-26", GARDEN, self.garlic, {"done": True, "done_on": "2026-10-25"})
        found = bars.build(self.conn, self.registry[GARDEN], self.registry[GARDEN].table.bars[0], None, "month",
                           TODAY, "monday", TODAY, registry=self.registry)
        self.assertEqual([(p.start.isoformat(), p.count) for p in found if p.count],
                         [("2026-09-01", 1), ("2026-10-01", 2)])
        page = self.page(f"/bars/{GARDEN}/done")
        text = main(page)
        self.assertIn("Vegetable garden · 12 months", text)
        self.assertIn("2 jobs done recorded", text)
        self.assertIn("never counted", text)
        self.assertNotIn("<script", text)
        self.assertNotIn(SECRET, text)
        self.assertNotIn("missed", re.sub(r"<[^>]+>", " ", text).replace("does not mean anything was missed", ""))
        listing = self.page(f"/t/{GARDEN}")
        self.assertIn(f'<a href="/calendar/{GARDEN}">Garden calendar</a>', listing)
        self.assertIn(f'<a href="/bars/{GARDEN}/done">Jobs done per month</a>', listing)
        calendar_page = self.page(f"/calendar/{GARDEN}?month=2026-10")
        self.assertIn("<h2>Jobs done per month</h2>", calendar_page)
        self.assertNotIn("Jobs done per month", self.page(f"/t/{GARDEN}/{self.weed}"),
                         "a chart of every job together is not a panel on one job's page")

    def test_garden_switched_off_has_no_bars_and_keeps_its_jobs(self):
        settings.set_module_enabled(self.conn, "garden", False)
        self.page(f"/bars/{GARDEN}/done", status=404)
        self.assertIsNotNone(self.store.get(GARDEN, self.weed))


class CalendarMonthTests(HistoryCase):
    def test_one_record_counts_once_a_day(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-09"})
        self.on("2026-07-11", SERVICES, self.service, {"last_done": "2026-03-02"})  # typed back to the first
        found = calendars.month(self.conn, self.registry, self.registry[SERVICES], 2026, 3, TODAY, "monday")
        self.assertEqual([(d.day.day, len(d.marks)) for d in found.days if d.marks], [(2, 1)])
