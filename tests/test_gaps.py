"""Tests for gaps: details worth filling in, declared in a table's `watch.gaps` and asked as questions."""
from support import TempDirTestCase
from dashboard.core import db, modules, records, startup, watch
import make_migration

TABLES = '''[tables.people]
title = "People"
columns.name = { type = "text", required = true }
columns.lives_here = { type = "boolean" }
columns.phone = { type = "text" }

[tables.roles]
title = "Who to call"
columns.person = { type = "link", to = "people", on_delete = "cascade", required = true }
columns.role = { type = "choice", required = true, choices = [{ key = "emergency_contact", label = "Emergency contact" }, "doctor"] }
columns.notes = { type = "text" }
'''
RULES = '''
[[tables.people.watch.gaps]]
none = { lives_here = true }
message = "Who lives here?"

[[tables.roles.watch.gaps]]
none = { role = "emergency_contact" }
message = "Who would you call first?"

[[tables.roles.watch.gaps]]
missing = "person.phone"
message = "What is {person}'s number? ({role})"

[[tables.roles.watch.gaps]]
missing = "notes"
where = { role = "doctor" }
message = "Any notes for {person}?"
'''


class GapRulesTests(TempDirTestCase):
    def problems(self, rules):
        folder = self.make_module(tables=TABLES + rules, labels=None)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " | ".join(caught.exception.problems)

    def gap(self, body):
        return self.problems(f"\n[[tables.roles.watch.gaps]]\n{body}\n")

    def test_valid_rules_load(self):
        module = modules.load_module(self.make_module(tables=TABLES + RULES, labels=None))
        rules = module.tables["roles"].watch["gaps"]
        self.assertEqual(rules[0], {"none": {"role": "emergency_contact"}, "message": "Who would you call first?"})
        self.assertEqual(rules[1]["missing"], "person.phone")
        self.assertEqual(module.tables["people"].watch["gaps"][0]["none"], {"lives_here": True})

    def test_mistakes_are_explained(self):
        self.assertIn("'message' is missing", self.gap('none = { role = "doctor" }'))
        self.assertIn("either 'missing'", self.gap('message = "Hm?"'))
        self.assertIn("either 'missing'", self.gap('missing = "notes"\nnone = { role = "doctor" }\nmessage = "Hm?"'))
        self.assertIn("not one of the choices", self.gap('none = { role = "plumber" }\nmessage = "Hm?"'))
        self.assertIn("Did you mean 'role'", self.gap('none = { rol = "doctor" }\nmessage = "Hm?"'))
        self.assertIn("like \"person.phone\"", self.gap('missing = "person.fax"\nmessage = "Hm?"'))
        self.assertIn("like \"person.phone\"", self.gap('missing = "role.phone"\nmessage = "Hm?"'))
        self.assertIn("not {owner}", self.gap('missing = "notes"\nmessage = "Ask {owner}"'))
        self.assertIn("cannot use", self.gap('none = { role = "doctor" }\nmessage = "Ask {person}"'))
        self.assertIn("unmatched", self.gap('missing = "notes"\nmessage = "Ask {person"'))
        self.assertIn("Did you mean 'missing'", self.gap('mising = "notes"\nmessage = "Hm?"'))
        self.assertIn("true or false", self.problems('\n[[tables.people.watch.gaps]]\nnone = { lives_here = "yes" }\n'
                                                     'message = "Hm?"\n'))


class GapResultsTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        make_migration.make(self.make_module(tables=TABLES + RULES, labels=None), "first_tables")
        startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual(failures, {})
        self.registry = records.build_registry(found)
        self.records = records.Records(self.conn, self.registry)

    def messages(self):
        return [g.message for g in watch.gaps(self.conn, self.registry)]

    def test_an_empty_household_is_asked_the_none_questions(self):
        gaps = watch.gaps(self.conn, self.registry)
        self.assertEqual([g.message for g in gaps], ["Who lives here?", "Who would you call first?"])
        self.assertEqual(gaps[0].fix, "/t/demo__people/new?lives_here=yes")
        self.assertEqual(gaps[1].fix, "/t/demo__roles/new?role=emergency_contact")

    def test_missing_linked_detail_is_asked_once_per_person_and_links_to_them(self):
        here = self.records.create("demo__people", {"name": "Person A", "lives_here": True, "phone": "555 0101"})
        friend = self.records.create("demo__people", {"name": "Friend B"})
        self.records.create("demo__roles", {"person": here, "role": "emergency_contact"})
        self.records.create("demo__roles", {"person": friend, "role": "emergency_contact"})
        self.records.create("demo__roles", {"person": friend, "role": "doctor", "notes": "Clinic"})
        gaps = watch.gaps(self.conn, self.registry)
        self.assertEqual([g.message for g in gaps], ["What is Friend B's number? (Emergency contact)"])
        self.assertEqual(gaps[0].fix, f"/t/demo__people/{friend}")

    def test_a_filled_in_or_deleted_detail_is_no_longer_asked(self):
        self.records.create("demo__people", {"name": "Person A", "lives_here": True})
        friend = self.records.create("demo__people", {"name": "Friend B"})
        doctor = self.records.create("demo__roles", {"person": friend, "role": "doctor", "notes": "  "})
        self.records.create("demo__roles", {"person": friend, "role": "emergency_contact"})
        self.assertIn("Any notes for Friend B?", self.messages())
        self.records.update("demo__people", friend, {"phone": "555 0199"})
        self.records.update("demo__roles", doctor, {"notes": "Clinic"})
        self.assertEqual(self.messages(), [])
        self.records.delete("demo__people", friend)
        self.assertEqual(self.messages(), ["Who would you call first?"])
