"""Tests for the Home layout module: gaps asked and cleared, checks shown as due, the Our home sheet, and shared places.

These follow the checks in Lane B's Home layout draft (its ACCEPTANCE.md, now in git history) that apply
when Home layout uses Household stock's places instead of moving them (decision 0054)."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5131
BASE = f"http://127.0.0.1:{PORT}"
WATER = "Where is the water shut-off? It is not written down yet."
POWER = "Where is the power board (switchboard or fuse box)? It is not written down yet."
EXITS = "Which ways out of your home would you use? None is written down yet."
ALARMS = "Where are your smoke alarms? None is written down yet."
CODE = "SYNTH-4417"


class HomeLayoutModuleTests(TempDirTestCase):
    MODULES = ("home_layout", "medical", "people", "stock")

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
        self.today = date.today()

    def day(self, offset):
        return (self.today + timedelta(days=offset)).isoformat()

    def gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("home_layout__")]

    def place(self, *path):
        """Make nested places (Kitchen, Pantry, Shelf 3) and give back the last one's id."""
        inside = None
        for name in path:
            inside = self.records.create("stock__places", {"name": name, "inside": inside})
        return inside

    def sheet(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client.get("/sheet/home_layout/our_home", base_url=BASE).get_data(as_text=True)

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertIn("home_layout", self.report.modules)

    def test_it_uses_household_stocks_places_and_has_none_of_its_own(self):
        self.assertNotIn("home_layout__places", self.registry)
        module = modules.load_module(ROOT / "modules" / "home_layout")
        self.assertEqual(module.requires, ["stock"])
        for table in module.tables.values():
            self.assertEqual(table.columns["place"].to, "stock.places", table.name)

    def test_an_empty_home_is_asked_about_not_told_off(self):
        self.assertEqual(self.gaps(), [EXITS, WATER, POWER, ALARMS])
        for message in self.gaps():
            self.assertIn("?", message)

    def test_gas_is_never_asked_about_because_many_homes_have_none(self):
        self.assertNotIn("gas", " ".join(self.gaps()).lower())

    def test_each_question_stops_once_it_is_answered(self):
        garage = self.place("Garage")
        self.records.create("home_layout__shutoffs", {"name": "Water main", "kind": "water", "place": garage})
        self.assertEqual(self.gaps(), [EXITS, POWER, ALARMS])
        self.records.create("home_layout__shutoffs", {"name": "Power board", "kind": "power", "place": garage})
        self.records.create("home_layout__exits", {"name": "Front door", "place": self.place("Front hall")})
        self.assertEqual(self.gaps(), [ALARMS])
        self.records.create("home_layout__equipment", {"name": "Hall smoke alarm", "kind": "smoke_alarm",
                                                       "place": self.place("Hall"), "next_check": self.day(90)})
        self.assertEqual(self.gaps(), [])

    def test_a_gas_shut_off_does_not_answer_the_water_question(self):
        self.records.create("home_layout__shutoffs", {"name": "Gas valve", "kind": "gas", "place": self.place("Kitchen")})
        self.assertIn(WATER, self.gaps())

    def test_a_record_without_a_place_or_a_test_date_is_asked_about(self):
        self.records.create("home_layout__shutoffs", {"name": "Water main", "kind": "water"})
        alarm = self.records.create("home_layout__equipment", {"name": "Hall smoke alarm", "kind": "smoke_alarm"})
        self.records.create("home_layout__equipment", {"name": "Fire blanket", "kind": "fire_blanket",
                                                       "place": self.place("Kitchen")})
        found = self.gaps()
        self.assertIn("Which place is Water main in? Choose where to find it.", found)
        self.assertIn("Which place is Hall smoke alarm in? Choose where to find it.", found)
        self.assertIn("When do you plan to test Hall smoke alarm again?", found)
        self.assertNotIn("When do you plan to test Fire blanket again?", found)  # only smoke alarms are asked
        self.records.update("home_layout__equipment", alarm, {"place": self.place("Hall"), "next_check": self.day(60)})
        self.assertEqual([m for m in self.gaps() if "smoke alarm" in m], [])

    def test_a_check_is_due_or_overdue_never_expired(self):
        self.records.create("home_layout__equipment", {"name": "Hall smoke alarm", "kind": "smoke_alarm",
                                                       "next_check": self.day(10)})
        self.records.create("home_layout__equipment", {"name": "Extinguisher", "kind": "fire_extinguisher",
                                                       "next_check": self.day(-3)})
        self.records.create("home_layout__equipment", {"name": "Kitchen alarm", "kind": "smoke_alarm",
                                                       "next_check": self.day(200)})
        details = {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)}
        self.assertTrue(details["Hall smoke alarm"].startswith("check due"), details)
        self.assertIn("overdue", details["Extinguisher"])
        self.assertNotIn("Kitchen alarm", details)
        self.assertNotIn("expire", " ".join(details.values()))

    def test_no_date_is_invented_when_the_household_gives_none(self):
        self.records.create("home_layout__equipment", {"name": "Hall smoke alarm", "kind": "smoke_alarm",
                                                       "last_tested": self.day(-400), "battery_changed": self.day(-400)})
        self.assertEqual(watch.expiring(self.conn, self.registry, self.today), [])
        row = self.conn.execute("SELECT next_check FROM home_layout__equipment").fetchone()
        self.assertIsNone(row["next_check"])

    def test_sheet_shows_full_place_paths_and_prints_nothing_private(self):
        shelf = self.place("Kitchen", "Pantry", "Shelf 3")
        garage = self.place("Garage")
        self.records.create("home_layout__exits", {"name": "Front door", "floor": "Ground floor", "place": garage,
                                                   "route": "Down the main stairs", "notes": "Key is with Person B"})
        self.records.create("home_layout__shutoffs", {"name": "Water main", "kind": "water", "place": garage,
                                                      "how_to_find": "Beside the grey shelves",
                                                      "notes": "Needs the long spanner"})
        self.records.create("home_layout__equipment", {"name": "Fire blanket", "kind": "fire_blanket", "place": shelf,
                                                       "notes": "Bought second-hand"})
        self.records.create("home_layout__meters", {"name": "Electricity meter", "kind": "electricity",
                                                    "place": garage, "how_to_find": "Inside the grey box"})
        page = self.sheet()
        for shown in ("Our home", "Kitchen › Pantry › Shelf 3", "Front door", "Down the main stairs", "Water shut-off",
                      "Beside the grey shelves", "Fire blanket", "Electricity meter", "Inside the grey box"):
            self.assertIn(shown, page)
        for private in ("Key is with Person B", "Needs the long spanner", "Bought second-hand"):
            self.assertNotIn(private, page)

    def test_codes_are_never_kept_and_a_code_saved_before_is_retired_unseen(self):
        """Decision 0141 (replacing 0077's private box): who to ask is kept, never the code; an old code stays unseen."""
        module = modules.load_module(ROOT / "modules" / "home_layout")
        for table in ("exits", "shutoffs", "equipment", "meters"):
            self.assertNotIn("access_details", module.tables[table].columns, table)
            old = module.tables[table].retired["access_details"]
            self.assertEqual((old.sensitive, old.travels), (True, "never"), table)
            self.assertEqual(module.tables[table].columns["access_hint"].guard, "where_kept", table)
        sheet_text = (ROOT / "modules" / "home_layout" / "sheets.toml").read_text(encoding="utf-8")
        self.assertNotIn("access_details", sheet_text)
        garage = self.place("Garage")
        with self.assertRaises(records.ValidationError):
            self.records.create("home_layout__exits", {"name": "Back door", "place": garage, "access_details": CODE})
        with self.assertRaises(records.ValidationError):
            self.records.create("home_layout__exits", {"name": "Back door", "place": garage, "access_hint": "4417"})
        ids = {
            "exits": self.records.create("home_layout__exits", {"name": "Front door", "place": garage,
                                                               "access_hint": "Ask Alex next door"}),
            "shutoffs": self.records.create("home_layout__shutoffs", {"name": "Water main", "kind": "water",
                                                                      "place": garage}),
            "equipment": self.records.create("home_layout__equipment", {"name": "Alarm panel", "kind": "other",
                                                                        "place": garage}),
            "meters": self.records.create("home_layout__meters", {"name": "Electricity meter", "kind": "electricity",
                                                                  "place": garage}),
        }
        for table, record in ids.items():  # saved before decision 0141
            self.conn.execute(f"UPDATE home_layout__{table} SET access_details = ? WHERE id = ?", (CODE, record))
        self.conn.commit()
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        paths = ["/sheet/home_layout/our_home", "/attention", "/"] + [f"/t/home_layout__{t}" for t in ids]
        paths += [f"/t/home_layout__{t}/{i}" for t, i in ids.items()]
        for path in paths:
            with self.subTest(path=path):
                self.assertNotIn(CODE, client.get(path, base_url=BASE).get_data(as_text=True))
        for table, record in ids.items():
            shown = client.post(f"/t/home_layout__{table}/{record}/reveal", data={"column": "access_details", "_csrf": client.application.config["CSRF_TOKEN"]}, base_url=BASE, headers={"Accept": "application/json"})
            self.assertEqual(shown.status_code, 404)
        form = client.get(f"/t/home_layout__exits/{ids['exits']}", base_url=BASE).get_data(as_text=True)
        self.assertIn("Who to ask, or where the code is kept", form)
        self.assertIn("Ask Alex next door", form)

    def test_moving_a_cupboard_updates_the_sheet(self):
        """Lane B check 4: move the parent and every path shown follows; nothing else changes."""
        kitchen, garage = self.place("Kitchen"), self.place("Garage")
        pantry = self.records.create("stock__places", {"name": "Pantry", "inside": kitchen})
        self.records.create("home_layout__equipment", {"name": "Fire blanket", "kind": "fire_blanket", "place": pantry})
        self.assertIn("Kitchen › Pantry", self.sheet())
        self.records.update("stock__places", pantry, {"inside": garage})
        page = self.sheet()
        self.assertIn("Garage › Pantry", page)
        self.assertNotIn("Kitchen › Pantry", page)

    def test_a_place_that_something_here_points_at_cannot_be_deleted(self):
        """Lane B checks 8 and 16: never strand a record by deleting its place."""
        rows = (("home_layout__exits", {"name": "Front door"}),
                ("home_layout__shutoffs", {"name": "Water main", "kind": "water"}),
                ("home_layout__equipment", {"name": "Hall smoke alarm", "kind": "smoke_alarm"}),
                ("home_layout__meters", {"name": "Water meter", "kind": "water"}))
        for table, values in rows:
            with self.subTest(table=table):
                place = self.place(f"Place for {values['name']}")
                record = self.records.create(table, {**values, "place": place})
                with self.assertRaises(records.ValidationError):
                    self.records.delete("stock__places", place)
                self.records.update(table, record, {"place": None})
                self.records.delete("stock__places", place)

    def test_switching_it_on_moves_nothing_in_stock_or_medical(self):
        """A household that already had places, items and a kit keeps every one exactly as it was."""
        before_dir = self.tmp / "before"
        for name in ("medical", "people", "stock"):
            shutil.copytree(ROOT / "modules" / name, before_dir / "modules" / name)
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        old = records.Records(conn, records.build_registry(report.loaded))
        kitchen = old.create("stock__places", {"name": "Kitchen pantry shelf"})  # an old flat name stays flat
        old.create("stock__items", {"name": "Kidney beans", "category": "pantry", "quantity": 3, "place": kitchen})
        old.create("medical__kits", {"name": "Hall kit", "kept": "home", "place": kitchen})
        tables = ("stock__places", "stock__items", "stock__lots", "stock__movements", "medical__kits")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        conn.close()

        shutil.copytree(ROOT / "modules" / "home_layout", before_dir / "modules" / "home_layout")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        self.assertEqual(report.module_problems, {})
        self.assertIn("home_layout", report.modules)
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        after = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        self.assertEqual(after, snapshot)
        new = records.Records(conn, records.build_registry(report.loaded))
        new.create("home_layout__shutoffs", {"name": "Water main", "kind": "water", "place": kitchen})
        with self.assertRaises(records.ValidationError):
            new.delete("stock__places", kitchen)

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "home_layout")))
