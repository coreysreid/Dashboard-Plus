"""Tests for faster Review (decision 0101): Accept all by group, ticked rows, keys, fixed buttons and Allow 200 more today."""
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from support import ROOT, TempDirTestCase
from dashboard.core import db, helpers, proposals, records, settings, startup
from dashboard.core.proposals import IN_GROUP_FAILED, NEEDS_FAILED, ProposalError
from dashboard.web.app import create_app

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
WHY = "Invented Example Market receipt, 20/11/26"


class SpeedTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        settings.put(self.conn, "setup.done", True)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.beans = self.store.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 5})
        self.helper, self.key = helpers.issue(self.conn, self.data, "Pantry helper", "suggest", ["stock"])
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=session-key", base_url=BASE)
        self.csrf = self.app.config["CSRF_TOKEN"]

    # ----- making suggestions -----------------------------------------------------------------------
    @staticmethod
    def new_item(name="Red lentils"):
        return {"table": "stock__items", "values": {"name": name, "category": "pantry", "unit": "bags"}}

    @staticmethod
    def bought(item, amount=2):
        return {"table": "stock__movements", "values": {"item": item, "reason": "bought", "amount": amount,
                                                        "happened_on": "2026-11-20"}}

    @staticmethod
    def used(item, amount=1):
        return {"table": "stock__movements", "values": {"item": item, "reason": "used", "amount": amount,
                                                        "happened_on": "2026-11-20"}}

    def send(self, entries, key="receipt-1", helper=None):
        return proposals.submit(self.conn, self.registry, helper or self.helper,
                                {"request_key": key, "why": WHY, "entries": entries})[0]

    def receipt(self):
        """Two groups (a new item with its Stock in, twice) and one row on its own."""
        return self.send([self.new_item("Red lentils"), self.bought({"ref": 0}),
                          self.bought(self.beans),
                          self.new_item("Rolled oats"), self.bought({"ref": 3}, amount=1)])

    def ids(self, result):
        return [p["id"] for p in result["proposals"]]

    def statuses(self):
        return [r[0] for r in self.conn.execute("SELECT status FROM core__proposals ORDER BY batch_id, position")]

    def reasons(self):
        return [r[0] for r in self.conn.execute("SELECT reason FROM core__proposals ORDER BY batch_id, position")]

    def item(self, name):
        return self.conn.execute("SELECT id, quantity FROM stock__items WHERE name = ?", (name,)).fetchone()

    def spoil(self, proposal_id, values):
        """Make a stored suggestion unusable, as if the household's records changed since it was sent."""
        self.conn.execute("UPDATE core__proposals SET values_json = ? WHERE id = ?", (json.dumps(values), proposal_id))
        self.conn.commit()

    def fill(self, count, helper=None, at=None):
        """Record `count` suggestions already sent by a helper (today, unless `at` says otherwise)."""
        helper = helper or self.helper
        at = at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db.transaction(self.conn):
            batch = self.conn.execute(
                "INSERT INTO core__helper_batches (helper_id, request_key, body_hash, why, created_at) "
                "VALUES (?, ?, 'x', 'Filler', ?)", (helper.id, f"fill-{self.conn.execute('SELECT COUNT(*) FROM core__helper_batches').fetchone()[0]}", at)).lastrowid
            for n in range(count):
                self.conn.execute("INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at, "
                                  "status) VALUES (?, ?, 'stock__places', '{\"name\": \"Shelf\"}', ?, 'rejected')",
                                  (batch, n, at))

    # ----- the pages ----------------------------------------------------------------------------------
    def page(self, path="/review"):
        return self.client.get(path, base_url=BASE).get_data(as_text=True)

    def post(self, path, data=None, token=True):
        data = dict(data or {}, **({"_csrf": self.csrf} if token else {}))
        return self.client.post(path, data=data, base_url=BASE)

    def follow(self, path, data=None):
        response = self.post(path, data)
        self.assertEqual(response.status_code, 302)
        return self.page(response.headers["Location"])


