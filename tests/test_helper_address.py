"""Tests for the steady helper address (decision 0092): Dashboard's address file, and the connector reading it each call."""
import contextlib
import io
import json
import os
import re
import stat
import threading
import time

from waitress import create_server

from support import TempDirTestCase
from test_mcp_connector import INIT, start_fake
from dashboard import server
from dashboard.connector import client, config, mcp_server
from dashboard.core import db, helper_address, helpers, settings, startup
from dashboard.web.app import create_app
from dashboard.web.helper_settings import assistant_settings


def connector_for(address_file, key, url=None):
    """One connector session started the way the Settings block starts it: with the address file."""
    environ = {config.ADDRESS_FILE_VARIABLE: str(address_file), config.KEY_VARIABLE: key}
    if url:
        environ[config.URL_VARIABLE] = url
    connector = mcp_server.Server(config.load(environ=environ))
    connector.handle_line(json.dumps(INIT))
    return connector


def me(connector):
    """Call dashboard_me; return (is an error, the text, the error code if any)."""
    line = connector.handle_line(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                             "params": {"name": "dashboard_me", "arguments": {}}}))
    result = json.loads(line)["result"]
    data = result.get("structuredContent", {}).get("data", {})
    return result["isError"], result["content"][0]["text"], data.get("error")


