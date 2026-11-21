"""Restore from a backup: check copies without changing them, put one back safely, and undo it."""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dashboard.core import backups, db, helpers, migrations, startup, sync
from dashboard.errors import PlainError

log = logging.getLogger("dashboard.restore")
JOURNAL_FILE = "restore.json"  # in the data folder: the last restore, so Undo works after a restart
NAME = re.compile(r"^(daily|close|before-update|before-restore|before-undo)-[0-9][0-9-]*\.db$")
KINDS = {"daily": "Daily", "close": "When the dashboard was closed", "before-update": "Before an update",
         "before-restore": "Before a restore", "before-undo": "Before an undo"}
PLACES = {"data": "Data folder", "computer": "This computer"}
NOTHING_CHANGED = "Nothing was changed."
SQLITE_HEADER = b"SQLite format 3\x00"
WAIT_SECONDS = 30.0  # how long a restore waits for open pages to finish with the data file
_one_at_a_time = threading.Lock()


class RestoreError(PlainError):
    """A restore could not be done. The records in use were not changed."""


@dataclass
class Copy:
    """One backup file, and what checking it found."""
    place: str          # "data" or "computer"
    name: str
    path: Path
    size: int
    made: datetime
    stamp: str          # its size and change time: shows whether the file changed after it was looked at
    state: str = "unchecked"  # ready, update, damaged, newer, unknown, edited, not-ours
    reason: str = ""
    pending: int = 0    # database changes this program would make to a copy of it

    @property
    def kind(self) -> str:
        match = NAME.match(self.name)
        return KINDS[match.group(1)] if match else "Backup"

    @property
    def where(self) -> str:
        return PLACES[self.place]

    @property
    def usable(self) -> bool:
        return self.state in ("ready", "update")


# ----- finding copies ---------------------------------------------------------------------------------

def folders(data_dir: Path, extra_dir: Path | None, conn) -> dict[str, Path]:
    """Where this data folder's backups are: its own backups folder and, if there is one, its second copy
    folder on this computer. Nothing is created or written."""
    from dashboard.core import settings

    found = {"data": Path(data_dir) / "backups"}
    folder_id = settings.get(conn, "backups.folder_id") if extra_dir is not None else None
    if isinstance(folder_id, str) and backups.FOLDER_ID.fullmatch(folder_id):
        found["computer"] = Path(extra_dir) / folder_id
    return found


def _copy(place: str, path: Path) -> Copy:
    info = path.stat()
    return Copy(place, path.name, path, info.st_size, datetime.fromtimestamp(info.st_mtime),
                f"{info.st_size}-{info.st_mtime_ns}")


def find(places: dict[str, Path]) -> list[Copy]:
    """Every backup this program made in those folders, newest first. Only names it makes are listed."""
    copies = []
    for place, folder in places.items():
        try:
            paths = [p for p in Path(folder).iterdir() if NAME.match(p.name) and p.is_file()]
        except OSError:
            continue  # the folder is not there (yet), or cannot be read
        for path in paths:
            try:
                copies.append(_copy(place, path))
            except OSError:
                continue
    return sorted(copies, key=lambda c: (c.made, c.name), reverse=True)


def get(places: dict[str, Path], place: str, name: str) -> Copy | None:
    """One copy, named by its place and exact file name, or None. A name with a folder in it is never used."""
    if place not in places or not NAME.match(name or ""):
        return None
    path = places[place] / name
    try:
        return _copy(place, path) if path.is_file() else None
    except OSError:
        return None


# ----- checking a copy, read-only ---------------------------------------------------------------------

def known_tracks(loaded) -> dict[str, list[migrations.Migration]]:
    """The database changes this program knows: its own, then each module's in use."""
    tracks = {migrations.CORE_TRACK: migrations.load_track(migrations.CORE_TRACK, migrations.CORE_FOLDER)}
    for module in loaded:
        tracks[module.name] = module.migrations
    return tracks


