"""Tests for one-step actions (buttons like Mark returned) and the date order rule `not_before` (decision 0075)."""
from datetime import date

from support import DEMO_MODULE, TempDirTestCase
import make_migration
from dashboard.core import db, modules, records, startup

TABLES = '''[tables.items]
title = "Items"
columns.name = { type = "text", required = true }
columns.quantity = { type = "integer" }
columns.code = { type = "text", sensitive = true }

[tables.lots]
title = "Lots"
columns.item = { type = "link", to = "items", required = true }
columns.amount = { type = "integer" }
columns.state = { type = "choice", default = "open", choices = ["open", "finished"] }
columns.opened = { type = "date" }
columns.finished_on = { type = "date", required_when = { state = "finished" }, not_before = "opened" }
columns.note = { type = "text" }

[tables.lots.total]
link = "item"
amount = "amount"
into = "quantity"

[[tables.lots.actions]]
key = "finish"
label = "Finish it"
show_when = { state = "open" }
set = { state = "finished", finished_on = "today", amount = 0 }
done = "Finished today."
'''

LABELS = '''[tables.lots]
columns.opened = { label = "Opened on" }
columns.finished_on = { label = "Finished on" }
'''


class ActionLoadingTests(TempDirTestCase):
    """Mistakes in an action or a date order are explained when the module loads, in plain words."""

    def problems(self, tables=TABLES, labels=LABELS):
        folder = self.make_module(tables=tables, labels=labels)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " | ".join(caught.exception.problems)

    def with_set(self, values: str, shown: str = '{ state = "open" }') -> str:
        return self.problems(TABLES.replace('set = { state = "finished", finished_on = "today", amount = 0 }',
                                            f"set = {values}").replace('show_when = { state = "open" }',
                                                                       f"show_when = {shown}"))

    def test_a_valid_action_and_date_order_load(self):
        module = modules.load_module(self.make_module(tables=TABLES, labels=LABELS))
        lots = module.tables["lots"]
        self.assertEqual([a["key"] for a in lots.actions], ["finish"])
        self.assertEqual(lots.actions[0]["set"]["finished_on"], "today")
        self.assertEqual(lots.columns["finished_on"].not_before, "opened")

    def test_unknown_column_suggests_the_closest(self):
        text = self.with_set('{ state = "finished", finished_onn = "today" }')
        self.assertIn("actions 'finish', set: there is no column 'finished_onn'", text)
        self.assertIn("Did you mean 'finished_on'", text)

    def test_a_private_column_cannot_be_set_or_decide_when_it_shows(self):
        tables = TABLES.replace('columns.note = { type = "text" }', 'columns.note = { type = "text", sensitive = true }')
        text = self.problems(tables.replace('amount = 0 }', 'amount = 0, note = "done" }'))
        self.assertIn("'note' is private, so an action can't change it", text)
        text = self.problems(tables.replace('show_when = { state = "open" }', 'show_when = { state = "open", note = "x" }'))
        self.assertIn("'note' is private, so it can't decide when a button shows", text)

    def test_a_worked_out_total_cannot_be_set(self):
        tables = TABLES + '''
[[tables.items.actions]]
key = "empty"
label = "Empty"
show_when = { name = "Rice" }
set = { name = "Rice (empty)", quantity = 0 }
done = "Emptied."
'''
        self.assertIn("'quantity' is worked out from other records", self.problems(tables))

    def test_a_choice_must_be_one_of_its_choices_and_values_must_fit_the_column(self):
        text = self.with_set('{ state = "done", finished_on = "today" }')
        self.assertIn("'state' can't be set to 'done': it is not one of the choices. Allowed: open, finished", text)
        self.assertIn("'finished_on' can't be set to 'yesterday'",
                      self.with_set('{ state = "finished", finished_on = "yesterday" }'))
        self.assertIn("links and files can't be set", self.with_set('{ state = "finished", finished_on = "today", item = 1 }'))

    def test_show_when_must_name_real_columns_and_choices(self):
        self.assertIn("show_when: 'closed' is not one of the choices for 'state'",
                      self.with_set('{ state = "finished", finished_on = "today" }', '{ state = "closed" }'))
        self.assertIn("show_when: there is no column 'stat'",
                      self.with_set('{ state = "finished", finished_on = "today" }', '{ stat = "open" }'))
        self.assertIn("show_when: write it as settings", self.with_set('{ state = "finished", finished_on = "today" }', '"open"'))

    def test_the_button_must_go_away_once_pressed(self):
        self.assertIn("'set' must change a column named in show_when", self.with_set('{ note = "done" }'))

    def test_what_it_sets_must_not_leave_a_required_field_blank(self):
        self.assertIn("makes 'finished_on' required, so set that too", self.with_set('{ state = "finished" }'))

    def test_missing_parts_and_unknown_settings_are_named(self):
        text = self.problems(TABLES.replace('done = "Finished today."\n', 'colour = "red"\n'))
        self.assertIn("'done' is missing", text)
        self.assertIn("unknown setting 'colour'", text)

    def test_labels_may_reword_a_declared_action_only(self):
        module = modules.load_module(self.make_module(tables=TABLES, labels=LABELS + 'actions.finish = { label = "All gone", done = "Marked all gone." }\n'))
        self.assertEqual(module.labels["tables"]["lots"]["actions"]["finish"]["label"], "All gone")
        text = self.problems(labels=LABELS + 'actions.finnish = { label = "All gone" }\n')
        self.assertIn("action 'finnish': tables.toml declares no such action. Did you mean 'finish'", text)
        self.assertIn("unknown setting 'colour'", self.problems(labels=LABELS + 'actions.finish = { colour = "red" }\n'))

    def test_not_before_names_another_date_column_of_the_same_table(self):
        for wrong in ('not_before = "openned"', 'not_before = "note"', 'not_before = "finished_on"'):
            text = self.problems(TABLES.replace('not_before = "opened"', wrong))
            self.assertIn("column 'finished_on': not_before names another date column of this table", text)
        tables = TABLES.replace('columns.note = { type = "text" }', 'columns.note = { type = "text", not_before = "opened" }')
        self.assertIn("column 'note': not_before", self.problems(tables))


