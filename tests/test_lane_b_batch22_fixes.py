"""Tests for decision 0142: the fixes from Lane B's batch 22 checks (calendars, bars, timeline, private lists, Stock names), one test per finding fixed."""
import json
import re
from datetime import date

from support import ROOT, TempDirTestCase
from dashboard.core import bars, settings, sync_sharing, tidy
from dashboard.web import display
from test_calendars_rest import RestCase, LOANS, main as rest_main
from test_module_medicine_doses import TABLE as DOSES
from test_no_fraud_grade_data_0141 import BASE, CARD, FraudGuardTestCase
from test_module_pet_feeding import FeedingTestCase, TABLE as FEED
from test_private_lists_and_dose_calendar import CAL, PrivateDoseCase

TEMPLATES = ROOT / "src" / "dashboard" / "web" / "templates"


def plain(page: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))


class PrintTests(TempDirTestCase):
    def test_every_calendar_day_list_is_opened_for_paper(self):
        text = (TEMPLATES / "_calendar.html").read_text(encoding="utf-8")
        self.assertIn('<details class="cal-list" data-print-open', text)

    def test_the_print_rules_hide_dead_buttons_and_stack_the_timeline(self):
        base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
        timeline = base[base.index("@media print { .tl-nav"):]
        timeline = timeline[:timeline.index("footer {")]
        for part in ("a[data-hide-details]", ".tl-text a", "flex: 1 1 100%"):
            self.assertIn(part, timeline)
        calendar = base[base.index(".cal-nav, .cal-wrap form.actions"):][:200]
        self.assertIn("a[data-hide-details]", calendar)


class PrivateOrdinalTests(PrivateDoseCase):
    def test_the_names_are_people_in_order_never_a_record_number(self):
        shown = display.private_subject_names([{"id": 9, "name": "x"}, {"id": 4, "name": "y"}])
        self.assertEqual([(s["id"], s["name"]) for s in shown], [(4, "Person 1"), (9, "Person 2")])
        for path in (CAL, f"{CAL}?subject={self.rosa}&month=2026-11", f"/bars/{DOSES}/doses?subject={self.rosa}"):
            text = self.page(path, self.web)
            self.assertIn("Person 1", text, path)
            self.assertNotRegex(text, r"Given to #\d", path)
            self.assertNotIn("Rosa Garcia", text, path)


class LoanWordsTests(RestCase):
    def test_a_loan_says_not_marked_returned_yet(self):
        self.store.update(LOANS, self.drill, {"due_back": "2026-11-10"})
        text = rest_main(self.page("/to-do/calendar?month=2026-11"))
        self.assertIn("due since 10/11/26, not marked returned yet", text)
        self.assertNotIn("return due since 10/11/26, not recorded as done yet", text)

    def test_a_us_household_hears_the_month_first(self):
        settings.put(self.conn, "household.country", "United States")
        page = self.page("/to-do/calendar?month=2026-11")
        self.assertIn("November 26", page)
        self.assertNotIn("26 November", page)


class BarsFixTests(FeedingTestCase):
    def test_the_page_opens_on_whoever_has_the_latest_entry(self):
        zed = self.records.create("pets__pets", {"name": "Zed", "species": "dog"})
        self.feed(pet=zed, at="2026-11-19T07:15:00")
        text = self.page(f"/bars/{FEED}/food")
        self.assertIn('<strong aria-current="page">Zed</strong>', text)
        self.assertIn("Showing the one with the most recent entry", text)
        chosen = self.page(f"/bars/{FEED}/food?subject={self.luna}")
        self.assertIn('<strong aria-current="page">Luna</strong>', chosen)
        self.assertNotIn("Showing the one with the most recent entry", chosen)

    def test_nobody_has_an_entry_keeps_the_first_name(self):
        text = self.page(f"/bars/{FEED}/food")
        self.assertIn('<strong aria-current="page">Luna</strong>', text)

    def test_a_waiting_suggestion_is_said_but_never_counted(self):
        self.feed(at="2026-11-10T07:15:00")
        helper, _ = self.helper()
        self.suggest(helper, {"given_at": "2026-11-19T07:15:00"})
        page = self.page(f"/bars/{FEED}/food?subject={self.rex}&by=day")
        text = plain(page[page.index("<main>"):page.index("</main>")])
        self.assertIn("Nothing accepted yet; 1 waiting on Review", text)
        self.assertNotIn("240 g", text)
        found = bars.build(self.conn, self.info, self.info.table.bars[0], self.rex, "day", date(2026, 11, 20),
                           "monday", date(2026, 11, 20))
        self.assertEqual((sum(p.waiting for p in found), sum(p.count for p in found)), (1, 1))


