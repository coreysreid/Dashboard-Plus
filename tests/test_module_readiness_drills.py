"""Tests for "Think it through" drills: the eight situations, their records, sources, practice runs and privacy.

These automate the twelve checks in Lane B's draft (workbench/drafts/think_it_through/ACCEPTANCE.md, now in
git history), plus a person's own words never leaving this computer (export, helpers, the sync change log and
snapshot, sheets, Home), the exact missing-record sentences, a shared question counting on the Questions page,
switching the module off and on, and the three example households (decision 0108)."""
import io
import json
import re
import shutil
import zipfile
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import db, drills, export, helpers, modules, questions, records, settings, startup, sync
from dashboard.core.csv_import import why_not_table
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
from dashboard.web.drills import CHANGED_WORDS
from dashboard.web.sheets import available_sheets
import load_example

PORT = 5143
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date(2026, 11, 21)
MODULES = ("people", "stock", "home_layout", "medical", "pets", "vehicles", "readiness")
WORDS = "Synthetic-plan: hide-key under the blue pot, back door tag 4417"  # never a real code (0141, 0143)
CODE = "Synthetic access code 9931"
SCENARIOS = ["pipe-in-wall", "bedroom-fire-night", "kitchen-fire", "break-in-night", "car-breakdown",
             "power-72-hours", "water-warning", "cyclone-forecast"]
CLAIMS = ("you are safe", "you are prepared", "you are ready", "household is safe", "home is safe now",
          "two safe ways", "route is safe", "confirmed safe", "readiness score", "% ready", "you must")


class DrillTestCase(TempDirTestCase):
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
        settings.put(self.conn, "household.country", "Australia")
        settings.put(self.conn, "household.home_type", "house")
        settings.put(self.conn, "household.hazards", ["storm"])

    @property
    def registry(self):
        on = settings.enabled_modules(self.conn)
        return records.build_registry([m for m in self.report.loaded if m.name in on])

    @property
    def store(self):
        return records.Records(self.conn, self.registry)

    @property
    def prompt_set(self):
        return drills.drill_sets(self.registry)["readiness"]

    def client(self):
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["TODAY"] = lambda: self.today
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None, status=200):
        reply = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(reply.status_code, status, path)
        return reply.get_data(as_text=True)

    def post(self, client, path, **form):
        return client.post(path, base_url=BASE, data={"_csrf": client.csrf, **form})

    def place(self, name, inside=None):
        return self.store.create("stock__places", {"name": name, "inside": inside})

    def person(self, name, lives_here=True, phone=None):
        return self.store.create("people__people", {"name": name, "lives_here": lives_here, "phone": phone})

    def steps(self, scenario_id):
        home = questions.profile(self.conn, self.registry)
        return [s.id for s in drills.fitting_steps(self.prompt_set, self.prompt_set.scenario(scenario_id), home)]

    def start(self, client, scenario_id):
        reply = self.post(client, f"/drills/readiness/{scenario_id}/start")
        self.assertEqual(reply.status_code, 302)
        return int(re.search(r"/runs/(\d+)", reply.headers["Location"]).group(1))

    def step_path(self, scenario_id, run_id, number):
        return f"/drills/readiness/{scenario_id}/runs/{run_id}/{number}"

    def step_page(self, client, scenario_id, step_id):
        run_id = self.start(client, scenario_id)
        number = self.steps(scenario_id).index(step_id) + 1
        return run_id, number, self.page(self.step_path(scenario_id, run_id, number), client)

    def practise(self, client, scenario_id, choice="plan", words=None, records_by_step=None, finish=True,
                 practised_on="21/11/26", review_on=None):
        run_id = self.start(client, scenario_id)
        for number, step_id in enumerate(self.steps(scenario_id), 1):
            form = {"choice": choice, "action": "next", "own_words": words or "",
                    "record": (records_by_step or {}).get(step_id, "")}
            self.assertEqual(self.post(client, self.step_path(scenario_id, run_id, number), **form).status_code, 302)
        if finish:
            form = {"practised_on": practised_on}
            if review_on:
                form["review_on"] = review_on
            self.assertEqual(self.post(client, f"/drills/readiness/{scenario_id}/runs/{run_id}/finish",
                                       **form).status_code, 302)
        return run_id

    def runs(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM readiness__drill_runs WHERE deleted_at IS NULL "
                                                   "ORDER BY id")]

    def step_rows(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM readiness__drill_steps WHERE deleted_at IS NULL "
                                                   "ORDER BY id")]


