"""Tests for preparing the database at start-up with the modules found."""
import sqlite3

from support import DEMO_TABLES, TempDirTestCase
from dashboard.core import migrations, startup
import make_migration


class StartupTests(TempDirTestCase):
    def query(self, sql):
        conn = sqlite3.connect(self.tmp / "data" / "dashboard.db")
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_fresh_start_with_no_modules(self):
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertTrue(report.database.exists())
        self.assertEqual(report.version, len(migrations.load_track("core", migrations.CORE_FOLDER)))
        self.assertEqual(report.modules, [])

    def test_module_tables_are_created_and_recorded(self):
        make_migration.make(self.make_module(), "first_tables")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.modules, ["demo"])
        self.assertIn("demo 0001 (first_tables)", report.applied)
        self.assertEqual(self.query("SELECT name, version, enabled FROM core__modules"), [("demo", "1.0.0", 1)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM demo__things"), [(0,)])

    def test_update_backs_up_first_and_keeps_data(self):
        folder = self.make_module()
        make_migration.make(folder, "first_tables")
        startup.prepare(self.tmp / "data", self.tmp / "modules")
        conn = sqlite3.connect(self.tmp / "data" / "dashboard.db")
        conn.execute("INSERT INTO demo__owners (created_at, updated_at, name) VALUES ('t', 't', 'Synthetic Owner')")
        conn.commit()
        conn.close()
        self.write("modules/demo/tables.toml", DEMO_TABLES + 'columns.notes = { type = "longtext" }\n')
        make_migration.make(folder, "add_notes")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.applied, ["demo 0002 (add_notes)"])
        self.assertEqual(len(list((self.tmp / "data" / "backups").glob("before-update-*.db"))), 1)
        self.assertEqual(self.query("SELECT name FROM demo__owners"), [("Synthetic Owner",)])

    def test_broken_module_is_left_out_and_reported(self):
        self.make_module("broken", tables="[tables.a\n")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.modules, [])
        self.assertIn("broken", report.module_problems)
