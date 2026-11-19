"""Tests that the published API description (openapi-v1.json) matches the real /api/v1 routes, errors and replies."""
import json
import re

from support import ROOT, TempDirTestCase
from test_helper_api import BASE, ApiTestCase
from dashboard.core import proposals
from dashboard.web.api import OPENAPI_FILE, QUEUE_LIMIT_KEY

WEB = ROOT / "src" / "dashboard" / "web"
SPEC = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))
JSON_TYPES = {"string": str, "boolean": bool, "object": dict, "array": list, "null": type(None)}


def check(value, schema, root=SPEC, path="$") -> list[str]:
    """Problems found comparing `value` with a schema, using only the parts of JSON Schema this file uses:
    $ref, type (one or a list), enum, required, properties, additionalProperties, items. An object that
    lists `properties` and says nothing about `additionalProperties` may not carry any other key."""
    if "$ref" in schema:
        return check(value, root["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]], root, path)
    problems = []
    if "type" in schema:
        kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is(value, kind) for kind in kinds):
            return [f"{path}: expected {'/'.join(kinds)}, got {type(value).__name__} {value!r:.40}"]
    if "enum" in schema and value not in schema["enum"]:
        problems.append(f"{path}: {value!r:.40} is not one of {schema['enum']}")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"{path}: missing {name}")
        listed = schema.get("properties", {})
        extra = schema.get("additionalProperties", False if listed else True)
        for name, item in value.items():
            if name in listed:
                problems += check(item, listed[name], root, f"{path}.{name}")
            elif extra is False:
                problems.append(f"{path}: {name} is not described")
            elif isinstance(extra, dict):
                problems += check(item, extra, root, f"{path}.{name}")
    if isinstance(value, list) and "items" in schema:
        for number, item in enumerate(value):
            problems += check(item, schema["items"], root, f"{path}[{number}]")
    return problems


def _is(value, kind) -> bool:
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, JSON_TYPES[kind])


def operations():
    for path, item in SPEC["paths"].items():
        for method, operation in item.items():
            yield path, method, operation


def ok_schema(path, method="get"):
    return SPEC["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]


class CheckerTests(TempDirTestCase):
    def test_the_checker_catches_what_it_should(self):
        schema = {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": ["string", "null"]},
                                                   "c": {"type": "array", "items": {"enum": ["x", "y"]}}},
                  "required": ["a"]}
        self.assertEqual(check({"a": 1, "b": None, "c": ["x"]}, schema), [])
        self.assertTrue(check({"b": "s"}, schema))                       # missing
        self.assertTrue(check({"a": True}, schema))                      # a bool is not an integer
        self.assertTrue(check({"a": 1, "z": 1}, schema))                 # not described
        self.assertTrue(check({"a": 1, "c": ["q"]}, schema))             # not in the list
        self.assertTrue(check({"a": 1.5}, schema))
        self.assertEqual(check({"a": 1, "z": 1}, dict(schema, additionalProperties=True)), [])


class FileTests(TempDirTestCase):
    def test_it_is_a_version_3_1_description_with_invented_examples_only(self):
        self.assertTrue(SPEC["openapi"].startswith("3.1."))
        text = OPENAPI_FILE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"dph_[A-Za-z0-9_-]{8,}")
        self.assertNotRegex(text, r"[\w.]+@[\w.]+\.\w+")

    def test_every_reference_points_at_a_schema_that_exists(self):
        names = set(SPEC["components"]["schemas"])
        found = set(re.findall(r'"\$ref": "#/components/schemas/(\w+)"', OPENAPI_FILE.read_text(encoding="utf-8")))
        self.assertLessEqual(found, names)
        self.assertLessEqual(names, found | {"Error"})

    def test_every_example_fits_the_schema_beside_it(self):
        seen = 0
        for path, method, operation in operations():
            bodies = [operation.get("requestBody", {})] + list(operation["responses"].values())
            for body in bodies:
                for media in body.get("content", {}).values():
                    examples = [media["example"]] if "example" in media else [e["value"] for e in media.get("examples", {}).values()]
                    for example in examples:
                        seen += 1
                        self.assertEqual(check(example, media["schema"]), [], f"{method} {path}")
        self.assertGreater(seen, 20)


