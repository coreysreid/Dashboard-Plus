"""Tests for decision 0144: Lane B's batch 23 findings 112, 113, 124 and 126 (Bring in dates, skip links, read-me words)."""
import re
import unittest
from datetime import date, timedelta

from support import ROOT
from test_bring_in_history import FEEDS, WEIGHS, BringInTestCase, plain
import build_macos
import build_portable
from dashboard.core import dates
from dashboard.web import pages

TEMPLATES = ROOT / "src" / "dashboard" / "web" / "templates"


def read(path) -> str:
    return path.read_text(encoding="utf-8")


class BringInDateAndAmountTests(BringInTestCase):
    def test_a_weigh_in_with_a_blank_date_is_listed_in_plain_words_and_never_dated_today(self):
        reply, page = self.check(WEIGHS, "Day,Pet,Weight\n20/01/26,Biscuit,21.0\n,Biscuit,21.4\n")
        self.assertEqual(reply.status_code, 200)
        words = plain(page)
        self.assertIn("Row 3", words)
        self.assertIn("Date is empty. Every earlier entry needs its own date; it is never filled in as today.", words)
        self.assertIn("1 weigh-in to bring in, 1 row needs fixing", words)
        self.add(WEIGHS, page)
        days = [r[0] for r in self.conn.execute(f"SELECT day FROM {WEIGHS}")]
        self.assertEqual(days, ["2026-01-20"])  # the blank row was not added, and not as today

    def test_a_blank_date_and_time_for_a_feeding_is_refused_the_same_way(self):
        _reply, page = self.check(FEEDS, "Pet,When,Food,Amount,Unit\nBiscuit,,Dry food,120,g\n")
        self.assertIn("is empty. Every earlier entry needs its own date and time", plain(page))

    def test_a_date_after_today_is_not_an_earlier_entry(self):
        later = date.today() + timedelta(days=20)
        _reply, page = self.check(WEIGHS, f"Pet,Date,Weight\nBiscuit,{later.isoformat()},21\n")
        words = plain(page)
        self.assertIn("is after today. Earlier entries must be on or before today: check the date order.", words)
        self.assertIn("0 weigh-ins to bring in", words)

    def test_an_amount_with_its_unit_typed_in_is_read_when_no_unit_column_is_matched(self):
        text = ("Pet,When,Food,Amount\n"
                "Biscuit,2026-02-01 07:30,Dry food,120g\n"
                "Biscuit,2026-02-01 18:00,Dry food,120 g\n"
                "Biscuit,2026-02-02 07:30,Dry food,0.5 pouch\n"
                "Biscuit,2026-02-02 18:00,Dry food,1 cup\n")
        _reply, page = self.check(FEEDS, text)
        words = plain(page)
        self.assertIn("3 feedings to bring in, 1 row needs fixing", words)
        self.assertIn("“cup” is not one of this list's units (g, ml, pouch, scoop, piece). Nothing is converted", words)
        self.add(FEEDS, page)
        rows = self.conn.execute(f"SELECT amount, unit FROM {FEEDS} ORDER BY given_at").fetchall()
        self.assertEqual([(r["amount"], r["unit"]) for r in rows], [(120, "g"), (120, "g"), (0.5, "pouch")])

    def test_nothing_ready_means_no_bring_in_button(self):
        _reply, page = self.check(WEIGHS, "Pet,Date,Weight\nBiscuit,,21\n")
        self.assertNotIn("/bring-in/pets__weigh_ins/add", page)
        self.assertIn("Nothing is ready to bring in yet.", plain(page))


