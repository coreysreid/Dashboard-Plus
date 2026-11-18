"""Suggestions from helpers: checked, kept waiting in their own table, and added only when a person accepts."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone

from dashboard.core import db, helpers
from dashboard.core.records import Records, ValidationError
from dashboard.errors import PlainError

MAX_ENTRIES = 50
MAX_PER_DAY = 200
MAX_WHY = 300
MAX_KEY = 100
REQUEST_KEY = re.compile(r"^[A-Za-z0-9._:-]+$")
SCALARS = (str, int, float, bool, type(None))


class ProposalError(PlainError):
    """A request the helper API refuses: an HTTP status, a short code, a plain message and any problems found."""

    def __init__(self, status: int, code: str, message: str, problems: list[dict] | None = None):
        super().__init__(message)
        self.status, self.code, self.problems = status, code, problems or []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _title(info) -> str:
    """A table's friendly name, as labels.toml gives it."""
    return info.module.labels.get("tables", {}).get(info.table.name, {}).get("title") or info.table.title


def _bad(message: str = "This request could not be read. Check the fields and try again.") -> ProposalError:
    return ProposalError(400, "bad_request", message)


def used_today(conn: sqlite3.Connection, helper: helpers.Helper) -> int:
    """How many suggested rows this helper has sent since midnight (UTC)."""
    midnight = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00")
    return conn.execute(
        "SELECT COUNT(*) FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
        "WHERE b.helper_id = ? AND p.created_at >= ?", (helper.id, midnight)).fetchone()[0]


def _read_body(body) -> tuple[str, str, list[tuple[str, dict]]]:
    """Check the shape of a request and return (request_key, why, [(table, values)])."""
    if not isinstance(body, dict) or set(body) - {"request_key", "why", "entries"}:
        raise _bad()
    key = body.get("request_key")
    if not isinstance(key, str) or not 1 <= len(key) <= MAX_KEY or not REQUEST_KEY.match(key):
        raise _bad("Give this request a key so a retry cannot add the same rows twice.")
    why = body.get("why")
    if not isinstance(why, str) or not 1 <= len(why.strip()) <= MAX_WHY:
        raise _bad("Say why, in a sentence, so the household knows where these came from.")
    entries = body.get("entries")
    if not isinstance(entries, list) or not entries:
        raise _bad()
    if len(entries) > MAX_ENTRIES:
        raise _bad(f"Send {MAX_ENTRIES} suggestions or fewer at a time.")
    found = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"table", "values"} or not isinstance(entry["table"], str) \
                or not isinstance(entry["values"], dict):
            raise _bad()
        found.append((entry["table"], entry["values"]))
    return key, why.strip(), found


