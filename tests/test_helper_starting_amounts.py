"""Tests for decision 0102: a new Stock item with its starting amount as one suggestion, and the helper's starting message."""
import json
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, proposals, records, settings, startup
from dashboard.core.proposals import ProposalError
from dashboard.web.app import create_app

PORT = 5139
BASE = f"http://127.0.0.1:{PORT}"
WHY = "Counted in the invented pantry on Saturday"
PRIVATE = "QX-7731-INVENTED"  # a made-up private vehicle registration, which must never leave


class StartingTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("stock", "vehicles", "people"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        settings.put(self.conn, "setup.done", True)
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.csrf = self.app.config["CSRF_TOKEN"]
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.shelf = self.store.create("stock__places", {"name": "Invented shelf"})
        self.beans = self.store.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 5})
        self.car = self.store.create("vehicles__vehicles", {"name": "Invented hatchback", "registration": PRIVATE})
        self.helper, self.key = helpers.issue(self.conn, self.data, "Move-in helper", "suggest", ["stock", "vehicles"])
        self.pets_only, self.pets_key = helpers.issue(self.conn, self.data, "People helper", "suggest", ["people"])
        self.reader, self.reader_key = helpers.issue(self.conn, self.data, "Look helper", "read", ["stock"])

    def rice(self, **more):
        return {"table": "stock__items", "values": dict({"name": "Invented rice", "category": "pantry", "unit": "kg",
                                                         "quantity": 2, "expires": "2027-09-20", "place": self.shelf},
                                                        **more)}

    def send(self, entries, key="count-1", helper=None):
        return proposals.submit(self.conn, self.registry, helper or self.helper,
                                {"request_key": key, "why": WHY, "entries": entries})[0]

    def refused(self, entries, status=422, code="invalid"):
        with self.assertRaises(ProposalError) as caught:
            self.send(entries)
        self.assertEqual((caught.exception.status, caught.exception.code), (status, code))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)
        return caught.exception

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE deleted_at IS NULL").fetchone()[0]

    def rice_row(self):
        return self.conn.execute("SELECT * FROM stock__items WHERE name = 'Invented rice'").fetchone()

    def page(self, path):
        self.client.get("/?key=session-key", base_url=BASE)
        return self.client.get(path, base_url=BASE).get_data(as_text=True)

    def api_get(self, path, key=None):
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return self.client.get(path, base_url=BASE, headers=headers)


