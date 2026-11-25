"""Tests that keep decision 0127's fixes in place: the narrow This year layout, the receipt group words and the Mac read-me words."""
import re
import sys
import unittest

from support import ROOT

sys.path.insert(0, str(ROOT / "tools"))

import build_macos  # noqa: E402
from dashboard.web import review  # noqa: E402

TEMPLATES = ROOT / "src" / "dashboard" / "web" / "templates"


class ThisYearFitsAPhoneTests(unittest.TestCase):
    def setUp(self):
        self.page = (TEMPLATES / "checklist.html").read_text(encoding="utf-8")

    def test_each_month_becomes_one_row_of_labelled_numbers_on_a_narrow_phone(self):
        narrow = re.search(r"@media \(max-width: 30rem\) \{(.*?)\n  \}", self.page, re.S)
        self.assertIsNotNone(narrow, "the narrow-phone rules are missing")
        css = narrow.group(1)
        self.assertIn(".todo-months tr { display: flex; flex-wrap: wrap", css)
        self.assertIn("display: block", css)
        self.assertIn('content: attr(data-label) ": "', css)

    def test_every_number_carries_the_word_that_labels_it(self):
        for label in ("Due", "Done", "Skipped"):
            self.assertIn(f'data-label="{label}"', self.page)

    def test_the_browser_check_asserts_the_320_pixel_width(self):
        script = (ROOT / "tools" / "browser_check.js").read_text(encoding="utf-8")
        self.assertIn("This year should fit a 320 pixel phone screen", script)
        self.assertIn("async function checkWidths", script)


class ReceiptGroupWordsTests(unittest.TestCase):
    def test_the_group_says_accepting_the_item_alone_leaves_the_stock_in_waiting(self):
        group = [{"needed_by": 1, "needs": [], "text": {"noun": "Stock item"}},
                 {"needed_by": 0, "needs": [1], "text": {"noun": "Stock in"}}]
        words = review.group_words(group)
        self.assertIn("Accepting only the Stock item leaves the Stock in waiting.", words)
        self.assertIn("Rejecting the Stock item rejects the Stock in too.", words)

    def test_the_dependent_button_names_what_it_adds(self):
        page = (TEMPLATES / "review.html").read_text(encoding="utf-8")
        self.assertIn("{{ p.text.noun }} and its new {{ p.needs_nouns[0] }}", page)


class MacReadMeWordsTests(unittest.TestCase):
    def setUp(self):
        self.bundled = " ".join(build_macos.README_TXT.split())
        self.readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())

    def test_nothing_overpromises(self):
        self.assertNotIn("Nothing is sent anywhere", self.bundled)
        for text in (self.bundled, self.readme):
            self.assertNotIn("You only do this once", text)
            self.assertNotIn("Only your account can open it", text)

    def test_a_connected_helper_is_not_ignored(self):
        self.assertIn("does not send your records to an online service by itself", self.bundled)
        self.assertIn("If you connect an online helper, information you allow it to read may be sent by that helper",
                      self.bundled)

    def test_each_unsigned_build_may_warn_again_and_the_account_claim_is_narrow(self):
        for text in (self.bundled, self.readme):
            self.assertIn("each new unsigned preview build", text)
            self.assertIn("Someone with access to this Mac account or its backups may be able to read", text)


if __name__ == "__main__":
    unittest.main()