def _body_hash(why: str, entries: list[tuple[str, dict]]) -> str:
    text = json.dumps({"why": why, "entries": [[t, v] for t, v in entries]}, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _grant_words(helper: helpers.Helper, registry: dict) -> str:
    titles = sorted({info.module.title for info in registry.values() if info.module.name in helper.modules})
    return f"{helper.name} may use: {', '.join(titles) or 'nothing yet'}."


def _check_tables(helper: helpers.Helper, registry: dict, entries: list[tuple[str, dict]]) -> None:
    for name, _values in entries:
        if name not in registry:
            raise ProposalError(404, "not_found", "That table or record could not be found.")
        if registry[name].module.name not in helper.modules:
            raise ProposalError(403, "not_allowed",
                                f"{_grant_words(helper, registry)} Ask the household to change its access in Settings.")
    private = sorted({field for name, values in entries for field in values
                      if field in registry[name].table.columns and registry[name].table.columns[field].sensitive})
    if private:
        raise ProposalError(403, "private_detail",
                            f"Private details are never shared with helpers. Leave out: {', '.join(private)}.")


def _shape_problems(registry: dict, entries: list[tuple[str, dict]]) -> list[dict]:
    """Problems found by looking at field names and kinds of value alone, before anything is tried."""
    problems = []
    for position, (name, values) in enumerate(entries):
        info = registry[name]
        needs_private = [c.name for c in info.table.columns.values() if c.sensitive and c.required]
        if needs_private:
            problems.append({"entry": position, "table": name, "field": "",
                             "message": "Helpers cannot add to this table, because it needs a private detail."})
            continue
        for field, value in values.items():
            column = info.table.columns.get(field)
            if column is None:
                problems.append({"entry": position, "table": name, "field": field[:60],
                                 "message": "is not a field of this table."})
            elif column.type == "file":
                problems.append({"entry": position, "table": name, "field": field,
                                 "message": "is a file, and helpers cannot suggest files."})
            elif not (isinstance(value, SCALARS) or (column.type == "links" and isinstance(value, list)
                                                    and all(isinstance(v, SCALARS) for v in value))):
                problems.append({"entry": position, "table": name, "field": field,
                                 "message": "must be a single value."})
    return problems


def _invalid(registry: dict, problems: list[dict]) -> ProposalError:
    tables = {p["table"] for p in problems}
    lead = f"{_title(registry[next(iter(tables))])}: some" if len(tables) == 1 else "Some"
    return ProposalError(422, "invalid", f"{lead} values could not be used. Nothing was saved.", problems)


def submit(conn: sqlite3.Connection, registry: dict, helper: helpers.Helper, body) -> tuple[dict, bool]:
    """Check a helper's request and keep it waiting for the household. Returns (result, newly_created).

    All or nothing: if any entry is wrong, nothing is stored. The same `request_key` with the same body
    returns the first answer again. `registry` holds every table switched on."""
    if not helper.may_suggest:
        raise ProposalError(403, "look_only", "This helper may look but not suggest changes. "
                                              "Ask the household to change its access in Settings.")
    key, why, entries = _read_body(body)
    digest = _body_hash(why, entries)
    stored = conn.execute("SELECT id, body_hash FROM core__helper_batches WHERE helper_id = ? AND request_key = ?",
                          (helper.id, key)).fetchone()
    if stored:
        return _same_or_refuse(conn, stored, digest), False
    if used_today(conn, helper) + len(entries) > MAX_PER_DAY:
        raise ProposalError(429, "daily_limit", f"This helper has reached {MAX_PER_DAY} suggestions today. "
                                                f"Try again tomorrow.")
    _check_tables(helper, registry, entries)
    problems = _shape_problems(registry, entries)
    if not problems:
        wrong = Records(conn, registry).check_create(entries, helper.actor)
        problems = [{"entry": position, "table": entries[position][0], "field": field[:60], "message": message}
                    for position, fields in sorted(wrong.items()) for field, message in fields.items()]
    if problems:
        raise _invalid(registry, problems)
    now = _now()
    try:
        with db.transaction(conn):
            batch_id = conn.execute(
                "INSERT INTO core__helper_batches (helper_id, request_key, body_hash, why, created_at) "
                "VALUES (?, ?, ?, ?, ?)", (helper.id, key, digest, why, now)).lastrowid
            for position, (name, values) in enumerate(entries):
                proposal_id = conn.execute(
                    "INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?)", (batch_id, position, name, json.dumps(values, sort_keys=True), now)).lastrowid
                conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                             "VALUES (?, ?, 'propose', 'core__proposals', ?, NULL, ?, ?)",
                             (now, helper.actor, proposal_id, json.dumps({"table": name, "batch": batch_id}), batch_id))
    except sqlite3.IntegrityError:  # two identical requests at once: the second gets the first's answer
        stored = conn.execute("SELECT id, body_hash FROM core__helper_batches WHERE helper_id = ? AND request_key = ?",
                              (helper.id, key)).fetchone()
        if stored is None:
            raise
        return _same_or_refuse(conn, stored, digest), False
    return batch_result(conn, batch_id), True


def _same_or_refuse(conn, stored, digest: str) -> dict:
    if stored["body_hash"] != digest:
        raise ProposalError(409, "request_key_reused", "This request key was already used for different "
                                                        "suggestions. Check the earlier batch, then use a new key.")
    return batch_result(conn, stored["id"])