class DrillFileTests(DrillTestCase):
    def test_1_eight_drills_with_ids_versions_ordered_steps_sources_and_exact_selectors(self):
        self.assertEqual(self.report.module_problems, {})
        prompts = modules.load_module(ROOT / "modules" / "readiness").prompts
        self.assertEqual([s.id for s in prompts.scenarios], SCENARIOS)
        self.assertEqual(len(prompts.prompts), 49)  # the questions page is unchanged
        for scenario in prompts.scenarios:
            self.assertEqual(scenario.version, 1, scenario.id)
            self.assertGreaterEqual(len(scenario.steps), 4, scenario.id)
            self.assertTrue(scenario.sources, scenario.id)
            for source in scenario.sources:
                self.assertTrue(source["url"].startswith("https://"), scenario.id)
                self.assertEqual(source["checked"], "2026-11-21", scenario.id)
                self.assertFalse(source["broken"])
            for step_id in scenario.steps:
                step = prompts.step(step_id)
                self.assertIsNotNone(step, step_id)
                self.assertTrue(step.question.endswith("?"), step_id)
                self.assertTrue(step.missing, step_id)  # every step says exactly what is not recorded
                self.assertEqual(step.match is None, step.answered_by == "none", step_id)
        self.assertEqual(set(prompts.emergency), {"Australia", "United States", "United Kingdom"})
        self.assertEqual({c: e["number"] for c, e in prompts.emergency.items()},
                         {"Australia": "000", "United States": "911", "United Kingdom": "999"})
        shared = {s for sc in prompts.scenarios for s in sc.steps if prompts.is_shared(s)}
        self.assertEqual(shared, {"fire-alarm-location", "fire-meeting-place", "power-food-outage",
                                  "power-power-updates", "storm-storm-alerts"})

    def test_1b_a_record_is_an_offer_and_no_answer_is_chosen_for_the_person(self):
        self.store.create("home_layout__shutoffs", {"name": "Mains tap", "kind": "water", "place": self.place("Yard")})
        _, _, page = self.step_page(self.client(), "pipe-in-wall", "pipe-shutoff")
        self.assertIn("A record is something to look at, not an answer.", page)
        self.assertIn("Mains tap", page)
        self.assertNotRegex(page, r'name="choice" value="\w+" required checked')
        self.assertEqual(self.step_rows(), [])

    def test_the_drill_file_is_checked(self):
        base = (ROOT / "modules/readiness/prompts.toml").read_text("utf-8")
        tables = (ROOT / "modules/readiness/tables.toml").read_text("utf-8")

        def problems(body, table_text=tables):
            folder = self.tmp / "bad" / "quiz"
            shutil.rmtree(folder, ignore_errors=True)
            self.write("bad/quiz/module.toml", 'name = "quiz"\ntitle = "Quiz"\nversion = "1.0.0"\n'
                                               'description = "x"\ncore_api = "1"\nkind = "declarative"\n')
            self.write("bad/quiz/tables.toml", table_text)
            self.write("bad/quiz/prompts.toml", body)
            try:
                modules.load_module(folder)
            except modules.ModuleError as error:
                return " ".join(error.problems)
            return ""

        self.assertEqual(problems(base), "")
        self.assertIn("step 'no-such-step' is not", problems(base.replace(
            'steps = ["pipe-notice",', 'steps = ["no-such-step", "pipe-notice",')))
        self.assertIn("a step is listed twice", problems(base.replace(
            '"pipe-notice", "pipe-shutoff"', '"pipe-notice", "pipe-notice"')))
        self.assertIn("'missing' must say", problems(base.replace(
            'missing = "No leak-check plan is recorded. Think about how you would notice and whom you would ask."\n',
            "")))
        self.assertIn("own_words", problems(base, tables.replace(
            'columns.own_words = { type = "longtext", sensitive = true, travels = "never" }',
            'columns.own_words = { type = "longtext" }')))
        self.assertIn("Drills need schema = 2", problems(base.replace("schema = 3", "schema = 1")))
        self.assertIn("has_records must be a table", problems(base.replace(
            'has_records = "vehicles.vehicles"', 'has_records = "vehicles"')))

    def test_migration_adds_only_the_two_run_tables(self):
        module = modules.load_module(ROOT / "modules" / "readiness")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules/readiness/migrations/0002_drill_runs.sql").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"CREATE TABLE (\S+)", sql), ["readiness__drill_runs", "readiness__drill_steps"])
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")
        words = module.tables["drill_steps"].columns["own_words"]
        self.assertEqual((words.sensitive, words.travels), (True, "never"))
        self.assertFalse(module.tables["drill_runs"].suggestions or module.tables["drill_steps"].suggestions)

    def test_no_safety_verdict_or_instruction_words_in_any_drill(self):
        text = " ".join(line for line in (ROOT / "modules/readiness/prompts.toml").read_text("utf-8").lower()
                        .splitlines() if not line.startswith("#"))  # the comments say what is never claimed
        for word in CLAIMS + ("call 000", "call 911", "call 999", "boil your water", "boil water for",
                              "run a generator", "use a generator", "safe for 72 hours", "evacuate now"):
            self.assertNotIn(word, text)