class TimelineWordsTests(TempDirTestCase):
    def test_no_wrong_possessive_in_the_back_links(self):
        for name in ("timeline.html", "bars.html", "calendar.html", "daily.html"):
            self.assertNotIn("'s page</a>", (TEMPLATES / name).read_text(encoding="utf-8").replace("person's page", ""), name)


class FeedingTimelineTests(FeedingTestCase):
    def test_a_feeding_with_no_amount_says_so(self):
        self.records.create(FEED, {"pet": self.rex, "given_at": "2026-11-19T07:15:00", "kind": "bowl",
                                   "food": "Example dry dog food"})
        page = self.page(f"/timeline/pets__pets/{self.rex}")
        text = plain(page[page.index("<main>"):page.index("</main>")])
        self.assertIn("recorded on", text)
        self.assertIn("no amount written down", text)


class StockExampleTests(TempDirTestCase):
    def test_no_example_stock_item_names_a_medicine_and_a_person(self):
        found = (ROOT / "examples" / "households" / "garcia.toml").read_text(encoding="utf-8")
        self.assertNotIn("Metformin 500 mg (Rosa)", found)
        self.assertIn("Prescription tablets (blister packs)", found)

    def test_the_stock_name_field_explains_where_medicines_belong(self):
        labels = (ROOT / "modules" / "stock" / "labels.toml").read_text(encoding="utf-8")
        self.assertIn("Keep a medicine's name, strength and who takes it in that person's medication details", labels)


class OldCardNumberTests(FraudGuardTestCase):
    """Values saved before decision 0141 that hold a full card number: never shown in full by Show, and cleaned out
    of the waiting (unsent) change log."""

    def setUp(self):
        super().setUp()
        self.conn.execute("UPDATE utilities__services SET notes = ? WHERE id = ?", (f"Paid with {CARD}", self.service))
        self.conn.commit()

    def test_show_gives_only_the_last_four_digits(self):
        client = self.client()
        for accept in ("application/json", "text/html"):
            reply = client.post(f"/t/utilities__services/{self.service}/reveal",
                                data={"_csrf": client.csrf, "column": "notes"}, base_url=BASE,
                                headers={"Accept": accept})
            text = json.loads(reply.get_data(as_text=True))["text"] if accept == "application/json" else reply.get_data(as_text=True)
            self.assertEqual(reply.status_code, 200)
            self.assertNotIn("4111 1111", text)
            self.assertNotIn(CARD.replace(" ", ""), text)
            self.assertIn("••••1111", text)

    def test_the_tidy_page_lists_it(self):
        found = [(i.record_id, i.column, i.kind) for i in tidy.find(self.store)]
        self.assertIn((self.service, "notes", "card"), found)

    def test_a_card_number_in_a_waiting_change_line_is_masked(self):
        self.conn.execute(
            "INSERT INTO core__sync_changes (epoch, operation_id, action, table_name, global_id, base_revision, "
            "revision, patch, exchange_schema, at) VALUES (1, 'op-card', 'update', 'people__people', 'g-1', 1, 2, ?, 1, "
            "'2026-11-27T00:00:00Z')", (json.dumps({"notes": f"Card {CARD}", "name": "Bob Example"}),))
        self.conn.commit()
        self.assertGreaterEqual(sync_sharing.mask_waiting_cards(self.conn), 1)
        lines = " ".join(str(json.loads(r[0]).get("notes") or "") for r in self.conn.execute("SELECT patch FROM core__sync_changes"))
        self.assertNotIn("4111 1111", lines)
        self.assertIn("••••1111", lines)
        self.assertEqual(sync_sharing.mask_waiting_cards(self.conn), 0, "nothing left to change")
