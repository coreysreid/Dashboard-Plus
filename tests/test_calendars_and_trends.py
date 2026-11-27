"""Tests for month calendars and trends on the dots chart (decision 0119): declarations, the household's day, looks, words, ranges, changes, structure and modules switched off."""
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard.core import calendars, checklist, daily, db, modules, records, settings, startup
from dashboard.web import charts
from dashboard.web.app import create_app
from dashboard.web.chart_pages import change_words, range_start

PORT = 5144
BASE = f"http://127.0.0.1:{PORT}"
SVG = "{http://www.w3.org/2000/svg}"
FEED, TIMES, ROUTINES, WEIGHTS = ("pet_feeding__servings", "routines__times", "routines__routines",
                                  "pets__weigh_ins")
SYDNEY_NOON = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)  # 20 Nov 2026, 12:00 in Sydney (daylight time)
TODAY = date(2026, 11, 20)


def chips(page: str) -> list[tuple[str, str, str]]:
    """Every mark drawn in a calendar's grid: (look, symbol, the words it stands for)."""
    return re.findall(r'<span class="cal-chip cal-(\w+)" title="([^"]*)" aria-hidden="true">([^<]+)', page)


def grid(page: str, cal_id: str) -> str:
    begin = page.index(f'<section class="cal-wrap" id="{cal_id}"')
    return page[begin:page.index("</table>", begin)]