class DrillCheckTests(DrillTestCase):
    def test_2_missing_shut_off_then_a_nested_place_with_access_details_behind_show(self):
        client = self.client()
        run_id, number, page = self.step_page(client, "pipe-in-wall", "pipe-shutoff")
        self.assertIn("You haven&#39;t recorded where your water shut-off is.", page)
        self.assertIn('href="/t/home_layout__shutoffs/new?kind=water">Add it now</a>', page)
        house = self.place("Laundry")
        cupboard = self.place("Under-sink cupboard", inside=house)
        tap = self.store.create("home_layout__shutoffs", {"name": "Mains water tap", "kind": "water",
                                                          "place": cupboard})
        self.conn.execute("UPDATE home_layout__shutoffs SET access_details = ? WHERE id = ?", (CODE, tap))
        self.conn.commit()  # a code saved before decision 0141, retired and never read
        page = self.page(self.step_path("pipe-in-wall", run_id, number), client)
        self.assertNotIn("You haven&#39;t recorded where your water shut-off is.", page)
        self.assertIn("Laundry › Under-sink cupboard", page)
        self.assertIn(f'href="/t/home_layout__shutoffs/{tap}"', page)
        self.assertNotIn(CODE, page)
        key = drills.questions.candidates(self.conn, self.registry, self.prompt_set.step("pipe-shutoff"))[0].key
        self.post(client, self.step_path("pipe-in-wall", run_id, number), choice="plan", record=key, action="next")
        row = self.step_rows()[0]
        self.assertEqual(row["record"], key)
        self.assertNotIn(CODE, json.dumps(row))
        self.assertNotIn(CODE, self.page(f"/drills/readiness/pipe-in-wall/runs/{run_id}", client))
        line = [dict(r) for r in self.conn.execute(
            "SELECT * FROM core__sync_changes WHERE table_name = 'readiness__drill_steps'")]
        self.assertNotIn(CODE, json.dumps(line))

    def test_3_fire_drills_in_a_house_and_a_flat_never_certify_a_way_out(self):
        client = self.client()
        self.assertNotIn("fire-building-plan", self.steps("bedroom-fire-night"))
        kitchen = self.place("Kitchen")
        self.store.create("stock__connections", {"place": kitchen, "kind": "outside_door"})
        self.store.create("home_layout__exits", {"name": "Back door", "place": kitchen})
        _, _, ways = self.step_page(client, "kitchen-fire", "kitchen-ways-out")
        self.assertIn("It is not a checked escape route.", ways)
        _, _, other = self.step_page(client, "bedroom-fire-night", "fire-other-way")
        self.assertIn("Back door", other)
        self.assertIn("Dashboard Plus cannot confirm that any route is clear or usable in a fire.", other)
        _, _, meet = self.step_page(client, "bedroom-fire-night", "fire-meeting-place")
        self.assertIn("You haven&#39;t written down an outside meeting place.", meet)
        settings.put(self.conn, "household.home_type", "apartment")
        for scenario in ("bedroom-fire-night", "kitchen-fire"):
            self.assertEqual(self.steps(scenario)[-1], "fire-building-plan")
        _, _, plan = self.step_page(client, "bedroom-fire-night", "fire-building-plan")
        self.assertIn("only your building&#39;s own plan can say which", plan)
        for text in (ways, other, meet, plan):
            for claim in CLAIMS + ("confirmed",):
                self.assertNotIn(claim, text.lower())

    def test_4_break_in_answers_stay_private_and_only_the_checked_number_is_named(self):
        client = self.client()
        self.practise(client, "break-in-night", words=WORDS)
        _, key = helpers.issue(self.conn, self.data, "Planner", "read", ["readiness"])
        auth = {"Authorization": f"Bearer {key}"}
        for path in ("/", "/attention", "/drills/readiness", "/drills/readiness/break-in-night",
                     "/t/readiness__drill_steps", "/questions/readiness"):
            self.assertNotIn(WORDS, self.page(path, client), path)
        for path in ("/api/v1/tables/readiness__drill_steps/records", "/api/v1/attention", "/api/v1/tables"):
            reply = client.get(path, base_url=BASE, headers=auth)
            self.assertEqual(reply.status_code, 200, path)
            self.assertNotIn(WORDS, reply.get_data(as_text=True), path)
        page = self.page("/drills/readiness/break-in-night", client)
        self.assertIn("phone the emergency service first: 000", page)
        body = page.split("<main>")[1]  # the page's colours may contain digits like 999
        self.assertNotIn("911", body)
        self.assertNotIn("999", body)
        settings.put(self.conn, "household.country", "New Zealand")
        page = self.page("/drills/readiness/break-in-night", client)
        self.assertIn("Use your local emergency number", page)
        for number in ("000", "911", "999"):
            self.assertNotIn(number, page.split("<main>")[1])
        settings.put(self.conn, "household.country", "United States")
        self.assertIn("phone the emergency service first: 911", self.page("/drills/readiness/break-in-night", client))

    def test_5_breakdown_missing_words_kit_caution_and_uk_motorway_advice_only_in_the_uk(self):
        client = self.client()
        drill = next(d for d in drills.overview(self.conn, self.registry, self.prompt_set)
                     if d.scenario.id == "car-breakdown")
        self.assertEqual(drill.reasons, ["Nothing is recorded in Vehicles yet."])
        car = self.store.create("vehicles__vehicles", {"name": "Blue hatchback"})
        _, _, who = self.step_page(client, "car-breakdown", "car-who")
        self.assertIn("You haven&#39;t recorded who to call if this vehicle breaks down.", who)
        _, _, kit = self.step_page(client, "car-breakdown", "car-kit")
        self.assertIn("You haven&#39;t recorded a vehicle kit here; check the vehicle itself.", kit)
        item = self.store.create("stock__items", {"name": "Car kit", "category": "first_aid"})
        self.store.update("vehicles__vehicles", car, {"emergency_kit": item})
        _, _, kit = self.step_page(client, "car-breakdown", "car-kit")
        self.assertIn("It may have been moved or used since; check the vehicle itself.", kit)
        for country in ("Australia", "United States", "New Zealand"):
            settings.put(self.conn, "household.country", country)
            self.assertNotIn("National Highways", self.page("/drills/readiness/car-breakdown", client), country)
        settings.put(self.conn, "household.country", "United Kingdom")
        self.assertIn("National Highways, Breakdowns (UK motorways only)",
                      self.page("/drills/readiness/car-breakdown", client))

    def test_6_power_cut_says_what_is_not_recorded_and_promises_nothing(self):
        client = self.client()
        _, _, needs = self.step_page(client, "power-72-hours", "power-needs")
        self.assertIn("You haven&#39;t recorded power-dependent needs here. That does not mean no one depends on "
                      "electricity.", needs)
        _, _, lights = self.step_page(client, "power-72-hours", "power-lights")
        self.assertIn("You haven&#39;t recorded where your light supplies are.", lights)
        torch = self.store.create("stock__items", {"name": "Torch", "category": "power"})
        self.store.create("stock__lots", {"item": torch, "quantity": 2, "place": self.place("Hall cupboard")})
        _, _, lights = self.step_page(client, "power-72-hours", "power-lights")
        self.assertIn("Hall cupboard", lights)
        self.assertIn("Amounts are from your last count", lights)
        pages = [self.page("/drills/readiness/power-72-hours", client), needs, lights]
        for text in pages:
            low = text.lower()
            self.assertNotRegex(low, r"safe for (72|three)|keeps for 72|use a generator|run a generator indoors")
        self.assertIn("It does not say how long any food keeps", pages[0])

    def test_7_water_warning_counts_only_positive_drinking_litres_and_gives_no_blanket_boil_advice(self):
        client = self.client()
        settings.put(self.conn, "household.people", 2)
        shelf = self.place("Garage shelf")
        good = self.store.create("stock__items", {"name": "Bottled water", "category": "water", "drinking": True,
                                                  "unit": "litres"})
        flush = self.store.create("stock__items", {"name": "Flushing water", "category": "water",
                                                   "drinking": False, "unit": "litres"})
        bottles = self.store.create("stock__items", {"name": "Water bottles", "category": "water",
                                                     "drinking": True, "unit": "bottles"})
        self.store.create("stock__lots", {"item": good, "quantity": 12, "place": shelf})
        self.store.create("stock__lots", {"item": flush, "quantity": 40, "place": shelf})
        self.store.create("stock__lots", {"item": bottles, "quantity": 6, "place": shelf})
        offered = drills.questions.candidates(self.conn, self.registry, self.prompt_set.step("water-stored"))
        self.assertEqual([c.row["item"] for c in offered], [good])
        _, _, days = self.step_page(client, "water-warning", "water-days")
        self.assertIn("12 litres on hand", days)
        self.assertIn("not a promise", days)
        page = self.page("/drills/readiness/water-warning", client)
        self.assertIn("no current warning is known here", page)
        for text in (days, page):
            self.assertNotRegex(text.lower(), r"boil (your|the|tap) water|bring water to a boil")
        self.store.delete("stock__lots", self.conn.execute("SELECT id FROM stock__lots WHERE item = ?",
                                                           (good,)).fetchone()[0])
        _, _, days = self.step_page(client, "water-warning", "water-days")
        self.assertIn("A days estimate cannot be shown until people, pets and drinking-water litres are checked.",
                      days)

    def test_8_cyclone_fits_only_the_selected_hazard_in_au_or_us_with_its_own_source(self):
        client = self.client()

        def fits():
            return next(d for d in drills.overview(self.conn, self.registry, self.prompt_set)
                        if d.scenario.id == "cyclone-forecast").fits

        self.assertTrue(fits())
        page = self.page("/drills/readiness/cyclone-forecast", client)
        self.assertIn("Bureau of Meteorology", page)
        self.assertNotIn("National Weather Service", page)
        self.assertIn("it is not an instruction to leave", page)
        settings.put(self.conn, "household.country", "United States")
        page = self.page("/drills/readiness/cyclone-forecast", client)
        self.assertIn("National Weather Service", page)
        self.assertNotIn("Bureau of Meteorology", page)
        settings.put(self.conn, "household.country", "United Kingdom")
        self.assertFalse(fits())
        settings.put(self.conn, "household.country", "Australia")
        settings.put(self.conn, "household.hazards", ["flood"])
        self.assertFalse(fits())
        listing = self.page("/drills/readiness", client)
        section = listing.split("Does not fit your settings")[1]
        self.assertIn("A cyclone or hurricane forecast near your suburb", section)
        settings.put(self.conn, "household.country", "")
        self.assertIn("Settings do not say which country you live in.", self.page("/drills/readiness", client))

    def test_9_continue_later_then_practise_keeping_history_and_asking_again_when_a_record_changes(self):
        client = self.client()
        alarm = self.store.create("home_layout__equipment", {"name": "Hall alarm", "kind": "smoke_alarm",
                                                             "place": self.place("Hall"), "last_tested": "2026-10-01"})
        key = drills.questions.candidates(self.conn, self.registry, self.prompt_set.get("fire-alarm-location"))[0].key
        run_id = self.start(client, "bedroom-fire-night")
        self.post(client, self.step_path("bedroom-fire-night", run_id, 1), choice="plan", record=key,
                  own_words=WORDS, action="later")
        self.assertEqual([(r["status"], r["practised_on"]) for r in self.runs()], [("in_progress", None)])
        self.assertIn("saved to continue later", self.page("/drills/readiness", client))
        self.assertNotIn("Save this practice", self.page(f"/drills/readiness/bedroom-fire-night/runs/{run_id}",
                                                         client))
        refused = self.post(client, f"/drills/readiness/bedroom-fire-night/runs/{run_id}/finish",
                            practised_on="21/11/26")
        self.assertEqual(refused.status_code, 422)
        self.assertEqual(self.start(client, "bedroom-fire-night"), run_id)  # carries on, no second run
        for number in range(2, len(self.steps("bedroom-fire-night")) + 1):
            self.post(client, self.step_path("bedroom-fire-night", run_id, number), choice="check", action="next")
        page = self.page(f"/drills/readiness/bedroom-fire-night/runs/{run_id}", client)
        self.assertIn('value="21/11/27"', page)  # the offered look-again date
        reply = self.post(client, f"/drills/readiness/bedroom-fire-night/runs/{run_id}/finish",
                          practised_on="20/11/26", review_on="01/06/27")
        self.assertEqual(reply.status_code, 302)
        run = self.runs()[0]
        self.assertEqual((run["status"], run["practised_on"], run["review_on"], run["scenario_version"]),
                         ("practised", "2026-11-20", "2027-06-01", 1))
        first = self.step_rows()[0]
        self.assertEqual((first["step"], first["choice"], first["record"], first["own_words"]),
                         ("fire-alarm-location", "plan", key, WORDS))
        done = self.page(f"/drills/readiness/bedroom-fire-night/runs/{run_id}?saved=1", client)
        self.assertIn("Practised on 20/11/26 · Look again on 01/06/27", done)
        self.assertNotIn(WORDS, done)
        self.assertIn(f'formaction="/t/readiness__drill_steps/{first["id"]}/reveal"', done)
        reveal = client.post(f"/t/readiness__drill_steps/{first['id']}/reveal", data={"column": "own_words", "_csrf": client.application.config["CSRF_TOKEN"]}, base_url=BASE, headers={"Accept": "application/json"})
        self.assertEqual(reveal.get_json()["text"], WORDS)
        self.assertEqual(self.post(client, self.step_path("bedroom-fire-night", run_id, 1), choice="not_relevant",
                                   action="next").status_code, 409)  # a finished practice is history
        second = self.practise(client, "bedroom-fire-night", choice="check")
        self.assertNotEqual(second, run_id)
        self.assertEqual([r["status"] for r in self.runs()], ["practised", "practised"])
        self.assertEqual(self.step_rows()[0]["own_words"], WORDS)
        self.store.update("home_layout__equipment", alarm, {"last_tested": "2026-11-15"})
        page = self.page(f"/drills/readiness/bedroom-fire-night/runs/{run_id}", client)
        self.assertIn(CHANGED_WORDS, page)
        self.assertEqual(self.step_rows()[0]["choice"], "plan")
        self.assertEqual(self.post(client, f"/drills/readiness/bedroom-fire-night/runs/{run_id}/finish",
                                   practised_on="21/11/26").status_code, 422)
        self.today = date(2027, 11, 22)
        self.assertIn("It is time to look at this again.", self.page("/drills/readiness", client))

    def test_10_a_shared_question_counts_on_questions_and_own_words_stay_out_of_the_answer(self):
        client = self.client()
        self.store.create("home_layout__equipment", {"name": "Hall alarm", "kind": "smoke_alarm",
                                                     "place": self.place("Hall"), "last_tested": "2026-10-01"})
        key = drills.questions.candidates(self.conn, self.registry, self.prompt_set.get("fire-alarm-location"))[0].key
        run_id, number, page = self.step_page(client, "bedroom-fire-night", "fire-alarm-location")
        self.assertIn("This question is also on the Questions page.", page)
        self.post(client, self.step_path("bedroom-fire-night", run_id, number), choice="plan", record=key,
                  own_words=WORDS, action="next")
        answer = dict(self.conn.execute("SELECT * FROM readiness__answers").fetchone())
        self.assertEqual((answer["prompt"], answer["answer"], answer["record"], answer["note"]),
                         ("fire-alarm-location", "yes", key, None))
        self.assertIn("Your answer: <strong>Yes</strong>", self.page("/questions/readiness/fire-alarm-location", client))
        self.assertRegex(self.page("/questions/readiness", client), r"1 of \d+ questions")
        self.post(client, self.step_path("bedroom-fire-night", run_id, number + 2), choice="check", action="next")
        answers = {r["prompt"]: r["answer"] for r in self.conn.execute("SELECT prompt, answer FROM readiness__answers")}
        self.assertEqual(answers, {"fire-alarm-location": "yes", "fire-meeting-place": "not_yet"})
        self.assertNotIn(WORDS, json.dumps([dict(r) for r in self.conn.execute("SELECT * FROM readiness__answers")]))
        # Helpers can look at runs but never answer one, and a spreadsheet cannot be imported into them.
        _, key2 = helpers.issue(self.conn, self.data, "Planner", "suggest", ["readiness"])
        auth = {"Authorization": f"Bearer {key2}"}
        specs = {t["table"]: t for t in client.get("/api/v1/tables", base_url=BASE, headers=auth).get_json()["tables"]}
        self.assertFalse(specs["readiness__drill_steps"]["can_suggest"])
        self.assertFalse(specs["readiness__drill_runs"]["can_suggest"])
        reply = client.post("/api/v1/proposals", base_url=BASE, headers=auth, json={
            "request_key": "drill-1", "why": "Practised it",
            "entries": [{"table": "readiness__drill_runs", "values": {"scenario": "pipe-in-wall",
                                                                    "scenario_version": 1, "status": "practised",
                                                                    "started_on": "2026-11-21"}}]})
        self.assertEqual(reply.status_code, 422)
        self.assertIn("can't be imported", why_not_table(self.registry["readiness__drill_steps"]))

    def test_11_every_screen_reads_in_order_with_labels_and_makes_no_claim(self):
        client = self.client()
        run_id = self.start(client, "pipe-in-wall")
        pages = [self.page(p, client) for p in (
            "/drills/readiness", "/drills/readiness/pipe-in-wall", self.step_path("pipe-in-wall", run_id, 1),
            f"/drills/readiness/pipe-in-wall/runs/{run_id}")]
        step = pages[2]
        for snippet in ('<label for="own_words">', "<legend", 'name="choice"', "Step 1 of 4"):
            self.assertIn(snippet, step)
        self.assertLess(step.index("<h1>"), step.index("From your records"))
        self.assertLess(step.index("From your records"), step.index("Your answer"))
        intro = pages[1]
        self.assertLess(intro.index("The questions"), intro.index("Sources and local limits"))
        self.assertEqual(intro.count("checked 21/11/26"), 3)  # two sources and the emergency number
        for text in pages:
            self.assertEqual(text.count("<h1>"), 1)
            for claim in CLAIMS:
                self.assertNotIn(claim, text.lower())

    def test_12_a_broken_or_old_source_is_kept_and_marked_never_replaced(self):
        scenario = self.prompt_set.scenario("pipe-in-wall")
        broken = drills.Scenario(**{**scenario.__dict__, "sources": [
            {"title": "A public body", "url": "", "checked": None, "country": None, "broken": True},
            {"title": "Another public body", "url": "https://example.org/", "checked": "2024-01-01",
             "country": None, "broken": False}]})
        shown = drills.sources(broken, "Australia", TODAY)
        self.assertEqual([(s["title"], s["needs_checking"]) for s in shown],
                         [("A public body", True), ("Another public body", True)])
        self.assertTrue(all(not s["needs_checking"] for s in drills.sources(scenario, "Australia", TODAY)))
        client = self.client()
        self.assertNotIn("Source needs checking", self.page("/drills/readiness/pipe-in-wall", client))
        self.today = date(2028, 1, 1)
        page = self.page("/drills/readiness/pipe-in-wall", client)
        self.assertEqual(page.count("Source needs checking."), 2)
        self.assertIn("American Red Cross, Make a Plan", page)
        self.assertNotIn("http://", page.split("Sources and local limits")[1].split("</ul>")[0])


