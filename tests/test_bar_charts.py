"""Tests for bars over time (decision 0124): declarations, periods by the household's own day, one unit at a time, empty periods never missed, the drawing, private doses and modules switched off."""
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard.core import bars, checklist, daily, db, modules, records, settings, startup
from dashboard.web.app import create_app
from test_module_medicine_doses import SECRET, TABLE as DOSES, DoseTestCase

PORT = 5149
BASE = f"http://127.0.0.1:{PORT}"
SVG = "{http://www.w3.org/2000/svg}"
FEED, TIMES, ROUTINES = "pet_feeding__servings", "routines__times", "routines__routines"
SYDNEY_NOON = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)  # Friday 20 Nov 2026, 12:00 in Sydney
TODAY = date(2026, 11, 20)


def svg_of(page: str, chart_id: str) -> ET.Element:
    begin = page.index("<svg", page.index(f'id="{chart_id}"'))
    return ET.fromstring(page[begin:page.index("</svg>", begin) + 6])


def words(page: str) -> str:
    main = page[page.index("<main>"):page.index("</main>")]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", main))


class DeclarationTests(TempDirTestCase):
    """The module checker explains a wrong `bars` declaration in plain words."""
    TABLES = '''[tables.pets]
title = "Pets"
columns.name = { type = "text", required = true }

[tables.meds]
title = "Meds"
columns.name = { type = "text", required = true }

[tables.log]
title = "Log"
columns.pet = { type = "link", to = "pets", required = true, on_delete = "cascade" }
columns.med = { type = "link", to = "meds", required = true, on_delete = "cascade" }
columns.at = { type = "datetime", required = true }
columns.on = { type = "date" }
columns.amount = { type = "decimal" }
columns.weight = { type = "decimal", unit = "kg" }
columns.cost = { type = "money" }
columns.secret = { type = "decimal", sensitive = true }
columns.unit = { type = "choice", choices = ["g", "pouch"] }
columns.outcome = { type = "choice", required = true, choices = ["done", "skipped"] }
'''
    GOOD = ('[[tables.log.bars]]\nkey = "food"\ntitle = "Food put out"\nwhen = "at"\nper = "pet"\nmeasure = "sum"\n'
            'amount = "amount"\nunit = "unit"\nverb = "put out"\nby = ["day", "month"]\nentry = ["feeding", '
            '"feedings"]\nsubject = "pet"\n\n[[tables.log.bars]]\nkey = "done"\ntitle = "Times done"\nwhen = "at"\n'
            'per = "pet"\nmeasure = "count"\nwhere = { outcome = "done" }\ngroup = "med"\nby = ["week"]\n'
            'entry = ["time", "times"]\nsubject = "pet"\n\n[[tables.log.bars]]\nkey = "weight"\ntitle = "Weight"\n'
            'when = "at"\nper = "pet"\nmeasure = "sum"\namount = "weight"\nverb = "recorded"\nby = ["month"]\n'
            'entry = ["reading", "readings"]\nsubject = "pet"\n')

    def load(self, extra: str, private: bool = False):
        tables = self.TABLES.replace('title = "Log"', 'title = "Log"\nprivate = true\nsuggestions = false') \
            if private else self.TABLES
        return modules.load_module(self.make_module(tables=tables + extra, labels=None))

    def problems(self, extra: str, private: bool = False) -> str:
        with self.assertRaises(modules.ModuleError) as caught:
            self.load(extra, private)
        return str(caught.exception)

    def test_good_bars_are_kept_with_a_fixed_unit_where_the_column_has_one(self):
        found = self.load(self.GOOD).tables["log"].bars
        self.assertEqual([b["key"] for b in found], ["food", "done", "weight"])
        self.assertEqual((found[0]["measure"], found[0]["unit"], found[0]["by"]), ("sum", "unit", ["day", "month"]))
        self.assertEqual((found[1]["where"], found[1]["group"]), ({"outcome": "done"}, "med"))
        self.assertEqual(found[2]["fixed_unit"], "kg")

    def test_wrong_bars_are_explained(self):
        text = self.problems('[[tables.log.bars]]\nkey = "Bad Key"\ntitle = " "\nwhen = "on"\nper = "amount"\n'
                             'measure = "average"\nby = ["year", "day", "day"]\nentry = ["one"]\ncolour = "red"\n'
                             'where = { outcome = "maybe" }\ngroup = "on"\n')
        for said in ("each chart needs its own 'key'", "'title' must be what the bars show",
                     "'when' must name a required date or date-and-time column",
                     "'per' must name a required link column", "'measure' must be \"count\"",
                     "'by' must list some of \"day\", \"week\" and \"month\", each once",
                     "'entry' must be two words", "'subject' must be the word for one subject",
                     "unknown setting 'colour'", "'where' names choice columns of this table that are not private",
                     "'group' must name another required link column"):
            self.assertIn(said, text)

    def test_a_sum_needs_an_ordinary_number_and_one_unit(self):
        base = ('[[tables.log.bars]]\nkey = "k"\ntitle = "T"\nwhen = "at"\nper = "pet"\nmeasure = "sum"\n'
                'by = ["day"]\nentry = ["a", "b"]\nsubject = "pet"\n')
        self.assertIn("a sum needs a unit", self.problems(base + 'amount = "amount"\nverb = "v"\n'))
        # Decision 0128: a private amount is added up only after a pressed Show, and money in whole units.
        secret = self.load(base + 'amount = "secret"\nunit = "unit"\nverb = "v"\n').tables["log"].bars[0]
        self.assertEqual((secret["hidden"], secret["money"]), (True, False))
        cost = self.load(base + 'amount = "cost"\nunit = "unit"\nverb = "v"\n').tables["log"].bars[0]
        self.assertEqual((cost["hidden"], cost["money"]), (False, True))
        self.assertIn("'amount' must name a number or money column", self.problems(base + 'amount = "on"\n'
                                                                                         'unit = "unit"\nverb = "v"\n'))
        self.assertIn("'verb' must be the words after an amount", self.problems(base + 'amount = "amount"\n'
                                                                                       'unit = "unit"\n'))
        count = base.replace('"sum"', '"count"')
        self.assertIn("'amount' only applies to measure = \"sum\"", self.problems(count + 'amount = "amount"\n'))

    def test_a_private_tables_bars_only_count_every_entry(self):
        base = ('[[tables.log.bars]]\nkey = "k"\ntitle = "T"\nwhen = "at"\nper = "pet"\nby = ["day"]\n'
                'entry = ["a", "b"]\nsubject = "pet"\n')
        text = self.problems(base + 'measure = "sum"\namount = "amount"\nunit = "unit"\nverb = "v"\n', private=True)
        self.assertIn("a private table's bars can only count entries", text)
        text = self.problems(base + 'measure = "count"\nwhere = { outcome = "done" }\n', private=True)
        self.assertIn("a private table's bars can't use 'where'", text)
        kept = self.load(base + 'measure = "count"\ngroup = "med"\n', private=True).tables["log"].bars
        self.assertEqual(kept[0]["group"], "med")

    def test_shipped_modules_declare_what_this_decision_describes(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        tables = {f"{m.name}__{t.name}": t for m in found for t in m.tables.values()}
        food = tables[FEED].bars[0]
        self.assertEqual((food["measure"], food["amount"], food["unit"], food["by"][0]), ("sum", "amount", "unit", "day"))
        done = tables[TIMES].bars[0]
        self.assertEqual((done["measure"], done["where"], done["by"][0]), ("count", {"outcome": "done"}, "month"))
        doses = tables[DOSES].bars[0]
        self.assertEqual((doses["measure"], doses["group"], doses["by"][0]), ("count", "medication", "week"))
        self.assertFalse(tables["vehicle_running__readings"].bars, "no distance travelled is ever worked out (0111)")


class BarsTestCase(TempDirTestCase):
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

    def feed(self, at, amount=None, unit=None, pet=None):
        values = {"pet": pet or self.rex, "given_at": at, "kind": "bowl", "food": "Example dry food"}
        if amount is not None:
            values.update(amount=amount, unit=unit)
        return self.store.create(FEED, values)

    def rule(self, table=FEED):
        return self.registry[table].table.bars[0]

    def build(self, by="day", last=TODAY, table=FEED, subject=None):
        return bars.build(self.conn, self.registry[table], self.rule(table), subject or self.rex, by, last,
                          "monday", TODAY)

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: SYDNEY_NOON
        app.config["TODAY"] = lambda: TODAY
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None, status=200):
        response = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)


