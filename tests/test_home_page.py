"""Tests for the grouped home page: one group per area, main lists large, other lists as links, all reachable."""
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup
from dashboard.web.app import create_app
from dashboard.web.home import HOUSEHOLD_FIRST, home_groups, home_places
import make_migration

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
ZEBRA = '''name = "demo"
title = "Aardvark notes"
version = "1.0.0"
description = "A made-up module for tests."
core_api = "1"
kind = "declarative"
requires = []
outbound_hosts = []
'''
TABLES = '''[tables.first]
title = "First list"
columns.name = { type = "text", required = true }

[tables.second]
title = "Second list"
columns.name = { type = "text", required = true }

[tables.third]
title = "Third list"
columns.name = { type = "text", required = true }
'''


class HomePlacesTests(TempDirTestCase):
    def places(self, labels):
        return home_places(modules.load_module(self.make_module(tables=TABLES, labels=labels)))

    def test_first_table_is_main_when_nothing_is_said(self):
        self.assertEqual(self.places(None), {"first": "main", "second": "more", "third": "more"})

    def test_a_table_that_says_main_replaces_the_first(self):
        self.assertEqual(self.places('[tables.second]\nhome = "main"\n'),
                         {"first": "more", "second": "main", "third": "more"})

    def test_two_tables_can_be_main(self):
        self.assertEqual(self.places('[tables.first]\nhome = "main"\n[tables.third]\nhome = "main"\n'),
                         {"first": "main", "second": "more", "third": "main"})

    def test_first_says_more_so_the_next_is_main(self):
        self.assertEqual(self.places('[tables.first]\nhome = "more"\n'),
                         {"first": "more", "second": "main", "third": "more"})

    def test_a_wrong_word_is_explained_in_plain_language(self):
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(self.make_module(tables=TABLES, labels='[tables.first]\nhome = "hidden"\n'))
        text = str(caught.exception)
        self.assertIn("In labels.toml, table 'first': 'home' must be \"main\"", text)
        self.assertIn("or \"more\"", text)
        self.assertIn("not 'hidden'", text)

    def test_home_is_a_known_label_key(self):
        self.assertIn("home", modules.LABEL_TABLE_KEYS)


class HomePageTests(TempDirTestCase):
    """The real modules, all switched on, plus one made-up module to check where newcomers go."""

    def setUp(self):
        super().setUp()
        for name in HOUSEHOLD_FIRST:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        make_migration.make(self.make_module(name="zebra", module=ZEBRA, tables=TABLES, labels=None), "first_tables")
        make_migration.make(self.make_module(name="garden", module=ZEBRA.replace("Aardvark notes", "Garden"),
                                             tables=TABLES, labels=None), "first_tables")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        settings.put(self.conn, "setup.done", True)
        self.registry = records.build_registry(self.report.loaded)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        self.client = app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def page(self):
        response = self.client.get("/", base_url=BASE)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_one_heading_per_area_household_first_then_a_to_z(self):
        headings = re.findall(r'<h2 id="area-[a-z_]+">([^<]+)</h2>', self.page())
        self.assertEqual(headings, ["People", "Household stock", "Home layout", "Medical readiness", "Pets",
                                    "Aardvark notes", "Garden"])

    def test_every_switched_on_table_is_reachable_from_home(self):
        page = self.page()
        for name in self.registry:
            self.assertIn(f'href="/t/{name}"', page, f"{name} has no link on the home page")
        self.assertEqual(len(re.findall(r'href="/t/[a-z_]+"', page)), len(self.registry), "each list is linked once")

    def test_only_main_lists_get_an_add_button(self):
        page = self.page()
        added = set(re.findall(r'href="/t/([a-z_]+)/new" aria-label="Add to ', page))
        self.assertEqual(added, {"people__people", "stock__items", "home_layout__exits", "home_layout__shutoffs",
                                 "medical__kits", "pets__pets", "zebra__first", "garden__first"})
        self.assertLess(len(added), len(self.registry) / 2, "most lists are compact links, not tiles")

    def test_groups_carry_their_own_lists_counts_and_sheets(self):
        store = records.Records(self.conn, self.registry)
        store.create("pets__pets", {"name": "Rex", "species": "dog"})
        from dashboard.web.sheets import available_sheets
        groups = {g["name"]: g for g in home_groups(self.registry, store.count, available_sheets(self.registry))}
        pets = groups["pets"]
        self.assertEqual([(t["name"], t["count"]) for t in pets["main"]], [("pets__pets", 1)])
        self.assertEqual([t["name"] for t in pets["more"]],
                         ["pets__treatments", "pets__given", "pets__weigh_ins", "pets__vet_visits"])
        self.assertEqual([s["title"] for s in pets["sheets"]], ["Pet details"])
        self.assertEqual([s["name"] for s in groups["people"]["sheets"]], ["emergency", "emergency_medical"])
        self.assertEqual([t["name"] for t in groups["stock"]["main"]], ["stock__items"])

    def test_print_links_sit_in_their_area_and_keep_their_words(self):
        page = self.page()
        people = page[page.index('id="area-people"'):page.index('id="area-stock"')]
        self.assertIn('<a href="/sheet/people/emergency">Print: Emergency sheet (fridge copy)</a>', people)
        self.assertNotIn("/sheet/stock/", people)
        self.assertEqual(len(re.findall(r'href="/sheet/', page)), 6)

    def test_friendly_titles_replace_the_technical_module_names(self):
        page = self.page()
        self.assertIn("You are tracking: People, Household stock, Home layout, Medical readiness, Pets, "
                      "Aardvark notes, Garden.", page)
        self.assertNotIn("Modules in use", page)
        self.assertNotIn("home_layout,", page)

    def test_pages_let_the_browser_say_a_form_came_from_here(self):
        # "no-referrer" makes browsers send "Origin: null" with a form, which the program refuses.
        response = self.client.get("/", base_url=BASE)
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        refused = self.client.post("/t/zebra__first/new", data={"name": "x"}, base_url=BASE, headers={"Origin": "null"})
        self.assertEqual(refused.status_code, 403)

    def test_a_switched_off_area_disappears_with_its_lists(self):
        settings.set_module_enabled(self.conn, "pets", False)
        page = self.page()
        self.assertNotIn('id="area-pets"', page)
        self.assertNotIn("/t/pets__", page)
        self.assertIn('id="area-people"', page)
