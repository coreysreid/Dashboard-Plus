"""Prepare the database at start-up: load modules, back up if needed, and migrate."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dashboard.core import db, migrations, modules

log = logging.getLogger("dashboard.startup")
DATABASE_FILE = "dashboard.db"
DEFAULT_MODULES_DIR = Path(__file__).resolve().parents[3] / "modules"


@dataclass
class StartupReport:
    """What happened at start-up, for the home page and the log."""
    database: Path
    version: int
    applied: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    module_problems: dict[str, list[str]] = field(default_factory=dict)


def database_path(data_dir: Path) -> Path:
    return Path(data_dir) / DATABASE_FILE


def prepare(data_dir: Path, modules_dir: Path | None = None) -> StartupReport:
    """Open the database, bring it up to date, and record the modules in use.

    A module with mistakes is left out and reported; it never stops the others.
    Problems that make the database unsafe raise a PlainError instead.
    """
    data_dir = Path(data_dir)
    found, failures = modules.discover(Path(modules_dir) if modules_dir else DEFAULT_MODULES_DIR)
    tracks = {migrations.CORE_TRACK: migrations.load_track(migrations.CORE_TRACK, migrations.CORE_FOLDER)}
    for module in found:
        tracks[module.name] = module.migrations
    path = database_path(data_dir)
    conn = db.connect(path)
    try:
        applied = migrations.migrate(conn, tracks, backup_dir=data_dir / "backups")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db.transaction(conn):
            for module in found:
                conn.execute(
                    "INSERT INTO core__modules (name, version, enabled, first_seen_at, updated_at) "
                    "VALUES (?, ?, 1, ?, ?) ON CONFLICT(name) DO UPDATE SET version = excluded.version, "
                    "updated_at = excluded.updated_at",
                    (module.name, module.version, now, now),
                )
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    for name, problems in failures.items():
        log.warning("Module %s was left out: %s", name, " ".join(problems))
    for item in applied:
        log.info("Applied database change %s", item.label)
    return StartupReport(database=path, version=version, applied=[m.label for m in applied],
                         modules=[m.name for m in found], module_problems=failures)
