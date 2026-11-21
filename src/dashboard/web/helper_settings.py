"""Settings, Helpers: give an assistant a key, choose what it may do, give it a new key, and turn its access off."""
from __future__ import annotations

import json
import secrets
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, url_for

import dashboard
from dashboard.connector.config import ADDRESS_FILE_VARIABLE, KEY_VARIABLE, URL_VARIABLE
from dashboard.core import helper_address, helpers, settings
from dashboard.errors import PlainError
from dashboard.web import helper_guide

helper_settings = Blueprint("helper_settings", __name__)
ACCESS_WORDS = {"read": "May look", "suggest": "May look and suggest new records"}
KEY_PLACEHOLDER = "YOUR-KEY-HERE"  # the real key is never put into this block (decision 0083)
ALREADY_MADE = ("A key was already made from this form. It cannot be shown again. "
                "Return to Helpers if you want to make another.")
OUT_OF_DATE = "This form is out of date, so no key was made. Please fill it in again."
FORMS_KEPT = 50  # open Add a helper forms remembered at once; older ones must be filled in again
NEW_KEY_FORMS_KEPT = 200  # open Make a new key buttons remembered at once (one per helper card shown)
ALREADY_CHANGED = ("A new key was already made from this button. It cannot be shown again. "
                   "Return to Helpers to make another new key if you did not copy it.")
NEW_KEY_OUT_OF_DATE = "This page is out of date, so no key was changed. Open Helpers and try again."
NOT_FINISHED = "Key change did not finish. Make a new key to reconnect."
CONNECTED_WITHIN = timedelta(minutes=10)  # "Connected from this computer" only after a key was used this recently
NO_ADDRESS_FILE = ("Dashboard Plus could not write its address file in this folder, so an assistant set up with "
                   "these settings cannot find it right now. Check the data folder, or use the current address "
                   "under Connection details.")
_forms_lock = threading.Lock()


def _forms() -> dict:
    """One-use tokens for Add a helper forms: a form makes at most one key, even if it is sent twice (0087)."""
    return current_app.config.setdefault("HELPER_FORMS", {"open": [], "used": []})


def _new_form_token() -> str:
    token = secrets.token_urlsafe(16)
    with _forms_lock:
        forms = _forms()
        forms["open"] = (forms["open"] + [token])[-FORMS_KEPT:]
    return token


def _spend_form_token(token: str) -> str | None:
    """None if this form may make a key now (and it is spent); otherwise the plain reason it may not."""
    with _forms_lock:
        forms = _forms()
        if token and token in forms["open"]:
            forms["open"].remove(token)
            forms["used"] = (forms["used"] + [token])[-FORMS_KEPT:]
            return None
        return ALREADY_MADE if token and token in forms["used"] else OUT_OF_DATE


def _give_back_form_token(token: str) -> None:
    """A refused key (a problem with the name or parts) leaves the form usable once it is corrected."""
    with _forms_lock:
        forms = _forms()
        if token in forms["used"]:
            forms["used"].remove(token)
        forms["open"] = (forms["open"] + [token])[-FORMS_KEPT:]


def _new_key_forms() -> dict:
    """One-use tokens for Make a new key buttons, each bound to one helper (decision 0093, like 0087)."""
    return current_app.config.setdefault("HELPER_NEW_KEY_FORMS", {"open": {}, "used": {}})


def _new_key_token(helper_id: int) -> str:
    token = secrets.token_urlsafe(16)
    with _forms_lock:
        forms = _new_key_forms()
        forms["open"][token] = helper_id
        while len(forms["open"]) > NEW_KEY_FORMS_KEPT:
            forms["open"].pop(next(iter(forms["open"])))
    return token


def _spend_new_key_token(token: str, helper_id: int) -> str | None:
    """None if this button may make a new key for this helper now (and it is spent); otherwise the reason."""
    with _forms_lock:
        forms = _new_key_forms()
        if token and forms["open"].get(token) == helper_id:
            del forms["open"][token]
            forms["used"][token] = helper_id
            while len(forms["used"]) > NEW_KEY_FORMS_KEPT:
                forms["used"].pop(next(iter(forms["used"])))
            return None
        return ALREADY_CHANGED if token and forms["used"].get(token) == helper_id else NEW_KEY_OUT_OF_DATE


def _address() -> str:
    return f"http://127.0.0.1:{current_app.config['PORT']}/api/v1"


def _address_file() -> str | None:
    """The full path of this data folder's address file, for the settings to paste (decision 0092)."""
    data_dir = current_app.config["DATA_DIR"]
    return str(helper_address.path(data_dir).resolve()) if data_dir is not None else None


def _connection() -> dict:
    """What the Connect an AI assistant section shows: the preferred settings and the manual ones."""
    address, address_file = _address(), _address_file()
    return {"address": address, "address_file": address_file,
            "assistant": assistant_settings(address_file=address_file) if address_file
            else assistant_settings(address),
            "manual": assistant_settings(address),
            # set by the server at start: None means the file could not be written (absent in tests)
            "address_file_problem": NO_ADDRESS_FILE if address_file and current_app.config.get(
                "HELPER_ADDRESS_RUN", "") is None else None}


