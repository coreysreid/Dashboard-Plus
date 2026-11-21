"""Tests for the first charts (decision 0109): the drinking-water breakdown, one pet's weigh-ins and the SVG drawing."""
import html
import re
import xml.etree.ElementTree as ET
from datetime import date

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, modules, proposals, records, settings, startup, watch
from dashboard.web import charts
from dashboard.web.app import create_app
import load_example

TODAY = date(2026, 11, 21)
PORT = 5143
BASE = f"http://127.0.0.1:{PORT}"
SVG = "{http://www.w3.org/2000/svg}"
WATER_PAGE = "/supplies/stock__items"
WEIGHTS = "/charts/pets__weigh_ins"


def svgs(page: str) -> list[ET.Element]:
    """Every chart on a page, parsed as XML (so a broken drawing fails the test)."""
    return [ET.fromstring(m) for m in re.findall(r"<svg class=\"chart-svg\".*?</svg>", page, flags=re.S)]


def marks(svg: ET.Element) -> list[ET.Element]:
    return svg.findall(f"{SVG}a")


def table_rows(page: str, chart_id: str) -> list[str]:
    return re.findall(rf'<tr id="{re.escape(chart_id)}-row-(\d+)"', page)


def section(page: str, start: str, end: str = "</section>") -> str:
    begin = page.index(start)
    return page[begin:page.index(end, begin)]


class DrawingTests(TempDirTestCase):
    """The drawing helper on its own: structure, scale from zero, escaping, nothing joined."""

    def test_axis_steps_are_round_and_start_at_zero(self):
        self.assertEqual(charts.axis_steps(21.3), (25, 5))
        self.assertEqual(charts.axis_steps(4.1), (5, 1))
        self.assertEqual(charts.axis_steps(3.8), (4, 1))
        self.assertEqual(charts.axis_steps(0), (1, 1))
        self.assertEqual(charts.axis_steps(34.4, most=2)[0], 40)

    def test_bar_chart_is_named_described_and_every_bar_is_labelled(self):
        bars = [charts.Bar("Casks <b>", 20, "20 litres", "#c-row-1"), charts.Bar("Bottles", 14.4, "14.4 litres", "#c-row-2")]
        svg = ET.fromstring(str(charts.bar_chart("c", "Water counted", "Bars for each item", bars, "Litres", "litres")))
        self.assertEqual(svg.tag, f"{SVG}svg")
        self.assertEqual(svg.get("aria-labelledby"), "c-title")
        self.assertEqual(svg.get("aria-describedby"), "c-desc")
        self.assertEqual(svg.find(f"{SVG}title").get("id"), "c-title")
        self.assertEqual(svg.find(f"{SVG}title").text, "Water counted")
        self.assertEqual(svg.find(f"{SVG}desc").text, "Bars for each item")
        self.assertEqual([a.get("href") for a in marks(svg)], ["#c-row-1", "#c-row-2"])
        self.assertEqual([a.get("aria-label") for a in marks(svg)], ["Casks <b>: 20 litres", "Bottles: 14.4 litres"])
        texts = [t.text for t in svg.iter(f"{SVG}text")]
        self.assertIn("Casks <b>", texts)  # escaped in the markup, read back as plain words
        self.assertIn("20 litres", texts)  # the value is printed, not left to colour or length
        self.assertIn("0 litres", texts)  # the scale starts at zero
        widths = [float(r.get("width")) for r in svg.iter(f"{SVG}rect")]
        self.assertAlmostEqual(widths[1] / widths[0], 14.4 / 20, places=2)
        self.assertNotIn("<script", str(charts.bar_chart("c", "t", "d", bars, "a", "u")))

    def test_dot_chart_draws_dots_only_from_zero_and_keeps_same_day_readings_apart(self):
        dots = [charts.Dot(date(2026, 11, 1), 4.1, "01/11/26: 4.1 kg", "#d-row-1"),
                charts.Dot(date(2026, 11, 20), 3.8, "20/11/26: 3.8 kg", "#d-row-2"),
                charts.Dot(date(2026, 11, 20), 3.8, "20/11/26: 3.8 kg, reading 2 of 2", "#d-row-3")]
        svg = ET.fromstring(str(charts.dot_chart("d", "Luna", "Dots", dots, "Date", "kg", lambda d: d.isoformat())))
        circles = list(svg.iter(f"{SVG}circle"))
        self.assertEqual(len(circles), 3)
        self.assertEqual(len({c.get("cx") for c in circles}), 3, "two readings on one day are both visible")
        self.assertEqual(svg.findall(f".//{SVG}path") + svg.findall(f".//{SVG}polyline"), [], "dots are never joined")
        texts = [t.text for t in svg.iter(f"{SVG}text")]
        self.assertIn("0", texts)
        self.assertIn("kg", texts)
        self.assertIn("2026-11-01", texts)
        self.assertIn("2026-11-20", texts)

    def test_check_8_print_high_contrast_phone_and_no_motion(self):
        css = (ROOT / "src" / "dashboard" / "web" / "templates" / "base.html").read_text(encoding="utf-8")
        charts_css = css[css.index("/* Charts drawn"):css.index("    footer { color")]
        for rule in ("@media print", "@media (forced-colors: active)", "@media (max-width: 40rem)",
                     "td::before { content: attr(data-label)", "a:focus .chart-bar"):
            self.assertIn(rule, charts_css)
        self.assertNotIn("animation", charts_css)
        self.assertNotIn("transition", charts_css)
        source = (ROOT / "src" / "dashboard" / "web" / "charts.py").read_text(encoding="utf-8")
        self.assertNotIn("<animate", source)
        self.assertNotIn("http://", source.replace('xmlns="http://www.w3.org/2000/svg"', ""), "nothing fetched")
        self.assertNotIn("https://", source)

    def test_one_dot_stays_one_dot_in_the_middle(self):
        svg = ET.fromstring(str(charts.dot_chart("d", "t", "d", [charts.Dot(date(2026, 1, 1), 4, "x", "#r")], "Date",
                                                 "kg", str)))
        self.assertEqual(len(list(svg.iter(f"{SVG}circle"))), 1)
        self.assertEqual(float(next(svg.iter(f"{SVG}circle")).get("cx")), 184.0)