class AddressFileTests(TempDirTestCase):
    """What Dashboard writes, and how the connector reads it, without any network."""

    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        self.file = helper_address.path(self.data)

    def test_the_file_holds_only_the_address_and_a_run_id(self):
        run_id = helper_address.write(self.data, 5123)
        found = json.loads(self.file.read_text(encoding="utf-8"))
        self.assertEqual(found, {"version": 1, "url": "http://127.0.0.1:5123/api/v1", "run_id": run_id})
        self.assertEqual(self.file, self.data / "run" / "helper-address.json")
        self.assertEqual(helper_address.read(self.file), ("http://127.0.0.1:5123/api/v1", None, None))
        self.assertEqual([p.name for p in self.file.parent.iterdir()], ["helper-address.json"])  # no partial left
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)

    def test_a_new_start_replaces_the_file_and_an_old_run_cannot_remove_it(self):
        old = helper_address.write(self.data, 5123)
        new = helper_address.write(self.data, 6001)
        self.assertNotEqual(old, new)
        self.assertFalse(helper_address.remove(self.data, old))
        self.assertEqual(helper_address.read(self.file)[0], "http://127.0.0.1:6001/api/v1")
        self.assertTrue(helper_address.remove(self.data, new))
        self.assertFalse(self.file.exists())
        self.assertFalse(helper_address.remove(self.data, new))  # already gone: nothing to do, no error

    def test_a_missing_file_says_where_to_look_and_that_the_key_was_not_sent(self):
        for where in (self.file, self.tmp / "moved" / "data" / "run" / "helper-address.json"):
            base, code, words = helper_address.read(where)
            self.assertEqual((base, code), (None, "address_file_missing"))
            self.assertEqual(words, "I cannot find Dashboard Plus's current address file. Open Dashboard Plus on "
                                    "this computer. If you moved its folder or USB drive, copy the connection "
                                    "settings again from Settings → Helpers. The key was not sent.")

    def test_a_wrong_file_is_refused_without_quoting_it(self):
        good = {"version": 1, "url": "http://127.0.0.1:5123/api/v1", "run_id": "a" * 32}
        cases = {
            "not json": b"{not json SECRET-LOOKING",
            "too large": json.dumps({**good, "pad": "x" * 5000}).encode(),
            "a list": b"[1, 2]",
            "another computer": json.dumps({**good, "url": "http://192.168.1.20:5123/api/v1"}).encode(),
            "a name, not the number": json.dumps({**good, "url": "http://localhost:5123/api/v1"}).encode(),
            "a query": json.dumps({**good, "url": "http://127.0.0.1:5123/api/v1?x=1"}).encode(),
            "another path": json.dumps({**good, "url": "http://127.0.0.1:5123/api/v2"}).encode(),
            "https": json.dumps({**good, "url": "https://127.0.0.1:5123/api/v1"}).encode(),
            "no port": json.dumps({**good, "url": "http://127.0.0.1/api/v1"}).encode(),
            "port too high": json.dumps({**good, "url": "http://127.0.0.1:70000/api/v1"}).encode(),
            "leading zero": json.dumps({**good, "url": "http://127.0.0.1:05123/api/v1"}).encode(),
            "a user": json.dumps({**good, "url": "http://u:p" + "@127.0.0.1:5123/api/v1"}).encode(),
            "extra value": json.dumps({**good, "key": "dph_" + "x" * 40}).encode(),
            "other version": json.dumps({**good, "version": 2}).encode(),
            "bad run id": json.dumps({**good, "run_id": "not-hex"}).encode(),
        }
        self.file.parent.mkdir(parents=True)
        for name, raw in cases.items():
            with self.subTest(name):
                self.file.write_bytes(raw)
                base, code, words = helper_address.read(self.file)
                self.assertEqual((base, code), (None, "address_file_wrong"))
                self.assertEqual(words, "Dashboard Plus's address file does not look right. Open Dashboard Plus "
                                        "and copy the connection settings again from Settings → Helpers. "
                                        "The key was not sent.")
                self.assertNotIn("SECRET", words)
        self.assertEqual(helper_address.read(self.file.with_name("other.json"))[1], "address_file_wrong")

    def test_a_link_to_another_file_is_refused(self):
        if os.name != "posix":
            self.skipTest("symbolic links need special rights on Windows")
        elsewhere = self.tmp / "planted" / "helper-address.json"
        elsewhere.parent.mkdir()
        elsewhere.write_text(json.dumps({"version": 1, "url": "http://127.0.0.1:5123/api/v1", "run_id": "b" * 32}))
        self.file.parent.mkdir(parents=True)
        self.file.symlink_to(elsewhere)
        self.assertEqual(helper_address.read(self.file)[1], "address_file_wrong")

    def test_a_folder_that_cannot_be_written_raises_and_leaves_nothing(self):
        if os.name != "posix" or os.geteuid() == 0:
            self.skipTest("needs a folder this account cannot write")
        run = self.data / "run"
        run.mkdir(parents=True)
        run.chmod(0o500)
        self.addCleanup(run.chmod, 0o700)
        with self.assertRaises(OSError):
            helper_address.write(self.data, 5123)
        self.assertEqual(list(run.iterdir()), [])

    def test_the_address_file_wins_over_a_stale_url_and_a_url_alone_still_works(self):
        key = "dph_" + "c" * 40
        both = config.load(environ={config.ADDRESS_FILE_VARIABLE: str(self.file), config.KEY_VARIABLE: key,
                                    config.URL_VARIABLE: "http://127.0.0.1:9/api/v1"})
        self.assertEqual((both.base, both.address_file, both.problem), (None, str(self.file), None))
        manual = config.load(environ={config.URL_VARIABLE: "http://127.0.0.1:5123", config.KEY_VARIABLE: key})
        self.assertEqual((manual.base, manual.address_file), ("http://127.0.0.1:5123/api/v1", None))
        settings_file = self.write("connector.toml", f'address_file = "{self.file.as_posix()}"\nkey = "{key}"\n')
        from_file = config.load(str(settings_file), environ={})
        self.assertEqual(from_file.address_file, self.file.as_posix())
        self.assertNotIn(key, repr(from_file))

    def test_a_missing_file_is_reported_before_anything_is_contacted(self):
        answer = client.call_via_file(str(self.file), "dph_" + "d" * 40, "GET", "/me")
        self.assertEqual((answer.status, answer.body["error"]), (0, "address_file_missing"))


