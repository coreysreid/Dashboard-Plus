"""Tests for the helper API (/api/v1): who may use it, what it shows, and how strictly the pages stay protected."""
import io
import json
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, records, settings, startup
from dashboard.web.app import create_app
import make_migration

TABLES = '''[tables.places]
title = "Places"
columns.name = { type = "text", required = true }

[tables.items]
title = "Items"
columns.name = { type = "text", required = true }
columns.kind = { type = "choice", choices = ["tool", { key = "first_aid", label = "First aid" }] }
columns.place = { type = "link", to = "places", on_delete = "restrict" }
columns.quantity = { type = "measure", unit = "each", min = 0 }
columns.price = { type = "money" }
columns.checked = { type = "boolean" }
columns.secret = { type = "text", sensitive = true }
columns.minimum = { type = "measure", min = 0 }

[tables.items.watch]
running_low = { quantity = "quantity", minimum = "minimum" }

[tables.vault]
title = "Vault"
columns.label = { type = "text", required = true }
columns.pin = { type = "text", required = true, sensitive = true }
'''
LABELS = '''[tables.items]
title = "Stock items"
columns.quantity = { label = "How many", help = "Count whole items" }
'''
PORT = 5123
BASE = f"http://127.0.0.1:{PORT}"
SECRET = "moss-green-4471"  # made-up private value used to check it never leaves


class ApiTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        make_migration.make(self.make_module(tables=TABLES, labels=LABELS), "first_tables")
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        settings.put(self.conn, "setup.done", True)
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.pet_helper, self.key = helpers.issue(self.conn, self.data, "Pet diary helper", "suggest", ["demo"])
        self.reader, self.reader_key = helpers.issue(self.conn, self.data, "Look helper", "read", ["demo"])
        self.stock_helper, self.stock_key = helpers.issue(self.conn, self.data, "Pantry helper", "suggest", ["stock"])
        self.place = self.store.create("demo__places", {"name": "Garage shelf"})
        self.item = self.store.create("demo__items", {"name": "Torch", "kind": "tool", "quantity": 2, "minimum": 4,
                                                      "price": "12.50", "checked": True, "place": self.place,
                                                      "secret": SECRET})

    def auth(self, key=None):
        return {"Authorization": f"Bearer {key or self.key}"}

    def api_get(self, path, key=None, **kwargs):
        return self.client.get(path, base_url=BASE, headers=kwargs.pop("headers", self.auth(key)), **kwargs)

    def api_post(self, path, body, key=None, headers=None, **kwargs):
        merged = dict(self.auth(key), **{"Content-Type": "application/json"})
        merged.update(headers or {})
        data = body if isinstance(body, (str, bytes)) else json.dumps(body)
        return self.client.post(path, data=data, base_url=BASE, headers=merged, **kwargs)

    def suggestion(self, **values):
        return {"request_key": "k-" + re.sub(r"[^A-Za-z0-9]", "", str(sorted(values.items())))[:50],
                "why": "Read it off the shelf label",
                "entries": [{"table": "demo__items", "values": dict({"name": "Batteries"}, **values)}]}

    def moss(self, response):
        self.assertNotIn(SECRET, response.get_data(as_text=True))


