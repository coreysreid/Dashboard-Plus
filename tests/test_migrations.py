"""Tests for numbered migrations: tracks, checksums, newer databases, rollback and backups."""
from support import TempDirTestCase
from dashboard.core import db, migrations as m


class MigrationTests(TempDirTestCase):
    def connect(self):
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        return conn

    def track(self, folder, files):
        for name, sql in files.items():
            self.write(f"{folder}/{name}", sql)
        return m.load_track(folder, self.tmp / folder)

    def test_core_track_is_valid_and_applies(self):
        conn = self.connect()
        core = m.load_track(m.CORE_TRACK, m.CORE_FOLDER)
        done = m.migrate(conn, {m.CORE_TRACK: core})
        self.assertEqual(len(done), len(core))
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], len(core))
        self.assertEqual(m.migrate(conn, {m.CORE_TRACK: core}), [])  # nothing left to do

    def test_badly_named_file_is_refused(self):
        with self.assertRaises(m.MigrationError):
            self.track("bad", {"1_first.sql": "SELECT 1;"})

    def test_gap_in_numbers_is_refused(self):
        with self.assertRaises(m.MigrationError) as caught:
            self.track("gap", {"0001_a.sql": "SELECT 1;", "0003_c.sql": "SELECT 1;"})
        self.assertIn("0002", str(caught.exception))

    def test_tracks_are_independent(self):
        conn = self.connect()
        core = m.load_track(m.CORE_TRACK, m.CORE_FOLDER)
        one = self.track("one", {"0001_a.sql": "CREATE TABLE one__a (id INTEGER PRIMARY KEY);"})
        two = self.track("two", {"0001_a.sql": "CREATE TABLE two__a (id INTEGER PRIMARY KEY);"})
        m.migrate(conn, {m.CORE_TRACK: core, "one": one})
        done = m.migrate(conn, {m.CORE_TRACK: core, "one": one, "two": two})
        self.assertEqual([x.label for x in done], ["two 0001 (a)"])

    def test_edited_migration_is_refused(self):
        conn = self.connect()
        one = self.track("one", {"0001_a.sql": "CREATE TABLE one__a (id INTEGER PRIMARY KEY);"})
        m.migrate(conn, {"one": one})
        edited = [m.Migration("one", 1, "a", "CREATE TABLE one__a (id INTEGER PRIMARY KEY, x TEXT);")]
        with self.assertRaises(m.MigrationError) as caught:
            m.migrate(conn, {"one": edited})
        self.assertIn("edited", str(caught.exception))

    def test_newer_database_is_refused(self):
        conn = self.connect()
        one = self.track("one", {"0001_a.sql": "CREATE TABLE one__a (id INTEGER PRIMARY KEY);",
                                 "0002_b.sql": "CREATE TABLE one__b (id INTEGER PRIMARY KEY);"})
        m.migrate(conn, {"one": one})
        with self.assertRaises(m.MigrationError) as caught:
            m.migrate(conn, {"one": one[:1]})
        self.assertIn("newer version", str(caught.exception))

    def test_failed_migration_changes_nothing(self):
        conn = self.connect()
        one = self.track("one", {"0001_a.sql": "CREATE TABLE one__a (id INTEGER PRIMARY KEY);\nNOT VALID SQL;"})
        with self.assertRaises(m.MigrationError):
            m.migrate(conn, {"one": one})
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("one__a", tables)
        self.assertEqual(m.applied(conn), {})

    def test_backup_made_before_updating_existing_data(self):
        conn = self.connect()
        backups = self.tmp / "data" / "backups"
        one = self.track("one", {"0001_a.sql": "CREATE TABLE one__a (id INTEGER PRIMARY KEY);"})
        m.migrate(conn, {"one": one}, backup_dir=backups)
        self.assertFalse(backups.exists(), "a brand-new database needs no backup")
        more = self.track("one", {"0002_b.sql": "CREATE TABLE one__b (id INTEGER PRIMARY KEY);"})
        m.migrate(conn, {"one": more}, backup_dir=backups)
        self.assertEqual(len(list(backups.glob("before-update-*.db"))), 1)
