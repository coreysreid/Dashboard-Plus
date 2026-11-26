"""Tests for one record's timeline (decision 0126): the declaration, newest first by month, a symbol and words per kind, the change since the weigh-in before, feedings one line a day, Earlier paging, the empty words, modules switched off and private doses before and after Show."""
import re
import shutil
from datetime import date, datetime, timedelta, timezone

from support import ROOT, TempDirTestCase
from dashboard.core import daily, db, modules, records, settings, startup, timeline
from dashboard.web.app import create_app
from test_module_medicine_doses import AMOUNT, SECRET, TABLE as DOSES, DoseTestCase

PORT = 5151
BASE = f"http://127.0.0.1:{PORT}"
PETS, WEIGH, VISITS, TREAT, GIVEN, FEED = ("pets__pets", "pets__weigh_ins", "pets__vet_visits", "pets__treatments",
                                           "pets__given", "pet_feeding__servings")
SYDNEY_NOON = datetime(2026, 11, 25, 1, 0, tzinfo=timezone.utc)  # Wednesday 25 Nov 2026, 12:00 in Sydney
TODAY = date(2026, 11, 25)


def plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def words(page: str) -> str:
    return plain(page[page.index("<main>"):page.index("</main>")])


def section(page: str) -> str:
    begin = page.index('<section class="timeline"')
    return page[begin:page.index("</section>", begin)]


class DeclarationTests(TempDirTestCase):
    """The module checker explains a wrong `timeline` declaration in plain words, naming no module."""
    TABLES = '''[tables.pets]
title = "Pets"
columns.name = { type = "text", required = true }

[tables.treatments]
title = "Treatments"
columns.pet = { type = "link", to = "pets", required = true, on_delete = "cascade" }
columns.name = { type = "text", required = true }

[tables.log]
title = "Log"
columns.pet = { type = "link", to = "pets", required = true, on_delete = "cascade" }
columns.treatment = { type = "link", to = "treatments", required = true, on_delete = "cascade" }
columns.at = { type = "datetime", required = true }
columns.on = { type = "date" }
columns.weight = { type = "decimal", unit = "kg" }
columns.amount = { type = "decimal" }
columns.secret = { type = "text", sensitive = true }
columns.note = { type = "text" }
'''

    def load(self, extra: str, private: bool = False):
        tables = self.TABLES.replace('title = "Log"', 'title = "Log"\nprivate = true\nsuggestions = false') \
            if private else self.TABLES
        return modules.load_module(self.make_module(tables=tables + extra, labels=None))

    def problems(self, extra: str, private: bool = False) -> str:
        with self.assertRaises(modules.ModuleError) as caught:
            self.load(extra, private)
        return str(caught.exception)

    def test_a_good_timeline_is_kept_and_may_go_through_one_link(self):
        rule = self.load('[tables.log.timeline]\nwhen = "at"\nper = "treatment.pet"\nentry = ["dose", "doses"]\n'
                         'words = "{treatment}: {note}"\nlook = "done"\n').tables["log"].timeline
        self.assertEqual((rule["link"], rule["through"], rule["look"], rule["summarise"]),
                         ("treatment", "pet", "done", None))
        rule = self.load('[tables.log.timeline]\nwhen = "at"\nper = "pet"\nentry = ["a", "b"]\nchange = "weight"\n'
                         ).tables["log"].timeline
        self.assertEqual((rule["look"], rule["change"], rule["words"]), ("recorded", "weight", ""))

    def test_wrong_timelines_are_explained(self):
        text = self.problems('[tables.log.timeline]\nwhen = "on"\nper = "note"\nentry = ["one"]\n'
                             'words = "{secret} and {nothing} {"\nlook = "red"\nsummarise = "week"\ncolour = "red"\n'
                             'change = "amount"\n')
        for said in ("'when' must name a required date or date-and-time column",
                     "'per' must name a required link column", "'entry' must be two words",
                     "'{secret}' is not one", "'{nothing}' is not one", "a brace without its pair",
                     "'look' must be one of recorded, done, measured, visit", "'summarise' can only be \"day\"",
                     "unknown setting 'colour'", "'change' must name a number column of this table with its own unit"):
            self.assertIn(said, text)
        self.assertIn("'treatment' must point at a table of this module or of a module this one requires, and 'name' must be a required link",
                      self.problems('[tables.log.timeline]\nwhen = "at"\nper = "treatment.name"\n'
                                    'entry = ["a", "b"]\n'))
        self.assertIn("can't be used with summarise",
                      self.problems('[tables.log.timeline]\nwhen = "at"\nper = "pet"\nentry = ["a", "b"]\n'
                                    'change = "weight"\nsummarise = "day"\n'))

    def test_a_private_tables_timeline_says_only_how_many_each_day_and_never_a_private_column(self):
        base = '[tables.log.timeline]\nwhen = "at"\nper = "pet"\nentry = ["dose", "doses"]\n'
        self.assertIn("a private table's timeline must say summarise = \"day\"", self.problems(base, private=True))
        self.assertIn("a private table's timeline can't use 'change'",
                      self.problems(base + 'summarise = "day"\nchange = "weight"\n', private=True))
        self.assertIn("'{secret}' is not one",
                      self.problems(base + 'summarise = "day"\nwords = "{secret}"\n', private=True))
        kept = self.load(base + 'summarise = "day"\nwords = "{treatment}"\n', private=True).tables["log"].timeline
        self.assertEqual(kept["summarise"], "day")

    def test_shipped_modules_declare_what_this_decision_describes(self):
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        tables = {f"{m.name}__{t.name}": t for m in found for t in m.tables.values()}
        self.assertEqual(tables[WEIGH].timeline["change"], "weight")
        self.assertEqual(tables[GIVEN].timeline["per"], "treatment.pet")
        self.assertEqual(tables[FEED].timeline["summarise"], "day")
        doses = tables[DOSES].timeline
        self.assertEqual((doses["summarise"], doses["words"]), ("day", "{medication}"))
        for table in tables.values():
            for name in modules.TIMELINE_WORD.findall((table.timeline or {}).get("words", "")):
                self.assertFalse(table.columns[name].sensitive, "a private column is never on a timeline")