class AcceptAllTests(SpeedTestCase):
    def test_accept_all_adds_every_group_in_order(self):
        result = self.receipt()
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, result["batch_id"]), (5, []))
        self.assertEqual(self.statuses(), ["accepted"] * 5)
        self.assertEqual(self.item("Red lentils")["quantity"], 2)
        self.assertEqual(self.item("Rolled oats")["quantity"], 1)
        self.assertEqual(self.store.get("stock__items", self.beans)["quantity"], 7)

    def test_a_group_whose_stock_in_fails_adds_nothing_and_the_rest_still_go_in(self):
        result = self.receipt()
        lentils, lentils_in, _beans, _oats, _oats_in = self.ids(result)
        self.spoil(lentils_in, {"item": {"ref": 0}, "reason": "bought", "amount": "lots"})
        added, failed = proposals.accept_batch(self.conn, self.registry, result["batch_id"])
        self.assertEqual((added, len(failed)), (3, 2))
        self.assertEqual(self.statuses(), ["pending", "pending", "accepted", "accepted", "accepted"])
        self.assertIsNone(self.item("Red lentils"))  # the group is all or nothing: its item waits too
        reasons = self.reasons()
        self.assertEqual(reasons[0], IN_GROUP_FAILED)
        self.assertIn("This can't be added as it is", reasons[1])
        self.assertEqual(reasons[2:], [None, None, None])

    def test_a_group_whose_new_item_fails_says_so_on_the_stock_in(self):
        result = self.receipt()
        lentils = self.ids(result)[0]
        self.spoil(lentils, {"name": "Red lentils", "category": "nonsense"})
        added, failed = proposals.accept_batch(self.conn, self.registry, result["batch_id"])
        self.assertEqual((added, len(failed)), (3, 2))
        self.assertIn("This can't be added as it is", self.reasons()[0])
        self.assertEqual(self.reasons()[1], NEEDS_FAILED)

    def test_a_row_whose_needed_row_was_rejected_waits_with_its_reason(self):
        result = self.receipt()
        lentils, lentils_in = self.ids(result)[:2]
        self.conn.execute("UPDATE core__proposals SET status = 'rejected' WHERE id = ?", (lentils,))  # as if from before
        self.conn.commit()
        added, failed = proposals.accept_batch(self.conn, self.registry, result["batch_id"])
        self.assertEqual((added, len(failed)), (3, 1))
        self.assertIn("which was rejected", self.reasons()[1])

    def test_on_review_accept_all_asks_first_with_the_count_and_the_tables(self):
        result = self.receipt()
        page = self.page()
        self.assertIn('<summary class="button" role="button">Accept all 5</summary>', page)
        self.assertIn("This adds 5 new records: 2 to Stock items and 3 to Stock in and out.", page)
        confirm = re.search(r'<details class="confirm-all">(.*?)</details>', page, re.S).group(1)
        self.assertIn(f'action="/review/batch/{result["batch_id"]}/accept-all"', confirm)
        self.assertIn("Yes, accept all 5", confirm)
        self.assertEqual(self.store.count("stock__movements"), 0)  # showing it adds nothing

    def test_on_review_accept_all_reports_the_group_left_waiting(self):
        result = self.receipt()
        self.spoil(self.ids(result)[1], {"item": {"ref": 0}, "reason": "bought", "amount": "lots"})
        page = self.follow(f"/review/batch/{result['batch_id']}/accept-all")
        self.assertIn("Added 2 to Stock in and out and 1 to Stock items. 2 could not be added and are still waiting: see "
                      "the reasons below.", page)
        self.assertIn("Nothing in this group was added.", page)
        self.assertIn("Added together", page)

    def test_accept_all_needs_the_pages_own_token(self):
        result = self.receipt()
        self.assertEqual(self.post(f"/review/batch/{result['batch_id']}/accept-all", token=False).status_code, 400)
        self.assertEqual(self.statuses(), ["pending"] * 5)