class SigningInTests(ApiTestCase):
    def test_every_way_of_not_having_a_good_key_is_refused_the_same_way(self):
        cases = {"no header": {}, "wrong key": {"Authorization": "Bearer dph_notarealkey"},
                 "bearer with no key": {"Authorization": "Bearer"}, "basic": {"Authorization": f"Basic {self.key}"},
                 "key without a scheme": {"Authorization": self.key}, "very long": {"Authorization": "Bearer " + "x" * 5000}}
        for what, headers in cases.items():
            with self.subTest(what):
                response = self.api_get("/api/v1/tables", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.get_json()["error"], "no_key")
        for place in ("?key=", "?token=", "?access_token="):
            with self.subTest(place):
                response = self.client.get("/api/v1/tables" + place + self.key, base_url=BASE)
                self.assertEqual(response.status_code, 401)

    def test_the_key_in_a_cookie_or_form_field_is_never_read(self):
        self.client.set_cookie("dashboard_session", "session-key", domain="127.0.0.1")
        self.assertEqual(self.client.get("/api/v1/tables", base_url=BASE).status_code, 401)
        self.client.set_cookie("key", self.key, domain="127.0.0.1")
        self.assertEqual(self.client.get("/api/v1/tables", base_url=BASE).status_code, 401)
        response = self.client.post("/api/v1/proposals", data={"key": self.key}, base_url=BASE)
        self.assertEqual(response.status_code, 401)

    def test_a_turned_off_key_is_refused(self):
        self.assertEqual(self.api_get("/api/v1/me").status_code, 200)
        helpers.turn_off(self.conn, self.data, self.pet_helper.id)
        self.assertEqual(self.api_get("/api/v1/me").status_code, 401)

    def test_a_good_key_needs_no_cookie_and_sets_none(self):
        response = self.api_get("/api/v1/tables")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Set-Cookie", response.headers)

    def test_a_request_from_another_address_is_refused(self):
        for base in ("http://evil.example:5123", f"http://127.0.0.1:{PORT + 1}"):
            with self.subTest(base):
                response = self.client.get("/api/v1/tables", base_url=base, headers=self.auth())
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "forbidden")

    def test_a_request_with_an_origin_is_from_a_web_page_and_is_refused(self):
        for origin in ("http://evil.example", BASE, "null"):
            with self.subTest(origin):
                response = self.api_get("/api/v1/tables", headers=dict(self.auth(), Origin=origin))
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["error"], "from_a_web_page")
                response = self.api_post("/api/v1/proposals", self.suggestion(), headers={"Origin": origin})
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)

    def test_every_reply_is_json_and_never_kept_in_a_cache(self):
        for path in ("/api/v1/me", "/api/v1/tables", "/api/v1/attention", "/api/v1/batches",
                     "/api/v1/tables/demo__items/records", "/api/v1/nope", "/api/v1/tables/nope__x/records"):
            for headers in (self.auth(), {}):
                with self.subTest(path=path, signed_in=bool(headers)):
                    response = self.api_get(path, headers=headers)
                    self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(self.api_get("/api/v1/nope").status_code, 404)
        self.assertEqual(self.api_get("/api/v1/nope").get_json()["error"], "not_found")
        wrong_way = self.client.delete("/api/v1/me", base_url=BASE, headers=self.auth())
        self.assertEqual(wrong_way.status_code, 405)
        self.assertEqual(wrong_way.get_json()["error"], "method_not_allowed")


class PagesStayStrictTests(ApiTestCase):
    """The helper API is the only exemption from the page rules; every page is exactly as strict as before."""

    def test_a_helper_key_does_not_open_a_page(self):
        for path in ("/", "/t/demo__items", "/settings", "/settings/helpers", "/review", "/attention"):
            with self.subTest(path):
                response = self.client.get(path, base_url=BASE, headers=self.auth())
                self.assertEqual(response.status_code, 302)
                self.assertIn("/start", response.headers["Location"])

    def test_a_page_cookie_does_not_open_the_helper_api(self):
        self.client.get("/?key=session-key", base_url=BASE)
        self.assertEqual(self.client.get("/", base_url=BASE).status_code, 200)
        response = self.client.get("/api/v1/tables", base_url=BASE)
        self.assertEqual(response.status_code, 401)

    def test_a_page_write_still_needs_its_page_token_even_with_a_helper_key(self):
        self.client.get("/?key=session-key", base_url=BASE)
        response = self.client.post("/t/demo__items/new", data={"name": "Sneaky"}, base_url=BASE, headers=self.auth())
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/settings/helpers", data={"name": "Sneaky", "access": "read", "modules": ["demo"]},
                                    base_url=BASE, headers=self.auth())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(helpers.all_helpers(self.conn)), 3)

    def test_a_page_write_without_a_cookie_is_still_sent_to_the_start_page(self):
        response = self.client.post("/settings/helpers", data={"name": "X", "_csrf": self.app.config["CSRF_TOKEN"]},
                                    base_url=BASE, headers=self.auth())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(helpers.all_helpers(self.conn)), 3)

    def test_pages_still_refuse_another_host_and_a_foreign_origin(self):
        self.client.get("/?key=session-key", base_url=BASE)
        self.assertEqual(self.client.get("/", base_url="http://evil.example:5123").status_code, 403)
        response = self.client.post("/settings/helpers/1/turn-off", data={"_csrf": self.app.config["CSRF_TOKEN"]},
                                    base_url=BASE, headers={"Origin": "http://evil.example"})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(helpers.get(self.conn, 1).active)

    def test_a_path_that_only_looks_like_the_api_is_still_a_page(self):
        for path in ("/api/v10/tables", "/api/v1", "/api/v1x/tables", "//api/v1/tables"):
            with self.subTest(path):
                response = self.client.get(path, base_url=BASE, headers=self.auth())
                self.assertIn(response.status_code, (302, 404))
                if response.status_code == 302:
                    self.assertIn("/start", response.headers["Location"])

    def test_the_review_count_is_not_shown_to_someone_who_is_not_signed_in(self):
        self.api_post("/api/v1/proposals", self.suggestion())
        self.assertNotIn("(1)", self.client.get("/start", base_url=BASE).get_data(as_text=True))


