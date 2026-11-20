"""Helpers the household has given a key to: making a key, checking it, replacing it, and turning it off."""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard.core import db, hello, schema
from dashboard.errors import PlainError

KEY_PREFIX = "dph_"
KEYS_FILE = "secrets/helper_keys.json"
MAX_HEADER = 100          # an Authorization header longer than this is refused without being looked at
MAX_NAME = 40
ACCESS_LEVELS = {"read": "Look only", "suggest": "Look and suggest new records"}
TOUCH_EVERY = timedelta(minutes=1)
_lock = threading.Lock()


@dataclass
class Helper:
    """One helper, as stored in core__helpers (never including its key)."""
    id: int
    key_id: str
    slug: str
    name: str
    access: str
    modules: list[str]
    created_at: str
    last_used_at: str | None
    revoked_at: str | None
    rotated_at: str | None = None      # when its key was last replaced (decision 0093)
    key_pending_at: str | None = None  # a key change started and not finished: no key of this helper works
    key_generation: int = 0            # goes up with each new key; a write checked with an older one is refused

    @property
    def actor(self) -> str:
        """Who a record made on this helper's suggestion is credited to in the history."""
        return f"agent:{self.slug}"

    @property
    def may_suggest(self) -> bool:
        return self.access == "suggest"

    @property
    def active(self) -> bool:
        return self.revoked_at is None

    @property
    def key_unfinished(self) -> bool:
        return self.key_pending_at is not None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _from_row(row) -> Helper:
    return Helper(row["id"], row["key_id"], row["slug"], row["name"], row["access"],
                  list(json.loads(row["modules"])), row["created_at"], row["last_used_at"], row["revoked_at"],
                  row["rotated_at"], row["key_pending_at"], int(row["key_generation"]))


def fingerprint(key: str) -> str:
    """The SHA-256 of a key: all that is ever kept of it."""
    return hello.fingerprint(key)


# ----- the file of fingerprints (outside the database, so a restored backup cannot revive a key) -----

def _keys_path(data_dir: Path) -> Path:
    return Path(data_dir) / KEYS_FILE


def _read_keys(data_dir: Path) -> dict[str, str]:
    try:
        found = json.loads(_keys_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in found.items()} if isinstance(found, dict) else {}


def known_key_ids(data_dir: Path) -> set[str]:
    """The helpers (by key_id) whose key still works: the ones with a fingerprint in the file."""
    return set(_read_keys(data_dir).values())


def active_fingerprints(data_dir: Path) -> list[str]:
    """The fingerprints of every key that still works, for Dashboard's answer to a connector's hello (0086)."""
    return list(_read_keys(data_dir))


def _write_keys(data_dir: Path, keys: dict[str, str]) -> None:
    """Write the file whole, under a temporary name first, readable only by this computer account."""
    path = _keys_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    db.keep_private(path.parent)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(keys, sort_keys=True), encoding="utf-8")
    db.keep_private(partial)
    os.replace(partial, path)
    db.keep_private(path)


# ----- making, listing and turning off -----------------------------------------------------------------

def make_slug(conn, name: str) -> str:
    """A short lower-case label for history ("Pet diary helper" -> pet-diary-helper), never used twice."""
    base = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", name.lower())).strip("-")[:MAX_NAME].strip("-") or "helper"
    taken = {r[0] for r in conn.execute("SELECT slug FROM core__helpers")}
    slug, number = base, 2
    while slug in taken:
        slug, number = f"{base}-{number}", number + 1
    return slug