class OneEntryStockTests(StartingTestCase):
    def test_nothing_is_added_until_accepted_then_the_item_and_its_first_batch_arrive_together(self):
        before = (self.count("stock__items"), self.count("stock__lots"), self.count("stock__movements"))
        result = self.send([self.rice()])
        self.assertEqual(result["state"], "waiting")
        self.assertEqual((self.count("stock__items"), self.count("stock__lots"), self.count("stock__movements")),
                         before)
        proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])
        item = self.rice_row()
        self.assertEqual((item["quantity"], item["expires"], item["unit"]), (2, "2027-09-20", "kg"))
        batch = self.conn.execute("SELECT * FROM stock__lots WHERE item = ?", (item["id"],)).fetchall()
        self.assertEqual([(b["quantity"], b["expires"], b["place"]) for b in batch], [(2, "2027-09-20", self.shelf)])
        self.assertEqual(batch[0]["source"], self.helper.actor)
        self.assertEqual(self.count("stock__movements"), before[2])  # no Stock in is needed

    def test_it_is_the_same_as_the_persons_own_add_form(self):
        self.store.create("stock__items", {"name": "Form rice", "category": "pantry", "unit": "kg", "quantity": 2,
                                           "expires": "2027-09-20", "place": self.shelf})
        proposals.accept(self.conn, self.registry, self.send([self.rice()])["proposals"][0]["id"])
        keep = ("quantity", "expires", "unit", "category", "place")
        form = self.conn.execute("SELECT * FROM stock__items WHERE name = 'Form rice'").fetchone()
        self.assertEqual({k: self.rice_row()[k] for k in keep}, {k: form[k] for k in keep})
        lots = lambda item: [(r["quantity"], r["expires"], r["place"]) for r in self.conn.execute(  # noqa: E731
            "SELECT * FROM stock__lots WHERE item = ?", (item,))]
        self.assertEqual(lots(self.rice_row()["id"]), lots(form["id"]))

    def test_it_counts_as_one_suggestion_against_the_limits(self):
        self.send([self.rice(), self.rice(name="Invented oats")])
        self.assertEqual(proposals.used_today(self.conn, self.helper), 2)
        self.assertEqual(proposals.waiting_for(self.conn, self.helper), 2)

    def test_rejecting_it_adds_nothing(self):
        result = self.send([self.rice()])
        proposals.reject(self.conn, result["proposals"][0]["id"])
        self.assertIsNone(self.rice_row())
        self.assertEqual(self.count("stock__lots"), 1)  # only the beans' own batch

    def test_an_unknown_place_is_refused_with_a_plain_next_step(self):
        for place in (99999, "Invented shelf"):
            with self.subTest(place):
                error = self.refused([self.rice(place=place)])
                problem = error.problems[0]
                self.assertEqual((problem["entry"], problem["field"]), (0, "place"))
                self.assertIn("Look up Places first", problem["message"])
                self.assertIn("/api/v1/tables/stock__places/records", problem["message"])
                self.assertIn('{"ref": N}', problem["message"])

    def test_bad_amounts_dates_and_units_are_refused_like_the_form(self):
        for values, field in (({"quantity": -1}, "quantity"), ({"quantity": "lots"}, "quantity"),
                              ({"expires": "20/09/27"}, "expires"), ({"unit": ["kg"]}, "unit"),
                              ({"unit": {"kind": "kg"}}, "unit")):
            with self.subTest(values):
                error = self.refused([self.rice(**values)])
                self.assertEqual(error.problems[0]["field"], field)

    def test_a_new_place_and_an_item_kept_there_go_together_with_a_ref(self):
        result = self.send([{"table": "stock__places", "values": {"name": "Invented garage"}},
                            self.rice(place={"ref": 0})])
        self.assertEqual(result["proposals"][1]["depends_on"], [0])
        proposals.accept(self.conn, self.registry, result["proposals"][1]["id"])
        garage = self.conn.execute("SELECT id FROM stock__places WHERE name = 'Invented garage'").fetchone()[0]
        lot = self.conn.execute("SELECT place, quantity FROM stock__lots WHERE item = ?", (self.rice_row()["id"],)).fetchone()
        self.assertEqual((lot["place"], lot["quantity"]), (garage, 2))

    def test_the_two_entry_group_still_works(self):
        new = {"table": "stock__items", "values": {"name": "Invented lentils", "category": "pantry", "unit": "bags"}}
        stock_in = {"table": "stock__movements", "values": {"item": {"ref": 0}, "reason": "bought", "amount": 3,
                                                            "happened_on": "2026-11-20"}}
        result = self.send([new, stock_in])
        proposals.accept(self.conn, self.registry, result["proposals"][1]["id"])
        row = self.conn.execute("SELECT quantity FROM stock__items WHERE name = 'Invented lentils'").fetchone()
        self.assertEqual(row["quantity"], 3)
        self.assertEqual([r[0] for r in self.conn.execute("SELECT status FROM core__proposals ORDER BY position")],
                         ["accepted", "accepted"])

    def test_a_starting_amount_on_a_link_from_a_stock_in_to_a_new_item_adds_both(self):
        stock_in = {"table": "stock__movements", "values": {"item": {"ref": 0}, "reason": "bought", "amount": 1,
                                                            "happened_on": "2026-11-20"}}
        proposals.accept_batch(self.conn, self.registry, self.send([self.rice(), stock_in])["batch_id"])
        self.assertEqual(self.rice_row()["quantity"], 3)  # what was sent: 2 on hand, then 1 more bought

    def test_review_shows_the_starting_amount(self):
        self.send([self.rice()])
        page = self.page("/review")
        self.assertIn("Amount on hand: <bdi>2</bdi> · Unit: <bdi>kg</bdi> · Where it is: <bdi>Invented shelf</bdi> · "
                      "Use by: <bdi>20/09/27</bdi>", page)


