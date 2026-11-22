"""Tests for the Pet feeding log: food put out (not eaten), honest daily totals by the household's own day, fast entry, helpers on Review.

These follow the eight checks in Lane B's draft (its ACCEPTANCE.md, now in git history) that a computer can run (decision 0110),
plus the household's local day around midnight and daylight-saving changes, units that never mix, paging and the change log.
The member phone app and transfer are not shipped, so offline save on a phone is not tested here."""
import json
import re
import shutil
import time
from datetime import date, datetime, timezone
from urllib.parse import parse_qs, urlparse

from support import ROOT, TempDirTestCase
from dashboard.core import daily, db, helpers, modules, proposals, records, settings, startup, sync, watch
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
import load_example

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
TABLE = "pet_feeding__servings"
NO_ENTRY = "No feeding entry recorded today"
SYDNEY_NOON = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)  # 20 Nov 2026, 12:00 in Sydney (daylight time)


class FeedingTestCase(TempDirTestCase):
    MODULES = ("people", "pets", "pet_feeding")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)
        self.info = self.registry[TABLE]
        self.rule = self.info.table.daily
        settings.put(self.conn, daily.ZONE_KEY, "Australia/Sydney")
        self.zone = daily.household_zone(self.conn)
        self.rex = self.records.create("pets__pets", {"name": "Rex", "species": "dog"})
        self.luna = self.records.create("pets__pets", {"name": "Luna", "species": "cat"})

    def feed(self, pet=None, at="2026-11-20T07:15:00", **values):
        values = {"kind": "bowl", "food": "Example dry dog food", "amount": 120, "unit": "g", **values}
        return self.records.create(TABLE, {"pet": pet or self.rex, "given_at": at, **values})

    def day(self, day="2026-11-20", pet=None):
        return daily.days(self.conn, self.info, pet or self.rex, day, day, self.zone)[0]

    def words(self, day="2026-11-20", pet=None, when="today"):
        return daily.summary(self.rule, self.day(day, pet), when)

    def client(self, now=SYDNEY_NOON):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: now
        app.config["TODAY"] = lambda: now.astimezone(self.zone).date()
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None, status=200):
        response = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)

    def helper(self, name="Feeding helper", modules_=("pets", "pet_feeding")):
        return helpers.issue(self.conn, self.data, name, "suggest", list(modules_))

    def suggest(self, helper, values, key="r1", why="Read from the feeding chart on the fridge", source=None):
        entry = {"table": TABLE, "values": {"pet": self.rex, "given_at": "2026-11-20T07:15:00", "kind": "bowl",
                                            "food": "Example dry dog food", "amount": 120, "unit": "g", **values}}
        if source:
            entry["source"] = source
        result, _ = proposals.submit(self.conn, self.registry, helper, {"request_key": key, "why": why,
                                                                       "entries": [entry]})
        return result


