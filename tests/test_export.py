"""Tests for Export my records: every table of an example household, private details, formula safety and the download."""
import csv
import io
import json
import zipfile
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import db, export, modules, records, settings, startup
from dashboard.web.app import create_app
import load_example

PORT = 5124
BASE = f"http://127.0.0.1:{PORT}"
SECRET = "Zebra made up private note"  # a made-up private value: it must never appear in an export
NOW = datetime(2026, 11, 18, 9, 30, tzinfo=timezone.utc)


def read_zip(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        return {name: archive.read(name) for name in archive.namelist()}


def read_csv(content: bytes) -> list[list[str]]:
    assert content.startswith(b"\xef\xbb\xbf")  # a byte-order mark, so Excel opens it as UTF-8
    return list(csv.reader(io.StringIO(content.decode("utf-8-sig"), newline="")))


class ExportTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.data = self.tmp / "smith"
        load_example.load("smith", self.data, today=date(2026, 6, 1))
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        found, failures = modules.discover(ROOT / "modules")
        self.assertEqual(failures, {})
        self.registry = records.build_registry(found)
        self.store = records.Records(self.conn, self.registry)

    def export(self, include_deleted=False):
        return read_zip(export.build(self.conn, self.registry, __version__, include_deleted, NOW))

    def table(self, files, name):
        rows = read_csv(files[f"{name}.csv"])
        return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]

    def test_every_table_gets_a_file_with_every_record(self):
        files = self.export()
        shared = [n for n, i in self.registry.items() if not i.table.private]  # private history is left out (0120)
        self.assertEqual(set(files), {"README.txt", "manifest.json"} | {f"{n}.csv" for n in shared})
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["private_tables_left_out"], ["Medicine doses"])
        self.assertEqual(manifest["app_version"], __version__)
        self.assertEqual(manifest["created"], "2026-11-18T09:30:00+00:00")
        self.assertEqual({m["name"] for m in manifest["modules"]}, {i.module.name for i in self.registry.values()})
        self.assertTrue(all("version" in m for m in manifest["modules"]))
        self.assertEqual({t["file"] for t in manifest["tables"]}, {f"{n}.csv" for n in shared})
        for name in shared:
            header, rows = self.table(files, name)
            live = self.conn.execute(f"SELECT COUNT(*) FROM {name} WHERE deleted_at IS NULL").fetchone()[0]
            self.assertEqual(len(rows), live, name)
            entry = next(t for t in manifest["tables"] if t["file"] == f"{name}.csv")
            self.assertEqual(entry["rows"], live)
            self.assertEqual([c["heading"] for c in entry["columns"]], header)

    def test_headings_are_the_household_labels_and_values_are_readable(self):
        header, rows = self.table(self.export(), "stock__items")
        self.assertEqual(header[0], "ID")
        beans = next(r for r in rows if r["Name"] == "Kidney beans")
        self.assertEqual(beans["Category"], "Pantry")  # a choice shows its words, not its key
        self.assertRegex(beans["Created"], r"^\d{4}-\d{2}-\d{2}T")
        manifest = json.loads(self.export()["manifest.json"])
        columns = next(t for t in manifest["tables"] if t["table"] == "items")["columns"]
        self.assertEqual(next(c for c in columns if c["key"] == "category")["choices"]["first_aid"], "First aid and medical")
        self.assertIn("name", [c["key"] for c in columns])

    def test_links_show_the_name_or_full_path_and_the_id(self):
        files = self.export()
        header, places = self.table(files, "stock__places")
        self.assertIn("Inside (id)", header)
        shelf = next(r for r in places if r["Name"] == "Shelf 3")
        self.assertEqual(shelf["Inside"], "Kitchen > Pantry")
        inside = self.conn.execute("SELECT inside FROM stock__places WHERE name = 'Shelf 3'").fetchone()[0]
        self.assertEqual(shelf["Inside (id)"], str(inside))
        self.assertEqual(shelf["ID"], str(self.conn.execute("SELECT id FROM stock__places WHERE name = 'Shelf 3'").fetchone()[0]))
        _, batches = self.table(files, "stock__lots")
        kidney = [b for b in batches if b["Item"] == "Kidney beans"]
        self.assertEqual(len(kidney), 2)
        self.assertIn("Kitchen > Pantry > Shelf 3", {b["Where it is"] for b in kidney})  # the full place path
        self.assertTrue(all(b["Item (id)"].isdigit() for b in kidney))

    def test_dates_are_iso_money_whole_units_and_yes_no(self):
        files = self.export()
        _, batches = self.table(files, "stock__lots")
        self.assertIn("2027-03-28", {r["Use by"] for r in batches})
        self.assertTrue(all(len(r["Use by"]) in (0, 10) for r in batches))
        _, waters = self.table(files, "stock__items")
        self.assertTrue({r["Is this water safe to drink now?"] for r in waters} <= {"Yes", "No", ""})
        self.assertIn("Yes", {r["Is this water safe to drink now?"] for r in waters})
        self.assertNotIn("1", {r["Is this water safe to drink now?"] for r in waters})

    def test_money_is_written_in_whole_units(self):
        info = next(i for i in self.registry.values() if any(c.type == "money" and not c.sensitive
                                                             for c in i.table.columns.values()))
        column = next(c for c in info.table.columns.values() if c.type == "money" and not c.sensitive)
        self.conn.execute(f"UPDATE {info.name} SET {column.name} = 123456 WHERE id = (SELECT MIN(id) FROM {info.name})")
        _, rows = self.table(self.export(), info.name)
        self.assertIn("1234.56", {v for r in rows for v in r.values()})

    def test_private_values_are_nowhere_in_the_zip_and_named_by_label_only(self):
        self.conn.execute("UPDATE home_layout__exits SET access_details = ? WHERE name = 'Front door'", (SECRET,))
        sensitive = [(i.name, c.name) for i in self.registry.values() for c in i.table.columns.values() if c.sensitive]
        self.assertTrue(sensitive)
        for table, column in sensitive:  # every private column holds the made-up value in its first row
            self.conn.execute(f"UPDATE {table} SET {column} = ? WHERE id = (SELECT MIN(id) FROM {table})", (SECRET,))
        raw = export.build(self.conn, self.registry, __version__, True, NOW)
        files = read_zip(raw)
        self.assertNotIn(SECRET.encode(), raw)
        for name, content in files.items():
            self.assertNotIn(SECRET.encode(), content, name)
        header, _ = self.table(files, "home_layout__exits")
        self.assertNotIn("Codes or access details (private)", header)
        manifest = json.loads(files["manifest.json"])
        exits = next(t for t in manifest["tables"] if t["table"] == "exits" and t["module"] == "home_layout")
        self.assertEqual(exits["left_out_as_private"], ["Codes or access details (private)"])
        self.assertNotIn("access_details", {c["key"] for c in exits["columns"]})
        self.assertIn("Codes or access details (private)", files["README.txt"].decode())

    def test_secrets_folder_is_never_read(self):
        (self.data / "secrets").mkdir(exist_ok=True)
        (self.data / "secrets" / "helper_keys.json").write_text(f'{{"key": "{SECRET}"}}', encoding="utf-8")
        for content in self.export(True).values():
            self.assertNotIn(SECRET.encode(), content)

    def test_text_that_looks_like_a_formula_gets_an_apostrophe(self):
        for text in ("=1+1", "+44 20 7946 0000", "-2", "@SUM(A1)"):
            self.store.create("stock__items", {"name": text})
        _, rows = self.table(self.export(), "stock__items")
        names = {r["Name"] for r in rows}
        for text in ("=1+1", "+44 20 7946 0000", "-2", "@SUM(A1)"):
            self.assertIn("'" + text, names)
            self.assertNotIn(text, names)
        for r in rows:  # no cell anywhere begins with a formula character, except plain numbers
            for value in r.values():
                self.assertFalse(value.startswith(("=", "+", "@", "\t", "\r")), value)
        self.assertIn("apostrophe", self.export()["README.txt"].decode())

    def test_a_tab_or_line_return_at_the_start_is_guarded_too(self):
        for text in ("\t=cmd", "\r=cmd", "=cmd"):
            self.assertEqual(export._guard(text), "'" + text)
        for text in ("cmd=1", "12", "", "Kidney beans"):
            self.assertEqual(export._guard(text), text)

    def test_a_link_to_a_record_named_like_a_formula_is_guarded_too(self):
        place = self.store.create("stock__places", {"name": "=HYPERLINK(1)"})
        item = self.store.create("stock__items", {"name": "Thing"})
        self.store.create("stock__lots", {"item": item, "quantity": 1, "place": place})
        _, rows = self.table(self.export(), "stock__lots")
        self.assertIn("'=HYPERLINK(1)", {r["Where it is"] for r in rows})

    def test_deleted_records_are_left_out_unless_asked_for(self):
        item = self.store.create("stock__items", {"name": "Old torch"})
        self.store.delete("stock__items", item)
        header, rows = self.table(self.export(), "stock__items")
        self.assertNotIn("Old torch", {r["Name"] for r in rows})
        self.assertNotIn("Deleted on", header)
        header, rows = self.table(self.export(include_deleted=True), "stock__items")
        old = next(r for r in rows if r["Name"] == "Old torch")
        self.assertRegex(old["Deleted on"], r"^\d{4}-\d{2}-\d{2}T")
        self.assertEqual({r["Deleted on"] for r in rows if r["Name"] == "Kidney beans"}, {""})
        self.assertIn("Deleted records are included", self.export(True)["README.txt"].decode())
        self.assertIn("not included", self.export()["README.txt"].decode())

    def test_a_table_with_no_records_still_has_its_headings(self):
        self.conn.execute("DELETE FROM stock__lots")
        files = self.export()
        rows = read_csv(files["stock__lots.csv"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "ID")

    def test_the_export_is_one_consistent_moment_and_leaves_no_open_transaction(self):
        self.export()
        self.assertFalse(self.conn.in_transaction)

    def test_text_with_commas_quotes_and_line_breaks_round_trips(self):
        self.store.create("stock__items", {"name": 'Tea, "loose"\nleaf Ünïcode 茶'})
        _, rows = self.table(self.export(), "stock__items")
        self.assertIn('Tea, "loose"\nleaf Ünïcode 茶', {r["Name"] for r in rows})

    def test_the_readme_is_in_plain_words(self):
        text = self.export()["README.txt"].decode()
        for phrase in ("NOT a backup", "Keep it private", "stock__items.csv", "year-month-day", "whole units"):
            self.assertIn(phrase, text)


class ExportPageTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.data = self.tmp / "smith"
        load_example.load("smith", self.data, today=date(2026, 6, 1))
        report = startup.prepare(self.data, ROOT / "modules")
        conn = db.connect(self.data / "dashboard.db")
        settings.put(conn, "setup.done", True)
        conn.close()
        self.app = create_app("t", lambda: None, report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def post(self, data=None, token=True):
        return self.client.post("/settings/export", data=dict(data or {}, **({"_csrf": self.app.config["CSRF_TOKEN"]} if token else {})),
                                base_url=BASE)

    def test_the_page_says_what_it_is_in_plain_words(self):
        page = self.client.get("/settings/export", base_url=BASE).get_data(as_text=True)
        for words in ("Export my records", "Private details are left out", "not a backup", "Stock items", "Download my records"):
            self.assertIn(words, page)
        self.assertIn("/settings/export", self.client.get("/settings", base_url=BASE).get_data(as_text=True))

    def test_the_button_downloads_a_zip_with_a_dated_name_and_no_store(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Content-Disposition"],
                         f'attachment; filename="dashboard-plus-export-{date.today().isoformat()}.zip"')
        files = read_zip(response.data)
        self.assertIn("stock__items.csv", files)
        self.assertNotIn("Deleted on", files["stock__items.csv"].decode("utf-8-sig").splitlines()[0])

    def test_the_checkbox_includes_deleted_records(self):
        response = self.post({"include_deleted": "yes"})
        self.assertIn("Deleted on", read_zip(response.data)["stock__items.csv"].decode("utf-8-sig").splitlines()[0])

    def test_it_needs_the_pages_own_token_and_the_sign_in(self):
        self.assertEqual(self.post(token=False).status_code, 400)
        stranger = self.app.test_client()
        self.assertEqual(stranger.post("/settings/export", data={"_csrf": self.app.config["CSRF_TOKEN"]}, base_url=BASE).status_code, 302)
        self.assertEqual(stranger.get("/settings/export", base_url=BASE).status_code, 302)
        self.assertEqual(self.client.get("/settings/export", base_url=BASE).status_code, 200)
