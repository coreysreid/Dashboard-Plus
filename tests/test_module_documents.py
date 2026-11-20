"""Tests for the Important documents module: places asked and kept, dates shown as due, no numbers, the sheet.

These follow the checks in Lane B's Documents draft (its NOTES.md, now in git history) that apply today (decision 0062)."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5133
BASE = f"http://127.0.0.1:{PORT}"


class DocumentsModuleTests(TempDirTestCase):
    MODULES = ("people", "stock", "documents")

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
        self.today = date.today()

    def day(self, offset):
        return (self.today + timedelta(days=offset)).isoformat()

    def gaps(self):
        return [g.message for g in watch.gaps(self.conn, self.registry) if g.table.startswith("documents__")]

    def due(self):
        return {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)}

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, path):
        return self.client().get(path, base_url=BASE).get_data(as_text=True)

    def test_module_loads_without_problems(self):
        self.assertEqual(self.report.module_problems, {})
        self.assertIn("documents", self.report.modules)

    def test_it_links_to_people_and_places_and_says_so(self):
        module = modules.load_module(ROOT / "modules" / "documents")
        self.assertEqual(module.requires, ["people", "stock"])
        columns = module.tables["documents"].columns
        self.assertEqual((columns["holder"].to, columns["place"].to), ("people.people", "stock.places"))

    def test_there_is_nowhere_to_type_a_document_number(self):
        """A location list, not a vault (draft NOTES): no number, password or copy of the paper."""
        columns = modules.load_module(ROOT / "modules" / "documents").tables["documents"].columns
        self.assertEqual(set(columns), {"name", "kind", "holder", "place", "renew_by", "copies", "notes"})
        self.assertFalse(any(c.type == "file" for c in columns.values()))

    def test_copies_are_names_of_places_only_never_a_file_or_number(self):
        tables = modules.load_module(ROOT / "modules" / "documents").tables
        self.assertEqual(set(tables["copy_places"].columns), {"name"})
        self.assertEqual((tables["documents"].columns["copies"].type, tables["documents"].columns["copies"].to),
                         ("links", "copy_places"))

    def test_a_paper_can_have_copies_at_several_places_shown_on_the_paper_its_form_the_sheet_and_export(self):
        usb = self.records.create("documents__copy_places", {"name": "Blue USB drive"})
        cloud = self.records.create("documents__copy_places", {"name": "Family cloud folder"})
        paper = self.records.create("documents__documents", {"name": "Family passports", "kind": "passport",
                                                             "copies": [usb, cloud]})
        self.assertEqual(self.records.get("documents__documents", paper)["copies"], [usb, cloud])
        self.records.update("documents__documents", paper, {"copies": [usb]})
        self.assertEqual(self.records.get("documents__documents", paper)["copies"], [usb])
        self.records.update("documents__documents", paper, {"copies": [usb, cloud]})
        client = self.client()
        for path in (f"/t/documents__documents/{paper}",
                     "/sheet/documents/document_review"):
            text = client.get(path, base_url=BASE).get_data(as_text=True)
            self.assertIn("Blue USB drive", text, path)
        self.assertIn("Copies also kept at", client.get("/t/documents__documents/new", base_url=BASE).get_data(as_text=True))
        from dashboard import __version__
        from dashboard.core import export
        import io, zipfile
        with zipfile.ZipFile(io.BytesIO(export.build(self.conn, self.registry, __version__))) as archive:
            names = [n for n in archive.namelist() if "documents__documents" in n or "Important documents" in n]
            text = "".join(archive.read(n).decode("utf-8-sig") for n in names if n.endswith(".csv"))
        self.assertIn("Blue USB drive", text)
        self.assertIn("Family cloud folder", text)

    def test_a_household_with_no_documents_is_asked_nothing(self):
        self.assertEqual(self.gaps(), [])
        self.assertEqual(self.due(), {})

    def test_where_it_is_kept_is_asked_for_each_paper_until_a_place_is_chosen(self):
        policy = self.records.create("documents__documents", {"name": "Home insurance policy", "kind": "insurance"})
        self.assertEqual(self.gaps(), ["Where is Home insurance policy kept? Choosing one of your places is enough."])
        study = self.records.create("stock__places", {"name": "Study"})
        self.records.update("documents__documents", policy, {"place": study})
        self.assertEqual(self.gaps(), [])

    def test_dates_are_due_or_overdue_never_expired(self):
        self.records.create("documents__documents", {"name": "Home insurance policy", "kind": "insurance",
                                                     "renew_by": self.day(12)})
        self.records.create("documents__documents", {"name": "Family passports", "kind": "passport",
                                                     "renew_by": self.day(-3)})
        self.records.create("documents__documents", {"name": "Bicycle warranty", "kind": "warranty",
                                                     "renew_by": self.day(200)})
        details = self.due()
        self.assertTrue(details["Home insurance policy"].startswith("review or renewal due"), details)
        self.assertIn("overdue", details["Family passports"])
        self.assertNotIn("Bicycle warranty", details)
        self.assertNotIn("expire", " ".join(details.values()))

    def test_no_date_is_invented_when_the_household_gives_none(self):
        self.records.create("documents__documents", {"name": "Family passports", "kind": "passport"})
        self.assertEqual(self.due(), {})
        self.assertIsNone(self.conn.execute("SELECT renew_by FROM documents__documents").fetchone()[0])

    def test_sheet_prints_names_kinds_and_dates_but_not_places_holders_or_notes(self):
        study = self.records.create("stock__places", {"name": "Study"})
        drawer = self.records.create("stock__places", {"name": "Locked drawer", "inside": study})
        holder = self.records.create("people__people", {"name": "Person A"})
        self.records.create("documents__documents", {"name": "Home insurance policy", "kind": "insurance",
                                                     "holder": holder, "place": drawer, "renew_by": self.day(40),
                                                     "notes": "Spare copy with Aunt B"})
        sheet = self.page("/sheet/documents/document_review")
        for shown in ("Document review dates", "Home insurance policy", "Insurance policy", "Review or renew by"):
            self.assertIn(shown, sheet)
        for kept_off in ("Locked drawer", "Person A", "Spare copy with Aunt B"):
            self.assertNotIn(kept_off, sheet)
        self.assertNotIn("Show private sheet", sheet)  # nothing private, so no extra step before printing

    def test_list_shows_the_full_place_and_whose_it_is(self):
        study = self.records.create("stock__places", {"name": "Study"})
        drawer = self.records.create("stock__places", {"name": "Filing drawer", "inside": study})
        holder = self.records.create("people__people", {"name": "Person A"})
        self.records.create("documents__documents", {"name": "Passport", "kind": "passport", "holder": holder,
                                                     "place": drawer})
        listing = self.page("/t/documents__documents")
        for shown in ("Passport", "Person A", "Study › Filing drawer"):
            self.assertIn(shown, listing)

    def test_a_place_a_paper_is_kept_at_cannot_be_deleted(self):
        """Never point to a place that no longer exists."""
        study = self.records.create("stock__places", {"name": "Study"})
        paper = self.records.create("documents__documents", {"name": "Will", "kind": "will", "place": study})
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__places", study)
        self.records.update("documents__documents", paper, {"place": None})
        self.records.delete("stock__places", study)

    def test_deleting_a_person_keeps_the_paper_and_clears_whose_it_is(self):
        holder = self.records.create("people__people", {"name": "Person A"})
        paper = self.records.create("documents__documents", {"name": "Passport", "kind": "passport",
                                                             "holder": holder})
        self.records.delete("people__people", holder)
        row = self.conn.execute("SELECT holder, deleted_at FROM documents__documents WHERE id = ?",
                                (paper,)).fetchone()
        self.assertEqual((row["holder"], row["deleted_at"]), (None, None))

    def test_switching_it_on_changes_nothing_in_people_or_stock(self):
        before_dir = self.tmp / "before"
        for name in ("people", "stock"):
            shutil.copytree(ROOT / "modules" / name, before_dir / "modules" / name)
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        conn = db.connect(before_dir / "data" / "dashboard.db")
        old = records.Records(conn, records.build_registry(report.loaded))
        old.create("people__people", {"name": "Person A"})
        old.create("stock__places", {"name": "Study"})
        tables = ("people__people", "stock__places", "stock__items")
        snapshot = {t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables}
        conn.close()

        shutil.copytree(ROOT / "modules" / "documents", before_dir / "modules" / "documents")
        report = startup.prepare(before_dir / "data", before_dir / "modules")
        self.assertEqual(report.module_problems, {})
        self.assertIn("documents", report.modules)
        conn = db.connect(before_dir / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        self.assertEqual({t: [tuple(r) for r in conn.execute(f"SELECT * FROM {t} ORDER BY id")] for t in tables},
                         snapshot)

    def test_migration_matches_its_description(self):
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(modules.load_module(ROOT / "modules" / "documents")))
