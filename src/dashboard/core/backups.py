"""Automatic backups: one a day, one at every safe close, kept in two places."""
from __future__ import annotations

import json
import logging
import os
import secrets
import sys
from datetime import date, datetime
from pathlib import Path

from dashboard.core import db

log = logging.getLogger("dashboard.backups")
KEEP = {"daily": 14, "close": 10, "before-update": 5}
STATUS_FILE = "status.json"  # in the data folder's backups folder: how the last backup went


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
    """Copy the database into every backup folder; a failing second copy is logged, not fatal.

    The household can switch the second copy off in Settings (`backups.second_copy`).
    """
    from dashboard.core import settings

    written = []
    second: dict = {"state": "off"}
    conn = db.connect(Path(data_dir) / "dashboard.db")
    try:
        if not settings.get(conn, "backups.second_copy", True):
            extra_dir = None
        elif extra_dir is not None:
            # Each data folder keeps its second copies in its own sub-folder, so two copies of the
            # program on one computer never overwrite each other's backups.
            folder_id = settings.get(conn, "backups.folder_id")
            if not folder_id:
                folder_id = secrets.token_hex(6)
                settings.put(conn, "backups.folder_id", folder_id)
            extra_dir = Path(extra_dir) / folder_id
        for i, folder in enumerate(backup_dirs(data_dir, extra_dir)):
            try:
                written.append(db.backup_to(conn, folder / filename))
                if i == 1:
                    second = {"state": "ok", "folder": str(folder)}
            except Exception as error:  # noqa: BLE001 - the main copy must not depend on the second
                if i == 0:
                    raise
                log.warning("The second backup copy could not be written to %s", folder)
                second = {"state": "failed", "folder": str(folder), "reason": _reason(error)}
    finally:
        conn.close()
    _record(data_dir, filename, second)
    for folder in backup_dirs(data_dir, extra_dir):
        prune(folder)
    return written


def _reason(error: Exception) -> str:
    """A short, plain reason a copy failed, for the Settings page."""
    if isinstance(error, PermissionError):
        return "the folder could not be written to (no permission)"
    if isinstance(error, OSError) and getattr(error, "errno", None) == 28:
        return "the disk is full"
    if isinstance(error, OSError):
        return "the folder could not be written to"
    return "an unexpected problem"


def _record(data_dir: Path, filename: str, second: dict) -> None:
    """Remember how this backup went, so the household can see a failed second copy."""
    now = datetime.now().isoformat(timespec="seconds")
    previous = status(data_dir).get("second", {})
    second = dict(second, at=now)
    if second["state"] == "ok":
        second["last_ok"] = now
    elif previous.get("last_ok"):
        second["last_ok"] = previous["last_ok"]
    path = Path(data_dir) / "backups" / STATUS_FILE
    try:
        path.write_text(json.dumps({"main": {"file": filename, "at": now}, "second": second}, indent=1),
                        encoding="utf-8")
    except OSError:
        log.warning("Could not record how the backup went")


def status(data_dir: Path) -> dict:
    """How the last backup went: {"main": {...}, "second": {"state": "ok" | "failed" | "off", ...}}."""
    try:
        return json.loads((Path(data_dir) / "backups" / STATUS_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def daily(data_dir: Path, extra_dir: Path | None = None, today: date | None = None) -> list[Path]:
    """Make today's backup if there is not one yet. Returns the files written (empty if done already)."""
    name = f"daily-{(today or date.today()).isoformat()}.db"
    done = (Path(data_dir) / "backups" / name).exists()
    if done and status(data_dir).get("second", {}).get("state") != "failed":
        return []  # already made today (a failed second copy is tried again)
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