class PeriodTests(BarsTestCase):
    def test_days_weeks_and_months_end_with_the_one_holding_today(self):
        days = self.build("day")
        self.assertEqual((len(days), days[0].start, days[-1].start, days[-1].so_far),
                         (14, date(2026, 11, 7), TODAY, True))
        weeks = self.build("week")
        self.assertEqual((len(weeks), weeks[-1].start, weeks[-1].end), (12, date(2026, 11, 16), date(2026, 11, 22)))
        self.assertTrue(all(w.start.weekday() == 0 for w in weeks), "weeks start on the household's Monday")
        sunday = bars.periods("week", TODAY, "sunday", TODAY)
        self.assertEqual(sunday[-1].start, date(2026, 11, 15))
        months = self.build("month")
        self.assertEqual((months[0].start, months[-1].start, months[-1].end),
                         (date(2025, 12, 1), date(2026, 11, 1), date(2026, 11, 30)))
        earlier = self.build("month", last=date(2026, 3, 15))
        self.assertFalse(earlier[-1].so_far)

    def test_an_offset_counts_on_the_households_day_and_a_typed_time_as_typed(self):
        late = self.feed("2026-11-19T23:30", 100, "g")  # Sydney's own 23:30 on the 19th
        sent = self.feed("2026-11-19T13:30:00+00:00", 50, "g")  # 00:30 on the 20th in Sydney
        by_day = {p.start.isoformat(): [e["id"] for e in p.entries] for p in self.build() if p.entries}
        self.assertEqual(by_day, {"2026-11-19": [late], "2026-11-20": [sent]})
        settings.put(self.conn, daily.ZONE_KEY, "America/Los_Angeles")
        by_day = {p.start.isoformat(): [e["id"] for e in p.entries] for p in self.build() if p.entries}
        self.assertEqual(by_day, {"2026-11-19": [sent, late]}, "05:30 there, before 23:30")

    def test_only_accepted_undeleted_records_of_this_subject_count(self):
        luna = self.store.create("pets__pets", {"name": "Luna", "species": "cat"})
        kept, gone = self.feed("2026-11-18T08:00", 100, "g"), self.feed("2026-11-18T09:00", 100, "g")
        self.feed("2026-11-18T10:00", 100, "g", pet=luna)
        self.store.delete(FEED, gone)
        self.conn.execute(f"UPDATE {FEED} SET review_status = 'suggested' WHERE id = ?", (kept,))
        self.assertEqual(sum(p.count for p in self.build()), 0)
        self.conn.execute(f"UPDATE {FEED} SET review_status = 'confirmed' WHERE id = ?", (kept,))
        self.assertEqual([e["id"] for p in self.build() for e in p.entries], [kept])

    def test_amounts_add_up_in_one_unit_only_and_no_amount_is_never_zero(self):
        self.feed("2026-11-18T07:00", 120, "g")
        self.feed("2026-11-18T18:00", 120.5, "g")
        self.feed("2026-11-18T19:00", 1, "pouch")
        self.feed("2026-11-18T20:00")
        day = next(p for p in self.build() if p.start == date(2026, 11, 18))
        part = bars.amounts(self.rule(), day, "g")
        self.assertEqual((str(part.total), part.added, part.unmeasured, {k: float(v) for k, v in part.others.items()}),
                         ("240.5", 2, 1, {"pouch": 1.0}))
        self.assertEqual(bars.units(self.rule(), self.build()), ["pouch", "g"], "the latest entry's unit first")


