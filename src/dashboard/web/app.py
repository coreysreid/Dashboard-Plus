"""Build the Flask web application and its local-only protections."""
from __future__ import annotations

import hmac
import logging
import platform
import secrets
from datetime import datetime
from pathlib import Path
from typing import Callable

from flask import Flask, abort, g, jsonify, redirect, render_template, request

from dashboard import __version__
from dashboard.core import db, records
from dashboard.core.startup import database_path

log = logging.getLogger("dashboard.web")
SESSION_COOKIE = "dashboard_session"
# Paths that work without the session cookie: the health check, the safe-close
# call (which has its own token), and the page that explains how to get in.
OPEN_PATHS = {"/api/ping", "/api/shutdown", "/start"}


def create_app(shutdown_token: str, on_shutdown: Callable[[], None], report=None,
               data_dir: Path | None = None, session_key: str | None = None) -> Flask:
    """Return the web app.

    - `on_shutdown` is called when a safe close is requested.
    - `report` is the start-up report (database version, modules and their problems).
    - `data_dir` is the data folder; pages that read records need it.
    - `session_key` is the secret in the launch link. The browser exchanges it for a
      cookie, so only the browser opened by *Open Dashboard* can use the pages.
    """
    app = Flask(__name__)
    app.config["PORT"] = None  # set by the server once it knows its port
    app.config["SESSION_KEY"] = session_key or secrets.token_urlsafe(32)
    app.config["CSRF_TOKEN"] = secrets.token_urlsafe(32)
    app.config["DATA_DIR"] = Path(data_dir) if data_dir else None
    app.config["REPORT"] = report
    app.config["REGISTRY"] = records.build_registry(report.loaded if report else [])

    def allowed_hosts() -> set[str]:
        port = app.config["PORT"]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    @app.before_request
    def only_this_computer():
        # Refuse requests that name another host. This blocks "DNS rebinding",
        # where a web page tries to reach this program through a fake address.
        if request.host not in allowed_hosts():
            abort(403)
        # Writes must come from our own pages, not from another website.
        if request.method == "POST":
            origin = request.headers.get("Origin")
            if origin and origin.split("://", 1)[-1] not in allowed_hosts():
                abort(403)
        if request.path in OPEN_PATHS or request.path.startswith("/static/"):
            return None
        # The launch link carries the key once; swap it for a cookie and tidy the address.
        key = request.args.get("key")
        if key is not None:
            if not hmac.compare_digest(key, app.config["SESSION_KEY"]):
                return redirect("/start")
            response = redirect(request.path)
            response.set_cookie(SESSION_COOKIE, app.config["SESSION_KEY"], httponly=True, samesite="Strict")
            return response
        cookie = request.cookies.get(SESSION_COOKIE, "")
        if not hmac.compare_digest(cookie, app.config["SESSION_KEY"]):
            return redirect("/start")
        if request.method == "POST" and not request.path.startswith("/api/"):
            supplied = request.form.get("_csrf", "")
            if not hmac.compare_digest(supplied, app.config["CSRF_TOKEN"]):
                abort(400)
        return None

    @app.context_processor
    def shared_values():
        return {"csrf_token": app.config["CSRF_TOKEN"], "version": __version__}

    def connection():
        if "db" not in g:
            g.db = db.connect(database_path(app.config["DATA_DIR"]))
        return g.db

    app.config["CONNECT"] = connection

    @app.teardown_appcontext
    def close_connection(_error):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.get("/start")
    def start():
        return render_template("start.html"), 403

    @app.get("/")
    def home():
        tables = []
        if app.config["DATA_DIR"] is not None and app.config["REGISTRY"]:
            from dashboard.web.display import table_title
            store = records.Records(connection(), app.config["REGISTRY"])
            for name, info in app.config["REGISTRY"].items():
                tables.append({"name": name, "title": table_title(info), "module": info.module.title,
                               "count": store.count(name)})
        return render_template("home.html", report=report, tables=tables)

    @app.get("/close")
    def close_page():
        return render_template("close.html", token=shutdown_token)

    @app.get("/api/ping")
    def ping():
        return jsonify(ok=True, version=__version__)

    @app.post("/api/shutdown")
    def shutdown():
        supplied = request.headers.get("X-Shutdown-Token") or request.form.get("token", "")
        if not hmac.compare_digest(supplied, shutdown_token):
            abort(403)
        on_shutdown()
        if request.form:
            return render_template("closed.html")
        return jsonify(ok=True)

    @app.post("/report")
    def save_report():
        path = write_report(app.config["DATA_DIR"])
        return render_template("report.html", path=path)

    from dashboard.web.pages import pages
    app.register_blueprint(pages)

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template("error.html", message="That form had expired. Go back, reload the page and try again."), 400

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", message="This request was refused because it did not come from this computer."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="That page does not exist."), 404

    @app.errorhandler(Exception)
    def unexpected(error):
        log.exception("Unexpected error", exc_info=error)
        return render_template("error.html", can_report=True,
                               message="Something went wrong. Your data is safe. "
                                       "You can save a report to share with whoever helps you."), 500

    return app


def write_report(data_dir: Path | None) -> Path | None:
    """Save a short report (version, system and the end of the log) to share for help.

    The log records what the program did, never the values people typed.
    """
    if data_dir is None:
        return None
    log_path = Path(data_dir) / "logs" / "dashboard.log"
    tail = ""
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-200:])
    reports = Path(data_dir) / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"report-{datetime.now():%Y%m%d-%H%M%S}.txt"
    path.write_text(
        f"Dashboard Plus {__version__}\nSystem: {platform.system()} {platform.release()}\n"
        f"Python: {platform.python_version()}\n\nRecent log:\n{tail}\n", encoding="utf-8")
    return path
