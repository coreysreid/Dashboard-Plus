"""Automatic backups: one a day, one at every safe close, kept in two places."""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dashboard.core import db

log = logging.getLogger("dashboard.backups")
KEEP = {"daily": 14, "close": 10, "before-update": 5}


def default_extra_dir() -> Path:
    """A second backup folder on the computer itself (decision 0006), outside the data folder."""
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "Dashboard Plus" / "backups"
    return Path.home() / ".local" / "share" / "dashboard-plus" / "backups"


def backup_dirs(data_dir: Path, extra_dir: Path | None) -> list[Path]:
    dirs = [Path(data_dir) / "backups"]
    if extra_dir is not None:
        dirs.append(Path(extra_dir))
    return dirs


def _write(data_dir: Path, extra_dir: Path | None, filename: str) -> list[Path]:
    """Copy the database into every backup folder; a failing second copy is logged, not fatal."""
    written = []
    conn = db.connect(Path(data_dir) / "dashboard.db")
    try:
        for i, folder in enumerate(backup_dirs(data_dir, extra_dir)):
            try:
                written.append(db.backup_to(conn, folder / filename))
            except Exception:  # noqa: BLE001 - the main copy must not depend on the second
                if i == 0:
                    raise
                log.warning("The second backup copy could not be written to %s", folder)
    finally:
        conn.close()
    for folder in backup_dirs(data_dir, extra_dir):
        prune(folder)
    return written


def daily(data_dir: Path, extra_dir: Path | None = None, today: date | None = None) -> list[Path]:
    """Make today's backup if there is not one yet. Returns the files written (empty if done already)."""
    name = f"daily-{(today or date.today()).isoformat()}.db"
    if (Path(data_dir) / "backups" / name).exists():
        return []
    return _write(data_dir, extra_dir, name)


def on_close(data_dir: Path, extra_dir: Path | None = None) -> list[Path]:
    """Back up as the program closes safely."""
    return _write(data_dir, extra_dir, f"close-{datetime.now():%Y%m%d-%H%M%S}.db")


def prune(folder: Path) -> None:
    """Keep the newest few of each kind of backup; never delete the newest one."""
    for kind, keep in KEEP.items():
        files = sorted(Path(folder).glob(f"{kind}-*.db"))
        for old in files[:-keep]:
            try:
                old.unlink()
            except OSError:
                log.warning("Could not remove old backup %s", old.name)


def latest(data_dir: Path) -> tuple[str, datetime] | None:
    """The newest backup in the data folder, as (file name, time written)."""
    files = list((Path(data_dir) / "backups").glob("*.db"))
    if not files:
        return None
    newest = max(files, key=lambda p: p.stat().st_mtime)
    return newest.name, datetime.fromtimestamp(newest.stat().st_mtime)
