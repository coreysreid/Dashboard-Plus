"""Start and stop the local web server, and remember how to reach it."""
from __future__ import annotations

import json
import logging
import os
import secrets
import threading
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from waitress import create_server

from dashboard.core import startup
from dashboard.web.app import create_app

HOST = "127.0.0.1"
log = logging.getLogger("dashboard.server")


@dataclass
class RunState:
    """What a second copy of the program needs to find or close the running one."""
    port: int
    token: str
    pid: int

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}/"


def state_file(data_dir: Path) -> Path:
    """Where the running program records its port and close token."""
    return Path(data_dir) / "run" / "dashboard.json"


def read_state(data_dir: Path) -> RunState | None:
    """Return the recorded run state, or None if there is none or it is unreadable."""
    try:
        raw = json.loads(state_file(data_dir).read_text(encoding="utf-8"))
        return RunState(port=int(raw["port"]), token=str(raw["token"]), pid=int(raw["pid"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def is_responding(state: RunState, timeout: float = 1.0) -> bool:
    """True if a dashboard is answering at the recorded port."""
    try:
        with urllib.request.urlopen(state.url + "api/ping", timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def setup_logging(data_dir: Path) -> logging.Handler:
    """Send technical details to a log file in the data folder, never to the screen.

    The caller must pass the returned handler to `release_logging` when it stops,
    so the file is closed and the drive can be unplugged (or the folder deleted).
    """
    logs = Path(data_dir) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(logs / "dashboard.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return handler


def release_logging(handler: logging.Handler) -> None:
    """Stop writing to the log file and close it."""
    logging.getLogger().removeHandler(handler)
    handler.close()


def serve(data_dir: Path, open_browser: bool = True, ready: threading.Event | None = None,
          modules_dir: Path | None = None) -> None:
    """Run the dashboard until a safe close is requested. Blocks until then."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    handler = setup_logging(data_dir)
    try:
        _serve(data_dir, open_browser, ready, modules_dir)
    finally:
        release_logging(handler)


def _serve(data_dir: Path, open_browser: bool, ready: threading.Event | None,
           modules_dir: Path | None) -> None:
    existing = read_state(data_dir)
    if existing and is_responding(existing):
        print("Dashboard is already open. Opening it in your browser.")
        if open_browser:
            webbrowser.open(existing.url)
        if ready:
            ready.set()
        return

    report = startup.prepare(data_dir, modules_dir)
    token = secrets.token_urlsafe(32)
    stopping = threading.Event()
    holder: dict[str, object] = {}

    def request_shutdown() -> None:
        stopping.set()
        # Close from another thread so the current reply can finish first.
        threading.Timer(0.3, lambda: holder["server"].close()).start()

    app = create_app(token, request_shutdown, report)
    server = create_server(app, host=HOST, port=0, threads=4)
    holder["server"] = server
    port = int(server.effective_port)
    app.config["PORT"] = port
    state = RunState(port=port, token=token, pid=os.getpid())

    path = state_file(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"port": port, "token": token, "pid": state.pid}), encoding="utf-8")
    log.info("Dashboard started on %s", state.url)

    print("Dashboard Plus is running.")
    print(f"It is open in your browser at {state.url}")
    print("Keep this window open. To stop, use 'Close Dashboard safely'.")
    if open_browser:
        webbrowser.open(state.url)
    if ready:
        ready.set()
    try:
        server.run()
    except (OSError, ValueError):
        # Closing the listening socket ends the loop with an error on some systems.
        if not stopping.is_set():
            raise
    finally:
        try:
            path.unlink()
        except OSError:
            pass
        log.info("Dashboard stopped")
    print("Dashboard closed safely. You can unplug the drive now.")


def close_running(data_dir: Path, timeout: float = 10.0) -> bool:
    """Ask a running dashboard to close safely. Returns True if one was closed."""
    state = read_state(data_dir)
    if not state or not is_responding(state):
        return False
    request = urllib.request.Request(
        state.url + "api/shutdown", method="POST", headers={"X-Shutdown-Token": state.token}
    )
    with urllib.request.urlopen(request, timeout=timeout):
        pass
    deadline = timeout
    step = 0.2
    while deadline > 0 and is_responding(state, timeout=step):
        threading.Event().wait(step)
        deadline -= step
    return True
