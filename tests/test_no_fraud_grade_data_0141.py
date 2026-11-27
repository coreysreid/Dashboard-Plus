"""Tests for decision 0141: no fraud-grade details are kept, and what was saved before can be tidied with Undo.

The card check on forms, the helper API and imports, retired fields hidden, Tidy sensitive details with a backup and
Undo, and no module may declare such a field. Every value is invented."""
import io
import json
import shutil
import zipfile
from datetime import datetime, timezone

from support import DEMO_MODULE, ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import csv_import, db, export, fraud_guard, helpers, modules, records, settings, startup, tidy
from dashboard.web.app import create_app

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
CARD = "4111 1111 1111 1111"   # the well-known test card number, never a real one
CARD_13 = "4222222222222"      # a 13-digit test card
CODE = "Invented gate code 7319"
ACCOUNT = "DEMO-4417-0931-2288"


class GuardTests(TempDirTestCase):
    def test_the_card_check_finds_cards_with_spaces_or_dashes_and_leaves_barcodes_and_microchips(self):
        for text in (CARD, "4111-1111-1111-1111", "Paid with 4111111111111111 today", CARD_13, "378282246310005"):
            with self.subTest(text=text):
                self.assertTrue(fraud_guard.has_card_number(text))
        for text in ("4111 1111 1111 1112", "985000000777888", "900000000123456", "9300000000001",
                     "4006381333931", "Phone 0491 570 156", "Shelf 3, 2026-11-27"):
            with self.subTest(text=text):
                self.assertFalse(fraud_guard.has_card_number(text))
        self.assertEqual(fraud_guard.mask_cards(f"Card {CARD} on file"), "Card ••••1111 on file")

    def test_each_guard_says_what_to_write_instead_and_never_repeats_the_value(self):
        self.assertIsNone(fraud_guard.check("••••1234", "last_digits"))
        self.assertIsNone(fraud_guard.check("1234", "last_digits"))
        self.assertEqual(fraud_guard.check("12345678", "last_digits"), fraud_guard.LAST_DIGITS)
        self.assertIsNone(fraud_guard.check("In the password manager", "where_kept"))
        self.assertIsNone(fraud_guard.check("Ask Alex next door", "where_kept"))
        for text in ("1-9-8-4", "PIN 4821", "password: hunter2", "the code is 7319"):
            with self.subTest(text=text):
                self.assertEqual(fraud_guard.check(text, "where_kept"), fraud_guard.WHERE_KEPT)
        for message in fraud_guard.REFUSALS:
            self.assertNotIn("4111", message)
        self.assertIn("••••1234", fraud_guard.CARD)


class ModuleCheckTests(TempDirTestCase):
    def test_no_shipped_or_example_module_declares_a_forbidden_kind_of_field(self):
        for folder in ("modules", "examples"):
            _loaded, failures = modules.discover(ROOT / folder)
            failures.pop("households", None)  # example data, not a module
            self.assertEqual(failures, {}, folder)

    def test_a_module_asking_for_a_password_pin_card_or_id_number_is_refused_in_plain_words(self):
        for column, what in (("wifi_password", "password"), ("door_pin", "PIN"), ("alarm_code", "access code"),
                             ("card_number", "card number"), ("bsb", "bank"), ("passport_number", "passport"),
                             ("licence_scan", "copy of an ID")):
            with self.subTest(column=column):
                folder = self.make_module(f"bad_{column}", DEMO_MODULE, f'[tables.things]\ntitle = "Things"\n'
                                          f'columns.name = {{ type = "text" }}\ncolumns.{column} = {{ type = "text" }}\n',
                                          None)
                with self.assertRaises(modules.ModuleError) as caught:
                    modules.load_module(folder)
                self.assertIn(what, str(caught.exception))
                self.assertIn("never keeps passwords", str(caught.exception))
        labelled = self.make_module("bad_label", DEMO_MODULE, '[tables.things]\ntitle = "Things"\n'
                                    'columns.name = { type = "text" }\ncolumns.extra = { type = "text" }\n',
                                    '[tables.things]\ncolumns.extra = { label = "Safe combination" }\n')
        with self.assertRaises(modules.ModuleError):
            modules.load_module(labelled)


class FraudGuardTestCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "utilities", "bills_insurance")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.garage = self.store.create("stock__places", {"name": "Garage"})
        self.door = self.store.create("home_layout__exits", {"name": "Side door", "place": self.garage})
        self.service = self.store.create("utilities__services", {"name": "Home electricity", "kind": "electricity"})
        self.bob = self.store.create("people__people", {"name": "Bob Example"})

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def post(self, client, path, **data):
        return client.post(path, data=dict(data, _csrf=client.csrf), base_url=BASE)

    def saved_before(self):
        """Values saved before decision 0141, put straight into the retired columns."""
        self.conn.execute("UPDATE home_layout__exits SET access_details = ? WHERE id = ?", (CODE, self.door))
        self.conn.execute("UPDATE utilities__services SET account_number = ? WHERE id = ?", (ACCOUNT, self.service))
        self.conn.commit()