class ChartDeclarationTests(TempDirTestCase):
    TABLES = '''[tables.animals]
title = "Animals"
columns.name = { type = "text", required = true }

[tables.readings]
title = "Readings"
columns.animal = { type = "link", to = "animals", required = true, on_delete = "cascade" }
columns.day = { type = "date", required = true }
columns.weight = { type = "decimal", required = true, unit = "kg" }
columns.note = { type = "text" }
'''

    def load(self, chart: str):
        return modules.load_module(self.make_module(tables=self.TABLES + chart, labels=None))

    def test_a_good_chart_is_kept(self):
        module = self.load('chart = { kind = "dots", x = "day", y = "weight", per = "animal", what = ["weight", '
                           '"weights"], entry = ["reading", "readings"], subject = "animal" }\n')
        self.assertEqual(module.tables["readings"].chart["per"], "animal")

    def test_wrong_columns_and_words_are_explained(self):
        with self.assertRaises(modules.ModuleError) as caught:
            self.load('chart = { kind = "line", x = "note", y = "note", per = "day", what = "weight", '
                      'entry = ["reading"], colour = "red" }\n')
        text = str(caught.exception)
        for words in ("'kind' must be \"dots\"", "'x' must name a required date or date-and-time column", "'y' must name a required "
                      "number column", "'per' must name a required link column", "'what' must be two words",
                      "'entry' must be two words", "'subject' must be the word", "colour"):
            self.assertIn(words, text)


class ChartPagesTestCase(TempDirTestCase):
    """A made-up example household loaded into the real app."""
    household = "smith"

    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        load_example.load(self.household, self.data, today=TODAY)
        self.report = startup.prepare(self.data, ROOT / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        self.client = app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def get(self, path: str, status: int = 200) -> str:
        response = self.client.get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)

    def supply(self) -> watch.Supply:
        return next(s for s in watch.supplies(self.conn, self.store.registry) if s.table == "stock__items")

    def item(self, name, quantity, unit="litres", drinking=True, category="water"):
        values = {"name": name, "category": category, "unit": unit, "drinking": drinking}
        if quantity is not None:
            values["quantity"] = quantity
        return self.store.create("stock__items", values)

    def pet(self, name):
        return self.conn.execute("SELECT id FROM pets__pets WHERE name = ?", (name,)).fetchone()[0]

    def home_days(self) -> str:
        return re.search(r"About ([\d.]+) days? of drinking water", self.get("/")).group(1)

    def headline(self, page: str) -> str:
        return re.search(r'<p class="chart-headline"[^>]*><strong>(.*?)</strong>', page).group(1)


