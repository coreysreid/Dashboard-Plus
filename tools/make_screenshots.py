"""Make the example screenshots: run each example household through every stage of using the dashboard."""
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
from dashboard.core import db, modules, records  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
GALLERY = ROOT / "docs" / "EXAMPLES.md"
HOUSEHOLDS = ["smith", "garcia", "taylor"]
LONG_SHEETS: list[str] = []  # printable sheets that did not fit on one page
WIDTH, HEIGHT = 1200, 800
DATA_SHOWN_AS = "D:\\Dashboard Plus\\data"
EXTRA_SHOWN_AS = "%LOCALAPPDATA%\\Dashboard Plus\\backups"

# Each stage: file name, title, what it shows, and where to go. "{id:table:name}" is replaced with
# the id of the record with that name. Stages before "load" happen before the household's records exist.
STAGES = [
    ("01-welcome", "First start: the welcome page", "The first-run questions, before anything is entered.",
     {"goto": "/setup"}),
    ("02-setup-answered", "Setup, answered", "Who lives here, the home, what to track and backups.",
     {"wizard": True}),
    ("03-first-home", "The first home page", "Straight after setup: the household is in People, and the "
     "dashboard says what to do first.", {"submit_wizard": True}),
    ("load", None, None, None),
    ("04-home", "Home, in everyday use", "Days of water, what needs attention, the printable sheets and "
     "every list.", {"goto": "/"}),
    ("05-people", "People", "Everyone in or around the household.", {"goto": "/t/people__people"}),
    ("06-person", "One person's page", "Their details, what links to them, and the history of changes.",
     {"goto": "/t/people__people/{id:people__people:person}"}),
    ("07-who-to-call", "Who to call", "In the order to call them.", {"goto": "/t/people__roles"}),
    ("08-important-details", "Important details", "Allergies, conditions, medication and access "
     "instructions, hidden until you choose to show them.", {"goto": "/t/people__important_info"}),
    ("09-emergency-sheet", "Emergency sheet (fridge copy)", "As it prints: who lives here and who to call.",
     {"goto": "/sheet/people/emergency", "media": "print"}),
    ("10-emergency-sheet-medical", "Emergency sheet with private medical details", "As it prints, for "
     "responders and carers.", {"goto": "/sheet/people/emergency_medical", "media": "print"}),
    ("11-places", "Places", "Where things are kept.", {"goto": "/t/stock__places"}),
    ("12-stock", "Stock items", "What the household has, how much, and how much to keep.",
     {"goto": "/t/stock__items"}),
    ("13-stock-item", "One stock item", "Its amount, where it is, and every change to it.",
     {"goto": "/t/stock__items/{id:stock__items:item}"}),
    ("14-stock-in", "Recording stock in", "Opened from the item's page: the item, the reason and today's "
     "date are already filled in.", {"goto": "/t/stock__movements/new?item={id:stock__items:item}"}),
    ("15-stock-in-and-out", "Stock in and out", "Everything bought, used, expired or thrown away.",
     {"goto": "/t/stock__movements"}),
    ("16-needs-attention", "Needs attention", "Days of water with the working shown, running low, use-by "
     "dates, and details worth filling in.", {"goto": "/attention"}),
    ("17-supplies-sheet", "Emergency supplies sheet", "As it prints: water, first aid, power and food, and "
     "where each is kept.", {"goto": "/sheet/stock/supplies", "media": "print"}),
    ("18-settings", "Settings", "The setup answers, which can be changed at any time.",
     {"goto": "/settings"}),
    ("19-close", "Closing safely", "A backup is made before it stops, so a USB stick can be unplugged.",
     {"goto": "/close"}),
    ("20-closed", "Closed", "Safe to unplug.", {"submit": "form button[type=submit]"}),
]
# Which record each household shows on the person and stock item pages.
# How each household's browser shows dates, as it would in their country.
LOCALES = {"smith": ("en-AU", "Australia/Sydney"), "garcia": ("en-US", "America/Los_Angeles"),
           "taylor": ("en-GB", "Europe/London")}
