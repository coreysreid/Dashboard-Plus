"""Tests for decision 0135: link names that include their record, a way-out text that tells two doors apart, and the folded Add buttons."""
import re

from support import ROOT
from test_bar_charts import BarsTestCase
from test_exit_sketch import SketchTestCase


class SketchTextNamesBothEnds(SketchTestCase):
    def test_two_doors_to_one_name_on_different_floors_read_differently(self):
        hall1 = self.room("Hallway", floor="street")
        hall2 = self.room("Hallway", floor="up1")
        a = self.room("Bedroom 2", floor="street")
        b = self.room("Bedroom 3", floor="up1")
        self.join(a, hall1)
        self.join(b, hall2)
        text = self.text("/exit-sketch/text")
        lines = re.findall(r'data-connection="\d+">(?:<a [^>]*>)?([^<]+)', text)
        joined = " ".join(lines)
        self.assertIn("Door from Bedroom 2 to Hallway", joined)
        self.assertIn("Door from Bedroom 3 to Hallway", joined)
        self.assertEqual(len(lines), len(set(lines)), lines)


class AccessibleNamesTests(BarsTestCase):
    MODULES = tuple(p.name for p in sorted((ROOT / "modules").iterdir()) if p.is_dir())

    def test_a_person_with_many_add_buttons_gets_one_fold_that_names_them(self):
        jane = self.store.create("people__people", {"name": "Jane Example"})
        page = self.page(f"/t/people__people/{jane}")
        self.assertIn("<summary>Add something linked to Jane Example…</summary>", page)
        fold = page[page.index('class="add-fold"'):]
        fold = fold[:fold.index("</details>")]
        self.assertGreater(fold.count('class="button quiet"'), 4)  # every button is still a real link, no script
        self.assertNotIn("<script", fold)

    def test_a_record_with_few_add_buttons_keeps_them_open(self):
        page = self.page(f"/t/pets__pets/{self.rex}")
        self.assertNotIn('class="add-fold"', page)

    def test_the_fold_has_styles_for_small_screens(self):
        self.assertIn(".add-list", self.page("/"))

    def test_home_and_needs_attention_links_name_their_record(self):
        for path in ("/", "/attention"):
            page = self.page(path)
            for label in re.findall(r'aria-label="((?:Look at this|Fill this in)[^"]*)"', page):
                self.assertRegex(label, r"^(Look at this|Fill this in): .{3,}")
            self.assertNotRegex(page, r'<a (?![^>]*aria-label)[^>]*>(Look at this|Fill this in)</a>')

    def test_two_weigh_ins_in_the_dot_chart_table_have_their_own_names(self):
        for day, kilos in (("2026-10-01", 20), ("2026-10-08", 21)):
            self.store.create("pets__weigh_ins", {"pet": self.rex, "day": day, "weight": kilos})
        page = self.page(f"/t/pets__pets/{self.rex}")
        names = re.findall(r'aria-label="(Open this weigh-in[^"]*)"', page)
        self.assertGreaterEqual(len(names), 2)
        self.assertEqual(len(names), len(set(names)), names)