class ReadingTests(ApiTestCase):
    def test_me_says_what_this_helper_may_do(self):
        data = self.api_get("/api/v1/me").get_json()
        self.assertEqual((data["name"], data["access"], data["private_details"]), ("Pet diary helper", "suggest", False))
        self.assertEqual(data["modules"], [{"name": "demo", "title": "Demo"}])
        self.assertEqual(data["limits"], {"entries_per_call": 50, "suggestions_per_day": 200,
                                          "suggestions_left_today": 200, "max_body_bytes": 65536})
        self.assertEqual(data["api_version"], "1")

    def test_tables_lists_only_the_granted_parts_and_leaves_private_columns_out(self):
        response = self.api_get("/api/v1/tables")
        self.moss(response)
        tables = {t["table"]: t for t in response.get_json()["tables"]}
        self.assertEqual(set(tables), {"demo__places", "demo__items", "demo__vault"})
        items = tables["demo__items"]
        self.assertEqual(items["title"], "Stock items")
        self.assertNotIn("secret", [c["name"] for c in items["columns"]])
        self.assertEqual(items["private_columns_left_out"], 1)
        self.assertTrue(items["can_suggest"])
        quantity = next(c for c in items["columns"] if c["name"] == "quantity")
        self.assertEqual((quantity["label"], quantity["help"], quantity["unit"]), ("How many", "Count whole items", "each"))
        kind = next(c for c in items["columns"] if c["name"] == "kind")
        self.assertEqual(kind["choices"], [{"key": "tool", "label": "Tool"}, {"key": "first_aid", "label": "First aid"}])
        self.assertEqual(next(c for c in items["columns"] if c["name"] == "place")["to"], "demo__places")

    def test_a_table_that_needs_a_private_detail_cannot_be_suggested_into(self):
        vault = {t["table"]: t for t in self.api_get("/api/v1/tables").get_json()["tables"]}["demo__vault"]
        self.assertFalse(vault["can_suggest"])
        self.assertIn("private detail", vault["reason"])
        body = {"request_key": "v1", "why": "Test", "entries": [{"table": "demo__vault", "values": {"label": "Safe"}}]}
        response = self.api_post("/api/v1/proposals", body)
        self.assertEqual(response.status_code, 422)

    def test_a_look_only_helper_sees_that_it_cannot_suggest(self):
        tables = self.api_get("/api/v1/tables", key=self.reader_key).get_json()["tables"]
        self.assertTrue(tables and not any(t["can_suggest"] for t in tables))

    def test_a_record_never_includes_private_details_or_bookkeeping(self):
        response = self.api_get(f"/api/v1/tables/demo__items/records/{self.item}")
        self.moss(response)
        record = response.get_json()["record"]
        self.assertEqual(record["values"]["name"], "Torch")
        self.assertEqual(record["values"]["price"], 12.5)  # whole units, not cents
        self.assertIs(record["values"]["checked"], True)
        self.assertEqual(record["values"]["place"], self.place)
        for hidden in ("secret", "review_status", "edited_by_person", "batch_id", "deleted_at"):
            self.assertNotIn(hidden, record["values"])
            self.assertNotIn(hidden, record)
        listing = self.api_get("/api/v1/tables/demo__items/records")
        self.moss(listing)

    def test_a_missing_or_deleted_record_is_not_found(self):
        self.assertEqual(self.api_get("/api/v1/tables/demo__items/records/9999").status_code, 404)
        self.store.delete("demo__items", self.item)
        self.assertEqual(self.api_get(f"/api/v1/tables/demo__items/records/{self.item}").status_code, 404)

    def test_other_parts_are_off_limits_and_unknown_tables_are_not_found(self):
        response = self.api_get("/api/v1/tables/stock__items/records")
        self.assertEqual((response.status_code, response.get_json()["error"]), (403, "not_allowed"))
        self.assertIn("Pet diary helper may use: Demo.", response.get_json()["message"])
        self.assertEqual(self.api_get("/api/v1/tables/core__helpers/records").status_code, 404)
        self.assertEqual(self.api_get("/api/v1/tables/nope__nothing/records").status_code, 404)
        names = [t["table"] for t in self.api_get("/api/v1/tables").get_json()["tables"]]
        self.assertFalse([n for n in names if n.startswith(("stock__", "core__"))])

    def test_paging_goes_by_id_and_leaves_out_deleted_records(self):
        ids = [self.store.create("demo__items", {"name": f"Thing {n}"}) for n in range(120)]
        self.store.delete("demo__items", ids[5])
        seen, after, pages = [], 0, 0
        while after is not None:
            data = self.api_get(f"/api/v1/tables/demo__items/records?after={after}&limit=50").get_json()
            seen += [r["id"] for r in data["records"]]
            after, pages = data["next_after"], pages + 1
        self.assertEqual(pages, 3)
        self.assertEqual(len(seen), 120)  # 121 made in all (one in setUp), one deleted
        self.assertNotIn(ids[5], seen)
        self.assertEqual(seen, sorted(seen))
        big = self.api_get("/api/v1/tables/demo__items/records?limit=100000").get_json()
        self.assertEqual(len(big["records"]), 120)
        small = self.api_get("/api/v1/tables/demo__items/records?limit=0").get_json()
        self.assertEqual(len(small["records"]), 1)
        odd = self.api_get("/api/v1/tables/demo__items/records?limit=abc&after=-5").get_json()
        self.assertEqual(len(odd["records"]), 50)

    def test_attention_shows_only_the_granted_parts(self):
        shelf = self.store.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 1, "minimum": 5})
        mine = self.api_get("/api/v1/attention").get_json()
        self.assertEqual([i["name"] for i in mine["running_low"]], ["Torch"])
        self.assertNotIn("sort_key", mine["running_low"][0])
        stock = self.api_get("/api/v1/attention", key=self.stock_key).get_json()
        self.assertEqual([i["name"] for i in stock["running_low"]], ["Rice"])
        self.assertEqual(stock["running_low"][0]["record_id"], shelf)
        self.moss(self.api_get("/api/v1/attention"))


