"""Tests for turning declared tables into SQL and generating the next migration."""
import sqlite3

from support import DEMO_TABLES, TempDirTestCase
from dashboard.core import modules, schema
import make_migration


class SchemaTests(TempDirTestCase):
    def test_first_migration_creates_tables_indexes_and_join_tables(self):
        module = modules.load_module(self.make_module())
        sql = schema.next_migration_sql(module)
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(sql)
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables, {"demo__owners", "demo__things", "demo__things__helpers"})
            columns = [r[1] for r in conn.execute("PRAGMA table_info(demo__things)")]
            for expected in ("id", "review_status", "deleted_at", "name", "kind", "owner", "quantity", "bought"):
                self.assertIn(expected, columns)
            self.assertNotIn("helpers", columns)
            indexes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
            self.assertIn("demo__things__owner__idx", indexes)
            self.assertIn("demo__things__bought__idx", indexes)
            foreign = conn.execute("PRAGMA foreign_key_list(demo__things)").fetchall()
            self.assertEqual(foreign[0][2], "demo__owners")
        finally:
            conn.close()

    def test_tool_writes_numbered_files_and_stops_when_up_to_date(self):
        folder = self.make_module()
        first = make_migration.make(folder, "first_tables")
        self.assertEqual(first.name, "0001_first_tables.sql")
        self.assertIsNone(make_migration.make(folder, "again"))
        self.write("modules/demo/tables.toml", DEMO_TABLES + 'columns.notes = { type = "longtext" }\n')
        second = make_migration.make(folder, "add_notes")
        self.assertEqual(second.name, "0002_add_notes.sql")
        self.assertIn("ALTER TABLE demo__things ADD COLUMN notes TEXT;", second.read_text(encoding="utf-8"))

    def test_removing_a_column_needs_a_hand_written_migration(self):
        folder = self.make_module()
        make_migration.make(folder, "first_tables")
        self.write("modules/demo/tables.toml", DEMO_TABLES.replace('columns.bought = { type = "date" }\n', ""))
        with self.assertRaises(schema.SchemaChangeError) as caught:
            schema.next_migration_sql(modules.load_module(folder))
        self.assertIn("demo__things.bought", str(caught.exception))

    def test_link_to_another_module_points_at_its_table(self):
        column = modules.Column(name="pet", type="link", to="pets.pets", on_delete="cascade")
        self.assertEqual(schema.column_sql("vet", column),
                         "pet INTEGER REFERENCES pets__pets(id) ON DELETE CASCADE")
