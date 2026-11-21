"""Tests for the Wine collection module: manual counts, free-text place, ordinary price and notes, the sheet, linked history.

These follow the 15 checks in Lane B's draft (its ACCEPTANCE.md, now in git history) that a computer can run (decision 0095).
Checks about reading a screen at 320 pixels wide and printing on A4 and Letter are done in the browser check and screenshots."""
import csv
import io
import re
import shutil
import zipfile
from datetime import date, datetime, timedelta, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import backups, db, export, helpers, modules, records, restore, settings, startup, watch
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
import load_example

PORT = 5136
BASE = f"http://127.0.0.1:{PORT}"
ASK = ("Where are the bottles of Evening Red kept? Write a shelf or rack if it would help you find them.")


class WineTestCase(TempDirTestCase):
    MODULES = ("wine",)

    def setUp(self):
        super().setUp()
        for name in self.MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)
        self.wine = self.records.create("wine__wines", {
            "name": "Evening Red", "producer": "Example Vineyard", "vintage": 2023,
            "region": "Fictional Valley", "grape": "Shiraz"})

    def bottle(self, quantity=2, **values):
        return self.records.create("wine__bottles", {"wine": self.wine, "quantity": quantity, **values})

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None):
        return (client or self.client()).get(path, base_url=BASE).get_data(as_text=True)

    def gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("wine__")]


