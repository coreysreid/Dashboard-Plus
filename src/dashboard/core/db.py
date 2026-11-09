"""Open the SQLite database with settings that are safe on USB drives."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dashboard.errors import PlainError

BUSY_TIMEOUT_MS = 5000


class DatabaseError(PlainError):
    """The database could not be opened or used safely."""


def connect(path: Path) -> sqlite3.Connection:
    """Open the database file with the removable-drive settings from decision 0009.

    - journal_mode=DELETE: no extra side files that WAL mode keeps open.
    - synchronous=FULL: every change is on disk before we say it is saved.
    - foreign_keys=ON: links between records cannot point at nothing.
    The connection uses explicit transactions (see `transaction`).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        conn = sqlite3.connect(path, isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000)
    except sqlite3.Error as error:
        raise DatabaseError(f"The data file could not be opened ({path.name}). Is the drive still plugged in?") from error
    conn.row_factory = sqlite3.Row
    try:
        mode = conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        if str(mode).lower() != "delete":
            raise DatabaseError("The data file could not be set up safely for this drive.")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    except Exception:
        conn.close()
        raise
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block of changes all together or not at all."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def split_statements(sql: str) -> list[str]:
    """Split SQL text into complete statements (triggers with inner ';' stay whole)."""
    statements: list[str] = []
    buffer = ""
    for part in sql.split(";"):
        buffer += part + ";"
        if sqlite3.complete_statement(buffer):
            text = buffer.strip()
            if text.strip(";").strip() and not _only_comments(text):
                statements.append(text)
            buffer = ""
    if buffer.strip(";").strip() and not _only_comments(buffer):
        raise DatabaseError("A migration ends with an incomplete statement.")
    return statements


def _only_comments(text: str) -> bool:
    lines = [line.strip() for line in text.strip().rstrip(";").splitlines()]
    return all(not line or line.startswith("--") for line in lines)


def integrity_ok(conn: sqlite3.Connection) -> bool:
    """True if SQLite's own consistency check finds no damage."""
    return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def backup_to(conn: sqlite3.Connection, destination: Path) -> Path:
    """Copy the whole database safely, even while it is open, and check the copy."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    target = sqlite3.connect(destination)
    try:
        conn.backup(target)
        if not integrity_ok(target):
            raise DatabaseError("A backup copy failed its check and was not kept.")
    finally:
        target.close()
    return destination