def batch_result(conn: sqlite3.Connection, batch_id: int, detail: bool = False) -> dict:
    """One batch as the helper sees it: its rows with their state. `detail` adds record ids, reasons and dates."""
    batch = conn.execute("SELECT * FROM core__helper_batches WHERE id = ?", (batch_id,)).fetchone()
    rows = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? ORDER BY position", (batch_id,)).fetchall()
    proposals = []
    for r in rows:
        item = {"id": r["id"], "position": r["position"], "table": r["table_name"], "status": r["status"]}
        if detail:
            item.update(record_id=r["record_id"], reason=r["reason"], decided_at=r["decided_at"])
        proposals.append(item)
    waiting = sum(1 for r in rows if r["status"] == "pending")
    if waiting:
        message = (f"{waiting} suggestion{' is' if waiting == 1 else 's are'} waiting for the household to review. "
                   f"Nothing changes until they accept {'it' if waiting == 1 else 'them'}.")
    else:
        message = "The household has decided on every suggestion in this batch."
    result = {"batch_id": batch_id, "state": "waiting" if waiting else "decided", "why": batch["why"],
              "proposals": proposals, "message": message}
    if detail:
        result.update(request_key=batch["request_key"], created_at=batch["created_at"])
    return result


def helper_batches(conn: sqlite3.Connection, helper: helpers.Helper, after: int | None, limit: int) -> list[dict]:
    """This helper's own batches, newest first, with how many rows are in each state."""
    rows = conn.execute(
        "SELECT b.id, b.request_key, b.why, b.created_at, COUNT(p.id) AS total, "
        "COALESCE(SUM(p.status = 'pending'), 0) AS pending, COALESCE(SUM(p.status = 'accepted'), 0) AS accepted, "
        "COALESCE(SUM(p.status = 'rejected'), 0) AS rejected FROM core__helper_batches b "
        "LEFT JOIN core__proposals p ON p.batch_id = b.id WHERE b.helper_id = ? AND b.id < ? "
        "GROUP BY b.id ORDER BY b.id DESC LIMIT ?", (helper.id, after or 2 ** 62, limit)).fetchall()
    return [{"id": r["id"], "request_key": r["request_key"], "why": r["why"], "created_at": r["created_at"],
             "state": "waiting" if r["pending"] else "decided", "total": r["total"], "pending": r["pending"],
             "accepted": r["accepted"], "rejected": r["rejected"]} for r in rows]


def owns(conn: sqlite3.Connection, helper: helpers.Helper, batch_id: int) -> bool:
    return conn.execute("SELECT 1 FROM core__helper_batches WHERE id = ? AND helper_id = ?",
                        (batch_id, helper.id)).fetchone() is not None


# ----- the household's side: Review -------------------------------------------------------------------

def pending_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM core__proposals WHERE status = 'pending'").fetchone()[0]


def pending(conn: sqlite3.Connection) -> list[dict]:
    """Batches that still have rows waiting, newest first, each with its waiting rows and its helper."""
    batches = conn.execute(
        "SELECT b.*, h.name AS helper_name, h.revoked_at AS helper_revoked_at FROM core__helper_batches b "
        "JOIN core__helpers h ON h.id = b.helper_id WHERE EXISTS "
        "(SELECT 1 FROM core__proposals p WHERE p.batch_id = b.id AND p.status = 'pending') "
        "ORDER BY b.id DESC").fetchall()
    found = []
    for b in batches:
        rows = conn.execute("SELECT * FROM core__proposals WHERE batch_id = ? AND status = 'pending' ORDER BY position",
                            (b["id"],)).fetchall()
        found.append({"id": b["id"], "helper": b["helper_name"], "helper_off": b["helper_revoked_at"] is not None,
                      "why": b["why"], "created_at": b["created_at"], "total": conn.execute(
                          "SELECT COUNT(*) FROM core__proposals WHERE batch_id = ?", (b["id"],)).fetchone()[0],
                      "proposals": [dict(r, values=json.loads(r["values_json"])) for r in rows]})
    return found