class WineModuleTests(WineTestCase):
    def test_1_module_loads_alone_with_no_problems_no_hosts_and_every_screen_opens(self):
        self.assertEqual(self.report.module_problems, {})
        module = modules.load_module(ROOT / "modules" / "wine")
        self.assertEqual((module.requires, module.outbound_hosts), ([], []))
        client = self.client()
        for path in ("/t/wine__wines", "/t/wine__bottles", "/t/wine__tastings", "/sheet/wine/collection"):
            self.assertEqual(client.get(path, base_url=BASE).status_code, 200, path)

    def test_2_empty_lists_say_so_and_required_fields_are_enforced(self):
        self.records.delete("wine__wines", self.wine)
        client = self.client()
        for path in ("/t/wine__wines", "/t/wine__bottles", "/t/wine__tastings"):
            self.assertIn("Nothing here yet.", self.page(path, client))
        self.assertIn("Add a wine you want to remember.", self.page("/", client))
        for table, values in (("wines", {"name": ""}), ("bottles", {"quantity": "1"}), ("bottles", {"wine": str(self.wine)}),
                              ("tastings", {"wine": str(self.wine), "tasted_on": "2026-11-20"}),
                              ("tastings", {"wine": str(self.wine), "notes": "Fine"})):
            reply = client.post(f"/t/wine__{table}/new", data={"_csrf": client.csrf, **values}, base_url=BASE)
            self.assertEqual(reply.status_code, 422, (table, values))
            self.assertIn("is required", reply.get_data(as_text=True))
        for table in ("wines", "bottles", "tastings"):
            self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM wine__{table} WHERE deleted_at IS NULL").fetchone()[0], 0)

    def test_3_a_wine_keeps_the_words_entered_and_an_edit_changes_one_field(self):
        before = self.records.get("wine__wines", self.wine)
        self.records.update("wine__wines", self.wine, {"region": "Another Fictional Valley"})
        after = self.records.get("wine__wines", self.wine)
        changed = {k for k in before if before[k] != after[k]} - {"updated_at", "edited_by_person", "row_revision"}
        self.assertEqual(changed, {"region"})
        self.assertEqual((after["name"], after["producer"], after["vintage"], after["grape"]),
                         ("Evening Red", "Example Vineyard", 2023, "Shiraz"))
        page = self.page(f"/t/wine__wines/{self.wine}")
        for shown in ("Evening Red", "Example Vineyard", "Another Fictional Valley", "Shiraz"):
            self.assertIn(shown, page)

    def test_4_two_bottle_rows_stay_separate_and_nothing_sums_them(self):
        pantry = self.bottle(2, place="Pantry shelf", bought_on="2026-11-20", price="12.00")
        rack = self.bottle(3, place="Rack A", bought_on="2026-11-19")
        self.assertEqual(self.records.get("wine__bottles", pantry)["price"], 1200)  # the household's own entry, in cents
        self.assertIsNone(self.records.get("wine__bottles", rack)["price"])
        page = self.page("/t/wine__bottles")
        self.assertIn("Pantry shelf", page)
        self.assertIn("Rack A", page)
        for sum_ in ("Total", "total", "5 bottles", "stocktake", "scanned"):
            self.assertNotIn(sum_, page)
        self.assertIn("in your household", self.page("/t/wine__bottles/new"))

    def test_5_a_count_changes_only_when_the_person_edits_it_and_a_tasting_moves_nothing(self):
        bottle = self.bottle(2, place="Pantry shelf")
        self.records.update("wine__bottles", bottle, {"quantity": 1})
        tasting = self.records.create("wine__tastings", {"wine": self.wine, "tasted_on": "2026-11-20", "notes": "Soft fruit."})
        self.assertEqual(self.records.get("wine__bottles", bottle)["quantity"], 1)
        self.records.delete("wine__tastings", tasting)
        self.records.restore("wine__tastings", tasting)
        self.assertEqual(self.records.get("wine__bottles", bottle)["quantity"], 1)
        self.records.delete("wine__bottles", bottle)
        self.records.restore("wine__bottles", bottle)
        self.assertEqual(self.records.get("wine__bottles", bottle)["quantity"], 1)
        tables = {t for t in self.registry if t.startswith("wine__")}
        self.assertEqual(tables, {"wine__wines", "wine__bottles", "wine__tastings"})  # no movement table exists to invent one
        self.assertIn("Update it when bottles are added or opened.", self.page("/t/wine__bottles/new"))

    def test_6_where_kept_is_asked_until_written_and_is_plain_text_not_a_stock_place(self):
        bottle = self.bottle(2)
        self.assertEqual(self.gaps(), [ASK])
        self.records.update("wine__bottles", bottle, {"place": "Rack A"})
        self.assertEqual(self.gaps(), [])
        self.assertEqual(modules.load_module(ROOT / "modules" / "wine").tables["bottles"].columns["place"].type, "text")
        self.assertIn("Write a shelf or rack", self.page("/t/wine__bottles/new") + ASK)

    def test_7_invalid_numbers_are_refused_whole_and_zero_is_a_real_count(self):
        for bad in ({"quantity": -1}, {"quantity": None}, {"price": "-1"}):
            with self.assertRaises(records.ValidationError):
                self.bottle(**{"quantity": 1, **bad})
        for year in (1899, 2101):
            with self.assertRaises(records.ValidationError):
                self.records.create("wine__wines", {"name": "Odd", "vintage": year})
        client = self.client()
        reply = client.post("/t/wine__bottles/new", data={"_csrf": client.csrf, "wine": str(self.wine), "quantity": "-1"},
                            base_url=BASE)
        self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wine__bottles").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wine__wines").fetchone()[0], 1)  # nothing partial
        zero = self.bottle(0, place="Rack A")
        self.assertEqual(self.records.get("wine__bottles", zero)["quantity"], 0)
        self.assertEqual(self.gaps(), [])

    def test_8_dates_use_the_household_order_and_wrong_order_is_refused_not_swapped(self):
        client = self.client()

        def add(text, country):
            settings.put(self.conn, "household.country", country)
            return client.post("/t/wine__bottles/new", data={
                "_csrf": client.csrf, "wine": str(self.wine), "quantity": "1", "place": "Rack A", "bought_on": text},
                base_url=BASE)

        self.assertEqual(add("20/11/26", "Australia").status_code, 302)
        self.assertEqual(add("11/20/26", "United States").status_code, 302)
        stored = [r[0] for r in self.conn.execute("SELECT bought_on FROM wine__bottles ORDER BY id")]
        self.assertEqual(stored, ["2026-11-20", "2026-11-20"])
        settings.put(self.conn, "household.country", "Australia")
        self.assertIn("20/11/26", self.page("/t/wine__bottles", client))
        settings.put(self.conn, "household.country", "United States")
        self.assertIn("11/20/26", self.page("/t/wine__bottles", client))
        for text, country, order in (("20/11/26", "United States", "MM/DD/YY"), ("11/20/26", "United Kingdom", "DD/MM/YY"),
                                     ("31/04/26", "Australia", "DD/MM/YY")):
            reply = add(text, country)
            self.assertEqual(reply.status_code, 422, text)
            self.assertIn(f"Enter a real date in {order} format.", reply.get_data(as_text=True))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wine__bottles").fetchone()[0], 2)
        bad = client.post("/t/wine__tastings/new", data={"_csrf": client.csrf, "wine": str(self.wine),
                                                         "tasted_on": "30/02/26", "notes": "x"}, base_url=BASE)
        self.assertEqual(bad.status_code, 422)

    def test_8b_no_due_date_or_ready_to_drink_reminder_is_invented(self):
        self.bottle(1, place="Rack A", bought_on="2020-01-01")
        self.assertEqual([i for i in watch.expiring(self.conn, self.registry, date.today()) if i.table.startswith("wine__")], [])
        module = modules.load_module(ROOT / "modules" / "wine")
        self.assertTrue(all(t.watch.get("expiring") is None for t in module.tables.values()))

    def test_9_tasting_text_is_shown_as_text_in_the_list_and_the_export_and_is_not_private(self):
        self.records.create("wine__tastings", {"wine": self.wine, "tasted_on": "2026-11-20", "notes": "Ordinary note"})
        self.records.create("wine__tastings", {"wine": self.wine, "tasted_on": "2026-11-19", "notes": "<b>sample</b>"})
        client = self.client()
        listing = self.page("/t/wine__tastings", client)
        self.assertIn("Ordinary note", listing)
        self.assertIn("&lt;b&gt;sample&lt;/b&gt;", listing)
        self.assertNotIn("<b>sample</b>", listing)
        self.assertNotIn("<b>sample</b>", self.page("/t/wine__tastings/new", client))
        self.assertIn("visible in the list and a spreadsheet export", self.page("/t/wine__tastings/new", client))
        module = modules.load_module(ROOT / "modules" / "wine")
        self.assertFalse(any(c.sensitive for t in module.tables.values() for c in t.columns.values()))
        files = self.export()
        self.assertIn("Ordinary note", files["wine__tastings.csv"])

    def export(self):
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 20, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return {n: archive.read(n).decode("utf-8-sig") for n in archive.namelist()}

    def test_10_price_is_ordinary_in_the_export_and_a_granted_helper_read_but_not_on_the_sheet(self):
        self.bottle(2, place="Pantry shelf", price="12.00")
        self.records.create("wine__tastings", {"wine": self.wine, "tasted_on": "2026-11-20", "notes": "Softly fruity"})
        rows = list(csv.reader(io.StringIO(self.export()["wine__bottles.csv"])))
        self.assertIn("Price paid", rows[0])
        self.assertEqual(rows[1][rows[0].index("Price paid")], "12.00")
        self.assertIn("is included in a spreadsheet export", self.page("/t/wine__bottles/new"))
        labels = (ROOT / "modules" / "wine" / "labels.toml").read_text(encoding="utf-8").lower()
        for promise in ("secret", "private", "hidden", "confidential"):
            self.assertNotIn(promise, labels)
        sheet = self.page("/sheet/wine/collection")
        self.assertIn("Pantry shelf", sheet)
        for left_out in ("12.00", "Price paid", "Softly fruity", "Tasting"):
            self.assertNotIn(left_out, sheet)
        _, granted = helpers.issue(self.conn, self.data, "Wine reader", "read", ["wine"])
        reply = self.client().get("/api/v1/tables/wine__bottles/records", base_url=BASE,
                                  headers={"Authorization": f"Bearer {granted}"})
        self.assertEqual(reply.status_code, 200)
        self.assertIn("12", str(reply.get_json()))
        notes = self.client().get("/api/v1/tables/wine__tastings/records", base_url=BASE,
                                  headers={"Authorization": f"Bearer {granted}"})
        self.assertIn("Softly fruity", notes.get_data(as_text=True))

    def test_10b_a_helper_without_a_wine_grant_sees_no_wine_records(self):
        self.bottle(2, place="Pantry shelf", price="12.00")
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        report = startup.prepare(self.data, self.tmp / "modules")
        _, other = helpers.issue(self.conn, self.data, "Stock reader", "read", ["stock"])
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        auth = {"Authorization": f"Bearer {other}"}
        client = app.test_client()
        tables = client.get("/api/v1/tables", base_url=BASE, headers=auth).get_data(as_text=True)
        self.assertNotIn("wine__", tables)
        for path in ("/api/v1/tables/wine__bottles/records", "/api/v1/tables/wine__wines/records"):
            reply = client.get(path, base_url=BASE, headers=auth)
            self.assertEqual(reply.status_code, 404, path)
            self.assertNotIn("Pantry shelf", reply.get_data(as_text=True))

    def test_11_the_sheet_prints_wine_count_place_and_bought_on_with_zero_and_long_text(self):
        long_place = "Back cellar rack, third shelf from the floor behind the folded boxes " * 3
        self.bottle(2, place=long_place.strip(), bought_on="2026-11-20", price="12.00")
        self.bottle(0, place="Rack A", bought_on="2026-11-19")
        sheet = self.page("/sheet/wine/collection")
        for shown in ("Wine collection", "A snapshot of the bottles recorded here", "Evening Red", long_place.strip(),
                      "Rack A", "20/11/26", "19/11/26", "Bottles on hand"):
            self.assertIn(shown, sheet)
        self.assertRegex(sheet, r">\s*0\s*<")  # zero is shown as zero
        for left_out in ("12.00", "Price paid", "worth", "market value"):
            self.assertNotIn(left_out, sheet)
        self.assertNotIn("Example Vineyard", sheet)

    def test_12_a_wine_with_bottles_or_notes_cannot_be_deleted_until_they_are_deliberately_removed(self):
        bottle = self.bottle(1, place="Rack A")
        tasting = self.records.create("wine__tastings", {"wine": self.wine, "tasted_on": "2026-11-20", "notes": "Kept"})
        with self.assertRaises(records.ValidationError) as caught:
            self.records.delete("wine__wines", self.wine)
        self.assertIn("still point at it", str(caught.exception.problems["delete"]))
        self.assertIsNone(self.records.get("wine__wines", self.wine)["deleted_at"])
        self.assertEqual(self.records.get("wine__tastings", tasting)["notes"], "Kept")
        self.records.delete("wine__bottles", bottle)
        with self.assertRaises(records.ValidationError):  # the tasting note still points at it
            self.records.delete("wine__wines", self.wine)
        self.records.delete("wine__tastings", tasting)
        self.records.delete("wine__wines", self.wine)
        self.records.restore("wine__wines", self.wine)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wine__wines WHERE deleted_at IS NULL").fetchone()[0], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM wine__bottles WHERE deleted_at IS NULL").fetchone()[0], 0)

    def test_13_switching_wine_off_hides_it_and_keeps_the_rows_and_switching_on_brings_them_back(self):
        self.bottle(2)
        self.records.create("wine__tastings", {"wine": self.wine, "tasted_on": "2026-11-20", "notes": "Kept"})
        client = self.client()
        self.assertIn("/t/wine__wines", self.page("/", client))
        self.assertIn(ASK, self.page("/attention", client))
        before = self.snapshot()
        settings.set_module_enabled(self.conn, "wine", False)
        self.assertEqual(client.get("/t/wine__wines", base_url=BASE).status_code, 404)
        self.assertNotIn("/t/wine__wines", self.page("/", client))
        self.assertNotIn(ASK, self.page("/attention", client))
        settings.set_module_enabled(self.conn, "wine", True)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("Evening Red", self.page("/t/wine__wines", client))
        self.assertIn(ASK, self.page("/attention", client))

    def snapshot(self):
        return {t: [tuple(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY id")]
                for t in ("wine__wines", "wine__bottles", "wine__tastings")}

    def test_home_page_has_a_wine_card_and_the_sheet_link(self):
        page = self.page("/")
        self.assertIn("/t/wine__wines", page)
        self.assertIn("/sheet/wine/collection", page)

    def test_no_drinking_buying_or_value_advice_in_the_module_files(self):
        text = " ".join(p.read_text(encoding="utf-8").lower() for p in (ROOT / "modules" / "wine").glob("*.toml"))
        for advice in ("drink by", "ready to drink", "cellar for", "good value", "worth", "recommend", "healthy",
                       "units of alcohol", "should buy"):
            self.assertNotIn(advice, text)

    def test_migration_matches_its_description_and_touches_only_its_own_tables(self):
        module = modules.load_module(ROOT / "modules" / "wine")
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "wine" / "migrations" / "0001_first_tables.sql").read_text(encoding="utf-8")
        created = re.findall(r"CREATE (?:TABLE|INDEX) (\S+)", sql)
        self.assertTrue(created)
        self.assertTrue(all(name.startswith("wine__") for name in created), created)
        self.assertNotRegex(sql, r"(?m)^\s*(ALTER|DROP|UPDATE|INSERT|DELETE)\b")


class WineExampleAndBackupTests(TempDirTestCase):
    def test_14_each_example_with_wine_has_one_wine_one_bottle_row_and_one_note_linked_to_it(self):
        today = date(2026, 6, 1)
        for household, name, place, bought, tasted in (("smith", "Evening Red", "Pantry", -30, -5),
                                                       ("taylor", "Weekend Rosé", "Kitchen cupboard", -8, -3)):
            data = self.tmp / household
            load_example.load(household, data, today=today)
            conn = db.connect(data / "dashboard.db")
            self.addCleanup(conn.close)
            wines = conn.execute("SELECT id, name FROM wine__wines").fetchall()
            self.assertEqual([w["name"] for w in wines], [name])
            bottles = conn.execute("SELECT * FROM wine__bottles").fetchall()
            tastings = conn.execute("SELECT * FROM wine__tastings").fetchall()
            self.assertEqual((len(bottles), len(tastings)), (1, 1))
            self.assertEqual((bottles[0]["wine"], tastings[0]["wine"]), (wines[0]["id"], wines[0]["id"]))
            self.assertEqual(bottles[0]["place"], place)
            self.assertEqual(bottles[0]["bought_on"], (today + timedelta(days=bought)).isoformat())
            self.assertEqual(tastings[0]["tasted_on"], (today + timedelta(days=tasted)).isoformat())
            self.assertIsNone(bottles[0]["price"])

    def test_14b_garcia_does_not_use_wine_and_loads_without_it(self):
        self.assertNotIn("wine", load_example.read("garcia")["setup"]["modules"])

    def test_15_restore_follows_the_chosen_backup_and_undo_brings_the_edit_back(self):
        data = self.tmp / "smith"
        load_example.load("smith", data, today=date(2026, 6, 1))
        report = startup.prepare(data)
        backups.daily(data, today=date(2026, 6, 1))
        conn = db.connect(data / "dashboard.db")
        store = records.Records(conn, records.build_registry(report.loaded))
        bottle = conn.execute("SELECT id, quantity FROM wine__bottles").fetchone()
        self.assertEqual(bottle["quantity"], 2)
        store.update("wine__bottles", bottle["id"], {"quantity": 1})
        conn.close()

        def count():
            c = db.connect(data / "dashboard.db")
            try:
                return c.execute("SELECT quantity FROM wine__bottles WHERE id = ?", (bottle["id"],)).fetchone()[0]
            finally:
                c.close()

        chosen = restore.get({"data": data / "backups"}, "data", "daily-2026-06-01.db")
        restore.restore(data, chosen, report.loaded)
        self.assertEqual(count(), 2)
        restore.undo(data, report.loaded)
        self.assertEqual(count(), 1)
        c = db.connect(data / "dashboard.db")
        try:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM wine__wines").fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM wine__tastings").fetchone()[0], 1)
        finally:
            c.close()