class DeclarationTests(TempDirTestCase):
    """The module checker explains a wrong `calendar` and wrong trend settings in plain words."""
    TABLES = '''[tables.tasks]
title = "Tasks"
columns.name = { type = "text", required = true }
columns.next_due = { type = "date" }
columns.paused = { type = "boolean" }

[tables.tasks.watch]
expiring = { date = "next_due", warn_days = 7, wording = "due", where = { paused = false } }

[tables.plain]
title = "Plain"
columns.name = { type = "text", required = true }

[tables.times]
title = "Times"
columns.task = { type = "link", to = "tasks", required = true, on_delete = "cascade" }
columns.other = { type = "link", to = "plain", required = true, on_delete = "cascade" }
columns.outcome = { type = "choice", required = true, choices = ["done", "skipped", "partly"] }
columns.secret = { type = "choice", required = true, sensitive = true, choices = ["a", "b"] }
columns.on = { type = "date", required = true }
columns.at = { type = "datetime" }
columns.weight = { type = "decimal", required = true, unit = "kg" }
columns.note = { type = "text" }
'''

    def load(self, extra: str):
        return modules.load_module(self.make_module(tables=self.TABLES + extra, labels=None))

    def problems(self, extra: str) -> str:
        with self.assertRaises(modules.ModuleError) as caught:
            self.load(extra)
        return str(caught.exception)

    def test_a_good_calendar_and_good_trends_are_kept(self):
        module = self.load('calendar = { when = "on", per = "task", show = "all", title = "Task calendar", '
                           'entry = ["time", "times"], state = "outcome", looks = { done = "done", skipped = '
                           '"skipped", partly = "recorded" }, due = true }\n'
                           'chart = { kind = "dots", x = "on", y = "weight", per = "task", what = ["weight", '
                           '"weights"], entry = ["reading", "readings"], subject = "task", ranges = ["3m", "all"], '
                           'change = true, line = { gap_days = 90 }, scale = "fitted" }\n')
        rule = module.tables["times"].calendar
        self.assertEqual((rule["show"], rule["due"], rule["looks"]["partly"]), ("all", True, "recorded"))
        chart = module.tables["times"].chart
        self.assertEqual((chart["ranges"], chart["change"], chart["line"], chart["gap_days"], chart["scale"]),
                         (["3m", "all"], True, True, 90, "fitted"))
        plain = self.load('calendar = { when = "on", per = "other", show = "one", title = "Plain", '
                          'entry = ["entry", "entries"] }\n').tables["times"].calendar
        self.assertEqual((plain["look"], plain["due"], plain["state"]), ("recorded", False, None))

    def test_wrong_calendars_are_explained(self):
        text = self.problems('calendar = { when = "at", per = "outcome", show = "some", title = " ", '
                             'entry = ["one"], colour = "red", look = "missed" }\n')
        for words in ("'when' must name a required date or date-and-time column",
                      "'per' must name a required link column", "'show' must be \"one\"", "'title' must be",
                      "'entry' must be two words", "unknown setting 'colour'", "'look' must be \"recorded\""):
            self.assertIn(words, text)

    def test_states_need_a_look_each_from_the_fixed_set(self):
        text = self.problems('calendar = { when = "on", per = "task", show = "all", title = "T", entry = ["a", '
                             '"b"], state = "outcome", looks = { done = "done", skipped = "red" } }\n')
        self.assertIn("'looks' must give each choice of 'outcome' (done, skipped, partly) one of the looks", text)
        text = self.problems('calendar = { when = "on", per = "task", show = "all", title = "T", entry = ["a", '
                             '"b"], state = "secret", looks = { a = "done", b = "done" } }\n')
        self.assertIn("'state' must name a required choice column of this table that is not private", text)
        text = self.problems('calendar = { when = "on", per = "task", show = "all", title = "T", entry = ["a", '
                             '"b"], looks = { done = "done" } }\n')
        self.assertIn("'looks' needs 'state'", text)

    def test_due_needs_a_reminder_with_due_wording_in_this_module(self):
        text = self.problems('calendar = { when = "on", per = "other", show = "all", title = "T", entry = ["a", '
                             '"b"], due = true }\n')
        self.assertIn("'due = true' shows the open due date of the record 'other' points at", text)
        self.assertIn("'due' must be true or false", self.problems(
            'calendar = { when = "on", per = "task", show = "all", title = "T", entry = ["a", "b"], due = "yes" }\n'))

    def test_wrong_trend_settings_are_explained(self):
        text = self.problems('chart = { kind = "dots", x = "on", y = "weight", per = "task", what = ["w", "ws"], '
                             'entry = ["r", "rs"], subject = "task", ranges = ["6m", "all", "all"], change = "yes", '
                             'line = { gap_days = 0 }, scale = "log" }\n')
        for words in ("'ranges' must list some of \"3m\", \"1y\" and \"all\", each once",
                      "'change' must be true or false", "'line' must be true, false or { gap_days = 365 }",
                      "'scale' must be \"zero\""):
            self.assertIn(words, text)

    def test_shipped_modules_declare_what_this_decision_describes(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        tables = {f"{m.name}__{t.name}": t for m in found for t in m.tables.values()}
        self.assertEqual(tables[FEED].calendar["show"], "one")
        self.assertFalse(tables[FEED].calendar["due"], "an empty feeding day is never due or missed")
        self.assertTrue(tables[TIMES].calendar["due"])
        weights = tables[WEIGHTS].chart
        self.assertEqual((weights["ranges"], weights["change"], weights["line"], weights["scale"]),
                         (["3m", "1y", "all"], True, True, "zero"), "pet weights keep a scale from zero")


class CalendarTestCase(TempDirTestCase):
    MODULES = ("people", "stock", "pets", "pet_feeding", "routines")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        settings.put(self.conn, daily.ZONE_KEY, "Australia/Sydney")
        settings.put(self.conn, checklist.WEEK_START_KEY, "monday")
        self.rex = self.store.create("pets__pets", {"name": "Rex", "species": "dog"})

    def feed(self, at, pet=None, **values):
        return self.store.create(FEED, {"pet": pet or self.rex, "given_at": at, "kind": "bowl",
                                        "food": "Example dry food", **values})

    def routine(self, name, next_due, paused=False):
        return self.store.create(ROUTINES, {"name": name, "repeat_count": 1, "repeat_unit": "weeks",
                                            "next_due": next_due, "paused": paused})

    def time(self, routine, on, outcome="done"):
        return self.store.create(TIMES, {"routine": routine, "outcome": outcome, "done_on": on})

    def month(self, table, year=2026, month=11, subject=None, today=TODAY, first_day="monday"):
        return calendars.month(self.conn, self.registry, self.registry[table], year, month, today, first_day, subject)

    def client(self, now=SYDNEY_NOON, today=TODAY):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: now
        app.config["TODAY"] = lambda: today
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, path, client=None, status=200):
        response = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)