class SteadyAddressTests(TempDirTestCase):
    """Acceptance checks 1, 3, 6 and 7: the real program started twice from one data folder."""

    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        (self.tmp / "modules").mkdir()
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))  # the program's own start and close notes

    def start(self):
        ready = threading.Event()
        thread = threading.Thread(target=server.serve, args=(self.data, False, ready, self.tmp / "modules"),
                                  daemon=True)
        thread.start()
        self.assertTrue(ready.wait(15), "Dashboard did not start")
        self.addCleanup(lambda: thread.is_alive() and server.close_running(self.data))
        return thread

    def stop(self, thread):
        self.assertTrue(server.close_running(self.data))
        thread.join(15)
        self.assertFalse(thread.is_alive())

    def test_one_unchanged_setting_works_across_a_restart_in_one_connector_run(self):
        address_file = helper_address.path(self.data)
        stale = {"version": 1, "url": "http://127.0.0.1:9/api/v1", "run_id": "e" * 32}
        address_file.parent.mkdir(parents=True)
        address_file.write_text(json.dumps(stale))  # left behind by an earlier run that crashed
        first = self.start()
        written = json.loads(address_file.read_text())
        self.assertNotEqual(written["run_id"], stale["run_id"])
        self.assertEqual(written["url"], f"http://127.0.0.1:{server.read_state(self.data).port}/api/v1")
        self.assertFalse(helper_address.remove(self.data, stale["run_id"]))  # an old run ID removes nothing
        dashboard_json = (self.data / "run" / "dashboard.json").read_text()
        state = server.read_state(self.data)
        for secret in (state.token, state.session):
            self.assertIn(secret, dashboard_json)
            self.assertNotIn(secret, address_file.read_text())
        conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(conn.close)
        _helper, key = helpers.issue(conn, self.data, "Pantry helper", "read", ["stock"])
        connector = connector_for(address_file, key, url="http://127.0.0.1:9/api/v1")  # a stale URL is ignored
        self.assertEqual(me(connector)[0], False)
        self.stop(first)
        self.assertFalse(address_file.exists())  # removed on a safe close
        error, words, code = me(connector)
        self.assertTrue(error)
        self.assertEqual(code, "address_file_missing")
        self.assertIn("The key was not sent.", words)
        second = self.start()
        self.assertEqual(me(connector)[0], False)  # the same connector, the same settings: it works again
        self.stop(second)

    def test_a_stale_file_after_a_crash_never_sends_the_key_to_the_program_on_the_old_port(self):
        startup.prepare(self.data, self.tmp / "modules")
        conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(conn.close)
        _helper, key = helpers.issue(conn, self.data, "Pantry helper", "read", ["stock"])
        web, url = start_fake(self, lambda handler, body: (200, {"hello": "dashboard-plus-hello-v1", "ok": 1}, ()))
        helper_address.path(self.data).parent.mkdir(parents=True, exist_ok=True)
        helper_address.path(self.data).write_text(json.dumps({"version": 1, "url": url, "run_id": "f" * 32}))
        error, words, code = me(connector_for(helper_address.path(self.data), key))
        self.assertTrue(error)
        self.assertEqual(code, "not_dashboard")
        self.assertTrue(words.startswith("This address is not Dashboard Plus"))
        self.assertTrue(all(s.startswith(b"POST /api/v1/hello") for s in web.seen))
        self.assertNotIn(key.encode(), b"".join(web.seen))
        self.assertEqual(len(web.seen), 1)  # no scan, no second address tried

    def test_nothing_answering_at_the_file_s_address_is_said_plainly(self):
        web, url = start_fake(self, lambda handler, body: (200, {}, ()))
        port = web.server_address[1]
        web.shutdown()
        web.server_close()
        time.sleep(0.1)
        helper_address.path(self.data).parent.mkdir(parents=True)
        helper_address.path(self.data).write_text(json.dumps({"version": 1, "url": url, "run_id": "1" * 32}))
        error, words, code = me(connector_for(helper_address.path(self.data), "dph_" + "g" * 40))
        self.assertTrue(error, port)
        self.assertEqual(code, "not_reachable")
        self.assertEqual(words.split("\n")[0], "Dashboard Plus is not answering at the address in its connection "
                                               "file. Open it again and try once more. The key was not sent.")