class TickedTests(SpeedTestCase):
    def test_ticking_a_stock_in_accepts_its_whole_group_and_nothing_else(self):
        result = self.receipt()
        _lentils, lentils_in, *_rest = self.ids(result)
        self.assertEqual(proposals.accept_ticked(self.conn, self.registry, [lentils_in]), (2, []))
        self.assertEqual(self.statuses(), ["accepted", "accepted", "pending", "pending", "pending"])

    def test_ticked_rows_from_two_batches(self):
        first = self.receipt()
        second = self.send([self.bought(self.beans, amount=3)], key="receipt-2")
        added, failed = proposals.accept_ticked(self.conn, self.registry, [self.ids(first)[3], self.ids(second)[0]])
        self.assertEqual((added, failed), (3, []))
        self.assertEqual(self.store.get("stock__items", self.beans)["quantity"], 8)
        self.assertEqual(self.item("Rolled oats")["quantity"], 1)

    def test_a_ticked_group_is_all_or_nothing(self):
        result = self.receipt()
        oats, oats_in = self.ids(result)[3:]
        self.spoil(oats_in, {"item": {"ref": 3}, "reason": "bought", "amount": -4})
        added, failed = proposals.accept_ticked(self.conn, self.registry, [oats, self.ids(result)[2]])
        self.assertEqual((added, len(failed)), (1, 2))
        self.assertIsNone(self.item("Rolled oats"))
        self.assertEqual(self.statuses(), ["pending", "pending", "accepted", "pending", "pending"])

    def test_rejecting_one_ticked_row_rejects_its_group(self):
        result = self.receipt()
        self.assertEqual(proposals.reject_ticked(self.conn, [self.ids(result)[1]]), 2)
        self.assertEqual(self.statuses(), ["rejected", "rejected", "pending", "pending", "pending"])

    def test_ticked_rows_already_decided_are_skipped(self):
        result = self.receipt()
        beans = self.ids(result)[2]
        proposals.reject(self.conn, beans)
        self.assertEqual(proposals.accept_ticked(self.conn, self.registry, [beans]), (0, []))
        self.assertEqual(proposals.reject_ticked(self.conn, [beans, 99999]), 0)

    def test_accept_and_reject_ticked_on_review(self):
        result = self.receipt()
        ids = self.ids(result)
        page = self.follow("/review/ticked/accept", {"ids": [str(ids[0]), str(ids[2])]})
        self.assertIn("Added 1 to Stock items and 2 to Stock in and out.", page)
        page = self.follow("/review/ticked/reject", {"ids": [str(ids[4])]})
        self.assertIn("Rejected 2 rows. Nothing was added.", page)
        self.assertEqual(self.statuses(), ["accepted", "accepted", "accepted", "rejected", "rejected"])
        self.assertIn("Nothing was ticked.", self.follow("/review/ticked/accept", {}))
        self.assertIn("Nothing was ticked.", self.follow("/review/ticked/reject", {"ids": ["not-a-number"]}))

    def test_ticked_forms_need_the_pages_own_token(self):
        result = self.receipt()
        for path in ("/review/ticked/accept", "/review/ticked/reject"):
            self.assertEqual(self.post(path, {"ids": [str(self.ids(result)[2])]}, token=False).status_code, 400)
        self.assertEqual(self.statuses(), ["pending"] * 5)


class RowShape(HTMLParser):
    """Each Review row's direct children (their classes), and the buttons inside its decide column, in order."""

    def __init__(self):
        super().__init__()
        self.rows, self.stack, self.groups = [], [], 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag in ("input", "br", "img", "meta", "link"):
            if tag == "input" and self.stack and self.rows and attrs.get("type") == "checkbox":
                self.rows[-1]["tick"] = attrs.get("form")
            return
        parent = self.stack[-1] if self.stack else None
        self.stack.append({"tag": tag, "classes": classes, "row": "review-row" in classes,
                           "decide": "decide" in classes or (parent and parent["decide"])})
        if "review-group" in classes:
            self.groups += 1
        if "review-row" in classes:
            self.rows.append({"children": [], "buttons": [], "grouped": any(
                "review-group" in s["classes"] for s in self.stack[:-1])})
        elif parent and parent["row"]:
            self.rows[-1]["children"].append(" ".join(classes))
        if tag == "button" and self.stack[-1]["decide"]:
            self.rows[-1]["buttons"].append(attrs)

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()["tag"] == tag:
                break


