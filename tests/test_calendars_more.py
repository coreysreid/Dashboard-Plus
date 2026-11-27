"""Tests for Home care, Garden, Vehicles and Bills on calendars and one Things to do month with Show links (decision 0122)."""
import re
import shutil
from datetime import date

from support import ROOT, TempDirTestCase
from dashboard.core import actions, calendars, checklist, db, modules, records, reminder_moves, settings, startup
from dashboard.web.app import create_app

PORT = 5146
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date(2026, 11, 20)
JOBS, WORK = "home_care__jobs", "home_care__work_done"
GARDEN = "garden__jobs"
CARS, INSURANCE, SERVICES = "vehicles__vehicles", "vehicles__insurance", "vehicles__services"
BILLS = "bills_insurance__commitments"
ROUTINES, TIMES = "routines__routines", "routines__times"
# Invented private values that must never reach a calendar's words or HTML.
PLATE, AMOUNT, COVERS = "PLATE-SENTINEL-4471", "432.19", "Invented cover sentinel 6620"
REFERENCE, NOTE = "DEMO-REF-SENTINEL-3318", "Invented private bill note 9054"


def chips(page: str) -> list[tuple[str, str, str]]:
    return re.findall(r'<span class="cal-chip cal-(\w+)" title="([^"]*)" aria-hidden="true">([^<]+)', page)


def main(page: str) -> str:
    return page[page.index("<main>"):page.index("</main>")]