class DrillPrivacyTests(DrillTestCase):
    def test_own_words_never_leave_this_computer(self):
        client = self.client()
        self.practise(client, "break-in-night", words=WORDS)
        self.practise(client, "power-72-hours", words=WORDS, finish=False)
        stored = self.step_rows()
        self.assertTrue(all(r["own_words"] == WORDS for r in stored))
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 21, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for name in archive.namelist():
                self.assertNotIn(WORDS, archive.read(name).decode("utf-8", "replace"), name)
            self.assertIn("practised", archive.read("readiness__drill_runs.csv").decode("utf-8-sig").lower())
        changes = [dict(r) for r in self.conn.execute(
            "SELECT * FROM core__sync_changes WHERE table_name = 'readiness__drill_steps'")]
        self.assertTrue(changes)
        self.assertNotIn(WORDS, json.dumps(changes))
        self.assertTrue(all("own_words" in json.loads(c["withheld"] or "[]") for c in changes if c["action"] == "create"))
        self.assertNotIn(WORDS, json.dumps(sync.snapshot(self.conn, self.registry), default=str))
        for sheet in available_sheets(self.registry):
            self.assertNotIn(WORDS, self.page(f"/sheet/{sheet['module']}/{sheet['name']}", client))
        _, key = helpers.issue(self.conn, self.data, "Reader", "read", ["readiness"])
        reply = client.get("/api/v1/tables/readiness__drill_steps/records", base_url=BASE,
                           headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(reply.status_code, 200)
        self.assertNotIn(WORDS, reply.get_data(as_text=True))
        self.assertNotIn("own_words", reply.get_data(as_text=True))
        for path in ("/", "/attention", "/drills/readiness", "/t/readiness__drill_steps",
                     f"/t/readiness__drill_steps/{stored[0]['id']}"):
            self.assertNotIn(WORDS, self.page(path, client), path)

    def test_an_unknown_or_stale_step_or_record_is_refused(self):
        client = self.client()
        run_id = self.start(client, "pipe-in-wall")
        self.assertEqual(self.post(client, self.step_path("pipe-in-wall", run_id, 2), choice="maybe").status_code, 422)
        self.assertEqual(self.post(client, self.step_path("pipe-in-wall", run_id, 2), choice="plan",
                                   record="people__people:nope").status_code, 422)
        self.assertEqual(self.post(client, self.step_path("pipe-in-wall", run_id, 9), choice="plan").status_code, 404)
        self.assertEqual(client.get(self.step_path("kitchen-fire", run_id, 1), base_url=BASE).status_code, 404)
        self.assertEqual(self.post(client, "/drills/readiness/no-such-drill/start").status_code, 404)
        self.assertEqual(self.step_rows(), [])


class DrillModuleTests(DrillTestCase):
    def test_module_off_hides_every_drill_screen_keeps_runs_and_on_brings_them_back(self):
        client = self.client()
        run_id = self.practise(client, "pipe-in-wall")
        self.assertIn('href="/drills/readiness">Think it through</a>', self.page("/", client))
        self.assertIn('href="/drills/readiness">Think it through</a>', self.page("/questions/readiness", client))
        self.assertEqual(client.get("/drills", base_url=BASE).headers["Location"], "/drills/readiness")
        settings.set_module_enabled(self.conn, "readiness", False)
        for path in ("/drills", "/drills/readiness", "/drills/readiness/pipe-in-wall",
                     f"/drills/readiness/pipe-in-wall/runs/{run_id}", f"/drills/readiness/pipe-in-wall/runs/{run_id}/1"):
            self.assertEqual(client.get(path, base_url=BASE).status_code, 404, path)
        self.assertEqual(self.post(client, "/drills/readiness/pipe-in-wall/start").status_code, 404)
        self.assertNotIn("Think it through", self.page("/", client))
        settings.set_module_enabled(self.conn, "readiness", True)
        self.assertEqual(len(self.runs()), 1)
        self.assertIn("Practised on 21/11/26", self.page("/drills/readiness", client))

    def test_a_switched_off_module_only_hides_its_records_from_a_step(self):
        self.store.create("home_layout__shutoffs", {"name": "Mains tap", "kind": "water", "place": self.place("Yard")})
        settings.set_module_enabled(self.conn, "home_layout", False)
        client = self.client()
        _, _, page = self.step_page(client, "pipe-in-wall", "pipe-shutoff")
        self.assertIn("You haven&#39;t recorded where your water shut-off is.", page)
        self.assertNotIn("Add it now", page)
        self.assertNotIn("Mains tap", page)


class DrillExampleTests(TempDirTestCase):
    def test_the_three_example_households_fit_as_the_draft_says(self):
        expected = {"smith": ("000", True, False, "pipe-in-wall"),
                    "garcia": ("911", False, True, "power-72-hours"),
                    "taylor": ("999", False, True, "bedroom-fire-night")}
        for household, (number, cyclone, flat_step, practised) in expected.items():
            data = self.tmp / household
            load_example.load(household, data, today=TODAY)
            report = startup.prepare(data)
            conn = db.connect(data / "dashboard.db")
            self.addCleanup(conn.close)
            registry = records.build_registry(report.loaded)
            prompt_set = drills.drill_sets(registry)["readiness"]
            home = questions.profile(conn, registry)
            found = {d.scenario.id: d for d in drills.overview(conn, registry, prompt_set)}
            self.assertEqual(drills.emergency(prompt_set, home["country"])["number"], number, household)
            self.assertEqual(found["cyclone-forecast"].fits, cyclone, household)
            self.assertTrue(found["car-breakdown"].fits, household)  # each example records a vehicle
            steps = [s.id for s in drills.fitting_steps(prompt_set, prompt_set.scenario("bedroom-fire-night"), home)]
            self.assertEqual("fire-building-plan" in steps, flat_step, household)
            runs = [r for d in found.values() for r in d.runs]
            self.assertEqual([r["scenario"] for r in runs if r["status"] == "practised"], [practised], household)
            self.assertTrue(all(r["review_on"] for r in runs if r["status"] == "practised"), household)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM readiness__drill_steps").fetchone()[0], 0)
