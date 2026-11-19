"""Tests for helpers' suggestions: they wait in their own place, and reach the records only when a person accepts."""
import json
import shutil
from unittest import mock

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, proposals, records, startup, watch
from dashboard.core.proposals import ProposalError
from dashboard.errors import PlainError

REASON = "Copied from Saturday's paper receipt"


class ProposalTests(TempDirTestCase):
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
        self.beans = self.store.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 5,
                                                        "minimum": 8})
        self.helper, _ = helpers.issue(self.conn, self.data, "Receipt helper", "suggest", ["stock"])
        self.other, _ = helpers.issue(self.conn, self.data, "Other helper", "suggest", ["stock"])

    def bought(self, amount=3, item=None, **more):
        return {"table": "stock__movements", "values": dict({"item": item or self.beans, "reason": "bought",
                                                              "amount": amount}, **more)}

    def send(self, entries, key="receipt-1", why=REASON, helper=None):
        return proposals.submit(self.conn, self.registry, helper or self.helper,
                                {"request_key": key, "why": why, "entries": entries})

    def quantity(self):
        return self.store.get("stock__items", self.beans)["quantity"]

    def count(self, table="stock__movements"):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def refused(self, body_or_entries, status, code=None, **kwargs):
        with self.assertRaises(ProposalError) as caught:
            if isinstance(body_or_entries, list):
                self.send(body_or_entries, **kwargs)
            else:
                proposals.submit(self.conn, self.registry, kwargs.get("helper") or self.helper, body_or_entries)
        self.assertEqual(caught.exception.status, status)
        if code:
            self.assertEqual(caught.exception.code, code)
        return caught.exception

    # ----- waiting -------------------------------------------------------------------------------------
    def test_a_suggestion_changes_nothing_until_it_is_accepted(self):
        result, created = self.send([self.bought(3)])
        self.assertTrue(created)
        self.assertEqual(result["state"], "waiting")
        self.assertIn("1 suggestion is waiting for the household to review. Nothing changes until they accept it.",
                      result["message"])
        self.assertEqual(self.count(), 0)
        self.assertEqual(self.quantity(), 5)
        self.assertEqual(len(watch.running_low(self.conn, self.registry)), 1)
        self.assertEqual(proposals.pending_count(self.conn), 1)
        history = [r["action"] for r in self.conn.execute(
            "SELECT action FROM core__audit WHERE actor = 'agent:receipt-helper'")]
        self.assertEqual(history, ["propose"])  # and no values are copied into the history
        row = self.conn.execute("SELECT after FROM core__audit WHERE action = 'propose'").fetchone()
        self.assertEqual(set(json.loads(row["after"])), {"table", "batch"})

    def test_accepting_adds_the_record_in_the_persons_name_and_the_stock_changes_only_now(self):
        result, _ = self.send([self.bought(3)])
        table, record_id = proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])
        self.assertEqual(table, "stock__movements")
        row = self.conn.execute("SELECT * FROM stock__movements WHERE id = ?", (record_id,)).fetchone()
        self.assertEqual((row["source"], row["review_status"], row["edited_by_person"], row["batch_id"]),
                         ("agent:receipt-helper", "confirmed", 1, result["batch_id"]))
        self.assertEqual(self.quantity(), 8)
        self.assertEqual(proposals.pending_count(self.conn), 0)
        decided = self.conn.execute("SELECT * FROM core__proposals").fetchone()
        self.assertEqual((decided["status"], decided["record_id"]), ("accepted", record_id))
        actions = [(r["actor"], r["action"]) for r in self.conn.execute(
            "SELECT actor, action FROM core__audit WHERE table_name = 'stock__movements' OR action = 'accept' "
            "ORDER BY id")]
        self.assertIn(("agent:receipt-helper", "create"), actions)
        self.assertIn(("person", "accept"), actions)

    def test_rejecting_changes_nothing(self):
        result, _ = self.send([self.bought(3)])
        proposals.reject(self.conn, result["proposals"][0]["id"])
        self.assertEqual((self.count(), self.quantity()), (0, 5))
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals").fetchone()[0], "rejected")
        self.assertIn(("person", "reject"), [(r["actor"], r["action"]) for r in self.conn.execute(
            "SELECT actor, action FROM core__audit")])
        with self.assertRaises(PlainError):
            proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])  # decided once only
        again, created = self.send([self.bought(3)])  # a retry never brings a rejected suggestion back
        self.assertFalse(created)
        self.assertEqual(again["proposals"][0]["status"], "rejected")
        self.assertEqual(proposals.pending_count(self.conn), 0)

    def test_a_stale_stock_out_stays_waiting_with_the_reason_and_writes_nothing(self):
        used = {"table": "stock__movements", "values": {"item": self.beans, "reason": "used", "amount": 4}}
        result, _ = self.send([used])
        self.store.create("stock__movements", {"item": self.beans, "reason": "used", "amount": 3})  # now only 2 left
        before = self.count()
        with self.assertRaises(PlainError) as caught:
            proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])
        self.assertIn("This can't be added as it is", str(caught.exception))
        self.assertIn("Reject it, or add the record yourself.", str(caught.exception))
        self.assertEqual((self.count(), self.quantity()), (before, 2))
        row = self.conn.execute("SELECT status, reason FROM core__proposals").fetchone()
        self.assertEqual(row["status"], "pending")
        self.assertIn("more than there is", row["reason"])

    def test_accepting_a_whole_batch_reports_the_ones_that_could_not_be_added(self):
        used = {"table": "stock__movements", "values": {"item": self.beans, "reason": "used", "amount": 4}}
        result, _ = self.send([self.bought(3), used, self.bought(1)])
        self.store.create("stock__movements", {"item": self.beans, "reason": "used", "amount": 3})
        added, failed = proposals.accept_batch(self.conn, self.registry, result["batch_id"])
        self.assertEqual((added, len(failed)), (2, 1))
        self.assertEqual(proposals.pending_count(self.conn), 1)
        self.assertEqual(self.quantity(), 2 + 3 + 1)

    # ----- all or nothing ---------------------------------------------------------------------------------
    def test_one_bad_entry_means_nothing_is_stored(self):
        bad = {"table": "stock__movements", "values": {"item": self.beans, "reason": "bought", "amount": -2}}
        error = self.refused([self.bought(3), bad, self.bought(1)], 422, "invalid")
        self.assertEqual([(p["entry"], p["table"], p["field"]) for p in error.problems],
                         [(1, "stock__movements", "amount")])
        self.assertIn("Nothing was saved.", str(error))
        self.assertEqual((self.count("core__helper_batches"), self.count("core__proposals")), (0, 0))
        self.assertEqual((self.count(), self.quantity()), (0, 5))  # the dry run left nothing behind

    def test_the_dry_run_counts_earlier_entries_for_later_ones(self):
        too_much = [{"table": "stock__movements", "values": {"item": self.beans, "reason": "used", "amount": 4}}] * 2
        error = self.refused(too_much, 422, "invalid")
        self.assertEqual([p["entry"] for p in error.problems], [1])
        self.assertEqual(self.quantity(), 5)

    def test_values_are_stored_as_sent_not_cleaned(self):
        result, _ = self.send([self.bought(" 3 ")])
        stored = self.conn.execute("SELECT values_json FROM core__proposals").fetchone()[0]
        self.assertEqual(json.loads(stored)["amount"], " 3 ")

    # ----- retrying ----------------------------------------------------------------------------------------
    def test_a_retry_with_the_same_key_and_body_returns_the_first_answer(self):
        first, created = self.send([self.bought(3)])
        again, created_again = self.send([self.bought(3)])
        self.assertEqual((created, created_again), (True, False))
        self.assertEqual(first["batch_id"], again["batch_id"])
        self.assertEqual(self.count("core__proposals"), 1)

    def test_the_same_key_with_different_suggestions_is_refused(self):
        self.send([self.bought(3)])
        self.refused([self.bought(4)], 409, "request_key_reused")
        self.assertEqual(self.count("core__proposals"), 1)

    def test_another_helper_may_use_the_same_key(self):
        self.send([self.bought(3)])
        _, created = self.send([self.bought(4)], helper=self.other)
        self.assertTrue(created)

    # ----- limits ------------------------------------------------------------------------------------------
    def test_fifty_one_entries_in_a_call_are_refused(self):
        error = self.refused([self.bought(1)] * 51, 400, "bad_request")
        self.assertEqual(str(error), "Send 50 suggestions or fewer at a time.")
        self.assertEqual(self.count("core__proposals"), 0)

    def test_the_two_hundred_and_first_suggestion_of_a_day_is_refused_without_a_partial_batch(self):
        for n in range(4):
            self.send([self.bought(1)] * 50, key=f"day-{n}")
        self.assertEqual(proposals.used_today(self.conn, self.helper), 200)
        error = self.refused([self.bought(1)], 429, "daily_limit", key="one-too-many")
        self.assertEqual(str(error), "This helper has reached 200 suggestions today. Try again tomorrow.")
        self.assertEqual(self.count("core__proposals"), 200)
        self.assertEqual(self.count("core__helper_batches"), 4)
        self.send([self.bought(1)], key="other-helper-fine", helper=self.other)

    def test_a_request_must_be_shaped_properly(self):
        good = {"request_key": "k1", "why": REASON, "entries": [self.bought(1)]}
        cases = {"no key": {k: v for k, v in good.items() if k != "request_key"},
                 "odd key": dict(good, request_key="has spaces"), "empty key": dict(good, request_key=""),
                 "long key": dict(good, request_key="k" * 101), "no why": dict(good, why="  "),
                 "long why": dict(good, why="w" * 301), "no entries": dict(good, entries=[]),
                 "entries not a list": dict(good, entries={"a": 1}), "extra top-level field": dict(good, status="accepted"),
                 "entry with extra field": dict(good, entries=[dict(self.bought(1), review_status="confirmed")]),
                 "values not an object": dict(good, entries=[{"table": "stock__movements", "values": [1]}]),
                 "not an object": ["entries"]}
        for what, body in cases.items():
            with self.subTest(what):
                self.refused(body, 400, "bad_request")
        self.assertEqual(self.count("core__helper_batches"), 0)

    # ----- text that is never kept (decision 0074) -------------------------------------------------------------
    def test_something_that_looks_like_a_helper_key_is_refused_and_never_kept(self):
        key = "dph_" + "Ab3-_x" * 7  # made up, shaped like a real key
        good = {"request_key": "k1", "why": REASON, "entries": [self.bought(1)]}
        cases = {"in why": dict(good, why=f"My key is {key}"), "as the request key": dict(good, request_key=key),
                 "in a value": dict(good, entries=[self.bought(1, note=key)]),
                 "as a field name": dict(good, entries=[self.bought(1, **{key: "x"})]),
                 "as a table name": dict(good, entries=[{"table": key, "values": {}}])}
        for what, body in cases.items():
            with self.subTest(what):
                error = self.refused(body, 400, "looks_like_a_key")
                self.assertEqual(str(error), "That looks like a helper key. Keys belong only in the Authorization header.")
                self.assertEqual(error.problems, [])
        self.assertEqual(self.count("core__helper_batches"), 0)
        self.assertEqual(self.count("core__proposals"), 0)

    def test_hidden_or_text_reversing_characters_are_refused(self):
        good = {"request_key": "k1", "why": REASON, "entries": [self.bought(1)]}
        for character in ("\u202e", "\u202a", "\u2066", "\u2069", "\x00", "\t", "\r", "\x1b", "\x7f", "\x85"):
            for where, body in {"why": dict(good, why=f"Receipt {character}total"),
                                "value": dict(good, entries=[self.bought(1, note=f"tin{character}s")])}.items():
                with self.subTest(character=repr(character), where=where):
                    error = self.refused(body, 400, "hidden_characters")
                    self.assertNotIn(character, str(error))
        self.assertEqual(self.count("core__helper_batches"), 0)

    def test_a_line_break_in_why_is_fine(self):
        result, created = self.send([self.bought(1)], why="From the receipt.\nTwo tins were dented.")
        self.assertTrue(created)
        self.assertEqual(result["why"], "From the receipt.\nTwo tins were dented.")

    # ----- one decision only (decision 0074) ----------------------------------------------------------------------
    def test_two_decisions_at_the_same_moment_make_exactly_one(self):
        """Both clicks read the suggestion as waiting before either is saved: only the first may win."""
        result, _ = self.send([self.bought(3)])
        pid = result["proposals"][0]["id"]
        seen_waiting = proposals._load(self.conn, pid)
        proposals.accept(self.conn, self.registry, pid)
        with mock.patch.object(proposals, "_load", lambda conn, proposal_id: seen_waiting):
            for second in (lambda: proposals.accept(self.conn, self.registry, pid),
                           lambda: proposals.reject(self.conn, pid)):
                with self.assertRaises(PlainError) as caught:
                    second()
                self.assertIn("already been decided", str(caught.exception))
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.quantity(), 8)  # the stock moved once
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals").fetchone()[0], "accepted")
        decisions = [r[0] for r in self.conn.execute(
            "SELECT action FROM core__audit WHERE action IN ('accept', 'reject')")]
        self.assertEqual(decisions, ["accept"])

    def test_a_reject_at_the_same_moment_as_an_accept_adds_nothing(self):
        result, _ = self.send([self.bought(3)])
        pid = result["proposals"][0]["id"]
        seen_waiting = proposals._load(self.conn, pid)
        proposals.reject(self.conn, pid)
        with mock.patch.object(proposals, "_load", lambda conn, proposal_id: seen_waiting):
            with self.assertRaises(PlainError):
                proposals.accept(self.conn, self.registry, pid)
        self.assertEqual((self.count(), self.quantity()), (0, 5))
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals").fetchone()[0], "rejected")

    def test_accepting_a_whole_batch_twice_adds_each_row_once(self):
        result, _ = self.send([self.bought(1), self.bought(2)])
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, result["batch_id"]), (2, []))
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, result["batch_id"]), (0, []))
        self.assertEqual(self.count(), 2)

    # ----- what may be sent ----------------------------------------------------------------------------------
    def test_system_fields_and_odd_field_names_are_refused_and_tables_stay_intact(self):
        for field in ("review_status", "source", "edited_by_person", "id", "batch_id", "deleted_at",
                      "amount; DROP TABLE stock__items"):
            with self.subTest(field):
                error = self.refused([self.bought(1, **{field: "x"})], 422, "invalid")
                self.assertIn("is not a field of this table.", error.problems[0]["message"])
        self.assertEqual(self.quantity(), 5)
        self.assertEqual(self.count("stock__items"), 1)

    def test_a_worked_out_column_must_not_be_suggested(self):
        item = {"table": "stock__items", "values": {"name": "Rice", "quantity": 4}}
        error = self.refused([item], 422, "invalid")
        self.assertIn("worked out", error.problems[0]["message"])
        self.assertEqual(self.count("stock__items"), 1)

    def test_a_look_only_helper_cannot_suggest(self):
        reader, _ = helpers.issue(self.conn, self.data, "Reader", "read", ["stock"])
        self.refused([self.bought(1)], 403, "look_only", helper=reader)

    def test_tables_outside_the_grant_or_unknown_are_refused(self):
        narrow, _ = helpers.issue(self.conn, self.data, "Narrow", "suggest", ["people"])
        hidden = self.refused([self.bought(1)], 404, "not_found", helper=narrow)
        unknown = self.refused([{"table": "nope__nothing", "values": {}}], 404, "not_found")
        self.assertEqual(str(hidden), str(unknown))

    # ----- switched-off parts ---------------------------------------------------------------------------------
    def test_a_suggestion_for_a_switched_off_module_can_only_be_rejected(self):
        result, _ = self.send([self.bought(3)])
        proposal_id = result["proposals"][0]["id"]
        with self.assertRaises(PlainError) as caught:
            proposals.accept(self.conn, {}, proposal_id)
        self.assertIn("switched off", str(caught.exception))
        self.assertEqual(self.count(), 0)
        proposals.reject(self.conn, proposal_id)
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals").fetchone()[0], "rejected")

    # ----- the helper's own view ----------------------------------------------------------------------------------
    def test_batches_are_listed_newest_first_with_totals_and_only_for_their_owner(self):
        first, _ = self.send([self.bought(1), self.bought(2)], key="a")
        second, _ = self.send([self.bought(1)], key="b")
        proposals.reject(self.conn, first["proposals"][0]["id"])
        listed = proposals.helper_batches(self.conn, self.helper, None, 20)
        self.assertEqual([b["id"] for b in listed], [second["batch_id"], first["batch_id"]])
        self.assertEqual({k: listed[1][k] for k in ("total", "pending", "accepted", "rejected")},
                         {"total": 2, "pending": 1, "accepted": 0, "rejected": 1})
        self.assertEqual(proposals.helper_batches(self.conn, self.other, None, 20), [])
        self.assertTrue(proposals.owns(self.conn, self.helper, first["batch_id"]))
        self.assertFalse(proposals.owns(self.conn, self.other, first["batch_id"]))
        page = proposals.helper_batches(self.conn, self.helper, second["batch_id"], 20)
        self.assertEqual([b["id"] for b in page], [first["batch_id"]])

    # ----- the review queue cap (decision 0085) ----------------------------------------------------------
    def send_capped(self, count, key, helper=None, limit=5):
        body = {"request_key": key, "why": REASON, "entries": [self.bought(1) for _ in range(count)]}
        return proposals.submit(self.conn, self.registry, helper or self.helper, body, queue_limit=limit)

    def test_queue_cap_defaults_to_five_hundred_and_reaching_it_exactly_is_allowed(self):
        self.assertEqual(proposals.MAX_WAITING, 500)
        self.send_capped(5, "exactly")
        self.assertEqual(proposals.waiting_for(self.conn, self.helper), 5)

    def test_queue_cap_one_over_is_refused_whole_and_nothing_is_kept(self):
        self.send_capped(3, "first")
        error = self.refused_capped(3, "second")  # 3 waiting + 3 would be 6, one over
        self.assertEqual((error.status, error.code), (429, "review_queue_full"))
        self.assertEqual(str(error), "3 suggestions from this helper are already waiting on Review. "
                                     "Ask the household to look at them first.")
        self.assertEqual(self.count("core__proposals"), 3)
        self.assertEqual(self.count("core__helper_batches"), 1)
        self.send_capped(2, "fits")  # the room that was left is still usable

    def refused_capped(self, count, key, helper=None):
        with self.assertRaises(ProposalError) as caught:
            self.send_capped(count, key, helper)
        return caught.exception

    def test_queue_cap_message_is_singular_for_one_waiting(self):
        self.send_capped(1, "a")
        self.assertEqual(str(self.refused_capped(5, "b")), "1 suggestion from this helper is already waiting on "
                                                          "Review. Ask the household to look at them first.")

    def test_queue_cap_accepting_or_rejecting_frees_room(self):
        first, _ = self.send_capped(5, "full")
        self.refused_capped(1, "no-room")
        proposals.reject(self.conn, first["proposals"][0]["id"])
        self.assertEqual(proposals.waiting_for(self.conn, self.helper), 4)
        self.send_capped(1, "room-after-reject")
        self.refused_capped(1, "full-again")
        proposals.accept(self.conn, self.registry, first["proposals"][1]["id"])
        self.send_capped(1, "room-after-accept")

    def test_queue_cap_a_retry_still_gets_its_first_answer_when_full(self):
        first, _ = self.send_capped(5, "same")
        again, created = self.send_capped(5, "same")
        self.assertFalse(created)
        self.assertEqual(again["batch_id"], first["batch_id"])

    def test_queue_cap_is_per_helper_and_imports_use_none_of_it(self):
        self.send_capped(5, "mine")
        self.send_capped(5, "theirs", helper=self.other)
        rows = [(n, "stock__movements", self.bought(1)["values"]) for n in range(2, 12)]
        proposals.stage_import(self.conn, "pantry.csv", rows)
        self.assertEqual(proposals.waiting_for(self.conn, self.helper), 5)
        self.refused_capped(1, "still-full")  # waiting imported rows neither fill nor free anything
        first = self.conn.execute("SELECT p.id FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
                                  "WHERE b.helper_id = ? LIMIT 1", (self.helper.id,)).fetchone()[0]
        proposals.reject(self.conn, first)
        self.send_capped(1, "after-import")

    def test_queue_cap_is_checked_before_the_entries_are(self):
        self.send_capped(5, "fill")
        body = {"request_key": "x", "why": REASON, "entries": [{"table": "nowhere", "values": {}}]}
        with self.assertRaises(ProposalError) as caught:
            proposals.submit(self.conn, self.registry, self.helper, body, queue_limit=5)
        self.assertEqual(caught.exception.code, "review_queue_full")