def issue(conn, data_dir: Path, name: str, access: str, modules: list[str]) -> tuple[Helper, str]:
    """Make a helper and its key. The key is returned once; only its fingerprint is kept."""
    name = " ".join((name or "").split())
    if not name:
        raise PlainError("Give the helper a name.")
    if len(name) > MAX_NAME:
        raise PlainError(f"Keep the helper's name to {MAX_NAME} letters or fewer.")
    if access not in ACCESS_LEVELS:
        raise PlainError("Choose what the helper may do.")
    modules = sorted(set(modules))
    if not modules:
        raise PlainError("Choose at least one part of your records.")
    key = _new_key()
    key_id = secrets.token_hex(8)
    now = _now()
    with _lock:
        with db.transaction(conn):  # the database row first, then the file
            slug = make_slug(conn, name)
            cursor = conn.execute(
                "INSERT INTO core__helpers (key_id, slug, name, access, modules, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (key_id, slug, name, access, json.dumps(modules), now))
            helper_id = cursor.lastrowid
            conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                         "VALUES (?, 'person', 'helper_add', 'core__helpers', ?, NULL, ?)",
                         (now, helper_id, json.dumps({"access": access, "modules": modules}, sort_keys=True)))
        keys = _read_keys(data_dir)
        keys[fingerprint(key)] = key_id
        _write_keys(data_dir, keys)
    return get(conn, helper_id), key


def _new_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def get(conn, helper_id: int) -> Helper | None:
    row = conn.execute("SELECT * FROM core__helpers WHERE id = ?", (helper_id,)).fetchone()
    return _from_row(row) if row else None


def all_helpers(conn) -> list[Helper]:
    """Every helper ever made, turned-on ones first, newest first."""
    rows = conn.execute("SELECT * FROM core__helpers ORDER BY revoked_at IS NOT NULL, id DESC")
    return [_from_row(r) for r in rows]


def verify(conn, data_dir: Path, header: str | None) -> Helper | None:
    """The helper an `Authorization: Bearer <key>` header belongs to, or None. Never raises on bad input."""
    if not header or len(header) > MAX_HEADER:
        return None
    scheme, _, key = header.partition(" ")
    if scheme != "Bearer" or not key.startswith(KEY_PREFIX) or " " in key:
        return None
    wanted = fingerprint(key)
    found = None
    for known, key_id in _read_keys(data_dir).items():  # compare against every one, so timing says nothing
        if hmac.compare_digest(known, wanted):
            found = key_id
    if found is None:
        return None
    row = conn.execute("SELECT * FROM core__helpers WHERE key_id = ?", (found,)).fetchone()
    if row is None or row["revoked_at"] is not None or row["key_pending_at"] is not None:
        return None  # turned off, or in the middle of a key change: no key of it works (0093)
    return _from_row(row)


def still_current(conn, helper: Helper) -> bool:
    """Inside a write transaction: True only if `helper`, as it was when its key was checked, may still write.

    A request checked with a key that was then turned off or replaced is refused at the write (decision 0093)."""
    row = conn.execute("SELECT revoked_at, key_pending_at, key_generation FROM core__helpers WHERE id = ?",
                       (helper.id,)).fetchone()
    return (row is not None and row["revoked_at"] is None and row["key_pending_at"] is None
            and int(row["key_generation"]) == helper.key_generation)


def turn_off(conn, data_dir: Path, helper_id: int) -> Helper:
    """Stop a helper's key working at once. Its suggestions and history are kept."""
    helper = get(conn, helper_id)
    if helper is None:
        raise PlainError("That helper could not be found.")
    if not helper.active:
        return helper
    with _lock:
        keys = {k: v for k, v in _read_keys(data_dir).items() if v != helper.key_id}  # the file first
        _write_keys(data_dir, keys)
        now = _now()
        with db.transaction(conn):
            conn.execute("UPDATE core__helpers SET revoked_at = ? WHERE id = ?", (now, helper_id))
            conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                         "VALUES (?, 'person', 'helper_off', 'core__helpers', ?, NULL, NULL)", (now, helper_id))
    return get(conn, helper_id)


class HelperOff(PlainError):
    """A new key was asked for a helper whose access is off: nothing is made."""


class KeyNotChanged(PlainError):
    """The key file could not be written, or the last step failed: the helper is paused and no key is shown."""


HELPER_OFF = "This helper's access is off. No key was made."
NOT_CHANGED = ("The key could not be changed. This helper's access is paused so the old key cannot be used. "
               "Check the data folder, then make a new key from Helpers.")