class DeclarationTests(TempDirTestCase):
    """A calendar of a table's own records (no `per`) is checked at load, with plain words for each mistake."""
    TABLES = '''[tables.jobs]
title = "Jobs"
columns.name = { type = "text", required = true }
columns.last_done = { type = "date" }
columns.next_due = { type = "date" }
columns.secret_day = { type = "date", sensitive = true, travels = "never" }

[tables.jobs.watch]
expiring = { date = "next_due", warn_days = 7, wording = "due" }

[tables.plain]
title = "Plain"
columns.name = { type = "text", required = true }
columns.on = { type = "date" }

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

    def test_a_good_own_calendar_is_kept(self):
        rule = self.load('[tables.jobs.calendar]\ntitle = "Job calendar"\nentry = ["job", "jobs"]\nwhen = '
                         '"last_done"\ndue = true\n').tables["jobs"].calendar
        self.assertEqual((rule["per"], rule["show"], rule["when"], rule["look"], rule["due"]),
                         (None, "all", "last_done", "done", True))

    def test_wrong_own_calendars_are_explained(self):
        text = self.problems('[tables.plain.calendar]\ntitle = " "\nentry = ["one"]\nshow = "one"\n'
                             'state = "name"\nlook = "red"\n')
        for words in ("without 'per' it is a calendar of this table's own records, so it needs due = true",
                      "leave out 'show' or write show = \"all\"", "'state' needs 'per'", "'title' must be",
                      "'entry' must be two words", "'look' must be \"recorded\""):
            self.assertIn(words, text)
        text = self.problems('[tables.plain.calendar]\ntitle = "P"\nentry = ["a", "b"]\ndue = true\n')
        self.assertIn("this table needs a reminder with wording = \"due\"", text)
        for column in ("next_due", "secret_day", "name", "nothing"):
            text = self.problems(f'[tables.jobs.calendar]\ntitle = "J"\nentry = ["a", "b"]\ndue = true\n'
                                 f'when = "{column}"\n')
            self.assertIn("'when' must name a date column of this table that says when it was last done", text)

    def test_one_due_date_is_on_one_calendar_only(self):
        text = self.problems('[tables.jobs.calendar]\ntitle = "J"\nentry = ["a", "b"]\ndue = true\n\n'
                             '[tables.done.calendar]\nwhen = "on"\nper = "job"\nshow = "all"\ntitle = "D"\n'
                             'entry = ["a", "b"]\nlook = "done"\ndue = true\n')
        self.assertIn("'done' already shows its due dates on its own calendar", text)

    def test_shipped_modules_declare_what_this_decision_describes(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        tables = {f"{m.name}__{t.name}": t for m in found for t in m.tables.values()}
        self.assertEqual((tables[WORK].calendar["per"], tables[WORK].calendar["due"]), ("job", True))
        for name in (GARDEN, CARS, INSURANCE, SERVICES, BILLS):
            self.assertIsNone(tables[name].calendar["per"], name)
            self.assertTrue(tables[name].calendar["due"], name)
        self.assertEqual(tables[SERVICES].calendar["when"], "last_done")
        self.assertFalse(tables[JOBS].calendar, "Home care jobs' dates are on the Work done calendar, once")


class MoreCalendarsCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_care", "garden", "vehicles", "bills_insurance", "routines")

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
        self.gutters = create(JOBS, {"name": "Clear the gutters", "kind": "gutters", "next_due": "2026-11-25"})
        self.work = create(WORK, {"job": self.gutters, "done_on": "2026-11-10"})
        self.weed = create(GARDEN, {"title": "Weed the beds", "due_on": "2026-11-18"})
        self.garlic = create(GARDEN, {"title": "Plant garlic", "due_on": "2026-11-27"})
        self.car = create(CARS, {"name": "Example hatchback", "registration": PLATE,
                                 "registration_due": "2026-11-30"})
        self.service = create(SERVICES, {"vehicle": self.car, "name": "Yearly service", "last_done": "2026-11-03",
                                         "next_due": "2026-12-15"})
        self.bill = create(BILLS, {"name": "Example electricity", "kind": "bill", "category": "electricity",
                                   "next_due": "2026-11-20", "amount": AMOUNT, "covers": COVERS,
                                   "reference_last4": REFERENCE[-4:], "notes": NOTE})

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["TODAY"] = lambda: TODAY
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, path, client=None, status=200):
        response = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)

    def press(self, job, op="0b5f3c1e-1111-4a6b-9e7d-000000000001"):
        self.store.action(GARDEN, job, "done", op=op, today=TODAY)
        return op


class TogetherTests(MoreCalendarsCase):
    def test_every_list_is_on_one_month_each_line_labelled_by_its_module(self):
        self.press(self.weed)
        page = self.page("/to-do/calendar")
        self.assertIn("<caption>Things to do calendar, November 2026</caption>", page)
        for words in ("Home care · Clear the gutters: Job done", "Home care · Clear the gutters: planned",
                      "Vegetable garden · Weed the beds: Job done", "Vegetable garden · Plant garlic: job planned",
                      "Vehicles · Example hatchback: registration or vehicle tax planned",
                      "Vehicles · Example hatchback: Yearly service: Service or check done",
                      "Bills and insurance · Example electricity: bill check due today"):
            self.assertIn(words, page)
        self.assertIn('<span class="vh">20 November, today: Done; Due today</span>', page)
        self.assertIn('<span class="vh">10 November: Done</span>', page)
        self.assertIn("How many this month, by list: Bills and insurance: 1 · Home care: 2 · Routines: 0 · "
                      "Vegetable garden: 2 · Vehicles: 2.", page)
        self.assertNotIn("Weed the beds: job", page, "a finished job has no due date left to show")
        drawn = {(look, symbol) for look, _, symbol in chips(page)}
        self.assertEqual(drawn, {("done", "✓"), ("due", "○"), ("planned", "◇")})
        legend = page[page.index('class="cal-legend"'):page.index("</ul>", page.index('class="cal-legend"'))]
        for words in ("Done", "Due, not recorded as done yet: shown once, on its own date", "Planned date",
                      "A blank day has nothing recorded or planned"):
            self.assertIn(words, legend)

    def test_show_links_keep_one_module_and_the_month(self):
        page = self.page("/to-do/calendar?month=2026-12")
        nav = page[page.index('class="cal-show"'):page.index("</nav>", page.index('class="cal-show"'))]
        for label in ("All", "Home care", "Vegetable garden", "Vehicles", "Bills and insurance", "Routines"):
            self.assertIn(f">{label}</a>", nav)
        self.assertIn('href="/to-do/calendar?month=2026-12" aria-current="page">All</a>', nav)
        self.assertIn('href="/to-do/calendar?only=garden&amp;month=2026-12">Vegetable garden</a>', nav)
        garden = self.page("/to-do/calendar?only=garden")
        self.assertIn("<caption>Garden calendar, November 2026</caption>", garden)
        self.assertIn('aria-current="page">Vegetable garden</a>', garden)
        self.assertNotIn("Clear the gutters", main(garden))
        self.assertIn('href="/to-do/calendar?only=garden&amp;month=2026-12" rel="next"', garden)
        cars = self.page("/to-do/calendar?only=vehicles")
        self.assertIn("<caption>Vehicles calendar, November 2026</caption>", cars)
        self.assertIn("Vehicles · Example hatchback: Yearly service: Service or check done", cars)
        self.assertNotIn("Example electricity", main(cars))
        december = self.page("/to-do/calendar?only=vehicles&month=2026-12")
        self.assertIn("Example hatchback: Yearly service: service or check planned", december)
        self.assertIn("Things to do calendar", self.page("/to-do/calendar?only=nothing_here"))

    def test_undo_takes_a_garden_press_away_and_the_due_date_comes_back(self):
        op = self.press(self.weed)
        self.assertIn("Vegetable garden · Weed the beds: Job done", self.page("/to-do/calendar"))
        actions.undo(self.store, GARDEN, self.weed, op)
        page = self.page("/to-do/calendar")
        self.assertNotIn("Weed the beds: Job done", page)
        self.assertIn("Vegetable garden · Weed the beds: job due since 18/11/26, not recorded as done yet", page)

    def test_a_late_date_is_marked_once_and_a_blank_day_is_never_called_missed(self):
        found = calendars.month(self.conn, self.store.registry, self.store.registry[GARDEN], 2026, 11, TODAY,
                                "monday")
        self.assertEqual([(d.day.day, [m.look for m in d.marks]) for d in found.days if d.marks],
                         [(18, ["due"]), (27, ["planned"])])
        text = re.sub(r"<[^>]+>", " ", main(self.page("/to-do/calendar"))).replace(
            "earlier times are never filled in as missed", "")
        for word in ("missed", "Missed", "overdue", "streak"):
            self.assertNotIn(word, text)

    def test_one_date_moved_to_bills_shows_once(self):
        policy = self.store.create(INSURANCE, {"vehicle": self.car, "name": "Comprehensive cover",
                                               "renew_by": "2026-11-24"})
        self.assertIn("Vehicles · Example hatchback: Comprehensive cover: insurance planned",
                      self.page("/to-do/calendar"))
        rule = reminder_moves.rule_for(self.store.registry, BILLS, self.report.loaded)
        reminder_moves.move(self.store, rule, policy)
        page = self.page("/to-do/calendar")
        self.assertNotIn("Comprehensive cover: insurance", page)
        self.assertEqual(page.count("Comprehensive cover"), 1)
        self.assertIn("Bills and insurance · Comprehensive cover: vehicle insurance review or renewal planned", page)

    def test_the_page_has_no_script_and_the_list_in_words(self):
        page = self.page("/to-do/calendar")
        part = page[page.index('class="cal-wrap"'):page.index("</section>", page.index('class="cal-wrap"'))]
        self.assertNotIn("<script", part)
        self.assertIn('<details class="cal-list" data-print-open open>', part)
        self.assertEqual(part.count('aria-current="date"'), 1)
        self.assertIn('href="#cal-together-d-2026-11-20"', part)


class PrivacyTests(MoreCalendarsCase):
    def test_private_fields_and_bill_amounts_never_reach_a_calendar(self):
        client = self.client()
        pages = [self.page(p, client) for p in ("/to-do/calendar", "/to-do/calendar?only=bills_insurance",
                                                "/to-do/calendar?only=vehicles", f"/calendar/{BILLS}",
                                                f"/calendar/{CARS}", f"/calendar/{SERVICES}")]
        for page in pages:
            for secret in (PLATE, AMOUNT, "43219", COVERS, REFERENCE, NOTE):
                self.assertNotIn(secret, page)
        self.assertIn("Example electricity: bill check due today", pages[3])


class PagesAndModulesOffTests(MoreCalendarsCase):
    def test_each_calendar_has_its_own_page_and_home_care_jobs_show_their_month(self):
        page = self.page(f"/calendar/{GARDEN}")
        self.assertIn("<caption>Garden calendar, November 2026</caption>", page)
        self.assertIn("Plant garlic: job planned", page)
        job = self.page(f"/t/{JOBS}/{self.gutters}")
        self.assertIn("Home care calendar", job)
        self.assertIn(f'href="/calendar/{WORK}?subject={self.gutters}">Open the home care calendar</a>', job)
        self.assertNotIn("Garden calendar", self.page(f"/t/{GARDEN}/{self.garlic}"),
                         "a calendar of the jobs themselves is not put on each job's page")

    def test_a_module_switched_off_is_not_shown_and_its_records_are_kept(self):
        settings.set_module_enabled(self.conn, "garden", False)
        settings.set_module_enabled(self.conn, "bills_insurance", False)
        client = self.client()
        page = self.page("/to-do/calendar", client)
        for gone in ("Vegetable garden", "Plant garlic", "Bills and insurance", "Example electricity"):
            self.assertNotIn(gone, main(page))
        self.assertIn("Home care · Clear the gutters", page)
        self.page(f"/calendar/{GARDEN}", client, status=404)
        self.assertIn("Things to do calendar", self.page("/to-do/calendar?only=garden", client))
        self.assertIsNotNone(self.store.get(GARDEN, self.garlic))

    def test_one_list_alone_keeps_its_own_calendar_and_no_show_links(self):
        for name in ("home_care", "garden", "vehicles", "bills_insurance"):
            settings.set_module_enabled(self.conn, name, False)
        page = self.page("/to-do/calendar")
        self.assertIn("<caption>Routines calendar, November 2026</caption>", page)
        self.assertNotIn('class="cal-show"', page)
