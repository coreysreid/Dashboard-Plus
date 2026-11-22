"""Tests for optional links between modules (decision 0115): Utilities works without Our home and keeps an exact meter link while it is off.

They automate the checks in Lane B's optional links draft (its ACCEPTANCE.md, now in git history) that apply before Bills is promoted,
with Utilities as the first module that uses `optional_requires`."""
import io
import json
import shutil
import zipfile
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import (backups, csv_import, db, export, helpers, modules, proposals, records, restore, schema,
                            settings, startup, sync)
from dashboard.core.proposals import ProposalError
from dashboard.web.app import create_app

PORT = 5139
BASE = f"http://127.0.0.1:{PORT}"
SERVICES = "utilities__services"
OFF_HELP = "Meter places are available if you switch on Our home. You can save this service without one."
KEPT_HELP = "A meter link is saved. Switch on Our home to see or change it."
KEPT = "Meter link saved; switch on Our home to see it."
NONE = "No meter place linked."
GONE = "The linked meter is no longer there."
MISSING = "The linked meter is no longer there. Choose another, or leave it blank."
PATH = "Electricity meter — Kitchen › Cupboard"


class OptionalLinkCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "utilities")

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        settings.put(self.conn, "setup.done", True)
        self.app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT

    # ----- helpers -----------------------------------------------------------------------------------------
    def switch(self, **on):
        for name, value in on.items():
            settings.set_module_enabled(self.conn, name, value)

    def store(self) -> records.Records:
        """Records with the tables a page would see now: modules switched on whose requirements are on."""
        on = settings.enabled_modules(self.conn)
        loaded = [m for m in self.report.loaded if m.name in on]
        while True:
            names = {m.name for m in loaded}
            kept = [m for m in loaded if all(r in names for r in m.requires)]
            if len(kept) == len(loaded):
                break
            loaded = kept
        return records.Records(self.conn, records.build_registry(loaded))

    def client(self):
        client = self.app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = self.app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None):
        reply = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(reply.status_code, 200, path)
        return reply.get_data(as_text=True)

    def post(self, path, data, client=None):
        client = client or self.client()
        return client.post(path, data={"_csrf": client.csrf, **data}, base_url=BASE)

    def meter_in_cupboard(self, name="Electricity meter"):
        store = self.store()
        kitchen = store.create("stock__places", {"name": "Kitchen"})
        cupboard = store.create("stock__places", {"name": "Cupboard", "inside": kitchen})
        return store.create("home_layout__meters", {"name": name, "kind": "electricity", "place": cupboard})

    def saved_meter(self, service):
        return self.conn.execute(f"SELECT meter FROM {SERVICES} WHERE id = ?", (service,)).fetchone()[0]

    def row(self, service):
        return tuple(self.conn.execute(f"SELECT * FROM {SERVICES} WHERE id = ?", (service,)).fetchone())

    def export_files(self):
        raw = export.build(self.conn, self.store().registry, __version__,
                           now=datetime(2026, 11, 22, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return {n: archive.read(n).decode("utf-8-sig") for n in archive.namelist()}

    def helper_get(self, path, key, client=None):
        reply = (client or self.client()).get(path, base_url=BASE, headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(reply.status_code, 200, path)
        return reply.get_data(as_text=True)

    def linked_service(self):
        """Our home on: an electricity service linked to a meter in Kitchen › Cupboard."""
        meter = self.meter_in_cupboard()
        service = self.store().create(SERVICES, {"name": "Home electricity", "kind": "electricity", "meter": meter})
        return service, meter


class UtilitiesAloneTests(OptionalLinkCase):
    def setUp(self):
        super().setUp()
        self.switch(stock=False, home_layout=False)  # People and Utilities only: an internet-only household

    def test_1_settings_switches_utilities_on_without_our_home_and_nothing_else(self):
        self.switch(utilities=False)
        reply = self.post("/settings", {"modules": ["people", "utilities"], "people": "2", "week_starts": "monday",
                                        "distance_unit": "km"})
        self.assertEqual(reply.status_code, 302, reply.get_data(as_text=True)[:400])
        self.assertEqual(settings.enabled_modules(self.conn), {"people", "utilities"})
        self.assertIn(f"/t/{SERVICES}", self.page("/"))

    def test_1_the_add_form_has_no_meter_picker_and_says_why_before_save(self):
        form = self.page(f"/t/{SERVICES}/new")
        self.assertIn(OFF_HELP, form)
        self.assertNotIn('name="meter"', form)
        self.assertNotIn("Type to find", form.split(OFF_HELP)[0].split("Meter in Our home")[-1])
        self.assertLess(form.index(OFF_HELP), form.index("Save and add another"))
        self.assertIn('id="f-meter-note" tabindex="0"', form)  # reached by keyboard, next to the missing picker
        self.assertNotIn("Add one in a new tab", form.split("Meter in Our home")[1].split("Notes")[0])

    def test_2_services_without_a_meter_save_and_say_no_meter_place_is_linked(self):
        client = self.client()
        for name, kind in (("Home internet", "internet"), ("Home electricity", "electricity")):
            reply = self.post(f"/t/{SERVICES}/new", {"name": name, "kind": kind, "then": "done"}, client)
            self.assertEqual(reply.status_code, 302, reply.get_data(as_text=True)[:400])
        power = self.conn.execute(f"SELECT id, meter FROM {SERVICES} WHERE name = 'Home electricity'").fetchone()
        self.assertIsNone(power["meter"])
        shown = self.page(f"/t/{SERVICES}/{power['id']}", client)
        self.assertIn(NONE, shown)
        self.assertIn(OFF_HELP, shown)
        listed = self.page(f"/t/{SERVICES}", client)
        self.assertNotIn(NONE, listed)  # no meter gap on the list: internet has none
        self.assertEqual(self.page("/sheet/utilities/utility_contacts", client).count("Home internet"), 1)
        self.assertEqual(settings.enabled_modules(self.conn), {"people", "utilities"})

    def test_a_record_can_not_get_a_meter_while_our_home_is_off(self):
        self.switch(stock=True, home_layout=True)
        meter = self.meter_in_cupboard()
        self.switch(stock=False, home_layout=False)
        store = self.store()
        with self.assertRaises(records.ValidationError) as caught:
            store.create(SERVICES, {"name": "Forged", "kind": "electricity", "meter": meter})
        self.assertIn("meter", caught.exception.problems)
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {SERVICES}").fetchone()[0], 0)
        made = store.create(SERVICES, {"name": "Plain", "kind": "electricity", "meter": ""})  # a blank is fine
        self.assertIsNone(self.saved_meter(made))
        reply = self.post(f"/t/{SERVICES}/new", {"name": "Crafted", "kind": "gas", "meter": str(meter), "then": "done"})
        self.assertEqual(reply.status_code, 302)  # the form never reads a picker that is not there
        self.assertIsNone(self.conn.execute(f"SELECT meter FROM {SERVICES} WHERE name = 'Crafted'").fetchone()[0])


class LinkKeptWhileOffTests(OptionalLinkCase):
    def test_3_the_full_path_shows_while_on_and_nothing_of_our_home_shows_while_off(self):
        service, meter = self.linked_service()
        client = self.client()
        for path in (f"/t/{SERVICES}/{service}", f"/t/{SERVICES}", "/sheet/utilities/utility_contacts"):
            self.assertIn(PATH, self.page(path, client), path)
        self.switch(home_layout=False)
        self.assertEqual(self.saved_meter(service), meter)
        _, key = helpers.issue(self.conn, self.data, "Utilities reader", "read", ["utilities"])
        record_page = self.page(f"/t/{SERVICES}/{service}", client)
        self.assertIn(KEPT_HELP, record_page)
        self.assertNotIn('name="meter"', record_page)
        for path in (f"/t/{SERVICES}", "/sheet/utilities/utility_contacts"):
            self.assertIn(KEPT, self.page(path, client), path)
        surfaces = {path: self.page(path, client) for path in
                    (f"/t/{SERVICES}/{service}", f"/t/{SERVICES}", f"/t/{SERVICES}/rows?offset=0",
                     "/sheet/utilities/utility_contacts", "/")}
        surfaces.update({path: self.helper_get(path, key, client) for path in
                         ("/api/v1/tables", f"/api/v1/tables/{SERVICES}/records",
                          f"/api/v1/tables/{SERVICES}/records/{service}", "/api/v1/guide")})
        surfaces.update({n: t for n, t in self.export_files().items() if n.startswith("utilities__")})
        for where, text in surfaces.items():
            for hidden in ("Electricity meter", "Kitchen", "Cupboard"):
                self.assertNotIn(hidden, text, f"{hidden} in {where}")
        spec = json.loads(surfaces["/api/v1/tables"])["tables"][0]
        self.assertNotIn("meter", [c["name"] for c in spec["columns"]])
        self.assertNotIn("meter", json.loads(surfaces[f"/api/v1/tables/{SERVICES}/records"])["records"][0]["values"])
        csv_text = surfaces[f"{SERVICES}.csv"]
        self.assertIn(KEPT, csv_text)
        self.assertIn(f",{meter},", csv_text)  # the exact ID is kept for recovery, marked as a saved link

    def test_3_sorting_never_follows_a_hidden_link(self):
        self.linked_service()
        self.switch(home_layout=False)
        page = self.page(f"/t/{SERVICES}?sort=meter")
        self.assertIn("<th>Meter in Our home</th>", page)  # a plain heading, not a sort link
        self.assertNotIn("?sort=meter", page)
        self.assertIn('href="?sort=name"', page)
        store = self.store()
        self.assertEqual(store.off_links(store.info(SERVICES)), {"meter"})

    def test_4_editing_other_fields_keeps_the_link_and_a_different_meter_is_refused(self):
        service, meter = self.linked_service()
        other = self.store().create("home_layout__meters", {"name": "Second meter", "kind": "gas"})
        self.switch(home_layout=False)
        reply = self.post(f"/t/{SERVICES}/{service}", {"name": "Home electricity", "kind": "electricity",
                                                       "notes": "Invented note", "meter": str(other)})
        self.assertEqual(reply.status_code, 302, reply.get_data(as_text=True)[:400])
        self.assertEqual(self.saved_meter(service), meter)
        store = self.store()
        provider = store.create("people__people", {"name": "Example Energy"})
        store.update(SERVICES, service, {"provider": provider})
        store.update(SERVICES, service, {"meter": meter})  # the same ID changes nothing
        self.assertEqual(self.saved_meter(service), meter)
        for forged in (other, None, "", str(other)):
            with self.subTest(forged=forged), self.assertRaises(records.ValidationError) as caught:
                store.update(SERVICES, service, {"meter": forged, "notes": "Changed"})
            self.assertIn("switched off", caught.exception.problems["meter"])
        with self.assertRaises(records.ValidationError):
            store.clean(store.info(SERVICES), {"meter": meter}, creating=False)
        self.assertEqual(self.saved_meter(service), meter)
        self.switch(home_layout=True)
        self.assertIn(PATH, self.page(f"/t/{SERVICES}/{service}"))
        self.assertIn(f'value="{meter}" selected', self.page(f"/t/{SERVICES}/{service}"))

    def test_off_and_on_cycles_and_a_restart_never_change_the_saved_link(self):
        service, meter = self.linked_service()
        before = self.row(service)
        for _ in range(3):
            self.switch(home_layout=False, stock=False)
            self.assertIn(KEPT, self.page(f"/t/{SERVICES}"))
            self.switch(home_layout=True, stock=True)
            self.assertIn(PATH, self.page(f"/t/{SERVICES}"))
        self.assertEqual(self.row(service), before)
        self.switch(home_layout=False)
        self.conn.close()
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.assertEqual(self.row(service), before)
        self.switch(home_layout=True)
        self.assertEqual(self.store().get(SERVICES, service)["meter"], meter)

    def test_switching_utilities_on_first_and_our_home_later_links_the_same_meter(self):
        self.switch(stock=False, home_layout=False)
        service = self.store().create(SERVICES, {"name": "Home electricity", "kind": "electricity"})
        self.switch(stock=True, home_layout=True)
        form = self.page(f"/t/{SERVICES}/{service}")
        self.assertIn('name="meter"', form)
        self.assertNotIn(OFF_HELP, form)
        meter = self.meter_in_cupboard()
        reply = self.post(f"/t/{SERVICES}/{service}", {"name": "Home electricity", "kind": "electricity",
                                                       "meter": str(meter)})
        self.assertEqual(reply.status_code, 302, reply.get_data(as_text=True)[:400])
        self.assertEqual(self.saved_meter(service), meter)
        self.assertIn(PATH, self.page(f"/t/{SERVICES}/{service}"))

    def test_restoring_a_backup_keeps_the_exact_link_while_our_home_is_off(self):
        service, meter = self.linked_service()
        self.switch(home_layout=False)
        backups.daily(self.data, today=date(2026, 11, 22))
        self.store().update(SERVICES, service, {"name": "Renamed later"})
        self.conn.close()
        chosen = restore.get({"data": self.data / "backups"}, "data", "daily-2026-11-22.db")
        restore.restore(self.data, chosen, self.report.loaded)
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.assertEqual(self.conn.execute(f"SELECT name, meter FROM {SERVICES}").fetchone()[:], ("Home electricity", meter))


class RepairTests(OptionalLinkCase):
    def test_5_a_deleted_meter_asks_for_repair_and_is_never_replaced_by_a_same_named_one(self):
        service, meter = self.linked_service()
        self.switch(utilities=False)  # Utilities off: deleting the meter cannot clear the service's link
        store = self.store()
        store.delete("home_layout__meters", meter)
        twin = store.create("home_layout__meters", {"name": "Electricity meter", "kind": "electricity",
                                                    "place": store.get("home_layout__meters", meter,
                                                                       include_deleted=True)["place"]})
        self.switch(utilities=True)
        self.assertEqual(self.saved_meter(service), meter)
        client = self.client()
        form = self.page(f"/t/{SERVICES}/{service}", client)
        self.assertIn(MISSING, form)
        self.assertIn(f'<option value="{twin}" >', form)  # offered, never chosen for the person
        self.assertNotIn(" selected>", form.split('name="meter"')[1].split("</select>")[0])
        self.assertNotIn("(deleted)", form)
        for path in (f"/t/{SERVICES}", "/sheet/utilities/utility_contacts"):
            text = self.page(path, client)
            self.assertIn(GONE, text, path)
            self.assertNotIn(PATH, text, path)
        csv_text = self.export_files()[f"{SERVICES}.csv"]
        self.assertIn(GONE, csv_text)
        self.assertIn(f",{meter},", csv_text)
        with self.assertRaises(records.ValidationError):  # the gone ID itself can't be saved again
            self.store().update(SERVICES, service, {"meter": meter})
        self.store().update(SERVICES, service, {"name": "Home electricity 2"})  # other fields keep repair state
        self.assertEqual(self.saved_meter(service), meter)
        reply = self.post(f"/t/{SERVICES}/{service}", {"name": "Home electricity", "kind": "electricity",
                                                       "meter": str(twin)}, client)
        self.assertEqual(reply.status_code, 302)
        self.assertEqual(self.saved_meter(service), twin)  # the person chose it

    def test_5_clearing_a_gone_link_is_a_deliberate_save(self):
        service, meter = self.linked_service()
        self.switch(utilities=False)
        self.store().delete("home_layout__meters", meter)
        self.switch(utilities=True)
        reply = self.post(f"/t/{SERVICES}/{service}", {"name": "Home electricity", "kind": "electricity", "meter": ""})
        self.assertEqual(reply.status_code, 302)
        self.assertIsNone(self.saved_meter(service))
        self.assertNotIn(MISSING, self.page(f"/t/{SERVICES}/{service}"))

    def test_a_live_delete_still_clears_as_decision_0099_says_and_restore_brings_it_back(self):
        service, meter = self.linked_service()
        self.store().delete("home_layout__meters", meter)
        self.assertIsNone(self.saved_meter(service))
        self.store().restore("home_layout__meters", meter)
        self.assertEqual(self.saved_meter(service), meter)


class HelperImportAndSyncTests(OptionalLinkCase):
    def entry(self, **values):
        return {"table": SERVICES, "values": {"name": "Home gas", "kind": "gas", **values}}

    def send(self, helper, *entries, key="k-1"):
        return proposals.submit(self.conn, self.store().registry, helper,
                                {"request_key": key, "why": "Invented test suggestion.", "entries": list(entries)})

    def test_9_a_helper_with_both_lists_may_suggest_a_live_meter_and_nothing_else_may(self):
        meter = self.meter_in_cupboard()
        both, _ = helpers.issue(self.conn, self.data, "Both lists", "suggest", ["utilities", "home_layout"])
        only, _ = helpers.issue(self.conn, self.data, "Utilities only", "suggest", ["utilities"])
        result, created = self.send(both, self.entry(meter=meter))
        self.assertTrue(created)
        table, made = proposals.accept(self.conn, self.store().registry, result["proposals"][0]["id"])
        self.assertEqual(self.saved_meter(made), meter)
        with self.assertRaises(ProposalError) as caught:
            self.send(only, self.entry(meter=meter), key="k-2")
        self.assertEqual(caught.exception.status, 403)
        with self.assertRaises(ProposalError):  # a forged ID that is no meter at all
            self.send(both, self.entry(meter=meter + 500), key="k-3")
        self.switch(home_layout=False)
        with self.assertRaises(ProposalError) as caught:
            self.send(both, self.entry(meter=meter), key="k-4")
        self.assertEqual(caught.exception.status, 403)
        result, _ = self.send(both, self.entry(), key="k-5")  # without the link it is an ordinary suggestion
        self.assertEqual(result["state"], "waiting")

    def test_9_a_suggestion_waiting_when_our_home_goes_off_can_not_bring_its_meter_in(self):
        meter = self.meter_in_cupboard()
        both, _ = helpers.issue(self.conn, self.data, "Both lists", "suggest", ["utilities", "home_layout"])
        result, _ = self.send(both, self.entry(meter=meter))
        self.switch(home_layout=False)
        with self.assertRaises(Exception):
            proposals.accept(self.conn, self.store().registry, result["proposals"][0]["id"])
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {SERVICES}").fetchone()[0], 0)

    def test_9_a_spreadsheet_import_can_not_assign_a_meter_while_our_home_is_off(self):
        self.switch(home_layout=False, stock=False)
        store = self.store()
        info = store.info(SERVICES)
        reason = csv_import.why_not_column(store, info, info.table.columns["meter"])
        self.assertEqual(reason, "Meter in Our home links to a part of your records that is switched off.")
        self.assertNotIn("meter", [c.name for c in csv_import.fields(store, info)[0]])

    def test_10_the_change_log_and_snapshot_keep_the_meters_permanent_id_while_our_home_is_off(self):
        service, meter = self.linked_service()
        meter_id = self.conn.execute("SELECT global_id FROM home_layout__meters WHERE id = ?", (meter,)).fetchone()[0]
        created = [c for c in sync.changes(self.conn) if c["table_name"] == SERVICES]
        self.assertEqual(created[-1]["patch"]["meter"], meter_id)
        self.switch(home_layout=False)
        seen = sync.changes(self.conn)[-1]["seq"]
        self.store().update(SERVICES, service, {"name": "Renamed"})
        later = sync.changes(self.conn, seen)
        self.assertEqual([c["columns"] for c in later], [["name"]])  # the link is not touched, so not rewritten
        snap = sync.snapshot(self.conn, self.store().registry)
        row = next(r for r in snap["records"] if r["table"] == SERVICES)
        self.assertEqual(row["values"]["meter"], meter_id)
        self.assertEqual([p for p in sync.check(self.conn, self.store().registry) if SERVICES in p], [])


class LoaderTests(TempDirTestCase):
    REFERRING = '''name = "demo"
title = "Demo"
version = "1.0.0"
description = "A made-up module for tests."
core_api = "1"
kind = "declarative"
requires = []
optional_requires = ["other"]
outbound_hosts = []
'''
    OTHER = '''name = "other"
title = "Other list"
version = "1.0.0"
description = "A made-up optional module."
core_api = "1"
kind = "declarative"
requires = []
outbound_hosts = []
'''
    TABLES = '''[tables.things]
title = "Things"
columns.name = { type = "text", required = true }
columns.spot = { type = "link", to = "other.spots", on_delete = "clear" }
'''
    OTHER_TABLES = '''[tables.spots]
title = "Spots"
columns.name = { type = "text", required = true }
'''

    def problems(self, tables=TABLES, module=REFERRING, labels=None, sheets=None):
        folder = self.make_module("demo", module=module, tables=tables, labels=labels)
        if sheets:
            self.write("modules/demo/sheets.toml", sheets)
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        return " ".join(caught.exception.problems)

    def test_10_a_module_whose_optional_module_is_not_installed_still_loads_and_works(self):
        folder = self.make_module("demo", module=self.REFERRING, tables=self.TABLES, labels=None)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual((failures, [m.name for m in found]), ({}, ["demo"]))
        column = found[0].tables["things"].columns["spot"]
        self.assertTrue(column.optional)
        self.write("modules/demo/migrations/0001_initial.sql", schema.next_migration_sql(modules.load_module(folder)))
        self.assertNotIn("REFERENCES", schema.column_sql("demo", column))  # no database rule to fail on
        report = startup.prepare(self.tmp / "data", self.tmp / "modules")
        self.assertEqual(report.module_problems, {})
        conn = db.connect(self.tmp / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        store = records.Records(conn, records.build_registry(report.loaded))
        thing = store.create("demo__things", {"name": "Invented thing"})
        with self.assertRaises(records.ValidationError):
            store.update("demo__things", thing, {"spot": 1})
        self.assertEqual(sync.check(conn, store.registry), [])

    def test_utilities_loads_with_home_layout_not_installed(self):
        for name in ("people", "utilities"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual((failures, [m.name for m in found]), ({}, ["people", "utilities"]))

    def test_an_installed_optional_module_comes_first_and_its_table_is_checked(self):
        self.make_module("other", module=self.OTHER, tables=self.OTHER_TABLES, labels=None)
        self.make_module("demo", module=self.REFERRING, tables=self.TABLES, labels=None)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual((failures, [m.name for m in found]), ({}, ["other", "demo"]))
        self.make_module("demo", module=self.REFERRING, tables=self.TABLES.replace("other.spots", "other.spotz"),
                         labels=None)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertIn("has no table 'spotz'", " ".join(failures["demo"]))
        self.assertEqual([m.name for m in found], ["other"])

    def test_an_optional_module_that_requires_this_one_is_not_a_loop(self):
        self.make_module("other", module=self.OTHER.replace("requires = []", 'requires = ["demo"]'),
                         tables=self.OTHER_TABLES + 'columns.thing = { type = "link", to = "demo.things" }\n',
                         labels=None)
        self.make_module("demo", module=self.REFERRING, tables=self.TABLES, labels=None)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertEqual((failures, [m.name for m in found]), ({}, ["demo", "other"]))

    def test_the_contract_refuses_what_an_optional_link_can_not_be(self):
        self.assertIn("can't be required", self.problems(self.TABLES.replace('on_delete = "clear"',
                                                                             'on_delete = "clear", required = true')))
        self.assertIn('can\'t use on_delete = "cascade"', self.problems(self.TABLES.replace('"clear"', '"cascade"')))
        both = self.REFERRING.replace("requires = []", 'requires = ["other"]')
        self.assertIn("under both requires and optional_requires", self.problems(module=both))
        neither = self.REFERRING.replace('optional_requires = ["other"]\n', "")
        self.assertIn("(or optional_requires, if this module works without it)", self.problems(module=neither))
        gap = self.TABLES + '[[tables.things.watch.gaps]]\nmissing = "spot"\nmessage = "Where is {name}?"\n'
        self.assertIn("can't be a question", self.problems(gap))
        sheet = ('[[sheet]]\nname = "s"\ntitle = "S"\n[[sheet.section]]\ntitle = "T"\ntable = "things"\n'
                 'columns = ["name", "spot.name"]\n')
        self.assertIn("through a link into an optional module", self.problems(sheets=sheet))
        words = '[tables.things]\ncolumns.name = { optional = { none = "No spot." } }\n'
        self.assertIn("only apply to a link into a module under optional_requires", self.problems(labels=words))
        words = '[tables.things]\ncolumns.spot = { optional = { nothing = "No spot." } }\n'
        self.assertIn("optional gives the household's words", self.problems(labels=words))

    def test_a_module_without_its_own_words_gets_plain_defaults(self):
        from dashboard.core import optional_links
        self.make_module("demo", module=self.REFERRING, tables=self.TABLES,
                         labels='[tables.things]\ncolumns.spot = { label = "Spot" }\n')
        module = modules.load_module(self.tmp / "modules" / "demo")
        info = records.TableInfo(module, module.tables["things"])
        column = module.tables["things"].columns["spot"]
        self.assertEqual(optional_links.words(info, column, "kept", "Other list"),
                         "Spot link saved; switch on Other list to see it.")
        self.assertEqual(optional_links.words(info, column, "missing", "Other list"),
                         "The linked spot is no longer there. Choose another, or leave it blank.")
