"""Tests for the Vehicle running log: odometer readings and service estimates beside Vehicles (decision 0111).

These follow the eight checks in Lane B's draft (its ACCEPTANCE.md, now in git history), plus units from Settings,
the gentle lower and mixed-unit checks, estimates never shown as costs paid, privacy and travel, and switching
the module or Vehicles off. Reading the pages at 320 pixels is done in the browser check and screenshots."""
import io
import re
import shutil
import sqlite3
import zipfile
from datetime import date, datetime, timedelta, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import backups, confirm, db, export, helpers, modules, proposals, records, settings, startup, sync
from dashboard.core import watch
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
import load_example

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
AMOUNT = 987654  # an invented quoted amount: 9,876.54 once stored as cents
SCOPE = "Invented scope sentinel 5521"
NOTE = "Invented private note 8830"
LOWER = "This is lower than the last reading. Check the vehicle and unit before saving."
HIGHER = "This is higher than a later reading. Check the date, vehicle and unit before saving."
MIXED = ("The reading before this one for this vehicle is in km. Dashboard does not convert miles and kilometres. "
         "Check the unit on the odometer before saving.")
CAVEAT = "Check what each quote includes. These are estimates, not a final price."
READINGS, ESTIMATES = "vehicle_running__readings", "vehicle_running__estimates"


class RunningTestCase(TempDirTestCase):
    MODULES = ("people", "stock", "vehicles", "vehicle_running")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)
        self.car = self.records.create("vehicles__vehicles", {"name": "Family car"})
        self.service = self.records.create("vehicles__services", {"vehicle": self.car, "name": "Routine service",
                                                                  "next_due": (date.today() + timedelta(days=12)).isoformat()})
        self.dealer = self.records.create("people__people", {"name": "Example Motors"})

    def reading(self, distance, at="2026-11-20T09:00:00", unit="km", vehicle=None):
        return self.records.create(READINGS, {"vehicle": vehicle or self.car, "read_at": at, "distance": distance,
                                              "unit": unit})

    def estimate(self, kind="dealer", **values):
        values = {"service": self.service, "kind": kind, "quoted_on": "2026-11-18", **values}
        return self.records.create(ESTIMATES, values)

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None):
        return (client or self.client()).get(path, base_url=BASE).get_data(as_text=True)

    def post(self, client, path, **form):
        return client.post(path, data={"_csrf": client.csrf, **form}, base_url=BASE)

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE deleted_at IS NULL").fetchone()[0]

    def export_text(self):
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 21, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return " ".join(archive.read(n).decode("utf-8-sig") for n in archive.namelist())


