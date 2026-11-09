"""Tests for opening the database safely, transactions, statement splitting and backups."""
import sqlite3

from support import TempDirTestCase
from dashboard.core import db


class DatabaseTests(TempDirTestCase):
    def connect(self, name="test.db"):
        conn = db.connect(self.tmp / name)
        self.addCleanup(conn.close)
        return conn

    def test_usb_safe_settings(self):
        conn = self.connect()
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "delete")
        self.assertEqual(conn.execute("PRAGMA synchronous").fetchone()[0], 2)  # FULL
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_transaction_rolls_back_on_error(self):
        conn = self.connect()
        conn.execute("CREATE TABLE t (x INTEGER)")
        with self.assertRaises(RuntimeError):
            with db.transaction(conn):
                conn.execute("INSERT INTO t VALUES (1)")
                raise RuntimeError("synthetic")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM t").fetchone()[0], 0)
        with db.transaction(conn):
            conn.execute("INSERT INTO t VALUES (2)")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM t").fetchone()[0], 1)

    def test_split_keeps_triggers_whole_and_drops_comments(self):
        sql = """-- a comment
CREATE TABLE a (x INTEGER);
CREATE TRIGGER a_t AFTER INSERT ON a BEGIN UPDATE a SET x = 1; SELECT 1; END;
-- trailing comment
"""
        parts = db.split_statements(sql)
        self.assertEqual(len(parts), 2)
        self.assertIn("END;", parts[1])

    def test_incomplete_statement_is_refused(self):
        with self.assertRaises(db.DatabaseError):
            db.split_statements("CREATE TABLE a (x INTEGER); CREATE TRIGGER t AFTER INSERT ON a BEGIN SELECT 1;")

    def test_backup_copies_and_checks(self):
        conn = self.connect()
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (7)")
        path = db.backup_to(conn, self.tmp / "backups" / "copy.db")
        copy = sqlite3.connect(path)
        try:
            self.assertEqual(copy.execute("SELECT x FROM t").fetchone()[0], 7)
        finally:
            copy.close()
