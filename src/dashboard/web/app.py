"""Build the Flask web application and its local-only protections."""
from __future__ import annotations

import hmac
import logging
import platform
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from flask import Flask, abort, g, jsonify, redirect, render_template, request
from werkzeug.exceptions import HTTPException

from dashboard import __version__
from dashboard.core import backups, db, proposals, questions, records, watch
from dashboard.core.startup import database_path
from dashboard.web.api import QUEUE_LIMIT_KEY, REQUESTS_PER_MINUTE, api_error
from dashboard.web.questions import REVIEW_WORDS

log = logging.getLogger("dashboard.web")
SESSION_COOKIE = "dashboard_session"
# Paths that work without the session cookie: the health check, the safe-close
# call (which has its own token), and the page that explains how to get in.
OPEN_PATHS = {"/api/ping", "/api/shutdown", "/start"}


def create_app(shutdown_token: str, on_shutdown: Callable[[], None], report=None,
               data_dir: Path | None = None, session_key: str | None = None,
               extra_backup_dir: Path | None = None) -> Flask:
    """Return the web app.

    - `on_shutdown` is called when a safe close is requested.
    - `report` is the start-up report (database version, modules and their problems).
    - `data_dir` is the data folder; pages that read records need it.
    - `session_key` is the secret in the launch link. The browser exchanges it for a
      cookie, so only the browser opened by *Open Dashboard* can use the pages.
    - `extra_backup_dir` is the second backup folder on this computer, or None; the restore page lists it.
    """
    app = Flask(__name__)
    from dashboard.web.csv_import import UploadRequest
    app.request_class = UploadRequest  # import uploads stay in memory; other requests are unchanged
    app.config["PORT"] = None  # set by the server once it knows its port
    app.config["SESSION_KEY"] = session_key or secrets.token_urlsafe(32)
    app.config["CSRF_TOKEN"] = secrets.token_urlsafe(32)
    app.config["DATA_DIR"] = Path(data_dir) if data_dir else None
    app.config["EXTRA_BACKUP_DIR"] = Path(extra_backup_dir) if extra_backup_dir else None
    app.config["REPORT"] = report
    app.config["LOADED"] = report.loaded if report else []
    app.config["HELPER_REQUESTS_PER_MINUTE"] = REQUESTS_PER_MINUTE  # tests may lower it (decision 0074)
    app.config[QUEUE_LIMIT_KEY] = proposals.MAX_WAITING  # suggestions per helper waiting on Review (decision 0085)
    app.config["TODAY"] = date.today  # what day it is for questions coming back; tests may set another day

    def allowed_hosts() -> set[str]:
        port = app.config["PORT"]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    @app.before_request
    def only_this_computer():
        # Refuse requests that name another host. This blocks "DNS rebinding",
        # where a web page tries to reach this program through a fake address.
        if request.host not in allowed_hosts():
            abort(403)
        # The helper API has its own rules (a key, no web pages, JSON only; see web/api.py and decision 0067).
        # Everything else below applies, exactly as before, to every other path.
        if request.path.startswith("/api/v1/"):
            from dashboard.web.api import authenticate
            return authenticate()
        if request.path.startswith("/api/") and request.path not in OPEN_PATHS:
            # Any other API address (such as /api/v2/me) is a plain refusal, never a page (Lane B, batch 14 item 56).
            return api_error(404, "not_found", "There is no such helper address. Helpers use /api/v1/.")
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
        # Every write from a page needs this page's own token. Only /api/v1/ is exempt, because it has no pages
        # or cookies: it checks a helper's key instead (above).
        if request.method == "POST":
            supplied = request.form.get("_csrf", "")
            if not hmac.compare_digest(supplied, app.config["CSRF_TOKEN"]):
                abort(400)
        # Until the first-run questions are answered, the home page leads to them.
        if request.path == "/" and app.config["DATA_DIR"] is not None:
            from dashboard.core import settings
            if not settings.get(connection(), "setup.done", False):
                return redirect("/setup")
        return None

    def waiting_suggestions() -> int:
        """How many helper suggestions wait for a decision (shown beside "Review" on every page)."""
        if app.config["DATA_DIR"] is None:
            return 0
        if not hmac.compare_digest(request.cookies.get(SESSION_COOKIE, ""), app.config["SESSION_KEY"]):
            return 0  # not signed in (for example the "how to get in" page): show nothing about the household
        try:
            return proposals.pending_count(connection())
        except sqlite3.Error:
            return 0

    def helpers_with_access() -> int:
        """How many helpers can connect now, shown in the mode badge on every page (decision 0082)."""
        if app.config["DATA_DIR"] is None:
            return 0
        if not hmac.compare_digest(request.cookies.get(SESSION_COOKIE, ""), app.config["SESSION_KEY"]):
            return 0
        try:
            return connection().execute("SELECT COUNT(*) FROM core__helpers WHERE revoked_at IS NULL").fetchone()[0]
        except sqlite3.Error:
            return 0

    @app.context_processor
    def shared_values():
        return {"csrf_token": app.config["CSRF_TOKEN"], "version": __version__, "review_count": waiting_suggestions(),
                "helper_count": helpers_with_access()}

    def connection():
        if "db" not in g:
            # Each request's connection passes the data file's gate, so a restore can wait until none is open
            # before it swaps the file (decision 0079).
            path = database_path(app.config["DATA_DIR"])
            gate = db.gate(path)
            gate.enter()
            try:
                g.db = db.connect(path)
            except BaseException:
                gate.leave()
                raise
            g.db_gate = gate
        return g.db

    def release_connection():
        """Close this request's connection now, instead of at the end of the request."""
        conn, gate = g.pop("db", None), g.pop("db_gate", None)
        if conn is not None:
            conn.close()
        if gate is not None:
            gate.leave()

    app.config["CONNECT"] = connection
    app.config["RELEASE"] = release_connection

    def registry():
        """Tables of the modules that are switched on, worked out once per request."""
        if "registry" not in g:
            loaded = app.config["LOADED"]
            if loaded and app.config["DATA_DIR"] is not None:
                from dashboard.core import settings
                on = settings.enabled_modules(connection())
                loaded = [m for m in loaded if m.name in on]
                while True:  # a module whose required module is switched off is off too
                    names = {m.name for m in loaded}
                    kept = [m for m in loaded if all(r in names for r in m.requires)]
                    if len(kept) == len(loaded):
                        break
                    loaded = kept
            g.registry = records.build_registry(loaded)
        return g.registry

    app.config["REGISTRY_FOR_REQUEST"] = registry

    @app.teardown_appcontext
    def close_connection(_error):
        release_connection()

    @app.get("/start")
    def start():
        return render_template("start.html"), 403

    @app.get("/")
    def home():
        groups, attention, last_backup, asked, my_home, to_do = [], None, None, [], None, None
        daily_cards = []  # food put out today, one line per pet (decision 0110)
        if app.config["DATA_DIR"] is not None:
            last_backup = backups.latest(app.config["DATA_DIR"])
        if app.config["DATA_DIR"] is not None and registry():
            from dashboard.web.home import home_groups
            from dashboard.web.sheets import available_sheets
            conn = connection()
            groups = home_groups(registry(), records.Records(conn, registry()).count, available_sheets(registry()))
            attention = {"low": watch.running_low(conn, registry()), "expiring": watch.expiring(conn, registry()),
                         "supplies": watch.supplies(conn, registry()),
                         "gaps": watch.gaps(conn, registry())}
            asked = questions.next_up(conn, registry(), today=app.config["TODAY"]())
            from dashboard.web.home_setup import summary
            my_home = summary(conn, registry())
            from dashboard.web.checklist import home_summary
            to_do = home_summary(conn, registry(), app.config["TODAY"]())
            from dashboard.web.daily_pages import home_cards
            daily_cards = home_cards(conn, registry(), app.config["NOW"]() if app.config.get("NOW") else None)
        from dashboard.web.setup import backup_report
        tables = [t for group in groups for t in group["main"] + group["more"]]
        return render_template("home.html", report=report, groups=groups, tables=tables, attention=attention,
                               last_backup=last_backup, backup=backup_report(app.config["DATA_DIR"]),
                               suggestions=waiting_suggestions(), asked=asked,
                               review_words=REVIEW_WORDS, my_home=my_home, to_do=to_do,
                               daily_cards=daily_cards)

    @app.get("/attention")
    def attention_page():
        conn, tables = connection(), registry()
        return render_template("attention.html", low=watch.running_low(conn, tables),
                               expiring=watch.expiring(conn, tables), supplies=watch.supplies(conn, tables),
                               gaps=watch.gaps(conn, tables), household=watch.household(conn, tables),
                               asked=questions.next_up(conn, tables, limit=3, today=app.config["TODAY"]()),
                               review_words=REVIEW_WORDS)

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

    from dashboard.web.api import helper_api
    from dashboard.web.checklist import checklist_pages
    from dashboard.web.export_page import export_pages
    from dashboard.web.csv_import import imports
    from dashboard.web.helper_settings import helper_settings
    from dashboard.web.home_setup import home_setup
    from dashboard.web.pages import pages
    from dashboard.web.questions import question_pages
    from dashboard.web.restore import restore_pages
    from dashboard.web.receipt_line import line_pages
    from dashboard.web.review import review_pages
    from dashboard.web.setup import setup_pages
    from dashboard.web.sheets import sheet_pages
    app.register_blueprint(pages)
    app.register_blueprint(sheet_pages)
    app.register_blueprint(setup_pages)
    app.register_blueprint(home_setup)
    app.register_blueprint(helper_settings)
    app.register_blueprint(export_pages)
    app.register_blueprint(imports)
    app.register_blueprint(review_pages)
    app.register_blueprint(line_pages)
    app.register_blueprint(restore_pages)
    app.register_blueprint(helper_api)
    app.register_blueprint(question_pages)
    app.register_blueprint(checklist_pages)
    from dashboard.web.moves_pages import moves_pages  # one reminder per policy (decision 0117)
    app.register_blueprint(moves_pages)
    from dashboard.web.chart_pages import chart_pages
    app.register_blueprint(chart_pages)
    from dashboard.web.daily_pages import daily_pages
    app.register_blueprint(daily_pages)
    from dashboard.web.calendar_pages import calendar_pages  # month calendars (decision 0119)
    app.register_blueprint(calendar_pages)
    from dashboard.web.bar_pages import bar_pages  # bars over time (decision 0124)
    app.register_blueprint(bar_pages)
    from dashboard.web.timeline_pages import timeline_pages  # one record's timeline (decision 0126)
    app.register_blueprint(timeline_pages)
    from dashboard.web.bring_in import bring_in_pages  # earlier entries from a spreadsheet (decision 0137)
    app.register_blueprint(bring_in_pages)
    from dashboard.web.drills import drill_pages
    app.register_blueprint(drill_pages)
    from dashboard.web.exit_sketch import exit_pages
    app.register_blueprint(exit_pages)

    def for_helpers() -> bool:
        return request.path.startswith("/api/v1/")

    @app.errorhandler(400)
    def bad_request(_error):
        if for_helpers():
            return api_error(400, "bad_request", "This request could not be read. Check the fields and try again.")
        return render_template("error.html", message="That form had expired. Go back, reload the page and try again."), 400

    @app.errorhandler(403)
    def forbidden(_error):
        if for_helpers():
            return api_error(403, "forbidden", "This request was refused because it did not come from this computer.")
        return render_template("error.html", message="This request was refused because it did not come from this computer."), 403

    @app.errorhandler(404)
    def not_found(_error):
        if for_helpers():
            return api_error(404, "not_found", "That table or record could not be found.")
        return render_template("error.html", message="That page does not exist."), 404

    @app.after_request
    def private_pages(response):
        # Household pages are private: never kept in the browser's cache, never shown inside another site.
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # "same-origin" tells other sites nothing about where a link came from, yet lets our own forms say
        # they came from here. With "no-referrer" current browsers send "Origin: null" and every save is refused.
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.errorhandler(HTTPException)
    def refused(error):
        if for_helpers():
            code = {405: "method_not_allowed", 413: "too_large", 415: "needs_json"}.get(error.code, "refused")
            message = {413: "This request is too large. Send fewer suggestions at a time.",
                       405: "That is not a way to use this address."}.get(error.code, "That request was refused.")
            return api_error(error.code or 400, code, message)
        # Ordinary refusals (wrong method, bad request) are not crashes: no error report, the right code.
        return render_template("error.html", message=error.description or "That request was refused."), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        log.exception("Unexpected error", exc_info=error)
        if for_helpers():
            return api_error(500, "server_error", "Something went wrong. Nothing was changed.")
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