class AcceptanceTests(RunningTestCase):
    def test_1_examples_link_each_reading_to_a_vehicle_and_each_estimate_to_a_service_and_unknown_ones_are_refused(self):
        self.assertEqual(self.report.module_problems, {})
        for name, vehicle, service, unit in (("smith", "Family car", "Routine service", "km"),
                                             ("garcia", "Household car", "Oil change and inspection", "mi"),
                                             ("taylor", "Small car", "MOT test", "mi")):
            with self.subTest(household=name):
                data = self.tmp / name
                load_example.load(name, data)
                conn = sqlite3.connect(data / "dashboard.db")
                self.addCleanup(conn.close)
                readings = conn.execute(f"SELECT v.name, r.unit FROM {READINGS} r JOIN vehicles__vehicles v "
                                        f"ON v.id = r.vehicle").fetchall()
                self.assertTrue(readings)
                self.assertEqual({r for r in readings}, {(vehicle, unit)})
                quotes = conn.execute(f"SELECT s.name FROM {ESTIMATES} e JOIN vehicles__services s "
                                      f"ON s.id = e.service").fetchall()
                self.assertTrue(quotes)
                self.assertEqual({q[0] for q in quotes}, {service})
        for bad in ({"vehicle": 99999}, {"vehicle": "Family car"}):
            with self.assertRaises(records.ValidationError):
                self.records.create(READINGS, {"read_at": "2026-11-20T09:00", "distance": 1, "unit": "km", **bad})
        with self.assertRaises(records.ValidationError):
            self.records.create(ESTIMATES, {"service": 99999, "kind": "dealer", "quoted_on": "2026-11-18"})

    def test_2_same_day_readings_stay_separate_a_lower_or_mixed_unit_one_asks_first_and_a_correction_keeps_history(self):
        client = self.client()
        self.reading(48500, "2026-11-20T09:00:00")
        second = self.reading(48512, "2026-11-20T17:30:00")
        self.assertEqual(self.count(READINGS), 2)
        car = self.page(f"/t/vehicles__vehicles/{self.car}", client)
        self.assertIn("reading 1 of 2 that day", car)
        self.assertIn("Last recorded: 48,512 km on 20/11/26 · 2 readings recorded", car)
        form = {"vehicle": self.car, "read_at": "2026-11-21T08:00", "distance": "48000", "unit": "km", "then": "done"}
        held = self.post(client, f"/t/{READINGS}/new", **form)
        self.assertEqual(held.status_code, 200)
        text = held.get_data(as_text=True)
        self.assertIn(LOWER, text)
        self.assertIn("Nothing is saved yet.", text)
        self.assertIn("Go back", text)
        self.assertIn("Save as entered", text)
        self.assertEqual(self.count(READINGS), 2)
        token = re.search(r'name="_confirm" value="([^"]+)"', text).group(1)
        changed = self.post(client, f"/t/{READINGS}/new", **dict(form, distance="47000", _confirm=token, then=""))
        self.assertIn(LOWER, changed.get_data(as_text=True))  # a changed value is checked again
        self.assertEqual(self.count(READINGS), 2)
        saved = self.post(client, f"/t/{READINGS}/new", **dict(form, _confirm=token, then="", _then="done"))
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(self.count(READINGS), 3)  # rollover or correction: both readings kept, nothing erased
        mixed = self.post(client, f"/t/{READINGS}/new", **dict(form, read_at="2026-11-22T08:00", distance="30100",
                                                               unit="mi"))
        self.assertIn(MIXED, mixed.get_data(as_text=True))
        self.assertNotIn(LOWER, mixed.get_data(as_text=True))  # km and mi are never compared as numbers
        self.assertEqual(self.count(READINGS), 3)
        late = self.post(client, f"/t/{READINGS}/new", **dict(form, read_at="2026-11-19T08:00", distance="49000"))
        self.assertIn(HIGHER, late.get_data(as_text=True))
        correction = {"vehicle": self.car, "read_at": "2026-11-20T17:30", "distance": "48521", "unit": "km"}
        asked = self.post(client, f"/t/{READINGS}/{second}", **correction)
        self.assertIn(HIGHER, asked.get_data(as_text=True))  # the 48,000 saved as entered the next morning
        token = re.search(r'name="_confirm" value="([^"]+)"', asked.get_data(as_text=True)).group(1)
        fixed = self.post(client, f"/t/{READINGS}/{second}", **correction, _confirm=token)
        self.assertEqual(fixed.status_code, 302)
        history = self.records.history(READINGS, second)
        self.assertEqual([h["action"] for h in history], ["create", "update"])
        self.assertEqual(history[-1]["before"]["distance"], 48512)
        page = self.page(f"/t/vehicles__vehicles/{self.car}", client)
        self.assertIn("Corrected on", page)
        for invented in ("km travelled", "travelled since", "per day", "average", "km since", "due at", "Service due"):
            self.assertNotIn(invented, page)

    def test_3_two_estimates_show_their_own_kind_dates_and_scope_with_no_cheapest_or_same_work_claim(self):
        self.estimate("dealer", provider=self.dealer, quoted_on="2026-11-18", good_until="2026-12-18",
                      amount="410", scope="Dealer scope words")
        self.estimate("independent", quoted_on="2026-11-19", amount="330", scope="Independent scope words")
        client = self.client()
        page = self.page(f"/t/vehicles__services/{self.service}", client)
        for shown in ("Cost estimates", CAVEAT, "Dealer", "Independent", "Example Motors", "18/11/26", "19/11/26",
                      "18/12/26", "Show estimated cost and scope", "Add estimate"):
            self.assertIn(shown, page)
        for claim in ("cheapest", "Cheapest", "recommend", "Recommended", "same work", "best value", "save "):
            self.assertNotIn(claim, page)
        self.assertNotIn("Dealer scope words", page)  # behind Show
        ids = [r[0] for r in self.conn.execute(f"SELECT id FROM {ESTIMATES} ORDER BY id")]
        shown = [client.get(f"/t/{ESTIMATES}/{i}/reveal?column=scope", base_url=BASE).get_json()["text"] for i in ids]
        self.assertEqual(shown, ["Dealer scope words", "Independent scope words"])
        self.assertEqual(client.get(f"/t/{ESTIMATES}/{ids[0]}/reveal?column=amount", base_url=BASE).get_json()["text"],
                         "410.00")
        with self.assertRaises(records.ValidationError):  # no quote good until before it was quoted
            self.estimate("other", quoted_on="2026-11-18", good_until="2026-11-01")

    def test_4_the_service_date_still_reminds_and_nothing_claims_a_distance_due(self):
        self.reading(48500)
        self.estimate(amount="410")
        found = [e for e in watch.expiring(self.conn, self.registry) if e.table == "vehicles__services"]
        self.assertEqual(len(found), 1)
        self.assertIn("in 12 days", found[0].detail)
        attention = self.page("/attention")
        self.assertIn("Routine service", attention)
        self.assertIn("in 12 days", attention)
        for claim in ("48,500", "48500", "km", "410", "estimate", "Service due at"):
            self.assertNotIn(claim, attention)
        module = modules.load_module(ROOT / "modules" / "vehicle_running")
        self.assertEqual({t: tb.watch for t, tb in module.tables.items()}, {"readings": {}, "estimates": {}})
        self.assertNotIn("due_at_distance", modules.load_module(ROOT / "modules" / "vehicles").tables["services"].columns)

    def test_5_private_amount_scope_and_notes_stay_behind_show_and_out_of_lists_exports_helpers_and_the_change_log(self):
        quote = self.estimate(amount=str(AMOUNT / 100), scope=SCOPE, notes=NOTE)
        sentinels = ("9,876.54", "9876.54", SCOPE, NOTE)
        client = self.client()
        for path in ("/", "/attention", f"/t/{ESTIMATES}", f"/t/{ESTIMATES}/{quote}", f"/t/vehicles__services/{self.service}",
                     f"/t/vehicles__vehicles/{self.car}", "/sheet/vehicles/vehicles"):
            with self.subTest(path=path):
                text = self.page(path, client)
                for private in sentinels:
                    self.assertNotIn(private, text)
        text = self.export_text()
        for private in sentinels:
            self.assertNotIn(private, text)
        _, key = helpers.issue(self.conn, self.data, "Car reader", "read", ["vehicle_running", "vehicles"])
        reply = client.get(f"/api/v1/tables/{ESTIMATES}/records", base_url=BASE,
                           headers={"Authorization": f"Bearer {key}"}).get_data(as_text=True)
        self.assertIn("dealer", reply)
        for private in sentinels + ("98765400",):
            self.assertNotIn(private, reply)
        log = sync.changes(self.conn, 0, limit=100000)
        created = next(e for e in log if e["table_name"] == ESTIMATES and e["action"] == "create")
        # User 1, 24 November: quote amounts and scope travel to the household's other computers; notes stay here.
        self.assertEqual(sorted(created["withheld"]), ["notes"])
        self.assertIn(SCOPE, str(log))
        self.assertNotIn(NOTE, str(log))
        backups.daily(self.data, today=date(2026, 6, 1))
        kept = sqlite3.connect(self.data / "backups" / "daily-2026-06-01.db")
        self.addCleanup(kept.close)
        self.assertEqual(kept.execute(f"SELECT amount, scope, notes FROM {ESTIMATES}").fetchone(), (AMOUNT, SCOPE, NOTE))

    def test_6_private_fields_say_where_they_travel_and_a_suggestion_waits_for_review(self):
        client = self.client()
        form = self.page(f"/t/{ESTIMATES}/new", client)
        self.assertGreaterEqual(form.count("shared with paired household computers"), 2)
        self.assertIn("not a final bill or a cost paid", form)
        module = modules.load_module(ROOT / "modules" / "vehicle_running")
        travel = {n: c.travels for n, c in module.tables["estimates"].columns.items()}
        self.assertEqual({n for n, t in travel.items() if t == "never"}, {"notes"})
        self.assertTrue(all(c.travels == "always" for c in module.tables["readings"].columns.values()))
        helper, _ = helpers.issue(self.conn, self.data, "Car helper", "suggest", ["vehicle_running", "vehicles"])
        with self.assertRaises(proposals.ProposalError) as refused:
            proposals.submit(self.conn, self.registry, helper, {"request_key": "q1", "why": "From the quote",
                             "entries": [{"table": ESTIMATES, "values": {"service": self.service, "kind": "dealer",
                                                                         "quoted_on": "2026-11-18", "amount": 410}}]})
        self.assertEqual(refused.exception.code, "private_detail")
        body = {"request_key": "r1", "why": "Seen on the dashboard photo",
                "entries": [{"table": READINGS, "values": {"vehicle": self.car, "read_at": "2026-11-21T08:00",
                                                           "distance": 48600, "unit": "km"}}]}
        result, _ = proposals.submit(self.conn, self.registry, helper, body)
        again, _ = proposals.submit(self.conn, self.registry, helper, body)
        self.assertEqual(result["batch_id"], again["batch_id"])  # the same request key adds no second row
        self.assertEqual(proposals.pending_count(self.conn), 1)
        self.assertEqual(self.count(READINGS), 0)  # nothing accepted before Review
        proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])
        self.assertEqual(self.count(READINGS), 1)

    def test_7_a_vehicle_or_service_with_history_cannot_be_deleted_until_the_household_resolves_it(self):
        reading = self.reading(48500)
        quote = self.estimate(amount="410")
        for table, record in (("vehicles__vehicles", self.car), ("vehicles__services", self.service)):
            with self.assertRaises(records.ValidationError, msg=table):
                self.records.delete(table, record)
        self.records.delete(READINGS, reading)
        with self.assertRaises(records.ValidationError):  # the service's quote still stops the vehicle going
            self.records.delete("vehicles__vehicles", self.car)
        self.assertIsNone(self.records.get("vehicles__services", self.service)["deleted_at"])
        self.assertIsNone(self.records.get(ESTIMATES, quote)["deleted_at"])
        client = self.client()
        refused = self.post(client, f"/t/vehicles__services/{self.service}/delete")
        self.assertEqual(refused.status_code, 409)
        self.assertIn("still point at it", refused.get_data(as_text=True))
        self.records.delete(ESTIMATES, quote)
        self.records.delete("vehicles__vehicles", self.car)  # now deliberate, and nothing is left behind

    def test_8_a_thousand_readings_and_a_hundred_estimates_page_sort_steadily_and_show_the_latest(self):
        start = datetime(2024, 1, 1, 8, 0)
        rows = [(self.car, (start + timedelta(hours=12 * (i // 2))).isoformat(timespec="seconds"), 10000 + i, "km")
                for i in range(1000)]
        with db.transaction(self.conn):
            for row in rows:
                self.conn.execute(f"INSERT INTO {READINGS} (created_at, updated_at, vehicle, read_at, distance, unit, "
                                  f"global_id, row_revision) VALUES ('t', 't', ?, ?, ?, ?, lower(hex(randomblob(16))), 1)",
                                  row)
            for i in range(100):
                self.conn.execute(f"INSERT INTO {ESTIMATES} (created_at, updated_at, service, kind, quoted_on, "
                                  f"global_id, row_revision) VALUES ('t', 't', ?, 'other', ?, lower(hex(randomblob(16))), 1)",
                                  (self.service, (date(2026, 1, 1) + timedelta(days=i)).isoformat()))
        client = self.client()
        car = self.page(f"/t/vehicles__vehicles/{self.car}", client)
        self.assertIn("Last recorded: 10,999 km on", car)
        self.assertIn("1,000 readings recorded", car)
        self.assertIn("The latest 50 of 1,000 readings are shown here", car)
        self.assertEqual(len(re.findall(rf'href="/t/{READINGS}/\d+"', car)), 50)
        service = self.page(f"/t/vehicles__services/{self.service}", client)
        self.assertEqual(len(re.findall(rf'href="/t/{ESTIMATES}/\d+"', service)), 50)
        self.assertIn("The latest 50 of 100 are shown.", service)
        self.assertIn("10/04/26", service)  # the newest quote first
        first = self.records.page(READINGS, order_by="read_at", descending=True, limit=4)
        self.assertEqual([r["distance"] for r in first], [10999, 10998, 10997, 10996])  # same time: id breaks the tie
        grid = self.page(f"/t/{READINGS}?sort=read_at&desc=1", client)
        self.assertEqual(len(set(re.findall(rf'/t/{READINGS}/(\d+)', grid))), 50)  # the list loads a page at a time


class UnitsAndChecksTests(RunningTestCase):
    def test_the_unit_starts_from_settings_or_the_country_and_is_never_converted(self):
        client = self.client()

        def chosen():
            form = self.page(f"/t/{READINGS}/new", client)
            return re.search(r'<option value="(km|mi)"\s*selected', form).group(1)

        self.assertEqual(chosen(), "km")
        settings.put(self.conn, "household.country", "United Kingdom")
        self.assertEqual(chosen(), "mi")
        settings.put(self.conn, "household.distance_unit", "km")
        self.assertEqual(chosen(), "km")
        page = self.page("/settings", client)
        self.assertIn("Odometers usually show", page)
        self.assertIn("nothing is converted", page)
        self.reading(48500, unit="km")
        self.reading(30200, at="2026-11-21T09:00:00", unit="mi")
        car = self.page(f"/t/vehicles__vehicles/{self.car}", client)
        self.assertIn("Last recorded: 30,200 mi on 21/11/26", car)
        self.assertIn("Not drawn: recorded in km, not mi", car)
        self.assertEqual(car.count('class="chart-dot"'), 1)

    def test_settings_refuses_an_unknown_unit(self):
        client = self.client()
        page = self.page("/settings", client)
        form = {"_csrf": client.csrf, "distance_unit": "furlongs", "week_starts": "monday",
                "modules": list(self.MODULES), "people": "2"}
        reply = client.post("/settings", data=form, base_url=BASE)
        self.assertEqual(reply.status_code, 422)
        self.assertIn("Choose kilometres or miles.", reply.get_data(as_text=True))
        self.assertIn("distance_unit", page)

    def test_the_check_compares_only_the_same_vehicle_and_unit_and_ignores_deleted_readings(self):
        info = self.registry[READINGS]
        other = self.records.create("vehicles__vehicles", {"name": "Trailer"})
        self.reading(48500)
        self.reading(900, vehicle=other)
        new = {"vehicle": self.car, "read_at": "2026-11-21T09:00:00", "distance": 48600, "unit": "km"}
        self.assertEqual(confirm.warnings(self.conn, info, new), [])
        self.assertEqual([w.key for w in confirm.warnings(self.conn, info, dict(new, distance=1000))], ["lower"])
        self.assertEqual([w.key for w in confirm.warnings(self.conn, info, dict(new, vehicle=other, distance=1000))], [])
        self.assertEqual([w.key for w in confirm.warnings(self.conn, info, dict(new, unit="mi", distance=10))], ["unit"])
        first = self.conn.execute(f"SELECT id FROM {READINGS} WHERE distance = 48500").fetchone()[0]
        self.records.delete(READINGS, first)
        self.assertEqual(confirm.warnings(self.conn, info, dict(new, distance=1000)), [])
        found = confirm.warnings(self.conn, info, dict(new, distance=1000))
        self.assertEqual(confirm.unconfirmed(found, []), [])


class EstimatesAreNotCostsTests(RunningTestCase):
    def test_no_page_totals_or_calls_an_estimate_paid_or_spent(self):
        self.estimate(amount="410", scope="Example")
        self.estimate("independent", amount="330")
        client = self.client()
        for path in (f"/t/{ESTIMATES}", f"/t/vehicles__services/{self.service}", f"/t/vehicles__vehicles/{self.car}",
                     "/", "/attention", "/to-do"):
            text = self.page(path, client)
            for word in ("740", "Total", "total cost", "paid", "spent", "Cost paid"):
                self.assertNotIn(word, text, f"{path}: {word}")
        module = modules.load_module(ROOT / "modules" / "vehicle_running")
        self.assertIn("An estimate, not a bill.", module.tables["estimates"].description)
        from dashboard.web import display
        listed = [c.name for c in display.list_columns(self.registry[ESTIMATES])]
        self.assertEqual(listed, ["service", "kind", "provider", "quoted_on", "good_until"])  # never the amount


class SwitchingOffTests(RunningTestCase):
    def snapshot(self):
        return {t: [tuple(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY id")]
                for t in (READINGS, ESTIMATES, "vehicles__vehicles", "vehicles__services")}

    def test_switching_it_off_hides_it_keeps_records_and_vehicles_work_alone(self):
        self.reading(48500)
        self.estimate(amount="410")
        client = self.client()
        before = self.snapshot()
        settings.set_module_enabled(self.conn, "vehicle_running", False)
        for path in (f"/t/{READINGS}", f"/t/{ESTIMATES}", f"/charts/{READINGS}"):
            self.assertEqual(client.get(path, base_url=BASE).status_code, 404, path)
        car = self.page(f"/t/vehicles__vehicles/{self.car}", client)
        self.assertNotIn("Recorded readings", car)
        self.assertNotIn("Add a reading", car)
        self.assertNotIn("Cost estimates", self.page(f"/t/vehicles__services/{self.service}", client))
        self.assertIn("Routine service", self.page("/attention", client))
        self.assertEqual(self.snapshot(), before)
        settings.set_module_enabled(self.conn, "vehicle_running", True)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("Last recorded: 48,500 km", self.page(f"/t/vehicles__vehicles/{self.car}", client))

    def test_vehicles_cannot_be_switched_off_while_the_running_log_is_on(self):
        client = self.client()
        chosen = [m for m in self.MODULES if m != "vehicles"]
        reply = client.post("/settings", data={"_csrf": client.csrf, "modules": chosen, "people": "2",
                                               "week_starts": "monday", "distance_unit": "km"}, base_url=BASE)
        self.assertEqual(reply.status_code, 422)
        self.assertIn("Vehicle running log needs Vehicles", reply.get_data(as_text=True))
        self.assertIn("vehicles", settings.enabled_modules(self.conn))


class ModuleFileTests(RunningTestCase):
    def test_the_migration_matches_and_only_makes_its_own_tables(self):
        module = modules.load_module(ROOT / "modules" / "vehicle_running")
        self.assertIsNone(next_migration_sql(module))
        self.assertEqual(sorted(module.requires), ["people", "vehicles"])
        sql = (ROOT / "modules" / "vehicle_running" / "migrations" / "0001_update_tables.sql").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"CREATE TABLE (\S+)", sql), [READINGS, ESTIMATES])
        self.assertIn("vehicles__vehicles(id) ON DELETE RESTRICT", sql)
        self.assertIn("vehicles__services(id) ON DELETE RESTRICT", sql)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")

    def check(self, table: dict, labels: dict | None = None) -> list[str]:
        problems = []
        tables = modules._check_tables("t", {"tables": {"x": {"title": "X", "description": "d", **table}}}, [], problems)
        if labels is not None:
            modules._check_labels({"tables": {"x": labels}}, tables, problems)
        return problems

    COLUMNS = {"who": {"type": "link", "to": "x", "required": True}, "at": {"type": "datetime", "required": True},
               "n": {"type": "integer", "required": True}, "u": {"type": "choice", "required": True,
                                                                   "choices": ["km", "mi"]},
               "secret": {"type": "text", "sensitive": True, "travels": "never"}}

    def test_the_checker_explains_wrong_confirm_chart_under_and_default_from_in_plain_words(self):
        good = {"key": "lower", "when": "lower", "column": "n", "per": "who", "order": "at", "message": "Lower.",
                "later": "Higher."}
        self.assertEqual(self.check({"columns": self.COLUMNS, "confirm": [good]}), [])
        for bad, words in (({"when": "smaller"}, "'when' must be"), ({"column": "secret"}, "not private"),
                           ({"per": "n"}, "'per' must name"), ({"order": "n"}, "'order' must name"),
                           ({"later": ""}, "'later' must be"), ({"among": "nope"}, "'among' names")):
            with self.subTest(bad=bad):
                self.assertIn(words, " ".join(self.check({"columns": self.COLUMNS, "confirm": [{**good, **bad}]})))
        twice = self.check({"columns": self.COLUMNS, "confirm": [good, good]})
        self.assertIn("its own 'key'", " ".join(twice))
        chart = {"kind": "dots", "x": "at", "y": "n", "per": "who", "what": ["r", "rs"], "entry": ["r", "rs"],
                 "subject": "car", "unit": "u"}
        self.assertEqual(self.check({"columns": self.COLUMNS, "chart": chart}), [])
        self.assertIn("'unit' names", " ".join(self.check({"columns": self.COLUMNS, "chart": {**chart, "unit": "n"}})))
        unit = {**self.COLUMNS, "u": {**self.COLUMNS["u"], "default_from": "distance_unit"}}
        self.assertEqual(self.check({"columns": unit}), [])
        wrong = {**self.COLUMNS, "n": {**self.COLUMNS["n"], "default_from": "distance_unit"}}
        self.assertIn("'default_from' names", " ".join(self.check({"columns": wrong})))
        under = {"link": "who", "title": "Quotes", "columns": ["n", "secret"], "reveal": "Show"}
        self.assertEqual(self.check({"columns": self.COLUMNS}, {"under": under}), [])
        for bad, words in (({"link": "n"}, "'link' must"), ({"columns": ["nope"]}, "'columns' lists"),
                           ({"columns": ["n"]}, "'reveal' is"), ({"order": "secret"}, "'order' names")):
            with self.subTest(under=bad):
                self.assertIn(words, " ".join(self.check({"columns": self.COLUMNS}, {"under": {**under, **bad}})))
