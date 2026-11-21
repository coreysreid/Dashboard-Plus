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


def enabled_modules(conn: sqlite3.Connection) -> set[str]:
    """Names of the modules switched on (all modules start switched on)."""
    return {r["name"] for r in conn.execute("SELECT name FROM core__modules WHERE enabled = 1")}


# A household's usual choice that a module's choice column may take as its default (decision 0111): the unit an
# odometer shows. Until Settings says, it follows the country: miles in the United States and the United Kingdom.
HOUSEHOLD_CHOICES = {"distance_unit": {"km": "Kilometres (km)", "mi": "Miles (mi)"}}
MILES_COUNTRIES = {"United States", "United Kingdom"}


def household_choice(conn: sqlite3.Connection, name: str) -> str:
    """The household's chosen value for one of HOUSEHOLD_CHOICES, or the country's usual one."""
    chosen = get(conn, f"household.{name}")
    if chosen in HOUSEHOLD_CHOICES[name]:
        return chosen
    return "mi" if get(conn, "household.country") in MILES_COUNTRIES else "km"


def set_module_enabled(conn: sqlite3.Connection, name: str, enabled: bool) -> None:
    """Switch a module on or off. Switching off hides it; its records are kept."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.transaction(conn):
        conn.execute("UPDATE core__modules SET enabled = ?, updated_at = ? WHERE name = ?",
                     (1 if enabled else 0, now, name))