class WaterChartTests(ChartPagesTestCase):
    def test_check_1_only_safe_litres_make_bars_and_left_out_rows_say_why(self):
        before = self.supply()
        self.item("Flushing water", 20, drinking=False)
        self.item("Spring water bottles", 6, unit="bottles")
        page = self.get(WATER_PAGE)
        after = self.supply()
        self.assertEqual((after.total, after.days), (before.total, before.days), "left-out rows add nothing")
        svg = svgs(page)[0]
        self.assertEqual(sorted(a.get("aria-label") for a in marks(svg)),
                         ["Water bottles (24 x 600 mL): 14.4 litres", "Water casks (10 L): 20 litres"])
        self.assertIn("Left out: marked as not drinking water", page)
        self.assertIn("Left out: recorded in bottles, not litres", page)
        self.assertEqual(len(table_rows(page, "chart-stock__items")), 4, "every water item has a table row")
        self.assertNotIn("Flushing water", ET.tostring(svg, encoding="unicode"), "no zero-valued bar")

    def test_check_2_the_chart_uses_the_same_snapshot_as_home_and_moves_with_it(self):
        def same():
            page, supply = self.get(WATER_PAGE), self.supply()
            self.assertIn(f"{supply.total:g} litres counted · about {round(supply.days, 1):g} day{'' if round(supply.days, 1) == 1 else 's'} for "
                          f"{supply.household.people} people and {supply.household.pets} pets · aim 3 days",
                          self.headline(page))
            self.assertEqual(self.home_days(), f"{round(supply.days, 1):g}")
            bars = sum(float(re.search(r": ([\d.]+) litres", a.get("aria-label")).group(1))
                       for a in marks(svgs(page)[0]))
            self.assertAlmostEqual(bars, supply.total)
            self.assertIn(supply.basis, page)
            return supply
        first = same()
        casks = self.conn.execute("SELECT id FROM stock__items WHERE name = 'Water casks (10 L)'").fetchone()[0]
        self.store.create("stock__movements", {"item": casks, "reason": "bought", "amount": 10,
                                               "happened_on": "2026-11-21"})  # a new batch
        self.assertAlmostEqual(same().total, first.total + 10)
        self.store.update("stock__items", casks, {"drinking": False})
        self.assertAlmostEqual(same().total, 14.4)
        person = self.conn.execute("SELECT id FROM people__people WHERE lives_here = 1 ORDER BY id").fetchone()[0]
        self.store.update("people__people", person, {"lives_here": False})
        self.assertEqual(same().household.people, first.household.people - 1)

    def test_check_2_a_pending_helper_stock_in_does_not_count(self):
        before = self.supply().total
        helper, _key = helpers.issue(self.conn, self.data, "Made-up helper", "suggest", ["stock"])
        casks = self.conn.execute("SELECT id FROM stock__items WHERE name = 'Water casks (10 L)'").fetchone()[0]
        proposals.submit(self.conn, self.registry, helper, {"request_key": "charts", "why": "A made-up shop",
                         "entries": [{"table": "stock__movements", "values": {
                             "item": casks, "reason": "bought", "amount": 50, "happened_on": "2026-11-21"}}]})
        self.assertEqual(self.supply().total, before)
        self.assertIn(f"{before:g} litres counted", self.headline(self.get(WATER_PAGE)))

    def test_check_3_no_person_count_shows_litres_but_no_days(self):
        self.conn.execute("UPDATE people__people SET lives_here = 0")
        settings.put(self.conn, "household.people", None)
        page = self.get(WATER_PAGE)
        self.assertEqual(self.headline(page), "34.4 litres counted. Tell Dashboard Plus how many people live here "
                                              "to work out days.")
        self.assertIn("Not worked out yet", page)
        self.assertNotIn("days for", page)

    def test_check_3_no_water_and_only_left_out_water_have_their_own_words(self):
        for row in self.conn.execute("SELECT id FROM stock__items WHERE category = 'water'").fetchall():
            self.store.delete("stock__items", row[0])
        page = self.get(WATER_PAGE)
        self.assertIn("No drinking water recorded yet. Add litres and answer whether each water item is safe to "
                      "drink now.", page)
        self.assertEqual(svgs(page), [])
        self.item("Rain barrel", 100, drinking=False)
        page = self.get(WATER_PAGE)
        self.assertIn("No litres are counted as drinking water yet. Check each item's answer and unit.", html.unescape(page))
        self.assertNotIn("No drinking water recorded yet", page)
        self.assertEqual(svgs(page), [])

    def test_check_3_a_missing_amount_is_unknown_and_a_zero_is_recorded_zero(self):
        self.item("Water jug, not measured", None)
        self.item("Empty cask", 0)
        page = self.get(WATER_PAGE)
        unmeasured = section(page, "Water jug, not measured", "</tr>")
        self.assertIn("Not recorded", unmeasured)
        self.assertIn("Left out: no amount recorded (unknown, not zero)", unmeasured)
        self.assertNotIn(">0", unmeasured)
        self.assertIn("0 litres counted (recorded as none left)", section(page, "Empty cask", "</tr>"))
        self.assertEqual(len(marks(svgs(page)[0])), 2, "neither becomes a bar")
        self.assertNotIn("guarantee", page.lower())
        self.assertIn("These daily figures are a starting point. Check your local authority's advice.",
                      html.unescape(page))

    def test_check_4_three_hundred_items_keep_a_bounded_chart_and_a_full_table(self):
        for n in range(300):
            self.conn.execute("INSERT INTO stock__items (name, category, quantity, unit, drinking, created_at, "
                              "updated_at) VALUES (?, 'water', ?, 'litres', 1, '2026-11-21T00:00:00+00:00', "
                              "'2026-11-21T00:00:00+00:00')", (f"Made-up water {n:03d}", 1 + n % 7))
        page = self.get(WATER_PAGE)
        self.assertEqual(len(marks(svgs(page)[0])), 12)
        self.assertIn("The chart shows the 12 largest of 302 counted items.", page)
        self.assertEqual(len(table_rows(page, "chart-stock__items")), 302)
        self.assertAlmostEqual(self.supply().total, 34.4 + sum(1 + n % 7 for n in range(300)))
        self.assertIn(f"{self.supply().total:g} litres counted", self.headline(page))

    def test_table_is_sorted_by_counted_litres_then_name(self):
        self.item("B water", 5)
        self.item("A water", 5)
        names = re.findall(r'<td data-label="Item"><a href="/t/stock__items/\d+">([^<]+)</a>', self.get(WATER_PAGE))
        self.assertEqual(names[:4], ["Water casks (10 L)", "Water bottles (24 x 600 mL)", "A water", "B water"])

    def test_check_9_the_water_chart_is_today_only(self):
        page = self.get(WATER_PAGE)
        self.assertIn("This is today's count, not a history", html.unescape(page))
        texts = [t.text or "" for t in svgs(page)[0].iter(f"{SVG}text")]
        self.assertFalse([t for t in texts if re.search(r"\d\d/\d\d/\d\d", t)], "no dates along the chart")
        self.get("/charts/stock__movements", status=404)  # no spend chart until purchase prices exist

    def test_home_and_attention_link_to_the_breakdown(self):
        self.assertIn(f'<a href="{WATER_PAGE}">What is counted</a>', self.get("/"))
        self.assertIn(f'<a href="{WATER_PAGE}">', self.get("/attention"))

    def test_module_off_means_no_page_and_no_link(self):
        settings.set_module_enabled(self.conn, "stock", False)
        self.get(WATER_PAGE, status=404)
        self.assertNotIn("/supplies/", self.get("/"))
        self.get("/supplies/pets__pets", status=404)  # a table with no supply rule

    def test_check_8_marks_and_table_rows_match_one_to_one(self):
        page = self.get(WATER_PAGE)
        rows = set(table_rows(page, "chart-stock__items"))
        for a in marks(svgs(page)[0]):
            self.assertIn(a.get("href").rpartition("-row-")[2], rows)
            self.assertRegex(a.get("aria-label"), r": [\d.]+ litres$")


