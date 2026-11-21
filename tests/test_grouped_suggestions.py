"""Tests for receipt lines on suggestions and for suggestions that point at an earlier one in the same batch (decision 0097)."""
import json
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, proposals, records, settings, startup
from dashboard.core.proposals import ProposalError
from dashboard.errors import PlainError
from dashboard.web.app import create_app

PORT = 5131
BASE = f"http://127.0.0.1:{PORT}"
WHY = "Invented Example Market receipt, 20/11/26"


class GroupedTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.beans = self.store.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 5})
        self.helper, self.key = helpers.issue(self.conn, self.data, "Pantry helper", "suggest", ["stock"])

    @staticmethod
    def new_item(name="Red lentils", **more):
        return {"table": "stock__items", "values": dict({"name": name, "category": "pantry", "unit": "bags"}, **more),
                "source": {"line": name.upper() + " 500G"}}

    @staticmethod
    def bought(item, amount=2, source=None):
        entry = {"table": "stock__movements", "values": {"item": item, "reason": "bought", "amount": amount,
                                                          "happened_on": "2026-11-20"}}
        if source:
            entry["source"] = source
        return entry

    def send(self, entries, key="receipt-1", why=WHY):
        return proposals.submit(self.conn, self.registry, self.helper,
                                {"request_key": key, "why": why, "entries": entries})[0]

    def refused(self, entries, status=422, code="invalid"):
        with self.assertRaises(ProposalError) as caught:
            self.send(entries)
        self.assertEqual((caught.exception.status, caught.exception.code), (status, code))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)
        return caught.exception

    def receipt(self):
        """A new item, its first Stock in, and a Stock in for an item already there."""
        return self.send([self.new_item(), self.bought({"ref": 0}, source={"line": "RED LENTILS 500G x2", "price": "3.80"}),
                          self.bought(self.beans, source={"line": "KIDNEY BEANS 400G x2", "price": "2.40"})])

    def ids(self, result):
        return [p["id"] for p in result["proposals"]]

    def lentils(self):
        return self.conn.execute("SELECT id, quantity FROM stock__items WHERE name = 'Red lentils'").fetchone()

    def statuses(self):
        return [r[0] for r in self.conn.execute("SELECT status FROM core__proposals ORDER BY position")]


class SourceLineTests(GroupedTestCase):
    def test_a_source_line_is_kept_with_the_suggestion_and_never_in_the_records(self):
        result = self.receipt()
        kept = [json.loads(r[0]) if r[0] else None for r in
                self.conn.execute("SELECT source_json FROM core__proposals ORDER BY position")]
        self.assertEqual(kept[1], {"line": "RED LENTILS 500G x2", "price": "3.80"})
        proposals.accept_batch(self.conn, self.registry, result["batch_id"])
        for table in ("stock__items", "stock__movements", "stock__lots", "core__audit"):
            text = json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {table}")])
            self.assertNotIn("3.80", text, table)
            self.assertNotIn("RED LENTILS 500G", text, table)

    def test_source_lines_are_screened_and_bounded_like_other_helper_text(self):
        cases = [({"line": "KIDNEY‮BEANS"}, 400, "hidden_characters"),
                 ({"line": "dph_abcdefgh12345678"}, 400, "looks_like_a_key"),
                 ({"line": "x" * 201}, 400, "bad_request"),
                 ({"price": "1" * 21}, 400, "bad_request"),
                 ({"line": ""}, 400, "bad_request"),
                 ({"line": 3}, 400, "bad_request"),
                 ({}, 400, "bad_request"),
                 ({"line": "BEANS", "shop": "Example Market"}, 400, "bad_request"),
                 ("BEANS", 400, "bad_request")]
        for source, status, code in cases:
            with self.subTest(source=source):
                self.refused([self.bought(self.beans, source=source) if source else
                              dict(self.bought(self.beans), source=source)], status, code)

    def test_a_request_without_sources_has_the_same_fingerprint_as_before(self):
        entries = [("stock__movements", {"item": 1})]
        self.assertEqual(proposals._body_hash("why", entries), proposals._body_hash("why", entries, [None]))
        self.assertNotEqual(proposals._body_hash("why", entries), proposals._body_hash("why", entries, [{"line": "A"}]))

    def test_a_retry_with_a_different_source_is_a_different_request(self):
        self.send([self.bought(self.beans, source={"line": "BEANS x2"})])
        self.send([self.bought(self.beans, source={"line": "BEANS x2"})])  # the same: the first answer again
        with self.assertRaises(ProposalError) as caught:
            self.send([self.bought(self.beans, source={"line": "BEANS x3"})])
        self.assertEqual(caught.exception.code, "request_key_reused")