class DayBoundaryTests(CalendarTestCase):
    def days_with(self, found):
        return {d.day.isoformat(): [m.record_id for m in d.marks] for d in found.days if d.marks}

    def test_a_typed_time_is_the_households_clock_and_an_offset_is_an_instant(self):
        late = self.feed("2026-11-19T23:30")  # typed: Sydney's own 23:30 on the 19th
        sent = self.feed("2026-11-19T13:30:00+00:00")  # 13:30 UTC is 00:30 on the 20th in Sydney
        self.assertEqual(self.days_with(self.month(FEED, subject=self.rex)), {"2026-11-19": [late],
                                                                              "2026-11-20": [sent]})

    def test_an_entry_near_midnight_at_the_month_edge_counts_in_the_households_month(self):
        edge = self.feed("2026-10-31T14:00:00+00:00")  # 1 November, 01:00 in Sydney
        self.assertEqual(self.days_with(self.month(FEED, subject=self.rex)), {"2026-11-01": [edge]})
        self.assertEqual(self.days_with(self.month(FEED, month=10, subject=self.rex)), {})
        settings.put(self.conn, daily.ZONE_KEY, "America/Los_Angeles")  # the same instant is 31 October there
        self.assertEqual(self.days_with(self.month(FEED, month=10, subject=self.rex)), {"2026-10-31": [edge]})

    def test_the_daylight_saving_change_keeps_each_entry_on_its_day(self):
        # Sydney's clocks went forward at 2:00 on 4 October 2026; 15:30 UTC on the 3rd is 01:30 on the 4th there.
        before = self.feed("2026-10-03T15:30:00+00:00")
        after = self.feed("2026-10-04T13:30:00+00:00")  # 00:30 on the 5th in daylight time
        self.assertEqual(self.days_with(self.month(FEED, month=10, subject=self.rex)),
                         {"2026-10-04": [before], "2026-10-05": [after]})

    def test_only_accepted_undeleted_records_of_this_subject_are_marked(self):
        luna = self.store.create("pets__pets", {"name": "Luna", "species": "cat"})
        kept, gone = self.feed("2026-11-02T08:00"), self.feed("2026-11-03T08:00")
        self.feed("2026-11-04T08:00", pet=luna)
        self.store.delete(FEED, gone)
        self.assertEqual(self.days_with(self.month(FEED, subject=self.rex)), {"2026-11-02": [kept]})

    def test_weeks_start_on_the_households_day_and_the_grid_is_whole_weeks(self):
        weeks = calendars.grid(2026, 11, "monday")
        self.assertEqual(weeks[0][:6], [None] * 6)  # 1 November 2026 is a Sunday
        self.assertEqual(weeks[0][6], date(2026, 11, 1))
        self.assertEqual(calendars.grid(2026, 11, "sunday")[0][0], date(2026, 11, 1))
        self.assertTrue(all(len(w) == 7 for w in weeks))
        self.assertEqual(calendars.shift(2026, 1, -1), (2025, 12))
        self.assertEqual(calendars.shift(2026, 12, 1), (2027, 1))
        settings.put(self.conn, checklist.WEEK_START_KEY, "sunday")
        page = self.page("/to-do/calendar")
        self.assertRegex(page, r'<thead><tr><th scope="col"><span aria-hidden="true">Sun</span>'
                               r'<span class="vh">Sunday</span></th>')