def open_read_only(path: Path) -> sqlite3.Connection:
    """Open a database file so that nothing can be written to it, not even SQLite's own bookkeeping."""
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _applied(conn) -> dict[str, dict[int, str]]:
    """{track: {number: checksum}} as recorded in a copy, or {} if it has no such record."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'core__migrations'").fetchone():
        return {}
    found: dict[str, dict[int, str]] = {}
    for row in conn.execute("SELECT track, number, checksum FROM core__migrations"):
        found.setdefault(row["track"], {})[int(row["number"])] = row["checksum"]
    return found


def compatibility(done: dict[str, dict[int, str]], tracks: dict) -> tuple[str, str, int]:
    """Whether this program can use a copy with these database changes: (state, reason, changes to make)."""
    if not done.get(migrations.CORE_TRACK):
        return "not-ours", "This file is not a Dashboard Plus backup.", 0
    unknown = sorted(t for t in done if t not in tracks and done[t])
    if unknown:
        return ("unknown", f"This copy has records for a part this copy of Dashboard Plus does not have "
                f"({', '.join(unknown)}). Restoring it could lose them, so it cannot be used here.", 0)
    pending = 0
    for track, steps in tracks.items():
        known = {m.number: m.checksum for m in steps}
        for number, checksum in done.get(track, {}).items():
            if number not in known:
                return ("newer", "This copy was made by a newer version of Dashboard Plus. Update Dashboard "
                        "Plus first, then try again.", 0)
            if known[number] != checksum:
                return ("edited", "This copy was made with a changed version of Dashboard Plus, so it cannot "
                        "be brought up to date safely.", 0)
        pending += len([n for n in known if n not in done.get(track, {})])
    if pending:
        return "update", "Check passed. It was made by an older version and will be brought up to date.", pending
    return "ready", "Check passed.", 0


def check(copy: Copy, tracks: dict, full: bool = False) -> Copy:
    """Check a copy without changing it: is it whole, and can this program use it? `full` runs SQLite's
    complete integrity check; otherwise its quicker check is used (for the list)."""
    damaged = "This copy is damaged, so it cannot be used. Try another copy."
    try:
        with open(copy.path, "rb") as handle:
            header = handle.read(len(SQLITE_HEADER))
    except OSError:
        copy.state, copy.reason = "damaged", "This copy could not be read."
        return copy
    if header != SQLITE_HEADER:
        copy.state, copy.reason = ("damaged", damaged) if copy.size < 512 else ("not-ours", "This file is not a Dashboard Plus backup.")
        return copy
    try:
        conn = open_read_only(copy.path)
    except sqlite3.Error:
        copy.state, copy.reason = "damaged", damaged
        return copy
    try:
        result = conn.execute("PRAGMA integrity_check" if full else "PRAGMA quick_check").fetchall()
        if [tuple(r) for r in result] != [("ok",)]:
            copy.state, copy.reason = "damaged", damaged
            return copy
        copy.state, copy.reason, copy.pending = compatibility(_applied(conn), tracks)
    except sqlite3.Error:
        copy.state, copy.reason = "damaged", damaged
    finally:
        conn.close()
    return copy


def counts(conn, table_names) -> dict[str, int | None]:
    """How many records (not deleted) each table holds; None for a table this database does not have."""
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    found: dict[str, int | None] = {}
    for name in table_names:
        if name not in have:
            found[name] = None
            continue
        columns = {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}
        where = " WHERE deleted_at IS NULL" if "deleted_at" in columns else ""
        found[name] = conn.execute(f"SELECT COUNT(*) FROM {name}{where}").fetchone()[0]
    return found


def copy_counts(copy: Copy, table_names) -> dict[str, int | None]:
    """Record counts in a backup, read-only."""
    conn = open_read_only(copy.path)
    try:
        return counts(conn, table_names)
    finally:
        conn.close()


# ----- the restore journal ----------------------------------------------------------------------------

def journal(data_dir: Path) -> dict | None:
    """The last restore that can still be undone, or None. A journal naming a copy that is not there,
    or a name this program does not make, is ignored."""
    try:
        found = json.loads((Path(data_dir) / JOURNAL_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(found, dict):
        return None
    before = found.get("before_restore")
    if not isinstance(before, str) or not NAME.match(before) or not before.startswith("before-restore-"):
        return None
    if not (Path(data_dir) / "backups" / before).is_file():
        return None
    return found


def dismiss(data_dir: Path) -> None:
    """Keep the restored records: Undo is no longer offered."""
    (Path(data_dir) / JOURNAL_FILE).unlink(missing_ok=True)


def _write_journal(data_dir: Path, entry: dict) -> None:
    path = Path(data_dir) / JOURNAL_FILE
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(entry, indent=1), encoding="utf-8")
    db.keep_private(partial)
    os.replace(partial, path)
    db.keep_private(path)


# ----- putting a copy back ----------------------------------------------------------------------------

def restore(data_dir: Path, source: Copy, loaded, seen: str | None = None) -> dict:
    """Put a backup back in place of the records in use. Returns what happened, for the result page.

    First checks the copy in full; copies it into the data folder as a new file and brings that copy up
    to date; then, with no page using the data file, makes a checked "before restore" backup of the
    records in use and swaps the prepared copy into place in one step. The journal names the
    before-restore backup so the restore can be undone. On any failure before the swap the prepared copy
    is deleted, the records in use are as they were, and RestoreError says "Nothing was changed."
    `seen` is the copy's stamp when the household looked at it; a copy changed since then is refused."""
    entry = _put_back(data_dir, source, loaded, seen, "before-restore")
    entry["undo_saved"] = True
    try:
        _write_journal(data_dir, {k: v for k, v in entry.items() if k != "undo_saved"})
    except OSError:
        log.exception("The restore worked but its Undo note could not be saved")
        entry["undo_saved"] = False
    return entry


