"""Tests for the screens: Settings, Helpers (making and turning off keys) and Review (accepting and rejecting)."""
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, proposals, records, settings, startup
from dashboard.web.app import create_app

PORT = 5127
BASE = f"http://127.0.0.1:{PORT}"


class ReviewScreenTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        settings.put(self.conn, "setup.done", True)
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.csrf = self.app.config["CSRF_TOKEN"]
        self.client.get("/?key=session-key", base_url=BASE)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.helper, self.key = helpers.issue(self.conn, self.data, "Receipt helper", "suggest", ["stock"])
        self.beans = self.store.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 5})

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def text(self, path):
        return self.get(path).get_data(as_text=True)

    def post(self, path, data=None, token=True):
        return self.client.post(path, data=dict(data or {}, **({"_csrf": self.csrf} if token else {})), base_url=BASE)

    def suggest(self, entries, key="r1", why="Copied from Saturday's receipt"):
        result, _ = proposals.submit(self.conn, self.registry, self.helper,
                                     {"request_key": key, "why": why, "entries": entries})
        return result

    def place(self, name="Garage"):
        return {"table": "stock__places", "values": {"name": name}}

    def used(self, amount):
        return {"table": "stock__movements", "values": {"item": self.beans, "reason": "used", "amount": amount}}

    # ----- Settings -> Helpers ---------------------------------------------------------------------
    def test_settings_links_to_helpers(self):
        page = self.text("/settings")
        self.assertIn('href="/settings/helpers"', page)
        self.assertIn("Helpers: let an assistant look at or suggest records", page)

    def test_the_helpers_page_explains_and_shows_the_address(self):
        page = self.text("/settings/helpers")
        self.assertIn("Nothing a helper suggests is added until you accept it", page)
        self.assertIn(f"http://127.0.0.1:{PORT}/api/v1", page)
        self.assertIn("This address changes each time Dashboard opens", page)
        self.assertIn("Receipt helper", page)
        self.assertIn("May look and suggest", page)
        self.assertIn("Parts: Household stock", page)
        self.assertIn("Private details: never shared", page)
        self.assertRegex(page, r'name="modules" value="stock"(?! checked)')  # nothing ticked by default

    def test_making_a_key_shows_it_once_and_never_again(self):
        response = self.post("/settings/helpers", {"name": "Pet diary helper", "access": "read", "modules": ["stock"]})
        self.assertEqual(response.status_code, 201)
        page = response.get_data(as_text=True)
        key = re.search(r'value="(dph_[A-Za-z0-9_-]+)"', page).group(1)
        self.assertIn("Copy it now: it will not be shown again.", page)
        self.assertIn("can look at Household stock while Dashboard is open on this computer", page)
        self.assertIn("you can turn it off in Settings", page.replace("You can", "you can"))
        self.assertNotIn(key, self.text("/settings/helpers"))
        self.assertNotIn(key, self.text("/settings"))
        self.assertNotIn(key.encode(), (self.data / "dashboard.db").read_bytes())
        self.assertEqual(self.client.get("/api/v1/me", base_url=BASE, headers={"Authorization": f"Bearer {key}"}).status_code, 200)
        log = self.data / "logs"
        self.assertFalse(log.exists() and key in "".join(p.read_text(errors="replace") for p in log.glob("*")))

    def test_making_a_key_needs_the_pages_own_token(self):
        response = self.post("/settings/helpers", {"name": "X", "access": "read", "modules": ["stock"]}, token=False)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(helpers.all_helpers(self.conn)), 1)

    def test_a_key_needs_a_name_and_a_part(self):
        response = self.post("/settings/helpers", {"name": "", "access": "read", "modules": ["stock"]})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Give the helper a name.", response.get_data(as_text=True))
        response = self.post("/settings/helpers", {"name": "Ok", "access": "read"})
        self.assertIn("Choose at least one part of your records.", response.get_data(as_text=True))
        response = self.post("/settings/helpers", {"name": "Ok", "access": "read", "modules": ["not_a_module"]})
        self.assertIn("Choose at least one part of your records.", response.get_data(as_text=True))
        self.assertEqual(len(helpers.all_helpers(self.conn)), 1)

    def test_turning_off_access_works_at_once_and_keeps_the_history(self):
        self.suggest([self.place()])
        response = self.post(f"/settings/helpers/{self.helper.id}/turn-off")
        self.assertEqual(response.status_code, 302)
        page = self.text(response.headers["Location"])
        self.assertIn("Receipt helper can no longer connect. Its suggestions and history are kept.", page)
        self.assertIn("Access turned off on", page)
        self.assertIn("Its history is kept.", page)
        self.assertEqual(self.client.get("/api/v1/me", base_url=BASE, headers={"Authorization": f"Bearer {self.key}"}).status_code, 401)
        self.assertIn("This helper's access is off. Its earlier suggestions still need your decision.", self.text("/review"))

    # ----- Review ------------------------------------------------------------------------------------
    def test_an_empty_review_page(self):
        page = self.text("/review")
        self.assertIn("Review suggestions", page)
        self.assertIn("No suggestions to review.", page)
        self.assertNotIn("needs a look", self.text("/"))

    def test_a_suggestion_is_shown_in_plain_words_with_its_reason(self):
        self.suggest([{"table": "stock__movements", "values": {"item": self.beans, "reason": "bought", "amount": "4"}}])
        page = self.text("/review")
        self.assertIn("Receipt helper · 1 suggestion", page)
        self.assertIn("Why: Copied from Saturday&#39;s receipt", page)
        self.assertRegex(page, r"Add to <strong>Stock in and out</strong>: Item: Kidney beans.* · Reason: Bought or added")
        self.assertIn("How many: 4", page)
        self.assertIn("Accept", page)
        self.assertIn("Reject", page)

    def test_the_home_page_and_menu_count_what_is_waiting_only_when_something_is(self):
        self.suggest([self.place()], key="a")
        home = self.text("/")
        self.assertIn("1 suggestion needs a look", home)
        self.assertIn("Review <span", home)
        self.suggest([self.place("Shed"), self.place("Cellar")], key="b")
        self.assertIn("3 suggestions need a look", self.text("/"))

    def test_accepting_adds_the_record_and_it_shows_in_its_list(self):
        result = self.suggest([self.place("Garage")])
        response = self.post(f"/review/{result['proposals'][0]['id']}/accept")
        self.assertEqual(response.status_code, 302)
        self.assertIn("Added to Places.", self.text(response.headers["Location"]))
        self.assertIn("Garage", self.text("/t/stock__places"))
        self.assertIn("No suggestions to review.", self.text("/review"))

    def test_rejecting_adds_nothing(self):
        result = self.suggest([self.place("Garage")])
        response = self.post(f"/review/{result['proposals'][0]['id']}/reject")
        self.assertIn("Rejected. Nothing was added to Places.", self.text(response.headers["Location"]))
        self.assertNotIn("Garage", self.text("/t/stock__places"))

    def test_deciding_needs_the_pages_own_token(self):
        result = self.suggest([self.place("Garage")])
        pid = result["proposals"][0]["id"]
        for path in (f"/review/{pid}/accept", f"/review/{pid}/reject", f"/review/batch/{result['batch_id']}/accept-all"):
            self.assertEqual(self.post(path, token=False).status_code, 400)
        self.assertEqual(proposals.pending_count(self.conn), 1)

    def test_the_result_line_cannot_be_made_to_say_anything(self):
        page = self.text("/review?done=added&table=%3Cb%3Eevil%3C/b%3E")
        self.assertIn("Added to your records.", page)
        self.assertNotIn("<b>evil", page)
        self.assertNotIn("anything", self.text("/review?done=<script>anything</script>"))

    def test_accept_all_with_one_stale_row_adds_the_rest_and_explains_the_one(self):
        result = self.suggest([self.place("Garage"), self.used(4), self.place("Shed")])
        self.store.create("stock__movements", {"item": self.beans, "reason": "used", "amount": 3})  # now only 2 left
        response = self.post(f"/review/batch/{result['batch_id']}/accept-all")
        page = self.text(response.headers["Location"])
        self.assertIn("Added 2. 1 could not be added and is still waiting", page)
        self.assertIn("This can&#39;t be added as it is:", page)
        self.assertIn("Reject it, or add the record yourself.", page)
        self.assertIn("more than there is", page)
        self.assertIn("Garage", self.text("/t/stock__places"))
        self.assertEqual(proposals.pending_count(self.conn), 1)
        self.assertEqual(self.store.get("stock__items", self.beans)["quantity"], 2)

    def test_reject_all_for_a_batch(self):
        result = self.suggest([self.place("Garage"), self.place("Shed")])
        response = self.post(f"/review/batch/{result['batch_id']}/reject-all")
        self.assertIn("Rejected 2 suggestions. Nothing was added.", self.text(response.headers["Location"]))
        self.assertEqual(self.store.count("stock__places"), 0)

    def test_deciding_twice_says_so(self):
        result = self.suggest([self.place("Garage")])
        pid = result["proposals"][0]["id"]
        self.post(f"/review/{pid}/reject")
        response = self.post(f"/review/{pid}/accept")
        self.assertIn("already been decided", self.text(response.headers["Location"]))
        self.assertEqual(self.store.count("stock__places"), 0)

    def test_text_a_helper_sends_is_shown_as_text_never_run(self):
        evil = "<script>alert('x')</script>"
        self.suggest([self.place(evil)], why=evil)
        page = self.text("/review")
        self.assertNotIn(evil, page)
        self.assertIn("&lt;script&gt;alert(", page)

    def test_a_suggestion_for_a_switched_off_part_can_only_be_rejected(self):
        result = self.suggest([self.place("Garage")])
        settings.set_module_enabled(self.conn, "stock", False)
        page = self.text("/review")
        self.assertIn("This is for Household stock, which is switched off.", page)
        pid = result["proposals"][0]["id"]
        self.assertNotIn(f"/review/{pid}/accept", page)
        self.assertIn(f"/review/{pid}/reject", page)
        self.post(f"/review/{pid}/reject")
        self.assertEqual(proposals.pending_count(self.conn), 0)
