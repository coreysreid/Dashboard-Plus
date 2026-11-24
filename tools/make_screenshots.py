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
from datetime import date, timedelta
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
PHONE_WIDTH = 320  # the narrowest screen the pages must work on
DATA_SHOWN_AS = "D:\\Dashboard Plus\\data"
EXTRA_SHOWN_AS = "%LOCALAPPDATA%\\Dashboard Plus\\backups"

# Each stage: file name, title, what it shows, and where to go. "{id:table:name}" is replaced with
# the id of the record with that name. Stages before "load" happen before the household's records exist.
STAGES = [
    ("01-welcome", "First start: the welcome page", "The first-run questions, before anything is entered.",
     {"goto": "/setup"}),
    ("02-setup-answered", "Setup, answered", "Who lives here, the home, what to track and backups.",
     {"wizard": True}),
    ("02b-set-up-my-home", "Set up my home, offered next", "Straight after setup: add rooms, storage spots and "
     "which rooms connect, or skip it for now.", {"submit_wizard": True}),
    ("03-first-home", "The first home page", "After setup: the household is in People, and the "
     "dashboard says what to do first.", {"goto": "/"}),
    ("load", None, None, None),
    ("04-home", "Home, in everyday use", "Days of water, what needs attention, then one card per area: its "
     "main list, its other lists as links, and its sheets to print.", {"goto": "/"}),
    ("04b-home-phone", "Home, on a phone", "The same page at 320 pixels wide: the cards stack in one column.",
     {"goto": "/", "width": PHONE_WIDTH}),
    ("05-people", "People", "Everyone in or around the household.", {"goto": "/t/people__people"}),
    ("06-person", "One person's page", "Their details, what links to them, and the history of changes.",
     {"goto": "/t/people__people/{id:people__people:person}"}),
    ("07-who-to-call", "Who to call", "In the order to call them.", {"goto": "/t/people__roles"}),
    ("08-important-details", "Important details", "Allergies, conditions, medication and access "
     "instructions, hidden until you choose to show them.", {"goto": "/t/people__important_info"}),
    ("09-emergency-sheet", "Emergency sheet (fridge copy)", "As it prints: who lives here and who to call.",
     {"goto": "/sheet/people/emergency", "media": "print"}),
    ("10-emergency-sheet-medical", "Emergency sheet with private medical details", "As it prints, for "
     "responders and carers.", {"goto": "/sheet/people/emergency_medical", "submit": "text=Show private sheet", "media": "print"}),
    ("11-places", "Places", "Where things are kept.", {"goto": "/t/stock__places"}),
    ("11b-set-up-my-home", "Set up my home", "One card per room or area: the storage spots inside it, what it "
     "connects to, and doors to outside.", {"goto": "/set-up-home"}),
    ("11c-way-out-sketch", "Our way-out sketch", "Rooms as boxes floor by floor, the recorded ways between them, "
     "doors to outside and what still needs checking, with the same facts as text.", {"goto": "/exit-sketch"}),
    ("11d-way-out-sheet", "Way-out sketch sheet", "As it prints: warnings, meeting place, the drawing, legend and "
     "Check together, on numbered pages.", {"goto": "/exit-sketch/print?paper=a4", "media": "print",
                                             "continues": True}),
    ("12-stock", "Stock items", "What the household has, how much, and how much to keep.",
     {"goto": "/t/stock__items"}),
    ("12b-adding-stock", "Adding a stock item", "Start typing and pick from 800 common goods; picking one fills "
     "in its kind and usual unit. Your own items come first.", {"goto": "/t/stock__items/new", "type": ["#f-name", "kid"]}),
    ("13-stock-item", "One stock item", "Its amount, where it is, and every change to it.",
     {"goto": "/t/stock__items/{id:stock__items:item}"}),
    ("14-stock-in", "Recording stock in", "Opened from the item's page: the item, the reason and today's "
     "date are already filled in.", {"goto": "/t/stock__movements/new?item={id:stock__items:item}"}),
    ("15-stock-in-and-out", "Stock in and out", "Everything bought, used, expired or thrown away.",
     {"goto": "/t/stock__movements"}),
    ("16-pets", "Pets", "Every pet, its vet and when vaccinations are due.", {"goto": "/t/pets__pets", "module": "pets"}),
    ("17-pet", "One pet's page", "Its details, its recorded weights as dots with the same values in a table, "
     "and buttons to add treatments, weigh-ins and vet visits.",
     {"goto": "/t/pets__pets/{id:pets__pets:pet}", "module": "pets"}),
    ("17b-pet-weights", "A pet's weights over the last year", "Last 3 months, Last year or All dates; the change "
     "since the reading before and since the start of the range in words; a line between readings that starts "
     "from a scale at zero.", {"goto": "/charts/pets__weigh_ins?subject={id:pets__pets:pet}&range=1y",
                               "module": "pets"}),
    ("18-pet-sheet", "Pet details sheet", "As it prints: for a sitter, a kennel or an evacuation centre.",
     {"goto": "/sheet/pets/pets", "media": "print", "module": "pets"}),
    ("18b-first-aid", "First aid kits", "Each kit, where it is kept and when it is next checked.",
     {"goto": "/t/medical__kits", "module": "medical"}),
    ("18c-first-aid-sheet", "First aid at home sheet", "As it prints: the kits, their places and who has trained.",
     {"goto": "/sheet/medical/first_aid", "media": "print", "module": "medical"}),
    ("18d-our-home", "Alarms and safety equipment", "Home layout: each smoke alarm, extinguisher or go-bag, "
     "where it is and when the household plans to check it.", {"goto": "/t/home_layout__equipment", "module": "home_layout"}),
    ("18e-our-home-sheet", "Our home sheet", "As it prints: the ways out, shut-offs, alarms and meters, each with "
     "its full place.", {"goto": "/sheet/home_layout/our_home", "media": "print", "module": "home_layout"}),
    ("18f-vehicles", "Vehicles", "Each vehicle, when its registration is due, who to call if it breaks down, "
     "where it is kept and its car kit.", {"goto": "/t/vehicles__vehicles", "module": "vehicles"}),
    ("18g-vehicle-sheet", "Vehicles sheet", "As it prints: the vehicles, who to call and their phone number, and "
     "the dates the household chose, with no plate or policy numbers.", {"goto": "/sheet/vehicles/vehicles", "media": "print", "module": "vehicles"}),
    ("18h-documents", "Important documents", "Where each important paper is kept, whose it is and the review "
     "or renewal date the household chose.", {"goto": "/t/documents__documents", "module": "documents"}),
    ("18i-documents-sheet", "Document review dates sheet", "As it prints: names, kinds, dates and where copies "
     "are also kept, with no original places or document numbers.", {"goto": "/sheet/documents/document_review", "media": "print",
                                     "module": "documents"}),
    ("18j-home-care", "Home care jobs", "Each job around the home, where it is, who usually does it, when it was "
     "last done and the date the household chose to do it again.", {"goto": "/t/home_care__jobs", "module": "home_care"}),
    ("18k-home-care-sheet", "Home care sheet", "As it prints: the jobs, who usually does them and their phone "
     "number, and the household's own dates, with no notes.",
     {"goto": "/sheet/home_care/home_care", "media": "print", "module": "home_care"}),
    ("18l-lent-out", "Things lent out", "What was lent, who borrowed it, when, the date it is due back and when "
     "it came back.", {"goto": "/t/lent_out__loans", "module": "lent_out"}),
    ("18m-lent-out-sheet", "Things still lent out sheet", "As it prints: only the loans still out, with the "
     "borrower's phone from People and no notes.", {"goto": "/sheet/lent_out/still_out", "media": "print",
                                                     "module": "lent_out"}),
    ("18n-garden", "Vegetable garden jobs", "Garden jobs with the date the household chose; a finished job is "
     "no longer a reminder.", {"goto": "/t/garden__jobs", "module": "garden"}),
    ("18o-garden-sheet", "Garden plan sheet", "As it prints: beds and where they are, plantings and the jobs "
     "not yet done, with no notes.", {"goto": "/sheet/garden/plan", "media": "print", "module": "garden"}),
    ("18p-wine", "Wine collection", "Each wine, how many bottles the household says it has and where they are "
     "kept; the count is typed, never worked out.", {"goto": "/t/wine__bottles", "module": "wine"}),
    ("18q-wine-sheet", "Wine collection sheet", "As it prints: wine, count, place and bought on, with no price "
     "or tasting notes.", {"goto": "/sheet/wine/collection", "media": "print", "module": "wine"}),
    ("18r-utilities", "Utilities and household accounts", "Each service, its provider, who to contact about a fault "
     "and its meter; the account reference stays hidden until Show.", {"goto": "/t/utilities__services",
                                                                       "module": "utilities"}),
    ("18s-utilities-sheet", "Utility contacts sheet", "As it prints: service, provider, fault contact and their "
     "phone from People, and the meter, with no account numbers or notes.",
     {"goto": "/sheet/utilities/utility_contacts", "media": "print", "module": "utilities"}),
    ("18sa-vehicle-readings", "A vehicle's odometer readings", "Last recorded, then each reading as a dot and a row "
     "in the unit it was saved in; nothing is converted or worked out.",
     {"goto": "/t/vehicles__vehicles/{id:vehicles__vehicles:vehicle}", "module": "vehicle_running"}),
    ("18sb-service-estimates", "A service's cost estimates", "Each quote with who gave it and its dates; the "
     "amount and what it covers stay hidden until Show. Estimates, not a bill.",
     {"goto": "/t/vehicles__services/{id:vehicles__services:service}", "module": "vehicle_running"}),
    ("18sc-bills", "Bills and insurance", "Each bill and policy with its provider and the date to check it; the "
     "amount, cover and reference stay hidden until Show. Car insurance already in Vehicles stays there until the "
     "household chooses.", {"goto": "/t/bills_insurance__commitments", "module": "bills_insurance"}),
    ("18sd-bills-sheet", "Bills and policies to check sheet", "As it prints: names, kinds, providers and dates, "
     "with no amounts, cover or references.",
     {"goto": "/sheet/bills_insurance/upcoming_bills_and_policies", "media": "print", "module": "bills_insurance"}),
    ("18t-questions", "Have you thought about…?", "Readiness: the questions that fit the household, by group, with "
     "how many have been looked at, never a safety score.", {"goto": "/questions/readiness", "module": "readiness"}),
    ("18u-question", "One question", "Why it may matter, its official source and the date checked, a record that may "
     "already answer it for the household to confirm, and Yes, Not relevant, Not yet or Tell me more.",
     {"goto": "/questions/readiness/medical-kit-location", "module": "readiness"}),
    ("18v-things-to-do", "Things to do, Today", "What is due today and anything late, each shown once as Due since, "
     "with the button its own list uses: Mark done, Mark this occurrence done, or Open record to update.",
     {"goto": "/to-do", "module": "routines"}),
    ("18w-things-to-do-month", "Things to do, This month", "The calendar month by week, from the dates the household "
     "recorded; a task with no date is under No date yet.", {"goto": "/to-do/month", "module": "routines"}),
    ("18wa-things-to-do-calendar", "Things to do, Calendar", "The routines' month: each Done or Skipped on the day "
     "it happened and each routine's next date once, every mark with its own symbol as well as a colour, a legend "
     "and the same days in words.", {"goto": "/to-do/calendar", "module": "routines"}),
    ("18x-routines", "Routines", "The household's own repeating tasks: the repeat it chose, the next date and when "
     "each was last done.", {"goto": "/t/routines__routines", "module": "routines"}),
    ("18y-drills", "Think it through", "Eight calm practice runs, the emergency number for the household's country "
     "first, when each was practised and when to look again; drills that do not fit the settings listed apart.",
     {"goto": "/drills/readiness", "module": "readiness"}),
    ("18z-drill", "One drill", "Its questions in order, Start or Not now, its sources with the date each was checked, "
     "and earlier practice.", {"goto": "/drills/readiness/pipe-in-wall", "module": "readiness"}),
    ("18za-feeding", "Food put out, one pet's day", "Pet feeding log: one pet's entries on one day, totals only in "
     "matching units, entries with no amount counted, then Add food and recent entries to start from.",
     {"goto": "/daily/pet_feeding__servings?subject={id:pets__pets:pet}&day={yesterday}", "module": "pet_feeding"}),
    ("18zb-feeding-phone", "Food put out, on a phone", "The same day at 320 pixels wide, for one-handed entry.",
     {"goto": "/daily/pet_feeding__servings?subject={id:pets__pets:pet}&day={yesterday}", "module": "pet_feeding",
      "width": PHONE_WIDTH}),
    ("18zbb-feeding-calendar-phone", "Feeding calendar, on a phone", "One pet's month at 320 pixels wide: a day "
     "with feedings shows ● and how many; a blank day only means nothing was recorded, never a missed meal.",
     {"goto": "/calendar/pet_feeding__servings?subject={id:pets__pets:pet}", "module": "pet_feeding",
      "width": PHONE_WIDTH}),
    ("18zc-feeding-sheet", "Pet feeding log sheet", "As it prints: every entry of the last 14 days with each day's "
     "totals by unit, and \"Food put out, not necessarily eaten\"; notes are left off.",
     {"goto": "/daily/pet_feeding__servings/sheet?subject={id:pets__pets:pet}", "media": "print",
      "module": "pet_feeding"}),
    ("18zd-doses", "Medicine given, one person's day", "Medicine doses: how many doses and when; the medicine, "
     "amounts and who gave them stay hidden until Show details, and nothing says a dose was missed.",
     {"goto": "/daily/medicine_doses__doses?subject={id:people__people:person}&day={yesterday}",
      "module": "medicine_doses", "width": PHONE_WIDTH}),
    ("18ze-dose-calendar-phone", "Dose calendar, on a phone", "One person's month at 320 pixels wide: a day with "
     "doses shows ● and how many, never which medicine or how much; Show lists each day's doses.",
     {"goto": "/calendar/medicine_doses__doses?subject={id:people__people:person}", "module": "medicine_doses",
      "width": PHONE_WIDTH}),
    ("19-needs-attention", "Needs attention", "Days of water with the working shown, running low, use-by "
     "and due dates, and details worth filling in.", {"goto": "/attention"}),
    ("19b-drinking-water", "Drinking water counted today", "Each water item behind Home's days of water, as a "
     "bar with its litres, then a table of every water item, counted or left out with the reason.",
     {"goto": "/supplies/stock__items", "module": "stock"}),
    ("19c-drinking-water-phone", "Drinking water, on a phone", "The same page at 320 pixels wide: the bars stay "
     "readable and each table row becomes a card.", {"goto": "/supplies/stock__items", "module": "stock",
                                                     "width": PHONE_WIDTH}),
    ("20-supplies-sheet", "Emergency supplies sheet", "As it prints: water, first aid, power and food, and "
     "where each is kept.", {"goto": "/sheet/stock/supplies", "media": "print"}),
    ("21-settings", "Settings", "The setup answers, which can be changed at any time.",
     {"goto": "/settings"}),
    ("22-close", "Save and exit", "A final backup is made before it stops, so a USB stick can be unplugged.",
     {"goto": "/close"}),
    ("23-closed", "Saved and closed", "Safe to unplug.", {"submit": "form button[type=submit]"}),
]
# Which record each household shows on the person and stock item pages.
# How each household's browser shows dates, as it would in their country.
LOCALES = {"smith": ("en-AU", "Australia/Sydney"), "garcia": ("en-US", "America/Los_Angeles"),
           "taylor": ("en-GB", "Europe/London")}