class FeedingPageTests(BarsTestCase):
    def test_the_bars_are_in_one_unit_and_say_the_others_and_the_missing_amounts(self):
        self.feed("2026-11-18T07:00", 120, "g")
        self.feed("2026-11-18T18:00", 120, "g")
        self.feed("2026-11-19T07:00", 1, "pouch")
        self.feed("2026-11-20T07:00")
        self.feed("2026-11-20T09:00", 80, "g")
        page = self.page(f"/bars/{FEED}/food?subject={self.rex}")
        text = words(page)
        self.assertIn("Rex · 14 days, 07/11/26 to today · 320 g put out, from 3 feedings", text)
        self.assertIn("1 feeding has no amount, so it is counted but not added.", text)
        self.assertIn("Also recorded in another unit, not added and never converted: 1 pouch.", text)
        self.assertIn("Food put out, not necessarily eaten.", text)
        self.assertIn("Wednesday 18/11/26 240 g put out 2 feedings recorded", text)
        self.assertIn("Thursday 19/11/26 none in g 1 feeding recorded · also 1 pouch, not in this chart", text)
        self.assertIn("Friday 20/11/26 (so far) 80 g put out 2 feedings recorded · 1 with no amount", text)
        self.assertIn("Saturday 07/11/26 Nothing recorded", text)
        self.assertIn(f'href="/daily/{FEED}?subject={self.rex}&amp;day=2026-11-18">See this day</a>', page)
        self.assertIn(f'href="/bars/{FEED}/food?subject={self.rex}&amp;by=day&amp;unit=pouch"', page)
        pouch = words(self.page(f"/bars/{FEED}/food?subject={self.rex}&unit=pouch"))
        self.assertIn("1 pouch put out, from 1 feeding", pouch)
        self.assertIn("Also recorded in another unit, not added and never converted: 320 g.", pouch)

    def test_an_empty_period_is_nothing_recorded_and_never_missed(self):
        self.feed("2026-10-02T07:00", 100, "g")
        text = words(self.page(f"/bars/{FEED}/food?subject={self.rex}"))
        self.assertIn("Nothing recorded for Rex in these 14 days, 07/11/26 to today.", text)
        cleaned = text.replace("it does not mean anything was missed", "")
        for word in ("missed", "Missed", "not fed", "streak", "late", " 0 g put out"):
            self.assertNotIn(word, cleaned)
        luna = self.store.create("pets__pets", {"name": "Luna", "species": "cat"})
        self.assertIn("No feedings recorded for Luna yet.", words(self.page(f"/bars/{FEED}/food?subject={luna}")))

    def test_the_drawing_is_labelled_from_zero_with_words_for_every_bar_and_no_script(self):
        self.feed("2026-11-18T07:00", 1250, "g")
        self.feed("2026-11-20T07:00", 100, "g")
        page = self.page(f"/bars/{FEED}/food?subject={self.rex}")
        chart_id = f"bars-{FEED}-food-{self.rex}"
        svg = svg_of(page, chart_id)
        self.assertEqual(svg.get("role"), "group")
        self.assertEqual(svg.find(f"{SVG}title").text, "Rex: food put out per day in g")
        self.assertIn("on a scale starting at 0", svg.find(f"{SVG}desc").text)
        marks = svg.findall(f"{SVG}a")
        self.assertEqual(len(marks), 14)
        labels = [m.get("aria-label") for m in marks]
        self.assertIn("Wednesday 18/11/26: 1,250 g", labels)
        self.assertIn("Friday 20/11/26 (so far): 100 g so far", labels)
        self.assertIn("Saturday 07/11/26: nothing recorded", labels)
        for mark in marks:  # every bar goes to its own row of the table
            self.assertIn(f'<tr id="{mark.get("href")[1:]}"', page)
        rects = [r for r in svg.iter(f"{SVG}rect") if (r.get("class") or "x").split()[0] == "chart-bar"]
        self.assertEqual(len(rects), 2, "one bar for each period with an amount")
        self.assertIn("url(#", next(r for r in rects if "chart-bar-so-far" in r.get("class")).get("style"))
        self.assertEqual(len([r for r in svg.iter(f"{SVG}rect") if r.get("class") == "chart-none"]), 12)
        self.assertEqual(svg.findall(f".//{SVG}text")[-4].text, "0 g")
        self.assertNotIn("<script", page[page.index(f'id="{chart_id}"'):page.index("</section>",
                                                                                 page.index(f'id="{chart_id}"'))])
        self.assertIn("A striped bar is the day still going on, so far.", page)

    def test_periods_and_ranges_are_server_links_and_never_go_past_today(self):
        self.feed("2026-09-10T07:00", 100, "g")
        page = self.page(f"/bars/{FEED}/food?subject={self.rex}&by=week")
        self.assertIn('aria-current="page">By week</a>', page)
        self.assertIn(f'href="/bars/{FEED}/food?subject={self.rex}&amp;by=month&amp;unit=g">By month</a>', page)
        self.assertIn(f'href="/bars/{FEED}/food?subject={self.rex}&amp;by=week&amp;end=2026-08-30&amp;unit=g" '
                      f'rel="prev">Earlier</a>', page)
        self.assertNotIn('rel="next"', page)
        self.assertIn("Week from 07/09/26 to 13/09/26 100 g put out", words(page))
        self.assertIn(f'href="/bars/{FEED}/food?subject={self.rex}&amp;by=day&amp;end=2026-09-13&amp;unit=g">'
                      f'See these days</a>', page)
        earlier = self.page(f"/bars/{FEED}/food?subject={self.rex}&by=day&end=2026-09-13")
        self.assertIn("14 days, 31/08/26 to 13/09/26", words(earlier))
        self.assertIn('rel="next">Later</a>', earlier)
        self.assertIn(">Up to today</a>", earlier)
        future = self.page(f"/bars/{FEED}/food?subject={self.rex}&end=2027-05-01&by=bogus")
        self.assertIn("14 days, 07/11/26 to today", words(future))

    def test_the_pets_page_shows_the_bars_with_the_table_folded_and_a_link_to_the_full_page(self):
        self.feed("2026-11-19T07:00", 100, "g")
        page = self.page(f"/t/pets__pets/{self.rex}")
        self.assertIn("<h2>Food put out per day in g</h2>", page)
        self.assertIn('<details class="bars-table"><summary>Food put out for Rex · 14 days', page)
        self.assertIn(f'href="/bars/{FEED}/food?subject={self.rex}">Open food put out per day in g</a>', page)