class TimelineTestCase(TempDirTestCase):
    MODULES = ("people", "stock", "pets", "pet_feeding")

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
        self.store = records.Records(self.conn, self.registry)
        settings.put(self.conn, daily.ZONE_KEY, "Australia/Sydney")
        self.rex = self.store.create(PETS, {"name": "Rex", "species": "dog"})

    def weigh(self, day, kg, pet=None):
        return self.store.create(WEIGH, {"pet": pet or self.rex, "day": day, "weight": kg})

    def feed(self, at, amount=None, unit=None):
        values = {"pet": self.rex, "given_at": at, "kind": "bowl", "food": "Example dry food"}
        if amount is not None:
            values.update(amount=amount, unit=unit)
        return self.store.create(FEED, values)

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: SYDNEY_NOON
        app.config["TODAY"] = lambda: TODAY
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None, status=200):
        response = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)


class PetTimelineTests(TimelineTestCase):
    def fill(self):
        self.weigh("2026-10-02", "4.4")
        self.weigh("2026-11-24", "4.7")
        self.store.create(VISITS, {"pet": self.rex, "day": "2026-10-20", "reason": "Yearly check-up"})
        treatment = self.store.create(TREAT, {"pet": self.rex, "name": "Example flea drops", "kind": "flea"})
        self.store.create(GIVEN, {"treatment": treatment, "given_on": "2026-11-01"})
        for clock in ("07:00", "12:00", "18:00"):
            self.feed(f"2026-11-24T{clock}", 80, "g")

    def test_the_pets_page_lists_every_kind_newest_first_under_month_headings(self):
        self.fill()
        page = self.page(f"/t/{PETS}/{self.rex}")
        self.assertIn("<h2>What happened, newest first</h2>", page)
        text = plain(section(page))
        order = [text.index(w) for w in (
            "November 2026", "Weigh-in · Tue 24 Nov · 4.7 kg", "3 feedings recorded on Tue 24 Nov · 240 g put out",
            "Treatment given · Sun 1 Nov · Example flea drops", "October 2026",
            "Vet visit · Tue 20 Oct · Yearly check-up", "Weigh-in · Fri 2 Oct · 4.4 kg")]
        self.assertEqual(order, sorted(order), text)
        self.assertIn("up 0.3 kg since 2 Oct, from 4.4 kg to 4.7 kg", text)
        self.assertEqual(text.count(" since "), 1, "the first weigh-in has nothing before it to compare with")

    def test_each_kind_has_its_own_symbol_beside_its_words_and_no_script(self):
        self.fill()
        part = section(self.page(f"/t/{PETS}/{self.rex}"))
        for look, symbol in (("measured", "◆"), ("visit", "■"), ("done", "✓"), ("recorded", "●")):
            self.assertIn(f'<span class="tl-mark tl-{look}" aria-hidden="true">{symbol}</span>', part)
        self.assertNotIn("<script", part)
        self.assertIn(f'href="/daily/{FEED}?subject={self.rex}&amp;day=2026-11-24"', part)
        self.assertRegex(part, r'aria-label="Open this weigh-in, Tue 24 Nov[^"]*"')
        self.assertNotIn("missed", part.lower().replace("it does not mean anything was missed", ""))

    def test_a_pet_with_nothing_recorded_says_so(self):
        part = section(self.page(f"/t/{PETS}/{self.rex}"))
        self.assertIn("Nothing recorded yet for Rex.", part)
        self.assertNotIn("Open the whole timeline", part)

    def test_only_accepted_undeleted_records_are_listed_and_the_change_follows(self):
        first = self.weigh("2026-10-02", "4.4")
        middle = self.weigh("2026-11-01", "5.0")
        self.weigh("2026-11-24", "4.7")
        text = plain(section(self.page(f"/t/{PETS}/{self.rex}")))
        self.assertIn("down 0.3 kg since 1 Nov", text)
        self.store.delete(WEIGH, middle)
        text = plain(section(self.page(f"/t/{PETS}/{self.rex}")))
        self.assertIn("up 0.3 kg since 2 Oct", text)
        self.assertNotIn("5 kg", text)
        self.conn.execute(f"UPDATE {WEIGH} SET review_status = 'suggested' WHERE id = ?", (first,))
        self.conn.commit()
        text = plain(section(self.page(f"/t/{PETS}/{self.rex}")))
        self.assertNotIn("4.4 kg", text)
        self.assertNotIn(" since ", text)
        other = self.store.create(PETS, {"name": "Luna", "species": "cat"})
        self.weigh("2026-11-20", "3.1", pet=other)
        self.assertNotIn("3.1 kg", plain(section(self.page(f"/t/{PETS}/{self.rex}"))))

    def test_earlier_pages_are_server_links_and_a_day_is_never_split(self):
        start = date(2026, 1, 1)
        for n in range(30):
            self.weigh((start + timedelta(days=n * 7)).isoformat(), f"{4 + n / 100:.2f}")
        client = self.client()
        panel = section(self.page(f"/t/{PETS}/{self.rex}", client))
        self.assertEqual(panel.count('class="tl-item"'), timeline.PANEL)
        self.assertIn(f'href="/timeline/{PETS}/{self.rex}"', panel)
        full = self.page(f"/timeline/{PETS}/{self.rex}", client)
        self.assertIn("<h1>What happened for Rex, newest first</h1>", full)
        self.assertEqual(section(full).count('class="tl-item"'), timeline.PAGE)
        found = re.search(r'href="(/timeline/[^"]+\?before=(\d{4}-\d\d-\d\d))" rel="prev">Earlier', full)
        self.assertIsNotNone(found)
        earlier = self.page(found.group(1), client)
        self.assertEqual(section(earlier).count('class="tl-item"'), 30 - timeline.PAGE)
        self.assertNotIn('rel="prev"', earlier)
        self.assertIn("Back to the newest", earlier)
        self.assertIn("Nothing recorded for Rex before 01/01/26.",
                      self.page(f"/timeline/{PETS}/{self.rex}?before=2026-01-01", client))
        self.page(f"/timeline/{PETS}/{self.rex}?before=not-a-day", client)  # read as the newest
        items = timeline.items(self.conn, self.registry, self.registry[PETS], self.rex)
        same_day = [timeline.Item(items[0].info, items[0].rule, date(2027, 1, 1), [{"id": 900 + n}])
                    for n in range(3)]
        shown, more = timeline.page(same_day + items, None, limit=2)
        self.assertEqual((len(shown), more), (3, date(2027, 1, 1)), "the rest of a day stays on its page")

    def test_a_missing_or_deleted_record_or_a_table_with_no_timeline_has_no_page(self):
        client = self.client()
        self.page(f"/timeline/{PETS}/999", client, status=404)
        self.page(f"/timeline/stock__items/1", client, status=404)
        reply = client.post(f"/timeline/{PETS}/{self.rex}", base_url=BASE, data={"_csrf": client.csrf})
        self.assertEqual(reply.status_code, 404, "only a timeline with private entries has a Show to press")
        self.store.delete(PETS, self.rex)
        self.page(f"/timeline/{PETS}/{self.rex}", client, status=404)

    def test_a_module_switched_off_takes_its_lines_away_and_keeps_its_records(self):
        self.fill()
        settings.set_module_enabled(self.conn, "pet_feeding", False)
        text = plain(section(self.page(f"/t/{PETS}/{self.rex}")))
        self.assertNotIn("feedings recorded", text)
        self.assertIn("Weigh-in", text)
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {FEED}").fetchone()[0], 3)
        settings.set_module_enabled(self.conn, "pet_feeding", True)
        self.assertIn("3 feedings recorded", plain(section(self.page(f"/t/{PETS}/{self.rex}"))))
        settings.set_module_enabled(self.conn, "pets", False)
        self.page(f"/timeline/{PETS}/{self.rex}", status=404)

    def test_the_styles_cover_dark_mode_print_high_contrast_and_a_phone(self):
        css = (ROOT / "src" / "dashboard" / "web" / "templates" / "base.html").read_text(encoding="utf-8")
        for rule in (".tl-item { display: flex; gap: .45rem; align-items: baseline; margin: .35rem 0; "
                     "overflow-wrap: anywhere; }", "@media (forced-colors: active) { .tl-mark { border-color: "
                     "CanvasText; } }", "@media print { .tl-nav, .timeline form { display: none; }",
                     ".tl-measured { background: var(--cal-due);"):
            self.assertIn(rule, css)