FEATURED = {
    "smith": {"person": "Emily Smith", "item": "Adrenaline auto-injector (Emily)", "pet": "Rex",
              "vehicle": "Family car", "service": "Routine service"},
    "garcia": {"person": "Rosa Garcia", "item": "Metformin 500 mg (Rosa)", "pet": "Luna",
               "vehicle": "Household car", "service": "Oil change and inspection"},
    "taylor": {"person": "Sam Taylor", "item": "Bottled water (6 x 2 L)", "vehicle": "Small car",
               "service": "MOT test"},
}


def wizard_steps(setup: dict) -> list[dict]:
    """Fill in the first-run questions as a person would."""
    steps = [{"goto": "/setup"}]
    for _ in range(max(0, len(setup["people"]) - 3)):
        steps.append({"click": "#add-person"})
    for number, name in enumerate(setup["people"], start=1):
        steps.append({"fill": f"#name_{number}", "value": name})
    pets = setup.get("pets", [])
    for _ in range(max(0, len(pets) - 2)):
        steps.append({"click": "#add-pet"})
    for number, pet in enumerate(pets, start=1):
        steps += [{"fill": f"#pet_{number}", "value": pet["name"]}, {"select": f"#pet_kind_{number}", "value": pet["kind"]}]
    steps += [{"check": "input[name=mobility_needs]", "value": bool(setup.get("mobility_needs"))},
              {"select": "#country", "value": setup.get("country", "")},
              {"select": "#region", "value": setup.get("region", "")},
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
        for key, table in (("person", "people__people"), ("item", "stock__items"), ("pet", "pets__pets"),
                             ("vehicle", "vehicles__vehicles"), ("service", "vehicles__services")):
            if key not in featured:
                continue
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
    result = subprocess.run(["node", str(ROOT / "tools" / "screenshots.js"), str(path)], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("The browser steps failed:\n" + result.stderr.strip()[-2000:])
    return [line for line in result.stdout.splitlines() if line.startswith("pages ")]


def start_server(data_dir: Path, env: dict) -> tuple[subprocess.Popen, str]:
    # The second backup goes to the temporary HOME (see `make`), so Settings shows it working.
    process = subprocess.Popen([sys.executable, "-m", "dashboard", "--data", str(data_dir), "--no-browser"],
                               cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            if action and action.get("module") and action["module"] not in example["setup"]["modules"]:
                continue  # this household does not use that module
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
                target = target.replace("{yesterday}", (date.today() - timedelta(days=1)).isoformat())
                steps.append({"media": action.get("media", "screen")})
                steps.append({"viewport": action.get("width", WIDTH)})
                steps.append({"goto": target})
                if action.get("media") == "print" and not action.get("continues"):
                    steps.append({"pages": target})  # a sheet that continues on numbered pages (0118) is not counted
            if "type" in action:
                steps.append({"type": action["type"][0], "value": action["type"][1]})
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
             "Three made-up households, each taken from the first start to saving and exiting. Every name,",
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
