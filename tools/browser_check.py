"""Click through the real dashboard in Chromium (setup, dates, stock in, private details, closing) and fail loudly."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import load_example  # noqa: E402
from make_screenshots import wizard_steps  # noqa: E402
from dashboard.core import db, modules, records  # noqa: E402

DRIVER = ROOT / "tools" / "browser_check.js"
TIME_LIMIT = 120  # seconds for one browser run; the whole check normally takes about 20

# The made-up records each run relies on (examples/households). Change these if the examples change.
AU = {"household": "smith", "locale": "en-AU", "timezone": "Australia/Sydney",
      "dates": {"item": "Browser check tins", "typed": "20/05/27", "words": "20 May 2027",
                "wrongOrder": "05/20/27", "hint": "Use DD/MM/YY"},
      "stock": {"item": "Kidney beans", "batches": 2, "blankAdds": "Start a new batch",
                "blankTakes": "Use the batch with the earliest use-by date"},
      "private": {"person": "Emily Smith", "secret": "Peanut allergy"}}
US = {"household": "garcia", "locale": "en-US", "timezone": "America/Los_Angeles",
      "dates": {"item": "Browser check tins", "typed": "05/20/27", "words": "May 20, 2027",
                "wrongOrder": "20/05/27", "hint": "Use MM/DD/YY"}}


class CheckFailed(Exception):
    """A step in the browser did not work; the message says which, in plain words."""


def unavailable() -> str | None:
    """Why the check cannot run on this computer (no Node, Playwright or Chromium), or None if it can."""
    if not shutil.which("node"):
        return "Node.js is not installed."
    probe = ("const fs=require('fs');let p;try{p=require('playwright')}catch(e){console.log('no-playwright');"
             "process.exit(0)}console.log(fs.existsSync(p.chromium.executablePath())?'ready':'no-chromium')")
    try:
        found = subprocess.run(["node", "-e", probe], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return "Node.js did not answer."
    if found == "no-playwright":
        return "The Playwright package for Node.js is not installed."
    if found != "ready":
        return "Playwright's Chromium is not installed (npx playwright install chromium)."
    return None


def server_env(work: Path) -> dict:
    """The server's settings: our code, and a throwaway home so no backup lands in the real one."""
    home = work / "home"
    home.mkdir(exist_ok=True)
    return dict(os.environ, PYTHONPATH=str(ROOT / "src"), HOME=str(home), USERPROFILE=str(home),
                LOCALAPPDATA=str(home / "AppData" / "Local"))


def start_server(data_dir: Path, env: dict) -> tuple[subprocess.Popen, str, str]:
    """Start the real program on a data folder; return it, its address and the launch link's path."""
    log = data_dir.parent / "server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "wb") as out:  # a file, not a pipe, so a chatty server can never fill it and stall
        process = subprocess.Popen([sys.executable, "-m", "dashboard", "--data", str(data_dir), "--no-browser"],
                                   cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT)
    state = data_dir / "run" / "dashboard.json"
    for _ in range(300):
        if state.exists():
            try:
                run = json.loads(state.read_text(encoding="utf-8"))
            except ValueError:  # still being written
                time.sleep(0.05)
                continue
            return process, f"http://127.0.0.1:{run['port']}", f"/?key={run['session']}"
        if process.poll() is not None:
            break
        time.sleep(0.1)
    process.kill()
    raise CheckFailed("The dashboard did not start:\n" + log.read_text(errors="replace")[-1500:])


def stop_server(process: subprocess.Popen, closed: bool) -> None:
    """After "Save and exit" the program must stop by itself; otherwise it is stopped here."""
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        if closed:
            raise CheckFailed("The program was still running 20 seconds after Save and exit.") from None


def drive(plan: dict, work: Path, phase: str) -> list[str]:
    """Run one browser phase; return its "ok ..." lines, or raise CheckFailed with the browser's words."""
    path = work / f"{plan['locale']}-{phase}.json"
    path.write_text(json.dumps(dict(plan, phase=phase)), encoding="utf-8")
    try:
        result = subprocess.run(["node", str(DRIVER), str(path)], cwd=ROOT, capture_output=True, text=True,
                                timeout=TIME_LIMIT)
    except subprocess.TimeoutExpired:
        raise CheckFailed(f"The browser ({plan['locale']}, {phase}) took more than {TIME_LIMIT} seconds.") from None
    lines = result.stdout.splitlines()
    if result.returncode != 0:
        said = "\n".join(line for line in lines if not line.startswith("ok ")) or result.stderr.strip()[-1500:]
        raise CheckFailed(f"In the browser ({plan['locale']}): " + said.removeprefix("FAILED: "))
    return [line for line in lines if line.startswith("ok ")]


def run_au(work: Path, executable: str | None) -> list[str]:
    """Australia: answer the setup wizard in the browser, add the Smiths' records, then check everything."""
    example = load_example.read(AU["household"])
    data_dir = work / "au" / "data"
    process, base, launch = start_server(data_dir, server_env(work))
    plan = {"base": base, "launch": launch, "locale": AU["locale"], "timezone": AU["timezone"],
            "executablePath": executable}
    closed = False
    try:
        done = drive(dict(plan, wizard=wizard_steps(example["setup"])), work, "setup")
        conn = db.connect(data_dir / "dashboard.db")
        try:
            found, _ = modules.discover(ROOT / "modules")
            load_example.load_records(conn, records.build_registry(found), example)
        finally:
            conn.close()
        done += drive(dict(plan, dates=AU["dates"], stock=AU["stock"], private=AU["private"]), work, "main")
        closed = True
    finally:
        stop_server(process, closed)
    return done


def run_us(work: Path, executable: str | None) -> list[str]:
    """United States: the Garcias, loaded directly, type and read dates month first."""
    data_dir = work / "us" / "data"
    load_example.load(US["household"], data_dir)
    process, base, launch = start_server(data_dir, server_env(work))
    closed = False
    try:
        done = drive({"base": base, "launch": launch, "locale": US["locale"], "timezone": US["timezone"],
                      "executablePath": executable, "dates": US["dates"]}, work, "main")
        closed = True
    finally:
        stop_server(process, closed)
    return done


def check(executable: str | None = None, us: bool = True) -> list[str]:
    """Run every browser check; return what passed, or raise CheckFailed at the first failure."""
    with tempfile.TemporaryDirectory(prefix="dashboard-browser-check-") as tmp:
        done = run_au(Path(tmp), executable)
        if us:
            done += run_us(Path(tmp), executable)
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", help="a Chromium executable, if Playwright cannot find its own")
    parser.add_argument("--au-only", action="store_true", help="skip the United States (month first) run")
    args = parser.parse_args(argv)
    reason = unavailable() if not args.browser else None
    if reason:
        print(f"Cannot run the browser check: {reason}")
        return 2
    started = time.monotonic()
    try:
        done = check(args.browser, us=not args.au_only)
    except CheckFailed as failure:
        print(f"FAIL  {failure}")
        return 1
    for line in done:
        print("PASS  " + line.removeprefix("ok "))
    print(f"\nThe browser check passed ({len(done)} checks, {time.monotonic() - started:.0f} seconds).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