class ActionSavingTests(TempDirTestCase):
    """Pressing an action saves through the normal path: checks, history and totals, all at once."""

    def setUp(self):
        super().setUp()
        make_migration.make(self.make_module(tables=TABLES, labels=LABELS), "first_tables")
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.module_problems, {})
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.records = records.Records(self.conn, records.build_registry(report.loaded))
        self.rice = self.records.create("demo__items", {"name": "Rice"})
        self.lot = self.records.create("demo__lots", {"item": self.rice, "amount": 4, "opened": "2026-01-02"})

    def quantity(self):
        return self.records.get("demo__items", self.rice)["quantity"]

    def test_it_sets_the_fields_with_today_keeps_history_and_updates_the_total(self):
        self.assertEqual(self.quantity(), 4)
        changed = self.records.action("demo__lots", self.lot, "finish")
        lot = self.records.get("demo__lots", self.lot)
        self.assertEqual((lot["state"], lot["finished_on"], lot["amount"]), ("finished", date.today().isoformat(), 0))
        self.assertEqual(changed["state"], ["open", "finished"])
        self.assertEqual(self.quantity(), 0)  # the item's total follows, as for any change
        self.assertEqual(self.records.history("demo__lots", self.lot)[-1]["after"]["state"], "finished")

    def test_pressed_twice_it_is_refused_and_nothing_changes(self):
        self.records.action("demo__lots", self.lot, "finish")
        before = self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
        with self.assertRaises(records.ActionNotAvailable) as caught:
            self.records.action("demo__lots", self.lot, "finish")
        self.assertIn("Nothing was changed", str(caught.exception))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0], before)

    def test_an_unknown_action_or_a_deleted_record_is_not_found(self):
        with self.assertRaises(records.RecordNotFound):
            self.records.action("demo__lots", self.lot, "explode")
        self.records.delete("demo__lots", self.lot)
        with self.assertRaises(records.RecordNotFound):
            self.records.action("demo__lots", self.lot, "finish")

    def test_a_date_order_mistake_refuses_the_whole_action(self):
        self.records.update("demo__lots", self.lot, {"opened": "2999-01-01"})
        with self.assertRaises(records.ValidationError) as caught:
            self.records.action("demo__lots", self.lot, "finish")
        self.assertEqual(caught.exception.problems, {"finished_on": "Finished on can't be before Opened on."})
        lot = self.records.get("demo__lots", self.lot)
        self.assertEqual((lot["state"], lot["amount"]), ("open", 4))
        self.assertEqual(self.quantity(), 4)

    def test_not_before_is_checked_on_create_and_update(self):
        with self.assertRaises(records.ValidationError) as caught:
            self.records.create("demo__lots", {"item": self.rice, "opened": "2026-03-02", "finished_on": "2026-03-01",
                                               "state": "finished"})
        self.assertEqual(caught.exception.problems["finished_on"], "Finished on can't be before Opened on.")
        self.records.update("demo__lots", self.lot, {"state": "finished", "finished_on": "2026-01-02"})  # same day is fine
        with self.assertRaises(records.ValidationError):
            self.records.update("demo__lots", self.lot, {"opened": "2026-01-03"})  # moving the first date past it
        self.records.update("demo__lots", self.lot, {"opened": None})  # either date blank: nothing to compare
        self.records.update("demo__lots", self.lot, {"opened": "2025-12-31"})


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
