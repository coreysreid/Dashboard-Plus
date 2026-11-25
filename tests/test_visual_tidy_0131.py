"""Tests for the hands-on visual check of decisions 0119 to 0130: Services done per month, folded bars, one "This month" (decision 0131)."""
import re

from test_bar_charts import FEED, BarsTestCase
from test_done_history import HistoryCase, SERVICES, main
from dashboard.core import bars


class ServicesBarsTests(HistoryCase):
    def test_vehicle_services_have_services_done_per_month_counting_each_done_day(self):
        self.on("2026-07-10", SERVICES, self.service, {"last_done": "2026-07-09"})
        rule = self.registry[SERVICES].table.bars[0]
        self.assertTrue(rule["history"])
        self.assertEqual(rule["measure"], "count")
        page = self.page(f"/bars/{SERVICES}/done")
        text = re.sub(r"<[^>]+>", " ", main(page))
        self.assertIn("Services done per month", text)
        self.assertIn("2 services done recorded", " ".join(text.split()))
        self.assertNotIn("Oil change", text)  # a chart of every service together names no one service
        self.assertIn(f'<a href="/bars/{SERVICES}/done">Services done per month</a>', self.page(f"/t/{SERVICES}"))
        self.assertIn("<h2>Services done per month</h2>", self.page(f"/calendar/{SERVICES}"))
        self.assertNotIn("Services done per month", self.page(f"/t/{SERVICES}/{self.service}"))


class FoldedBarsTests(BarsTestCase):
    def test_a_pet_page_with_a_calendar_folds_its_bars_under_a_summary_and_keeps_every_word(self):
        self.feed("2026-11-19T07:00", 100, "g")
        page = self.page(f"/t/pets__pets/{self.rex}")
        self.assertIn("<h2>Food put out per day in g</h2>", page)
        self.assertRegex(page, r'<details class="panel-fold" data-print-open><summary>Show the bars: Rex · 14 days')
        folded = page[page.index('class="panel-fold"'):]
        folded = folded[:folded.index("</details>\n", folded.index("bars-table"))]
        self.assertIn('class="chart-svg"', folded)  # the drawing is inside the fold, not removed
        self.assertIn(f'href="/bars/{FEED}/food?subject={self.rex}&amp;by=week&amp;unit=g"', folded)
        self.assertIn("beforeprint", page)  # opened for the paper, so a printout has every part

    def test_the_calendar_and_the_timeline_stay_open(self):
        page = self.page(f"/t/pets__pets/{self.rex}")
        self.assertEqual(page.count('class="panel-fold"'), 1)
        self.assertIn("<h2>Feeding calendar</h2>", page)
        self.assertNotIn("<details open", page)

    def test_bars_with_no_calendar_beside_them_are_not_folded(self):
        text = self.page(f"/bars/{FEED}/food?subject={self.rex}")
        self.assertNotIn('class="panel-fold"', text)


class OneThisMonthTests(BarsTestCase):
    def test_a_calendars_own_link_is_not_called_this_month_beside_the_things_to_do_tab(self):
        page = self.page("/to-do/calendar")
        self.assertEqual(page.count(">This month</a>"), 1)  # the Things to do tab
        self.assertIn(">Go to the current month</a>", self.page("/to-do/calendar?month=2026-10"))
        self.assertIn(">Go to the current month</a>", self.page(f"/calendar/{FEED}?subject={self.rex}&month=2026-10"))


class SameWordsTests(BarsTestCase):
    def test_two_buttons_to_one_list_say_which_link_each_fills_in(self):
        jane = self.store.create("people__people", {"name": "Jane Example"})
        page = self.page(f"/t/people__people/{jane}")
        buttons = re.findall(r'class="button quiet" href="/t/pets__pets/new\?[a-z_]+=\d+">([^<]+)</a>', page)
        self.assertEqual(len(buttons), len(set(buttons)), buttons)
        self.assertGreaterEqual(len(buttons), 2)
        self.assertTrue(all("(" in b for b in buttons), buttons)
