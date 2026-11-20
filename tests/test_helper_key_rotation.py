"""Tests for Make a new key (decision 0093): one press, one new key shown once, the old key stopped, the helper kept."""
import json
import re
import shutil
import sqlite3
from unittest import mock

from test_mcp_connector import SECRET, LiveDashboard
from dashboard.connector import config, mcp_server
from dashboard.core import db, helpers, proposals, records
from dashboard.core.proposals import ProposalError

INIT = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
SUGGESTION = {"request_key": "pantry-1", "why": "Seen on the shelf", "entries": [
    {"table": "demo__places", "values": {"name": "Pantry"}}]}


class RotationTests(LiveDashboard):
    """The core of a key change, checked against a real local Dashboard (Lane B's checks 1, 3 to 7, 9 and 10)."""

    def setUp(self):
        super().setUp()
        self.registry = records.build_registry(self.report.loaded)
        proposals.submit(self.conn, self.registry, self.helper, SUGGESTION)  # one suggestion waiting on Review

    def keys_file(self):
        return json.loads((self.data / "secrets" / "helper_keys.json").read_text(encoding="utf-8"))

    def verify(self, key):
        return helpers.verify(self.conn, self.data, f"Bearer {key}")

    def me(self, key):
        server = mcp_server.Server(config.load(environ={config.URL_VARIABLE: self.url, config.KEY_VARIABLE: key}))
        server.handle_line(json.dumps(INIT))
        reply = json.loads(server.handle_line(json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "dashboard_me"}})))["result"]
        return reply

    def test_the_helper_keeps_everything_but_its_key(self):
        before = helpers.get(self.conn, self.helper.id)
        changed, new = helpers.rotate(self.conn, self.data, self.helper.id)
        self.assertNotEqual(new, self.key)
        self.assertTrue(new.startswith("dph_") and len(new) == len(self.key))
        for field in ("id", "key_id", "slug", "name", "access", "modules", "created_at"):
            self.assertEqual(getattr(changed, field), getattr(before, field), field)
        self.assertIsNotNone(changed.rotated_at)
        self.assertIsNone(changed.key_pending_at)
        self.assertEqual(changed.key_generation, before.key_generation + 1)
        self.assertIsNone(self.verify(self.key))
        self.assertEqual(self.verify(new).id, self.helper.id)
        mine = [k for k, v in self.keys_file().items() if v == self.helper.key_id]
        self.assertEqual(mine, [helpers.fingerprint(new)])
        self.assertIn(helpers.fingerprint(self.reader_key), self.keys_file())  # another helper is untouched
        self.assertEqual([b["id"] for b in proposals.helper_batches(self.conn, self.verify(new), None, 10)],
                         [r["id"] for r in self.conn.execute("SELECT id FROM core__helper_batches")])
        self.assertEqual(proposals.waiting_for(self.conn, self.verify(new)), 1)
        audit = self.conn.execute("SELECT actor, before, after FROM core__audit WHERE action = 'helper_rotate'").fetchall()
        self.assertEqual([tuple(r) for r in audit], [("person", None, None)])

    def test_the_old_key_fails_the_check_and_the_api_and_the_new_one_sees_the_same_grant(self):
        old_me = self.me(self.key)
        self.assertFalse(old_me["isError"])
        _changed, new = helpers.rotate(self.conn, self.data, self.helper.id)
        refused = self.me(self.key)
        self.assertTrue(refused["isError"])
        self.assertEqual(refused["structuredContent"]["data"]["error"], "not_dashboard")
        now = self.me(new)
        self.assertFalse(now["isError"])
        self.assertEqual(now["structuredContent"]["data"]["modules"], old_me["structuredContent"]["data"]["modules"])
        self.assertEqual(now["structuredContent"]["data"]["access"], "suggest")
        self.assertEqual(now["structuredContent"]["data"]["limits"]["suggestions_waiting"], 1)

    def test_the_new_key_is_kept_nowhere(self):
        _changed, new = helpers.rotate(self.conn, self.data, self.helper.id)
        self.conn.close()
        for path in self.data.rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                self.assertNotIn(new.encode(), raw, path.name)
                self.assertNotIn(self.key.encode(), raw, path.name)
        self.conn = db.connect(self.data / "dashboard.db")

    def test_a_key_file_that_cannot_be_written_pauses_the_helper_and_shows_no_key(self):
        with mock.patch.object(helpers, "_write_keys", side_effect=OSError("read-only")):
            with self.assertRaises(helpers.KeyNotChanged) as caught:
                helpers.rotate(self.conn, self.data, self.helper.id)
        self.assertEqual(str(caught.exception), "The key could not be changed. This helper's access is paused so "
                                                "the old key cannot be used. Check the data folder, then make a "
                                                "new key from Helpers.")
        self.assertIsNone(self.verify(self.key))  # the old key is stopped by the pause
        self.assertTrue(helpers.get(self.conn, self.helper.id).key_unfinished)
        self.assertIn(helpers.fingerprint(self.key), self.keys_file())  # still in the file, but not usable
        self.assertEqual(helpers.stop_unfinished_key_changes(self.conn, self.data), [self.helper.id])
        self.assertNotIn(helpers.fingerprint(self.key), self.keys_file())  # at start-up: removed, never revived
        _changed, new = helpers.rotate(self.conn, self.data, self.helper.id)  # once writable, a fresh one works
        self.assertEqual(self.verify(new).id, self.helper.id)
        self.assertEqual(helpers.stop_unfinished_key_changes(self.conn, self.data), [])

    def test_a_stop_after_the_file_swap_leaves_no_working_key(self):
        with mock.patch.object(helpers, "_finish_rotation", side_effect=sqlite3.OperationalError("disk")):
            with self.assertRaises(helpers.KeyNotChanged):
                helpers.rotate(self.conn, self.data, self.helper.id)
        mine = [k for k, v in self.keys_file().items() if v == self.helper.key_id]
        self.assertEqual(len(mine), 1)
        self.assertNotIn(helpers.fingerprint(self.key), mine)  # the file was swapped: the old key is gone
        self.assertIsNone(self.verify(self.key))
        helpers.stop_unfinished_key_changes(self.conn, self.data)
        self.assertEqual([v for v in self.keys_file().values() if v == self.helper.key_id], [])
        self.assertIsNotNone(helpers.verify(self.conn, self.data, f"Bearer {self.reader_key}"))

    def test_during_the_change_neither_key_can_suggest(self):
        def suggest_during(*_args, **_kwargs):
            stale = helpers.Helper(**{**helpers.get(self.conn, self.helper.id).__dict__, "key_pending_at": None})
            for helper in (self.helper, stale):
                with self.assertRaises(ProposalError) as caught:
                    proposals.submit(self.conn, self.registry, helper, {**SUGGESTION, "request_key": "during"})
                self.assertEqual((caught.exception.status, caught.exception.code), (401, "no_key"))
            self.assertIsNone(self.verify(self.key))
            raise OSError("stop here")
        with mock.patch.object(helpers, "_swap_fingerprint", side_effect=suggest_during):
            with self.assertRaises(helpers.KeyNotChanged):
                helpers.rotate(self.conn, self.data, self.helper.id)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__helper_batches").fetchone()[0], 1)

    def test_a_suggestion_checked_with_the_old_key_is_refused_at_the_write(self):
        checked = self.verify(self.key)  # authenticated before the change
        _changed, new = helpers.rotate(self.conn, self.data, self.helper.id)
        with self.assertRaises(ProposalError) as caught:
            proposals.submit(self.conn, self.registry, checked, {**SUGGESTION, "request_key": "late"})
        self.assertEqual((caught.exception.status, caught.exception.code), (401, "no_key"))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__helper_batches").fetchone()[0], 1)
        result, created = proposals.submit(self.conn, self.registry, self.verify(new),
                                           {**SUGGESTION, "request_key": "late"})
        self.assertTrue(created)

    def test_a_request_key_from_before_the_change_still_returns_its_batch(self):
        _changed, new = helpers.rotate(self.conn, self.data, self.helper.id)
        again, created = proposals.submit(self.conn, self.registry, self.verify(new), SUGGESTION)
        self.assertFalse(created)
        with self.assertRaises(ProposalError) as caught:
            proposals.submit(self.conn, self.registry, self.verify(new),
                             {**SUGGESTION, "entries": [{"table": "demo__places", "values": {"name": "Attic"}}]})
        self.assertEqual(caught.exception.code, "request_key_reused")

    def test_restoring_older_copies_never_revives_the_old_key(self):
        before_helper = self.tmp / "before-helper.db"
        db.backup_to(self.conn, before_helper)
        extra, extra_key = helpers.issue(self.conn, self.data, "Late helper", "read", ["demo"])
        before_change = self.tmp / "before-change.db"
        db.backup_to(self.conn, before_change)
        _changed, new = helpers.rotate(self.conn, self.data, extra.id)
        for copy, new_works in ((before_change, True), (before_helper, False)):
            with self.subTest(copy=copy.name):
                self.conn.close()
                shutil.copy(copy, self.data / "dashboard.db")
                self.conn = db.connect(self.data / "dashboard.db")
                self.assertIsNone(self.verify(extra_key))
                self.assertEqual(self.verify(new) is not None, new_works)
        self.assertNotIn(helpers.fingerprint(extra_key), self.keys_file())

    def test_a_helper_that_is_off_gets_no_new_key_and_others_are_untouched(self):
        helpers.turn_off(self.conn, self.data, self.reader.id)
        with self.assertRaises(helpers.HelperOff) as caught:
            helpers.rotate(self.conn, self.data, self.reader.id)
        self.assertEqual(str(caught.exception), "This helper's access is off. No key was made.")
        self.assertNotIn(self.reader.key_id, self.keys_file().values())
        self.assertEqual(self.verify(self.key).id, self.helper.id)