class RefTests(GroupedTestCase):
    def test_a_new_item_and_its_first_stock_in_arrive_together_and_change_nothing_yet(self):
        result = self.receipt()
        self.assertEqual([p.get("depends_on") for p in result["proposals"]], [None, [0], None])
        self.assertIsNone(self.lentils())
        self.assertEqual(self.store.count("stock__movements"), 0)

    def test_refs_must_point_at_an_earlier_entry_for_the_linked_table(self):
        place = {"table": "stock__places", "values": {"name": "Pantry"}}
        cases = {"itself": [self.bought({"ref": 0})],
                 "a later one": [self.bought({"ref": 1}), self.new_item()],
                 "the wrong table": [place, self.bought({"ref": 0})],
                 "not a number": [self.new_item(), self.bought({"ref": "0"})],
                 "a yes or no": [self.new_item(), self.bought({"ref": True})],
                 "another key": [self.new_item(), self.bought({"ref": 0, "also": 1})],
                 "negative": [self.new_item(), self.bought({"ref": -1})],
                 "not a link": [self.new_item(), dict(self.bought(self.beans), values={
                     "item": self.beans, "reason": "bought", "amount": {"ref": 0}})]}
        for what, entries in cases.items():
            with self.subTest(what):
                error = self.refused(entries)
                self.assertEqual(error.problems[-1]["entry"], len(entries) - 1 if what != "a later one" else 0)
        wrong = self.refused([place, self.bought({"ref": 0})])
        self.assertIn("points at entry 0, which would add to Places, but this field links to Stock items",
                      wrong.problems[0]["message"])

    def test_a_ref_to_an_entry_that_could_not_be_added_is_refused_with_it(self):
        error = self.refused([{"table": "stock__items", "values": {"category": "pantry"}}, self.bought({"ref": 0})])
        self.assertEqual({p["entry"] for p in error.problems}, {0, 1})
        self.assertIn("could not be added", next(p["message"] for p in error.problems if p["entry"] == 1))

    def test_a_ref_counts_the_earlier_entry_in_the_dry_run(self):
        """A Stock in then a Stock out of the new item: the dry run sees the bought amount."""
        used = {"table": "stock__movements", "values": {"item": {"ref": 0}, "reason": "used", "amount": 1}}
        self.send([self.new_item(), self.bought({"ref": 0}, amount=2), used], key="fits")
        too_many = dict(used, values=dict(used["values"], amount=5))
        self.conn.execute("DELETE FROM core__proposals")
        self.conn.commit()
        self.refused([self.new_item(), self.bought({"ref": 0}, amount=2), too_many])

    def test_accepting_the_stock_in_adds_its_new_item_first_in_one_step(self):
        result = self.receipt()
        _item, movement, _beans = self.ids(result)
        table, record_id, also = proposals.accept_counted(self.conn, self.registry, movement)
        self.assertEqual((table, also), ("stock__movements", 1))
        lentils = self.lentils()
        self.assertEqual(lentils["quantity"], 2)
        self.assertEqual(self.store.get("stock__movements", record_id)["item"], lentils["id"])
        self.assertEqual(self.statuses(), ["accepted", "accepted", "pending"])
        rows = self.conn.execute("SELECT record_id FROM core__proposals ORDER BY position").fetchall()
        self.assertEqual((rows[0][0], rows[1][0]), (lentils["id"], record_id))
        self.assertEqual(self.conn.execute("SELECT source FROM stock__items WHERE id = ?", (lentils["id"],)).fetchone()[0],
                         "agent:pantry-helper")

    def test_accepting_the_item_alone_then_the_stock_in_later_links_to_it(self):
        result = self.receipt()
        item, movement, _beans = self.ids(result)
        proposals.accept(self.conn, self.registry, item)
        self.assertFalse(self.lentils()["quantity"])  # added, with nothing bought yet
        _table, record_id, also = proposals.accept_counted(self.conn, self.registry, movement)
        self.assertEqual(also, 0)
        self.assertEqual(self.store.get("stock__movements", record_id)["item"], self.lentils()["id"])
        self.assertEqual(self.lentils()["quantity"], 2)

    def test_if_the_stock_in_fails_its_new_item_is_not_added_either(self):
        used = {"table": "stock__movements", "values": {"item": {"ref": 0}, "reason": "used", "amount": 2}}
        result = self.send([self.new_item(), self.bought({"ref": 0}, amount=2), used])
        item, bought, use = self.ids(result)
        proposals.accept(self.conn, self.registry, bought)
        self.store.create("stock__movements", {"item": self.lentils()["id"], "reason": "used", "amount": 1})
        with self.assertRaises(PlainError):
            proposals.accept(self.conn, self.registry, use)
        self.assertEqual(self.statuses(), ["accepted", "accepted", "pending"])
        self.assertIn("more than there is", self.conn.execute("SELECT reason FROM core__proposals WHERE id = ?",
                                                               (use,)).fetchone()[0])

    def test_a_needed_item_that_cannot_be_added_keeps_both_waiting_with_reasons(self):
        result = self.receipt()
        item, movement, _beans = self.ids(result)
        self.store.create("stock__items", {"name": "Other"})
        # The item's stored values are made unusable, as if a module had changed since it was suggested.
        self.conn.execute("UPDATE core__proposals SET values_json = ? WHERE id = ?",
                          (json.dumps({"name": "Red lentils", "category": "nonsense"}), item))
        self.conn.commit()
        with self.assertRaises(PlainError):
            proposals.accept(self.conn, self.registry, movement)
        self.assertEqual(self.statuses(), ["pending", "pending", "pending"])
        self.assertIsNone(self.lentils())
        reasons = dict(self.conn.execute("SELECT id, reason FROM core__proposals"))
        self.assertIn("This can't be added as it is", reasons[item])
        self.assertIn("This needs a new record in Stock items above, which cannot be added yet", reasons[movement])

    def test_rejecting_the_item_rejects_its_stock_in_but_not_the_rest(self):
        result = self.receipt()
        item, movement, _beans = self.ids(result)
        self.assertEqual(proposals.reject_counted(self.conn, item), ("stock__items", 1))
        self.assertEqual(self.statuses(), ["rejected", "rejected", "pending"])
        self.assertIn("Rejected with entry 0", self.conn.execute("SELECT reason FROM core__proposals WHERE id = ?",
                                                                  (movement,)).fetchone()[0])
        detail = proposals.batch_result(self.conn, result["batch_id"], detail=True)
        self.assertEqual([p["status"] for p in detail["proposals"]], ["rejected", "rejected", "pending"])

    def test_rejecting_only_the_stock_in_leaves_the_item_waiting(self):
        result = self.receipt()
        item, movement, _beans = self.ids(result)
        self.assertEqual(proposals.reject_counted(self.conn, movement), ("stock__movements", 0))
        self.assertEqual(self.statuses(), ["pending", "rejected", "pending"])
        proposals.accept(self.conn, self.registry, item)
        self.assertFalse(self.lentils()["quantity"])  # added, with nothing bought yet

    def test_a_stock_in_whose_item_was_rejected_cannot_be_accepted(self):
        result = self.receipt()
        item, movement, _beans = self.ids(result)
        self.conn.execute("UPDATE core__proposals SET status = 'rejected' WHERE id = ?", (item,))  # as if from before
        self.conn.commit()
        with self.assertRaises(PlainError) as caught:
            proposals.accept(self.conn, self.registry, movement)
        self.assertIn("which was rejected", str(caught.exception))
        self.assertIsNone(self.lentils())

    def test_accept_all_adds_each_in_order_once(self):
        result = self.receipt()
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, result["batch_id"]), (3, []))
        self.assertEqual(self.lentils()["quantity"], 2)
        self.assertEqual(self.store.get("stock__items", self.beans)["quantity"], 7)
        self.assertEqual(self.store.count("stock__movements"), 2)
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, result["batch_id"]), (0, []))

    def test_accept_all_skips_what_needs_a_row_that_failed(self):
        result = self.receipt()
        item, movement, _beans = self.ids(result)
        self.conn.execute("UPDATE core__proposals SET values_json = ? WHERE id = ?",
                          (json.dumps({"name": "Red lentils", "category": "nonsense"}), item))
        self.conn.commit()
        added, failed = proposals.accept_batch(self.conn, self.registry, result["batch_id"])
        self.assertEqual((added, len(failed)), (1, 2))
        self.assertEqual(self.statuses(), ["pending", "pending", "accepted"])
        self.assertIn("needs a suggestion above", failed[1])

    def test_reject_all_counts_each_row_once(self):
        result = self.receipt()
        self.assertEqual(proposals.reject_batch(self.conn, result["batch_id"]), 3)
        self.assertEqual(self.statuses(), ["rejected"] * 3)

    def test_imports_are_unchanged(self):
        batch = proposals.stage_import(self.conn, "pantry.csv", [(2, "stock__places", {"name": "Shed"})])
        added, failed = proposals.accept_batch(self.conn, self.registry, batch)
        self.assertEqual((added, failed), (1, []))
        self.assertEqual(self.conn.execute("SELECT source_json FROM core__proposals").fetchone()[0], None)


