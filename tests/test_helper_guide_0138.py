"""Tests for decision 0138: the helper guide, connector words and published description say which lists a helper may fill, which it never may, and how units and the household's day apply. All data is invented."""
import json
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.connector import tools
from dashboard.core import db, helpers, proposals, records, settings, startup
from dashboard.core.proposals import ProposalError
from dashboard.web import api, helper_examples, helper_guide
from dashboard.web.app import create_app

PORT = 5147
BASE = f"http://127.0.0.1:{PORT}"
WHY = "Invented entries for the guide test"
OPENAPI = json.loads((ROOT / "src" / "dashboard" / "web" / "openapi-v1.json").read_text(encoding="utf-8"))
NEW_SINCE_0116 = ("pets__weigh_ins", "pet_feeding__servings", "vehicle_running__readings", "routines__times",
                  "routines__routines", "garden__jobs", "vehicle_running__estimates")


class GuideCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules", self.tmp / "modules")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        settings.put(self.conn, "setup.done", True)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        modules = sorted({i.module.name for i in self.registry.values()})
        self.helper, _ = helpers.issue(self.conn, self.data, "Everything helper", "suggest", modules)
        self.reader, _ = helpers.issue(self.conn, self.data, "Look helper", "read", modules)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        self.app = app

    def guide(self, helper=None) -> str:
        with self.app.app_context():
            return helper_guide.guide_text(self.conn, self.registry, helper or self.helper)

    def spec(self, name):
        return api.table_spec(self.registry[name], self.store, True, set())

    def writable(self) -> list[str]:
        allowed = helpers.allowed_registry(self.registry, self.helper)
        return [n for n in allowed if self.spec(n)["can_suggest"]]


class EveryWritableTableTests(GuideCase):
    def test_the_guide_names_every_list_a_helper_may_fill_in(self):
        text = self.guide()
        self.assertGreater(len(self.writable()), 30)
        for name in self.writable():
            title = self.spec(name)["title"]
            self.assertIn(f"{title} ({name}): you may suggest new records here.", text, name)

    def test_the_guide_never_says_a_private_or_person_only_list_may_be_suggested_into(self):
        text = self.guide()
        allowed = helpers.allowed_registry(self.registry, self.helper)
        blocked = [n for n in self.registry if n not in self.writable()]
        self.assertIn("medicine_doses__doses", blocked)
        for name in blocked:
            self.assertNotIn(f"({name}): you may suggest", text, name)
            if name in allowed:
                self.assertIn(f"({name}): look only.", text, name)
            else:  # a private list is not named or titled at all
                self.assertNotIn(name, text)
                self.assertNotIn(self.registry[name].table.title, text)
        for name in ("stock__refunds", "readiness__answers", "readiness__drill_runs", "people__important_info"):
            self.assertIn(f"({name}): look only.", text)

    def test_a_private_field_is_never_listed_as_something_to_send(self):
        text = self.guide()
        blocks = re.split(r"\n\n(?=[^\n-][^\n]*\([a-z_]+__[a-z_]+\):)", text)
        checked = 0
        for block in blocks:
            match = re.match(r"[^\n]*\(([a-z_]+__[a-z_]+)\):", block)
            if not match or match.group(1) not in self.registry:
                continue
            for column in self.registry[match.group(1)].table.columns.values():
                if column.sensitive:
                    checked += 1
                    self.assertNotIn(f"\n- {column.name}: ", block, match.group(1))
        self.assertGreater(checked, 20)

    def test_a_send_naming_a_price_money_back_or_a_dose_is_refused(self):
        for table, values in (("stock__movements", {"price": "3.50"}), ("stock__refunds", {"amount": "2.00"}),
                              ("medicine_doses__doses", {"amount": 1})):
            with self.assertRaises(ProposalError, msg=table) as caught:
                proposals.submit(self.conn, self.registry, self.helper,
                                 {"request_key": "k-" + table, "why": WHY,
                                  "entries": [{"table": table, "values": values}]})
            self.assertIn(caught.exception.status, (403, 404, 422), table)
            self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)