class LayoutTests(SpeedTestCase):
    def shape(self, page):
        found = RowShape()
        found.feed(page)
        return found

    def test_single_and_grouped_rows_have_their_buttons_in_the_same_column(self):
        self.receipt()
        shape = self.shape(self.page())
        self.assertEqual(shape.groups, 2)
        self.assertEqual(len(shape.rows), 5)
        self.assertEqual([r["grouped"] for r in shape.rows], [True, True, False, True, True])
        for row in shape.rows:
            self.assertEqual(row["children"], ["tick", "what", "decide"])  # always last, always the same place
            self.assertEqual([("data-accept" in b, "data-reject" in b) for b in row["buttons"]],
                             [(True, False), (False, True)])
            self.assertEqual(row["tick"], "ticked")

    def test_a_row_that_cannot_be_accepted_keeps_its_buttons_in_place(self):
        self.send([self.bought(self.beans)])
        settings.set_module_enabled(self.conn, "stock", False)
        shape = self.shape(self.page())
        self.assertEqual(shape.rows[0]["children"], ["tick", "what", "decide"])
        self.assertEqual(len(shape.rows[0]["buttons"]), 2)
        self.assertIn("disabled", shape.rows[0]["buttons"][0])

    def test_a_group_is_shown_by_a_band_and_a_label_not_by_moving_buttons(self):
        self.receipt()
        page = self.page()
        self.assertEqual(page.count("<strong>Added together</strong>"), 2)
        self.assertIn("Ticking one ticks both, and Accept all or Accept ticked adds both or neither.", page)
        self.assertRegex(page, r"\.review-group \{[^}]*border-left: 6px solid var\(--accent\)")
        self.assertRegex(page, r"\.review-row \{[^}]*grid-template-columns: 2rem minmax\(0, 1fr\) var\(--decide\)")
        self.assertRegex(page, r"@media \(max-width: 40rem\) \{[^@]*--decide: 6rem")  # phone width: still a column

    def test_the_keys_hint_and_the_script_are_on_the_page_and_need_nothing_outside(self):
        self.receipt()
        page = self.page()
        self.assertIn('id="review-keys" hidden', page)  # shown by the script, so it never promises keys without it
        self.assertIn("<kbd>A</kbd> accept · <kbd>R</kbd> reject · <kbd>Space</kbd> tick", page)
        self.assertIn("<kbd>J</kbd> <kbd>K</kbd>", page)
        self.assertNotRegex(page, r"<script[^>]+src=")
        self.assertIn('target.closest("input, textarea, select, [contenteditable]")', page)  # never while typing
        self.assertIn('<form id="ticked" method="post" action="/review/ticked/accept">', page)
        self.assertIn('formaction="/review/ticked/reject"', page)

    def test_an_empty_review_has_no_keys_or_ticked_bar(self):
        page = self.page()
        self.assertNotIn("review-keys", page)
        self.assertNotIn("Accept ticked", page)


