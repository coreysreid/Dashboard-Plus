"""Tests for Readiness: "Have you thought about…?" questions, what fits, record matches, answers and coming back.

These follow the 12 checks in Lane B's draft (its ACCEPTANCE.md, now in git history) that a computer can run,
plus switching the module off and on, the example households, privacy, the sync change log, export and restore
(decision 0104). Reading the screens at 320 pixels is checked in the browser check and screenshots."""
import io
import json
import re
import shutil
import tomllib
import zipfile
from datetime import date, datetime, timedelta, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import backups, db, export, helpers, modules, questions, records, restore, settings
from dashboard.core import startup
from dashboard.core.csv_import import why_not_table
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
from dashboard.web.questions import REVIEW_WORDS
import load_example

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date(2026, 11, 21)
MODULES = ("people", "stock", "home_layout", "medical", "pets", "readiness")
SECRET = "Synthetic-medicine-name 40mg nightly"
# The draft's exact mapping (NOTES.md, rechecked 2026-11-18): eight prompts with a field, 41 with none.
MAPPING = {"fire-alarm-location": "home_layout.equipment.last_tested",
           "flood-flood-utilities": "home_layout.shutoffs.place", "heat-heat-water": "stock.lots.place",
           "medical-kit-location": "medical.kits.place", "medical-prescriptions": "people.important_info.detail",
           "medical-care-contact": "people.roles.person", "medical-special-food": "people.important_info.detail",
           "leaving-contact-away": "people.roles.person"}
HAZARD_PROMPTS = 21  # seven each for flood, storm and heat


class ReadinessTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.today = TODAY
        settings.put(self.conn, "setup.done", True)
        self.everything_applies()

    @property
    def registry(self):
        on = settings.enabled_modules(self.conn)
        return records.build_registry([m for m in self.report.loaded if m.name in on])

    @property
    def store(self):
        return records.Records(self.conn, self.registry)

    @property
    def prompt_set(self):
        return questions.prompt_sets(self.registry)["readiness"]

    def everything_applies(self):
        settings.put(self.conn, "household.storeys", 2)
        settings.put(self.conn, "household.hazards", ["flood", "storm", "heat"])
        settings.put(self.conn, "household.mobility_needs", True)
        settings.put(self.conn, "household.country", "Australia")
        self.pet = self.store.create("pets__pets", {"name": "Biscuit", "species": "dog"})

    def client(self):
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["TODAY"] = lambda: self.today
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None):
        return (client or self.client()).get(path, base_url=BASE).get_data(as_text=True)

    def post(self, client, path, **form):
        return client.post(path, base_url=BASE, data={"_csrf": client.csrf, **form})

    def state(self, prompt_id):
        found = questions.evaluate(self.conn, self.registry, self.prompt_set, self.today)
        return next(q for q in found if q.prompt.id == prompt_id)

    def coverage(self):
        return questions.coverage(questions.evaluate(self.conn, self.registry, self.prompt_set, self.today),
                                  self.prompt_set)

    def answers(self):
        return self.conn.execute("SELECT * FROM readiness__answers WHERE deleted_at IS NULL").fetchall()

    def place(self, name, inside=None):
        return self.store.create("stock__places", {"name": name, "inside": inside})

    def person(self, name, lives_here=True, phone=None):
        return self.store.create("people__people", {"name": name, "lives_here": lives_here, "phone": phone})


