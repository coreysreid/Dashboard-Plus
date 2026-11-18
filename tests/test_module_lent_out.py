"""Tests for the Things lent out module: due-back reminders only while a loan is out, borrowers in People, Stock untouched, privacy.

These follow the checks in Lane B's draft (its ACCEPTANCE.md and NOTES.md, now in git history) that apply today
(decisions 0072, 0073)."""
import re
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5134
BASE = f"http://127.0.0.1:{PORT}"


class LentOutModuleTests(TempDirTestCase):
    MODULES = ("people", "stock", "lent_out")

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
        self.friend = self.records.create("people__people", {"name": "Person A"})

    def day(self, offset):
        return (self.today + timedelta(days=offset)).isoformat()

    def loan(self, name="Cordless drill", **values):
        values = {"borrower": self.friend, "due_back": self.day(3), **values}
        return self.records.create("lent_out__loans", {"name": name, **values})

    def returned(self, loan, offset=0):
        self.records.update("lent_out__loans", loan, {"status": "returned", "returned_on": self.day(offset)})

    def gaps(self):
        return [g for g in watch.gaps(self.conn, self.registry) if g.table.startswith("lent_out__")]

    def due(self):
        return {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)
                if i.table.startswith("lent_out__")}

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, path):
        return self.client().get(path, base_url=BASE).get_data(as_text=True)

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertIn("lent_out", self.report.modules)

    def test_it_links_to_people_and_stock_and_says_so(self):
        module = modules.load_module(ROOT / "modules" / "lent_out")
        self.assertEqual(module.requires, ["people", "stock"])
        columns = module.tables["loans"].columns
        self.assertEqual((columns["borrower"].to, columns["stock_item"].to), ("people.people", "stock.items"))
        self.assertEqual(module.labels["tables"]["loans"]["home"], "main")

    def test_a_household_with_no_loans_is_asked_nothing(self):
        self.records.delete("people__people", self.friend)
        self.assertEqual(self.gaps(), [])
        self.assertEqual(self.due(), {})

    def test_due_back_reads_due_or_overdue_and_only_within_a_week(self):
        self.loan("Cordless drill", due_back=self.day(1))
        self.loan("Ladder", due_back=self.day(0))
        self.loan("Garden trowel", due_back=self.day(-1))
        self.loan("Camping stove", due_back=self.day(20))
        details = self.due()
        self.assertTrue(details["Cordless drill, lent to Person A"].startswith("return due"), details)
        self.assertEqual(details["Ladder, lent to Person A"], "return due today")
        self.assertIn("return overdue since", details["Garden trowel, lent to Person A"])
        self.assertNotIn("Camping stove, lent to Person A", details)
        self.assertNotIn("expire", " ".join(details.values()))

    def test_a_returned_loan_is_never_overdue_and_reopening_brings_the_reminder_back(self):
        loan = self.loan(due_back=self.day(-5))
        self.assertEqual(len(self.due()), 1)
        self.returned(loan)
        self.assertEqual(self.due(), {})
        self.records.update("lent_out__loans", loan, {"status": "out"})  # a mistaken return, corrected
        self.assertEqual(len(self.due()), 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM lent_out__loans").fetchone()[0], 1)  # kept as history

    def test_returned_needs_the_date_it_came_back(self):
        loan = self.loan()
        with self.assertRaises(records.ValidationError):
            self.records.update("lent_out__loans", loan, {"status": "returned"})

    def test_a_loan_needs_a_borrower_and_a_due_date(self):
        with self.assertRaises(records.ValidationError):
            self.records.create("lent_out__loans", {"name": "Ladder", "due_back": self.day(3)})
        with self.assertRaises(records.ValidationError):
            self.records.create("lent_out__loans", {"name": "Ladder", "borrower": self.friend})

    def test_how_to_reach_the_borrower_is_asked_once_and_only_while_something_is_out(self):
        first = self.loan("Cordless drill")
        second = self.loan("Ladder")
        found = self.gaps()
        self.assertEqual([g.message for g in found],
                         ["How would you reach Person A about Cordless drill? Add a phone number if you have one."])
        self.assertEqual(found[0].fix, f"/t/people__people/{self.friend}")  # filled in on their People record
        self.returned(first)
        self.returned(second)
        self.assertEqual(self.gaps(), [])
        self.records.update("lent_out__loans", second, {"status": "out", "returned_on": None})
        self.records.update("people__people", self.friend, {"phone": "0491 570 110"})
        self.assertEqual(self.gaps(), [])

    def test_a_borrower_with_a_loan_cannot_be_deleted(self):
        self.loan()
        with self.assertRaises(records.ValidationError):
            self.records.delete("people__people", self.friend)

    def test_lending_a_stock_item_changes_no_count_and_deleting_it_keeps_the_loan(self):
        drill = self.records.create("stock__items", {"name": "Cordless drill", "category": "tools", "quantity": 1})
        moves = self.conn.execute("SELECT COUNT(*) FROM stock__movements").fetchone()[0]
        loan = self.loan(stock_item=drill)
        self.returned(loan)
        self.assertEqual(self.conn.execute("SELECT quantity FROM stock__items WHERE id = ?", (drill,)).fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM stock__movements").fetchone()[0], moves)
        self.conn.execute("DELETE FROM stock__items WHERE id = ?", (drill,))  # removed for good: the link clears
        row = self.conn.execute("SELECT name, stock_item FROM lent_out__loans WHERE id = ?", (loan,)).fetchone()
        self.assertEqual((row["name"], row["stock_item"]), ("Cordless drill", None))

    def test_the_sheet_lists_only_loans_still_out_with_the_borrowers_phone_and_no_notes(self):
        self.records.update("people__people", self.friend, {"phone": "0491 570 110"})
        self.loan("Cordless drill", notes="Charger is in the blue bag")
        self.returned(self.loan("Garden trowel"))
        sheet = self.page("/sheet/lent_out/still_out")
        for shown in ("Things still lent out", "Cordless drill", "Person A", "0491 570 110", "Due back"):
            self.assertIn(shown, sheet)
        self.assertNotIn("Garden trowel", sheet)
        self.assertNotIn("Charger is in the blue bag", sheet)
        self.assertNotIn("private details", sheet)

    def test_the_form_says_nothing_is_sent_and_stock_is_not_changed(self):
        page = self.page("/t/lent_out__loans/new")
        self.assertIn("Who borrowed it", page)
        self.assertIn("nothing is sent to them", page)
        self.assertIn("does not change how many Stock says you have", page)

    def test_home_page_has_a_things_lent_out_card(self):
        page = self.page("/")
        self.assertIn("Things lent out", page)
        self.assertIn("/t/lent_out__loans", page)
        self.assertIn("/sheet/lent_out/still_out", page)

    def test_nothing_private_is_stored_named_or_asked(self):
        """No private column, and nothing private in a record's name or a question (decisions 0055, 0059)."""
        module = modules.load_module(ROOT / "modules" / "lent_out")
        people = modules.load_module(ROOT / "modules" / "people").tables["people"].columns
        table = module.tables["loans"]
        self.assertEqual([n for n, c in table.columns.items() if c.sensitive], [])
        names = set(re.findall(r"{(\w+)", table.record_name or ""))
        asked = {f for g in table.watch["gaps"] for f in re.findall(r"{(\w+)", g["message"])}
        self.assertFalse({n for n in names | asked if table.columns[n].sensitive})
        self.assertFalse(people["phone"].sensitive)  # the one detail it prints from People is not private

    def test_switching_it_on_changes_nothing_in_people_or_stock(self):
        before_dir = self.tmp / "before"
        for name in ("people", "stock"):
            shutil.copytree(ROOT / "modules" / name, before_dir / "modules" / name)
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        conn = db.connect(before_dir / "data" / "dashboard.db")
        old = records.Records(conn, records.build_registry(report.loaded))
        old.create("people__people", {"name": "Person A", "phone": "0491 570 110"})
        old.create("stock__items", {"name": "Cordless drill", "category": "tools", "quantity": 1})
        tables = ("people__people", "stock__places", "stock__items", "stock__movements")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        conn.close()

        shutil.copytree(ROOT / "modules" / "lent_out", before_dir / "modules" / "lent_out")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        self.assertEqual(report.module_problems, {})
        self.assertIn("lent_out", report.modules)
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        self.assertEqual({t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables},
                         snapshot)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM lent_out__loans").fetchone()[0], 0)

    def test_migration_matches_its_description_and_touches_only_its_own_tables(self):
        from dashboard.core.schema import next_migration_sql
        module = modules.load_module(ROOT / "modules" / "lent_out")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "lent_out" / "migrations" / "0001_first_tables.sql").read_text(encoding="utf-8")
        created = re.findall(r"CREATE (?:TABLE|INDEX) (\S+)", sql)
        self.assertTrue(created)
        self.assertTrue(all(name.startswith("lent_out__") for name in created), created)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")