class NewKeyPageTests(LiveDashboard):
    """The Make a new key button on Settings, Helpers (Lane B's checks 2, 3, 8 and 11)."""

    def setUp(self):
        super().setUp()
        self.page = self.app.test_client()
        self.base = f"http://127.0.0.1:{self.port}"
        self.page.get("/?key=session-key", base_url=self.base)

    def helpers_page(self, query=""):
        return self.page.get("/settings/helpers" + query, base_url=self.base).get_data(as_text=True)

    def token_for(self, helper_id, html=None):
        html = html or self.helpers_page()
        found = re.search(rf'action="/settings/helpers/{helper_id}/new-key".*?name="new_key_token" value="([^"]+)"',
                          html, re.S)
        return found.group(1)

    def press(self, helper_id, token):
        return self.page.post(f"/settings/helpers/{helper_id}/new-key", base_url=self.base,
                              data={"_csrf": self.app.config["CSRF_TOKEN"], "new_key_token": token})

    def test_the_card_explains_the_button(self):
        html = self.helpers_page()
        self.assertIn("Make a new key", html)
        self.assertIn("Use this if the key was lost or may have been seen. Your helper keeps the same name, access "
                      "and Review history. Its old key stops when the new one is made. You will need to replace "
                      "the key in your assistant app.", html)

    def test_one_press_shows_the_new_key_once_and_a_resend_makes_nothing(self):
        token = self.token_for(self.helper.id)
        response = self.press(self.helper.id, token)
        self.assertEqual(response.status_code, 201)
        html = response.get_data(as_text=True)
        self.assertIn("New key for Shelf helper", html)
        self.assertIn("Copy it now. This key will not be shown again. The old key no longer works.", html)
        self.assertIn("replace only <code>DASHBOARD_PLUS_KEY</code> with this key", html)
        self.assertIn("Suggestions already waiting on Review are still there.", html)
        self.assertEqual(len(re.findall(r"dph_[A-Za-z0-9_-]{8,}", html)), 1)
        new = re.search(r"dph_[A-Za-z0-9_-]{8,}", html).group(0)
        block = re.search(r'<pre id="assistant-settings"[^>]*>(.*?)</pre>', html, re.S).group(1)
        self.assertNotIn(new, block)
        self.assertIn("YOUR-KEY-HERE", block)
        self.assertIn("Copy key", html)
        self.assertIn("Copy connection settings", html)
        self.assertIn(f'href="/settings/helpers?changed={self.helper.id}"', html)
        self.assertEqual(helpers.verify(self.conn, self.data, f"Bearer {new}").id, self.helper.id)
        for _ in range(2):  # a resend, a refresh, a double click
            again = self.press(self.helper.id, token)
            self.assertEqual(again.status_code, 409)
            text = again.get_data(as_text=True)
            self.assertIn("A new key was already made from this button. It cannot be shown again. Return to Helpers "
                          "to make another new key if you did not copy it.", text)
            self.assertNotRegex(text, r"dph_[A-Za-z0-9_-]{8,}")
        self.assertEqual(helpers.verify(self.conn, self.data, f"Bearer {new}").id, self.helper.id)  # still the one
        back = self.helpers_page(f"?changed={self.helper.id}")
        stamp = helpers.get(self.conn, self.helper.id)
        self.assertIn(f"Shelf helper's key was changed on {self._when(stamp.rotated_at)}. Its access and history "
                      "are unchanged.", back)
        self.assertIn(f"Made {self._when(stamp.created_at)} · Key changed {self._when(stamp.rotated_at)}", back)
        self.assertNotIn(new, back)

    @staticmethod
    def _when(text):
        from datetime import datetime
        return datetime.fromisoformat(text).strftime("%d %b %Y").lstrip("0")

    def test_an_out_of_date_or_borrowed_button_changes_nothing(self):
        html = self.helpers_page()
        other = self.token_for(self.reader.id, html)
        for token in ("", "made-up", other):
            with self.subTest(token=token):
                response = self.press(self.helper.id, token)
                self.assertEqual(response.status_code, 409)
                self.assertIn("This page is out of date, so no key was changed. Open Helpers and try again.",
                              response.get_data(as_text=True))
        self.assertEqual(helpers.verify(self.conn, self.data, f"Bearer {self.key}").id, self.helper.id)

    def test_a_helper_turned_off_since_the_page_was_opened_gets_no_key(self):
        token = self.token_for(self.reader.id)
        helpers.turn_off(self.conn, self.data, self.reader.id)
        response = self.press(self.reader.id, token)
        self.assertEqual(response.status_code, 409)
        text = response.get_data(as_text=True)
        self.assertIn("This helper&#39;s access is off. No key was made.", text)
        self.assertNotRegex(text, r"dph_[A-Za-z0-9_-]{8,}")
        self.assertNotIn(f'action="/settings/helpers/{self.reader.id}/new-key"', self.helpers_page())

    def test_a_storage_failure_says_so_and_shows_no_key(self):
        token = self.token_for(self.helper.id)
        with mock.patch.object(helpers, "_write_keys", side_effect=OSError("read-only")):
            response = self.press(self.helper.id, token)
        self.assertEqual(response.status_code, 500)
        text = response.get_data(as_text=True)
        self.assertIn("The key could not be changed. This helper&#39;s access is paused", text)
        self.assertNotRegex(text, r"dph_[A-Za-z0-9_-]{8,}")
        self.assertIn("Key change did not finish. Make a new key to reconnect.", self.helpers_page())
        response = self.press(self.helper.id, self.token_for(self.helper.id))
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("Key change did not finish", self.helpers_page())

    def test_the_page_never_holds_a_secret(self):
        html = self.helpers_page()
        self.assertNotIn(SECRET, html)
        self.assertNotRegex(html, r"dph_[A-Za-z0-9_-]{8,}")