class PromptFileTests(ReadinessTestCase):
    def test_module_loads_alone_with_49_sourced_questions_in_seven_groups(self):
        self.assertEqual(self.report.module_problems, {})
        module = modules.load_module(ROOT / "modules" / "readiness")
        self.assertEqual((module.requires, module.outbound_hosts), ([], []))
        prompts = module.prompts.prompts
        self.assertEqual(len(prompts), 49)
        self.assertEqual([k for k, _ in module.prompts.groups],
                         ["fire", "flood", "storm", "heat", "power", "medical", "leaving"])
        for key, _ in module.prompts.groups:
            self.assertEqual(sum(1 for p in prompts if p.group == key), 7, key)
        for p in prompts:
            self.assertTrue(p.source["url"].startswith("https://"), p.id)
            self.assertEqual(p.source["checked"], "2026-11-16", p.id)
            self.assertTrue(p.source["title"], p.id)
            self.assertEqual(p.review_every, 12, p.id)
            self.assertTrue(p.question.endswith("?"), p.id)

    def test_answered_by_is_exactly_the_draft_mapping_and_none_never_has_a_match(self):
        prompts = modules.load_module(ROOT / "modules" / "readiness").prompts.prompts
        self.assertEqual({p.id: p.answered_by for p in prompts if p.answered_by != "none"}, MAPPING)
        self.assertEqual(sum(1 for p in prompts if p.answered_by == "none"), 41)
        self.assertTrue(all(p.match is None for p in prompts if p.answered_by == "none"))

    def test_question_wording_matches_lane_b_draft_word_for_word(self):
        draft_ids = ["fire-two-ways", "fire-upper-floor", "medical-prescriptions", "leaving-local-plan"]
        prompts = {p.id: p for p in modules.load_module(ROOT / "modules" / "readiness").prompts.prompts}
        self.assertEqual(prompts["fire-upper-floor"].question,
                         "If the stairs were blocked, have you thought about how everyone upstairs would leave?")
        self.assertTrue(all(i in prompts for i in draft_ids))

    def test_migration_matches_and_touches_only_its_own_table(self):
        module = modules.load_module(ROOT / "modules" / "readiness")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "readiness" / "migrations" / "0001_first_tables.sql").read_text(encoding="utf-8")
        created = re.findall(r"CREATE (?:TABLE|INDEX) (\S+)", sql)
        self.assertTrue(created and all(n.startswith("readiness__") for n in created), created)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")

    def test_no_safety_verdict_or_emergency_instruction_words_in_the_module(self):
        text = " ".join(p.read_text(encoding="utf-8").lower()
                        for p in (ROOT / "modules" / "readiness").glob("*.toml"))
        for word in ("you are safe", "you are prepared", "you are ready", "unsafe", "readiness score", "% ready",
                     "call 000", "call 911", "you must"):
            self.assertNotIn(word, text)

    def write_prompts(self, body, tables=None):
        folder = self.tmp / "bad" / "quiz"
        shutil.rmtree(folder, ignore_errors=True)
        self.write("bad/quiz/module.toml", 'name = "quiz"\ntitle = "Quiz"\nversion = "1.0.0"\ndescription = "x"\n'
                                           'core_api = "1"\nkind = "declarative"\n')
        self.write("bad/quiz/tables.toml", tables or (ROOT / "modules/readiness/tables.toml").read_text("utf-8"))
        self.write("bad/quiz/prompts.toml", body)
        return folder

    def problems(self, body, tables=None):
        try:
            modules.load_module(self.write_prompts(body, tables))
        except modules.ModuleError as error:
            return " ".join(error.problems)
        return ""

    GOOD = ('schema = 1\nanswers = "answers"\n[[group]]\nkey = "g"\ntitle = "G"\n[[prompt]]\nid = "one"\n'
            'group = "g"\nquestion = "Have you?"\nwhy = "Because."\nfits = {}\nanswered_by = "none"\n'
            'review_every = 12\nsource = { title = "Body", url = "https://example.org/", checked = "2026-11-16" }\n')

    def test_prompt_files_are_checked_and_mistakes_explained(self):
        self.assertEqual(self.problems(self.GOOD), "")
        self.assertIn("unknown setting 'region'", self.problems(self.GOOD.replace("fits = {}", 'fits = {region = ["x"]}')))
        self.assertIn("so 'match' must say", self.problems(self.GOOD.replace('"none"', '"quiz.answers.note"')))
        self.assertIn("cannot have a match", self.problems(
            self.GOOD + 'match = { table = "answers", filled = ["note"] }\n'))
        self.assertIn("https://", self.problems(self.GOOD.replace("https://example.org/", "http://example.org/")))
        self.assertIn("source.checked", self.problems(self.GOOD.replace("2026-11-16", "16/11/26")))
        self.assertIn("'schema' must be 1, 2 or 3", self.problems(self.GOOD.replace("schema = 1", "schema = 4")))
        self.assertEqual(self.problems(self.GOOD.replace("schema = 1", "schema = 2")), "")
        self.assertIn("Drills need schema = 2", self.problems(self.GOOD.replace(
            'answers = "answers"', 'answers = "answers"\nruns = "drill_runs"')))
        self.assertIn("another prompt already has this id", self.problems(
            self.GOOD + self.GOOD.split("[[prompt]]")[1].join(["[[prompt]]", ""])))
        loose = (ROOT / "modules/readiness/tables.toml").read_text("utf-8").replace("suggestions = false\n", "")
        self.assertIn("suggestions = false", self.problems(self.GOOD, loose))

    def test_a_match_into_a_missing_column_fails_to_load_and_into_a_missing_module_finds_nothing(self):
        body = self.GOOD.replace('"none"', '"stock.items.colour"') + \
            'match = { table = "stock.items", filled = ["colour"] }\n'
        folder = self.write_prompts(body)
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "bad" / "stock")
        _, failures = modules.discover(self.tmp / "bad")
        self.assertIn("'colour' is not a field", " ".join(failures.get("quiz", [])))
        shutil.rmtree(self.tmp / "bad" / "stock")
        found, failures = modules.discover(folder.parent)
        self.assertEqual(failures, {})
        self.assertEqual([m.name for m in found], ["quiz"])