FEATURED = {
    "smith": {"person": "Emily Smith", "item": "Adrenaline auto-injector (Emily)"},
    "garcia": {"person": "Rosa Garcia", "item": "Metformin 500 mg (Rosa)"},
    "taylor": {"person": "Sam Taylor", "item": "Bottled water (6 x 2 L)"},
}


def wizard_steps(setup: dict) -> list[dict]:
    """Fill in the first-run questions as a person would."""
    steps = [{"goto": "/setup"}]
    for _ in range(max(0, len(setup["people"]) - 3)):
        steps.append({"click": "#add-person"})
    for number, name in enumerate(setup["people"], start=1):
        steps.append({"fill": f"#name_{number}", "value": name})
    steps += [{"fill": "#pets", "value": setup.get("pets", 0)},
              {"check": "input[name=mobility_needs]", "value": bool(setup.get("mobility_needs"))},
              {"fill": "#country", "value": setup.get("country", "")},
              {"fill": "#region", "value": setup.get("region", "")},
              {"select": "#home_type", "value": setup.get("home_type", "")},
              {"fill": "#storeys", "value": setup.get("storeys", "")}]
    steps += [{"check": f"input[name=hazards][value={h}]"} for h in setup.get("hazards", [])]
    found, _ = modules.discover(ROOT / "modules")
    steps += [{"check": f"input[name=modules][value={m.name}]", "value": m.name in setup["modules"]}
              for m in found]
    return steps


def record_ids(data_dir: Path, featured: dict) -> dict:
    conn = db.connect(data_dir / "dashboard.db")
    try:
        ids = {}
        for key, table in (("person", "people__people"), ("item", "stock__items")):
            row = conn.execute(f"SELECT id FROM {table} WHERE name = ? AND deleted_at IS NULL",
                               (featured[key],)).fetchone()
            ids[f"{table}:{key}"] = row["id"]
        return ids
    finally:
        conn.close()


def run_browser(plan: dict, work: Path) -> list[str]:
    """Run the browser steps; return the printed page counts it reports, like "pages /sheet/x A4 1"."""
    path = work / "steps.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    result = subprocess.run(["node", str(ROOT / "tools" / "screenshots.js"), str(path)], check=True, cwd=ROOT,
                            capture_output=True, text=True)
    return [line for line in result.stdout.splitlines() if line.startswith("pages ")]