class AcceptanceTests(FeedingTestCase):
    def test_1_examples_link_to_real_pets_and_a_pet_with_feedings_is_not_deleted(self):
        found = {}
        for name in ("smith", "garcia", "taylor"):
            data = self.tmp / name
            load_example.load(name, data, ROOT / "modules", today=date(2026, 11, 21))
            conn = db.connect(data / "dashboard.db")
            try:
                on = settings.enabled_modules(conn)
                found[name] = ("pet_feeding" in on, [tuple(r) for r in conn.execute(
                    f"SELECT p.name, s.given_at, s.amount, s.unit FROM {TABLE} s JOIN pets__pets p ON p.id = s.pet "
                    f"ORDER BY s.id")])
            finally:
                conn.close()
        self.assertEqual(found["smith"], (True, [("Rex", "2026-11-20T07:15:00", 120.0, "g"),
                                                 ("Rex", "2026-11-20T18:10:00", 120.0, "g")]))
        self.assertEqual(found["garcia"], (True, [("Luna", "2026-11-20T08:00:00", 1.0, "pouch"),
                                                  ("Luna", "2026-11-20T18:00:00", None, None)]))
        self.assertEqual(found["taylor"], (False, []))  # Taylor has no pet and no invented feeding
        with self.assertRaises(records.ValidationError) as caught:
            self.records.create(TABLE, {"pet": 999, "given_at": "2026-11-20T07:15", "kind": "bowl", "food": "X"})
        self.assertIn("pet", caught.exception.problems)
        self.feed()
        with self.assertRaises(Exception) as refused:
            self.records.delete("pets__pets", self.rex)
        self.assertIn("food given", str(refused.exception).lower())
        self.assertIsNone(self.records.get("pets__pets", self.rex).get("deleted_at"))
        self.records.delete("pets__pets", self.luna)  # a pet with no feedings can still go

    def test_2_bowl_refill_and_treat_add_only_new_food_and_a_correction_changes_the_total_once(self):
        self.feed(at="2026-11-20T07:15:00")
        refill = self.feed(at="2026-11-20T12:00:00", kind="refill", amount=40)
        self.feed(at="2026-11-20T15:00:00", kind="treat", food="Example dog biscuit", amount=2, unit="piece")
        self.assertEqual(self.words(), "Recorded today: 160 g and 2 pieces put out")
        before = self.conn.execute(f"SELECT global_id, row_revision FROM {TABLE} WHERE id = ?", (refill,)).fetchone()
        self.records.update(TABLE, refill, {"amount": 60})  # a mistaken amount is corrected on the same entry
        after = self.conn.execute(f"SELECT global_id, row_revision FROM {TABLE} WHERE id = ?", (refill,)).fetchone()
        self.assertEqual((after[0], after[1]), (before[0], before[1] + 1))
        self.assertEqual(self.words(), "Recorded today: 180 g and 2 pieces put out")
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0], 3)  # no offsetting row

    def test_3_units_never_mix_and_unmeasured_entries_are_counted_not_guessed(self):
        self.feed(at="2026-11-20T07:15:00")
        self.feed(at="2026-11-20T18:00:00", food="Example wet food", amount=1, unit="pouch")
        self.assertEqual(self.words(), "Recorded today: 120 g and 1 pouch put out")
        self.assertNotIn("121", self.words())
        self.feed(at="2026-11-20T19:00:00", kind="refill", amount=None, unit=None)
        self.assertEqual(self.words(), "Recorded today: 120 g and 1 pouch put out; 1 feeding has no amount")
        for word in ("ate", "eaten", "intake", "complete"):
            self.assertNotIn(word, self.words().lower())
        self.feed(pet=self.luna, amount=None, unit=None)
        self.feed(pet=self.luna, at="2026-11-20T09:00:00", amount=None, unit=None)
        self.assertEqual(self.words(pet=self.luna), "2 feedings recorded today; amounts not measured")
        with self.assertRaises(records.ValidationError) as caught:
            self.feed(unit=None)
        self.assertEqual(caught.exception.problems, {"unit": "is needed with an amount. Choose one, or leave the "
                                                             "amount blank."})
        with self.assertRaises(records.ValidationError) as caught:
            self.feed(amount=None)
        self.assertIn("amount", caught.exception.problems)
        entry = self.feed(at="2026-11-20T20:00:00")
        with self.assertRaises(records.ValidationError):
            self.records.update(TABLE, entry, {"unit": None})  # a change is checked the same way

    def test_4_the_household_day_keeps_each_instant_and_a_late_entry_updates_its_own_day(self):
        self.feed(at="2026-11-20T23:59:00")  # typed in the household's local time
        self.feed(at="2026-11-20T13:30:00+00:00", amount=10)  # an instant: 00:30 on 21 Nov in Sydney
        self.feed(at="2026-11-20T00:05:00+11:00", amount=5)  # sent with Sydney's own offset
        self.assertEqual(self.words("2026-11-20"), "Recorded today: 125 g put out")
        self.assertEqual(self.words("2026-11-21"), "Recorded today: 10 g put out")
        stored = [r[0] for r in self.conn.execute(f"SELECT given_at FROM {TABLE} ORDER BY id")]
        self.assertEqual(stored[1:], ["2026-11-20T13:30:00+00:00", "2026-11-20T00:05:00+11:00"])  # kept as sent
        # A late entry, typed days afterwards, counts on the day it happened.
        self.feed(at="2026-11-18T08:00:00", amount=7)
        self.assertEqual(self.words("2026-11-18", when="on 18/11/26"), "Recorded on 18/11/26: 7 g put out")

    def test_4_daylight_saving_changes_and_another_time_zone(self):
        # Sydney: clocks went forward at 02:00 on 4 October 2026 and back at 03:00 on 5 April 2026.
        cases = {"2026-10-03T13:59:00Z": "2026-10-03", "2026-10-03T14:00:00Z": "2026-10-04",
                 "2026-10-04T12:59:00Z": "2026-10-04", "2026-10-04T13:00:00Z": "2026-10-05",
                 "2026-04-04T13:30:00Z": "2026-04-05", "2026-04-05T13:59:00Z": "2026-04-05",
                 "2026-04-05T14:00:00Z": "2026-04-06"}
        for instant, day in cases.items():
            self.assertEqual(daily.local_day(instant, self.zone), day, instant)
        settings.put(self.conn, daily.ZONE_KEY, "America/New_York")
        zone = daily.household_zone(self.conn)
        self.assertEqual(daily.local_day("2026-11-02T04:30:00Z", zone), "2026-11-01")  # 23:30 EST, after the change
        self.assertEqual(daily.local_day("2026-11-01T03:59:00Z", zone), "2026-10-31")  # 23:59 EDT
        self.assertEqual(daily.local_day("2026-11-01T23:30:00", zone), "2026-11-01")  # typed local time stays put
        self.assertEqual(daily.today(self.conn, datetime(2026, 11, 2, 4, 30, tzinfo=timezone.utc)), date(2026, 11, 1))
        settings.put(self.conn, daily.ZONE_KEY, "Not/AZone")
        self.assertIsNone(daily.household_zone(self.conn))  # an unknown zone falls back to this computer's clock
        self.assertEqual(daily.local_day("2026-11-01T23:30:00", None), "2026-11-01")

    def test_5_a_retry_makes_one_review_request_and_only_an_acceptance_changes_the_total(self):
        helper, _key = self.helper()
        first = self.suggest(helper, {}, key="tap-1")
        again = self.suggest(helper, {}, key="tap-1")  # a double tap or a retried transfer
        self.assertEqual(first, again)
        self.assertEqual(proposals.pending_count(self.conn), 1)
        self.assertEqual(self.words(), NO_ENTRY)  # waiting is not accepted
        self.assertEqual(daily.waiting(self.conn, self.info, self.rex), 1)
        client = self.client()
        pet_page = self.page(f"/t/pets__pets/{self.rex}", client)
        self.assertIn(NO_ENTRY, pet_page)
        self.assertIn("1 suggestion is waiting on Review</a>, not counted until accepted", pet_page)
        home = self.page("/", client)
        self.assertIn(f"Rex</a> · {NO_ENTRY}", home)
        proposal = self.conn.execute("SELECT id FROM core__proposals").fetchone()[0]
        client.post(f"/review/{proposal}/reject", data={"_csrf": client.csrf}, base_url=BASE)
        self.assertEqual(self.words(), NO_ENTRY)
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals").fetchone()[0], "rejected")
        self.suggest(helper, {}, key="tap-2")
        proposal = self.conn.execute("SELECT id FROM core__proposals WHERE status = 'pending'").fetchone()[0]
        client.post(f"/review/{proposal}/accept", data={"_csrf": client.csrf}, base_url=BASE)
        self.assertEqual(self.words(), "Recorded today: 120 g put out")
        self.assertIn("Rex</a> · 1 feeding recorded today · 120 g put out", self.page("/", client))

    def test_6_helper_needs_the_grant_and_possible_repeats_wait_for_a_person(self):
        other, other_key = self.helper("Pantry helper", ("pets",))
        with self.assertRaises(proposals.ProposalError):
            self.suggest(other, {})
        client = self.client()
        reply = client.get(f"/api/v1/tables/{TABLE}/records", base_url=BASE,
                           headers={"Authorization": f"Bearer {other_key}"})
        self.assertIn(reply.status_code, (403, 404))
        self.feed(at="2026-11-20T07:15:00")  # typed by a person
        first, first_key = self.helper("Kitchen tablet")
        second, _ = self.helper("Fridge camera helper")
        reply = client.get(f"/api/v1/tables/{TABLE}/records", base_url=BASE,
                           headers={"Authorization": f"Bearer {first_key}"})
        self.assertEqual(reply.status_code, 200)
        self.suggest(first, {"given_at": "2026-11-20T07:20:00"}, key="a", why="SECRET-REASON-31",
                     source={"line": "SOURCE-LINE-77"})
        self.suggest(second, {"given_at": "2026-11-20T07:25:00"}, key="b")
        self.suggest(second, {"given_at": "2026-11-20T18:10:00"}, key="c")  # evening: not a repeat
        page = self.page("/review", client)
        self.assertEqual(page.count("Possible repeat feeding entry."), 2)
        self.assertIn("20/11/26 7:15 am · Bowl · Example dry dog food · 120 g, already in your records", page)
        self.assertIn("also waiting on Review, from Fridge camera helper", page)
        self.assertIn("also waiting on Review, from Kitchen tablet", page)
        self.assertEqual(page.count("Accept as another feeding"), 2)
        self.assertEqual(page.count("Reject this copy"), 2)
        self.assertEqual(self.words(), "Recorded today: 120 g put out")  # nothing counts before acceptance
        ids = [r[0] for r in self.conn.execute("SELECT id FROM core__proposals ORDER BY id")]
        client.post(f"/review/{ids[0]}/accept", data={"_csrf": client.csrf}, base_url=BASE)
        client.post(f"/review/{ids[1]}/reject", data={"_csrf": client.csrf}, base_url=BASE)
        client.post(f"/review/{ids[2]}/accept", data={"_csrf": client.csrf}, base_url=BASE)
        self.assertEqual(self.words(), "Recorded today: 360 g put out")
        notes = [r[0] for r in self.conn.execute(f"SELECT notes FROM {TABLE}")]
        self.assertEqual(notes, [None, None, None])  # the source and reason never become a feeding note
        text = json.dumps([list(r) for r in self.conn.execute(f"SELECT * FROM {TABLE}")])
        self.assertNotIn("SECRET-REASON-31", text)
        self.assertNotIn("SOURCE-LINE-77", text)

    def test_6_acceptance_checks_the_pet_again(self):
        helper, _ = self.helper()
        self.suggest(helper, {"pet": self.luna})
        self.records.delete("pets__pets", self.luna)
        proposal = self.conn.execute("SELECT id FROM core__proposals").fetchone()[0]
        with self.assertRaises(Exception):
            proposals.accept_counted(self.conn, self.registry, proposal)
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0], 0)

    def test_7_a_thousand_entries_a_year_page_and_the_sheet_is_complete_or_says_it_cannot_be(self):
        rows = []
        for n in range(1000):  # about 2.7 a day for a year, invented
            day = date.fromordinal(date(2025, 11, 21).toordinal() + n * 365 // 1000)
            rows.append((self.rex, f"{day.isoformat()}T{7 + n % 12:02d}:{n % 60:02d}:00", "bowl", "Example dry dog food",
                         100.0, "g", "2026-01-01T00:00:00", "2026-01-01T00:00:00"))
        self.conn.executemany(
            f"INSERT INTO {TABLE} (pet, given_at, kind, food, amount, unit, created_at, updated_at) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        self.conn.commit()
        client = self.client()
        grid = self.page(f"/t/{TABLE}", client)
        self.assertIn("1000", grid)
        self.assertLessEqual(len(re.findall(rf'href="/t/{TABLE}/\d+"', grid)), 60)  # one page, not 1,000 rows
        started = time.perf_counter()
        day_page = self.page(f"/daily/{TABLE}?subject={self.rex}&day=2026-11-19", client)
        sheet = self.page(f"/daily/{TABLE}/sheet?subject={self.rex}", client)
        self.assertLess(time.perf_counter() - started, 2.0)
        self.assertIn("Food put out for Rex · 19/11/26", day_page)
        self.assertIn("Every entry in the range is on this sheet.", sheet)
        counted = int(re.search(r"(\d+) feedings recorded\.", sheet).group(1))
        self.assertEqual(counted, daily.count(self.conn, self.info, self.rex, "2026-11-07", "2026-11-20", self.zone))
        self.assertEqual(sheet.count("<tr><td"), counted)  # one line per entry, none left out
        year = self.page(f"/daily/{TABLE}/sheet?subject={self.rex}&from=21/11/25&to=20/11/26", client)
        self.assertIn("This range has 365 days and 1000 feedings, more than one sheet can print completely", year)
        self.assertIn("Nothing was left out: choose a shorter range.", year)
        self.assertNotIn("<tr><td", year)
        self.assertEqual(year.count("/sheet?subject="), 8)  # shorter ranges offered
        self.assertIn("Food put out, not necessarily eaten. Check for entries made elsewhere.", sheet)

    def test_8_an_empty_day_never_warns_and_the_sheet_omits_notes(self):
        client = self.client()
        home = self.page("/", client)
        self.assertIn(f"Rex</a> · {NO_ENTRY}", home)
        self.assertIn("See feeding log", home)
        for page in (home, self.page("/attention", client)):
            for word in ("not been fed", "missed", "hungry", "feeding target", "should eat"):
                self.assertNotIn(word, page.lower())
        self.assertEqual([g for g in watch.gaps(self.conn, self.registry) if g.table == TABLE], [])
        self.assertEqual([e for e in watch.expiring(self.conn, self.registry) if e.table == TABLE], [])
        self.feed(notes="NOTE-SHOULD-NOT-PRINT-19")
        sheet = self.page(f"/daily/{TABLE}/sheet?subject={self.rex}", client)
        self.assertIn("7:15 am", sheet)
        self.assertNotIn("NOTE-SHOULD-NOT-PRINT-19", sheet)
        self.assertIn("Day total: 120 g put out", sheet)


class FastEntryTests(FeedingTestCase):
    def test_add_food_from_the_pet_page_fills_in_the_last_choices_visibly_and_comes_back(self):
        client = self.client()
        page = self.page(f"/t/pets__pets/{self.rex}", client)
        self.assertIn("Food put out today", page)
        link = re.search(r'href="([^"]+)" data-add-food>Add food<', page).group(1).replace("&amp;", "&")
        args = parse_qs(urlparse(link).query)
        self.assertEqual((args["pet"], args["given_at"]), ([str(self.rex)], ["2026-11-20T12:00"]))
        self.assertNotIn("amount", args)  # nothing remembered yet
        self.feed(at="2026-11-20T07:15:00", bowl="Kitchen bowl")
        page = self.page(f"/t/pets__pets/{self.rex}", client)
        self.assertIn("Recorded today: 120 g put out", page)
        link = re.search(r'href="([^"]+)" data-add-food>Add food<', page).group(1).replace("&amp;", "&")
        args = parse_qs(urlparse(link).query)
        self.assertEqual({k: v[0] for k, v in args.items() if k not in ("pet", "given_at")},
                         {"kind": "bowl", "bowl": "Kitchen bowl", "food": "Example dry dog food", "amount": "120",
                          "unit": "g", "from": "last"})
        form = self.page(link, client)
        self.assertIn("Filled in from a recent entry. Check each answer before you save.", form)
        self.assertIn('value="Kitchen bowl"', form)
        self.assertIn('value="120"', form)
        saved = client.post(f"/t/{TABLE}/new", base_url=BASE, data={
            "_csrf": client.csrf, "pet": str(self.rex), "given_at": "2026-11-20T18:10", "kind": "bowl",
            "bowl": "Kitchen bowl", "food": "Example dry dog food", "amount": "120", "unit": "g", "then": "back",
            "back": f"/t/pets__pets/{self.rex}"})
        self.assertEqual(saved.headers["Location"], f"/t/pets__pets/{self.rex}")
        page = self.page(f"/t/pets__pets/{self.rex}", client)
        self.assertIn("Recorded today: 240 g put out", page)
        self.assertIn("7:15 am · Kitchen bowl · Example dry dog food · 120 g", page)
        self.assertIn("6:10 pm · Kitchen bowl · Example dry dog food · 120 g", page)

    def test_the_day_page_moves_between_days_and_says_yesterday(self):
        self.feed(at="2026-11-19T07:15:00")
        client = self.client()
        today = self.page(f"/daily/{TABLE}?subject={self.rex}", client)
        self.assertIn("Food put out for Rex · 20/11/26", today)
        self.assertIn(NO_ENTRY, today)
        self.assertNotIn("Day after", today)  # no future days
        before = self.page(f"/daily/{TABLE}?subject={self.rex}&day=2026-11-19", client)
        self.assertIn("Recorded yesterday: 120 g put out", before)
        self.assertIn("Day after", before)
        self.assertIn("Luna", before)  # choose another pet
        future = self.page(f"/daily/{TABLE}?subject={self.rex}&day=2027-01-01", client)
        self.assertIn("Food put out for Rex · 20/11/26", future)


class ModuleTests(FeedingTestCase):
    def test_module_files_migration_and_its_checker(self):
        module = modules.load_module(ROOT / "modules" / "pet_feeding")
        self.assertEqual((module.requires, module.outbound_hosts), (["pets"], []))
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "pet_feeding" / "migrations" / "0001_initial.sql").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"CREATE TABLE (\S+)", sql), [TABLE])
        self.assertIn("pets__pets(id) ON DELETE RESTRICT", sql)
        self.assertEqual(self.rule["repeat"], {"minutes": 30, "same": ["food", "amount", "unit"]})
        bad = (ROOT / "modules" / "pet_feeding" / "tables.toml").read_text(encoding="utf-8").replace(
            'when = "given_at"', 'when = "food"').replace("minutes = 30", "minutes = 0")
        self.make_module("feedbad", tables=bad.replace("pets.pets", "pets"), labels=None, root="bad")
        found, failures = modules.discover(self.tmp / "bad")
        text = " ".join(failures.get("feedbad", []))
        self.assertIn("'when' must name a required date-and-time column", text)
        self.assertIn("repeat 'minutes' must be a whole number from 1 to 240", text)

    def test_switched_off_it_has_no_pages_and_on_again_it_keeps_its_entries(self):
        entry = self.feed()
        settings.set_module_enabled(self.conn, "pet_feeding", False)
        client = self.client()
        self.page(f"/daily/{TABLE}", client, status=404)
        self.page(f"/daily/{TABLE}/sheet", client, status=404)
        self.assertNotIn("Food put out today", self.page("/", client))
        self.assertNotIn("Food put out today", self.page(f"/t/pets__pets/{self.rex}", client))
        settings.set_module_enabled(self.conn, "pet_feeding", True)
        client = self.client()
        self.assertIn("Rex</a> · 1 feeding recorded today · 120 g put out", self.page("/", client))
        self.assertIsNotNone(self.records.get(TABLE, entry))

    def test_the_change_log_covers_every_entry_and_its_notes_travel(self):
        start = self.conn.execute("SELECT COALESCE(MAX(seq), 0) FROM core__sync_changes").fetchone()[0]
        entry = self.feed(notes="Ate half, invented")
        self.records.update(TABLE, entry, {"amount": 100})
        self.records.delete(TABLE, entry)
        lines = [c for c in sync.changes(self.conn, start) if c["table_name"] == TABLE]
        self.assertEqual([c["action"] for c in lines], ["create", "update", "delete"])
        self.assertEqual(len({c["global_id"] for c in lines}), 1)
        self.assertEqual(lines[0]["patch"]["notes"], "Ate half, invented")
        self.assertEqual(lines[0]["patch"]["given_at"], "2026-11-20T07:15:00")
        self.assertEqual(sync.unreviewed(self.registry), [])
        self.assertEqual(sync.check(self.conn, self.registry), [])
        self.assertEqual(self.words(), NO_ENTRY)  # a deleted entry is not counted

    def test_amount_words(self):
        self.assertEqual([daily.amount_words(a, u) for a, u in ((120, "g"), (1, "pouch"), (2, "pouch"),
                                                                  (1.5, "scoop"), (3, "piece"), (250.0, "ml"))],
                         ["120 g", "1 pouch", "2 pouches", "1.5 scoops", "3 pieces", "250 ml"])