class ReadinessScreenTests(ReadinessTestCase):
    def test_1_home_shows_at_most_two_calm_cards_and_not_now_records_nothing(self):
        client = self.client()
        home = self.page("/", client)
        cards = re.findall(r'class="asked-one"', home)
        self.assertEqual(len(cards), 2)
        first, second = self.prompt_set.prompts[0], self.prompt_set.prompts[1]
        for p in (first, second):
            self.assertIn(p.question.replace("'", "&#39;"), home)
            self.assertIn(p.why, home)
        self.assertIn("Look at this", home)
        self.assertIn("Not now", home)
        for word in ("unsafe", "warning", "urgent"):
            self.assertNotIn(word, home.lower())
        before = self.coverage()
        reply = self.post(client, f"/questions/readiness/{first.id}/not-now", back="/")
        self.assertEqual(reply.status_code, 302)
        self.assertEqual(self.answers(), [])
        self.assertEqual(self.coverage(), before)
        home = self.page("/", client)
        self.assertNotIn(first.question.replace("'", "&#39;"), home)
        self.assertIn(self.prompt_set.prompts[2].question.replace("'", "&#39;"), home)
        self.assertEqual(len(re.findall(r'class="asked-one"', home)), 2)
        self.today = TODAY + timedelta(days=8)  # set aside for a week, then it may come back
        self.assertIn(first.question.replace("'", "&#39;"), self.page("/", client))

    def test_2_four_actions_and_tell_me_more_saves_nothing(self):
        client = self.client()
        page = self.page("/questions/readiness/fire-upper-floor", client)
        for label in ('value="yes">Yes<', 'value="not_relevant" class="quiet">Not relevant<',
                      'value="not_yet" class="quiet">Not yet<', "Tell me more"):
            self.assertIn(label, page)
        for words in ("We have thought about this.", "This does not fit our household.", "Remind us later."):
            self.assertIn(words, page)
        more = page.split("<summary><strong>Tell me more</strong></summary>")[1].split("</details>")[0]
        self.assertIn("https://www.usfa.fema.gov/prevention/home-fires/prepare-for-fire/home-fire-escape-plans/", more)
        self.assertIn("checked 16/11/26", more)
        self.assertIn("Upper floors need a route", more)
        self.assertEqual(self.answers(), [])
        for answer in ("yes", "not_relevant", "not_yet"):
            reply = self.post(client, "/questions/readiness/fire-upper-floor", answer=answer)
            self.assertEqual(reply.status_code, 302)
            row = self.answers()[0]
            self.assertEqual((row["answer"], row["answered_on"]), (answer, TODAY.isoformat()))
            self.assertIn("Saved your answer. You can change it later.",
                          self.page("/questions/readiness/fire-upper-floor?saved=1", client))
        self.assertEqual(len(self.answers()), 1)  # one record per question; history keeps the earlier ones
        history = self.store.history("readiness__answers", self.answers()[0]["id"])
        self.assertEqual([h["action"] for h in history], ["create", "update", "update"])
        self.assertIn("Earlier answers", self.page("/questions/readiness/fire-upper-floor", client))

    def test_3_applicability_comes_from_settings_and_is_not_a_not_relevant_answer(self):
        self.assertTrue(self.state("fire-upper-floor").fits)
        settings.put(self.conn, "household.storeys", 1)
        q = self.state("fire-upper-floor")
        self.assertEqual(q.state, "does_not_fit")
        self.assertIn("1 storey", " ".join(q.not_fit_reasons))
        settings.put(self.conn, "household.storeys", None)
        self.assertTrue(self.state("fire-upper-floor").fits)  # storeys not given: still asked
        settings.put(self.conn, "household.hazards", ["storm"])
        self.assertEqual(self.state("flood-higher-ground").state, "does_not_fit")
        self.assertTrue(self.state("storm-storm-alerts").fits)
        settings.put(self.conn, "household.hazards", [])
        settings.put(self.conn, "household.country", "")
        self.assertEqual(self.state("storm-storm-alerts").state, "does_not_fit")  # never guessed from country
        self.assertEqual(self.answers(), [])
        listing = self.page("/questions/readiness?show=does_not_fit")
        self.assertIn("Does not fit your settings", listing)
        self.assertNotIn("Not relevant,", listing)

    def test_4_count_says_looked_at_and_never_safe(self):
        plain = [p for p in self.prompt_set.prompts if "hazards" not in p.fits]
        self.assertEqual(len(plain), 28)
        for p in plain[:20]:
            questions.save(self.store, self.prompt_set, p.id, "yes", today=TODAY)
        for p in plain[20:22]:
            questions.save(self.store, self.prompt_set, p.id, "not_relevant", today=TODAY)
        questions.save(self.store, self.prompt_set, plain[22].id, "not_yet", review_on="2027-01-10", today=TODAY)
        client = self.client()
        page = self.page("/questions/readiness", client)
        self.assertIn("23 of 49 questions looked at.", page)
        self.page(f"/questions/readiness/{plain[23].id}", client)  # opening one, or Tell me more, is not an answer
        self.assertIn("23 of 49 questions looked at.", self.page("/questions/readiness", client))
        self.assertIn("Looked at means someone answered a question. It does not say whether your household is safe "
                      "or ready.", page)
        settings.put(self.conn, "household.hazards", ["heat"])
        page = self.page("/questions/readiness", client)
        self.assertIn("23 of 35 questions that fit your household looked at.", page)
        self.assertIn("14 do not fit the settings you gave.", page)
        text = re.sub(r"<[^>]+>", " ", page).lower()
        for word in ("prepared", "% ", "pass", "score", "you are safe"):
            self.assertNotIn(word, text)
        self.assertEqual(text.count("safe"), text.count("is safe or ready") +
                         sum(p.question.lower().count("safe") for p in self.prompt_set.prompts))

    def test_5_the_upstairs_question_has_no_invented_match_and_offers_ways_out_to_write_a_plan(self):
        upstairs = self.place("Upstairs hall")
        self.store.create("home_layout__exits", {"name": "Upstairs window", "floor": "Upstairs", "place": upstairs,
                                                 "route": "Through the window onto the porch roof"})
        q = self.state("fire-upper-floor")
        self.assertEqual(q.candidates, [])
        page = self.page("/questions/readiness/fire-upper-floor")
        self.assertNotIn("You already recorded this", page)
        self.assertIn('href="/t/home_layout__exits/new">Write down a way out', page)
        self.assertIn("it does not answer this question", page)
        self.assertEqual(q.state, "to_look_at")

    def test_6_and_8_each_record_match_needs_exactly_its_conditions(self):
        kitchen = self.place("Kitchen")
        shelf = self.place("Shelf 3", inside=kitchen)
        for p in self.prompt_set.prompts:
            self.assertEqual(self.state(p.id).candidates, [], p.id)
        # Torches: a power-category item never answers the light question (answered_by none).
        self.store.create("stock__items", {"name": "Batteries", "category": "power", "quantity": 4, "unit": "packs",
                                           "place": shelf})
        self.assertEqual(self.state("power-light").candidates, [])
        # Smoke alarms need the smoke alarm kind, a place and a last tested date.
        self.store.create("home_layout__equipment", {"name": "Hall CO alarm", "kind": "co_alarm", "place": kitchen,
                                                     "last_tested": "2026-10-01"})
        untested = self.store.create("home_layout__equipment", {"name": "Hall alarm", "kind": "smoke_alarm",
                                                                "place": kitchen})
        self.assertEqual(self.state("fire-alarm-location").candidates, [])
        self.store.update("home_layout__equipment", untested, {"last_tested": "2026-10-01"})
        self.assertEqual(len(self.state("fire-alarm-location").candidates), 1)
        # Shut-offs: water, power or gas with a place.
        self.store.create("home_layout__shutoffs", {"name": "Odd tap", "kind": "other", "place": kitchen})
        self.store.create("home_layout__shutoffs", {"name": "Main water", "kind": "water"})
        self.assertEqual(self.state("flood-flood-utilities").candidates, [])
        self.store.create("home_layout__shutoffs", {"name": "Power board", "kind": "power", "place": shelf})
        self.assertEqual(len(self.state("flood-flood-utilities").candidates), 1)
        # Kits need a linked place, and a deleted kit is not offered.
        self.store.create("medical__kits", {"name": "No place kit", "kept": "home"})
        self.assertEqual(self.state("medical-kit-location").candidates, [])
        kit = self.store.create("medical__kits", {"name": "Kitchen kit", "kept": "home", "place": shelf})
        self.assertEqual(len(self.state("medical-kit-location").candidates), 1)
        self.store.delete("medical__kits", kit)
        self.assertEqual(self.state("medical-kit-location").candidates, [])
        # Contacts: the right role, pointing at a person with a phone number.
        doctor = self.person("Dr Example", lives_here=False)
        self.store.create("people__roles", {"person": doctor, "role": "doctor"})
        dentist = self.person("Dentist Example", lives_here=False, phone="0491 570 110")
        self.store.create("people__roles", {"person": dentist, "role": "dentist"})
        self.assertEqual(self.state("medical-care-contact").candidates, [])
        self.store.update("people__people", doctor, {"phone": "0491 570 111"})
        self.assertEqual(len(self.state("medical-care-contact").candidates), 1)
        self.assertEqual(self.state("leaving-contact-away").candidates, [])
        self.store.create("people__roles", {"person": doctor, "role": "emergency_contact"})
        self.assertEqual(len(self.state("leaving-contact-away").candidates), 1)
        # Important details: the right kind, for someone who lives here.
        visitor, resident = self.person("Visitor Example", lives_here=False), self.person("Alex Example")
        self.store.create("people__important_info", {"person": visitor, "kind": "medication", "detail": SECRET})
        self.store.create("people__important_info", {"person": resident, "kind": "allergy", "detail": SECRET})
        self.assertEqual(self.state("medical-prescriptions").candidates, [])
        self.store.create("people__important_info", {"person": resident, "kind": "medication", "detail": SECRET})
        found = self.state("medical-prescriptions").candidates
        self.assertEqual((len(found), found[0].private), (1, True))
        self.assertEqual(self.state("medical-special-food").candidates, [])
        self.store.create("people__important_info", {"person": resident, "kind": "dietary", "detail": "Soft food"})
        self.assertEqual(len(self.state("medical-special-food").candidates), 1)
        # Water: a positive batch in litres of drinking water, at a place.
        for name, drinking, unit in (("Flushing water", False, "litres"), ("Bottled water", True, "bottles")):
            item = self.store.create("stock__items", {"name": name, "category": "water", "drinking": drinking,
                                                      "unit": unit})
            self.store.create("stock__lots", {"item": item, "quantity": 10, "place": shelf})
        cask = self.store.create("stock__items", {"name": "Cask", "category": "water", "drinking": True,
                                                  "unit": "litres"})
        empty = self.store.create("stock__lots", {"item": cask, "quantity": 0, "place": shelf})
        self.store.create("stock__lots", {"item": cask, "quantity": 10})
        self.assertEqual(self.state("heat-heat-water").candidates, [])
        self.store.update("stock__lots", empty, {"quantity": 10})
        found = self.state("heat-heat-water").candidates
        self.assertEqual([c.record_id for c in found], [empty])
        # A single pet's record never answers a question about pets: those questions have no match at all.
        for pid in ("heat-heat-pets", "flood-flood-pets", "storm-storm-pets", "leaving-pets-away"):
            self.assertEqual(self.state(pid).candidates, [], pid)
        # None of it is an answer.
        self.assertEqual(self.answers(), [])
        self.assertTrue(all(self.state(p).state == "to_look_at" for p in MAPPING))

    def test_6b_switching_a_matched_module_off_finds_nothing(self):
        self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        self.assertEqual(len(self.state("medical-kit-location").candidates), 1)
        settings.set_module_enabled(self.conn, "medical", False)
        self.assertEqual(self.state("medical-kit-location").candidates, [])

    def test_7_a_private_detail_is_never_quoted_and_a_person_still_chooses(self):
        resident = self.person("Alex Example")
        self.store.create("people__important_info", {"person": resident, "kind": "medication", "detail": SECRET})
        client = self.client()
        page = self.page("/questions/readiness/medical-prescriptions", client)
        self.assertIn("You have a private record that may relate to this question.", page)
        self.assertIn("You already recorded this. Does it answer the question?", page)
        key = self.state("medical-prescriptions").candidates[0].key
        self.post(client, "/questions/readiness/medical-prescriptions", answer="yes", record=key)
        self.assertEqual(self.answers()[0]["record"], key)
        self.store.update("people__important_info", self.state("medical-prescriptions").candidates[0].record_id,
                          {"detail": SECRET + " (changed)"})
        self.assertEqual(self.state("medical-prescriptions").review_reason, "record_changed")
        for path in ("/", "/attention", "/questions/readiness", "/questions/readiness?show=review",
                     "/questions/readiness/medical-prescriptions", "/sheet/people/emergency",
                     "/t/readiness__answers"):
            text = self.page(path, client)
            self.assertNotIn("Synthetic-medicine-name", text, path)
        self.assertIn(REVIEW_WORDS["record_changed"], self.page("/", client))
        stored = " ".join(str(v) for row in self.answers() for v in tuple(row))
        self.assertNotIn("Synthetic-medicine-name", stored)

    def test_9_not_yet_comes_back_on_its_date_with_the_earlier_answer_kept(self):
        client = self.client()
        reply = self.post(client, "/questions/readiness/fire-meeting-place", answer="not_yet", review_on="10/01/27")
        self.assertEqual(reply.status_code, 302)
        row = self.answers()[0]
        self.assertEqual((row["answered_on"], row["review_on"]), ("2026-11-21", "2027-01-10"))
        self.assertEqual(self.state("fire-meeting-place").state, "looked_at")
        self.assertEqual(self.coverage()["looked_at"], 1)
        self.assertEqual(self.post(client, "/questions/readiness/fire-meeting-place", answer="not_yet",
                                   review_on="31/02/27").status_code, 422)
        self.assertEqual(self.post(client, "/questions/readiness/fire-meeting-place", answer="not_yet",
                                   review_on="01/11/26").status_code, 422)
        self.today = date(2027, 1, 10)
        q = self.state("fire-meeting-place")
        self.assertEqual((q.state, q.review_reason, q.answer["answer"]), ("review", "due", "not_yet"))
        self.assertEqual(self.coverage()["looked_at"], 0)
        home = self.page("/", client)
        self.assertIn(q.prompt.question, home.replace("&#39;", "'"))
        self.assertIn(REVIEW_WORDS["due"], home)
        self.assertIn(">Review again (1)<", self.page("/questions/readiness", client))
        page = self.page("/questions/readiness/fire-meeting-place", client)
        self.assertIn("Your answer: <strong>Not yet</strong>", page)

    def test_9b_yes_comes_back_after_the_twelve_month_interval(self):
        questions.save(self.store, self.prompt_set, "fire-two-ways", "yes", today=TODAY)
        self.assertEqual(self.answers()[0]["review_on"], "2027-11-21")
        self.today = date(2027, 11, 20)
        self.assertEqual(self.state("fire-two-ways").state, "looked_at")
        self.today = date(2027, 11, 21)
        self.assertEqual(self.state("fire-two-ways").state, "review")

    def test_10_a_changed_or_removed_linked_record_asks_again_and_a_new_yes_needs_a_person(self):
        hall, landing = self.place("Hall"), self.place("Landing")
        kit = self.store.create("medical__kits", {"name": "Hall kit", "kept": "home", "place": hall})
        client = self.client()
        key = self.state("medical-kit-location").candidates[0].key
        self.assertTrue(key.startswith("medical__kits:"))
        self.post(client, "/questions/readiness/medical-kit-location", answer="yes", record=key)
        self.assertEqual(self.state("medical-kit-location").state, "looked_at")
        self.store.update("stock__places", hall, {"inside": landing})  # the place moved
        self.assertEqual(self.state("medical-kit-location").review_reason, "record_changed")
        self.post(client, "/questions/readiness/medical-kit-location", answer="yes", record=key)
        self.assertEqual(self.state("medical-kit-location").state, "looked_at")
        self.store.update("medical__kits", kit, {"place": landing})  # the kit moved
        self.assertEqual(self.state("medical-kit-location").review_reason, "record_changed")
        self.post(client, "/questions/readiness/medical-kit-location", answer="yes", record=key)
        self.store.delete("medical__kits", kit)
        q = self.state("medical-kit-location")
        self.assertEqual((q.state, q.answer["answer"]), ("review", "yes"))
        self.assertEqual(q.review_reason, "record_missing")
        home = self.page("/", client)
        self.assertIn(REVIEW_WORDS["record_missing"], home)
        self.assertNotIn("Hall kit", home)
        # The old record can no longer be chosen; a person answers again without it.
        self.assertEqual(self.post(client, "/questions/readiness/medical-kit-location", answer="yes",
                                   record=key).status_code, 422)
        self.post(client, "/questions/readiness/medical-kit-location", answer="yes")
        self.assertEqual((self.state("medical-kit-location").state, self.answers()[0]["record"]), ("looked_at", None))
        self.assertGreaterEqual(len(self.store.history("readiness__answers", self.answers()[0]["id"])), 4)

    def test_10b_a_record_is_kept_only_for_yes_and_only_when_it_is_offered(self):
        kit = self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        key = self.state("medical-kit-location").candidates[0].key
        client = self.client()
        self.assertEqual(self.post(client, "/questions/readiness/medical-kit-location", answer="not_yet",
                                   record=key).status_code, 422)
        self.assertEqual(self.post(client, "/questions/readiness/fire-two-ways", answer="yes",
                                   record=key).status_code, 422)
        self.assertEqual(self.post(client, "/questions/readiness/medical-kit-location", answer="maybe").status_code,
                         422)
        self.assertEqual(self.post(client, "/questions/readiness/no-such-question", answer="yes").status_code, 404)
        self.assertEqual(self.answers(), [])
        self.assertEqual(self.state("medical-kit-location").candidates[0].record_id, kit)

    def test_11_changing_settings_recounts_without_rewriting_answers(self):
        questions.save(self.store, self.prompt_set, "flood-higher-ground", "yes", today=TODAY)
        before = [tuple(r) for r in self.answers()]
        self.assertEqual(self.coverage()["fit"], 49)
        settings.put(self.conn, "household.hazards", ["storm", "heat"])
        self.assertEqual((self.coverage()["fit"], self.coverage()["looked_at"]), (42, 0))
        self.assertEqual(self.state("flood-higher-ground").state, "does_not_fit")
        self.assertEqual([tuple(r) for r in self.answers()], before)
        self.store.delete("pets__pets", self.pet)
        self.assertEqual(self.coverage()["fit"], 39)  # the storm, heat and leaving questions about pets
        settings.put(self.conn, "household.hazards", ["flood", "storm", "heat"])
        self.store.restore("pets__pets", self.pet)
        self.assertEqual((self.coverage()["fit"], self.coverage()["looked_at"]), (49, 1))
        self.assertEqual([tuple(r) for r in self.answers()], before)

    def test_12_source_dates_and_answer_dates_stay_separate(self):
        client = self.client()
        self.post(client, "/questions/readiness/storm-storm-alerts", answer="yes")
        page = self.page("/questions/readiness/storm-storm-alerts", client)
        self.assertIn("https://getready.govt.nz/emergency/storms", page)
        self.assertIn("checked 16/11/26", page)
        self.assertIn("on 21/11/26", page)
        for p in self.prompt_set.prompts:
            self.assertIn(p.source["url"], self.page(f"/questions/readiness/{p.id}", client), p.id)
        self.today = date(2029, 1, 1)  # sources long past any editorial review: no household due date appears
        q = self.state("fire-two-ways")
        self.assertEqual((q.state, q.due_on), ("to_look_at", None))
        self.assertNotIn("warning", self.page("/questions/readiness/fire-two-ways", client).lower())

    def test_module_off_hides_every_screen_and_keeps_answers_and_on_brings_them_back(self):
        questions.save(self.store, self.prompt_set, "fire-two-ways", "yes", today=TODAY)
        client = self.client()
        self.assertIn("Have you thought about…?", self.page("/", client))
        settings.set_module_enabled(self.conn, "readiness", False)
        for path in ("/questions", "/questions/readiness", "/questions/readiness/fire-two-ways"):
            self.assertEqual(client.get(path, base_url=BASE).status_code, 404, path)
        self.assertEqual(self.post(client, "/questions/readiness/fire-two-ways", answer="no").status_code, 404)
        self.assertNotIn("Have you thought about…?", self.page("/", client))
        self.assertNotIn("Have you thought about", self.page("/attention", client))
        self.assertEqual(len(self.answers()), 1)
        settings.set_module_enabled(self.conn, "readiness", True)
        self.assertEqual(self.state("fire-two-ways").state, "looked_at")
        self.assertIn("1 of 49 questions looked at.", self.page("/questions/readiness", client))

    def test_needs_attention_shows_a_few_questions_gently(self):
        page = self.page("/attention")
        section = page.split("<h2>Have you thought about…?</h2>")[1]
        self.assertEqual(section.count("/questions/readiness/"), 3)
        self.assertIn("A few questions to think about when you have time.", section)
        self.assertNotRegex(section, r"\b4[0-9]\b")  # never the number left unanswered
        for word in ("overdue", "unsafe", "failed", "missing"):
            self.assertNotIn(word, section.lower())

    def test_home_card_for_the_module_links_the_questions(self):
        self.assertIn('href="/questions/readiness">Have you thought about…?</a>', self.page("/"))
        self.assertEqual(self.client().get("/questions", base_url=BASE).headers["Location"], "/questions/readiness")