class RecordPageWalkTests(BringInTestCase):
    def test_an_existing_record_does_not_take_the_cursor_but_an_add_form_does(self):
        page = self.client.get(f"/t/pets__pets/{self.pet}", base_url="http://127.0.0.1:5161").get_data(as_text=True)
        self.assertNotIn("autofocus", page)
        new = self.client.get("/t/pets__pets/new", base_url="http://127.0.0.1:5161").get_data(as_text=True)
        self.assertIn("autofocus", new)

    def test_every_page_starts_with_a_skip_link_and_a_record_page_lists_its_parts(self):
        page = self.client.get(f"/t/pets__pets/{self.pet}", base_url="http://127.0.0.1:5161").get_data(as_text=True)
        self.assertRegex(page, r'<a class="skip-main" href="#main">Skip to main content</a>')
        self.assertIn('<main>\n    <span id="main" tabindex="-1"></span>', page)
        found = re.search(r'<nav class="muted" aria-label="Skip to" id="skip-to">(.*?)</nav>', page, re.S)
        self.assertIsNotNone(found)
        for target in re.findall(r'href="#(sec-[\w-]+)"', found.group(1)):
            self.assertIn(f'id="{target}"', page)  # every skip link lands on a real heading

    def test_history_times_are_in_the_households_style_and_an_empty_before_reads_as_added(self):
        self.assertEqual(pages._history_time("2026-11-27T15:38:12", dates.DAY_FIRST), "27/11/26, 3:38 pm")
        self.assertEqual(pages._history_time("2026-11-27 00:05", dates.DAY_FIRST), "27/11/26, 12:05 am")
        form = read(TEMPLATES / "form.html")
        self.assertIn("{% elif h.added %}{{ c.after }}", form)

    def test_the_calendar_notice_takes_focus_so_undo_is_next(self):
        self.assertIn('id="fix-notice" tabindex="-1" data-focus-here', read(TEMPLATES / "calendar.html"))
        self.assertIn("data-focus-here", read(ROOT / "src" / "dashboard" / "web" / "static" / "common.js"))

    def test_home_cards_carry_their_names_in_the_heading(self):
        home = read(TEMPLATES / "home.html")
        for name in ("Things to do", "Needs attention", "Days of {{ s.label }}"):
            self.assertIn(f'<span class="muted card-name">{name}<span class="vh">: </span></span>', home)
        self.assertNotIn('<div class="muted">Things to do</div>', home)


class ReadMeWordsTests(unittest.TestCase):
    def setUp(self):
        self.windows = " ".join(build_portable.README_TXT.split())
        self.mac = " ".join(build_macos.README_TXT.split())
        self.readme = " ".join(read(ROOT / "README.md").split())

    def test_the_windows_read_me_no_longer_overpromises_and_says_how_to_unblock_update_and_move(self):
        self.assertNotIn("Nothing is sent anywhere", self.windows)
        self.assertIn("does not send them to an online service by itself", self.windows)
        self.assertIn("If you connect an online helper, what you allow it to read may be sent by that helper", self.windows)
        self.assertIn("tick Unblock and click OK", self.windows)
        self.assertIn("The next start backs up your records first", self.windows)
        self.assertIn("Moving to a new computer?", self.windows)
        self.assertIn("Backups are in data\\backups and in %LOCALAPPDATA%\\Dashboard Plus\\backups.", self.windows)
        self.assertIn("This is an early test version.", self.windows)

    def test_the_mac_read_me_names_the_update_backup_and_the_second_copy(self):
        self.assertIn("backs up your records before changing anything", self.mac)
        self.assertIn(".local/share/dashboard-plus in your home folder", self.mac)

    def test_the_readme_opening_status_prices_charts_calendar_and_helper_words(self):
        for words in ("connect a helper (an AI assistant you give a key) or, later, pair another computer of your own",
                      "Status: an early test version.**",
                      "unless you choose to share them with your other computers",
                      "**Charts:**", "**Things to do → Calendar** shows every dated list together",
                      "Do not type codes or medicines into ordinary notes",
                      "A second backup copy is kept in your account's local app data folder",
                      "To **move to a new computer**"):
            self.assertIn(words, self.readme)
        self.assertNotIn("The first charts", self.readme)
        self.assertNotIn("(M1)", self.readme)


class AgreedWordsTests(unittest.TestCase):
    def test_one_word_for_each_idea(self):
        web = ROOT / "src" / "dashboard" / "web"
        self.assertIn(">Next 50 rows<", read(TEMPLATES / "grid.html"))
        self.assertNotIn("Show more", read(TEMPLATES / "grid.html"))
        checklist = read(web / "checklist.py")
        self.assertIn('"late": "From before today"', checklist)
        self.assertIn('"Open to update"', checklist)
        self.assertIn("due today or before", read(TEMPLATES / "home.html"))
        self.assertNotIn("due or late", read(TEMPLATES / "home.html"))
        self.assertIn("none of these fit your settings", read(TEMPLATES / "questions.html"))
        self.assertIn("Bring in earlier entries: added at once, with one Undo", read(TEMPLATES / "import.html"))
        self.assertIn("See what is in it", read(TEMPLATES / "restore_list.html"))
        self.assertIn("(an earlier date you recorded)", read(web / "calendar_pages.py"))
        for name in ("bars.html", "calendar.html", "daily.html"):
            self.assertIn("All entries in this list", read(TEMPLATES / name))
        self.assertNotIn("occurrence done", read(ROOT / "modules" / "routines" / "tables.toml").split("[[")[1])
        self.assertIn('label = "Done"', read(ROOT / "modules" / "garden" / "labels.toml"))


if __name__ == "__main__":
    unittest.main()
