"""Start the built portable folder, check it answers, and close it safely."""
from __future__ import annotations

import http.cookiejar
import json
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


def run(folder: Path) -> list[str]:
    """Run the checks and return a list of failures (empty means it worked)."""
    python = folder / "app" / "python" / ("python.exe" if sys.platform == "win32" else "python")
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "data"
        process = subprocess.Popen([str(python), "-m", "dashboard", "--data", str(data), "--no-browser"],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
            close = subprocess.run([str(python), "-m", "dashboard", "--data", str(data), "--close"],
                                   capture_output=True, text=True, timeout=60)
            if "closed safely" not in close.stdout:
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
        print("Usage: python tools/smoke_test_portable.py <built folder>")
        return 2
    failures = run(Path(args[0]))
    if failures:
        print("Portable smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Portable smoke test passed: it started, showed the first-run wizard, turned away a browser "
          "without it, refused a forged host and closed safely.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
