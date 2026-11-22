"""Tests for the Utilities module: services linked to People and to an exact Home layout meter, a printed fault phone, a private account reference.

These follow the 12 checks in Lane B's draft (its ACCEPTANCE.md, now in git history) that a computer can run (decision 0099).
Checks about reading a screen at 320 pixels wide and printing on A4 and Letter are done in the browser check and screenshots."""
import io
import re
import shutil
import zipfile
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import backups, db, export, helpers, modules, records, restore, settings, startup, watch
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
import load_example

PORT = 5137
BASE = f"http://127.0.0.1:{PORT}"
ACCOUNT = "DEMO-ACCT-7731"
PRIVATE_NOTE = "Invented private note 4412"
NO_CONTACT = "Who would you contact about a fault with Home electricity? Add a People contact if you have one."
NO_PHONE = "What is the fault-line number for Home electricity? Add it to the People contact."


class UtilitiesTestCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "utilities")

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
        self.garage = self.records.create("stock__places", {"name": "Garage"})
        self.meter = self.records.create("home_layout__meters", {"name": "Electricity meter", "kind": "electricity",
                                                                 "place": self.garage})
        self.provider = self.records.create("people__people", {"name": "Example Energy"})
        self.faults = self.records.create("people__people", {"name": "Example Energy Faults", "phone": "0491 570 162"})

    def service(self, name="Home electricity", **values):
        values = {"kind": "electricity", "provider": self.provider, "fault_contact": self.faults,
                  "meter": self.meter, **values}
        return self.records.create("utilities__services", {"name": name, **values})

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

    def gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("utilities__")]

    def export(self):
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 21, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return {n: archive.read(n).decode("utf-8-sig") for n in archive.namelist()}


