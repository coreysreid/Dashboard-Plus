"""Build the Flask web application and its local-only protections."""
from __future__ import annotations

import hmac
import logging
from typing import Callable

from flask import Flask, abort, jsonify, render_template, request

from dashboard import __version__

log = logging.getLogger("dashboard.web")


def create_app(shutdown_token: str, on_shutdown: Callable[[], None], report=None) -> Flask:
    """Return the web app. `on_shutdown` is called when a safe close is requested.

    `report` is the start-up report (database version, modules, module problems).
    """
    app = Flask(__name__)
    app.config["PORT"] = None  # set by the server once it knows its port

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

    @app.get("/")
    def home():
        return render_template("home.html", version=__version__, report=report)

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

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", message="This request was refused because it did not come from this computer."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="That page does not exist."), 404

    @app.errorhandler(Exception)
    def unexpected(error):
        log.exception("Unexpected error", exc_info=error)
        return render_template("error.html", message="Something went wrong. Your data is safe. Details were written to the log file."), 500

    return app