class ReadinessDataTests(ReadinessTestCase):
    def test_answers_are_in_the_sync_change_log_with_every_field(self):
        questions.save(self.store, self.prompt_set, "fire-two-ways", "not_yet", review_on="2027-01-01",
                       note="Talk it through on Sunday", today=TODAY)
        row = self.answers()[0]
        line = self.conn.execute("SELECT * FROM core__sync_changes WHERE table_name = 'readiness__answers'"
                                 ).fetchone()
        self.assertEqual(line["global_id"], row["global_id"])
        patch = json.loads(line["patch"])
        self.assertEqual((patch["prompt"], patch["answer"], patch["note"]),
                         ("fire-two-ways", "not_yet", "Talk it through on Sunday"))
        self.assertEqual(json.loads(line["withheld"] or "[]"), [])
        module = modules.load_module(ROOT / "modules" / "readiness")
        self.assertTrue(all(c.travels == "always" and not c.sensitive
                            for c in module.tables["answers"].columns.values()))

    def test_export_has_the_answers(self):
        questions.save(self.store, self.prompt_set, "fire-two-ways", "yes", note="Done in October", today=TODAY)
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 21, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            answers = archive.read("readiness__answers.csv").decode("utf-8-sig")
        self.assertIn("fire-two-ways", answers)
        self.assertIn("Done in October", answers)

    def test_helpers_may_look_at_answers_but_never_suggest_one_and_import_refuses_them(self):
        questions.save(self.store, self.prompt_set, "fire-two-ways", "yes", today=TODAY)
        _, key = helpers.issue(self.conn, self.data, "Planner", "suggest", ["readiness"])
        _, other = helpers.issue(self.conn, self.data, "Stock only", "read", ["stock"])
        client = self.client()
        auth = {"Authorization": f"Bearer {key}"}
        listing = client.get("/api/v1/tables/readiness__answers/records", base_url=BASE, headers=auth)
        self.assertEqual(listing.status_code, 200)
        self.assertIn("fire-two-ways", listing.get_data(as_text=True))
        spec = next(t for t in client.get("/api/v1/tables", base_url=BASE, headers=auth).get_json()["tables"]
                    if t["table"] == "readiness__answers")
        self.assertFalse(spec["can_suggest"])
        reply = client.post("/api/v1/proposals", base_url=BASE, headers=auth, json={
            "request_key": "answer-1", "why": "Thought it through",
            "entries": [{"table": "readiness__answers", "values": {"prompt": "fire-meeting-place", "answer": "yes",
                                                                  "answered_on": "2026-11-21"}}]})
        self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)
        self.assertEqual(client.get("/api/v1/tables/readiness__answers/records", base_url=BASE,
                                    headers={"Authorization": f"Bearer {other}"}).status_code, 404)
        self.assertIn("can't be imported", why_not_table(self.registry["readiness__answers"]))

    def test_examples_load_their_answers_and_list_readiness_once(self):
        expected = {"smith": {"fire-upper-floor": "not_yet", "heat-heat-pets": "not_yet",
                              "leaving-contact-away": "yes"},
                    "garcia": {"power-medical-power": "not_yet", "leaving-go-bags": "not_yet"},
                    "taylor": {"storm-storm-alerts": "not_yet", "leaving-contact-away": "not_yet"}}
        ids = {p.id for p in self.prompt_set.prompts}
        for household, answers in expected.items():
            text = (ROOT / "examples" / "households" / f"{household}.toml").read_text(encoding="utf-8")
            setup = tomllib.loads(text)["setup"]
            self.assertEqual(setup["modules"].count("readiness"), 1, household)
            self.assertEqual(len(setup["modules"]), len(set(setup["modules"])), household)
            self.assertEqual(text.count("# ---- Readiness"), 1, household)
            data = self.tmp / household
            load_example.load(household, data, today=TODAY)
            conn = db.connect(data / "dashboard.db")
            self.addCleanup(conn.close)
            rows = conn.execute("SELECT prompt, answer, answered_on, review_on FROM readiness__answers").fetchall()
            self.assertEqual({r["prompt"]: r["answer"] for r in rows}, answers, household)
            self.assertTrue(all(r["prompt"] in ids for r in rows))
            self.assertTrue(all(r["review_on"] for r in rows if r["answer"] == "not_yet"))

    def test_examples_fit_as_the_draft_says(self):
        found = {}
        for household in ("smith", "taylor"):
            data = self.tmp / household
            load_example.load(household, data, today=TODAY)
            report = startup.prepare(data)
            conn = db.connect(data / "dashboard.db")
            self.addCleanup(conn.close)
            registry = records.build_registry(report.loaded)
            prompt_set = questions.prompt_sets(registry)["readiness"]
            found[household] = {q.prompt.id: q for q in questions.evaluate(conn, registry, prompt_set, TODAY)}
        self.assertTrue(found["smith"]["fire-upper-floor"].fits)       # two storeys
        self.assertFalse(found["taylor"]["fire-upper-floor"].fits)     # one storey
        self.assertEqual(found["smith"]["fire-upper-floor"].candidates, [])
        self.assertTrue(found["taylor"]["flood-higher-ground"].fits)   # Taylor ticked flood
        self.assertFalse(found["smith"]["flood-higher-ground"].fits)
        self.assertEqual(found["smith"]["leaving-contact-away"].state, "looked_at")

    def test_restore_brings_back_the_answers_of_the_chosen_backup(self):
        data = self.tmp / "smith"
        load_example.load("smith", data, today=date(2026, 6, 1))
        report = startup.prepare(data)
        backups.daily(data, today=date(2026, 6, 1))
        conn = db.connect(data / "dashboard.db")
        registry = records.build_registry(report.loaded)
        store = records.Records(conn, registry)
        prompt_set = questions.prompt_sets(registry)["readiness"]
        questions.save(store, prompt_set, "fire-two-ways", "yes", today=date(2026, 6, 2))
        conn.close()

        def prompts():
            c = db.connect(data / "dashboard.db")
            try:
                return sorted(r[0] for r in c.execute("SELECT prompt FROM readiness__answers WHERE deleted_at IS NULL"))
            finally:
                c.close()

        self.assertIn("fire-two-ways", prompts())
        chosen = restore.get({"data": data / "backups"}, "data", "daily-2026-06-01.db")
        restore.restore(data, chosen, report.loaded)
        self.assertEqual(prompts(), ["fire-upper-floor", "heat-heat-pets", "leaving-contact-away"])
        restore.undo(data, report.loaded)
        self.assertIn("fire-two-ways", prompts())