class UtilitiesModuleTests(UtilitiesTestCase):
    def test_1_it_starts_with_its_dependencies_and_the_empty_list_says_what_to_add(self):
        self.assertEqual(self.report.module_problems, {})
        module = modules.load_module(ROOT / "modules" / "utilities")
        self.assertEqual((module.requires, module.optional_requires, module.outbound_hosts),
                         (["people"], ["home_layout"], []))  # Home layout only for the meter (decision 0115)
        client = self.client()
        from dashboard.web import display
        self.assertEqual(display.empty_hint(self.registry["utilities__services"]),
                         "Add one household service and who to contact about a fault.")  # the Home page shows the first such prompt
        self.assertIn("Nothing here yet.", self.page("/t/utilities__services", client))
        for path in ("/t/utilities__services/new", "/sheet/utilities/utility_contacts"):
            self.assertEqual(client.get(path, base_url=BASE).status_code, 200, path)

    def test_2_the_phone_lives_in_people_and_follows_a_change_onto_the_sheet(self):
        self.service()
        sheet = self.page("/sheet/utilities/utility_contacts")
        for shown in ("Utility contacts", "Home electricity", "Example Energy", "Example Energy Faults", "0491 570 162",
                      "Electricity meter"):
            self.assertIn(shown, sheet)
        self.records.update("people__people", self.faults, {"phone": "0491 570 199"})
        later = self.page("/sheet/utilities/utility_contacts")
        self.assertIn("0491 570 199", later)
        self.assertNotIn("0491 570 162", later)
        self.assertNotIn("phone", set(modules.load_module(ROOT / "modules" / "utilities").tables["services"].columns))

    def test_3_the_meter_is_an_exact_row_or_blank_and_never_typed_text(self):
        internet = self.service("Home internet", kind="internet", meter=None)
        self.assertIsNone(self.records.get("utilities__services", internet)["meter"])
        power = self.service()
        self.assertEqual(self.records.get("utilities__services", power)["meter"], self.meter)
        for bad in ("Electricity meter", 99999):
            with self.assertRaises(records.ValidationError, msg=bad):
                self.service("Bad link", meter=bad)
        client = self.client()
        reply = client.post("/t/utilities__services/new", data={"_csrf": client.csrf, "name": "Typed", "kind": "gas",
                                                                 "meter": "Electricity meter"}, base_url=BASE)
        self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM utilities__services WHERE name = 'Typed'").fetchone()[0], 0)
        self.assertIn("Electricity meter", self.page("/t/utilities__services/new", client))  # offered as a choice

    def test_5_moving_the_place_updates_our_home_and_keeps_the_meter_link_and_a_place_with_a_meter_stays(self):
        service = self.service()
        kitchen = self.records.create("stock__places", {"name": "Kitchen"})
        shed = self.records.create("stock__places", {"name": "Shed", "inside": kitchen})
        self.records.update("home_layout__meters", self.meter, {"place": shed})
        self.assertIn("Kitchen › Shed", self.page("/sheet/home_layout/our_home"))
        self.records.update("stock__places", shed, {"inside": self.garage})
        home = self.page("/sheet/home_layout/our_home")
        self.assertIn("Garage › Shed", home)
        self.assertNotIn("Kitchen › Shed", home)
        self.assertEqual(self.records.get("utilities__services", service)["meter"], self.meter)
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", shed)
        self.assertIsNone(self.records.get("stock__places", shed)["deleted_at"])

    def test_6_the_account_reference_and_note_stay_off_lists_sheets_pages_attention_exports_and_helpers_until_shown(self):
        service = self.service(account_number=ACCOUNT, notes=PRIVATE_NOTE)
        client = self.client()
        paths = ["/", "/attention", "/t/utilities__services", f"/t/utilities__services/{service}",
                 "/sheet/utilities/utility_contacts", "/sheet/home_layout/our_home", "/t/people__people"]
        for path in paths:
            with self.subTest(path=path):
                text = self.page(path, client)
                for private in (ACCOUNT, PRIVATE_NOTE):
                    self.assertNotIn(private, text)
        shown = client.get(f"/t/utilities__services/{service}/reveal?column=account_number", base_url=BASE).get_json()
        self.assertEqual(shown["value"], ACCOUNT)  # only the Show button's request returns it
        self.assertEqual(client.get(f"/t/utilities__services/{service}/reveal?column=name", base_url=BASE).status_code, 404)
        for name, text in self.export().items():
            with self.subTest(export=name):
                self.assertNotIn(ACCOUNT, text)
                self.assertNotIn(PRIVATE_NOTE, text)
        _, granted = helpers.issue(self.conn, self.data, "Utilities reader", "read", ["utilities"])
        reply = client.get("/api/v1/tables/utilities__services/records", base_url=BASE,
                           headers={"Authorization": f"Bearer {granted}"})
        self.assertEqual(reply.status_code, 200)
        self.assertIn("Home electricity", reply.get_data(as_text=True))
        for private in (ACCOUNT, PRIVATE_NOTE):
            self.assertNotIn(private, reply.get_data(as_text=True))
        module = modules.load_module(ROOT / "modules" / "utilities")
        columns = module.tables["services"].columns
        self.assertEqual({n for n, c in columns.items() if c.sensitive}, {"account_number", "notes"})
        self.assertEqual({n for n in columns if re.search(r"password|login|code|card|pin", n)}, set())
        form = self.page("/t/utilities__services/new", client)
        self.assertIn("Hidden from lists and print sheets", form)
        self.assertIn("Avoid passwords, login codes and payment card details", form)

    def test_7_missing_contact_and_missing_phone_are_each_asked_and_adding_clears_them(self):
        service = self.service(fault_contact=None)
        self.assertEqual(self.gaps(), [NO_CONTACT])
        nameless = self.records.create("people__people", {"name": "Example Faults Desk"})
        self.records.update("utilities__services", service, {"fault_contact": nameless})
        self.assertEqual(self.gaps(), [NO_PHONE])
        self.assertIn(NO_PHONE, self.page("/attention"))
        self.records.update("people__people", nameless, {"phone": "0491 570 163"})
        self.assertEqual(self.gaps(), [])

    def test_8_the_sheet_prints_service_kind_provider_contact_phone_and_meter_and_never_private_values(self):
        long_name = "Example long-named provider of electricity for a very big household " * 3
        self.records.update("people__people", self.provider, {"name": long_name.strip()})
        self.service(account_number=ACCOUNT, notes=PRIVATE_NOTE)
        self.service("Home internet", kind="internet", meter=None)
        sheet = self.page("/sheet/utilities/utility_contacts")
        for shown in ("Check it with your provider before relying on this page", "Home electricity", "Electricity",
                      long_name.strip(), "Example Energy Faults", "0491 570 162", "Electricity meter", "Home internet"):
            self.assertIn(shown, sheet)
        for left_out in (ACCOUNT, PRIVATE_NOTE, "<th>Account number", "<th>Notes"):
            self.assertNotIn(left_out, sheet)

    def test_9_deleting_a_contact_or_meter_clears_the_link_keeps_the_service_and_undo_adds_no_duplicate(self):
        service = self.service()
        self.records.delete("people__people", self.faults)
        self.assertIsNone(self.records.get("utilities__services", service)["fault_contact"])
        self.assertEqual(self.gaps(), [NO_CONTACT])
        self.records.delete("people__people", self.provider)
        self.assertIsNone(self.records.get("utilities__services", service)["provider"])
        self.records.delete("home_layout__meters", self.meter)
        kept = self.records.get("utilities__services", service)
        self.assertIsNone(kept["meter"])
        sheet = self.page("/sheet/utilities/utility_contacts")
        self.assertIn("Home electricity", sheet)
        self.assertNotIn("Garage", sheet)
        self.assertNotIn("Electricity meter", sheet)
        self.records.restore("home_layout__meters", self.meter)
        count = self.conn.execute("SELECT COUNT(*) FROM utilities__services WHERE deleted_at IS NULL").fetchone()[0]
        self.assertEqual(count, 1)

    def test_10_switching_it_off_hides_it_and_switching_on_returns_every_link_and_changes_no_other_module(self):
        self.service(account_number=ACCOUNT)
        client = self.client()
        self.assertIn("/t/utilities__services", self.page("/", client))
        before = self.snapshot()
        settings.set_module_enabled(self.conn, "utilities", False)
        self.assertEqual(client.get("/t/utilities__services", base_url=BASE).status_code, 404)
        self.assertEqual(client.get("/sheet/utilities/utility_contacts", base_url=BASE).status_code, 404)
        self.assertNotIn("/t/utilities__services", self.page("/", client))
        self.assertEqual(self.snapshot(), before)
        settings.set_module_enabled(self.conn, "utilities", True)
        self.assertEqual(self.snapshot(), before)
        sheet = self.page("/sheet/utilities/utility_contacts", client)
        for shown in ("Home electricity", "Example Energy Faults", "Electricity meter"):
            self.assertIn(shown, sheet)

    def snapshot(self):
        return {t: [tuple(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY id")]
                for t in ("utilities__services", "people__people", "home_layout__meters", "stock__places")}

    def test_11_no_provider_number_outage_instruction_payment_step_or_reading_is_preloaded_or_given_as_advice(self):
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM utilities__services").fetchone()[0], 0)
        text = " ".join(p.read_text(encoding="utf-8").lower() for p in (ROOT / "modules" / "utilities").glob("*.toml"))
        self.assertNotRegex(text, r"\d{4} ?\d{3} ?\d{3}")
        for advice in ("pay your bill", "report an outage", "meter reading", "call us", "should call", "emergency number"):
            self.assertNotIn(advice, text)
        self.assertIn("check it with your provider", text)

    def test_12_the_migration_matches_its_description_links_two_modules_and_changes_no_shipped_table(self):
        module = modules.load_module(ROOT / "modules" / "utilities")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "utilities" / "migrations" / "0001_initial.sql").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"CREATE TABLE (\S+)", sql), ["utilities__services"])
        for reference in ("people__people(id) ON DELETE SET NULL", "home_layout__meters(id) ON DELETE SET NULL"):
            self.assertIn(reference, sql)
        created = re.findall(r"CREATE (?:TABLE|INDEX) (\S+)", sql)
        self.assertTrue(all(name.startswith("utilities__") for name in created), created)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")

    def test_13_the_list_record_page_and_picker_show_the_meters_full_place_path(self):
        yard = self.records.create("stock__places", {"name": "Front yard"})
        box = self.records.create("stock__places", {"name": "Meter box", "inside": yard})
        self.records.update("home_layout__meters", self.meter, {"name": "Water meter", "place": box})
        service = self.service("Home water", kind="water")
        client = self.client()
        shown = "Water meter — Front yard › Meter box"
        for path in ("/t/utilities__services", f"/t/utilities__services/{service}",
                     "/sheet/utilities/utility_contacts"):
            self.assertIn(shown, self.page(path, client), path)
        self.records.update("stock__places", box, {"name": "Meter cupboard"})
        self.assertIn("Water meter — Front yard › Meter cupboard", self.page("/t/utilities__services", client))
        self.records.update("home_layout__meters", self.meter, {"place": None})  # no place: just the name
        listed = self.page("/t/utilities__services", client)
        self.assertIn("Water meter", listed)
        self.assertNotIn("Water meter —", listed)

    def test_14_with_place_is_checked_in_the_module_file_and_home_layout_is_optional(self):
        module = modules.load_module(ROOT / "modules" / "utilities")
        self.assertEqual(module.tables["services"].columns["meter"].with_place, "place")
        self.assertEqual(module.requires, ["people"])  # decision 0115 replaces 0106's hard requirement
        self.assertTrue(module.tables["services"].columns["meter"].optional)
        problems = []
        modules._check_tables("t", {"tables": {"x": {"title": "X", "description": "d",
                                                    "columns": {"name": {"type": "text", "with_place": "place"}}}}},
                              [], problems)
        self.assertTrue(any("with_place" in p for p in problems), problems)

    def test_home_page_has_a_utilities_card_and_the_sheet_link(self):
        page = self.page("/")
        self.assertIn("/t/utilities__services", page)
        self.assertIn("/sheet/utilities/utility_contacts", page)


