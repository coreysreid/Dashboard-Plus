"""Tests for restoring a backup: checks that change nothing, the safe swap, Undo after a restart, and refusals."""
import hashlib
import shutil
import sqlite3
from datetime import date
from unittest import mock

from support import TempDirTestCase
from dashboard.core import backups, db, helpers, records, restore, settings, startup
from dashboard.web.app import create_app
import load_example
import make_migration

PORT = 5124
BASE = f"http://127.0.0.1:{PORT}"
VISITOR = {"name": "Restore test visitor", "lives_here": False}


def fingerprint(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RestoreTestCase(TempDirTestCase):
    """The made-up Smith household, with one daily backup taken before a visitor was added."""

    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        load_example.load("smith", self.data, today=date(2026, 6, 1))
        self.report = startup.prepare(self.data)
        self.loaded = self.report.loaded
        backups.daily(self.data, today=date(2026, 6, 1))
        self.backup = self.data / "backups" / "daily-2026-06-01.db"
        self.people_then = self.people()
        self.add_visitor()

    def connect(self):
        conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(conn.close)
        return conn

    def people(self) -> int:
        conn = db.connect(self.data / "dashboard.db")
        try:
            return conn.execute("SELECT COUNT(*) FROM people__people WHERE deleted_at IS NULL").fetchone()[0]
        finally:
            conn.close()

    def add_visitor(self):
        conn = db.connect(self.data / "dashboard.db")
        try:
            records.Records(conn, records.build_registry(self.loaded)).create("people__people", VISITOR)
        finally:
            conn.close()

    def copy(self, name="daily-2026-06-01.db"):
        return restore.get({"data": self.data / "backups"}, "data", name)

    def staging_files(self):
        return sorted(p.name for p in self.data.glob("restore-staging-*"))

    def tampered(self, name: str, sql: str):
        """A copy of the backup with one change made to it, saved as another backup."""
        target = self.data / "backups" / name
        shutil.copyfile(self.backup, target)
        conn = sqlite3.connect(target)
        try:
            conn.execute(sql)
            conn.commit()
        finally:
            conn.close()
        return self.copy(name)


class RestoreTests(RestoreTestCase):
    def test_round_trip_puts_the_backup_back_and_keeps_the_records_before(self):
        self.assertEqual(self.people(), self.people_then + 1)
        result = restore.restore(self.data, self.copy(), self.loaded)
        self.assertEqual(self.people(), self.people_then)
        self.assertTrue(result["undo_saved"])
        before = self.data / "backups" / result["before_restore"]
        conn = restore.open_read_only(before)
        try:
            names = [r[0] for r in conn.execute("SELECT name FROM people__people")]
        finally:
            conn.close()
        self.assertIn(VISITOR["name"], names)
        self.assertEqual(restore.journal(self.data)["before_restore"], before.name)
        self.assertEqual(self.staging_files(), [])

    def test_undo_puts_back_the_records_from_before_the_restore(self):
        restore.restore(self.data, self.copy(), self.loaded)
        restore.undo(self.data, self.loaded)
        self.assertEqual(self.people(), self.people_then + 1)
        self.assertIsNone(restore.journal(self.data))
        self.assertTrue(list((self.data / "backups").glob("before-undo-*.db")))
        with self.assertRaises(restore.RestoreError) as caught:
            restore.undo(self.data, self.loaded)
        self.assertIn("Nothing was changed", str(caught.exception))

    def test_the_backup_file_itself_is_never_changed(self):
        before = fingerprint(self.backup)
        restore.check(self.copy(), restore.known_tracks(self.loaded), full=True)
        restore.copy_counts(self.copy(), ["people__people"])
        restore.restore(self.data, self.copy(), self.loaded)
        self.assertEqual(fingerprint(self.backup), before)
        self.assertFalse((self.data / "backups" / "daily-2026-06-01.db-journal").exists())

    def test_a_damaged_backup_is_refused_and_nothing_changes(self):
        broken = self.data / "backups" / "daily-2026-06-02.db"
        raw = bytearray(self.backup.read_bytes())
        raw[4096:8192] = b"\xff" * 4096  # scribble over the second page
        broken.write_bytes(bytes(raw))
        cut = self.data / "backups" / "daily-2026-06-03.db"
        cut.write_bytes(self.backup.read_bytes()[:6000])
        current = fingerprint(self.data / "dashboard.db")
        for name in (broken.name, cut.name):
            copy = restore.check(self.copy(name), restore.known_tracks(self.loaded), full=True)
            self.assertEqual(copy.state, "damaged")
            with self.assertRaises(restore.RestoreError) as caught:
                restore.restore(self.data, self.copy(name), self.loaded)
            self.assertIn("Nothing was changed", str(caught.exception))
        self.assertEqual(fingerprint(self.data / "dashboard.db"), current)
        self.assertIsNone(restore.journal(self.data))
        self.assertFalse(list((self.data / "backups").glob("before-restore-*.db")))

    def test_a_backup_from_a_newer_version_is_refused(self):
        copy = self.tampered("daily-2026-06-04.db", "INSERT INTO core__migrations VALUES "
                                                    "('core', 999, 'later', 'x', '2027-01-01')")
        self.assertEqual(restore.check(copy, restore.known_tracks(self.loaded)).state, "newer")
        with self.assertRaises(restore.RestoreError) as caught:
            restore.restore(self.data, copy, self.loaded)
        self.assertIn("newer version", str(caught.exception))
        self.assertEqual(self.people(), self.people_then + 1)

    def test_a_backup_with_a_part_this_program_lacks_is_refused(self):
        copy = self.tampered("daily-2026-06-05.db", "INSERT INTO core__migrations VALUES "
                                                    "('stargazing', 1, 'first', 'x', '2027-01-01')")
        self.assertEqual(restore.check(copy, restore.known_tracks(self.loaded)).state, "unknown")
        with self.assertRaises(restore.RestoreError):
            restore.restore(self.data, copy, self.loaded)

    def test_a_file_that_is_not_a_backup_is_refused(self):
        (self.data / "backups" / "daily-2026-06-06.db").write_bytes(b"not a database at all, " * 50)
        self.assertEqual(restore.check(self.copy("daily-2026-06-06.db"), {}).state, "not-ours")

    def test_failed_staging_leaves_no_trace(self):
        current = fingerprint(self.data / "dashboard.db")
        with mock.patch.object(restore.startup, "record_modules", side_effect=sqlite3.OperationalError("disk I/O")), \
                self.assertLogs("dashboard.restore"):
            with self.assertRaises(restore.RestoreError) as caught:
                restore.restore(self.data, self.copy(), self.loaded)
        self.assertIn("Nothing was changed", str(caught.exception))
        self.assertEqual(fingerprint(self.data / "dashboard.db"), current)
        self.assertEqual(self.staging_files(), [])
        self.assertIsNone(restore.journal(self.data))
        self.assertFalse(list((self.data / "backups").glob("before-restore-*.db")))

    def test_a_failed_swap_leaves_the_records_in_use(self):
        current = fingerprint(self.data / "dashboard.db")
        with mock.patch.object(restore.os, "replace", side_effect=PermissionError("in use")), \
                self.assertLogs("dashboard.restore"):
            with self.assertRaises(restore.RestoreError) as caught:
                restore.restore(self.data, self.copy(), self.loaded)
        self.assertIn("Nothing was changed", str(caught.exception))
        self.assertEqual(fingerprint(self.data / "dashboard.db"), current)
        self.assertEqual(self.staging_files(), [])
        self.assertIsNone(restore.journal(self.data))

    def test_a_backup_changed_after_it_was_looked_at_is_refused(self):
        with self.assertRaises(restore.RestoreError) as caught:
            restore.restore(self.data, self.copy(), self.loaded, seen="0-0")
        self.assertIn("changed after you looked", str(caught.exception))
        self.assertEqual(self.people(), self.people_then + 1)

    def test_waits_for_open_pages_and_gives_up_safely(self):
        gate = db.gate(self.data / "dashboard.db")
        gate.enter()  # a page still holds the data file
        self.addCleanup(gate.leave)
        with mock.patch.object(restore, "WAIT_SECONDS", 0.2), self.assertLogs("dashboard.restore"):
            with self.assertRaises(restore.RestoreError) as caught:
                restore.restore(self.data, self.copy(), self.loaded)
        self.assertIn("still in use", str(caught.exception))
        self.assertIn("Nothing was changed", str(caught.exception))
        self.assertEqual(self.people(), self.people_then + 1)
        self.assertEqual(self.staging_files(), [])

    def test_helper_keys_are_untouched_and_a_turned_off_helper_stays_off(self):
        conn = self.connect()
        kept, _ = helpers.issue(conn, self.data, "Older helper", "read", ["people"])
        backups.daily(self.data, today=date(2026, 6, 7))
        helpers.turn_off(conn, self.data, kept.id)
        helpers.issue(conn, self.data, "Newer helper", "read", ["people"])
        conn.close()
        keys = self.data / "secrets" / "helper_keys.json"
        before = fingerprint(keys)
        restore.restore(self.data, self.copy("daily-2026-06-07.db"), self.loaded)
        self.assertEqual(fingerprint(keys), before)
        conn = self.connect()
        found = {h.name: h for h in helpers.all_helpers(conn)}
        self.assertEqual(set(found), {"Older helper"})  # the newer one was made after the backup
        self.assertFalse(found["Older helper"].active)
        conn.close()
        restore.undo(self.data, self.loaded)
        self.assertEqual(fingerprint(keys), before)


class OlderBackupTests(TempDirTestCase):
    def test_an_older_backup_is_brought_up_to_date_on_a_copy(self):
        module = self.make_module()
        make_migration.make(module, "first_tables")
        data = self.tmp / "data"
        startup.prepare(data, self.tmp / "modules")
        backups.daily(data, today=date(2026, 6, 1))
        old = data / "backups" / "daily-2026-06-01.db"
        old_print = fingerprint(old)
        tables = (module / "tables.toml").read_text(encoding="utf-8")
        (module / "tables.toml").write_text(tables + 'columns.colour = { type = "text" }\n', encoding="utf-8")
        make_migration.make(module, "add_colour")
        report = startup.prepare(data, self.tmp / "modules")
        copy = restore.get({"data": data / "backups"}, "data", old.name)
        checked = restore.check(copy, restore.known_tracks(report.loaded), full=True)
        self.assertEqual((checked.state, checked.pending), ("update", 1))
        restore.restore(data, copy, report.loaded)
        self.assertEqual(fingerprint(old), old_print)
        conn = db.connect(data / "dashboard.db")
        try:
            columns = {r[1] for r in conn.execute("PRAGMA table_info(demo__things)")}
            steps = conn.execute("SELECT COUNT(*) FROM core__migrations WHERE track = 'demo'").fetchone()[0]
        finally:
            conn.close()
        self.assertIn("colour", columns)
        self.assertEqual(steps, 2)


class RestorePageTests(RestoreTestCase):
    def setUp(self):
        super().setUp()
        self.extra = self.tmp / "computer-copy"
        conn = db.connect(self.data / "dashboard.db")
        try:
            settings.put(conn, "backups.second_copy", True)  # the examples switch it off
            backups.second_folder(conn, self.extra)  # gives this data folder its second-copy folder name
        finally:
            conn.close()
        self.app = self.make_app()
        self.client = self.app.test_client()
        self.client.get("/?key=session-key", base_url=BASE)

    def make_app(self):
        report = startup.prepare(self.data)
        app = create_app("shutdown-token", lambda: None, report, data_dir=self.data, session_key="session-key",
                         extra_backup_dir=self.extra)
        app.config["PORT"] = PORT
        return app

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def post(self, path, data=None, client=None, app=None):
        app = app or self.app
        return (client or self.client).post(path, data=dict(data or {}, _csrf=app.config["CSRF_TOKEN"]),
                                            base_url=BASE)

    def test_list_preview_restore_and_undo_after_a_restart(self):
        backups.daily(self.data, self.extra, today=date(2026, 6, 8))
        settings_page = self.get("/settings").get_data(as_text=True)
        self.assertIn('href="/settings/backups"', settings_page)
        page = self.get("/settings/backups").get_data(as_text=True)
        self.assertIn("Data folder", page)
        self.assertIn("This computer", page)
        self.assertIn("Helper keys are not part of a backup", page)
        preview = self.get("/settings/backups/data/daily-2026-06-01.db")
        text = preview.get_data(as_text=True)
        self.assertEqual(preview.status_code, 200)
        self.assertIn("Check passed", text)
        self.assertIn(f"<td>{self.people_then}</td>", text)
        self.assertIn(f"{self.people_then + 1} <span class=\"muted\">(different)</span>", text)
        seen = restore.get({"data": self.data / "backups"}, "data", "daily-2026-06-01.db").stamp
        done = self.post("/settings/backups/data/daily-2026-06-01.db/restore", {"seen": seen})
        self.assertEqual(done.status_code, 302)
        self.assertIn("Backup restored", self.get(done.headers["Location"]).get_data(as_text=True))
        self.assertEqual(self.people(), self.people_then)

        # Close and reopen: a new program object still offers Undo.
        app = self.make_app()
        client = app.test_client()
        client.get("/?key=session-key", base_url=BASE)
        self.assertIn("Undo restore", client.get("/settings/backups", base_url=BASE).get_data(as_text=True))
        undone = self.post("/settings/backups/undo", client=client, app=app)
        self.assertEqual(undone.status_code, 200)
        self.assertIn("Restore undone", undone.get_data(as_text=True))
        self.assertEqual(self.people(), self.people_then + 1)
        self.assertNotIn("Undo restore", client.get("/settings/backups", base_url=BASE).get_data(as_text=True))

    def test_restore_needs_the_page_token(self):
        current = fingerprint(self.data / "dashboard.db")
        seen = self.copy().stamp
        response = self.client.post("/settings/backups/data/daily-2026-06-01.db/restore", data={"seen": seen},
                                    base_url=BASE)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(fingerprint(self.data / "dashboard.db"), current)
        self.assertIsNone(restore.journal(self.data))

    def test_a_refused_restore_says_nothing_was_changed(self):
        response = self.post("/settings/backups/data/daily-2026-06-01.db/restore", {"seen": "stale"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("Nothing was changed.", response.get_data(as_text=True))
        self.assertEqual(self.people(), self.people_then + 1)

    def test_a_damaged_copy_offers_no_restore_button(self):
        (self.data / "backups" / "daily-2026-06-09.db").write_bytes(self.backup.read_bytes()[:5000])
        text = self.get("/settings/backups/data/daily-2026-06-09.db").get_data(as_text=True)
        self.assertIn("Cannot restore this copy", text)
        self.assertNotIn("Restore this backup", text)

    def test_only_backups_by_their_exact_name_can_be_opened(self):
        for path in ("/settings/backups/data/dashboard.db", "/settings/backups/data/..%2Fdashboard.db",
                     "/settings/backups/elsewhere/daily-2026-06-01.db", "/settings/backups/data/daily-2026-01-01.db"):
            self.assertEqual(self.get(path).status_code, 404, path)

    def test_keep_the_restored_records(self):
        restore.restore(self.data, self.copy(), self.loaded)
        response = self.post("/settings/backups/keep")
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(restore.journal(self.data))
        self.assertEqual(self.people(), self.people_then)
