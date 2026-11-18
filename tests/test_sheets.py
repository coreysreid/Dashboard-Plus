"""Tests for printable sheets: checking sheets.toml and printing the emergency sheet."""
from support import TempDirTestCase
from dashboard.core import db, modules, settings, startup
from dashboard.web.app import create_app
import make_migration

PEOPLE_MODULE = '''name = "people"
title = "People"
version = "1.0.0"
description = "Synthetic people module for tests."
core_api = "1"
kind = "declarative"
'''
PEOPLE_TABLES = '''[tables.people]
title = "People"
columns.name = { type = "text", required = true }
columns.lives_here = { type = "boolean" }
columns.phone = { type = "text" }

[tables.roles]
title = "Roles"
columns.person = { type = "link", to = "people", on_delete = "cascade" }
columns.role = { type = "choice", choices = ["emergency_contact", "neighbour", "doctor", "vet"] }
columns.priority = { type = "integer" }

[tables.important_info]
title = "Important information"
columns.person = { type = "link", to = "people", on_delete = "cascade" }
columns.detail = { type = "text", sensitive = true }
'''
SHEETS = '''[[sheet]]
name = "emergency"
title = "Emergency sheet"
intro = "Keep a printed copy on the fridge."

[[sheet.section]]
title = "Who lives here"
table = "people"
where = { lives_here = true }
columns = ["name", "phone"]
order_by = "name"

[[sheet.section]]
title = "Who to call"
table = "roles"
columns = ["role", "person", "person.phone"]
order_by = "priority"
'''
LOANS_MODULE = '''name = "loans"
title = "Loans"
version = "1.0.0"
description = "Synthetic module that links People, for tests."
core_api = "1"
kind = "declarative"
requires = ["people"]
'''
LOANS_TABLES = '''[tables.loans]
title = "Loans"
columns.name = { type = "text", required = true }
columns.borrower = { type = "link", to = "people.people", on_delete = "clear" }
columns.info = { type = "link", to = "people.important_info", on_delete = "clear" }
'''
LOANS_SHEET = '''[[sheet]]
name = "out"
title = "Loans"

[[sheet.section]]
table = "loans"
columns = ["name", "borrower", "borrower.phone"]
'''
PORT = 5125
BASE = f"http://127.0.0.1:{PORT}"


class CrossModuleSheetCheckTests(TempDirTestCase):
    """A sheet column from a record in another module, like the borrower's phone from People (decision 0072)."""

    def failures(self, sheet):
        self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None)
        self.make_module("loans", module=LOANS_MODULE, tables=LOANS_TABLES, labels=None)
        self.write("modules/loans/sheets.toml", sheet)
        found, failures = modules.discover(self.tmp / "modules")
        return [m.name for m in found], " | ".join(failures.get("loans", []))

    def test_a_column_of_a_required_module_loads(self):
        loaded, problems = self.failures(LOANS_SHEET)
        self.assertEqual(problems, "")
        self.assertIn("loans", loaded)

    def test_a_missing_column_is_explained_after_every_module_loads(self):
        loaded, problems = self.failures(LOANS_SHEET.replace("borrower.phone", "borrower.phon"))
        self.assertNotIn("loans", loaded)
        self.assertIn("'borrower.phon' names a column 'phon' that 'people.people' does not have", problems)
        self.assertIn("Did you mean 'phone'", problems)

    def test_a_private_column_of_another_module_is_refused(self):
        loaded, problems = self.failures(LOANS_SHEET.replace("borrower.phone", "info.detail"))
        self.assertNotIn("loans", loaded)
        self.assertIn("'info.detail' is private in the 'people' module, so this sheet can't print it", problems)

    def test_a_link_into_a_module_not_required_is_refused(self):
        self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None)
        self.make_module("loans", module=LOANS_MODULE.replace('requires = ["people"]', "requires = []"),
                         tables=LOANS_TABLES, labels=None)
        self.write("modules/loans/sheets.toml", LOANS_SHEET)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(self.tmp / "modules" / "loans")
        self.assertIn("must be listed in module.toml under requires", " | ".join(caught.exception.problems))