class ReviewPageTests(GroupedTestCase):
    def setUp(self):
        super().setUp()
        settings.put(self.conn, "setup.done", True)
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=session-key", base_url=BASE)

    def page(self, path="/review"):
        return self.client.get(path, base_url=BASE).get_data(as_text=True)

    def post(self, path):
        response = self.client.post(path, data={"_csrf": self.app.config["CSRF_TOKEN"]}, base_url=BASE)
        return self.page(response.headers["Location"])

    def test_the_group_and_its_receipt_lines_are_shown_as_the_helpers_words(self):
        self.receipt()
        page = self.page()
        self.assertIn("Accepting the Stock in also adds its new Stock item. Accepting only the Stock item leaves the "
                      "Stock in waiting. Rejecting the Stock item rejects the Stock in too.", page)
        self.assertIn("<bdi>Add 2 bags of Red lentils on 20/11/26</bdi>", page)
        self.assertIn("From the receipt or paper, as Pantry helper read it: <q><bdi>RED LENTILS 500G x2</bdi></q> · "
                      "Price: <bdi>3.80</bdi>. Shown for checking only; it is not saved in your records.", page)
        self.assertIn("Accepting this Stock in also adds its new Stock item above.", page)
        self.assertIn("Accepting only this leaves the 1 row below waiting. Rejecting this also rejects the 1 row below "
                      "that needs it.", page)
        self.assertEqual(page.count("<strong>Added together</strong>"), 1)  # the Kidney beans row stands alone

    def test_text_in_a_source_line_is_escaped(self):
        self.send([self.bought(self.beans, source={"line": "<b>BEANS</b>"})])
        page = self.page()
        self.assertIn("&lt;b&gt;BEANS&lt;/b&gt;", page)
        self.assertNotIn("<b>BEANS", page)

    def test_accepting_the_stock_in_on_review_says_its_item_was_added_too(self):
        result = self.receipt()
        page = self.post(f"/review/{result['proposals'][1]['id']}/accept")
        self.assertIn("Added to Stock in and out, together with the 1 row it needed.", page)
        self.assertNotIn("go together", page)
        self.assertIn("KIDNEY BEANS 400G x2", page)  # the third row still waits

    def test_after_the_item_is_accepted_the_stock_in_shows_its_name(self):
        result = self.receipt()
        self.post(f"/review/{result['proposals'][0]['id']}/accept")
        page = self.page()
        self.assertIn("<bdi>Add 2 bags of Red lentils on 20/11/26</bdi>", page)
        self.assertNotIn("go together", page)

    def test_rejecting_the_item_on_review_says_what_went_with_it(self):
        result = self.receipt()
        page = self.post(f"/review/{result['proposals'][0]['id']}/reject")
        self.assertIn("Rejected. Nothing was added to Stock items. 1 row that needed it was rejected too.", page)
        self.assertNotIn("RED LENTILS", page)

    def test_skipping_one_row_of_a_batch_leaves_the_rest_and_the_group(self):
        result = self.receipt()
        page = self.post(f"/review/{result['proposals'][2]['id']}/reject")
        self.assertIn("Rejected. Nothing was added to Stock in and out.", page)
        self.assertIn("<strong>Added together</strong>", page)
        self.assertEqual(len(re.findall(r'action="/review/\d+/accept"', page)), 2)

    def test_accept_all_on_review(self):
        result = self.receipt()
        page = self.post(f"/review/batch/{result['batch_id']}/accept-all")
        self.assertIn("Added 1 to Stock items and 2 to Stock in and out.", page)
        self.assertEqual(self.lentils()["quantity"], 2)


class ConnectorSchemaTests(TempDirTestCase):
    def test_the_suggest_tool_takes_a_source_and_a_ref_and_nothing_else(self):
        from dashboard.connector import tools
        schema = tools.BY_NAME["dashboard_suggest_new_records"].schema
        good = {"request_key": "r-1", "why": WHY, "entries": [
            {"table": "stock__items", "values": {"name": "Red lentils"}, "source": {"line": "RED LENTILS 500G"}},
            {"table": "stock__movements", "values": {"item": {"ref": 0}, "amount": 2},
             "source": {"line": "RED LENTILS 500G x2", "price": "3.80"}}]}
        self.assertEqual(tools.problems(schema, good), [])
        bad = json.loads(json.dumps(good))
        bad["entries"][0]["source"]["shop"] = "Example Market"
        bad["entries"][1]["source"]["line"] = "x" * 201
        self.assertEqual(len(tools.problems(schema, bad)), 2)
        self.assertIn('{"ref": N}', tools.BY_NAME["dashboard_suggest_new_records"].description)
