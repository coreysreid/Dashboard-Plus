"""Read and write household settings kept in the database (core__settings)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from dashboard.core import db


def get(conn: sqlite3.Connection, key: str, default=None):
    """Return a setting's value, or `default` if it has never been set."""
    row = conn.execute("SELECT value FROM core__settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def put(conn: sqlite3.Connection, key: str, value) -> None:
    """Save a setting (any value that can be written as JSON)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.transaction(conn):
        conn.execute(
            "INSERT INTO core__settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, json.dumps(value), now))