class GuideTests(StartingTestCase):
    def guide(self, key=None):
        response = self.api_get("/api/v1/guide", key or self.key)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:200])
        return response.get_json()

    def test_it_lists_the_granted_lists_their_fields_the_stock_model_and_the_limits(self):
        text = self.guide()["text"]
        for words in ("Stock items (stock__items): you may suggest new records here.", "Places (stock__places)",
                      "Vehicles (vehicles__vehicles)", "name: Name (text, required)",
                      "quantity: Amount on hand", "Links to stock__places", "send ONE entry to stock__items",
                      "the record and its first batch are added together", "Do not also send a Stock in and out",
                      "At most 50 entries in one send", "200 suggestions a day", "200 are left today",
                      "they can allow more on the Review page", "At most 500 of this helper's suggestions",
                      "waits on the Review page", '"source"', '{"ref": N}', "Send small batches",
                      "Never ask for the access key", "what you could not fit",
                      "Private, never for helpers: Registration or plate number"):
            self.assertIn(words, text)
        self.assertNotIn("people__", text)  # People was not given, so even the link to it is left out
        self.send([self.rice()])
        self.assertIn("199 are left today", self.guide()["text"])
        self.assertEqual(self.guide()["limits"]["suggestions_waiting"], 1)

    def test_it_holds_no_records_no_private_values_and_no_key(self):
        text = json.dumps(self.guide())
        for secret in (PRIVATE, "Invented hatchback", "Invented shelf", "Kidney beans", self.key, "dph_"):
            self.assertNotIn(secret, text)

    def test_it_needs_a_working_key_and_follows_the_grant(self):
        self.assertEqual(self.api_get("/api/v1/guide").status_code, 401)
        self.assertEqual(self.api_get("/api/v1/guide", "dph_" + "x" * 43).status_code, 401)
        people = self.guide(self.pets_key)["text"]
        self.assertIn("People (people__people)", people)
        self.assertNotIn("stock__", people)
        look = self.guide(self.reader_key)["text"]
        self.assertIn("Look at the lists below only", look)
        self.assertIn("Stock items (stock__items): look only.", look)
        for words in ("HOW TO SEND", "send ONE entry", "suggestions a day"):
            self.assertNotIn(words, look)
        helpers.turn_off(self.conn, self.data, self.helper.id)
        self.assertEqual(self.api_get("/api/v1/guide", self.key).status_code, 401)

    def test_the_tables_listing_marks_the_starting_fields_as_suggestible_for_a_new_item(self):
        tables = self.api_get("/api/v1/tables", self.key).get_json()["tables"]
        items = next(t for t in tables if t["table"] == "stock__items")
        columns = {c["name"]: c for c in items["columns"]}
        for name in ("quantity", "expires", "place"):
            self.assertTrue(columns[name]["can_suggest"], name)
            self.assertIn("Only when suggesting a new record", columns[name]["note"])
        self.assertEqual(items["worked_out"], ["expires", "quantity"])


class SettingsPageTests(StartingTestCase):
    def test_each_helper_on_the_helpers_page_has_its_starting_message_and_no_key(self):
        page = self.page("/settings/helpers")
        self.assertIn("Starting message for your assistant", page)
        self.assertIn('id="starting-message-%d"' % self.helper.id, page)
        self.assertIn("Copy starting message", page)
        self.assertIn("Stock items (stock__items): you may suggest new records here.", page)
        self.assertIn("People (people__people)", page)  # the People helper's own message
        for secret in (self.key, self.pets_key, PRIVATE, "Invented hatchback", "Kidney beans"):
            self.assertNotIn(secret, page)

    def test_a_turned_off_helper_has_no_starting_message(self):
        helpers.turn_off(self.conn, self.data, self.pets_only.id)
        page = self.page("/settings/helpers")
        self.assertNotIn('id="starting-message-%d"' % self.pets_only.id, page)

    def test_the_new_key_page_shows_the_message_beside_the_settings_and_the_key_only_once(self):
        page = self.page("/settings/helpers")
        token = re.search(r'name="form_token" value="([^"]+)"', page).group(1)
        response = self.client.post("/settings/helpers", base_url=BASE, data={
            "_csrf": self.csrf, "form_token": token, "name": "Pantry counter", "access": "suggest",
            "modules": ["stock"]})
        self.assertEqual(response.status_code, 201)
        html = response.get_data(as_text=True)
        key = re.search(r'value="(dph_[A-Za-z0-9_-]+)"', html).group(1)
        self.assertEqual(html.count(key), 1)
        message = re.search(r'<pre id="starting-message"[^>]*>(.*?)</pre>', html, re.S).group(1)
        self.assertIn("send ONE entry to stock__items", message)
        self.assertNotIn("vehicles__", message)
        self.assertNotIn("dph_", message)
