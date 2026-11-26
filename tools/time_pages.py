"""Time the pages on a synthetic household with years of records, and report each page's speed and SQL query count (decision 0136)."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dashboard.core import db, records, settings, startup  # noqa: E402

TODAY = date(2026, 11, 20)
BASE = "http://127.0.0.1:5199"
MODULES = ("people", "pets", "pet_feeding", "medicine_doses", "vehicles", "vehicle_running", "routines", "stock",
           "home_care", "home_layout", "garden", "lent_out")
SLOW_MS = 300


def build(data: Path, modules_dir: Path, scale: float = 1.0) -> dict:
    """Fill an empty data folder with an invented household and years of records; returns the counts made.

    `scale` shrinks everything (tests use a small one). Every name is made up; nothing real is used."""
    for name in MODULES:
        shutil.copytree(ROOT / "modules" / name, modules_dir / name, dirs_exist_ok=True)
    report = startup.prepare(data, modules_dir)
    assert not report.module_problems, report.module_problems
    conn = db.connect(data / "dashboard.db")
    conn.execute("PRAGMA synchronous=OFF")  # a throwaway folder: speed matters more than a crash-proof save
    settings.put(conn, "household.time_zone", "UTC")
    settings.put(conn, "setup.done", True)
    clock = {"at": f"{TODAY.isoformat()}T12:00:00+00:00"}
    store = records.Records(conn, records.build_registry(report.loaded), clock=lambda: clock["at"])
    counts: dict[str, int] = {}

    def made(table: str, values: dict, saved: date | None = None) -> int:
        clock["at"] = f"{(saved or TODAY).isoformat()}T12:00:00+00:00"
        counts[table] = counts.get(table, 0) + 1
        return store.create(table, values)

    def changed(table: str, record_id: int, values: dict, saved: date) -> None:
        clock["at"] = f"{saved.isoformat()}T12:00:00+00:00"
        store.update(table, record_id, values)

    def n(count: int) -> int:
        return max(1, round(count * scale))

    span = max(90, round(365 * 5 * scale))  # days of history: five years at the usual size
    start = TODAY - timedelta(days=span)
    people = [made("people__people", {"name": f"Example Person {i}", "lives_here": True}) for i in (1, 2)]
    meds = [made("people__important_info", {"person": p, "kind": "medication", "detail": "Example tablet"})
            for p in people]
    pets = [made("pets__pets", {"name": f"Example Pet {i}", "species": "dog"}) for i in (1, 2, 3)]
    for pet in pets:  # twice-daily feedings for years, weekly weigh-ins
        for d in range((TODAY - start).days):
            day = start + timedelta(days=d)
            for hour in (7, 18):
                made("pet_feeding__servings", {"pet": pet, "given_at": f"{day.isoformat()}T{hour:02d}:00:00",
                                               "kind": "bowl", "food": "Example kibble", "amount": 150,
                                               "unit": "g"}, day)
            if d % 7 == 0:
                made("pets__weigh_ins", {"pet": pet, "day": day.isoformat(), "weight": 20 + (d % 9) / 10}, day)
    dose_days = min(span, 3 * 365)
    for person, med in zip(people, meds):
        for d in range(dose_days):
            day = TODAY - timedelta(days=dose_days - d)
            made("medicine_doses__doses", {"recipient": person, "medication": med, "amount": 1, "unit": "tablet",
                                           "given_at": f"{day.isoformat()}T08:00:00"}, day)
    for v in (1, 2):
        car = made("vehicles__vehicles", {"name": f"Example Car {v}"})
        months = max(3, span // 30)
        for m in range(months):  # a reading a month
            day = TODAY - timedelta(days=30 * (months - m))
            made("vehicle_running__readings", {"vehicle": car, "read_at": f"{day.isoformat()}T09:00:00",
                                               "distance": 10000 + m * 900, "unit": "km"}, day)
        for name in ("Oil change", "Tyres", "Brakes", "Service"):
            service = made("vehicles__services", {"vehicle": car, "name": name, "last_done": start.isoformat(),
                                                  "next_due": (start + timedelta(days=200)).isoformat()}, start)
            for k in range(1, n(360)):  # edited many times: lots of history rows
                saved = start + timedelta(days=k * 5)
                if saved > TODAY:
                    break
                changed("vehicles__services", service, {"last_done": saved.isoformat(),
                                                        "next_due": (saved + timedelta(days=200)).isoformat()}, saved)
    people_ids = people
    for i in range(n(40)):
        routine = made("routines__routines", {"name": f"Example routine {i + 1}", "who": people_ids[i % 2],
                                              "repeat_count": 1, "repeat_unit": "weeks",
                                              "first_due": start.isoformat(), "next_due": TODAY.isoformat()}, start)
        for k in range(n(40)):
            day = start + timedelta(days=7 * k + i % 5)
            if day > TODAY:
                break
            made("routines__times", {"routine": routine, "outcome": "skipped" if k % 9 == 0 else "done",
                                     "done_on": day.isoformat(), "planned_for": day.isoformat()}, day)
    place = made("stock__places", {"name": "Example cupboard"})
    categories = ["pantry", "cleaning", "first_aid"]
    moves = []
    for i in range(n(200)):
        item = made("stock__items", {"name": f"Example supply {i + 1}", "category": categories[i % 3],
                                     "unit": "packs", "quantity": 0, "minimum": 2, "place": place})
        for k in range(n(10)):  # 2,000 Stock ins in all, with prices; every fourth has no price
            day = start + timedelta(days=(i * 7 + k * 37) % span)
            values = {"item": item, "reason": "bought", "amount": 3, "happened_on": day.isoformat(),
                      "place": place}
            if (i + k) % 4:
                values.update({"price": "4.50", "price_basis": "each", "currency": "AUD"})
            move = made("stock__movements", values, day)
            if "price" in values:
                moves.append((move, day))
    for j, (move, day) in enumerate(moves):
        if j % 20 == 0:
            made("stock__refunds", {"movement": move, "happened_on": day.isoformat(), "amount": "4.50",
                                    "currency": "AUD"}, day)
    for i in range(n(20)):
        job = made("home_care__jobs", {"name": f"Example job {i + 1}", "kind": "other", "last_done": start.isoformat(),
                                       "repeat_count": 2, "repeat_unit": "weeks",
                                       "next_due": (start + timedelta(days=14)).isoformat()}, start)
        for k in range(n(40)):
            day = start + timedelta(days=14 * k)
            if day > TODAY:
                break
            made("home_care__work_done", {"job": job, "done_on": day.isoformat()}, day)
    for i in range(n(10)):  # alarms tested again and again, with history
        alarm = made("home_layout__equipment", {"name": f"Example alarm {i + 1}", "kind": "smoke_alarm",
                                                "last_tested": start.isoformat()}, start)
        for k in range(1, n(60)):
            day = start + timedelta(days=30 * k)
            if day > TODAY:
                break
            changed("home_layout__equipment", alarm, {"last_tested": day.isoformat()}, day)
    for i in range(n(20)):  # garden jobs ticked done by the button and put back again
        job = made("garden__jobs", {"title": f"Example garden job {i + 1}"}, start)
        for k in range(n(30)):
            day = start + timedelta(days=50 * k + i)
            if day > TODAY:
                break
            clock["at"] = f"{day.isoformat()}T12:00:00+00:00"
            store.action("garden__jobs", job, "done", today=day)
            changed("garden__jobs", job, {"done": False, "done_on": None}, day + timedelta(days=1))
    person = people[0]
    for i in range(n(100)):  # things lent out and returned
        lent = start + timedelta(days=(i * 17) % span)
        loan = made("lent_out__loans", {"name": f"Example loan {i + 1}", "borrower": person,
                                        "lent_on": lent.isoformat(), "due_back": (lent + timedelta(days=7)).isoformat()},
                    lent)
        changed("lent_out__loans", loan, {"status": "returned", "returned_on": (lent + timedelta(days=9)).isoformat()},
                lent + timedelta(days=9))
    conn.close()
    return counts


def count_queries(conn: sqlite3.Connection, bucket: list) -> None:
    conn.set_trace_callback(lambda sql: bucket.append(sql))


def client_for(data: Path, modules_dir: Path):
    """A signed-in test client for the data folder, and the list that collects its SQL."""
    from dashboard.web.app import create_app
    report = startup.prepare(data, modules_dir)
    app = create_app("t", lambda: None, report, data_dir=data, session_key="k")
    app.config["PORT"] = 5199
    app.config["TODAY"] = lambda: TODAY
    bucket: list[str] = []
    real = db.connect

    def counting(path):
        conn = real(path)
        count_queries(conn, bucket)
        return conn
    db.connect = counting
    client = app.test_client()
    client.get("/?key=k", base_url=BASE)
    return app, client, bucket


def pages(conn: sqlite3.Connection, app) -> list[tuple[str, str, str]]:
    """(label, method, path) for each page under test, using real record ids from this household."""
    def one(sql):
        return conn.execute(sql).fetchone()[0]
    pet = one("SELECT MIN(id) FROM pets__pets")
    car = one("SELECT MIN(id) FROM vehicles__vehicles")
    service = one("SELECT MIN(id) FROM vehicles__services")
    routine = one("SELECT MIN(id) FROM routines__routines")
    person = one("SELECT MIN(id) FROM people__people")
    job = one("SELECT MIN(id) FROM home_care__jobs")
    return [
        ("Home", "GET", "/"),
        ("Needs attention", "GET", "/attention"),
        ("Feeding calendar, this month", "GET", "/calendar/pet_feeding__servings?month=2026-11"),
        ("Feeding calendar, a year ago", "GET", "/calendar/pet_feeding__servings?month=2025-11"),
        ("Dose bars by month", "GET", "/bars/medicine_doses__doses/doses?by=month"),
        ("Dose calendar", "GET", "/calendar/medicine_doses__doses?month=2026-11"),
        ("Vehicle services calendar", "GET", "/calendar/vehicles__services?month=2026-11"),
        ("Routines calendar", "GET", "/calendar/routines__times?month=2026-11"),
        ("Home care calendar", "GET", "/calendar/home_care__work_done?month=2026-11"),
        ("Things to do: Today", "GET", "/to-do"),
        ("Things to do: Calendar, all lists", "GET", "/to-do/calendar?month=2026-11"),
        ("Feeding bars by day", "GET", "/bars/pet_feeding__servings/food?by=day"),
        ("Feeding bars by month", "GET", "/bars/pet_feeding__servings/food?by=month"),
        ("Vehicle services bars by month", "GET", "/bars/vehicles__services/done?by=month"),
        ("Routines bars by week", "GET", "/bars/routines__times/done?by=week"),
        ("Home care bars by month", "GET", "/bars/home_care__work_done/done?by=month"),
        ("Spent per month: before Show", "GET", "/bars/stock__movements/spending?by=month"),
        ("Spent per month: after Show", "POST", "/bars/stock__movements/spending?by=month"),
        ("Pet timeline, first page", "GET", f"/timeline/pets__pets/{pet}"),
        ("Pet timeline, Earlier", "GET", f"/timeline/pets__pets/{pet}?before=2025-06-01"),
        ("Person timeline", "GET", f"/timeline/people__people/{person}"),
        ("Vehicle timeline", "GET", f"/timeline/vehicles__vehicles/{car}"),
        ("Routine timeline", "GET", f"/timeline/routines__routines/{routine}"),
        ("Pet page with panels", "GET", f"/t/pets__pets/{pet}"),
        ("Vehicle page with panels", "GET", f"/t/vehicles__vehicles/{car}"),
        ("Service page (history)", "GET", f"/t/vehicles__services/{service}"),
        ("Routine page with panels", "GET", f"/t/routines__routines/{routine}"),
        ("Home care job page", "GET", f"/t/home_care__jobs/{job}"),
        ("Stock items list", "GET", "/t/stock__items"),
    ]


def time_all(data: Path, modules_dir: Path, repeat: int = 3) -> list[dict]:
    app, client, bucket = client_for(data, modules_dir)
    conn = sqlite3.connect(data / "dashboard.db")
    conn.row_factory = sqlite3.Row
    csrf = app.config["CSRF_TOKEN"]
    rows = []
    for label, method, path in pages(conn, app):
        times, queries, status = [], 0, 0
        for _ in range(repeat):
            bucket.clear()
            began = time.perf_counter()
            if method == "POST":
                response = client.post(path, base_url=BASE, data={"_csrf": csrf})
            else:
                response = client.get(path, base_url=BASE)
            times.append((time.perf_counter() - began) * 1000)
            queries, status = len(bucket), response.status_code
        rows.append({"page": label, "ms": min(times), "median": statistics.median(times), "queries": queries,
                     "status": status, "path": path})
    conn.close()
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, help="folder to keep the invented household in (default: a temporary one)")
    parser.add_argument("--rebuild", action="store_true", help="remove the folder's records and build them again")
    parser.add_argument("--repeat", type=int, default=3, help="times each page is loaded; the fastest is shown")
    args = parser.parse_args(argv)
    folder = args.data or Path(tempfile.mkdtemp(prefix="dashboard-plus-speed-"))
    if args.rebuild and folder.exists():
        shutil.rmtree(folder)
    modules_dir = folder / "modules"
    if not (folder / "data" / "dashboard.db").exists():
        print(f"Building the invented household in {folder} (a few minutes the first time)...")
        began = time.perf_counter()
        counts = build(folder / "data", modules_dir)
        print(f"Built {sum(counts.values()):,} records in {time.perf_counter() - began:.0f} s: "
              + ", ".join(f"{k.split('__')[1]} {v:,}" for k, v in counts.items()))
    rows = time_all(folder / "data", modules_dir, args.repeat)
    print(f"{'Page':<42}{'fastest ms':>11}{'median ms':>11}{'queries':>9}  status")
    for row in rows:
        flag = "  SLOW" if row["ms"] > SLOW_MS else ""
        print(f"{row['page']:<42}{row['ms']:>11.0f}{row['median']:>11.0f}{row['queries']:>9}  {row['status']}{flag}")
    slow = [r for r in rows if r["ms"] > SLOW_MS or r["status"] != 200]
    print(f"{len(slow)} of {len(rows)} pages over {SLOW_MS} ms or not answering normally.")
    return 1 if slow else 0


if __name__ == "__main__":
    raise SystemExit(main())