class AllowanceTests(SpeedTestCase):
    def test_each_press_adds_two_hundred_for_today_only(self):
        self.assertEqual(proposals.limit_today(self.conn, self.helper), 200)
        self.assertEqual(proposals.allow_more(self.conn, self.helper.id), 400)
        self.assertEqual(proposals.allow_more(self.conn, self.helper.id), 600)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        proposals.allow_more(self.conn, self.helper.id, now=yesterday)
        self.assertEqual(proposals.limit_today(self.conn, self.helper), 600)  # yesterday's press counts for nothing
        self.assertEqual(proposals.limit_today(self.conn, self.helper, now=yesterday), 400)
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        self.assertEqual(proposals.limit_today(self.conn, self.helper, now=tomorrow), 200)
        other, _key = helpers.issue(self.conn, self.data, "Other helper", "suggest", ["stock"])
        self.assertEqual(proposals.limit_today(self.conn, other), 200)  # only that helper

    def test_a_press_is_in_the_history_with_who_and_when(self):
        proposals.allow_more(self.conn, self.helper.id)
        row = self.conn.execute("SELECT * FROM core__audit WHERE action = 'helper_allow_more'").fetchone()
        self.assertEqual((row["actor"], row["table_name"], row["record_id"]), ("person", "core__helpers", self.helper.id))
        self.assertEqual(json.loads(row["after"])["extra"], 200)
        self.assertEqual(json.loads(row["after"])["day"], proposals.today()[0])
        kept = self.conn.execute("SELECT * FROM core__helper_allowances").fetchone()
        self.assertEqual((kept["granted_by"], kept["extra"]), ("person", 200))
        self.assertTrue(kept["granted_at"])

    def test_more_allowed_lets_the_helper_send_more_today(self):
        self.fill(200)
        with self.assertRaises(ProposalError) as caught:
            self.send([self.bought(self.beans)], key="one-more")
        self.assertEqual(caught.exception.code, "daily_limit")
        proposals.allow_more(self.conn, self.helper.id)
        self.send([self.bought(self.beans)], key="one-more")
        self.fill(199)
        with self.assertRaises(ProposalError):
            self.send([self.bought(self.beans)], key="past-400")

    def test_the_raised_limit_is_checked_again_inside_the_write_lock(self):
        self.fill(200)
        proposals.allow_more(self.conn, self.helper.id)
        real, looks = proposals.limit_today, []

        def racing(conn, helper, now=None):  # the first look sees the raised limit; by the write it is gone
            looks.append(1)
            return real(conn, helper, now) if len(looks) == 1 else proposals.MAX_PER_DAY
        proposals.limit_today = racing
        self.addCleanup(setattr, proposals, "limit_today", real)
        with self.assertRaises(ProposalError) as caught:
            self.send([self.bought(self.beans)], key="racing")
        self.assertEqual(caught.exception.code, "daily_limit")
        self.assertEqual(len(looks), 2)

    def test_the_day_is_the_households_own_and_used_today_follows_it(self):
        day, began = proposals.today()
        self.assertEqual(day, datetime.now().astimezone().date().isoformat())
        self.fill(3, at=(datetime.fromisoformat(began + "+00:00") - timedelta(seconds=1)).isoformat())
        self.fill(2, at=(datetime.fromisoformat(began + "+00:00") + timedelta(seconds=1)).isoformat())
        self.assertEqual(proposals.used_today(self.conn, self.helper), 2)

    def test_a_helper_off_or_look_only_cannot_be_given_more(self):
        reader, _key = helpers.issue(self.conn, self.data, "Look helper", "read", ["stock"])
        with self.assertRaises(proposals.AllowanceRefused):
            proposals.allow_more(self.conn, reader.id)
        helpers.turn_off(self.conn, self.data, self.helper.id)
        with self.assertRaises(proposals.AllowanceRefused):
            proposals.allow_more(self.conn, self.helper.id)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__helper_allowances").fetchone()[0], 0)

    def test_the_429_tells_the_helper_to_stop_and_ask(self):
        self.fill(200)
        response = self.client.post("/api/v1/proposals", base_url=BASE, headers={"Authorization": f"Bearer {self.key}"},
                                    json={"request_key": "over", "why": WHY, "entries": [self.bought(self.beans)]})
        self.assertEqual(response.status_code, 429)
        body = response.get_json()
        self.assertEqual(body["error"], "daily_limit")
        self.assertIn("Stop sending now and ask the household", body["message"])
        self.assertIn("they can allow more on the Review page", body["message"])
        partly = proposals.daily_limit_message(200, 10)
        self.assertIn("has 10 of its 200 suggestions left for today, fewer than this request holds", partly)

    def test_the_helper_sees_its_raised_limit_in_me(self):
        proposals.allow_more(self.conn, self.helper.id)
        self.fill(5)
        limits = self.client.get("/api/v1/me", base_url=BASE,
                                 headers={"Authorization": f"Bearer {self.key}"}).get_json()["limits"]
        self.assertEqual((limits["suggestions_per_day"], limits["suggestions_left_today"]), (400, 395))

    def test_a_helper_cannot_allow_itself_more(self):
        self.fill(200)
        auth = {"Authorization": f"Bearer {self.key}"}
        for path in ("/api/v1/allow-more", f"/api/v1/helpers/{self.helper.id}/allow-more",
                     f"/settings/helpers/{self.helper.id}/allow-more"):
            response = self.app.test_client().post(path, base_url=BASE, headers=auth, json={})
            self.assertIn(response.status_code, (302, 400, 403, 404, 405), path)
        self.assertEqual(proposals.limit_today(self.conn, self.helper), 200)

    def allow_token(self, page):
        return re.search(r'name="allow_token" value="([^"]+)"', page).group(1)

    def test_review_offers_allow_more_only_when_the_helper_is_near_its_limit(self):
        self.fill(150)
        self.assertNotIn("Allow 200 more today", self.page())
        self.fill(10)
        page = self.page()
        self.assertIn("Pantry helper has used 160 of its 200 suggestions for today, so it has 40 left.", page)
        self.assertIn('aria-label="Allow 200 more suggestions today for Pantry helper"', page)
        page = self.follow(f"/settings/helpers/{self.helper.id}/allow-more",
                           {"allow_token": self.allow_token(page), "back": "review"})
        self.assertIn("Pantry helper may now send 200 more suggestions today: 400 in all for today. "
                      "Tomorrow its limit is back to 200.", page)
        self.assertNotIn('name="allow_token"', page)  # 240 left: no longer near

    def test_the_same_button_twice_allows_more_once_and_a_new_press_again(self):
        self.fill(200)
        token = self.allow_token(self.page())
        self.follow(f"/settings/helpers/{self.helper.id}/allow-more", {"allow_token": token, "back": "review"})
        again = self.follow(f"/settings/helpers/{self.helper.id}/allow-more", {"allow_token": token, "back": "review"})
        self.assertIn("That button was already pressed, so nothing more was allowed this time.", again)
        self.assertEqual(proposals.limit_today(self.conn, self.helper), 400)
        self.fill(200)
        self.follow(f"/settings/helpers/{self.helper.id}/allow-more",
                    {"allow_token": self.allow_token(self.page()), "back": "review"})
        self.assertEqual(proposals.limit_today(self.conn, self.helper), 600)

    def test_allow_more_needs_the_pages_token_and_a_button_token_for_that_helper(self):
        self.fill(200)
        other, _key = helpers.issue(self.conn, self.data, "Other helper", "suggest", ["stock"])
        token = self.allow_token(self.page())
        self.assertEqual(self.post(f"/settings/helpers/{self.helper.id}/allow-more", {"allow_token": token},
                                   token=False).status_code, 400)
        page = self.follow(f"/settings/helpers/{other.id}/allow-more", {"allow_token": token})  # bound to the first
        self.assertIn("This page was out of date, so nothing more was allowed.", page)
        page = self.follow(f"/settings/helpers/{self.helper.id}/allow-more", {"allow_token": "made-up"})
        self.assertIn("This page was out of date", page)
        self.assertEqual(proposals.limit_today(self.conn, self.helper), 200)
        self.assertEqual(proposals.limit_today(self.conn, other), 200)

    def test_settings_helpers_shows_today_and_offers_allow_more_beside_the_helper(self):
        self.fill(30)
        page = self.page("/settings/helpers")
        self.assertIn("Today: 30 of 200 suggestions used.</p>", page)
        self.assertIn("Today: 30 of 200 suggestions used.", page)
        self.assertNotIn("Allow 200 more today", page)
        self.fill(140)
        self.assertIn("Today: 170 of 200 suggestions used. It is near today's limit.", self.page("/settings/helpers"))
        self.fill(30)
        page = self.page("/settings/helpers")
        self.assertIn("Today: 200 of 200 suggestions used. It has used all of today's.", page)
        page = self.follow(f"/settings/helpers/{self.helper.id}/allow-more", {"allow_token": self.allow_token(page)})
        self.assertIn("Pantry helper may now send 200 more suggestions today: 400 in all for today.", page)
        self.assertIn("Today: 200 of 400 suggestions used.", page)

    def test_the_review_queue_cap_is_unchanged(self):
        proposals.allow_more(self.conn, self.helper.id)
        self.assertEqual(proposals.MAX_WAITING, 500)
        with self.assertRaises(ProposalError) as caught:
            proposals.submit(self.conn, self.registry, self.helper,
                             {"request_key": "q", "why": WHY, "entries": [self.bought(self.beans)]}, queue_limit=0)
        self.assertEqual(caught.exception.code, "review_queue_full")