class DoseTimelineTests(DoseTestCase):
    """A person's doses: one line a day with how many, before Show; which medicine after a pressed Show; never the
    amount or who gave it."""

    def setUp(self):
        super().setUp()
        self.dose(at="2026-11-24T08:00:00", amount=AMOUNT, unit="drop")
        self.dose(at="2026-11-24T13:00:00")
        self.dose(med=self.med2, at="2026-11-24T20:00:00")
        self.web = self.client()
        self.path = f"/timeline/people__people/{self.rosa}"

    def test_before_show_a_day_says_only_how_many_doses(self):
        for path in (f"/t/people__people/{self.rosa}", self.path, f"{self.path}?show=1"):
            page = self.page(path, self.web)
            main = page[page.index("<main>"):]
            for secret in (SECRET, "Invented eye drops", AMOUNT, "Medication #", "Maria Garcia"):
                self.assertNotIn(secret, main, f"{path}: {secret}")
            self.assertIn("3 doses recorded on Tue 24 Nov", words(page))
            self.assertIn("data-show-timeline", page)
            self.assertNotIn(f"/t/{DOSES}/", section(page), "no dose's own page is linked")

    def test_show_is_a_pressed_button_that_names_each_medicine_but_never_an_amount_or_giver(self):
        reply = self.post(self.web, self.path)
        self.assertEqual(reply.status_code, 200)
        text = words(reply.get_data(as_text=True))
        self.assertIn(f"8:00 am · {SECRET}", text)
        self.assertIn(f"8:00 pm · Invented eye drops", text)
        self.assertIn("Hide details", text)
        for never in (AMOUNT, "7.25 drops", "Maria Garcia"):
            self.assertNotIn(never, text)
        refused = self.web.post(self.path, base_url=BASE)
        self.assertIn(refused.status_code, (400, 403), "no session check: refused")

    def test_a_person_with_nothing_recorded_and_doses_switched_off(self):
        self.assertIn("Nothing recorded yet for Sofia Garcia.", self.page(f"/t/people__people/{self.sofia}", self.web))
        settings.set_module_enabled(self.conn, "medicine_doses", False)
        client = self.client()
        self.assertNotIn("What happened", self.page(f"/t/people__people/{self.rosa}", client))
        self.page(self.path, client, status=404)
        self.assertEqual(self.post(client, self.path).status_code, 404)
        self.assertEqual(self.count(), 3, "records are kept while the module is off")
