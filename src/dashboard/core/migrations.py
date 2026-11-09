"""Apply numbered migrations, one track for the core and one per module."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dashboard.core import db
from dashboard.errors import PlainError

FILENAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
CORE_TRACK = "core"
CORE_FOLDER = Path(__file__).resolve().parent / "migrations"
BOOTSTRAP = """CREATE TABLE IF NOT EXISTS core__migrations (
    track TEXT NOT NULL,
    number INTEGER NOT NULL,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    PRIMARY KEY (track, number)
)"""


class MigrationError(PlainError):
    """The database cannot be brought up to date safely."""


@dataclass(frozen=True)
class Migration:
    """One numbered change to the database, belonging to one track."""
    track: str
    number: int
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.replace("\r\n", "\n").encode("utf-8")).hexdigest()

    @property
    def label(self) -> str:
        return f"{self.track} {self.number:04d} ({self.name})"


def load_track(track: str, folder: Path) -> list[Migration]:
    """Read a folder of NNNN_name.sql files; numbers must run 0001, 0002, ... with no gaps."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    found: dict[int, Migration] = {}
    for path in sorted(folder.iterdir()):
        if path.suffix != ".sql":
            continue
        match = FILENAME.match(path.name)
        if not match:
            raise MigrationError(
                f"The {track} migration file '{path.name}' is badly named. Use four digits, an underscore "
                "and a lower-case name, for example 0001_first_tables.sql."
            )
        number = int(match.group(1))
        if number in found:
            raise MigrationError(f"The {track} migrations have two files numbered {number:04d}.")
        sql = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        found[number] = Migration(track, number, match.group(2), sql)
    numbers = sorted(found)
    if numbers != list(range(1, len(numbers) + 1)):
        missing = sorted(set(range(1, (numbers[-1] if numbers else 0) + 1)) - set(numbers))
        raise MigrationError(f"The {track} migrations skip a number ({', '.join(f'{n:04d}' for n in missing)}).")
    return [found[n] for n in numbers]


def applied(conn: sqlite3.Connection) -> dict[str, dict[int, str]]:
    """Return {track: {number: checksum}} for everything already applied."""
    conn.execute(BOOTSTRAP)
    result: dict[str, dict[int, str]] = {}
    for row in conn.execute("SELECT track, number, checksum FROM core__migrations"):
        result.setdefault(row["track"], {})[row["number"]] = row["checksum"]
    return result


def plan(conn: sqlite3.Connection, tracks: dict[str, list[Migration]]) -> list[Migration]:
    """Return the migrations still to run, after checking nothing already run has changed."""
    done = applied(conn)
    todo: list[Migration] = []
    for track, migrations in tracks.items():
        known = {m.number: m for m in migrations}
        for number, checksum in sorted(done.get(track, {}).items()):
            if number not in known:
                raise MigrationError(
                    f"This data folder was last used by a newer version of Dashboard Plus "
                    f"(the '{track}' part is at step {max(done[track])}, this version only knows "
                    f"{len(migrations)}). Please open it with the newer version."
                )
            if known[number].checksum != checksum:
                raise MigrationError(
                    f"The database change {known[number].label} has been edited since it was applied. "
                    "Released changes must never be edited; add a new numbered change instead."
                )
        todo.extend(m for m in migrations if m.number not in done.get(track, {}))
    return todo


def migrate(conn: sqlite3.Connection, tracks: dict[str, list[Migration]],
            backup_dir: Path | None = None) -> list[Migration]:
    """Bring the database up to date. Core runs first, then tracks in the order given.

    If anything is pending and the database already holds data, a backup is made
    first. Each migration runs in its own transaction with its record, so a
    failure leaves the database exactly as it was before that migration.
    """
    ordered = {CORE_TRACK: tracks[CORE_TRACK]} if CORE_TRACK in tracks else {}
    ordered.update({k: v for k, v in tracks.items() if k != CORE_TRACK})
    todo = plan(conn, ordered)
    if not todo:
        return []
    if backup_dir is not None and any(applied(conn).values()):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        db.backup_to(conn, Path(backup_dir) / f"before-update-{stamp}.db")
    for migration in todo:
        try:
            with db.transaction(conn):
                for statement in db.split_statements(migration.sql):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO core__migrations (track, number, name, checksum, applied_at) VALUES (?, ?, ?, ?, ?)",
                    (migration.track, migration.number, migration.name, migration.checksum,
                     datetime.now(timezone.utc).isoformat(timespec="seconds")),
                )
                if migration.track == CORE_TRACK:
                    conn.execute(f"PRAGMA user_version = {int(migration.number)}")
        except sqlite3.Error as error:
            raise MigrationError(
                f"The database change {migration.label} could not be applied, so nothing was changed. "
                f"Details: {error}"
            ) from error
    return todo