class LookTests(CalendarTestCase):
    def test_every_look_has_a_colour_a_symbol_and_more_than_colour(self):
        css = (ROOT / "src" / "dashboard" / "web" / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertEqual(len(set(calendars.SYMBOLS[look] for look in calendars.LOOKS)), len(calendars.LOOKS))
        for look in calendars.LOOKS:
            rule = re.search(rf"\.cal-{look} \{{([^}}]*)\}}", css).group(1)
            self.assertIn("border-color", rule, look)
            self.assertIn("background", rule, look)
        for look, extra in (("skipped", "repeating-linear-gradient"), ("skipped", "dotted"), ("due", "dashed"),
                            ("planned", "dashed")):
            self.assertIn(extra, re.search(rf"\.cal-{look} \{{([^}}]*)\}}", css).group(1))
        for rule in ("@media (prefers-color-scheme: dark)", "--cal-due:", "print-color-adjust: exact",
                     "@media (forced-colors: active) { .cal-chip"):
            self.assertIn(rule, css)
        self.assertNotIn("animation", css[css.index("/* Month calendars"):css.index("    footer {")])

    def test_routines_show_done_skipped_due_and_planned_each_with_words_and_symbol(self):
        bins = self.routine("Put the bins out", "2026-11-13")
        plants = self.routine("Water the pot plants", "2026-11-20")
        filters = self.routine("Clean the filter", "2026-11-27")
        self.time(bins, "2026-11-06")
        self.time(plants, "2026-11-13", "skipped")
        page = self.page("/to-do/calendar")
        drawn = {(look, symbol) for look, _, symbol in chips(page)}
        self.assertEqual(drawn, {("done", "✓"), ("skipped", "–"), ("due", "○"), ("planned", "◇")})
        for look, words, _ in chips(page):
            self.assertTrue(words, f"{look} has its words")
        self.assertIn('<span class="vh">6 November: Done</span>', page)
        self.assertIn('<span class="vh">13 November: Skipped this time; Due, not recorded as done yet</span>', page)
        self.assertIn('<span class="vh">20 November, today: Due today</span>', page)
        self.assertIn('<span class="vh">27 November: Planned</span>', page)
        self.assertIn("Put the bins out: due since 13/11/26, not recorded as done yet", page)
        self.assertIn(f'href="/t/{ROUTINES}/{filters}">Clean the filter: planned</a>', page)
        legend = page[page.index('class="cal-legend"'):page.index("</ul>", page.index('class="cal-legend"'))]
        for words in ("Done", "Skipped this time", "Due, not recorded as done yet: shown once, on its own date",
                      "Planned date"):
            self.assertIn(words, legend)

    def test_a_late_routine_is_due_once_and_the_days_since_are_blank(self):
        self.routine("Put the bins out", "2026-11-02")
        found = self.month(TIMES)
        marked = [d.day.isoformat() for d in found.days if d.marks]
        self.assertEqual(marked, ["2026-11-02"], "three late weeks are one due date, not a pile of missed ones")
        self.assertNotIn("issed", " ".join(w for _, w, _ in chips(self.page("/to-do/calendar"))))

    def test_a_paused_or_deleted_routine_has_no_due_mark_but_its_history_stays(self):
        paused = self.routine("Clean the pool", "2026-11-10", paused=True)
        gone = self.routine("Old job", "2026-11-11")
        self.time(paused, "2026-11-03")
        self.store.delete(ROUTINES, gone)
        found = self.month(TIMES)
        self.assertEqual([(d.day.day, [m.look for m in d.marks]) for d in found.days if d.marks], [(3, ["done"])])

    def test_one_routines_own_page_shows_only_its_own_marks(self):
        bins = self.routine("Put the bins out", "2026-11-27")
        other = self.routine("Water the pot plants", "2026-11-25")
        self.time(bins, "2026-11-06")
        self.time(other, "2026-11-07")
        page = self.page(f"/t/{ROUTINES}/{bins}")
        part = page[page.index(f'id="cal-{TIMES}-{bins}"'):]
        self.assertIn("Put the bins out: Done", part)
        self.assertNotIn("Water the pot plants", part)
        self.assertIn(f'href="/calendar/{TIMES}?subject={bins}">Open the routines calendar</a>', part)


class EmptyDayTests(CalendarTestCase):
    def test_an_empty_feeding_month_says_no_entry_and_never_missed(self):
        page = self.page(f"/calendar/{FEED}?subject={self.rex}")
        self.assertIn("No feeding entry recorded for Rex in November 2026.", page)
        self.assertIn("A blank day has no feeding entry recorded. It does not mean anything was missed.", page)
        self.assertEqual(chips(page), [])
        main = page[page.index("<main>"):page.index("</main>")]
        text = re.sub(r"<[^>]+>", " ", main).replace("does not mean anything was missed", "")
        for word in ("missed", "Missed", "not fed", "streak", "late"):
            self.assertNotIn(word, text)

    def test_a_day_with_feedings_shows_the_count_and_the_totals_by_unit(self):
        self.feed("2026-11-18T07:15", amount=120, unit="g")
        self.feed("2026-11-18T18:10", amount=1, unit="pouch")
        page = self.page(f"/calendar/{FEED}?subject={self.rex}")
        self.assertEqual(chips(page), [("recorded", "2 feedings recorded", "●")])
        self.assertIn('<span class="cal-n">2</span>', page)
        self.assertIn("2 feedings recorded · 120 g and 1 pouch put out", page)
        self.assertIn(f"/daily/{FEED}?subject={self.rex}&amp;day=2026-11-18", page)
        self.assertIn("7:15 am · Feeding recorded", page)
        self.assertIn("November 2026 · Rex · 2 feedings recorded", page)

    def test_an_empty_routines_month_says_nothing_recorded_or_planned(self):
        page = self.page("/to-do/calendar?month=2026-09")
        self.assertIn("Nothing recorded or planned in September 2026.", page)
        self.assertIn("earlier times are never filled in as missed", page)


class StructureTests(CalendarTestCase):
    def test_the_grid_is_a_captioned_table_with_named_days_and_an_equal_list(self):
        self.feed("2026-11-18T07:15")
        page = self.page(f"/calendar/{FEED}?subject={self.rex}")
        table = grid(page, f"cal-{FEED}-{self.rex}")
        self.assertIn("<caption>Feeding calendar for Rex, November 2026</caption>", table)
        self.assertEqual(len(re.findall(r'<th scope="col">', table)), 7)
        for name in ("Monday", "Sunday"):
            self.assertIn(f'<span class="vh">{name}</span>', table)
        self.assertEqual(table.count('aria-current="date"'), 1)
        self.assertIn('<span class="vh">20 November, today</span>', table)
        self.assertIn(f'href="#cal-{FEED}-{self.rex}-d-2026-11-18"', table)
        self.assertIn(f'<li id="cal-{FEED}-{self.rex}-d-2026-11-18">', page)
        self.assertIn('<details class="cal-list" data-print-open open>', page)
        self.assertIn('aria-label="Choose the month: Feeding calendar"', page)
        self.assertNotIn("<script", page[page.index('class="cal-wrap"'):page.index("</section>",
                                                                                     page.index('class="cal-wrap"'))])

    def test_previous_and_next_month_and_how_far_ahead(self):
        page = self.page(f"/calendar/{FEED}?subject={self.rex}")
        self.assertIn(f'href="/calendar/{FEED}?subject={self.rex}&amp;month=2026-10" rel="prev"', page)
        self.assertIn(f'href="/calendar/{FEED}?subject={self.rex}&amp;month=2026-12" rel="next"', page)
        page = self.page(f"/calendar/{FEED}?subject={self.rex}&month=2027-11")
        self.assertIn("November 2027", page)
        self.assertNotIn('rel="next"', page, "twelve months ahead is the last one offered")
        self.assertIn(">Go to the current month</a>", page)
        for wrong in ("2028-01", "2026-13", "soon", "0999-01"):
            self.assertIn("November 2026", self.page(f"/calendar/{FEED}?subject={self.rex}&month={wrong}"))

    def test_the_pet_page_and_the_daily_page_link_to_the_calendar(self):
        self.feed("2026-11-20T07:15")
        page = self.page(f"/t/pets__pets/{self.rex}")
        self.assertIn("<h2>Feeding calendar</h2>", page)
        self.assertIn('<details class="cal-list" data-print-open>', page, "on the pet's page the words are one tap away")
        self.assertIn(f'href="/calendar/{FEED}?subject={self.rex}">Open the feeding calendar</a>', page)
        self.assertIn(f"/calendar/{FEED}?subject={self.rex}&amp;month=2026-11", self.page(f"/daily/{FEED}"))

    def test_things_to_do_has_a_calendar_tab(self):
        page = self.page("/to-do")
        self.assertIn('<a href="/to-do/calendar">Calendar</a>', page)
        page = self.page("/to-do/calendar")
        self.assertIn('<a href="/to-do/calendar" aria-current="page">Calendar</a>', page)
        self.assertIn("<caption>Routines calendar, November 2026</caption>", page)


class ModuleOffTests(CalendarTestCase):
    def test_switched_off_there_is_no_calendar_page_tab_or_panel_and_records_are_kept(self):
        entry = self.feed("2026-11-20T07:15")
        settings.set_module_enabled(self.conn, "pet_feeding", False)
        settings.set_module_enabled(self.conn, "routines", False)
        client = self.client()
        self.page(f"/calendar/{FEED}", client, status=404)
        self.page(f"/calendar/{TIMES}", client, status=404)
        self.page("/to-do/calendar", client, status=404)
        self.assertNotIn("/to-do/calendar", self.page("/to-do", client))
        self.assertNotIn("Feeding calendar", self.page(f"/t/pets__pets/{self.rex}", client))
        settings.set_module_enabled(self.conn, "pet_feeding", True)
        self.assertIn("Feeding calendar", self.page(f"/t/pets__pets/{self.rex}", self.client()))
        self.assertIsNotNone(self.store.get(FEED, entry))

    def test_an_unknown_or_undeclared_table_has_no_calendar(self):
        self.page("/calendar/pets__pets", status=404)
        self.page("/calendar/nothing_here", status=404)


class TrendTests(CalendarTestCase):
    def weigh(self, day, weight):
        return self.store.create(WEIGHTS, {"pet": self.rex, "day": day, "weight": weight})

    def test_range_presets_start_on_the_same_day_or_the_months_last(self):
        self.assertEqual(range_start("3m", date(2026, 11, 20)), "2026-08-20")
        self.assertEqual(range_start("3m", date(2026, 5, 31)), "2026-02-28")
        self.assertEqual(range_start("1y", date(2028, 2, 29)), "2027-02-28")
        self.assertEqual(range_start("1y", date(2026, 1, 15)), "2025-01-15")
        self.assertIsNone(range_start("all", date(2026, 1, 15)))

    def test_change_words_say_up_down_or_no_change_with_units(self):
        decimal = self.registry[WEIGHTS].table.columns["weight"]
        self.assertEqual(change_words(decimal, {"value": 4.4}, {"value": 4.7}, "kg"), "up 0.3 kg, from 4.4 kg to 4.7 kg")
        self.assertEqual(change_words(decimal, {"value": 4.8}, {"value": 4.4}, "kg"),
                         "down 0.4 kg, from 4.8 kg to 4.4 kg")
        self.assertEqual(change_words(decimal, {"value": 4.4}, {"value": 4.4}, "kg"), "no change (4.4 kg both times)")
        whole = modules.Column("distance", "integer")
        self.assertEqual(change_words(whole, {"value": 47300}, {"value": 48500}, "km"),
                         "up 1,200 km, from 47,300 km to 48,500 km")

    def test_the_page_offers_presets_and_says_the_change_since_the_last_and_the_first_reading(self):
        self.weigh("2025-06-01", 18.0)
        self.weigh("2026-09-01", 19.4)
        self.weigh("2026-10-01", 20.1)
        self.weigh("2026-11-15", 19.9)
        page = self.page(f"/charts/{WEIGHTS}?subject={self.rex}")
        self.assertIn(f'<a href="/charts/{WEIGHTS}?subject={self.rex}&amp;range=all" aria-current="page">All dates</a>',
                      page)
        self.assertIn("Since the reading before, on 01/10/26: down 0.2 kg, from 20.1 kg to 19.9 kg.", page)
        self.assertIn("Since the first reading, on 01/06/25: up 1.9 kg, from 18 kg to 19.9 kg.", page)
        page = self.page(f"/charts/{WEIGHTS}?subject={self.rex}&range=3m")
        self.assertIn('aria-current="page">Last 3 months</a>', page)
        self.assertIn("20/08/26 to today (the last 3 months)", page)
        self.assertIn("Since the start of this period, on 01/09/26: up 0.5 kg, from 19.4 kg to 19.9 kg.", page)
        self.assertNotIn("01/06/25", page)
        page = self.page(f"/charts/{WEIGHTS}?subject={self.rex}&range=1y&from=01/10/26&to=20/11/26")
        self.assertIn("01/10/26 to 20/11/26", page, "dates typed in win over a preset")
        self.assertNotIn('aria-current="page">Last year', page)
        self.assertIn("All dates", self.page(f"/charts/{WEIGHTS}?subject={self.rex}&range=5y"))

    def test_the_line_is_only_a_guide_and_breaks_across_a_long_gap(self):
        self.weigh("2024-01-01", 17.0)
        self.weigh("2026-09-01", 19.4)
        self.weigh("2026-10-01", 20.1)
        page = self.page(f"/charts/{WEIGHTS}?subject={self.rex}")
        svg = ET.fromstring(re.search(r'<svg class="chart-svg".*?</svg>', page, flags=re.S).group(0))
        lines = svg.findall(f".//{SVG}polyline")
        self.assertEqual(len(lines), 1, "more than 365 days apart: not joined")
        self.assertEqual(len(lines[0].get("points").split()), 2)
        self.assertEqual(lines[0].get("aria-hidden"), "true")
        self.assertIn("0", [t.text for t in svg.iter(f"{SVG}text")], "the scale still starts at zero")
        self.assertIn("broken where they are more than 365 days apart", page)

    def test_one_reading_has_no_change_words_and_no_line(self):
        self.weigh("2026-11-01", 19.0)
        page = self.page(f"/charts/{WEIGHTS}?subject={self.rex}")
        self.assertNotIn("Since the", page)
        self.assertNotIn("<polyline", page)

    def test_a_fitted_scale_says_where_it_starts_and_a_zero_scale_does_not(self):
        dots = [charts.Dot(date(2026, 11, 1), 4.4, "a", "#r1"), charts.Dot(date(2026, 11, 20), 4.8, "b", "#r2")]
        fitted = ET.fromstring(str(charts.dot_chart("d", "t", "d", dots, "Date", "kg", str, line=True, fitted=True)))
        texts = [t.text for t in fitted.iter(f"{SVG}text")]
        self.assertIn("Scale starts at 4.3 kg, not 0", texts)
        self.assertNotIn("0", texts)
        zero = ET.fromstring(str(charts.dot_chart("d", "t", "d", dots, "Date", "kg", str)))
        self.assertFalse(any((t.text or "").startswith("Scale starts") for t in zero.iter(f"{SVG}text")))
        self.assertEqual(zero.findall(f".//{SVG}polyline"), [], "no line unless the chart allows it")
        self.assertEqual(charts.fitted_steps(4.4, 4.8), (4.3, 4.8, 0.1))
        self.assertEqual(charts.fitted_steps(40000, 48500)[:2], (38000, 50000))
