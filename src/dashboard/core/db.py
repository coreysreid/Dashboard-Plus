"""Open the SQLite database with settings that are safe on USB drives."""
from __future__ import annotations

import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dashboard.errors import PlainError

BUSY_TIMEOUT_MS = 5000


class DatabaseError(PlainError):
    """The database could not be opened or used safely."""


def keep_private(*paths: Path) -> None:
    """On Mac and Linux, let only this computer account read the household's files: folders 0700,
    files 0600. Another account on a shared computer could otherwise read medical details or the
    session key (security review, decision 0055). Windows keeps each user's files private already."""
    if os.name != "posix":
        return
    for path in paths:
        try:
            path = Path(path)
            if path.is_dir():
                path.chmod(0o700)
            elif path.exists():
                path.chmod(0o600)
        except OSError:
            pass  # a drive that doesn't keep permissions (such as a FAT USB stick) is left as it is


def connect(path: Path) -> sqlite3.Connection:
    """Open the database file with the removable-drive settings from decision 0009.

    - journal_mode=DELETE: no extra side files that WAL mode keeps open.
    - synchronous=FULL: every change is on disk before we say it is saved.
    - foreign_keys=ON: links between records cannot point at nothing.
    The connection uses explicit transactions (see `transaction`).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keep_private(path.parent)
    try:
        conn = sqlite3.connect(path, isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000)
    except sqlite3.Error as error:
        raise DatabaseError(f"The data file could not be opened ({path.name}). Is the drive still plugged in?") from error
    conn.row_factory = sqlite3.Row
    keep_private(path)
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


# The operation each open transaction belongs to, by connection: every record change made inside one
# transaction shares one operation ID in the change log (decision 0100). Removed when the transaction ends.
_operations: dict[int, str] = {}


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block of changes all together or not at all, as one operation."""
    conn.execute("BEGIN IMMEDIATE")
    with operation(conn):
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")


@contextmanager
def operation(conn: sqlite3.Connection) -> Iterator[str]:
    """Mark the transaction already begun on `conn` as one operation with a fresh random ID."""
    key = id(conn)
    _operations[key] = secrets.token_hex(16)
    try:
        yield _operations[key]
    finally:
        _operations.pop(key, None)


def current_operation(conn: sqlite3.Connection) -> str | None:
    """The ID of the operation the open transaction on `conn` belongs to, or None outside one."""
    return _operations.get(id(conn)) if conn.in_transaction else None


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
    """Copy the whole database safely, even while it is open, and check the copy.

    The copy is written under a temporary name and only renamed into place once it passes its
    check, so a failed or interrupted backup never leaves a file that looks like a good one."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    keep_private(destination.parent)
    partial = destination.with_name(destination.name + ".partial")
    target = sqlite3.connect(partial)
    keep_private(partial)
    try:
        conn.backup(target)
        ok = integrity_ok(target)
    except BaseException:
        target.close()
        partial.unlink(missing_ok=True)
        raise
    target.close()
    if not ok:
        partial.unlink(missing_ok=True)
        raise DatabaseError("A backup copy failed its check and was not kept.")
    os.replace(partial, destination)
    return destination


class Gate:
    """Lets any number of pages use one data file at once, or a restore hold it alone (decision 0079).

    Pages enter as "shared" and leave when they close their connection. `alone` stops new pages from
    entering, waits until every open connection is closed, and holds the file until the block ends."""

    def __init__(self):
        self._lock = threading.Condition()
        self._users = 0
        self._held = False

    def enter(self, timeout: float = 60.0) -> None:
        with self._lock:
            if not self._lock.wait_for(lambda: not self._held, timeout):
                raise DatabaseError("The dashboard is busy putting back a backup. Try again in a moment.")
            self._users += 1

    def leave(self) -> None:
        with self._lock:
            self._users = max(0, self._users - 1)
            self._lock.notify_all()

    @contextmanager
    def shared(self, timeout: float = 120.0) -> Iterator[None]:
        self.enter(timeout)
        try:
            yield
        finally:
            self.leave()

    @contextmanager
    def alone(self, timeout: float = 30.0) -> Iterator[None]:
        with self._lock:
            if not self._lock.wait_for(lambda: not self._held, timeout):
                raise DatabaseError("Another change to the whole data file is still running.")
            self._held = True
            if not self._lock.wait_for(lambda: self._users == 0, timeout):
                self._held = False
                self._lock.notify_all()
                raise DatabaseError("The data file is still in use by another page.")
        try:
            yield
        finally:
            with self._lock:
                self._held = False
                self._lock.notify_all()


_gates: dict[str, Gate] = {}
_gates_lock = threading.Lock()


def gate(path: Path) -> Gate:
    """The one gate for a data file in this program, found by its full path."""
    key = os.path.normcase(str(Path(path).resolve()))
    with _gates_lock:
        return _gates.setdefault(key, Gate())
