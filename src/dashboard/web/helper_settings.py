"""Settings, Helpers: give an assistant a key, choose what it may do, and turn its access off."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, url_for

import dashboard
from dashboard.connector.config import KEY_VARIABLE, URL_VARIABLE
from dashboard.core import helpers, settings
from dashboard.errors import PlainError

helper_settings = Blueprint("helper_settings", __name__)
ACCESS_WORDS = {"read": "May look", "suggest": "May look and suggest"}
KEY_PLACEHOLDER = "YOUR-KEY-HERE"  # the real key is never put into this block (decision 0083)


def _address() -> str:
    return f"http://127.0.0.1:{current_app.config['PORT']}/api/v1"


def assistant_settings(address: str) -> str:
    """The settings to paste into an AI assistant's app (MCP), with a placeholder where the key goes.

    The command is the Python running Dashboard now, so it is right for the portable folder too. When the
    program is run from its source folder, that folder is added so the connector can be found."""
    env = {URL_VARIABLE: address, KEY_VARIABLE: KEY_PLACEHOLDER}
    package_home = Path(dashboard.__file__).resolve().parent.parent
    portable = any(Path(sys.executable).parent.glob("python3*._pth"))
    if not portable and "site-packages" not in package_home.parts:
        env["PYTHONPATH"] = str(package_home)
    block = {"mcpServers": {"dashboard-plus": {"command": sys.executable, "args": ["-m", "dashboard.connector"],
                                               "env": env}}}
    return json.dumps(block, indent=2)


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


def _render(values: dict | None = None, error: str | None = None, status: int = 200):
    conn = current_app.config["CONNECT"]()
    parts = _parts()
    titles = {m.name: m.title for m in current_app.config["LOADED"]}
    rows = [{"id": h.id, "name": h.name, "access": ACCESS_WORDS[h.access], "active": h.active,
             "parts": ", ".join(titles.get(n, n) for n in h.modules), "made": _when(h.created_at),
             "last_used": _when(h.last_used_at) or "not yet", "off_at": _when(h.revoked_at)}
            for h in helpers.all_helpers(conn)]
    turned_off = helpers.get(conn, request.args.get("off", 0, type=int)) if request.args.get("off") else None
    address = _address()
    return render_template("helpers.html", rows=rows, parts=parts, values=values or {}, error=error,
                           address=address, turned_off=turned_off,
                           assistant=assistant_settings(address)), status


@helper_settings.get("/settings/helpers")
def helpers_page():
    return _render()


@helper_settings.post("/settings/helpers")
def make_key():
    conn = current_app.config["CONNECT"]()
    chosen = [m for m in request.form.getlist("modules") if m in {p["name"] for p in _parts()}]
    values = {"name": request.form.get("name", ""), "access": request.form.get("access", ""), "modules": chosen}
    try:
        helper, key = helpers.issue(conn, current_app.config["DATA_DIR"], values["name"], values["access"], chosen)
    except PlainError as error:
        return _render(values, str(error), 422)
    titles = {m.name: m.title for m in current_app.config["LOADED"]}
    # The key is shown in this one response, never in a redirect or an address, and never stored.
    return render_template("helper_key.html", helper=helper, key=key, can_suggest=helper.may_suggest,
                           parts=", ".join(titles.get(n, n) for n in helper.modules),
                           address=_address(), assistant=assistant_settings(_address())), 201


@helper_settings.post("/settings/helpers/<int:helper_id>/turn-off")
def turn_off(helper_id):
    try:
        helpers.turn_off(current_app.config["CONNECT"](), current_app.config["DATA_DIR"], helper_id)
    except PlainError:
        return redirect(url_for("helper_settings.helpers_page"))
    return redirect(url_for("helper_settings.helpers_page", off=helper_id))
