"""Tests for the screens: sign-in by launch link, grid paging, forms, history and reports."""
import re

from support import TempDirTestCase
from dashboard.core import startup
from dashboard.web.app import create_app
import make_migration

TABLES = '''[tables.places]
title = "Places"
columns.name = { type = "text", required = true }

[tables.items]
title = "Items"
columns.name = { type = "text", required = true }
columns.kind = { type = "choice", choices = ["tool", { key = "first_aid", label = "First aid" }] }
columns.place = { type = "link", to = "places", on_delete = "restrict" }
columns.quantity = { type = "measure", unit = "each", min = 0 }
columns.price = { type = "money" }
columns.checked = { type = "boolean" }
columns.secret = { type = "text", sensitive = true }
columns.minimum = { type = "measure", min = 0 }

[tables.items.watch]
running_low = { quantity = "quantity", minimum = "minimum" }
'''
LABELS = '''[tables.items]
title = "Stock items"
list = ["name", "kind", "place", "quantity", "secret"]
columns.quantity = { label = "How many", help = "Count whole items" }
'''
PORT = 5123
BASE = f"http://127.0.0.1:{PORT}"


class WebTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        make_migration.make(self.make_module(tables=TABLES, labels=LABELS), "first_tables")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "modules")
        self.app = create_app("shutdown-token", lambda: None, report, data_dir=data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.csrf = self.app.config["CSRF_TOKEN"]

    def sign_in(self):
        response = self.client.get("/?key=session-key", base_url=BASE)
        self.assertEqual(response.status_code, 302)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def post(self, path, data):
        return self.client.post(path, data=dict(data, _csrf=self.csrf), base_url=BASE)

    def add_place(self, name="Garage shelf"):
        self.post("/t/demo__places/new", {"name": name, "then": "done"})
        return name

    def test_pages_need_the_launch_link(self):
        response = self.get("/t/demo__items")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/start", response.headers["Location"])
        self.assertIn("from its shortcut", self.get("/start").get_data(as_text=True))
        self.assertEqual(self.client.get("/?key=wrong", base_url=BASE).headers["Location"], "/start")

    def test_forms_need_their_hidden_token(self):
        self.sign_in()
        response = self.client.post("/t/demo__places/new", data={"name": "x"}, base_url=BASE)
        self.assertEqual(response.status_code, 400)

    def test_home_lists_tables_with_counts(self):
        self.sign_in()
        self.add_place()
        page = self.get("/").get_data(as_text=True)
        self.assertIn("Stock items", page)
        self.assertIn("1 record", page)

    def test_add_with_mistakes_keeps_what_was_typed(self):
        self.sign_in()
        response = self.post("/t/demo__items/new", {"name": "", "quantity": "lots", "kind": "first_aid"})
        self.assertEqual(response.status_code, 422)
        page = response.get_data(as_text=True)
        self.assertIn("Name is required.", page)
        self.assertIn("How many must be a number.", page)
        self.assertIn('value="lots"', page)
        self.assertRegex(page, r'<option value="first_aid"\s+selected>')

    def test_save_and_add_another_then_grid_shows_friendly_values(self):
        self.sign_in()
        self.add_place()
        page = self.get("/t/demo__items/new").get_data(as_text=True)
        place_id = re.search(r'<option value="(\d+)" >Garage shelf</option>', page).group(1)
        response = self.post("/t/demo__items/new", {"name": "Bandages", "kind": "first_aid", "place": place_id,
                                                    "quantity": "12", "price": "4.5", "checked": "yes",
                                                    "secret": "hidden note", "then": "another"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("saved=Bandages", response.headers["Location"])
        grid = self.get("/t/demo__items").get_data(as_text=True)
        for text in ("Bandages", "First aid", "Garage shelf", "12 each", "How many"):
            self.assertIn(text, grid)
        self.assertIn("<summary>Show</summary>hidden note", grid)

    def test_edit_records_history_and_delete_restore(self):
        self.sign_in()
        self.post("/t/demo__items/new", {"name": "Torch", "quantity": "1", "then": "done"})
        response = self.post("/t/demo__items/1", {"name": "Torch", "quantity": "2"})
        self.assertEqual(response.status_code, 302)
        page = self.get("/t/demo__items/1").get_data(as_text=True)
        self.assertIn("<h1>Torch", page)
        self.assertIn('How many from "1 each" to "2 each"', page)
        self.assertIn("You added this", page)
        self.post("/t/demo__items/1/delete", {})
        self.assertIn("(deleted)", self.get("/t/demo__items/1").get_data(as_text=True))
        self.assertIn("0 records", self.get("/t/demo__items").get_data(as_text=True))
        self.post("/t/demo__items/1/restore", {})
        self.assertIn("1 record", self.get("/t/demo__items").get_data(as_text=True))

    def test_delete_refused_while_linked(self):
        self.sign_in()
        self.add_place()
        self.post("/t/demo__items/new", {"name": "Ladder", "place": "1", "then": "done"})
        response = self.post("/t/demo__places/1/delete", {})
        self.assertEqual(response.status_code, 409)
        self.assertIn("still point at it", response.get_data(as_text=True))

    def test_grid_loads_more_rows_a_page_at_a_time(self):
        self.sign_in()
        for i in range(60):
            self.post("/t/demo__places/new", {"name": f"Shelf {i:02d}", "then": "done"})
        page = self.get("/t/demo__places?sort=name").get_data(as_text=True)
        self.assertEqual(page.count('<a href="/t/demo__places/'), 50)
        self.assertIn('data-offset="50"', page)
        more = self.get("/t/demo__places/rows?offset=50&sort=name").get_data(as_text=True)
        self.assertEqual(more.count('<a href="/t/demo__places/'), 10)
        self.assertNotIn("data-next", more)
        self.assertIn("Shelf 59", more)

    def test_home_and_attention_page_show_what_is_running_low(self):
        self.sign_in()
        self.post("/t/demo__items/new", {"name": "Batteries", "quantity": "1", "minimum": "4", "then": "done"})
        home = self.get("/").get_data(as_text=True)
        self.assertIn("1 running low", home)
        page = self.get("/attention").get_data(as_text=True)
        self.assertIn("Batteries</a>: 1 left, keep at least 4 each", page)

    def test_unknown_table_and_record_are_friendly(self):
        self.sign_in()
        self.assertEqual(self.get("/t/demo__nothing").status_code, 404)
        response = self.get("/t/demo__items/99")
        self.assertEqual(response.status_code, 404)
        self.assertIn("does not exist", response.get_data(as_text=True))

    def test_save_a_report_writes_a_file_without_records(self):
        self.sign_in()
        self.post("/t/demo__places/new", {"name": "Private place name", "then": "done"})
        page = self.post("/report", {}).get_data(as_text=True)
        self.assertIn("Report saved", page)
        reports = list((self.tmp / "data" / "reports").glob("report-*.txt"))
        self.assertEqual(len(reports), 1)
        self.assertNotIn("Private place name", reports[0].read_text(encoding="utf-8"))
