"""Tests for starting, protecting and safely closing the local web server."""
import http.client
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dashboard import server  # noqa: E402


def request(port, method="GET", path="/", host=None, headers=None, cookie=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    all_headers = dict(headers or {})
    if host:
        all_headers["Host"] = host
    if cookie:
        all_headers["Cookie"] = cookie
    conn.request(method, path, headers=all_headers)
    response = conn.getresponse()
    body = response.read().decode("utf-8", "replace")
    set_cookie = response.getheader("Set-Cookie")
    conn.close()
    return response.status, body if set_cookie is None else (body, set_cookie)


def sign_in(state):
    """Follow the launch link like a browser and return the session cookie."""
    status, (_, set_cookie) = request(state.port, path=f"/?key={state.session}")
    assert status == 302, status
    return set_cookie.split(";", 1)[0]


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        ready = threading.Event()
        self.thread = threading.Thread(target=server.serve, args=(self.data, False, ready), daemon=True)
        self.thread.start()
        self.assertTrue(ready.wait(10), "server did not start")
        self.state = server.read_state(self.data)

    def tearDown(self):
        if self.thread.is_alive():
            server.close_running(self.data)
            self.thread.join(10)
        self.tmp.cleanup()

    def test_home_page_needs_the_launch_link(self):
        status, _ = request(self.state.port)
        self.assertEqual(status, 302, "a browser without the launch link is sent to the explanation page")
        status, body = request(self.state.port, path="/?key=wrong")
        self.assertEqual(status, 302)
        cookie = sign_in(self.state)
        status, _ = request(self.state.port, cookie=cookie)
        self.assertEqual(status, 302, "a new household is taken to the first-run questions")
        status, body = request(self.state.port, path="/setup", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("Look after what your household has", body)
        self.assertTrue(server.is_responding(self.state))
        self.assertIn("?key=", self.state.launch_url)

    def test_listens_on_this_computer_only(self):
        self.assertEqual(server.HOST, "127.0.0.1")
        status, _ = request(self.state.port, host="evil.example")
        self.assertEqual(status, 403)

    def test_post_from_another_website_is_refused(self):
        status, _ = request(self.state.port, "POST", "/api/shutdown",
                            headers={"Origin": "http://evil.example", "X-Shutdown-Token": self.state.token})
        self.assertEqual(status, 403)
        self.assertTrue(self.thread.is_alive())

    def test_shutdown_needs_the_token(self):
        status, _ = request(self.state.port, "POST", "/api/shutdown", headers={"X-Shutdown-Token": "wrong"})
        self.assertEqual(status, 403)
        self.assertTrue(self.thread.is_alive())

    def test_safe_close_stops_and_cleans_up(self):
        self.assertTrue(server.close_running(self.data))
        self.thread.join(10)
        self.assertFalse(self.thread.is_alive())
        self.assertFalse(server.state_file(self.data).exists())

    def test_close_safely_move_the_folder_and_nothing_is_lost(self):
        # M1: close safely, unplug, plug in again (here: copy the folder elsewhere and start from the copy).
        import shutil
        from dashboard.core import db, modules, records, settings
        found, _ = modules.discover(Path(__file__).resolve().parents[1] / "modules")
        conn = db.connect(self.data / "dashboard.db")
        records.Records(conn, records.build_registry(found)).create("stock__places", {"name": "Under the stairs"})
        settings.put(conn, "setup.done", True)
        conn.close()
        self.assertTrue(server.close_running(self.data))
        self.thread.join(10)
        left_behind = [p.name for p in self.data.iterdir() if p.name.endswith(("-journal", "-wal", "-shm"))]
        self.assertEqual(left_behind, [])
        moved = Path(self.tmp.name) / "plugged-in-again"
        shutil.copytree(self.data, moved)
        ready = threading.Event()
        thread = threading.Thread(target=server.serve, args=(moved, False, ready), daemon=True)
        thread.start()
        self.assertTrue(ready.wait(10), "server did not start from the moved folder")
        try:
            state = server.read_state(moved)
            status, body = request(state.port, path="/t/stock__places", cookie=sign_in(state))
            self.assertEqual(status, 200)
            self.assertIn("Under the stairs", body)
        finally:
            server.close_running(moved)
            thread.join(10)

    def test_safe_close_releases_the_log_file(self):
        # An open file blocks unplugging (and deleting on Windows), so closing
        # must let go of the log file.
        import logging
        server.close_running(self.data)
        self.thread.join(10)
        log_path = (self.data / "logs" / "dashboard.log").resolve()
        still_open = [h for h in logging.getLogger().handlers
                      if isinstance(h, logging.FileHandler) and Path(h.baseFilename) == log_path]
        self.assertEqual(still_open, [])

    def test_start_prepares_the_database(self):
        self.assertTrue((self.data / "dashboard.db").exists())
        status, body = request(self.state.port, path="/setup", cookie=sign_in(self.state))
        self.assertIn("Welcome to Dashboard Plus", body)

    def test_unknown_page_is_friendly(self):
        status, body = request(self.state.port, path="/nope", cookie=sign_in(self.state))
        self.assertEqual(status, 404)
        self.assertIn("does not exist", body)
        self.assertNotIn("Traceback", body)

    def test_second_start_reuses_the_running_one(self):
        ready = threading.Event()
        start = time.monotonic()
        server.serve(self.data, False, ready)  # returns at once because one is running
        self.assertLess(time.monotonic() - start, 5)
        self.assertEqual(server.read_state(self.data).port, self.state.port)


if __name__ == "__main__":
    unittest.main()
