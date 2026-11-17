"""Tests for dates the household's way (Lane B's stock lots acceptance checks 8 to 11, decision 0052)."""
import shutil
import unittest

from support import ROOT, TempDirTestCase
from dashboard.core import dates, db, settings, startup
from dashboard.web.app import create_app

PORT = 5130
BASE = f"http://127.0.0.1:{PORT}"

AU, US, CA = dates.style_for("Australia"), dates.style_for("United States"), dates.style_for("Canada")


class DateStyleTests(unittest.TestCase):
    def test_who_writes_what_first(self):
        for country in ("Australia", "United Kingdom", "New Zealand", "Ireland", "South Africa", None, "Atlantis"):
            self.assertEqual(dates.style_for(country), dates.DAY_FIRST, country)
        self.assertEqual(US, dates.MONTH_FIRST)
        self.assertEqual(CA, dates.YEAR_FIRST)

    def test_day_first_typed_and_shown(self):  # check 8
        self.assertEqual(dates.parse("20/05/27", AU), "2027-05-20")
        self.assertEqual(dates.show("2027-05-20", AU), "20/05/27")
        self.assertEqual(dates.parse("1/2/27", AU), "2027-02-01")
        self.assertEqual(dates.long("2027-02-01", AU), "1 February 2027")
        self.assertEqual(dates.show("2027-02-01", AU), "01/02/27")
        self.assertEqual(dates.HINTS[AU], "Day / month / year (DD/MM/YY)")

    def test_month_first_typed_and_shown(self):  # check 9
        self.assertEqual(dates.parse("05/20/27", US), "2027-05-20")
        self.assertEqual(dates.show("2027-05-20", US), "05/20/27")
        self.assertEqual(dates.parse("1/2/27", US), "2027-01-02")
        self.assertEqual(dates.long("2027-01-02", US), "January 2, 2027")
        self.assertEqual(dates.HINTS[US], "Month / day / year (MM/DD/YY)")

    def test_the_international_order_is_understood_everywhere(self):  # check 10
        for style in (AU, US, CA):
            self.assertEqual(dates.parse("2027-05-20", style), "2027-05-20")
        self.assertEqual(dates.show("2027-05-20", CA), "2027-05-20")
        with self.assertRaises(ValueError):
            dates.parse("05/06/27", CA)  # a guess either way

    def test_two_digit_years_are_this_century_and_four_digits_still_work(self):  # check 10
        self.assertEqual(dates.parse("01/01/99", AU), "2099-01-01")
        self.assertEqual(dates.parse("01/01/1999", AU), "1999-01-01")
        self.assertEqual(dates.show("1999-01-01", AU), "01/01/1999")  # never shown as 99, which reads as 2099

    def test_impossible_dates_are_refused_never_rolled_over(self):  # check 11
        for text in ("31/04/27", "29/02/27", "32/01/27", "20/13/27", "tomorrow", "20/05"):
            with self.assertRaises(ValueError) as caught:
                dates.parse(text, AU)
            self.assertEqual(str(caught.exception), "Enter a real date in DD/MM/YY format.")
        with self.assertRaises(ValueError) as caught:
            dates.parse("02/30/27", US)
        self.assertEqual(str(caught.exception), "Enter a real date in MM/DD/YY format.")
        self.assertEqual(dates.parse("29/02/28", AU), "2028-02-29")
        self.assertEqual(dates.parse("02/29/28", US), "2028-02-29")

    def test_other_separators_and_spaces(self):
        self.assertEqual(dates.parse(" 20.05.2027 ", AU), "2027-05-20")
        self.assertEqual(dates.parse("20-5-27", AU), "2027-05-20")


class DateFormTests(TempDirTestCase):
    """Typed in a form, shown in a list: the household's country decides the order."""

    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        self.client = app.test_client()
        self.client.get("/?key=k", base_url=BASE)
        self.csrf = app.config["CSRF_TOKEN"]

    def add(self, expires, country):
        settings.put(self.conn, "household.country", country)
        return self.client.post("/t/stock__items/new", base_url=BASE, data={
            "_csrf": self.csrf, "name": "Kidney beans", "category": "pantry", "quantity": "5", "unit": "tins",
            "expires": expires})

    def test_an_australian_date_is_stored_the_international_way_and_shown_back(self):
        self.assertEqual(self.add("20/05/27", "Australia").status_code, 302)
        self.assertEqual(self.conn.execute("SELECT expires FROM stock__items").fetchone()[0], "2027-05-20")
        self.assertIn("20/05/27", self.client.get("/t/stock__items", base_url=BASE).get_data(as_text=True))
        settings.put(self.conn, "household.country", "United States")  # presentation changes, the date does not
        self.assertIn("05/20/27", self.client.get("/t/stock__items", base_url=BASE).get_data(as_text=True))
        self.assertEqual(self.conn.execute("SELECT expires FROM stock__items").fetchone()[0], "2027-05-20")

    def test_an_impossible_date_saves_nothing_and_keeps_what_was_typed(self):
        page = self.add("31/04/27", "United Kingdom")
        self.assertEqual(page.status_code, 422)
        text = page.get_data(as_text=True)
        self.assertIn("Enter a real date in DD/MM/YY format.", text)
        self.assertIn('value="31/04/27"', text)
        self.assertIn('value="Kidney beans"', text)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM stock__items").fetchone()[0], 0)

    def test_a_bad_date_and_another_problem_are_both_reported(self):
        settings.put(self.conn, "household.country", "United States")
        page = self.client.post("/t/stock__items/new", base_url=BASE, data={
            "_csrf": self.csrf, "name": "", "category": "pantry", "expires": "02/30/27"})
        text = page.get_data(as_text=True)
        self.assertIn("Enter a real date in MM/DD/YY format.", text)
        self.assertIn("is required", text)
