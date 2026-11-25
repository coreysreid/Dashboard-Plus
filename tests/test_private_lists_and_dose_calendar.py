"""Tests for private lists and the dose calendar (decision 0121): nothing of a private table before a pressed Show, and doses as ● and a count by day.

A synthetic medicine name, amount and giver are planted and looked for in the HTML source of every page that could
show them: the list, a record, a person's page, the calendar, the day page, Home, Needs attention, Things to do,
questions, drills, Review and Settings. A link with ?show=1 never shows them; only a POST with the session check does."""
import shutil

from support import ROOT
from dashboard.core import modules, questions, settings
from dashboard.core.prompts import Match
from dashboard.web import display
from test_module_medicine_doses import AMOUNT, BASE, MODULE_TOML, SECRET, TABLE, DoseTestCase

GIVER = "Quillon Sentinelperson"  # an invented giver: named only after Show
PRIVATE = "Private history — press Show to see it."
CAL = f"/calendar/{TABLE}"


class PrivateDoseCase(DoseTestCase):
    def setUp(self):
        super().setUp()
        self.giver = self.records.create("people__people", {"name": GIVER, "lives_here": False})
        # 19 Nov: two doses (one with an amount); 20 Nov ("today" in these tests) has none.
        self.first = self.dose(at="2026-11-19T08:00:00", given_by=self.giver, amount=AMOUNT, unit="drop")
        self.second = self.dose(at="2026-11-19T18:30:00", given_by=self.giver)
        self.web = self.client()

    def shown(self, path, **data):
        reply = self.post(self.web, path, **data)
        self.assertEqual(reply.status_code, 200, path)
        return reply.get_data(as_text=True)

    def assert_nothing_private(self, text, where, giver=True):
        for words in (SECRET, AMOUNT, "7.25 drops") + ((GIVER,) if giver else ()):
            self.assertNotIn(words, text, where)


