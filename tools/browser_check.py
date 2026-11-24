"""Click through the real dashboard in Chromium (setup, Set up my home, dates, stock in, stocktake, Mark returned, Mark done, Things to do, spreadsheet import, Review keys and buttons, readiness questions, Think it through drills, charts, the way-out sketch, pet feeding at 320px, vehicle running log, Bills and a moved car insurance reminder, Utilities with Our home off, private details, closing) and fail loudly."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import load_example  # noqa: E402
from make_screenshots import wizard_steps  # noqa: E402
from dashboard.core import db, helpers, modules, proposals, records  # noqa: E402

DRIVER = ROOT / "tools" / "browser_check.js"
TIME_LIMIT = 120  # seconds for one browser run; the whole check normally takes about 20

# The made-up records each run relies on (examples/households). Change these if the examples change.
AU = {"household": "smith", "locale": "en-AU", "timezone": "Australia/Sydney",
      "dates": {"item": "Browser check tins", "typed": "20/05/27", "words": "20 May 2027",
                "wrongOrder": "05/20/27", "hint": "Use DD/MM/YY"},
      "stock": {"item": "Kidney beans", "batches": 2, "blankAdds": "Start a new batch",
                "blankTakes": "Use the batch with the earliest use-by date"},
      "private": {"person": "Emily Smith", "secret": "Peanut allergy"},
      "loan": {"name": "Cordless drill, lent to Dave Wilson"},
      "job": {"name": "Clean the gutters", "next": "20/05/27"},
      "routine": {"name": "Put the bins out"},  # late by three days: shown once as "Due since" (decision 0107)
      # A made-up spreadsheet: a byte order mark, CRLF, a quoted note with a comma and a line break, a bad date.
      "csv": {"file": "browser-check.csv", "ready": 2, "fixing": 1, "item": "Browser import rice",
              "note": "Top shelf, left\nbehind the flour",
              "text": "\ufeffName,Keep at least,Use by,Notes\r\nBrowser import rice,2,20/05/27,\"Top shelf, left\r\n"
                      "behind the flour\"\r\nBrowser import oats,1,,\r\nBrowser import salt,1,31/02/27,\r\n"},
      "questions": {"id": "medical-kit-location", "table": "medical__kits"},
      "charts": {"pet": "Rex", "dots": 3},  # the first charts (decision 0109): Rex has three weigh-ins
      # The way-out sketch (decision 0118): the Smiths' upstairs bedroom, with the warnings every version carries.
      "exit": {"room": "Main bedroom", "words": ["Practice aid only.", "call 000", "Only one way out recorded"]},
      # Pet feeding log (decision 0110): Rex's last bowl was 120 g yesterday, so Add food shows 120 g to check.
      "feeding": {"pet": "Rex", "amount": "120", "unit": "g", "after": "Recorded today: 120 g put out"},
      # Vehicle running log (decision 0111): the Family car's two readings in km, a lower one asks first.
      "running": {"vehicle": "Family car", "service": "Family car: Routine service", "last": "48,500 km",
                  "lower": "48000", "amount": "410.00"},
      # Think it through (decision 0108): the pipe drill offers the Smiths' water main at step 2.
      "drills": {"scenario": "pipe-in-wall", "number": "000", "record": "Water main", "steps": 4,
                 "words": "Browser check: made-up words about the spare key"},
      # A made-up helper's receipt on Review: a new item with its Stock in (one group), a Stock in on its own,
      # and a line the helper could not match, which the person turns into a Stock in (decision 0105).
      "review": {"helper": "Browser check helper", "item": "Browser check lentils", "existing": "Kidney beans",
                 "rows": 3, "line": "BRWSR TOM 400G 1 @ 1.50", "hint": "1"}}
US = {"household": "garcia", "locale": "en-US", "timezone": "America/Los_Angeles",
      "dates": {"item": "Browser check tins", "typed": "05/20/27", "words": "May 20, 2027",
                "wrongOrder": "20/05/27", "hint": "Use MM/DD/YY"},
      # Bills and insurance (decision 0117): the Garcias' Auto insurance stays in Vehicles until they choose.
      "bills": {"title": "Vehicle insurance already in Vehicles", "earlier": "Household car: Auto insurance",
                "name": "Auto insurance",
                "done": "Moved Auto insurance to Bills and insurance. One reminder is active there"},
      # Optional links (decision 0115): switch Our home off in Settings, the Garcias' meter link is kept unseen.
      "optional": {"service": "Apartment electricity", "meter": "Apartment electricity meter",
                   "kept": "Meter link saved; switch on Our home to see it.",
                   "keptHelp": "A meter link is saved. Switch on Our home to see or change it.",
                   "offHelp": "Meter places are available if you switch on Our home. You can save this service without one."}}


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


def suggest_receipt(conn, registry: dict, data_dir: Path) -> None:
    """Put a made-up helper's receipt on Review, as a helper would send it, for the Review keys check."""
    r = AU["review"]
    existing = conn.execute("SELECT id FROM stock__items WHERE name = ?", (r["existing"],)).fetchone()[0]
    helper, _key = helpers.issue(conn, data_dir, r["helper"], "suggest", ["stock"])
    bought = {"reason": "bought", "amount": 2, "happened_on": "2026-11-20"}
    proposals.submit(conn, registry, helper, {"request_key": "browser-check", "why": "A made-up receipt", "entries": [
        {"table": "stock__items", "values": {"name": r["item"], "category": "pantry", "unit": "bags"}},
        {"table": "stock__movements", "values": dict(bought, item={"ref": 0})},
        {"table": "stock__movements", "values": dict(bought, item=existing)},
        {"kind": "unmatched_product_line", "source": {"line": r["line"], "price": "1.50"},
         "receipt_date": "2026-11-20", "quantity_hint": r["hint"], "unit_hint": "tin"}]})


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
            registry = records.build_registry(found)
            load_example.load_records(conn, registry, example)
            suggest_receipt(conn, registry, data_dir)
        finally:
            conn.close()
        done += drive(dict(plan, dates=AU["dates"], stock=AU["stock"], private=AU["private"], loan=AU["loan"],
                           job=AU["job"], routine=AU["routine"], csv=AU["csv"], review=AU["review"], questions=AU["questions"],
                           charts=AU["charts"], exit=AU["exit"], feeding=AU["feeding"], drills=AU["drills"],
                           running=dict(AU["running"], at=date.today().isoformat() + "T10:00")), work,
                           "main")
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
                      "executablePath": executable, "dates": US["dates"], "optional": US["optional"],
                      "bills": US["bills"]}, work, "main")
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