class CardCheckEverywhereTests(FraudGuardTestCase):
    def test_a_form_refuses_a_card_number_says_what_to_write_and_never_puts_it_back_on_the_page(self):
        client = self.client()
        reply = self.post(client, "/t/people__people/new", name="Card holder", notes=f"Card {CARD}")
        text = reply.get_data(as_text=True)
        self.assertEqual(reply.status_code, 422)
        self.assertIn("looks like a full card number", text)
        self.assertIn("••••1234", text)
        self.assertNotIn(CARD, text)
        self.assertNotIn("4111111111111111", text)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM people__people WHERE name = 'Card holder'")
                         .fetchone()[0], 0)
        with self.assertRaises(records.ValidationError) as caught:
            self.store.update("people__people", self.bob, {"notes": CARD_13})
        self.assertEqual(caught.exception.problems, {"notes": fraud_guard.CARD})

    def test_guarded_fields_keep_only_the_last_digits_or_where_a_code_is_kept(self):
        with self.assertRaises(records.ValidationError) as caught:
            self.store.update("utilities__services", self.service, {"account_last4": "44170931"})
        self.assertEqual(caught.exception.problems, {"account_last4": fraud_guard.LAST_DIGITS})
        self.store.update("utilities__services", self.service, {"account_last4": "2288"})
        self.assertEqual(self.store.get("utilities__services", self.service)["account_last4"], "••••2288")
        with self.assertRaises(records.ValidationError):
            self.store.update("home_layout__exits", self.door, {"access_hint": "1-9-8-4"})
        self.store.update("home_layout__exits", self.door, {"access_hint": "Ask Alex next door"})
        with self.assertRaises(records.ValidationError):
            self.store.create("people__important_info", {"person": self.bob, "kind": "access",
                                                         "detail": "The side gate code is 1-9-8-4"})
        self.store.create("people__important_info", {"person": self.bob, "kind": "access",
                                                     "detail": "Ask Bob for the side gate code"})
        self.store.create("people__important_info", {"person": self.bob, "kind": "medication",
                                                     "detail": "Takes 2000 units at breakfast"})

    def test_the_helper_api_refuses_a_card_number_and_keeps_nothing(self):
        _helper, key = helpers.issue(self.conn, self.data, "People helper", "suggest", ["people"])
        client = self.client()
        body = {"request_key": "card-1", "why": "Read from a note",
                "entries": [{"table": "people__people", "values": {"name": "Card holder", "notes": CARD_13}}]}
        reply = client.post("/api/v1/proposals", data=json.dumps(body), base_url=BASE,
                            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        self.assertEqual((reply.status_code, reply.get_json()["error"]), (400, "payment_detail"))
        self.assertNotIn(CARD_13, reply.get_data(as_text=True))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)

    def test_a_spreadsheet_card_number_is_left_out_when_read_and_its_row_is_refused(self):
        text = csv_import.decode(f"name,notes\nCard holder,{CARD}\nPlain,Fine note\n".encode())
        self.assertNotIn(CARD, text)
        self.assertIn(fraud_guard.LEFT_OUT, text)
        sheet = csv_import.parse(text)
        run = csv_import.dry_run(self.store, self.registry["people__people"], sheet, ["name", "notes"])
        self.assertEqual([n for n, _v in run.ready], [3])
        self.assertEqual(len(run.problems), 1)
        self.assertIn("looks like a full card number", run.problems[0][1][0])
        client = self.client()
        reply = client.post("/settings/import", data={"_csrf": client.csrf, "table": "people__people",
                                                      "file": (io.BytesIO(f"name,notes\nX,{CARD}\n".encode()), "p.csv")},
                            base_url=BASE, content_type="multipart/form-data")
        self.assertEqual(reply.status_code, 200)
        self.assertIn("card number left out", reply.get_data(as_text=True))
        self.assertNotIn(CARD, reply.get_data(as_text=True))
        self.assertNotIn("4111111111111111", reply.get_data(as_text=True))