class PrivateListTests(PrivateDoseCase):
    def test_the_list_says_only_how_many_until_show_and_a_link_never_opens_it(self):
        for path in (f"/t/{TABLE}", f"/t/{TABLE}?show=1", f"/t/{TABLE}?sort=given_at"):
            text = self.page(path, self.web)
            self.assert_nothing_private(text, path)
            self.assertIn(PRIVATE, text)
            self.assertIn("2 records", text)
            for words in ("Rosa Garcia", "8:00", "08:00", "Medication #", "Important details #", "data-reveal=",
                          f"/t/{TABLE}/{self.first}\""):
                self.assertNotIn(words, text, f"{path}: {words}")
            self.assertIn(f'action="/t/{TABLE}/show"', text)
        self.page(f"/t/{TABLE}/rows?offset=0", self.web, status=404)  # rows never come from an address
        self.page(f"/t/{TABLE}/suggest?column=given_at&q=a", self.web, status=404)

    def test_show_is_a_pressed_button_that_lists_the_latest_entries_only_on_that_page(self):
        text = self.shown(f"/t/{TABLE}/show")
        self.assertIn(GIVER, text)
        self.assertIn("Rosa Garcia", text)
        self.assertIn("Hide details", text)
        self.assertLess(text.index(f"/t/{TABLE}/{self.second}\""), text.index(f"/t/{TABLE}/{self.first}\""))
        self.assertNotIn(SECRET, text)  # the medicine's words stay behind their own Show (decision 0120)
        missing = self.web.post(f"/t/{TABLE}/show", base_url=BASE)  # no session check: refused
        self.assertEqual(missing.status_code, 400)
        self.assertNotIn(GIVER, missing.get_data(as_text=True))
        self.assertEqual(self.post(self.web, "/t/people__people/show").status_code, 404)  # ordinary lists: no Show

    def test_a_record_page_shows_only_its_number_until_show_and_saving_hides_it_again(self):
        for path in (f"/t/{TABLE}/{self.first}", f"/t/{TABLE}/{self.first}?show=1"):
            text = self.page(path, self.web)
            self.assert_nothing_private(text, path)
            self.assertIn(PRIVATE, text)
            self.assertIn(f"Medicine doses #{self.first}", text)
            for words in ("Rosa Garcia", "8:00", "08:00", "Medication #", "History", "Delete"):
                self.assertNotIn(words, text, f"{path}: {words}")
        text = self.shown(f"/t/{TABLE}/{self.first}/show")
        self.assertIn(GIVER, text)
        self.assertIn("2026-11-19T08:00", text)
        self.assertIn("History", text)
        self.assertNotIn(SECRET, text)
        self.assertNotIn(AMOUNT, text)  # the amount is a private detail with its own Show (decision 0059)
        saved = self.post(self.web, f"/t/{TABLE}/{self.second}", recipient=str(self.rosa), medication=str(self.med),
                          given_at="2026-11-19T18:45", given_by=str(self.giver))
        self.assertEqual(saved.status_code, 302)
        after = self.page(saved.headers["Location"], self.web)
        self.assertIn("Saved.", after)
        self.assert_nothing_private(after, "after saving")
        self.assertEqual(self.post(self.web, f"/t/people__people/{self.rosa}/show").status_code, 404)

    def test_a_deleted_dose_is_hidden_too_and_comes_back_from_the_shown_page(self):
        self.records.delete(TABLE, self.second)
        text = self.page(f"/t/{TABLE}/{self.second}", self.web)
        self.assertIn("(deleted)", text)
        self.assert_nothing_private(text, "deleted")
        self.assertIn("Restore it", self.shown(f"/t/{TABLE}/{self.second}/show"))

    def test_no_other_page_carries_the_medicine_the_amount_or_the_giver(self):
        paths = ["/", "/attention", "/to-do", "/to-do/week", "/to-do/month", "/to-do/year", "/to-do/no-date",
                 "/questions", "/drills", "/review", "/settings", "/settings/export", "/settings/backups",
                 "/settings/helpers", f"/t/people__people/{self.rosa}", f"/daily/{TABLE}?subject={self.rosa}",
                 f"/daily/{TABLE}?subject={self.rosa}&day=2026-11-19", f"/daily/{TABLE}?subject={self.rosa}&show=1",
                 f"{CAL}?subject={self.rosa}&month=2026-11", f"{CAL}?subject={self.rosa}&month=2026-11&show=1"]
        for path in paths:
            response = self.web.get(path, base_url=BASE)
            if response.status_code == 404:
                continue
            self.assertEqual(response.status_code, 200, path)
            self.assert_nothing_private(response.get_data(as_text=True), path)
        self.assertEqual(self.web.get("/to-do/calendar", base_url=BASE).status_code, 404)  # no due-date calendar

    def test_a_record_name_and_a_question_match_never_carry_a_private_record(self):
        row = self.records.get(TABLE, self.first)
        self.assertEqual(display.display_name(self.info, row, self.records), f"Medicine doses #{self.first}")
        prompt = type("P", (), {"match": Match("medicine_doses.doses", {}, ["given_by"], []), "ask_again": None})()  # looks in it
        found = questions.candidates(self.conn, self.registry, prompt)
        self.assertTrue(found)
        self.assertTrue(all(c.private for c in found))