def undo(data_dir: Path, loaded) -> dict:
    """Undo the last restore: put back the before-restore copy it made (itself a restore, which first
    makes a "before undo" backup). Afterwards Undo is no longer offered."""
    found = journal(data_dir)
    if found is None:
        raise RestoreError(f"There is no restore to undo. {NOTHING_CHANGED}")
    source = get({"data": Path(data_dir) / "backups"}, "data", found["before_restore"])
    if source is None:
        raise RestoreError(f"The copy from before the restore could not be found. {NOTHING_CHANGED}")
    entry = _put_back(data_dir, source, loaded, None, "before-undo")
    dismiss(data_dir)
    return entry


def _put_back(data_dir: Path, source: Copy, loaded, seen: str | None, kind: str) -> dict:
    if not _one_at_a_time.acquire(blocking=False):
        raise RestoreError(f"Another restore is already running. {NOTHING_CHANGED}")
    try:
        return _put_back_alone(Path(data_dir), source, loaded, seen, kind)
    finally:
        _one_at_a_time.release()


def _put_back_alone(data_dir: Path, source: Copy, loaded, seen: str | None, kind: str) -> dict:
    current = startup.database_path(data_dir)
    tracks = known_tracks(loaded)
    try:
        fresh = _copy(source.place, source.path)
    except OSError:
        raise RestoreError(f"That backup could not be found. {NOTHING_CHANGED}") from None
    if seen is not None and fresh.stamp != seen:
        raise RestoreError(f"This backup changed after you looked at it. Look at it again first. {NOTHING_CHANGED}")
    check(fresh, tracks, full=True)
    if not fresh.usable:
        raise RestoreError(f"{fresh.reason} {NOTHING_CHANGED}")
    staged = data_dir / f"restore-staging-{secrets.token_hex(6)}.db"
    try:
        previous = _check_current(current, tracks)
        _stage(fresh.path, staged, data_dir, loaded, tracks, previous, undo=kind == "before-undo")
        with db.gate(current).alone(WAIT_SECONDS):
            before = _backup_current(current, data_dir / "backups", kind)
            _swap(staged, current)
    except PlainError as error:
        _remove(staged)
        log.warning("A restore was refused: %s", error)
        message = str(error)
        raise RestoreError(message if NOTHING_CHANGED in message else f"{message} {NOTHING_CHANGED}") from error
    except (sqlite3.Error, OSError) as error:
        _remove(staged)
        log.exception("A restore could not be done")
        raise RestoreError(f"The backup could not be put back. Check that the drive is still plugged in and "
                           f"has free space, then try again. {NOTHING_CHANGED}") from error
    except BaseException:
        _remove(staged)
        raise
    log.info("Restored backup %s from the %s; the records before were kept as %s", fresh.name, fresh.place, before.name)
    return {"restored_at": datetime.now().isoformat(timespec="seconds"),
            "from": {"place": fresh.place, "file": fresh.name, "made": fresh.made.isoformat(timespec="seconds")},
            "brought_up_to_date": fresh.pending, "before_restore" if kind == "before-restore" else "before_undo": before.name}