class RetiredFieldTests(FraudGuardTestCase):
    def test_retired_values_stay_saved_but_are_hidden_from_pages_exports_helpers_and_records(self):
        self.saved_before()
        self.assertNotIn("access_details", self.store.get("home_layout__exits", self.door))
        self.assertNotIn("account_number", self.store.page("utilities__services")[0])
        self.assertEqual(self.conn.execute("SELECT access_details FROM home_layout__exits").fetchone()[0], CODE)
        client = self.client()
        for path in ("/t/home_layout__exits", f"/t/home_layout__exits/{self.door}", "/sheet/home_layout/our_home",
                     "/t/utilities__services", f"/t/utilities__services/{self.service}", "/tidy"):
            with self.subTest(path=path):
                text = client.get(path, base_url=BASE).get_data(as_text=True)
                self.assertNotIn(CODE, text)
                self.assertNotIn(ACCOUNT, text)
        self.assertIn("Tidy sensitive details", client.get("/", base_url=BASE).get_data(as_text=True))
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 27, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for name in archive.namelist():
                self.assertNotIn(CODE, archive.read(name).decode("utf-8-sig"))
                self.assertNotIn(ACCOUNT, archive.read(name).decode("utf-8-sig"))
        _helper, key = helpers.issue(self.conn, self.data, "Reader", "read", ["home_layout", "utilities"])
        for table in ("home_layout__exits", "utilities__services"):
            reply = client.get(f"/api/v1/tables/{table}/records", base_url=BASE,
                               headers={"Authorization": f"Bearer {key}"}).get_data(as_text=True)
            self.assertNotIn(CODE, reply)
            self.assertNotIn(ACCOUNT, reply)
        changes = " ".join(str(tuple(r)) for r in self.conn.execute("SELECT * FROM core__sync_changes"))
        self.assertNotIn(CODE, changes)

    def test_an_old_card_number_in_ordinary_text_shows_only_as_its_last_digits(self):
        self.conn.execute("UPDATE people__people SET notes = ? WHERE id = ?", (f"Card {CARD}", self.bob))
        self.conn.commit()
        text = self.client().get(f"/t/people__people/{self.bob}", base_url=BASE).get_data(as_text=True)
        self.assertNotIn(CARD, text)
        self.assertIn("••••1111", text)


class TidyTests(FraudGuardTestCase):
    def backups(self):
        return sorted(p.name for p in (self.data / "backups").glob("before-tidy-*.db"))

    def test_the_page_lists_by_count_shows_values_only_after_a_pressed_show_and_never_caches(self):
        self.saved_before()
        client = self.client()
        page = client.get("/tidy", base_url=BASE)
        self.assertIn("2 saved details to tidy", page.get_data(as_text=True))
        self.assertIn("Codes or access details", page.get_data(as_text=True))
        self.assertNotIn(CODE, page.get_data(as_text=True))
        self.assertEqual(client.get("/tidy/show", base_url=BASE).status_code, 405)
        self.assertEqual(client.post("/tidy/show", base_url=BASE).status_code, 400)  # no page token
        shown = self.post(client, "/tidy/show")
        self.assertIn(CODE, shown.get_data(as_text=True))
        self.assertIn("no-store", shown.headers["Cache-Control"])

    def test_where_it_is_kept_with_a_backup_first_then_undo_then_forget(self):
        self.saved_before()
        client = self.client()
        key = f"home_layout__exits|{self.door}|access_details"
        refused = self.post(client, "/tidy/do", key=key, choice="where", hint="Code 7319")
        self.assertEqual(refused.status_code, 409)
        self.assertNotIn("7319", refused.get_data(as_text=True).replace(CODE, ""))
        self.assertEqual(self.backups(), [])
        done = self.post(client, "/tidy/do", key=key, choice="where", hint="In the password manager")
        self.assertEqual(done.status_code, 302)
        self.assertEqual(len(self.backups()), 1)
        row = self.conn.execute("SELECT access_details, access_hint FROM home_layout__exits").fetchone()
        self.assertEqual(tuple(row), (None, "In the password manager"))
        self.assertIn("Undo", client.get("/tidy", base_url=BASE).get_data(as_text=True))
        entry = tidy.recent(self.store)[0]
        self.post(client, "/tidy/undo", tidy=str(entry["id"]))
        row = self.conn.execute("SELECT access_details, access_hint FROM home_layout__exits").fetchone()
        self.assertEqual(tuple(row), (CODE, None))
        self.assertEqual(len(self.backups()), 2)
        self.post(client, "/tidy/do", key=key, choice="remove")
        self.post(client, "/tidy/forget")
        audit = " ".join(str(tuple(r)) for r in self.conn.execute("SELECT before, after FROM core__audit"))
        self.assertNotIn(CODE, audit)
        with self.assertRaises(tidy.TidyRefused):
            tidy.undo(self.store, tidy.recent(self.store)[0]["id"])

    def test_keep_only_the_last_digits_and_tidy_an_old_card_number_in_notes(self):
        self.saved_before()
        self.conn.execute("UPDATE people__people SET notes = ? WHERE id = ?", (f"Card {CARD} kept", self.bob))
        self.conn.commit()
        client = self.client()
        self.post(client, "/tidy/do", key=f"utilities__services|{self.service}|account_number", choice="last4")
        self.assertEqual(tuple(self.conn.execute("SELECT account_number, account_last4 FROM utilities__services")
                               .fetchone()), (None, "••••2288"))
        self.post(client, "/tidy/do", key=f"people__people|{self.bob}|notes", choice="last4")
        self.assertEqual(self.store.get("people__people", self.bob)["notes"], "Card ••••1111 kept")
        self.assertEqual(tidy.waiting(self.store), 1)  # the code is still to tidy
        self.assertEqual([i.column for i in tidy.find(self.store)], ["access_details"])
        stale = self.post(client, "/tidy/do", key=f"people__people|{self.bob}|notes", choice="last4")
        self.assertEqual(stale.status_code, 409)
