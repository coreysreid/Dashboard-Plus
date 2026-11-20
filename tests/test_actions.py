"""Tests for actions: one-step buttons like Mark returned, the date order rule `not_before` (decision 0075), and the checks on actions that add a record (decision 0091)."""
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


FORM_TABLES = '''[tables.jobs]
title = "Jobs"
columns.name = { type = "text", required = true }
columns.last_done = { type = "date" }
columns.next_due = { type = "date" }
columns.every = { type = "integer", min = 1, max = 99 }
columns.unit = { type = "choice", choices = ["weeks", "months", "years"] }
columns.secret = { type = "text", sensitive = true }

[tables.work]
title = "Work"
columns.job = { type = "link", to = "jobs", required = true }
columns.done_on = { type = "date", required = true, default = "today" }
columns.note = { type = "longtext" }
columns.code = { type = "text", sensitive = true }
columns.kind = { type = "choice", choices = ["check", "repair"] }

[[tables.jobs.actions]]
key = "done"
label = "Mark done"
title = "Mark {record} done"
done = "Marked done on {done_on}."
undo = "Undo it"
adds = { table = "work", link = "job", ask = ["done_on", "note"], values = { kind = "check" } }
latest = { date = "done_on", into = "last_done" }
next_date = { into = "next_due", question = "When next?", repeat = { count = "every", unit = "unit" } }
help = { done_on = "The day." }
'''


class FormActionLoadingTests(TempDirTestCase):
    """An action that adds a record through a small form (decision 0091) is checked when the module loads."""

    def problems(self, old: str, new: str, labels=None) -> str:
        self.assertIn(old, FORM_TABLES)
        folder = self.make_module(tables=FORM_TABLES.replace(old, new), labels=labels)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " | ".join(caught.exception.problems)

    def test_a_valid_form_action_loads_with_default_messages(self):
        module = modules.load_module(self.make_module(tables=FORM_TABLES, labels=None))
        action = module.tables["jobs"].actions[0]
        self.assertEqual(action["adds"], {"table": "work", "link": "job", "ask": ["done_on", "note"],
                                          "values": {"kind": "check"}, "add_button": None})
        self.assertEqual(action["next_date"]["repeat"], {"count": "every", "unit": "unit"})
        self.assertEqual((action["show_when"], action["set"]), ({}, {}))  # neither is needed
        self.assertIn("Nothing was saved", action["messages"]["stale"])

    def test_the_added_table_and_its_link_must_be_real(self):
        text = self.problems('table = "work"', 'table = "wrok"')
        self.assertIn("'table' must name another table of this module", text)
        self.assertIn("Did you mean 'work'", text)
        self.assertIn("'link' must name the column of 'work' that points at 'jobs'",
                      self.problems('link = "job"', 'link = "note"'))

    def test_what_it_asks_must_be_public_typed_in_fields(self):
        self.assertIn("'code' is private, so this form can't ask for it",
                      self.problems('ask = ["done_on", "note"]', 'ask = ["done_on", "note", "code"]'))
        self.assertIn("'job' is filled in by the action itself",
                      self.problems('ask = ["done_on", "note"]', 'ask = ["done_on", "job"]'))
        self.assertIn("'work' has no column 'nots'. Did you mean 'note'",
                      self.problems('ask = ["done_on", "note"]', 'ask = ["done_on", "nots"]'))
        self.assertIn("'kind' can't be set to 'fix'",
                      self.problems('values = { kind = "check" }', 'values = { kind = "fix" }'))
        self.assertIn("'note' is asked or linked already",
                      self.problems('values = { kind = "check" }', 'values = { note = "x" }'))

    def test_a_required_field_left_unasked_is_named(self):
        old = 'columns.kind = { type = "choice", choices = ["check", "repair"] }'
        text = self.problems(old, old + '\ncolumns.cost = { type = "money", required = true }')
        self.assertIn("'cost' is required in 'work', so ask for it or give it a value", text)

    def test_latest_next_date_and_repeat_name_the_right_kinds_of_column(self):
        self.assertIn("latest: 'date' must be one of the asked fields and a date",
                      self.problems('latest = { date = "done_on"', 'latest = { date = "note"'))
        self.assertIn("latest: 'into' must be a date column of 'jobs'",
                      self.problems('into = "last_done" }', 'into = "name" }'))
        self.assertIn("'secret' is not a date column", self.problems('into = "last_done" }', 'into = "secret" }'))
        self.assertIn("next_date: it needs 'latest' too",
                      self.problems('latest = { date = "done_on", into = "last_done" }\n', ''))
        self.assertIn("next_date: 'next_due' is filled in elsewhere",
                      self.problems('into = "last_done" }', 'into = "next_due" }'))
        self.assertIn("repeat: 'count' must name a whole-number column",
                      self.problems('count = "every"', 'count = "unit"'))
        self.assertIn("whose choices are among weeks, months, years",
                      self.problems('choices = ["weeks", "months", "years"]', 'choices = ["weeks", "fortnights"]'))
        self.assertIn("'question' is the heading", self.problems('question = "When next?"', 'question = ""'))

    def test_words_name_only_what_they_can_and_unknown_settings_are_reported(self):
        self.assertIn("'done' may name only asked fields, like {done_on}, not {due}",
                      self.problems('done = "Marked done on {done_on}."', 'done = "Due {due}."'))
        self.assertIn("'title' may name only {record}",
                      self.problems('title = "Mark {record} done"', 'title = "Mark {name}"'))
        self.assertIn("'help' gives words under asked fields", self.problems('help = { done_on', 'help = { name'))
        self.assertIn("adds: unknown setting 'tabel'", self.problems('adds = { table', 'adds = { tabel = "x", table'))
        self.assertIn("messages: unknown setting 'stal'",
                      self.problems('undo = "Undo it"', 'undo = "Undo it"\nmessages = { stal = "x" }'))
        self.assertIn("'same_day' may name only {date}",
                      self.problems('undo = "Undo it"', 'undo = "Undo it"\nmessages = { same_day = "On {day}" }'))

    def test_form_settings_need_adds(self):
        text = self.problems('adds = { table = "work", link = "job", ask = ["done_on", "note"], values = { kind = "check" } }\n',
                             'show_when = { name = "x" }\nset = { name = "y" }\n')
        self.assertIn("only work in an action that adds a record", text)

    def test_labels_may_reword_its_title_intro_and_undo(self):
        labels = '[tables.jobs]\nactions.done = { title = "Finished {record}", undo = "Take it back" }\n'
        module = modules.load_module(self.make_module(tables=FORM_TABLES, labels=labels))
        self.assertEqual(module.labels["tables"]["jobs"]["actions"]["done"]["undo"], "Take it back")


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