def start_server(data_dir: Path, env: dict) -> tuple[subprocess.Popen, str]:
    process = subprocess.Popen([sys.executable, "-m", "dashboard", "--data", str(data_dir), "--no-browser",
                                "--no-extra-backup"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    state = data_dir / "run" / "dashboard.json"
    for _ in range(100):
        if state.exists():
            run = json.loads(state.read_text(encoding="utf-8"))
            return process, f"http://127.0.0.1:{run['port']}/?key={run['session']}"
        time.sleep(0.1)
    process.kill()
    raise RuntimeError("The dashboard did not start.")


def make(household: str, work: Path, executable: str | None) -> list[tuple[str, str, str]]:
    """Run one household through every stage; return (file, title, caption) for the gallery."""
    example = load_example.read(household)
    out = OUT / household
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    data_dir = work / household / "data"
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), HOME=str(work / "home"))
    process, launch = start_server(data_dir, env)
    swaps = [[str(data_dir / "backups"), DATA_SHOWN_AS + "\\backups"], [str(data_dir), DATA_SHOWN_AS]]
    from dashboard.core.backups import default_extra_dir
    os.environ["HOME"] = env["HOME"]  # so the second backup folder matches the one the server shows
    swaps.append([str(default_extra_dir()), EXTRA_SHOWN_AS])
    shown = []
    try:
        steps: list[dict] = [{"goto": launch.replace(launch.split("/?")[0], "")}]
        ids: dict = {}
        for name, title, caption, action in STAGES:
            if name == "load":
                run_browser({"base": launch.split("/?")[0], "steps": steps, "width": WIDTH, "height": HEIGHT,
                             "swaps": swaps, "executablePath": executable,
                             "locale": LOCALES[household][0], "timezone": LOCALES[household][1]}, work)
                conn = db.connect(data_dir / "dashboard.db")
                try:
                    found, _ = modules.discover(ROOT / "modules")
                    load_example.load_records(conn, records.build_registry(found), example)
                finally:
                    conn.close()
                ids = record_ids(data_dir, FEATURED[household])
                steps = [{"goto": launch.replace(launch.split("/?")[0], "")}]
                continue
            if action.get("wizard"):
                steps += wizard_steps(example["setup"])
            if action.get("submit_wizard"):
                steps.append({"submit": "form.record button[type=submit]"})
            if "goto" in action:
                target = action["goto"]
                for key, value in ids.items():
                    target = target.replace("{id:" + key + "}", str(value))
                steps.append({"media": action.get("media", "screen")})
                steps.append({"goto": target})
                if action.get("media") == "print":
                    steps.append({"pages": target})
            if "submit" in action:
                steps.append({"submit": action["submit"]})
            steps.append({"shot": str(out / f"{name}.png")})
            shown.append((f"{name}.png", title, caption))
        pages = run_browser({"base": launch.split("/?")[0], "steps": steps, "width": WIDTH, "height": HEIGHT,
                     "swaps": swaps, "executablePath": executable,
                             "locale": LOCALES[household][0], "timezone": LOCALES[household][1]}, work)
    finally:
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
    write_index(household, example, shown)
    for line in pages:
        _, sheet, paper, count = line.split()
        print(f"{household}: {sheet} prints on {count} {paper} page{'s' if count != '1' else ''}")
        if count != "1":
            LONG_SHEETS.append(f"{household} {sheet} ({paper})")
    return shown


def write_index(household: str, example: dict, shown: list) -> None:
    lines = [f"# docs/screenshots/{household}/  (summary: screenshots of {example['title']}, made up)",
             "Made by tools/make_screenshots.py from examples/households. Do not edit by hand.",
             "| Entry | What it is | Open it when |", "|---|---|---|",
             f"| *.png | Each stage of using the dashboard, in order: welcome to closing | showing {example['title']} |"]
    (OUT / household / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gallery(results: dict) -> None:
    lines = ["# Examples: Dashboard Plus at every stage", "",
             "Three made-up households, each taken from the first start to closing safely. Every name,",
             "number and address is invented (see `examples/households/`). The screenshots are made",
             "automatically by `tools/make_screenshots.py`, so they always match the current program;",
             "they are taken on Linux, with folder names shown as they appear on Windows.", ""]
    for household, shown in results.items():
        example = load_example.read(household)
        lines += [f"- [{example['title']}](#{household}): {example['summary']}"]
    for household, shown in results.items():
        example = load_example.read(household)
        lines += ["", f'<a id="{household}"></a>', f"## {example['title']}", "", example["summary"], ""]
        for file, title, caption in shown:
            lines += [f"### {title}", "", caption, "", f"![{title}](screenshots/{household}/{file})", ""]
    GALLERY.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("households", nargs="*", default=HOUSEHOLDS, help="which households (default: all)")
    parser.add_argument("--browser", help="a Chromium executable, if Playwright cannot find its own")
    args = parser.parse_args(argv)
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for household in args.households:
            results[household] = make(household, Path(tmp), args.browser)
    if list(results) == HOUSEHOLDS:
        write_gallery(results)
    print(f"Saved screenshots for {', '.join(results)} in {OUT.relative_to(ROOT)}.")
    if LONG_SHEETS:
        print("These sheets no longer fit on one page: " + "; ".join(LONG_SHEETS))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