class RoutineTests(BarsTestCase):
    def test_a_routines_page_counts_only_the_times_done_per_month(self):
        bins = self.store.create(ROUTINES, {"name": "Put the bins out", "next_due": "2026-11-27"})
        other = self.store.create(ROUTINES, {"name": "Water the plants", "next_due": "2026-11-27"})
        for on, outcome in (("2026-11-02", "done"), ("2026-11-09", "done"), ("2026-11-16", "skipped"),
                            ("2026-10-05", "done")):
            self.store.create(TIMES, {"routine": bins, "outcome": outcome, "done_on": on})
        self.store.create(TIMES, {"routine": other, "outcome": "done", "done_on": "2026-11-03"})
        page = self.page(f"/t/{ROUTINES}/{bins}")
        text = words(page)
        self.assertIn("Times done per month", text)
        self.assertIn("Put the bins out · 12 months, 01/12/25 to today · 3 times done recorded", text)
        self.assertIn("November 2026 (so far) 2 times done recorded", text)
        self.assertIn("October 2026 1 time done recorded", text)
        svg = svg_of(page, f"bars-{TIMES}-done-{bins}")
        axis = [t.text for t in svg.iter(f"{SVG}text") if t.text and t.text[0].isdigit()]
        self.assertEqual(axis[-3:], ["0", "1", "2"], "a count's scale is whole times, from zero")