def _check_current(current: Path, tracks: dict) -> dict | None:
    """Refuse when the records in use have a part this program does not know: they could not be put back.
    Returns their household ID and epoch (decision 0100), so the restored copy's epoch can go above it."""
    conn = open_read_only(current)
    try:
        unknown = sorted(t for t, steps in _applied(conn).items() if t not in tracks and steps)
        previous = sync.read_state(conn)
    finally:
        conn.close()
    if unknown:
        raise RestoreError(f"Your records in use include a part this copy of Dashboard Plus does not have "
                           f"({', '.join(unknown)}), so a restore could not be undone. {NOTHING_CHANGED}")
    return previous


def _stage(source: Path, staged: Path, data_dir: Path, loaded, tracks: dict, previous: dict | None = None,
           undo: bool = False) -> None:
    """Copy the backup into a new file and make that copy ready to use. The backup itself is only read.
    Its records keep their permanent IDs (a copy from before them gets new ones) and it starts a new epoch
    above the records in use (`previous`), so revisions from before the restore are never taken as now."""
    reader = open_read_only(source)
    try:
        writer = sqlite3.connect(staged)
        try:
            reader.backup(writer)
        finally:
            writer.close()
    finally:
        reader.close()
    db.keep_private(staged)
    conn = db.connect(staged)
    try:
        migrations.migrate(conn, {migrations.CORE_TRACK: tracks[migrations.CORE_TRACK]})
        for module in loaded:
            migrations.migrate(conn, {module.name: module.migrations})
        if migrations.plan(conn, tracks):
            raise RestoreError("This copy could not be brought up to date.")
        startup.record_modules(conn, loaded)
        sync.after_restore(conn, loaded, previous, undo)
        _turn_off_lost_helpers(conn, data_dir)
        if not db.integrity_ok(conn):
            raise RestoreError("The prepared copy failed its check.")
    finally:
        conn.close()
    _flush(staged)
    if _journal_of(staged).exists():
        raise RestoreError("The prepared copy was not finished cleanly.")


def _turn_off_lost_helpers(conn, data_dir: Path) -> None:
    """A helper whose key is no longer kept (turned off, or made after another copy) is shown as off.
    Keys are never part of a backup, so a restore cannot bring one back (decision 0066)."""
    keys = helpers.known_key_ids(data_dir)
    lost = [r["id"] for r in conn.execute("SELECT id, key_id FROM core__helpers WHERE revoked_at IS NULL")
            if r["key_id"] not in keys]
    if not lost:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.transaction(conn):
        for helper_id in lost:
            conn.execute("UPDATE core__helpers SET revoked_at = ? WHERE id = ?", (now, helper_id))
            conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                         "VALUES (?, 'system', 'helper_off', 'core__helpers', ?, NULL, NULL)", (now, helper_id))


def _backup_current(current: Path, folder: Path, kind: str) -> Path:
    """A checked copy of the records in use, under a name not used before."""
    if not current.is_file():
        raise RestoreError("The data file in use could not be found.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target, number = folder / f"{kind}-{stamp}.db", 2
    while target.exists():
        target, number = folder / f"{kind}-{stamp}-{number}.db", number + 1
    conn = db.connect(current)
    try:
        return db.backup_to(conn, target)
    finally:
        conn.close()


def _swap(staged: Path, current: Path) -> None:
    """Put the prepared copy in place of the data file in one step (same folder, so the rename is atomic)."""
    if _journal_of(current).exists():
        raise RestoreError("The data file has an unfinished change waiting. Close and reopen Dashboard Plus, "
                           "then try again.")
    os.replace(staged, current)
    db.keep_private(current)
    _flush_folder(current.parent)


def _journal_of(path: Path) -> Path:
    return path.with_name(path.name + "-journal")


def _flush(path: Path) -> None:
    with open(path, "rb+") as handle:
        os.fsync(handle.fileno())


def _flush_folder(folder: Path) -> None:
    """Make the rename itself reach the disk (Mac and Linux; Windows does not open folders this way)."""
    if os.name != "posix":
        return
    try:
        descriptor = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _remove(path: Path) -> None:
    for leftover in (path, _journal_of(path)):
        try:
            leftover.unlink(missing_ok=True)
        except OSError:
            log.warning("Could not remove the unused restore file %s", leftover.name)
