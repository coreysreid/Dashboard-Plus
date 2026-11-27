"""Tests for the robustness fixes from the November 2026 review: modules, switching off, long lists, privacy."""
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup
from dashboard.web.app import create_app
import make_migration

PORT = 5130
BASE = f"http://127.0.0.1:{PORT}"


class ModuleLoadingTests(TempDirTestCase):
    def broken(self, name="demo", **files):
        folder = self.make_module(name, labels=None)
        for file, text in files.items():
            (folder / file.replace("_", ".", 1)).write_bytes(text if isinstance(text, bytes) else text.encode())
        _, failures = modules.discover(self.tmp / "modules")
        return " ".join(failures.get(name, []))

    def test_malformed_files_leave_the_module_out_instead_of_stopping(self):
        self.assertIn("could not be read", self.broken(labels_toml='tables = "x"\n'))
        tables = self.make_module(labels=None) / "tables.toml"
        text = tables.read_text(encoding="utf-8")
        self.assertTrue(self.broken(tables_toml=text + '\n[tables.things.watch]\nrunning_low = { quantity = ["qty"], minimum = "qty" }\n'))

    def test_a_catalogue_that_is_not_utf8_is_reported(self):
        labels = '[tables.things]\ncolumns.name = { suggest_from = "list.csv" }\n'
        self.assertTrue(self.broken(labels_toml=labels, list_csv=b"name\n\xff\xfe bad\n"))

    def test_a_module_name_must_be_a_safe_name(self):
        folder = self.tmp / "modules" / "my-mod"
        shutil.copytree(self.make_module(labels=None), folder)
        (folder / "module.toml").write_text((folder / "module.toml").read_text(encoding="utf-8").replace('name = "demo"', 'name = "my-mod"'))
        _, failures = modules.discover(self.tmp / "modules")
        self.assertIn("lower-case letters", " ".join(failures["my-mod"]))

    def test_gap_messages_cannot_use_format_tricks(self):
        tables = self.make_module(labels=None) / "tables.toml"
        text = tables.read_text(encoding="utf-8") + ('\n[[tables.things.watch.gaps]]\nmissing = "owner"\n'
                                                      'message = "Who owns {name:{name}}?"\n')
        self.assertIn("plain {column} names", self.broken(tables_toml=text))

    def test_a_module_whose_tables_were_never_migrated_is_left_out_and_others_work(self):
        make_migration.make(self.make_module("first", labels=None), "first_tables")
        self.make_module("second", labels=None)  # no migration generated
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.modules, ["first"])
        self.assertIn("make_migration", " ".join(report.module_problems["second"]))

    def test_a_module_whose_database_change_fails_is_left_out(self):
        make_migration.make(self.make_module("first", labels=None), "first_tables")
        folder = self.make_module("second", labels=None)
        (folder / "migrations").mkdir()
        (folder / "migrations" / "0001_broken.sql").write_text("CREATE TABLE oops (;\n", encoding="utf-8")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.modules, ["first"])
        self.assertIn("left out", " ".join(report.module_problems["second"]))


class ShippedModuleTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("people", "pets", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.records = records.Records(self.conn, records.build_registry(self.report.loaded))
        settings.put(self.conn, "setup.done", True)
        self.app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def post(self, path, data):
        return self.client.post(path, data=dict(data, _csrf=self.app.config["CSRF_TOKEN"]), base_url=BASE)

    def test_people_cannot_be_switched_off_while_pets_needs_it(self):
        response = self.post("/settings", {"modules": ["pets", "stock"]})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Pets needs People", response.get_data(as_text=True))

    def test_pets_is_hidden_rather_than_broken_if_people_was_already_off(self):
        settings.set_module_enabled(self.conn, "people", False)
        self.assertEqual(self.get("/t/pets__pets").status_code, 404)
        self.assertEqual(self.get("/").status_code, 200)

    def test_a_long_list_still_offers_the_chosen_record_and_can_search_past_the_first_500(self):
        from dashboard.web import display
        for i in range(display.OPTION_LIMIT + 5):
            last = self.records.create("stock__items", {"name": f"Item {i:04d}"})
        last = self.records.create("stock__items", {"name": "zz last item", "quantity": 1})
        move = self.records.create("stock__movements", {"item": last, "reason": "used", "amount": 1})
        form = self.get(f"/t/stock__movements/{move}").get_data(as_text=True)
        self.assertRegex(form, rf'<option value="{last}" selected>zz last item</option>')
        self.assertIn('data-search="/t/stock__items/suggest?column=name"', form)
        found = self.get("/t/stock__items/suggest?column=name&q=zz").get_json()
        self.assertEqual(found[0]["existing_id"], last)

    def test_private_details_are_never_used_as_names_or_suggestions(self):
        person = self.records.create("people__people", {"name": "Person A"})
        response = self.post("/t/people__important_info/new",
                             {"person": str(person), "kind": "allergy", "detail": "ZZSECRET", "then": "another"})
        self.assertNotIn("ZZSECRET", response.headers.get("Location", ""))
        self.assertEqual(self.get("/t/people__important_info/suggest?column=detail&q=ZZ").status_code, 404)

    def test_places_list_by_full_path_and_find_children_by_their_parent(self):
        kitchen = self.records.create("stock__places", {"name": "Zzz kitchen"})
        self.records.create("stock__places", {"name": "A child shelf", "inside": kitchen})
        page = self.get("/t/stock__places").get_data(as_text=True)
        self.assertLess(page.index("Zzz kitchen<"), page.index("Zzz kitchen › A child shelf"))
        self.assertIn('aria-label="Open Zzz kitchen › A child shelf"', page)
        found = self.get("/t/stock__places/suggest?column=name&q=zzz").get_json()
        self.assertIn("Zzz kitchen › A child shelf", [f["name"] for f in found])

    def test_a_refused_save_lists_what_to_check_and_ties_each_message_to_its_field(self):
        page = self.post("/t/stock__items/new", {"name": "", "category": "pantry"}).get_data(as_text=True)
        self.assertIn("Nothing was saved. Check these answers:", page)
        self.assertIn('<a href="#f-name">Name</a>', page)
        self.assertRegex(page, r'id="f-name"[^>]*aria-invalid="true"[^>]*aria-describedby="f-name-error f-name-help"')


class SecurityReviewWebTests(TempDirTestCase):
    """Security review findings 6 and 7: odd input is refused politely and pages are kept private."""

    def setUp(self):
        super().setUp()
        import shutil
        from dashboard.core import db, settings, startup
        from dashboard.web.app import create_app
        from support import ROOT
        shutil.copytree(ROOT / "modules" / "people", self.tmp / "modules" / "people")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        settings.put(conn, "setup.done", True)
        conn.close()
        app = create_app("t", lambda: None, report, data_dir=self.tmp / "data", session_key="k")
        app.config["PORT"] = 5132
        self.base = "http://127.0.0.1:5132"
        self.client = app.test_client()
        self.client.get("/?key=k", base_url=self.base)

    def test_an_unusual_digit_in_the_address_does_not_crash_the_page(self):
        page = self.client.get("/t/people__roles/new?person=²", base_url=self.base)
        self.assertEqual(page.status_code, 200)

    def test_a_wrong_method_is_refused_not_reported_as_a_crash(self):
        self.assertEqual(self.client.put("/", base_url=self.base).status_code, 405)

    def test_pages_are_not_cached_or_framed(self):
        page = self.client.get("/", base_url=self.base)
        self.assertEqual(page.headers["Cache-Control"], "no-store")
        self.assertEqual(page.headers["X-Frame-Options"], "DENY")