class UtilitiesExampleAndBackupTests(TempDirTestCase):
    def test_4_each_example_has_one_service_linked_to_one_exact_meter_at_its_place(self):
        for household, service, meter, place, phone in (
                ("smith", "Home electricity", "Electricity meter", "Garage", "0491 570 162"),
                ("garcia", "Apartment electricity", "Apartment electricity meter", "Hall closet", "(415) 555-0112"),
                ("taylor", "Flat water", "Flat water meter", "Kitchen cupboard", "07700 900791")):
            with self.subTest(household=household):
                data = self.tmp / household
                load_example.load(household, data, today=date(2026, 6, 1))
                conn = db.connect(data / "dashboard.db")
                self.addCleanup(conn.close)
                rows = conn.execute(
                    "SELECT s.name, m.name AS meter, p.name AS place, f.phone, s.account_number "
                    "FROM utilities__services s JOIN home_layout__meters m ON m.id = s.meter "
                    "JOIN stock__places p ON p.id = m.place JOIN people__people f ON f.id = s.fault_contact").fetchall()
                self.assertEqual([tuple(r)[:4] for r in rows], [(service, meter, place, phone)])
                self.assertTrue(rows[0]["account_number"].startswith("DEMO-"))
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM home_layout__meters WHERE name = ?", (meter,)).fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM home_layout__meters").fetchone()[0], 1)

    def test_12b_restore_then_undo_keeps_the_exact_meter_link_and_the_private_value(self):
        data = self.tmp / "smith"
        load_example.load("smith", data, today=date(2026, 6, 1))
        report = startup.prepare(data)
        backups.daily(data, today=date(2026, 6, 1))
        conn = db.connect(data / "dashboard.db")
        store = records.Records(conn, records.build_registry(report.loaded))
        row = conn.execute("SELECT id, meter, account_number FROM utilities__services").fetchone()
        self.assertEqual(row["account_number"], "DEMO-AU-ACCOUNT-01")
        store.update("utilities__services", row["id"], {"meter": None, "account_number": "DEMO-AU-ACCOUNT-02"})
        conn.close()

        def saved():
            c = db.connect(data / "dashboard.db")
            try:
                return tuple(c.execute("SELECT meter, account_number FROM utilities__services").fetchone())
            finally:
                c.close()

        chosen = restore.get({"data": data / "backups"}, "data", "daily-2026-06-01.db")
        restore.restore(data, chosen, report.loaded)
        self.assertEqual(saved(), (row["meter"], "DEMO-AU-ACCOUNT-01"))
        restore.undo(data, report.loaded)
        self.assertEqual(saved(), (None, "DEMO-AU-ACCOUNT-02"))
