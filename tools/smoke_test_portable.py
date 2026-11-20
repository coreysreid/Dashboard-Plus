"""Start the built portable folder or Mac app, check it answers, and close it safely."""
from __future__ import annotations

import http.cookiejar
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def wait_for(condition, seconds: float, step: float = 0.25) -> bool:
    """Poll `condition` until it is true or the time runs out."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(step)
    return False


OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def fetch(url: str, host: str | None = None) -> tuple[int, str]:
    """Return (status, body) for a GET request, keeping cookies like a browser.

    `host` forges the Host header, to check that such requests are refused.
    """
    request = urllib.request.Request(url, headers={"Host": host} if host else {})
    try:
        with OPENER.open(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        # Refusals (such as 403) still carry a page worth checking.
        return error.code, error.read().decode("utf-8", "replace")


def commands(folder: Path) -> tuple[list[str], list[str]]:
    """How to start the build, and how to run its bundled Python: (start, python).

    A Mac app (a folder ending in .app) is started through its own launcher, as Finder would; the
    launcher's failure window is turned off so a test machine never waits for a click."""
    if folder.suffix == ".app":
        python = [str(folder / "Contents" / "Resources" / "python" / "bin" / "python3"), "-I"]
        return [str(folder / "Contents" / "MacOS" / "Dashboard Plus")], python
    python = [str(folder / "app" / "python" / ("python.exe" if sys.platform == "win32" else "python"))]
    return python + ["-m", "dashboard"], python


def check_mac_default(python: list[str]) -> list[str]:
    """Inside a Mac app, the records' default home must be Application Support, outside the app."""
    found = subprocess.run(python + ["-c", "from dashboard import data_location as d; print(d.default_data_dir())"],
                           capture_output=True, text=True, timeout=60).stdout.strip()
    expected = str(Path.home() / "Library" / "Application Support" / "Dashboard Plus")
    if found != expected:
        return [f"the Mac app's default data folder was {found!r}, not {expected!r}"]
    return []


def run(folder: Path) -> list[str]:
    """Run the checks and return a list of failures (empty means it worked)."""
    start, python = commands(folder)
    failures: list[str] = []
    if folder.suffix == ".app" and sys.platform == "darwin":
        failures += check_mac_default(python)
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        process = subprocess.Popen(start + ["--data", str(data), "--no-browser"],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   env=dict(os.environ, DASHBOARD_PLUS_NO_ALERT="1"))
        state_path = data / "run" / "dashboard.json"
        try:
            if not wait_for(state_path.exists, 30):
                return ["the program did not start within 30 seconds"]
            state = json.loads(state_path.read_text(encoding="utf-8"))
            base = f"http://127.0.0.1:{state['port']}/"
            status, body = fetch(base)
            if status != 403 or "open Dashboard Plus from its shortcut" not in body:
                failures.append(f"a browser without the launch link was not turned away (got {status})")
            status, body = fetch(f"{base}?key={state['session']}")
            if status != 200 or "Welcome to Dashboard Plus" not in body:
                failures.append(f"the first-run wizard did not appear (got {status})")
            status, _ = fetch(base, host="evil.example")
            if status != 403:
                failures.append(f"a request naming another host was not refused (got {status})")
            close = subprocess.run(python + ["-m", "dashboard", "--data", str(data), "--close"],
                                   capture_output=True, text=True, timeout=60)
            if "Saved and closed" not in close.stdout:
                failures.append(f"close command said: {close.stdout.strip()}")
            try:
                code = process.wait(timeout=20)
                if code != 0:
                    failures.append(f"the program exited with code {code}")
            except subprocess.TimeoutExpired:
                failures.append("the program did not stop after a safe close")
            if state_path.exists():
                failures.append("the run file was left behind after closing")
        finally:
            if process.poll() is None:
                process.kill()
            output = process.communicate()[0] if process.stdout else ""
            print(output)
    return failures


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns 1 if any check fails."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python tools/smoke_test_portable.py <built folder, or the built Dashboard Plus.app>")
        return 2
    failures = run(Path(args[0]))
    if failures:
        print("Portable smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Portable smoke test passed: it started, showed the first-run wizard, turned away a browser "
          "without it, refused a forged host and saved and closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
