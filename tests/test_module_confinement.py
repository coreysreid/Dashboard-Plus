"""A module's database changes may touch only its own tables (security review, decision 0055).

Each attack below was tried by the November 2026 security review against a files-only module;
every one must now leave the module out and the household's records untouched."""
from support import TempDirTestCase
from dashboard.core import db, settings, startup
import make_migration

TABLES = '''[tables.recipes]
title = "Recipes"
columns.name = { type = "text", required = true }
'''

ATTACKS = {
    "read another module's private details":
        "INSERT INTO evil__recipes (name, created_at, updated_at) SELECT value, '', '' FROM core__settings;",
    "plant a trigger that acts later": "CREATE TRIGGER evil__t AFTER INSERT ON core__settings "
                                       "BEGIN DELETE FROM core__settings; END;",
    "wipe the change history": "DELETE FROM core__audit;",
    "change a setting such as the backup folder": "UPDATE core__settings SET value = '\"x\"';",
    "commit part-way and copy the database elsewhere": "COMMIT; VACUUM INTO 'stolen.db'; BEGIN;",
    "attach another file": "ATTACH DATABASE 'other.db' AS other;",
    "change database settings": "PRAGMA writable_schema = 1;",
    "make a view over other tables": "CREATE VIEW evil__v AS SELECT * FROM core__settings;",
    "drop the core's tables": "DROP TABLE core__audit;",
}


class ModuleConfinementTests(TempDirTestCase):
    def start(self, extra_sql: str = ""):
        folder = self.make_module(name="evil", tables=TABLES, labels=None)
        make_migration.make(folder, "first_tables")
        sql = folder / "migrations" / "0001_first_tables.sql"
        sql.write_text(sql.read_text(encoding="utf-8") + "\n" + extra_sql + "\n", encoding="utf-8")
        data = self.tmp / "data"
        conn = db.connect(data / "dashboard.db") if (data / "dashboard.db").exists() else None
        if conn:
            conn.close()
        return startup.prepare(data, self.tmp / "modules")

    def test_a_module_creates_and_fills_its_own_tables(self):
        report = self.start("INSERT INTO evil__recipes (name, created_at, updated_at) VALUES ('Soup', '', '');")
        self.assertEqual(report.module_problems, {})

    def test_every_attack_is_refused_and_changes_nothing(self):
        for what, sql in ATTACKS.items():
            with self.subTest(what):
                for path in (self.tmp / "modules", self.tmp / "data"):
                    if path.exists():
                        import shutil
                        shutil.rmtree(path)
                startup.prepare(self.tmp / "data", self.tmp / "modules")  # the household's own data first
                conn = db.connect(self.tmp / "data" / "dashboard.db")
                settings.put(conn, "household.country", "Australia")
                history = conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
                conn.close()
                report = self.start(sql)
                self.assertIn("evil", report.module_problems, what)
                self.assertNotIn("evil", report.modules)
                conn = db.connect(self.tmp / "data" / "dashboard.db")
                self.assertEqual(settings.get(conn, "household.country"), "Australia")
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0], history)
                self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'evil%'").fetchone())
                conn.close()
                self.assertFalse((self.tmp / "data" / "stolen.db").exists() or (self.tmp / "stolen.db").exists())


class ReservedNameTests(TempDirTestCase):
    """A module may not borrow the program's own name or a name that could be mistaken for another's tables."""

    def prepare(self, name):
        self.make_module(name=name, tables=TABLES, labels=None)
        return startup.prepare(self.tmp / "data", self.tmp / "modules")

    def test_core_is_refused_with_a_plain_message(self):
        report = self.prepare("core")
        self.assertNotIn("core", report.modules)
        self.assertIn("'core' is reserved for the program itself", " ".join(report.module_problems["core"]))

    def test_double_underscore_and_trailing_underscore_names_are_refused(self):
        for name in ("a__b", "pets_", "pets___x"):
            with self.subTest(name):
                report = self.prepare(name)
                self.assertNotIn(name, report.modules)
                self.assertIn(name, report.module_problems)

    def test_a_core_module_with_its_own_migrations_cannot_run_them(self):
        from dashboard.core import migrations
        real = sorted(migrations.CORE_FOLDER.glob("*.sql"))
        startup.prepare(self.tmp / "data", self.tmp / "modules")
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        before = conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
        conn.close()
        folder = self.make_module(name="core", tables=TABLES, labels=None)
        (folder / "migrations").mkdir()
        for sql in real[:2]:
            (folder / "migrations" / sql.name).write_text(sql.read_text(encoding="utf-8"), encoding="utf-8")
        (folder / "migrations" / "0003_evil.sql").write_text(
            "DROP TABLE core__audit;\nCREATE TABLE core__evil (id INTEGER);\n", encoding="utf-8")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertNotIn("core", report.modules)
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0], before)
        self.assertIsNone(conn.execute("SELECT name FROM sqlite_master WHERE name = 'core__evil'").fetchone())
        conn.close()

    def test_second_net_skips_a_core_module_that_got_past_loading(self):
        from dataclasses import replace
        from unittest import mock
        from dashboard.core import modules
        self.make_module(name="demo", tables=TABLES, labels=None)
        real, _ = modules.discover(self.tmp / "modules")
        sneaky = replace(real[0], name="core")
        with mock.patch.object(modules, "discover", return_value=([sneaky], {})):
            report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.modules, [])
        self.assertIn("core", report.module_problems)
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0] > 0, True)
        conn.close()
