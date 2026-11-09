"""Tests for records that change a linked quantity (stock in and out), and the checks on `adjusts`."""
from support import TempDirTestCase
from dashboard.core import db, modules, records, startup
import make_migration

TABLES = '''[tables.items]
title = "Items"
columns.name = { type = "text", required = true }
columns.quantity = { type = "decimal", min = 0 }

[tables.moves]
title = "Moves"
columns.item = { type = "link", to = "items", required = true, on_delete = "cascade" }
columns.reason = { type = "choice", required = true, choices = ["bought", "used", "expired"] }
columns.amount = { type = "decimal", required = true, min = 0 }
columns.day = { type = "date", default = "today" }

[tables.moves.adjusts]
link = "item"
quantity = "quantity"
amount = "amount"
direction = "reason"
adds = ["bought"]
'''


class AdjustRulesTests(TempDirTestCase):
    def problems(self, tables):
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(self.make_module(tables=tables, labels=None))
        return " | ".join(caught.exception.problems)

    def test_valid_rule_loads(self):
        rule = modules.load_module(self.make_module(tables=TABLES, labels=None)).tables["moves"].adjusts
        self.assertEqual(rule["target"], "items")
        self.assertEqual(rule["adds"], ["bought"])

    def test_mistakes_are_explained(self):
        self.assertIn("'link' must name a link column", self.problems(TABLES.replace('link = "item"', 'link = "reason"')))
        self.assertIn("Did you mean 'quantity'", self.problems(TABLES.replace('quantity = "quantity"\namount', 'quantity = "quantty"\namount')))
        self.assertIn("not choices: sold", self.problems(TABLES.replace('adds = ["bought"]', 'adds = ["sold"]')))
        self.assertIn("'adds' is missing", self.problems(TABLES.replace('adds = ["bought"]\n', '')))


class AdjustTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        make_migration.make(self.make_module(tables=TABLES, labels=None), "first_tables")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.records = records.Records(self.conn, records.build_registry(report.loaded))
        self.item = self.records.create("demo__items", {"name": "Tins", "quantity": 4})

    def count(self):
        return self.records.get("demo__items", self.item)["quantity"]

    def move(self, reason, amount):
        return self.records.create("demo__moves", {"item": self.item, "reason": reason, "amount": amount})

    def test_buying_adds_and_using_takes_away(self):
        self.move("bought", 6)
        self.assertEqual(self.count(), 10)
        self.move("used", 3)
        self.move("expired", 1)
        self.assertEqual(self.count(), 6)

    def test_date_defaults_to_today(self):
        from datetime import date
        move = self.move("bought", 1)
        self.assertEqual(self.records.get("demo__moves", move)["day"], date.today().isoformat())

    def test_blank_date_from_a_form_uses_the_default(self):
        from datetime import date
        move = self.records.create("demo__moves", {"item": self.item, "reason": "bought", "amount": 1, "day": ""})
        self.assertEqual(self.records.get("demo__moves", move)["day"], date.today().isoformat())

    def test_cannot_take_out_more_than_there_is(self):
        with self.assertRaises(records.ValidationError) as caught:
            self.move("used", 5)
        self.assertIn("only 4 left", caught.exception.problems["amount"])
        self.assertEqual(self.count(), 4)
        self.assertEqual(self.records.count("demo__moves"), 0, "nothing is saved when the move is refused")

    def test_deleting_undoes_and_restoring_reapplies(self):
        move = self.move("used", 3)
        self.assertEqual(self.count(), 1)
        self.records.delete("demo__moves", move)
        self.assertEqual(self.count(), 4)
        self.records.restore("demo__moves", move)
        self.assertEqual(self.count(), 1)

    def test_changing_a_move_corrects_the_count(self):
        move = self.move("used", 3)
        self.records.update("demo__moves", move, {"amount": 1})
        self.assertEqual(self.count(), 3)
        self.records.update("demo__moves", move, {"reason": "bought"})
        self.assertEqual(self.count(), 5)

    def test_item_history_shows_each_change(self):
        self.move("bought", 2)
        changes = [h for h in self.records.history("demo__items", self.item) if h["action"] == "update"]
        self.assertEqual(changes[-1]["before"], {"quantity": 4})
        self.assertEqual(changes[-1]["after"], {"quantity": 6})

    def test_deleting_the_item_with_its_moves_is_allowed(self):
        self.move("used", 4)
        self.records.delete("demo__items", self.item)
        self.assertEqual(self.records.count("demo__moves"), 0)
