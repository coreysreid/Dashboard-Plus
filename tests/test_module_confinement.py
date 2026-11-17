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
