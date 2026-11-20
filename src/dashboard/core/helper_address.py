"""The small address file a connector reads to find Dashboard after a restart: only the address and a run ID (0092)."""
from __future__ import annotations

import json
import os
import re
import secrets
import stat
from pathlib import Path

from dashboard.core import db

FILE = Path("run") / "helper-address.json"
FILE_NAME = FILE.name
VERSION = 1
MAX_BYTES = 1024  # the real file is about 110 bytes; anything larger is refused unread
RUN_ID = re.compile(r"^[0-9a-f]{32}$")
URL = re.compile(r"^http://127\.0\.0\.1:([0-9]{1,5})/api/v1$")  # one exact spelling, nothing else


def path(data_dir: Path) -> Path:
    """Where this data folder's address file is kept."""
    return Path(data_dir) / FILE


def write(data_dir: Path, port: int) -> str:
    """Write the file whole, under a temporary name first, then put it in place in one step. Returns its run ID.

    It holds a version, the current address and a random run ID that is not a secret. Never a key, cookie,
    session or close token: those stay in run/dashboard.json, which the connector never reads."""
    run_id = secrets.token_hex(16)
    target = path(data_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{FILE_NAME}.{run_id}.partial")
    text = json.dumps({"version": VERSION, "url": f"http://127.0.0.1:{int(port)}/api/v1", "run_id": run_id})
    descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(partial, target)
    except OSError:
        try:
            partial.unlink()
        except OSError:
            pass
        raise
    db.keep_private(target)
    return run_id


def remove(data_dir: Path, run_id: str) -> bool:
    """On a safe close, remove the file only if it is still this run's. Another run's file is left alone."""
    target = path(data_dir)
    try:
        if json.loads(target.read_text(encoding="utf-8")).get("run_id") != run_id:
            return False
        target.unlink()
    except (OSError, ValueError, AttributeError):
        return False
    return True


MISSING = ("I cannot find Dashboard Plus's current address file. Open Dashboard Plus on this computer. If you moved "
           "its folder or USB drive, copy the connection settings again from Settings → Helpers. The key was not sent.")
WRONG = ("Dashboard Plus's address file does not look right. Open Dashboard Plus and copy the connection settings "
         "again from Settings → Helpers. The key was not sent.")


def read(file: str | Path) -> tuple[str | None, str | None, str | None]:
    """The connector's side: (address, None, None), or (None, error code, plain reason). Never raises.

    The file is never trusted as proof: the address it gives must still pass the hello (0086) before the key
    goes. It is refused unread if it is too large, is a link to another file, or is not a regular file, and
    its contents are never quoted back."""
    file = Path(file)
    if file.name != FILE_NAME:
        return None, "address_file_wrong", WRONG
    try:
        if file.is_symlink():
            return None, "address_file_wrong", WRONG
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        descriptor = os.open(file, flags)
    except OSError:
        return None, "address_file_missing", MISSING
    try:
        with os.fdopen(descriptor, "rb") as handle:
            facts = os.fstat(handle.fileno())
            if not stat.S_ISREG(facts.st_mode) or facts.st_size > MAX_BYTES:
                return None, "address_file_wrong", WRONG
            raw = handle.read(MAX_BYTES + 1)
    except OSError:
        return None, "address_file_missing", MISSING
    if len(raw) > MAX_BYTES:
        return None, "address_file_wrong", WRONG
    try:
        found = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, "address_file_wrong", WRONG
    if (not isinstance(found, dict) or set(found) != {"version", "url", "run_id"} or found["version"] != VERSION
            or isinstance(found["version"], bool) or not isinstance(found["url"], str)
            or not isinstance(found["run_id"], str) or not RUN_ID.match(found["run_id"])):
        return None, "address_file_wrong", WRONG
    match = URL.match(found["url"])
    if not match or not 1 <= int(match.group(1)) <= 65535 or match.group(1) != str(int(match.group(1))):
        return None, "address_file_wrong", WRONG
    return found["url"], None, None