class WeightChartTests(ChartPagesTestCase):
    household = "garcia"

    def weights_section(self, pet_id) -> str:
        return section(self.get(f"/t/pets__pets/{pet_id}"), f'aria-labelledby="chart-pets__weigh_ins-{pet_id}-heading"')

    def test_check_5_lunas_two_weigh_ins_are_two_dots_and_two_rows(self):
        luna = self.pet("Luna")
        part = self.weights_section(luna)
        svg = svgs(part)[0]
        self.assertEqual(len(marks(svg)), 2)
        self.assertEqual(len(table_rows(part, f"chart-pets__weigh_ins-{luna}")), 2)
        self.assertRegex(part, r"Luna · 3\.8 kg on \d\d/\d\d/\d\d · 2 weigh-ins recorded")
        for word in ("healthy", "trend", "diagnos", "because"):
            self.assertNotIn(word, part.lower())
        self.assertEqual(svg.findall(f".//{SVG}path") + svg.findall(f".//{SVG}polyline"), [])

    def test_check_6_same_day_readings_corrections_delete_and_restore_stay_in_step(self):
        luna = self.pet("Luna")
        first = self.store.create("pets__weigh_ins", {"pet": luna, "day": "2026-11-21", "weight": 3.7})
        second = self.store.create("pets__weigh_ins", {"pet": luna, "day": "2026-11-21", "weight": 3.7})
        part = self.weights_section(luna)
        ids = table_rows(part, f"chart-pets__weigh_ins-{luna}")
        self.assertEqual(ids[-2:], [str(first), str(second)], "same day: both kept, oldest first")
        self.assertIn("reading 1 of 2 that day", part)
        self.assertEqual(len(marks(svgs(part)[0])), 4)
        self.store.update("pets__weigh_ins", first, {"weight": 3.9})
        part = self.weights_section(luna)
        self.assertIn("3.9 kg", part)
        self.assertIn("Corrected on", section(part, f'<tr id="chart-pets__weigh_ins-{luna}-row-{first}"', "</tr>"))
        self.store.delete("pets__weigh_ins", second)
        part = self.weights_section(luna)
        self.assertNotIn(f'-row-{second}"', part)
        self.assertEqual(len(marks(svgs(part)[0])), 3)
        self.store.restore("pets__weigh_ins", second)
        part = self.weights_section(luna)
        self.assertIn("Restored on", section(part, f'<tr id="chart-pets__weigh_ins-{luna}-row-{second}"', "</tr>"))
        self.assertEqual(len(marks(svgs(part)[0])), 4)
        self.store.update("pets__weigh_ins", second, {"notes": "After breakfast"})
        self.assertIn("Restored on", section(self.weights_section(luna), f'<tr id="chart-pets__weigh_ins-{luna}-row-{second}"', "</tr>"),
                      "a note is not a correction of the reading")

    def test_check_7_no_cause_labels_and_no_private_or_note_text(self):
        luna = self.pet("Luna")
        part = self.weights_section(luna)
        visit = self.conn.execute("SELECT reason, notes FROM pets__vet_visits WHERE pet = ?", (luna,)).fetchone()
        notes = [r[0] for r in self.conn.execute("SELECT notes FROM pets__weigh_ins WHERE pet = ? AND notes IS NOT NULL",
                                                 (luna,))]
        pet = self.conn.execute("SELECT notes, microchip FROM pets__pets WHERE id = ?", (luna,)).fetchone()
        for private in [visit["reason"], visit["notes"], pet["notes"], pet["microchip"], *notes]:
            if private:
                self.assertNotIn(private.replace("'", "&#39;"), part)
        self.assertIn("Nothing here says why a value changed.", part)
        page = self.get(f"{WEIGHTS}?subject={luna}")
        for private in [visit["reason"], pet["microchip"], *notes]:
            if private:
                self.assertNotIn(private.replace("'", "&#39;"), page)

    def test_check_8_every_dot_names_its_date_value_and_unit_and_reaches_its_row(self):
        luna = self.pet("Luna")
        page = self.get(f"{WEIGHTS}?subject={luna}")
        svg = svgs(page)[0]
        rows = set(table_rows(page, f"chart-pets__weigh_ins-{luna}"))
        for a in marks(svg):
            self.assertRegex(a.get("aria-label"), r"^\d\d/\d\d/\d\d: [\d.]+ kg")
            self.assertIn(a.get("href").rpartition("-row-")[2], rows)
        self.assertEqual(svg.find(f"{SVG}title").text, "Luna's recorded weights")
        self.assertIn("The dots are not joined", svg.find(f"{SVG}desc").text)
        self.assertIn("<h3>Luna&#39;s recorded weights · all dates", page)

    def test_check_9_a_period_with_no_weigh_ins_is_a_gap_not_zero(self):
        luna = self.pet("Luna")
        page = self.get(f"{WEIGHTS}?subject={luna}&from=01/01/25&to=01/31/25")  # Garcias type month first
        self.assertIn("No weights recorded in this period.", page)
        self.assertEqual(svgs(page), [])
        self.assertNotIn("0 kg", page)

    def test_a_chosen_period_keeps_only_its_readings_and_a_bad_date_shows_all(self):
        luna = self.pet("Luna")
        days = [r[0] for r in self.conn.execute("SELECT day FROM pets__weigh_ins WHERE pet = ? ORDER BY day", (luna,))]
        last = date.fromisoformat(days[-1]).strftime("%m/%d/%y")
        page = self.get(f"{WEIGHTS}?subject={luna}&from={last}")
        self.assertEqual(len(marks(svgs(page)[0])), 1)
        self.assertIn("One weight recorded. Add another dated reading to compare, if you choose to track this.", page)
        page = self.get(f"{WEIGHTS}?subject={luna}&from=13/45/26")
        self.assertIn("Showing all dates instead.", page)
        self.assertEqual(len(marks(svgs(page)[0])), 2)

    def test_a_pet_with_no_weigh_ins(self):
        new = self.store.create("pets__pets", {"name": "Pip", "species": "bird"})
        self.assertIn("No weights recorded for Pip yet.", self.weights_section(new))