class SwitchedOffTests(BarsTestCase):
    def test_switched_off_there_is_no_page_or_panel_and_records_are_kept(self):
        entry = self.feed("2026-11-20T07:15", 100, "g")
        settings.set_module_enabled(self.conn, "pet_feeding", False)
        client = self.client()
        self.page(f"/bars/{FEED}/food?subject={self.rex}", client, status=404)
        self.page(f"/bars/{FEED}/nope?subject={self.rex}", client, status=404)
        self.assertNotIn("Food put out per", self.page(f"/t/pets__pets/{self.rex}", client))
        self.assertIsNotNone(self.store.get(FEED, entry))
        settings.set_module_enabled(self.conn, "pet_feeding", True)
        self.assertIn("Food put out per", self.page(f"/t/pets__pets/{self.rex}", self.client()))
        self.page(f"/bars/{FEED}/nope?subject={self.rex}", status=404)
        client = self.client()  # only a private table's bars have a Show to press
        reply = client.post(f"/bars/{FEED}/food", base_url=BASE, data={"_csrf": client.csrf})
        self.assertEqual(reply.status_code, 404)

    def test_the_styles_cover_dark_mode_print_and_high_contrast(self):
        css = (ROOT / "src" / "dashboard" / "web" / "templates" / "base.html").read_text(encoding="utf-8")
        for rule in (".chart-svg .chart-bar-so-far-bg { fill: var(--card); }", ".chart-svg .chart-none { stroke: "
                     "var(--muted); stroke-dasharray: 2 2; }", ".chart-svg .chart-bar-so-far-line, .chart-svg "
                     ".chart-none { stroke: CanvasText; }", ".chart-svg .chart-none-text { fill: #000; }"):
            self.assertIn(rule, css)