class SheetCheckTests(TempDirTestCase):
    def problems(self, sheets):
        folder = self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None)
        self.write("modules/people/sheets.toml", sheets)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " | ".join(caught.exception.problems)

    def test_valid_sheet_loads(self):
        folder = self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None)
        self.write("modules/people/sheets.toml", SHEETS)
        sheet = modules.load_module(folder).sheets[0]
        self.assertEqual(sheet["name"], "emergency")
        self.assertEqual(sheet["sections"][0]["where"], {"lives_here": True})

    def test_mistakes_are_explained(self):
        self.assertIn("Did you mean 'people'", self.problems(SHEETS.replace('table = "people"', 'table = "peple"')))
        self.assertIn("Did you mean 'phone'", self.problems(SHEETS.replace('"name", "phone"', '"name", "phon"')))
        self.assertIn("'order_by'", self.problems(SHEETS.replace('order_by = "priority"', 'order_by = "rank"')))
        self.assertIn("'where' names a column", self.problems(SHEETS.replace("lives_here = true", "here = true")))
        self.assertIn("at least one", self.problems('[[sheet]]\nname = "x"\ntitle = "X"\n'))
        self.assertIn("Did you mean 'phone'", self.problems(SHEETS.replace('"person.phone"', '"person.phon"')))
        self.assertIn("must start with a link column", self.problems(SHEETS.replace('"person.phone"', '"role.phone"')))


class SheetPageTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.make_module("people", module=PEOPLE_MODULE, tables=PEOPLE_TABLES, labels=None)
        self.write("modules/people/sheets.toml", SHEETS)
        make_migration.make(self.tmp / "modules" / "people", "first_tables")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "modules")
        conn = db.connect(data / "dashboard.db")
        settings.put(conn, "setup.done", True)
        conn.close()
        self.app = create_app("t", lambda: None, report, data_dir=data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def post(self, path, data):
        return self.client.post(path, data=dict(data, _csrf=self.app.config["CSRF_TOKEN"]), base_url=BASE)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def test_emergency_sheet_prints_people_and_contacts(self):
        self.post("/t/people__people/new", {"name": "Person B", "lives_here": "yes", "phone": "555 0102", "then": "done"})
        self.post("/t/people__people/new", {"name": "Person A", "lives_here": "yes", "phone": "555 0101", "then": "done"})
        self.post("/t/people__people/new", {"name": "Neighbour C", "phone": "555 0199", "then": "done"})
        self.post("/t/people__roles/new", {"person": "3", "role": "neighbour", "priority": "1", "then": "done"})
        self.post("/t/people__people/2/delete", {})
        self.assertIn("Print: Emergency sheet", self.get("/").get_data(as_text=True))
        page = self.get("/sheet/people/emergency").get_data(as_text=True)
        self.assertIn("Keep a printed copy on the fridge.", page)
        self.assertIn("Person B", page)
        self.assertNotIn("Person A", page, "deleted people are left off")
        self.assertIn("Neighbour C", page)
        self.assertIn("Neighbour</td>", page)
        self.assertIn('<td data-label="Person">Neighbour C</td><td data-label="Phone">555 0199</td>', page.replace("\n", "").replace("  ", ""))
        self.assertNotIn("private details", page)
        self.assertIn("window.print()", page)

    def test_sheet_with_private_column_says_so(self):
        self.app.config["LOADED"][0].sheets[0]["sections"].append(
            {"title": "Medical", "table": "important_info", "where": {}, "columns": ["detail"], "order_by": "id"})
        self.assertIn("includes private details", self.get("/sheet/people/emergency?show=1").get_data(as_text=True))

    def test_cross_module_column_prints_the_linked_contacts_phone(self):
        self.make_module("loans", module=LOANS_MODULE, tables=LOANS_TABLES, labels=None)
        self.write("modules/loans/sheets.toml", LOANS_SHEET)
        make_migration.make(self.tmp / "modules" / "loans", "first_tables")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "modules")
        self.assertEqual(report.module_problems, {})
        app = create_app("t", lambda: None, report, data_dir=data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        post = lambda path, values: client.post(path, data=dict(values, _csrf=app.config["CSRF_TOKEN"]),  # noqa: E731
                                                 base_url=BASE)
        post("/t/people__people/new", {"name": "Neighbour C", "phone": "555 0199", "then": "done"})
        post("/t/loans__loans/new", {"name": "Ladder", "borrower": "1", "then": "done"})
        page = client.get("/sheet/loans/out", base_url=BASE).get_data(as_text=True).replace("\n", "").replace("  ", "")
        self.assertIn('<td data-label="Borrower">Neighbour C</td><td data-label="Phone">555 0199</td>', page)
        self.assertNotIn("private details", page)

    def test_unknown_or_switched_off_sheet_is_not_found(self):
        self.assertEqual(self.get("/sheet/people/nothing").status_code, 404)
        self.post("/settings", {"modules": []})
        self.assertEqual(self.get("/sheet/people/emergency").status_code, 404)