def rotate(conn, data_dir: Path, helper_id: int) -> tuple[Helper, str]:
    """Give a helper a new key and stop its old one, keeping its id, name, grant, suggestions and history.

    The database and the key file cannot change in one step, so (decision 0093):
    1. the helper is marked as changing its key, and its key count goes up: from now no key of it works, and
       a suggestion checked with the old key is refused when it reaches the write;
    2. the key file is replaced whole, holding the new fingerprint instead of every old one for this helper;
    3. the mark is cleared and the change noted in the history, without any key or fingerprint.
    Only then is the new key returned, to be shown once. If any step fails, the helper stays paused, no key is
    returned, and the old key never works again."""
    with _lock:
        helper = get(conn, helper_id)
        if helper is None:
            raise PlainError("That helper could not be found.")
        if not helper.active:
            raise HelperOff(HELPER_OFF)
        key = _new_key()
        with db.transaction(conn):
            changed = conn.execute(
                "UPDATE core__helpers SET key_pending_at = ?, key_generation = key_generation + 1 "
                "WHERE id = ? AND revoked_at IS NULL", (_now(), helper_id)).rowcount
        if not changed:
            raise HelperOff(HELPER_OFF)
        try:
            _swap_fingerprint(data_dir, helper.key_id, fingerprint(key))
            _finish_rotation(conn, helper_id)
        except (OSError, sqlite3.Error) as error:
            raise KeyNotChanged(NOT_CHANGED) from error
    return get(conn, helper_id), key


def _swap_fingerprint(data_dir: Path, key_id: str, new_fingerprint: str) -> None:
    """One whole-file replacement: every fingerprint of this helper out, the new one in. Never both at once."""
    keys = {k: v for k, v in _read_keys(data_dir).items() if v != key_id}
    keys[new_fingerprint] = key_id
    _write_keys(data_dir, keys)


def _finish_rotation(conn, helper_id: int) -> None:
    now = _now()
    with db.transaction(conn):
        conn.execute("UPDATE core__helpers SET key_pending_at = NULL, rotated_at = ? WHERE id = ?", (now, helper_id))
        conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) "
                     "VALUES (?, 'person', 'helper_rotate', 'core__helpers', ?, NULL, NULL)", (now, helper_id))


def stop_unfinished_key_changes(conn, data_dir: Path) -> list[int]:
    """At start-up: a key change that did not finish (the program stopped half way) leaves no working key.

    Every fingerprint of such a helper is removed and the helper stays marked, so its card says the change
    did not finish and offers a new key. The old key is never brought back. Returns the helpers stopped."""
    unfinished = conn.execute("SELECT id, key_id FROM core__helpers WHERE key_pending_at IS NOT NULL "
                              "AND revoked_at IS NULL").fetchall()
    if not unfinished:
        return []
    with _lock:
        stale = {r["key_id"] for r in unfinished}
        keys = _read_keys(data_dir)
        if any(v in stale for v in keys.values()):
            _write_keys(data_dir, {k: v for k, v in keys.items() if v not in stale})
    return [r["id"] for r in unfinished]


def touch(conn, helper: Helper) -> None:
    """Note that the helper was just used, at most once a minute."""
    now = datetime.now(timezone.utc)
    if helper.last_used_at:
        try:
            if now - datetime.fromisoformat(helper.last_used_at) < TOUCH_EVERY:
                return
        except ValueError:
            pass
    stamp = now.isoformat(timespec="seconds")
    with db.transaction(conn):
        conn.execute("UPDATE core__helpers SET last_used_at = ? WHERE id = ?", (stamp, helper.id))
    helper.last_used_at = stamp


def allowed_registry(registry: dict, helper: Helper) -> dict:
    """The tables a helper may use: those of the modules switched on that the household ticked for it."""
    return {name: info for name, info in registry.items() if info.module.name in helper.modules}


def hidden_links(info, helper: Helper, registry: dict) -> list:
    """The link columns of a table that point into a part this helper was not given (or one switched off).

    A helper never sees these: not in the table's description, not in records, and it may not suggest them.
    Leaving them out is what stops a helper given Vehicles from learning anything about People."""
    allowed = allowed_registry(registry, helper)
    return [c for c in info.table.columns.values() if c.type in ("link", "links")
            and schema.target_table(info.module.name, c) not in allowed]
