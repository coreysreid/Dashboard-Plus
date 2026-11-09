"""Tests for saving, checking, linking, deleting and restoring records, and their history."""
from support import TempDirTestCase
from dashboard.core import db, modules, records, startup
import make_migration

TABLES = '''[tables.owners]
title = "Owners"
columns.name = { type = "text", required = true }

[tables.things]
title = "Things"
columns.name = { type = "text", required = true }
columns.kind = { type = "choice", choices = ["tool", { key = "first_aid", label = "First aid" }], default = "tool" }
columns.owner = { type = "link", to = "owners", on_delete = "restrict" }
columns.quantity = { type = "measure", unit = "kg", min = 0, max = 1000 }
columns.count = { type = "integer" }
columns.price = { type = "money" }
columns.bought = { type = "date" }
columns.ok = { type = "boolean" }
columns.photo = { type = "file" }
columns.helpers = { type = "links", to = "owners" }

[tables.notes]
title = "Notes"
columns.text = { type = "longtext" }
columns.thing = { type = "link", to = "things", on_delete = "cascade" }

[tables.tags]
title = "Tags"
columns.thing = { type = "link", to = "things", on_delete = "clear" }
'''


class RecordTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        folder = self.make_module(tables=TABLES, labels=None)
        make_migration.make(folder, "first_tables")
        startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual(failures, {})
        self.ticks = 0
        self.records = records.Records(self.conn, records.build_registry(found), clock=self.clock)

    def clock(self):
        self.ticks += 1
        return f"2026-01-01T00:00:{self.ticks:02d}+00:00"

    def owner(self, name="Synthetic Owner"):
        return self.records.create("demo__owners", {"name": name})

    def test_create_converts_values_and_applies_defaults(self):
        owner = self.owner()
        thing = self.records.create("demo__things", {
            "name": "  Torch ", "owner": owner, "quantity": "2.5", "count": "3", "price": "12.34",
            "bought": "2026-06-03", "ok": "yes", "helpers": [owner, owner]})
        row = self.records.get("demo__things", thing)
        self.assertEqual(row["name"], "Torch")
        self.assertEqual(row["kind"], "tool")
        self.assertEqual(row["quantity"], 2.5)
        self.assertEqual(row["count"], 3)
        self.assertEqual(row["price"], 1234)
        self.assertEqual(row["ok"], 1)
        self.assertEqual(row["helpers"], [owner])
        self.assertEqual(row["source"], "person")
        self.assertEqual(row["review_status"], "confirmed")

    def test_choice_accepts_its_label(self):
        thing = self.records.create("demo__things", {"name": "Bandages", "kind": "First aid"})
        self.assertEqual(self.records.get("demo__things", thing)["kind"], "first_aid")

    def test_every_problem_is_reported_in_plain_words(self):
        with self.assertRaises(records.ValidationError) as caught:
            self.records.create("demo__things", {"nmae": "x", "quantity": "-1", "count": "1.5", "bought": "3 June",
                                                 "kind": "spoon", "ok": "maybe", "owner": 999})
        problems = caught.exception.problems
        self.assertIn("Did you mean 'name'", problems["nmae"])
        self.assertEqual(problems["name"], "is required.")
        self.assertIn("at least 0", problems["quantity"])
        self.assertIn("whole number", problems["count"])
        self.assertIn("2026-06-03", problems["bought"])
        self.assertIn("First aid", problems["kind"])
        self.assertIn("yes or no", problems["ok"])
        self.assertIn("does not exist", problems["owner"])
        self.assertEqual(self.records.count("demo__things"), 0, "nothing is saved when anything is wrong")

    def test_files_must_stay_inside_the_data_folder(self):
        for bad in ("../secrets.txt", "/etc/passwd", "C:\\\\Windows\\\\x"):
            with self.assertRaises(records.ValidationError):
                self.records.create("demo__things", {"name": "x", "photo": bad})

    def test_update_records_only_what_changed(self):
        thing = self.records.create("demo__things", {"name": "Torch", "count": 1})
        changed = self.records.update("demo__things", thing, {"count": "2", "name": "Torch"})
        self.assertEqual(changed, {"count": [1, 2]})
        self.assertEqual(self.records.update("demo__things", thing, {"count": 2}), {})
        history = self.records.history("demo__things", thing)
        self.assertEqual([h["action"] for h in history], ["create", "update"])
        self.assertEqual(history[1]["before"], {"count": 1})
        self.assertEqual(history[1]["after"], {"count": 2})
        self.assertEqual(self.records.get("demo__things", thing)["edited_by_person"], 1)

    def test_required_field_cannot_be_emptied(self):
        thing = self.records.create("demo__things", {"name": "Torch"})
        with self.assertRaises(records.ValidationError) as caught:
            self.records.update("demo__things", thing, {"name": " "})
        self.assertEqual(caught.exception.problems["name"], "is required.")

    def test_delete_is_refused_while_restricted_links_exist(self):
        owner = self.owner()
        self.records.create("demo__things", {"name": "Torch", "owner": owner})
        with self.assertRaises(records.ValidationError) as caught:
            self.records.delete("demo__owners", owner)
        self.assertIn("1 things record(s)", caught.exception.problems["delete"])
        self.assertEqual(self.records.count("demo__owners"), 1)

    def test_delete_cascades_and_clears_and_can_be_restored(self):
        thing = self.records.create("demo__things", {"name": "Torch"})
        note = self.records.create("demo__notes", {"text": "Spare batteries in drawer", "thing": thing})
        tag = self.records.create("demo__tags", {"thing": thing})
        self.records.delete("demo__things", thing)
        with self.assertRaises(records.RecordNotFound):
            self.records.get("demo__notes", note)
        self.assertIsNone(self.records.get("demo__tags", tag)["thing"])
        self.records.restore("demo__things", thing)
        self.assertEqual(self.records.get("demo__things", thing)["name"], "Torch")
        actions = [h["action"] for h in self.records.history("demo__things", thing)]
        self.assertEqual(actions, ["create", "delete", "restore"])

    def test_cannot_link_to_a_deleted_record(self):
        owner = self.owner()
        self.records.delete("demo__owners", owner)
        with self.assertRaises(records.ValidationError):
            self.records.create("demo__things", {"name": "Torch", "owner": owner})

    def test_pages_and_counts_leave_out_deleted_records(self):
        ids = [self.records.create("demo__things", {"name": f"Item {i:02d}"}) for i in range(12)]
        self.records.delete("demo__things", ids[0])
        self.assertEqual(self.records.count("demo__things"), 11)
        self.assertEqual(self.records.count("demo__things", include_deleted=True), 12)
        first = self.records.page("demo__things", offset=0, limit=5, order_by="name")
        self.assertEqual([r["name"] for r in first], [f"Item {i:02d}" for i in range(1, 6)])
        last = self.records.page("demo__things", offset=10, limit=5, order_by="name")
        self.assertEqual(len(last), 1)
        with self.assertRaises(records.ValidationError):
            self.records.page("demo__things", order_by="name; DROP TABLE x")

    def test_unknown_table_and_actor(self):
        with self.assertRaises(records.RecordNotFound) as caught:
            self.records.create("demo__thing", {"name": "x"})
        self.assertIn("demo__things", str(caught.exception))
        with self.assertRaises(ValueError):
            self.records.create("demo__things", {"name": "x"}, actor="hacker")

    def test_agent_changes_are_labelled_and_do_not_mark_person_edits(self):
        thing = self.records.create("demo__things", {"name": "Torch"}, actor="agent:helper", review_status="needs_review")
        self.records.update("demo__things", thing, {"count": 4}, actor="agent:helper")
        row = self.records.get("demo__things", thing)
        self.assertEqual((row["source"], row["review_status"], row["edited_by_person"]),
                         ("agent:helper", "needs_review", 0))
        self.assertEqual(self.records.history("demo__things", thing)[0]["actor"], "agent:helper")