class SuggestingTests(ApiTestCase):
    def test_a_suggestion_is_kept_waiting_and_the_records_do_not_change(self):
        response = self.api_post("/api/v1/proposals", self.suggestion(quantity=3))
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["state"], "waiting")
        self.assertEqual(data["proposals"][0]["table"], "demo__items")
        self.assertEqual(self.store.count("demo__items"), 1)
        again = self.api_post("/api/v1/proposals", self.suggestion(quantity=3))
        self.assertEqual((again.status_code, again.get_json()["batch_id"]), (200, data["batch_id"]))
        detail = self.api_get(f"/api/v1/batches/{data['batch_id']}").get_json()
        self.assertEqual(detail["proposals"][0]["status"], "pending")
        listing = self.api_get("/api/v1/batches").get_json()
        self.assertEqual((listing["batches"][0]["total"], listing["batches"][0]["pending"]), (1, 1))

    def test_a_look_only_helper_cannot_suggest(self):
        response = self.api_post("/api/v1/proposals", self.suggestion(), key=self.reader_key)
        self.assertEqual((response.status_code, response.get_json()["error"]), (403, "look_only"))

    def test_a_private_detail_is_refused_without_repeating_it(self):
        response = self.api_post("/api/v1/proposals", self.suggestion(secret=SECRET))
        self.assertEqual((response.status_code, response.get_json()["error"]), (403, "private_detail"))
        self.assertIn("Leave out: secret.", response.get_json()["message"])
        self.moss(response)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)

    def test_errors_never_repeat_what_was_sent(self):
        response = self.api_post("/api/v1/proposals", self.suggestion(quantity=SECRET))
        self.assertEqual(response.status_code, 422)
        self.moss(response)
        self.assertEqual(response.get_json()["problems"][0]["field"], "quantity")

    def test_a_table_in_a_part_the_helper_was_not_given_is_refused(self):
        body = {"request_key": "s1", "why": "Test", "entries": [{"table": "stock__items", "values": {"name": "Rice"}}]}
        self.assertEqual(self.api_post("/api/v1/proposals", body).status_code, 403)
        body["entries"][0]["table"] = "nope__x"
        self.assertEqual(self.api_post("/api/v1/proposals", body).status_code, 404)

    def test_system_fields_cannot_be_set_and_nothing_appears_in_the_records(self):
        response = self.api_post("/api/v1/proposals", self.suggestion(review_status="confirmed"))
        self.assertEqual(response.status_code, 422)
        self.assertIn("is not a field of this table.", response.get_json()["problems"][0]["message"])
        top = dict(self.suggestion(), status="accepted")
        self.assertEqual(self.api_post("/api/v1/proposals", top).status_code, 400)
        self.assertEqual(self.store.count("demo__items"), 1)

    def test_a_big_request_is_refused(self):
        body = self.suggestion(name="x" * 70000)
        response = self.api_post("/api/v1/proposals", body)
        self.assertEqual((response.status_code, response.get_json()["error"]), (413, "too_large"))
        chunked = self.client.post("/api/v1/proposals", input_stream=io.BytesIO(b"{" + b" " * 70000 + b"}"), base_url=BASE,
                                   headers=dict(self.auth(), **{"Content-Type": "application/json"}))
        self.assertEqual(chunked.status_code, 413)

    def test_fifty_one_entries_are_refused(self):
        body = {"request_key": "many", "why": "Test",
                "entries": [{"table": "demo__items", "values": {"name": f"N{n}"}} for n in range(51)]}
        response = self.api_post("/api/v1/proposals", body)
        self.assertEqual((response.status_code, response.get_json()["message"]),
                         (400, "Send 50 suggestions or fewer at a time."))

    def test_the_body_must_be_json(self):
        response = self.api_post("/api/v1/proposals", "name=x", headers={"Content-Type": "text/plain"})
        self.assertEqual((response.status_code, response.get_json()["error"]), (415, "needs_json"))
        for body in ("{not json", "[]", '"text"', json.dumps(dict(self.suggestion(), entries="nope")),
                     json.dumps(dict(self.suggestion(), entries=[{"table": "demo__items", "values": "x"}]))):
            with self.subTest(body[:20]):
                self.assertEqual(self.api_post("/api/v1/proposals", body).status_code, 400)

    def test_batches_belong_to_their_helper(self):
        mine = self.api_post("/api/v1/proposals", self.suggestion()).get_json()["batch_id"]
        self.assertEqual(self.api_get(f"/api/v1/batches/{mine}", key=self.stock_key).status_code, 404)
        self.assertEqual(self.api_get("/api/v1/batches", key=self.stock_key).get_json()["batches"], [])
        self.assertEqual(self.api_get(f"/api/v1/batches/{mine}").status_code, 200)
        self.assertEqual(self.api_get("/api/v1/batches/9999").status_code, 404)

    def test_helpers_have_no_way_to_decide_or_change_anything_else(self):
        batch = self.api_post("/api/v1/proposals", self.suggestion()).get_json()
        pid = batch["proposals"][0]["id"]
        for method, path in (("post", f"/api/v1/proposals/{pid}/accept"), ("post", "/api/v1/helpers"),
                             ("post", "/api/v1/tables/demo__items/records"), ("put", f"/api/v1/tables/demo__items/records/{self.item}"),
                             ("delete", f"/api/v1/tables/demo__items/records/{self.item}"), ("get", "/api/v1/helpers"),
                             ("post", "/api/v1/settings"), ("get", "/api/v1/backups")):
            with self.subTest(path=path):
                response = getattr(self.client, method)(path, base_url=BASE, headers=dict(self.auth(), **{"Content-Type": "application/json"}))
                self.assertIn(response.status_code, (404, 405))
        self.assertEqual(self.store.get("demo__items", self.item)["name"], "Torch")
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals").fetchone()[0], "pending")