class LiveAddressTests(TempDirTestCase):
    """Acceptance checks 2, 5, 6 and 9 against Dashboards served in this test, each with its own data folder."""

    def live(self, folder_name):
        data = self.tmp / folder_name
        modules_dir = self.tmp / "modules"
        modules_dir.mkdir(exist_ok=True)
        report = startup.prepare(data, modules_dir)
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        settings.put(conn, "setup.done", True)
        app = create_app("shutdown-token", lambda: None, report, data_dir=data, session_key="session-key")
        web = create_server(app, host="127.0.0.1", port=0, threads=2)
        port = int(web.effective_port)
        app.config["PORT"] = port
        thread = threading.Thread(target=web.run, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(web.close)
        app.config["HELPER_ADDRESS_RUN"] = helper_address.write(data, port)
        helper, key = helpers.issue(conn, data, "Pantry helper", "read", ["stock"])
        return {"data": data, "conn": conn, "app": app, "port": port, "key": key, "helper": helper,
                "file": helper_address.path(data)}

    def test_two_dashboards_each_find_their_own_and_crossed_files_fail_the_check(self):
        a, b = self.live("home one"), self.live("home two")
        self.assertFalse(me(connector_for(a["file"], a["key"]))[0])
        self.assertFalse(me(connector_for(b["file"], b["key"]))[0])
        for file, key in ((a["file"], b["key"]), (b["file"], a["key"])):
            error, _words, code = me(connector_for(file, key))
            self.assertEqual((error, code), (True, "not_dashboard"))

    def test_a_file_changed_between_calls_is_read_again_and_checked_again(self):
        a = self.live("data")
        connector = connector_for(a["file"], a["key"])
        self.assertFalse(me(connector)[0])
        good = a["file"].read_text()
        web, url = start_fake(self, lambda handler, body: (200, {"hello": "dashboard-plus-hello-v1"}, ()))
        a["file"].write_text(json.dumps({"version": 1, "url": url, "run_id": "2" * 32}))
        self.assertEqual(me(connector)[2], "not_dashboard")
        self.assertNotIn(a["key"].encode(), b"".join(web.seen))
        a["file"].write_text(good)
        self.assertFalse(me(connector)[0])

    def test_a_turned_off_key_stays_off_though_the_file_still_finds_dashboard(self):
        a = self.live("data")
        helpers.turn_off(a["conn"], a["data"], a["helper"].id)
        self.assertEqual(helper_address.read(a["file"])[0], f"http://127.0.0.1:{a['port']}/api/v1")
        error, words, code = me(connector_for(a["file"], a["key"]))
        self.assertEqual((error, code), (True, "not_dashboard"))
        self.assertIn("this helper's key may have been turned off", words)

    def test_settings_block_points_at_this_folder_s_file_even_with_spaces_in_the_path(self):
        a = self.live("my data folder")
        page = a["app"].test_client()
        base = f"http://127.0.0.1:{a['port']}"
        page.get("/?key=session-key", base_url=base)
        html = page.get("/settings/helpers", base_url=base).get_data(as_text=True)
        block = re.search(r'<pre id="assistant-settings"[^>]*>(.*?)</pre>', html, re.S).group(1)
        env = json.loads(block.replace("&#34;", '"'))["mcpServers"]["dashboard-plus"]["env"]
        self.assertEqual(env[config.ADDRESS_FILE_VARIABLE], str(a["file"].resolve()))
        self.assertNotIn(config.URL_VARIABLE, env)
        self.assertEqual(env[config.KEY_VARIABLE], "YOUR-KEY-HERE")
        self.assertIn("an ordinary restart needs no new copy", html)
        self.assertIn("with the key you copied when you made this helper", html)
        self.assertIn(f"Current local address: <code>http://127.0.0.1:{a['port']}/api/v1</code>", html)
        self.assertIn("Use current address instead", html)
        self.assertNotIn("could not write its address file", html)
        a["app"].config["HELPER_ADDRESS_RUN"] = None  # as if the run folder could not be written
        html = page.get("/settings/helpers", base_url=base).get_data(as_text=True)
        self.assertIn("could not write its address file", html)
        self.assertNotIn("dph_", html)

    def test_the_manual_block_still_uses_the_copied_address(self):
        manual = json.loads(assistant_settings("http://127.0.0.1:5123/api/v1"))["mcpServers"]["dashboard-plus"]
        self.assertEqual(manual["env"][config.URL_VARIABLE], "http://127.0.0.1:5123/api/v1")
        located = json.loads(assistant_settings(address_file="/x/run/helper-address.json"))
        self.assertNotIn(config.URL_VARIABLE, located["mcpServers"]["dashboard-plus"]["env"])