class DoseBarsTests(DoseTestCase):
    """Doses per week: how many, every medicine together, until a pressed Show gives each medicine its own bars."""

    def setUp(self):
        super().setUp()
        self.dose(at="2026-11-17T08:00:00", amount="7.25", unit="drop")
        self.dose(at="2026-11-18T08:00:00")
        self.dose(med=self.med2, at="2026-11-18T20:00:00")
        self.web = self.client()
        self.path = f"/bars/{DOSES}/doses"

    def test_before_show_the_bars_count_every_dose_and_name_no_medicine(self):
        for path in (f"{self.path}?subject={self.rosa}", f"{self.path}?subject={self.rosa}&show=1",
                     f"/t/people__people/{self.rosa}"):
            page = self.page(path, self.web)
            for secret in (SECRET, "Invented eye drops", "7.25", "Medication #", "Maria Garcia"):
                self.assertNotIn(secret, page[page.index("<main>"):], f"{path}: {secret}")
            self.assertIn("3 doses recorded", words(page))
            self.assertIn(f'action="/bars/{DOSES}/doses"', page)
            self.assertIn("data-show-bars", page)
        self.assertNotIn(f"/t/{DOSES}/", self.page(f"{self.path}?subject={self.rosa}", self.web))

    def test_show_is_a_pressed_button_that_gives_each_medicine_its_own_bars(self):
        reply = self.post(self.web, self.path, subject=str(self.rosa), by="week")
        self.assertEqual(reply.status_code, 200)
        text = words(reply.get_data(as_text=True))
        self.assertIn("Each medicine on its own", text)
        self.assertIn(SECRET, text)
        self.assertIn("Invented eye drops", text)
        self.assertIn("Week from 16/11/26 to 22/11/26 (so far) 2 doses recorded", text)
        self.assertIn("Hide details", text)
        self.assertNotIn("7.25", text, "amounts are never added up or shown on the bars")
        refused = self.web.post(self.path, base_url=BASE, data={"subject": str(self.rosa)})
        self.assertIn(refused.status_code, (400, 403), "no session check: refused")

    def test_a_person_with_no_medication_and_no_doses_gets_no_dose_bars(self):
        self.assertNotIn("Doses recorded per", self.page(f"/t/people__people/{self.maria}", self.web))
        self.assertIn("Doses recorded per week", self.page(f"/t/people__people/{self.rosa}", self.web))

    def test_switched_off_there_are_no_dose_bars(self):
        settings.set_module_enabled(self.conn, "medicine_doses", False)
        client = self.client()
        self.page(f"{self.path}?subject={self.rosa}", client, status=404)
        self.assertEqual(self.post(client, self.path, subject=str(self.rosa)).status_code, 404)