def assistant_settings(address: str | None = None, address_file: str | None = None) -> str:
    """The settings to paste into an AI assistant's app (MCP), with a placeholder where the key goes.

    Given the address file, the connector reads Dashboard's current address from it for every call, so a
    restart needs no new copy (decision 0092). Given only an address, that address is used as it is.
    The command is the Python running Dashboard now, so it is right for the portable folder too. When the
    program is run from its source folder, that folder is added so the connector can be found."""
    where = {ADDRESS_FILE_VARIABLE: address_file} if address_file else {URL_VARIABLE: address}
    env = {**where, KEY_VARIABLE: KEY_PLACEHOLDER}
    package_home = Path(dashboard.__file__).resolve().parent.parent
    portable = any(Path(sys.executable).parent.glob("python3*._pth"))
    if not portable and "site-packages" not in package_home.parts:
        env["PYTHONPATH"] = str(package_home)
    block = {"mcpServers": {"dashboard-plus": {"command": sys.executable, "args": ["-m", "dashboard.connector"],
                                               "env": env}}}
    return json.dumps(block, indent=2)


def _starting_message(helper: helpers.Helper) -> str:
    """The starting message to paste into the assistant's chat (decision 0102): no records and never the key."""
    return helper_guide.guide_text(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"](),
                                   helper)


def _when(text: str | None) -> str | None:
    try:
        return datetime.fromisoformat(text).strftime("%d %b %Y").lstrip("0") if text else None
    except ValueError:
        return None


def _parts() -> list[dict]:
    """The modules a helper could be allowed to use: the ones switched on."""
    conn = current_app.config["CONNECT"]()
    on = settings.enabled_modules(conn)
    return [{"name": m.name, "title": m.title} for m in current_app.config["LOADED"] if m.name in on]


def _recent(text: str | None) -> bool:
    try:
        return bool(text) and datetime.now(timezone.utc) - datetime.fromisoformat(text) < CONNECTED_WITHIN
    except (TypeError, ValueError):
        return False


def _render(values: dict | None = None, error: str | None = None, status: int = 200,
            key_error: str | None = None):
    conn = current_app.config["CONNECT"]()
    parts = _parts()
    titles = {m.name: m.title for m in current_app.config["LOADED"]}
    rows = [{"id": h.id, "name": h.name, "access": ACCESS_WORDS[h.access], "active": h.active,
             "parts": ", ".join(titles.get(n, n) for n in h.modules), "made": _when(h.created_at),
             "last_used": _when(h.last_used_at) or "not yet", "off_at": _when(h.revoked_at),
             "key_changed": _when(h.rotated_at), "unfinished": h.key_unfinished,
             "connected": h.active and not h.key_unfinished and _recent(h.last_used_at),
             "new_key_token": _new_key_token(h.id) if h.active else None,
             "starting_message": _starting_message(h) if h.active else None}
            for h in helpers.all_helpers(conn)]
    turned_off = helpers.get(conn, request.args.get("off", 0, type=int)) if request.args.get("off") else None
    changed = helpers.get(conn, request.args.get("changed", 0, type=int)) if request.args.get("changed") else None
    if changed is not None and (changed.rotated_at is None or changed.key_unfinished):
        changed = None
    return render_template("helpers.html", rows=rows, parts=parts, values=values or {}, error=error,
                           key_error=key_error, turned_off=turned_off, form_token=_new_form_token(),
                           changed=changed, changed_on=_when(changed.rotated_at) if changed else None,
                           not_finished=NOT_FINISHED, key_shown=False, **_connection()), status


@helper_settings.get("/settings/helpers")
def helpers_page():
    return _render()


@helper_settings.post("/settings/helpers")
def make_key():
    conn = current_app.config["CONNECT"]()
    chosen = [m for m in request.form.getlist("modules") if m in {p["name"] for p in _parts()}]
    values = {"name": request.form.get("name", ""), "access": request.form.get("access", ""), "modules": chosen}
    token = request.form.get("form_token", "")
    refusal = _spend_form_token(token)
    if refusal:
        return _render(values if refusal == OUT_OF_DATE else None, refusal, 409)
    try:
        helper, key = helpers.issue(conn, current_app.config["DATA_DIR"], values["name"], values["access"], chosen)
    except PlainError as error:
        _give_back_form_token(token)
        return _render(values, str(error), 422)
    titles = {m.name: m.title for m in current_app.config["LOADED"]}
    # The key is shown in this one response, never in a redirect or an address, and never stored.
    return render_template("helper_key.html", helper=helper, key=key, can_suggest=helper.may_suggest,
                           parts=", ".join(titles.get(n, n) for n in helper.modules),
                           key_shown=True, starting_message=_starting_message(helper), **_connection()), 201


@helper_settings.post("/settings/helpers/<int:helper_id>/new-key")
def new_key(helper_id):
    """Make a new key for a helper, once per button (decision 0093). The old key stops; nothing else changes."""
    conn = current_app.config["CONNECT"]()
    helper = helpers.get(conn, helper_id)
    if helper is None:
        return redirect(url_for("helper_settings.helpers_page"))
    if not helper.active:
        return _render(key_error=helpers.HELPER_OFF, status=409)
    refusal = _spend_new_key_token(request.form.get("new_key_token", ""), helper_id)
    if refusal:
        return _render(key_error=refusal, status=409)
    try:
        helper, key = helpers.rotate(conn, current_app.config["DATA_DIR"], helper_id)
    except helpers.HelperOff as error:
        return _render(key_error=str(error), status=409)
    except helpers.KeyNotChanged as error:
        return _render(key_error=str(error), status=500)
    # Like a first key: shown in this one response only, never in a redirect, an address or a file.
    return render_template("helper_new_key.html", helper=helper, key=key, key_shown=True,
                           starting_message=_starting_message(helper), **_connection()), 201


@helper_settings.post("/settings/helpers/<int:helper_id>/turn-off")
def turn_off(helper_id):
    try:
        helpers.turn_off(current_app.config["CONNECT"](), current_app.config["DATA_DIR"], helper_id)
    except PlainError:
        return redirect(url_for("helper_settings.helpers_page"))
    return redirect(url_for("helper_settings.helpers_page", off=helper_id))