class RouteTests(ApiTestCase):
    def test_every_route_under_api_v1_is_described_with_the_same_methods_and_no_others(self):
        real = {}
        for rule in self.app.url_map.iter_rules():
            if rule.rule.startswith("/api/v1/"):
                path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)
                real.setdefault(path, set()).update(m.lower() for m in rule.methods - {"HEAD", "OPTIONS"})
        described = {}
        for path, method, _operation in operations():
            described.setdefault(path, set()).add(method)
        self.assertEqual(described, real)

    def test_every_error_code_in_the_code_is_in_the_file_and_the_file_claims_no_other(self):
        used, pairs = set(), set()
        for name in ("web/api.py", "web/app.py", "core/proposals.py"):
            text = (ROOT / "src" / "dashboard" / name).read_text(encoding="utf-8")
            for status, code in re.findall(r'(?:api_error|ProposalError)\(\s*(\d{3}),\s*"([a-z_]+)"', text):
                used.add(code)
                pairs.add((status, code))
            used.update(re.findall(r'\b\d{3}: "([a-z_]+)"', text))  # the table of codes for the web server's own refusals
            used.update(re.findall(r'\.get\(error\.code, "([a-z_]+)"\)', text))
        self.assertGreater(len(used), 15)
        documented = set(SPEC["components"]["schemas"]["Error"]["properties"]["error"]["enum"])
        self.assertEqual(used, documented)
        for status, code in pairs:
            found = any(status in operation["responses"] and f'"{code}"' in json.dumps(operation["responses"][status])
                        for _p, _m, operation in operations())
            self.assertTrue(found, f"{status} {code} is not shown in any response")

    def test_the_description_needs_the_key_and_is_served_as_the_file(self):
        self.assertEqual(self.client.get("/api/v1/openapi.json", base_url=BASE).status_code, 401)
        self.assertEqual(self.api_get("/api/v1/openapi.json", headers={"Authorization": "Bearer dph_nope12345"}).status_code, 401)
        response = self.client.get("/api/v1/openapi.json", base_url=BASE, headers=dict(self.auth(), Origin="http://evil.example"))
        self.assertEqual(response.status_code, 403)
        for key in (self.key, self.reader_key):  # a look-only helper may read it too
            response = self.api_get("/api/v1/openapi.json", key=key)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(response.get_json(), SPEC)
        self.assertEqual(self.api_post("/api/v1/openapi.json", {}).status_code, 405)
        self.assertEqual(self.client.put("/api/v1/openapi.json", base_url=BASE, headers=self.auth()).status_code, 405)

    def test_the_page_side_never_serves_it_without_the_launch_cookie(self):
        self.assertEqual(self.client.get("/openapi.json", base_url=BASE).status_code, 302)  # not a page, not a route


class ReplyShapeTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.store.create("stock__items", {"name": "Torch batteries", "unit": "each", "quantity": 2, "minimum": 6})

    def valid(self, response, path, status=200, method="get"):
        self.assertEqual(response.status_code, status, response.get_data(as_text=True)[:200])
        schema = SPEC["paths"][path][method]["responses"][str(status)]["content"]["application/json"]["schema"]
        self.assertEqual(check(response.get_json(), schema), [], path)
        return response.get_json()

    def test_me(self):
        body = self.valid(self.api_get("/api/v1/me"), "/api/v1/me")
        self.assertEqual(body["limits"]["review_queue_limit"], proposals.MAX_WAITING)
        self.assertEqual(body["limits"]["suggestions_waiting"], 0)
        self.assertIn("message", body)
        self.assertEqual(body["limits"]["requests_per_minute"], 120)

    def test_tables_for_each_kind_of_helper(self):
        for key, seen in ((self.key, "demo__items"), (self.stock_key, "stock__items"), (self.reader_key, "demo__items")):
            body = self.valid(self.api_get("/api/v1/tables", key=key), "/api/v1/tables")
            self.assertIn(seen, [t["table"] for t in body["tables"]])
        items = next(t for t in self.valid(self.api_get("/api/v1/tables"), "/api/v1/tables")["tables"] if t["table"] == "demo__items")
        kinds = {c["type"] for c in items["columns"]}
        self.assertTrue({"link", "choice", "money"} <= kinds)
        self.assertTrue(any("choices" in c for c in items["columns"]) and any("to" in c for c in items["columns"]))

    def test_a_table_that_cannot_be_suggested_into_says_why(self):
        body = self.valid(self.api_get("/api/v1/tables"), "/api/v1/tables")
        vault = [t for t in body["tables"] if t["table"] == "demo__vault"][0]
        self.assertFalse(vault["can_suggest"])  # it needs a private detail, which helpers never get
        self.assertEqual(vault["private_columns_left_out"], 1)
        self.assertIn("reason", vault)
        look = self.valid(self.api_get("/api/v1/tables", key=self.reader_key), "/api/v1/tables")["tables"]
        self.assertTrue(all("reason" in t for t in look))

    def test_records_and_one_record(self):
        body = self.valid(self.api_get("/api/v1/tables/demo__items/records"), "/api/v1/tables/{table}/records")
        self.assertEqual(len(body["records"]), 1)
        self.assertIsNone(body["next_after"])
        self.valid(self.api_get(f"/api/v1/tables/demo__items/records/{self.item}"),
                   "/api/v1/tables/{table}/records/{record_id}")
        self.store.create("demo__items", {"name": "Spanner"})
        paged = self.valid(self.api_get("/api/v1/tables/demo__items/records?limit=1"), "/api/v1/tables/{table}/records")
        self.assertEqual(paged["next_after"], paged["records"][0]["id"])

    def test_attention(self):
        body = self.valid(self.api_get("/api/v1/attention", key=self.stock_key), "/api/v1/attention")
        self.assertTrue(body["running_low"])
        self.valid(self.api_get("/api/v1/attention"), "/api/v1/attention")

    def test_suggesting_and_the_batches(self):
        first = self.api_post("/api/v1/proposals", self.suggestion(price=3))
        batch = self.valid(first, "/api/v1/proposals", 201, "post")
        self.valid(self.api_post("/api/v1/proposals", self.suggestion(price=3)), "/api/v1/proposals", 200, "post")
        listed = self.valid(self.api_get("/api/v1/batches"), "/api/v1/batches")
        self.assertEqual([b["id"] for b in listed["batches"]], [batch["batch_id"]])
        self.valid(self.api_get(f"/api/v1/batches/{batch['batch_id']}"), "/api/v1/batches/{batch_id}")
        helper_proposal = batch["proposals"][0]["id"]
        proposals.reject(self.conn, helper_proposal)
        detail = self.valid(self.api_get(f"/api/v1/batches/{batch['batch_id']}"), "/api/v1/batches/{batch_id}")
        self.assertEqual(detail["proposals"][0]["status"], "rejected")

    def test_every_refusal_has_the_documented_shape_and_a_documented_status(self):
        error = SPEC["components"]["schemas"]["Error"]
        cases = [
            (self.client.get("/api/v1/me", base_url=BASE), 401, "no_key", "/api/v1/me"),
            (self.api_get("/api/v1/me", headers=dict(self.auth(), Origin="http://evil.example")), 403, "from_a_web_page", "/api/v1/me"),
            (self.client.get("/api/v1/me", base_url="http://evil.example:5123", headers=self.auth()), 403, "forbidden", "/api/v1/me"),
            (self.api_get("/api/v1/tables/stock__items/records"), 404, "not_found", "/api/v1/tables/{table}/records"),
            (self.api_get("/api/v1/tables/nowhere/records"), 404, "not_found", "/api/v1/tables/{table}/records"),
            (self.api_get("/api/v1/tables/demo__items/records/9999"), 404, "not_found", "/api/v1/tables/{table}/records/{record_id}"),
            (self.api_get("/api/v1/batches/9999"), 404, "not_found", "/api/v1/batches/{batch_id}"),
            (self.api_post("/api/v1/proposals", "{"), 400, "bad_request", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", self.suggestion(name="dph_abcdefgh12345")), 400, "looks_like_a_key", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", self.suggestion(name="a‮b")), 400, "hidden_characters", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", self.suggestion(secret="x")), 403, "private_detail", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", self.suggestion(), key=self.reader_key), 403, "look_only", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", self.suggestion(quantity=-5)), 422, "invalid", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", "x" * 70000), 413, "too_large", "/api/v1/proposals"),
            (self.api_post("/api/v1/proposals", "{}", headers={"Content-Type": "text/plain"}), 415, "needs_json", "/api/v1/proposals"),
            (self.client.delete("/api/v1/me", base_url=BASE, headers=self.auth()), 405, "method_not_allowed", None),
        ]
        for response, status, code, path in cases:
            with self.subTest(code=code, status=status):
                self.assertEqual(response.status_code, status)
                body = response.get_json()
                self.assertEqual(check(body, error), [])
                self.assertEqual(body["error"], code)
                if path:
                    method = "post" if path == "/api/v1/proposals" else "get"
                    self.assertIn(str(status), SPEC["paths"][path][method]["responses"])

    def test_a_not_allowed_link_and_a_request_key_clash(self):
        self.valid(self.api_post("/api/v1/proposals", self.suggestion(price=1)), "/api/v1/proposals", 201, "post")
        clash = dict(self.suggestion(price=1), why="Something else")
        response = self.api_post("/api/v1/proposals", clash)
        self.assertEqual((response.status_code, response.get_json()["error"]), (409, "request_key_reused"))
        self.assertEqual(check(response.get_json(), SPEC["components"]["schemas"]["Error"]), [])

    def test_the_two_429s_match_the_file(self):
        error = SPEC["components"]["schemas"]["Error"]
        self.app.config["HELPER_REQUESTS_PER_MINUTE"] = 3
        for _ in range(3):
            self.api_get("/api/v1/me")
        response = self.api_get("/api/v1/me")
        self.assertEqual((response.status_code, response.get_json()["error"]), (429, "too_many_requests"))
        self.assertEqual(check(response.get_json(), error), [])
        self.assertRegex(response.headers["Retry-After"], r"^\d+$")
        self.assertIn("Retry-After", SPEC["paths"]["/api/v1/me"]["get"]["responses"]["429"]["headers"])

    def test_review_queue_full_is_documented_and_reported_by_me(self):
        self.app.config[QUEUE_LIMIT_KEY] = 2
        self.valid(self.api_post("/api/v1/proposals", dict(self.suggestion(price=1), entries=[
            {"table": "demo__items", "values": {"name": "A"}}, {"table": "demo__items", "values": {"name": "B"}}])),
            "/api/v1/proposals", 201, "post")
        me = self.valid(self.api_get("/api/v1/me"), "/api/v1/me")
        self.assertEqual((me["limits"]["review_queue_limit"], me["limits"]["suggestions_waiting"]), (2, 2))
        response = self.api_post("/api/v1/proposals", dict(self.suggestion(price=2), request_key="more"))
        self.assertEqual((response.status_code, response.get_json()["error"]), (429, "review_queue_full"))
        self.assertEqual(response.get_json()["message"], "2 suggestions from this helper are already waiting on Review. "
                                                         "Ask the household to look at them first.")
        self.assertNotIn("Retry-After", response.headers)
        self.assertEqual(check(response.get_json(), SPEC["components"]["schemas"]["Error"]), [])
        self.assertIn("review_queue_full", json.dumps(SPEC["paths"]["/api/v1/proposals"]["post"]["responses"]["429"]))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 2)
        waiting = self.conn.execute("SELECT id FROM core__proposals ORDER BY id").fetchall()
        proposals.reject(self.conn, waiting[0][0])
        self.assertEqual(self.api_get("/api/v1/me").get_json()["limits"]["suggestions_waiting"], 1)
        self.valid(self.api_post("/api/v1/proposals", dict(self.suggestion(price=2), request_key="now-fits")),
                   "/api/v1/proposals", 201, "post")

    def test_a_larger_proposal_than_the_room_left_is_refused_whole(self):
        self.app.config[QUEUE_LIMIT_KEY] = 3
        two = dict(self.suggestion(price=1), entries=[{"table": "demo__items", "values": {"name": n}} for n in "AB"])
        self.assertEqual(self.api_post("/api/v1/proposals", two).status_code, 201)
        again = dict(two, request_key="second-pair")
        self.assertEqual(self.api_post("/api/v1/proposals", again).status_code, 429)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 2)
        one = dict(two, request_key="third", entries=two["entries"][:1])
        self.assertEqual(self.api_post("/api/v1/proposals", one).status_code, 201)  # exactly full is allowed
