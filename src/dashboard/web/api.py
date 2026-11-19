"""The helper API (/api/v1): programs the household gave a key to can look at records and suggest new ones."""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections import deque
from dataclasses import asdict
from decimal import Decimal

from flask import Blueprint, Response, current_app, g, request

from dashboard import __version__
from dashboard.core import helpers, proposals, records, schema, watch
from dashboard.core.proposals import MAX_ENTRIES, MAX_PER_DAY, ProposalError
from dashboard.web import display

log = logging.getLogger("dashboard.helpers")
helper_api = Blueprint("helper_api", __name__, url_prefix="/api/v1")
PREFIX = "/api/v1/"
MAX_BODY = 65536
DEFAULT_PAGE, MAX_PAGE = 50, 200
JSON_TYPE = "application/json; charset=utf-8"
REQUESTS_PER_MINUTE = 120  # per helper; app.config["HELPER_REQUESTS_PER_MINUTE"] can change it (decision 0074)
NOT_FOUND = "That table or record could not be found. GET /api/v1/tables lists what this helper may use."
_recent_lock = threading.Lock()


def api_error(status: int, code: str, message: str, **extra) -> Response:
    """An error in the one shape helpers can rely on: {"error": code, "message": plain sentence, ...}."""
    return reply({"error": code, "message": message, **extra}, status)


def reply(payload: dict, status: int = 200) -> Response:
    return Response(json.dumps(payload, ensure_ascii=False), status=status, content_type=JSON_TYPE)


def authenticate():
    """Run before every /api/v1 request: who is this helper? Returns an error response, or None to carry on.

    Helpers are programs, not web pages: a request that carries an Origin header (every browser adds one to
    a cross-site request) is refused, and only `Authorization: Bearer <key>` is read. Cookies, the address
    and form fields are never looked at, and pages never look at this header."""
    if "Origin" in request.headers:
        return api_error(403, "from_a_web_page", "The helper API cannot be used from a web page.")
    request.max_content_length = MAX_BODY
    if current_app.config["DATA_DIR"] is None:
        return api_error(401, "no_key", "This helper's access key is missing or no longer works. "
                                        "Ask the household to check Helpers in Settings.")
    conn = current_app.config["CONNECT"]()
    helper = helpers.verify(conn, current_app.config["DATA_DIR"], request.headers.get("Authorization"))
    if helper is None:
        log.warning("helper key refused")
        return api_error(401, "no_key", "This helper's access key is missing or no longer works. "
                                        "Ask the household to check Helpers in Settings.")
    wait = _too_soon(helper)
    if wait:
        response = api_error(429, "too_many_requests", "This helper is sending requests too quickly. "
                                                       f"Wait {wait} seconds, then try again.")
        response.headers["Retry-After"] = str(wait)
        return response
    helpers.touch(conn, helper)
    g.helper = helper
    if request.method == "POST":  # only once we know who is asking
        if (request.content_length or 0) > MAX_BODY:
            return api_error(413, "too_large", "This request is too large. Send fewer suggestions at a time.")
        if request.mimetype != "application/json":
            return api_error(415, "needs_json", "Send the body as JSON (Content-Type: application/json).")
    return None


def _too_soon(helper) -> int:
    """Count this request against the helper's limit per minute. Returns 0 to carry on, or seconds to wait.

    Kept in memory only: it starts again when Dashboard restarts, which is fine for one household's computer."""
    limit = current_app.config.get("HELPER_REQUESTS_PER_MINUTE", REQUESTS_PER_MINUTE)
    now = time.monotonic()
    with _recent_lock:
        recent = current_app.extensions.setdefault("helper_requests", {}).setdefault(helper.id, deque())
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= limit:
            return max(1, math.ceil(60 - (now - recent[0])))
        recent.append(now)
    return 0


def _full() -> dict:
    return current_app.config["REGISTRY_FOR_REQUEST"]()


def _allowed() -> dict:
    return helpers.allowed_registry(_full(), g.helper)


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), _full())


def _hidden(info) -> set[str]:
    """Columns this helper never sees in this table: links into parts it was not given."""
    return {c.name for c in helpers.hidden_links(info, g.helper, _full())}


def _grant_refusal(name: str) -> Response | None:
    """The refusal for a table this helper may not use, or None if it may.

    A table in a part the helper was not given gets exactly the same answer as a table that does not exist,
    so a helper cannot find out what else the household keeps (decision 0074). /me says what it may use."""
    if name not in _allowed():
        return api_error(404, "not_found", NOT_FOUND)
    return None


def _out(column, value):
    """A stored value as the helper sees it: money in whole units (not cents), yes/no as true/false."""
    if value is None or value == []:
        return value
    if column.type == "money":
        return float(Decimal(int(value)) / 100)
    if column.type == "boolean":
        return bool(value)
    return value


def record_out(info: records.TableInfo, row: dict, hidden: set[str]) -> dict:
    """One record for a helper: its ordinary fields, never private ones, links it may not follow, or the
    program's own bookkeeping."""
    return {"id": row["id"], "created_at": row["created_at"], "updated_at": row["updated_at"], "source": row["source"],
            "values": {c.name: _out(c, row.get(c.name)) for c in info.table.columns.values()
                       if not c.sensitive and c.name not in hidden}}