class DoseCalendarTests(PrivateDoseCase):
    def test_the_calendar_shows_a_mark_and_how_many_only_until_show(self):
        for path in (f"{CAL}?subject={self.rosa}&month=2026-11", f"{CAL}?subject={self.rosa}&month=2026-11&show=1"):
            text = self.page(path, self.web)
            self.assert_nothing_private(text, path)
            self.assertIn("Dose calendar", text)
            self.assertIn("2 doses recorded", text)
            self.assertIn('class="cal-chip cal-recorded"', text)
            self.assertIn(PRIVATE, text)
            for words in ("8:00", "6:30", f'href="/t/{TABLE}/', "Medication #", "chip cal-due", "chip cal-planned",
                          "Due today", "Planned", "overdue", "not given"):
                self.assertNotIn(words, text, f"{path}: {words}")
            self.assertIn(f"/daily/{TABLE}?subject={self.rosa}&amp;day=2026-11-19", text)  # See this day
        text = self.shown(CAL, subject=str(self.rosa), month="2026-11")
        for words in ("8:00 am · dose", "6:30 pm · dose", SECRET, "7.25 drops", f"Who gave it: {GIVER}",
                      "no amount entered", "Hide details"):
            self.assertIn(words, text)
        self.assertEqual(self.post(self.web, "/calendar/pet_feeding__servings").status_code, 404)

    def test_the_persons_page_has_this_months_dose_calendar_with_counts_only(self):
        text = self.page(f"/t/people__people/{self.rosa}", self.web)
        self.assertIn("Dose calendar", text)
        self.assertIn("2 doses recorded", text)
        self.assertIn(f'action="{CAL}"', text)
        self.assert_nothing_private(text, "person page")
        self.assertNotIn("6:30 pm", text)
        self.assertNotIn("Dose calendar", self.page(f"/t/people__people/{self.maria}", self.web))  # no medicine
        self.assertIn("Dose calendar", self.page(f"/t/people__people/{self.sofia}", self.web))  # has one
        chooser = self.page(f"{CAL}?month=2026-11", self.web)
        self.assertNotIn(f"subject={self.maria}", chooser)  # only people the dose log applies to

    def test_an_empty_month_is_never_missed_and_the_day_page_names_the_giver_only_after_show(self):
        empty = self.page(f"{CAL}?subject={self.rosa}&month=2026-10", self.web)
        self.assertIn("No dose entry recorded for this person in October 2026.", empty)
        self.assertIn("It does not mean anything was missed.", empty)
        self.assertNotIn(PRIVATE, empty)  # nothing to show
        day = self.page(f"/daily/{TABLE}?subject={self.rosa}&day=2026-11-19", self.web)
        self.assertIn(">8:00 am · dose</a>", day)
        self.assertIn("See the month as a calendar", day)
        self.assert_nothing_private(day, "day page")
        shown = self.shown(f"/daily/{TABLE}", subject=str(self.rosa), day="2026-11-19")
        self.assertIn(f"Who gave it: {GIVER}", shown)

    def test_switched_off_there_is_no_calendar_and_on_again_it_is_back(self):
        settings.set_module_enabled(self.conn, "medicine_doses", False)
        client = self.client()
        self.page(f"{CAL}?subject={self.rosa}", client, status=404)
        self.assertEqual(self.post(client, CAL, subject=str(self.rosa)).status_code, 404)
        self.assertNotIn("Dose calendar", self.page(f"/t/people__people/{self.rosa}", client))
        settings.set_module_enabled(self.conn, "medicine_doses", True)
        self.assertIn("Dose calendar", self.page(f"/t/people__people/{self.rosa}", self.client()))

    def test_a_private_calendar_may_not_declare_a_state_a_due_date_or_another_look(self):
        tables = (ROOT / "modules" / "medicine_doses" / "tables.toml").read_text(encoding="utf-8")
        bad = tables.replace('entry = ["dose", "doses"]\n', 'entry = ["dose", "doses"]\ndue = true\nlook = "done"\n')
        bad = bad.replace("[tables.doses.calendar]", "[tables.doses.calendar]\nstate = \"unit\"")
        self.make_module("dosecal", module=MODULE_TOML, tables=bad, labels=None,
                         root="bad")
        shutil.copytree(ROOT / "modules" / "people", self.tmp / "bad" / "people")
        _, failures = modules.discover(self.tmp / "bad")
        text = " ".join(failures.get("dosecal", []))
        self.assertIn("a private table's calendar can't use 'state'", text)
        self.assertIn("a private table's calendar can't use 'due'", text)
        self.assertIn("uses the look \"recorded\" only", text)
