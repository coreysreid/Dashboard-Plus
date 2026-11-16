"""Tests for suggestions while typing: matching, the household's own records first, and module catalogues."""
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, suggest
from dashboard.web.app import create_app

PORT = 5129
BASE = f"http://127.0.0.1:{PORT}"
CATALOGUE = [
    {"name": "Kidney beans", "also": ["canned kidney beans", "tinned kidney beans"], "fills": {"unit": "tins"}},
    {"name": "Baked beans", "also": [], "fills": {}},
    {"name": "Bell pepper", "also": ["capsicum"], "fills": {}},
    {"name": "Crème fraîche", "also": [], "fills": {}},
]


class MatchingTests(TempDirTestCase):
    def names(self, typed, own=()):
        return [s["name"] for s in suggest.suggestions(typed, list(own), CATALOGUE)]

    def test_start_of_name_then_any_word_then_other_names(self):
        self.assertEqual(self.names("kid"), ["Kidney beans"])
        self.assertEqual(self.names("beans"), ["Baked beans", "Kidney beans"])
        self.assertEqual(self.names("capsicum"), ["Bell pepper"])
        self.assertEqual(self.names("tinned kid"), ["Kidney beans"])

    def test_case_accents_and_punctuation_do_not_matter(self):
        self.assertEqual(self.names("CREME-FRAICHE"), ["Crème fraîche"])
        self.assertEqual(self.names(""), [])

    def test_the_households_own_record_comes_first_and_is_not_offered_twice(self):
        found = suggest.suggestions("kid", [{"id": 7, "name": "Kidney beans"}], CATALOGUE)
        self.assertEqual(found, [{"name": "Kidney beans", "existing_id": 7}])


class StockCatalogueTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("people", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        self.client = app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def test_the_stock_catalogue_loads_and_fills_category_unit_and_drinking(self):
        catalogue = self.registry["stock__items"].module.catalogues[("items", "name")]
        self.assertGreater(len(catalogue), 700)
        found = self.get("/t/stock__items/suggest?column=name&q=kid").get_json()
        self.assertEqual(found[0]["name"], "Kidney beans")
        self.assertEqual(found[0]["fills"]["category"], "pantry")
        water = self.get("/t/stock__items/suggest?column=name&q=distilled").get_json()[0]
        self.assertFalse(water["fills"]["drinking"])

    def test_an_item_already_recorded_is_offered_first(self):
        item = self.records.create("stock__items", {"name": "Kidney beans", "quantity": 3})
        found = self.get("/t/stock__items/suggest?column=name&q=kidn").get_json()
        self.assertEqual(found[0], {"name": "Kidney beans", "existing_id": item})

    def test_the_form_offers_suggestions_and_long_lists_get_a_find_box(self):
        form = self.get("/t/stock__items/new").get_data(as_text=True)
        self.assertIn('data-suggest="/t/stock__items/suggest?column=name"', form)
        for i in range(10):
            self.records.create("stock__items", {"name": f"Thing {i}"})
        form = self.get("/t/stock__movements/new").get_data(as_text=True)
        self.assertIn('data-find-for="f-item"', form)
        self.assertIn('data-add-new="/t/stock__items/new?name="', form)

    def test_suggestions_only_for_text_columns(self):
        self.assertEqual(self.get("/t/stock__items/suggest?column=quantity&q=1").status_code, 404)

    def test_a_catalogue_must_be_a_csv_in_the_module(self):
        labels = self.tmp / "modules" / "stock" / "labels.toml"
        labels.write_text(labels.read_text(encoding="utf-8").replace('suggest_from = "catalogue.csv"',
                                                                     'suggest_from = "../secrets.csv"'),
                          encoding="utf-8")
        _, failures = modules.discover(self.tmp / "modules")
        self.assertIn("suggest_from must name a .csv file in the module folder", " ".join(failures["stock"]))

    def test_places_are_suggested_while_typing(self):
        found = self.get("/t/stock__places/suggest?column=name&q=pan").get_json()
        self.assertIn("Pantry", [f["name"] for f in found])