class OneReadingTests(ChartPagesTestCase):
    household = "smith"

    def test_check_5_one_reading_has_its_own_words_and_one_dot(self):
        whiskers = self.pet("Whiskers")
        page = self.get(f"/t/pets__pets/{whiskers}")
        self.assertIn("One weight recorded. Add another dated reading to compare, if you choose to track this.", page)
        self.assertEqual(len(marks(svgs(page)[0])), 1)
        self.assertIn(f'href="{WEIGHTS}?subject={whiskers}"', page)

    def test_pets_are_never_mixed(self):
        rex = self.pet("Rex")
        page = self.get(f"{WEIGHTS}?subject={rex}")
        self.assertEqual(len(svgs(page)), 1)
        self.assertEqual(len(marks(svgs(page)[0])), 3)
        self.assertNotIn("4.6 kg", page)  # Whiskers' weight


class TaylorTests(ChartPagesTestCase):
    household = "taylor"

    def test_check_5_no_pet_says_add_a_pet_and_pets_off_has_no_chart(self):
        self.get(WEIGHTS, status=404)  # the Taylors have not switched Pets on
        settings.set_module_enabled(self.conn, "pets", True)
        page = self.get(WEIGHTS)
        self.assertIn("Add a pet before showing its weight history.", page)
        self.assertIn('href="/t/pets__pets/new"', page)

    def test_the_water_breakdown_matches_home(self):
        page = self.get(WATER_PAGE)
        self.assertEqual(self.headline(page), "12 litres counted · about 4 days for 1 person · aim 3 days")
        self.assertEqual(self.home_days(), "4")
        self.assertIn("Left out: marked as not drinking water", page)
        self.assertIn("Hall › Hall cupboard", page)  # the batch's full place path


class GarciaWaterTests(ChartPagesTestCase):
    household = "garcia"

    def test_the_water_breakdown_matches_home(self):
        supply = self.supply()
        page = self.get(WATER_PAGE)
        self.assertEqual(self.home_days(), f"{round(supply.days, 1):g}")
        self.assertIn(f"about {round(supply.days, 1):g} days", self.headline(page))
        self.assertEqual(len(marks(svgs(page)[0])), len([i for i in supply.items if i.counted > 0]))