class NewListsTests(GuideCase):
    def test_every_list_added_since_0116_has_an_example_and_a_warning(self):
        text = self.guide()
        for name in NEW_SINCE_0116:
            self.assertIn(name, helper_examples.EXAMPLES)
            self.assertIn(name, self.writable())
            entry, warning = helper_examples.EXAMPLES[name]
            self.assertIn(f"Example: {json.dumps({'table': name, 'values': entry}, ensure_ascii=False)}", text, name)
            self.assertIn(warning, text, name)

    def test_every_example_is_a_real_table_and_is_accepted_by_the_real_checks(self):
        pet = self.store.create("pets__pets", {"name": "Invented Rex", "species": "dog"})
        car = self.store.create("vehicles__vehicles", {"name": "Invented hatchback"})
        service = self.store.create("vehicles__services", {"vehicle": car, "name": "Routine service"})
        routine = self.store.create("routines__routines", {"name": "Invented task"})
        ids = {"pet": pet, "vehicle": car, "service": service, "routine": routine}
        for number, (name, (entry, _)) in enumerate(helper_examples.EXAMPLES.items()):
            self.assertIn(name, self.registry)
            values = {k: ids.get(k, v) if k in ids else v for k, v in entry.items()}
            result = proposals.submit(self.conn, self.registry, self.helper,
                                      {"request_key": f"example-{number}", "why": WHY,
                                       "entries": [{"table": name, "values": values}]})[0]
            self.assertEqual(result["state"], "waiting", name)

    def test_the_examples_name_no_private_field(self):
        for name, (entry, _) in helper_examples.EXAMPLES.items():
            for field in entry:
                self.assertFalse(self.registry[name].table.columns[field].sensitive, (name, field))

    def test_a_look_only_helper_is_not_given_examples_to_send(self):
        text = self.guide(self.reader)
        self.assertNotIn("LISTS WITH THEIR OWN WAYS OF WORKING", text)
        self.assertNotIn("Example:", text)
        self.assertIn("NEVER FOR HELPERS", text)

    def test_a_helper_given_only_part_of_the_records_gets_only_its_examples(self):
        helper, _ = helpers.issue(self.conn, self.data, "Pets helper", "suggest", ["pets"])
        text = self.guide(helper)
        self.assertIn("Example: " + json.dumps({"table": "pets__weigh_ins", "values":
                                                 helper_examples.EXAMPLES["pets__weigh_ins"][0]}), text)
        self.assertNotIn("pet_feeding__servings", text)
        self.assertNotIn("garden__jobs", text)


class WhatToDoInsteadTests(GuideCase):
    def test_the_guide_says_what_is_never_for_helpers_and_what_the_household_does(self):
        text = self.guide()
        for words in ("NEVER FOR HELPERS (the household types these in Dashboard Plus on its own computer)",
                      "Anything about medicines taken or given",
                      "Prices, what was paid, quotes and bill amounts, and money back (refunds)",
                      "refused with private_detail",
                      "the person types the price themselves when they accept",
                      "Answers to the readiness questions",
                      "Calendars, bars and timelines are only ways for a person to look",
                      "You cannot press Mark done"):
            self.assertIn(words, text)
        self.assertNotIn("Medicine doses", text)
        # a later decision describes the person-only spreadsheet import; these new words do not
        self.assertNotIn("spreadsheet", " ".join(helper_guide._never_lines()).lower())

    def test_units_and_the_household_day_are_explained(self):
        text = self.guide()
        for words in ("A day means the household's own calendar day",
                      "no offset is the household's own local time",
                      "an exact moment, counted on the household day it falls in",
                      "Never convert between units",
                      "Review does not question a reading that is lower than the last"):
            self.assertIn(words, text)

    def test_the_move_in_guards_are_still_there(self):
        text = self.guide()
        for words in ("Its warnings (such as may_count_twice) need the person's attention",
                      "Do not also send a", "ask the household which one",
                      "A tracker count is not a purchase",
                      "Match by the full path and details"):
            self.assertIn(words, text)

    def test_nothing_in_the_guide_is_the_old_wording(self):
        text = self.guide()
        self.assertNotIn("TODO", text)
        self.assertNotIn("Private details are never shared.\n", text)


class SameWordsElsewhereTests(GuideCase):
    def test_the_connector_tells_an_assistant_the_same_things(self):
        guide = tools.BY_NAME["dashboard_how_to_help"].description
        suggest = tools.BY_NAME["dashboard_suggest_new_records"].description
        for words in ("weigh-ins", "feedings", "odometer", "routine", "Garden"):
            self.assertIn(words, guide)
        for words in ("never for helpers", "private_detail", "household's own", "never convert"):
            self.assertIn(words, suggest)
        for tool in tools.TOOLS:
            self.assertNotIn("spreadsheet", tool.description.lower())

    def test_the_published_description_says_it_too(self):
        guide = OPENAPI["paths"]["/api/v1/guide"]["get"]["description"]
        propose = OPENAPI["paths"]["/api/v1/proposals"]["post"]["description"]
        for words in ("weigh-ins", "feedings", "odometer readings", "Done or skipped", "Garden jobs",
                      "never for helpers", "household's own"):
            self.assertIn(words, guide)
        for words in ("private_detail", "money back", "medicines", "household's own calendar day",
                      "Never convert"):
            self.assertIn(words, propose)
