"""Tests for loading module folders and the plain-language problems they report."""
from support import DEMO_MODULE, DEMO_TABLES, TempDirTestCase
from dashboard.core import modules


class ModuleLoadingTests(TempDirTestCase):
    def problems(self, **kwargs):
        folder = self.make_module(**kwargs)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " | ".join(caught.exception.problems)

    def test_valid_module_loads(self):
        module = modules.load_module(self.make_module())
        self.assertEqual(module.name, "demo")
        things = module.tables["things"]
        self.assertEqual([c.key for c in things.columns["kind"].choices], ["tool", "food", "first_aid"])
        self.assertEqual(things.columns["kind"].choices[2].label, "First aid")
        self.assertEqual(things.columns["quantity"].unit, "kg")

    def test_missing_module_file(self):
        folder = self.make_module()
        (folder / "module.toml").unlink()
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        self.assertIn("module.toml is missing", caught.exception.problems[0])

    def test_folder_and_name_must_match(self):
        self.assertIn("must match", self.problems(module=DEMO_MODULE.replace('name = "demo"', 'name = "other"')))

    def test_wrong_core_api(self):
        self.assertIn("different version", self.problems(module=DEMO_MODULE.replace('core_api = "1"', 'core_api = "2"')))

    def test_unknown_type_suggests_the_closest(self):
        text = self.problems(tables=DEMO_TABLES.replace('type = "measure"', 'type = "measur"'))
        self.assertIn("unknown type 'measur'", text)
        self.assertIn("Did you mean 'measure'", text)
        self.assertIn("table 'things', column 'quantity'", text)

    def test_unknown_setting_suggests_the_closest(self):
        text = self.problems(tables=DEMO_TABLES.replace("required = true }", "requred = true }", 1))
        self.assertIn("Did you mean 'required'", text)

    def test_choice_needs_choices(self):
        text = self.problems(tables='[tables.a]\ntitle = "A"\ncolumns.k = { type = "choice" }\n')
        self.assertIn("'choices' must be a non-empty list", text)

    def test_choice_keys_are_words(self):
        text = self.problems(tables='[tables.a]\ntitle = "A"\ncolumns.k = { type = "choice", choices = ["Dry food"] }\n')
        self.assertIn("lower-case", text)

    def test_link_to_unknown_table(self):
        text = self.problems(tables=DEMO_TABLES.replace('to = "owners", on_delete', 'to = "ownrs", on_delete'))
        self.assertIn("Did you mean 'owners'", text)

    def test_link_to_another_module_needs_requires(self):
        text = self.problems(tables='[tables.a]\ntitle = "A"\ncolumns.p = { type = "link", to = "people.people" }\n')
        self.assertIn("requires", text)

    def test_system_column_names_are_reserved(self):
        self.assertIn("added automatically", self.problems(tables='[tables.a]\ntitle = "A"\ncolumns.id = { type = "integer" }\n'))

    def test_min_only_for_numbers(self):
        self.assertIn("only applies to number", self.problems(tables='[tables.a]\ntitle = "A"\ncolumns.n = { type = "text", min = 1 }\n'))

    def test_declarative_module_cannot_contact_hosts(self):
        text = self.problems(module=DEMO_MODULE.replace("outbound_hosts = []", 'outbound_hosts = ["api.example.com"]'))
        self.assertIn("cannot contact anything", text)

    def test_labels_must_match_tables(self):
        text = self.problems(labels='[tables.things]\nform = ["nmae"]\n')
        self.assertIn("Did you mean 'name'", text)

    def test_broken_toml_is_explained(self):
        self.assertIn("could not be read", self.problems(tables="[tables.a\n"))

    def test_discover_isolates_broken_modules_and_orders_by_requirement(self):
        self.make_module("base")
        self.make_module("addon", module=DEMO_MODULE.replace("requires = []", 'requires = ["base"]'))
        self.make_module("broken", tables="[tables.a\n")
        self.make_module("orphan", module=DEMO_MODULE.replace("requires = []", 'requires = ["broken"]'))
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual([m.name for m in found], ["base", "addon"])
        self.assertIn("broken", failures)
        self.assertIn("problems of its own", " ".join(failures["orphan"]))

    def test_requirement_loop_is_reported(self):
        self.make_module("a", module=DEMO_MODULE.replace("requires = []", 'requires = ["b"]'))
        self.make_module("b", module=DEMO_MODULE.replace("requires = []", 'requires = ["a"]'))
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual(found, [])
        self.assertIn("loop", " ".join(failures["a"] + failures["b"]))