def _audit(conn, action: str, proposal_id: int, after: dict | None, batch_id: int) -> None:
    conn.execute("INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
                 "VALUES (?, 'person', ?, 'core__proposals', ?, NULL, ?, ?)",
                 (_now(), action, proposal_id, json.dumps(after, sort_keys=True) if after else None, batch_id))


def _load(conn, proposal_id: int):
    row = conn.execute(
        "SELECT p.*, h.slug AS slug FROM core__proposals p JOIN core__helper_batches b ON b.id = p.batch_id "
        "JOIN core__helpers h ON h.id = b.helper_id WHERE p.id = ?", (proposal_id,)).fetchone()
    if row is None:
        raise PlainError("That suggestion could not be found.")
    if row["status"] != "pending":
        raise PlainError("That suggestion has already been decided.")
    return row


def _why_not(store: Records, info, error: ValidationError) -> str:
    parts = []
    for field, message in error.problems.items():
        label = store._label(info, field) if field in info.table.columns else field
        parts.append(f"{label} {message}" if field else message)
    return "This can't be added as it is: " + " ".join(parts) + " Reject it, or add the record yourself."


def accept(conn: sqlite3.Connection, registry: dict, proposal_id: int) -> tuple[str, int]:
    """Add the suggested record, in the person's name. Returns (table, new record id).

    If the world has changed so the record can no longer be added, the suggestion stays waiting with the
    reason written on it, nothing else is changed, and a PlainError says why."""
    row = _load(conn, proposal_id)
    info = registry.get(row["table_name"])
    if info is None:
        module = row["table_name"].split("__", 1)[0]
        reason = f"This is for {module}, which is switched off. Reject it, or switch it on in Settings first."
        raise PlainError(reason)
    store = Records(conn, registry)
    try:
        with db.transaction(conn):
            record_id = store.create_in(row["table_name"], json.loads(row["values_json"]), actor=f"agent:{row['slug']}",
                                        review_status="confirmed", batch_id=row["batch_id"])
            conn.execute(f"UPDATE {info.name} SET edited_by_person = 1 WHERE id = ?", (record_id,))
            conn.execute("UPDATE core__proposals SET status = 'accepted', record_id = ?, reason = NULL, decided_at = ? "
                         "WHERE id = ?", (record_id, _now(), proposal_id))
            _audit(conn, "accept", proposal_id, {"table": info.name, "record_id": record_id}, row["batch_id"])
    except ValidationError as error:
        reason = _why_not(store, info, error)
        with db.transaction(conn):
            conn.execute("UPDATE core__proposals SET reason = ? WHERE id = ?", (reason, proposal_id))
        raise PlainError(reason) from None
    return info.name, record_id


def reject(conn: sqlite3.Connection, proposal_id: int) -> str:
    """Say no to one suggestion. Nothing is added. Returns its table name."""
    row = _load(conn, proposal_id)
    with db.transaction(conn):
        conn.execute("UPDATE core__proposals SET status = 'rejected', decided_at = ? WHERE id = ?",
                     (_now(), proposal_id))
        _audit(conn, "reject", proposal_id, {"table": row["table_name"]}, row["batch_id"])
    return row["table_name"]


def accept_batch(conn: sqlite3.Connection, registry: dict, batch_id: int) -> tuple[int, list[str]]:
    """Accept every waiting row of a batch, each in its own transaction. Returns (added, [reasons for the rest])."""
    added, failed = 0, []
    for row in conn.execute("SELECT id FROM core__proposals WHERE batch_id = ? AND status = 'pending' ORDER BY position",
                            (batch_id,)).fetchall():
        try:
            accept(conn, registry, row["id"])
            added += 1
        except PlainError as error:
            failed.append(str(error))
    return added, failed


def reject_batch(conn: sqlite3.Connection, batch_id: int) -> int:
    """Reject every waiting row of a batch. Returns how many."""
    ids = [r["id"] for r in conn.execute(
        "SELECT id FROM core__proposals WHERE batch_id = ? AND status = 'pending' ORDER BY position", (batch_id,))]
    for proposal_id in ids:
        reject(conn, proposal_id)
    return len(ids)