def table_spec(info: records.TableInfo, store: records.Records, may_suggest: bool, hidden: set[str]) -> dict:
    """What a helper needs to know to read or suggest into one table. Private columns are left out, and so
    are links into parts it was not given (`hidden`), without saying where they lead."""
    worked_out = sorted(store._derived(info))
    columns, private = [], 0
    for column in info.table.columns.values():
        if column.sensitive:
            private += 1
            continue
        if column.name in hidden:
            continue
        item = {"name": column.name, "label": display.column_label(info, column), "type": column.type,
                "required": column.required, "help": display.column_help(info, column), "unit": column.unit,
                "min": column.min, "max": column.max,
                "can_suggest": column.type != "file" and column.name not in worked_out}
        if column.type in ("link", "links"):
            item["to"] = schema.target_table(info.module.name, column)
        if column.type == "choice":
            item["choices"] = [{"key": c.key, "label": c.label} for c in column.choices]
        if column.type == "money":
            item["note"] = "Send and read in whole units, like 12.50. It is stored in cents."
        columns.append(item)
    spec = {"table": info.name, "module": info.module.name, "title": display.table_title(info),
            "can_suggest": may_suggest, "columns": columns, "worked_out": worked_out,
            "private_columns_left_out": private}
    needs_private = any(c.sensitive and c.required for c in info.table.columns.values())
    needs_file = any(c.type == "file" and c.required for c in info.table.columns.values())
    needs_hidden = any(c.required for c in info.table.columns.values() if c.name in hidden)
    if may_suggest and (needs_private or needs_file or needs_hidden):
        spec["can_suggest"] = False
        spec["reason"] = ("This table needs a private detail, so helpers cannot add to it." if needs_private
                          else "This table needs a file, so helpers cannot add to it." if needs_file
                          else "This table needs a link to a part of the records this helper was not given, "
                               "so it cannot add to it.")
    elif not may_suggest:
        spec["reason"] = "This helper may look but not suggest."
    return spec


@helper_api.get("/me")
def me():
    helper, conn = g.helper, current_app.config["CONNECT"]()
    titles = {i.module.name: i.module.title for i in _allowed().values()}
    words = ", ".join(titles[n] for n in sorted(titles, key=titles.get)) or "nothing yet"
    return reply({"name": helper.name, "access": helper.access,
                  "modules": [{"name": n, "title": titles[n]} for n in sorted(titles)],
                  "message": f"{helper.name} may use: {words}. Ask the household to change its access in Settings.",
                  "private_details": False,
                  "limits": {"entries_per_call": MAX_ENTRIES, "suggestions_per_day": MAX_PER_DAY,
                             "suggestions_left_today": max(0, MAX_PER_DAY - proposals.used_today(conn, helper)),
                             "max_body_bytes": MAX_BODY,
                             "requests_per_minute": current_app.config.get("HELPER_REQUESTS_PER_MINUTE",
                                                                           REQUESTS_PER_MINUTE)},
                  "api_version": "1", "program_version": __version__})


@helper_api.get("/tables")
def tables():
    store = _store()
    return reply({"tables": [table_spec(info, store, g.helper.may_suggest, _hidden(info))
                             for info in _allowed().values()]})


def _int_arg(name: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(int(request.args.get(name, default)), high))
    except (TypeError, ValueError):
        return default


@helper_api.get("/tables/<table>/records")
def table_records(table):
    refusal = _grant_refusal(table)
    if refusal:
        return refusal
    limit = _int_arg("limit", DEFAULT_PAGE, 1, MAX_PAGE)
    rows = _store().after(table, _int_arg("after", 0, 0, 2 ** 62), limit)
    info = _full()[table]
    hidden = _hidden(info)
    return reply({"table": table, "records": [record_out(info, r, hidden) for r in rows],
                  "next_after": rows[-1]["id"] if len(rows) == limit else None})


@helper_api.get("/tables/<table>/records/<int:record_id>")
def one_record(table, record_id):
    refusal = _grant_refusal(table)
    if refusal:
        return refusal
    try:
        row = _store().get(table, record_id)
    except records.RecordNotFound:
        return api_error(404, "not_found", NOT_FOUND)
    info = _full()[table]
    return reply({"table": table, "record": record_out(info, row, _hidden(info))})


def _plain(items) -> list[dict]:
    return [{k: v for k, v in asdict(item).items() if k not in ("sort_key", "fix")} for item in items]


@helper_api.get("/attention")
def attention():
    conn, allowed = current_app.config["CONNECT"](), _allowed()
    return reply({"running_low": _plain(watch.running_low(conn, allowed)),
                  "expiring": _plain(watch.expiring(conn, allowed)),
                  "supplies": _plain(watch.supplies(conn, allowed)),
                  "gaps": _plain(watch.gaps(conn, allowed))})


@helper_api.post("/proposals")
def suggest():
    body = request.get_json(silent=True)
    try:
        result, created = proposals.submit(current_app.config["CONNECT"](), _full(), g.helper, body)
    except ProposalError as error:
        extra = {"problems": error.problems} if error.problems else {}
        return api_error(error.status, error.code, str(error), **extra)
    return reply(result, 201 if created else 200)


@helper_api.get("/batches")
def batches():
    limit = _int_arg("limit", 20, 1, 100)
    found = proposals.helper_batches(current_app.config["CONNECT"](), g.helper, _int_arg("after", 0, 0, 2 ** 62) or None,
                                     limit)
    return reply({"batches": found, "next_after": found[-1]["id"] if len(found) == limit else None})


@helper_api.get("/batches/<int:batch_id>")
def one_batch(batch_id):
    conn = current_app.config["CONNECT"]()
    if not proposals.owns(conn, g.helper, batch_id):
        return api_error(404, "not_found", "That batch could not be found.")
    return reply(proposals.batch_result(conn, batch_id, detail=True))
