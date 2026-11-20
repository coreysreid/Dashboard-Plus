"""Tests for Import from a spreadsheet: reading a CSV, matching columns, the dry run, staging for Review and Accept."""
import html
import io
import re
import shutil

import make_migration

from support import ROOT, TempDirTestCase
from dashboard.core import csv_import, db, helpers, migrations, proposals, records, settings, startup
from dashboard.web.app import create_app
from dashboard.web.csv_import import UploadRequest
from dashboard.web.display import actor_text

PORT = 5131
BASE = f"http://127.0.0.1:{PORT}"
# Shaped like Lane B's workbench/drafts/csv_import/EXAMPLE.csv (all made up).
EXAMPLE = (
    "name,category,amount_on_hand,unit,keep_at_least,place,use_by,safe_to_drink,notes\n"
    "TOM TINNED 400G,pantry,4,tins,8,Kitchen › Pantry › Top shelf,20/05/27,,Made-up stocktake row\n"
    "Rice,pantry,1.5,kg,3,Garage › Top shelf,,,Another Top shelf in a different room\n"
    "Flushing water,water,12,litres,12,Garage › Top shelf,,no,Not for drinking\n"
    "Kidney beans,pantry,2,tins,6,Kitchen › Pantry › Top shelf,1/2/27,,\"Two lines,\nwith a comma\"\n"
)
PRIVATE_MODULE = '''name = "keys"
title = "Spare keys"
version = "1.0.0"
description = "A made-up module with a private detail."
core_api = "1"
kind = "declarative"
requires = []
outbound_hosts = []
'''
PRIVATE_TABLES = '''[tables.keys]
title = "Spare keys"
columns.name = { type = "text", required = true }
columns.code = { type = "text", sensitive = true }

[tables.safes]
title = "Key safes"
columns.name = { type = "text", required = true }
columns.combination = { type = "text", required = true, sensitive = true }
'''


def plain(page: str) -> str:
    """A page's words as a person reads them: no tags, no escapes, spaces collapsed."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", page)).split())


class CsvImportTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        make_migration.make(self.make_module("keys", module=PRIVATE_MODULE, tables=PRIVATE_TABLES, labels=None),
                            "first_tables")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", "Australia")
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.csrf = self.app.config["CSRF_TOKEN"]
        self.client.get("/?key=session-key", base_url=BASE)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        kitchen = self.store.create("stock__places", {"name": "Kitchen"})
        pantry = self.store.create("stock__places", {"name": "Pantry", "inside": kitchen})
        self.kitchen_shelf = self.store.create("stock__places", {"name": "Top shelf", "inside": pantry})
        garage = self.store.create("stock__places", {"name": "Garage"})
        self.garage_shelf = self.store.create("stock__places", {"name": "Top shelf", "inside": garage})

    # ----- helpers --------------------------------------------------------------------------------------
    def post(self, path, data=None, token=True, **kwargs):
        return self.client.post(path, data=dict(data or {}, **({"_csrf": self.csrf} if token else {})),
                                base_url=BASE, **kwargs)

    def upload(self, text, table="stock__items", name="pantry.csv", raw=None, token=True):
        body = raw if raw is not None else text.encode("utf-8")
        return self.post("/settings/import", {"table": table, "file": (io.BytesIO(body), name)}, token=token,
                         content_type="multipart/form-data")

    @staticmethod
    def form(page):
        """The hidden fields and chosen matches of the match page, as the browser would send them back."""
        found = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', page))
        found.pop("_csrf", None)
        for select in re.findall(r'<select id="(match_\d+)".*?</select>', page, re.S):
            block = re.search(rf'<select id="{select}".*?</select>', page, re.S).group(0)
            chosen = re.search(r'<option value="(\w*)" selected', block)
            found[select] = chosen.group(1) if chosen else ""
        return {k: v.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"') for k, v in found.items()}

    def check(self, text, changes=None, **kwargs):
        page = self.upload(text, **kwargs).get_data(as_text=True)
        fields = dict(self.form(page), **(changes or {}))
        response = self.post("/settings/import/check", fields)
        return response, response.get_data(as_text=True)

    def send(self, text, changes=None, **kwargs):
        _response, page = self.check(text, changes, **kwargs)
        return self.post("/settings/import/send", self.form(page))

    def go(self, page, **extra):
        """Press Send on a check page after ticking that the dates that could be read either way are right."""
        return self.post("/settings/import/send", dict(self.form(page), dates_ok="1", **extra))

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def items(self):
        return self.count("stock__items")

    # ----- choosing and reading -------------------------------------------------------------------------
    def test_settings_links_to_import(self):
        page = self.client.get("/settings", base_url=BASE).get_data(as_text=True)
        self.assertIn('href="/settings/import"', page)
        page = self.client.get("/settings/import?table=stock__items", base_url=BASE).get_data(as_text=True)
        self.assertIn('value="stock__items" selected', page)
        self.assertIn("Private details, such as door codes, can't be imported in this version", plain(page))
        self.assertNotIn('value="keys__safes"', page)  # needs a private detail
        self.assertIn("Key safes needs a private detail", plain(page))

    def test_columns_are_matched_by_label_or_key_ignoring_case(self):
        page = self.upload(EXAMPLE).get_data(as_text=True)
        self.assertIn("pantry.csv into Stock items: 4 rows read", plain(page))
        chosen = self.form(page)
        self.assertEqual([chosen[f"match_{i}"] for i in range(9)],
                         ["name", "category", "quantity", "unit", "minimum", "place", "expires", "", "notes"])
        page = self.upload("NAME;Keep At Least;Where it is\nRice;3;Garage › Top shelf\n").get_data(as_text=True)
        chosen = self.form(page)
        self.assertEqual([chosen["match_0"], chosen["match_1"], chosen["match_2"]], ["name", "minimum", "place"])

    def test_the_example_goes_to_review_and_only_accept_adds_it(self):
        response, page = self.check(EXAMPLE, {"match_7": "drinking"})
        self.assertIn("4 rows ready", plain(page))
        self.assertIn("Nothing has been saved yet.", plain(page))
        self.assertIn("Row 5: Name: Kidney beans", plain(page))
        self.assertIn("Use by: 01/02/27", plain(page))  # typed the household's way (day first in Australia)
        self.assertEqual((self.items(), self.count("core__proposals")), (0, 0))
        response = self.go(page)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/review?done=imported&count=4", response.headers["Location"])
        self.assertEqual((self.items(), self.count("stock__lots"), self.count("core__proposals")), (0, 0, 4))
        batch = self.conn.execute("SELECT * FROM core__helper_batches").fetchone()
        self.assertEqual((batch["kind"], batch["helper_id"], batch["source_name"]), ("import", None, "pantry.csv"))
        review = self.client.get("/review?done=imported&count=4&table=stock__items", base_url=BASE).get_data(as_text=True)
        self.assertIn("Sent 4 rows from your spreadsheet to Review. Nothing is added to Stock items", plain(review))
        self.assertIn("Import 'pantry.csv' · 4 rows waiting", plain(review))
        self.assertIn("Row 2 would add to Stock items", plain(review))
        self.assertIn("Accept all 4", plain(review))
        self.assertNotIn("says why", plain(review))

        self.post(f"/review/batch/{batch['id']}/accept-all")
        self.assertEqual(self.items(), 4)
        rice = self.conn.execute("SELECT * FROM stock__items WHERE name = 'Rice'").fetchone()
        self.assertEqual((rice["quantity"], rice["minimum"], rice["source"]), (1.5, 3, "import:pantry.csv"))
        lot = self.conn.execute("SELECT * FROM stock__lots WHERE item = ?", (rice["id"],)).fetchone()
        self.assertEqual(lot["place"], self.garage_shelf)
        beans = self.conn.execute("SELECT * FROM stock__items WHERE name = 'Kidney beans'").fetchone()
        self.assertEqual((beans["expires"], beans["notes"]), ("2027-02-01", "Two lines,\nwith a comma"))
        tomatoes = self.conn.execute("SELECT * FROM stock__items WHERE name = 'TOM TINNED 400G'").fetchone()
        tomato_lot = self.conn.execute("SELECT place FROM stock__lots WHERE item = ?", (tomatoes["id"],)).fetchone()
        self.assertEqual(tomato_lot["place"], self.kitchen_shelf)
        water = self.conn.execute("SELECT drinking FROM stock__items WHERE name = 'Flushing water'").fetchone()
        self.assertEqual(water["drinking"], 0)
        history = self.store.history("stock__items", rice["id"])
        self.assertEqual(actor_text(history[0]["actor"]), "Import 'pantry.csv'")
        # Accepting again adds nothing more.
        response = self.post(f"/review/batch/{batch['id']}/accept-all")
        self.assertIn("done=nothing", response.headers["Location"])
        self.assertEqual(self.items(), 4)

    def test_a_bad_date_is_reported_with_its_row_and_nothing_is_staged(self):
        text = EXAMPLE.replace("1/2/27", "31/02/27")
        _response, page = self.check(text, {"match_7": "drinking"})
        self.assertIn("3 rows ready, 1 needs fixing", plain(page))
        self.assertIn("Row 5: Use by must be a date like 20/05/27 or 2027-05-20.", plain(page))
        self.assertEqual(self.count("core__proposals"), 0)
        self.post("/settings/import/send", self.form(page))
        staged = [r[0] for r in self.conn.execute("SELECT source_row FROM core__proposals ORDER BY position")]
        self.assertEqual(staged, [2, 3, 4])
        self.assertEqual(self.items(), 0)

    def test_the_same_checks_as_review_catch_a_missing_answer(self):
        _response, page = self.check(EXAMPLE)  # Safe to drink left unmatched: the water row needs an answer
        self.assertIn("3 rows ready, 1 needs fixing", plain(page))
        self.assertIn("Row 4: Is this water safe to drink now? Please choose one.", plain(page))

    def test_links_by_name_by_place_path_and_unknown_or_unclear_names(self):
        text = ("name,place\nTins,kitchen›pantry › top SHELF\nRope,Garage > Top shelf\nFlour,Pantry\n"
                "Bulbs,Shed\nNails,Top shelf\n")
        _response, page = self.check(text)
        self.assertIn("3 rows ready, 2 need fixing", plain(page))
        self.assertIn("Row 5: Where it is has no match: there is nothing in places called “Shed”. Use the full path "
                      "of a place saved in this household, or add the place first.", plain(page))
        self.assertIn("Row 6: Where it is: “Top shelf” matches more than one: Garage › Top shelf; "
                      "Kitchen › Pantry › Top shelf. Use the full path", plain(page))
        self.post("/settings/import/send", self.form(page))
        values = [proposals.json.loads(r[0]) for r in self.conn.execute("SELECT values_json FROM core__proposals")]
        self.assertEqual([v["place"] for v in values], [self.kitchen_shelf, self.garage_shelf,
                                                         self.conn.execute("SELECT id FROM stock__places WHERE "
                                                                           "name = 'Pantry'").fetchone()[0]])
        self.assertEqual(self.count("stock__places"), 5)  # nothing invented

    def test_a_link_to_a_batch_is_matched_by_its_item_name(self):
        rice = self.store.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        self.assertEqual(self.count("stock__movements"), 0)
        _response, page = self.check("item,reason,amount,happened_on\nrice,used,1,2027-01-05\n",
                                     table="stock__movements")
        self.assertIn("1 row ready", plain(page))
        self.post("/settings/import/send", self.form(page))
        self.assertEqual(self.store.get("stock__items", rice)["quantity"], 2)  # not until Accept

    # ----- pausing on names already there, dates that could be read either way, and missing links (0094) -----
    def test_a_name_already_in_the_list_is_flagged_and_skipped_unless_added_anyway(self):
        self.store.create("stock__items", {"name": "Rice", "unit": "kg"})
        self.store.create("stock__items", {"name": "Kidney beans"})
        text = "name,quantity\n  rice ,1\nKIDNEY  Beans,2\nFlour,3\n"
        _response, page = self.check(text)
        self.assertIn("3 rows ready", plain(page))
        self.assertIn("Row 2: Rice is already in Stock items. This row would add a second one.", plain(page))
        self.assertIn("Row 3: Kidney beans is already in Stock items. This row would add a second one.", plain(page))
        self.assertNotIn("Flour is already", plain(page))
        self.assertIn("Send 1 row to Review", plain(page))
        self.assertEqual(self.count("core__proposals"), 0)
        response = self.go(page)  # nothing ticked: both repeated names are skipped
        self.assertIn("count=1", response.headers["Location"])
        self.assertEqual([r[0] for r in self.conn.execute("SELECT source_row FROM core__proposals")], [4])
        # Ticking Add anyway on row 3 sends it as well, and Review says it already exists.
        self.conn.execute("DELETE FROM core__proposals")
        self.conn.execute("DELETE FROM core__helper_batches")
        self.conn.commit()
        _response, page = self.check(text, {"add_3": "1"})
        self.assertIn("Send 2 rows to Review", plain(page))
        response = self.go(page, add_3="1")
        self.assertIn("count=2", response.headers["Location"])
        review = plain(self.client.get("/review", base_url=BASE).get_data(as_text=True))
        self.assertIn("Row 3 would add to Stock items", review)
        self.assertIn("Already exists: Kidney beans is already in Stock items. Accepting this row will make another "
                      "Kidney beans. To add what you bought, use Stock in; to correct a count, use Count this batch.",
                      review)
        self.assertEqual(review.count("Already exists"), 1)

    def test_every_row_already_in_the_list_sends_nothing(self):
        self.store.create("stock__items", {"name": "Rice"})
        _response, page = self.check("name\nRice\n")
        response = self.go(page)
        self.assertEqual(response.status_code, 200)
        self.assertIn("No rows are chosen to send", plain(response.get_data(as_text=True)))
        self.assertEqual(self.count("core__proposals"), 0)

    def test_the_same_name_under_another_parent_is_a_different_place(self):
        self.store.create("stock__places", {"name": "Spare room"})
        sheet = csv_import.parse("name,inside\nTop shelf,Garage\nTop shelf,Spare room\n")
        info = self.registry["stock__places"]
        run = csv_import.dry_run(self.store, info, sheet, ["name", "inside"])
        self.assertEqual(sorted(run.same_name), [2])  # only the one under Garage repeats a name
        self.assertEqual(csv_import.SameName(self.store, self.registry["stock__lots"]).find({"notes": "x"}), None)

    def test_a_short_date_that_could_be_read_either_way_is_flagged_and_needs_a_tick(self):
        text = "name,expires\nA,1/2/27\nB,20/05/27\nC,2027-02-01\nD,5/5/27\n"
        _response, page = self.check(text)
        words = plain(page)
        self.assertIn("4 rows ready", words)
        self.assertIn("Use by: “1/2/27” could be read either way. Read as 1 February 2027 (day first). "
                      "Change it in the spreadsheet if that's wrong.", words)
        self.assertEqual(words.count("could be read either way. Read as"), 1)  # 20/05/27, ISO and 5/5/27 are clear
        response = self.post("/settings/import/send", self.form(page))  # box not ticked
        self.assertIn("tick the box", plain(response.get_data(as_text=True)))
        self.assertEqual(self.count("core__proposals"), 0)
        self.assertEqual(self.go(page).status_code, 302)
        self.assertEqual(self.count("core__proposals"), 4)

    def test_clear_dates_need_no_tick(self):
        _response, page = self.check("name,expires\nA,20/05/27\nB,2027-02-01\n")
        self.assertNotIn("could be read either way", plain(page))
        self.assertEqual(self.post("/settings/import/send", self.form(page)).status_code, 302)

    def test_a_month_first_household_is_told_so(self):
        settings.put(self.conn, "household.country", "United States")
        _response, page = self.check("name,expires\nA,1/2/27\n")
        self.assertIn("Read as January 2, 2027 (month first).", plain(page))

    def test_links_that_match_nothing_are_summed_up_once_at_the_top(self):
        text = "name,place\nTins,Shed › Top\nRope,Loft\nNails,Loft\nFlour,Garage › Top shelf\n"
        _response, page = self.check(text)
        words = plain(page)
        self.assertEqual(words.count("matched nothing in Places"), 1)
        self.assertIn("Where it is: 2 values on 3 rows matched nothing in Places (first: “Shed › Top”, “Loft”). "
                      "Add them first, fix the names, or skip this column.", words)
        self.assertLess(words.index("matched nothing in Places"), words.index("Row 2: Where it is has no match"))

    def test_skipping_a_column_says_how_many_rows_lose_a_value(self):
        text = "name,place\nTins,Shed › Top\nRope,Loft\nNails,\n"
        _response, page = self.check(text, {"match_1": ""})
        words = plain(page)
        self.assertIn("3 rows ready", words)
        self.assertIn("Skipping Place leaves it blank on 2 rows. These values will not be added.", words)
        _response, page = self.check(text)  # not skipped: no such line
        self.assertNotIn("Skipping", plain(page))
        _response, page = self.check("name,mystery\nTins,x\n")  # a heading that names no field is just ignored
        self.assertNotIn("Skipping", plain(page))

    def test_private_columns_cannot_be_imported(self):
        text = "name,code\nFront door spare,1234\n"
        page = self.upload(text, table="keys__keys").get_data(as_text=True)
        self.assertIn("Code is a private detail. Private details can't be imported in this version. "
                      "This column will be skipped.", plain(page))
        self.assertNotIn('<option value="code"', page)
        response, page = self.check(text, {"match_1": "code"}, table="keys__keys")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Code is a private detail.", plain(page))
        self.assertNotIn("1 row ready", plain(page))
        response = self.post("/settings/import/send", dict(self.form(page), match_1="code"))
        self.assertEqual(self.count("core__proposals"), 0)
        response = self.upload("name,combination\nShed,1234\n", table="keys__safes")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Choose the list to import into.", response.get_data(as_text=True))

    def test_every_step_needs_the_pages_own_token(self):
        self.assertEqual(self.upload(EXAMPLE, token=False).status_code, 400)
        page = self.upload(EXAMPLE).get_data(as_text=True)
        fields = self.form(page)
        self.assertEqual(self.post("/settings/import/check", fields, token=False).status_code, 400)
        _response, page = self.check(EXAMPLE, {"match_7": "drinking"})
        self.assertEqual(self.post("/settings/import/send", self.form(page), token=False).status_code, 400)
        self.assertEqual(self.count("core__proposals"), 0)

    def test_a_file_over_the_limit_is_refused_plainly(self):
        big = "name,notes\n" + "".join(f"Item {i},{'x' * 200}\n" for i in range(5200))
        response = self.upload(big)
        self.assertEqual(response.status_code, 413)
        self.assertIn("The limit is 1 MB", response.get_data(as_text=True))
        response = self.upload("", raw=b"name\n" + b"x" * 3_100_000)
        self.assertEqual(response.status_code, 413)
        self.assertIn("This file is too large. The limit is 1 MB", response.get_data(as_text=True))
        self.assertEqual(self.count("core__proposals"), 0)

    def test_utf8_with_a_bom_semicolons_and_crlf(self):
        text = "\ufeffname;minimum;notes\r\nCrème fraîche;1,000;\"Dairy; keep cold\r\nsecond line\"\r\nOats;1,5;\r\n"
        _response, page = self.check(text.lstrip("\ufeff"), raw=text.encode("utf-8"))
        self.assertIn("1 row ready, 1 needs fixing", plain(page))
        self.assertIn("Row 3: Keep at least uses a comma. Write decimals with a full stop, like 1.5.", plain(page))
        self.post("/settings/import/send", self.form(page))
        values = proposals.json.loads(self.conn.execute("SELECT values_json FROM core__proposals").fetchone()[0])
        self.assertEqual(values, {"name": "Crème fraîche", "minimum": "1,000", "notes": "Dairy; keep cold\nsecond line"})

    def test_a_file_that_is_not_utf8_is_refused_without_changing_letters(self):
        response = self.upload("", raw="name\nCrème\n".encode("latin-1"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("not saved as UTF-8", response.get_data(as_text=True))

    def test_a_broken_quote_is_reported_by_row(self):
        response = self.upload('name,notes\nRice,"fine"\nOats,"never closed\n')
        self.assertIn("Row 3 could not be read: check its quote marks", response.get_data(as_text=True))

    def test_formula_looking_cells_are_kept_as_plain_text(self):
        text = 'name,notes\n=HYPERLINK("http://example.com"),+1 spare\n@SUM(A1:A3),-2 used\n'
        _response, page = self.check(text)
        self.assertIn("2 rows ready", plain(page))
        self.post("/settings/import/send", self.form(page))
        batch = self.conn.execute("SELECT id FROM core__helper_batches").fetchone()[0]
        self.post(f"/review/batch/{batch}/accept-all")
        rows = self.conn.execute("SELECT name, notes FROM stock__items ORDER BY id").fetchall()
        self.assertEqual([tuple(r) for r in rows], [('=HYPERLINK("http://example.com")', "+1 spare"),
                                                    ("@SUM(A1:A3)", "-2 used")])

    def test_changed_matches_are_checked_again_before_sending(self):
        _response, page = self.check(EXAMPLE, {"match_7": "drinking"})
        response = self.go(page, match_8="")
        self.assertIn("The matches changed since the rows were checked", response.get_data(as_text=True))
        self.assertEqual(self.count("core__proposals"), 0)

    def test_a_field_matched_twice_or_a_needed_field_missing_is_explained(self):
        _response, page = self.check(EXAMPLE, {"match_0": "", "match_3": "notes"})
        self.assertIn("Every row needs Name. Match one of the columns to it.", plain(page))
        self.assertIn("Notes is matched to more than one column.", plain(page))

    def test_the_file_is_not_written_anywhere(self):
        marker = "Synthetic-marker-7f3a"
        page = self.upload(f"name\n{marker}\n").get_data(as_text=True)
        self.assertIn(marker, plain(page))
        self.conn.close()
        for path in self.data.rglob("*"):
            if path.is_file():
                self.assertNotIn(marker.encode(), path.read_bytes(), path)
        self.conn = db.connect(self.data / "dashboard.db")
        with self.app.test_request_context("/settings/import", method="POST"):
            from flask import request
            self.assertIsInstance(request, UploadRequest)
            self.assertIsInstance(request._get_file_stream(5_000_000, "text/csv", "a.csv"), io.BytesIO)
            self.assertEqual(request.max_content_length, 3_000_000)
        with self.app.test_request_context("/t/stock__items", method="POST"):
            self.assertIsNone(request.max_content_length)

    def test_helpers_never_see_an_import_batch(self):
        helper, _key = helpers.issue(self.conn, self.data, "Receipt helper", "suggest", ["stock"])
        _response, page = self.check(EXAMPLE, {"match_7": "drinking"})
        self.go(page)
        batch = self.conn.execute("SELECT id FROM core__helper_batches").fetchone()[0]
        self.assertEqual(proposals.helper_batches(self.conn, helper, None, 20), [])
        self.assertFalse(proposals.owns(self.conn, helper, batch))
        self.assertEqual(proposals.used_today(self.conn, helper), 0)

    def test_the_helper_check_on_derived_amounts_still_applies(self):
        wrong = self.store.check_create([("stock__items", {"name": "Rice", "quantity": 2})], "person")
        self.assertIn("quantity", wrong[0])
        self.assertEqual(self.store.check_create([("stock__items", {"name": "Rice", "quantity": 2})], "person",
                                                 starting_amounts=True), {})

    def test_file_names_become_safe_labels_and_actors(self):
        self.assertEqual(proposals.source_label("C:\\Users\\Someone\\My Pantry.CSV"), "My Pantry.CSV")
        self.assertEqual(proposals.import_actor("My Pantry.CSV"), "import:my-pantry.csv")
        self.assertEqual(proposals.import_actor("???"), "import:spreadsheet")
        self.assertRegex(proposals.import_actor("a" * 200), r"^import:a{60}$")
        self.assertTrue(records.ACTOR.match(proposals.import_actor("Stock list (2027).csv")))


class ImportMigrationTests(TempDirTestCase):
    def test_helper_batches_waiting_before_the_change_are_kept(self):
        conn = db.connect(self.tmp / "dashboard.db")
        self.addCleanup(conn.close)
        core = migrations.load_track(migrations.CORE_TRACK, migrations.CORE_FOLDER)
        migrations.migrate(conn, {migrations.CORE_TRACK: core[:3]})
        with db.transaction(conn):
            conn.execute("INSERT INTO core__helpers (id, key_id, slug, name, access, created_at) "
                         "VALUES (1, 'k1', 'receipts', 'Receipt helper', 'suggest', '2026-11-18')")
            conn.execute("INSERT INTO core__helper_batches (id, helper_id, request_key, body_hash, why, created_at) "
                         "VALUES (7, 1, 'r1', 'h', 'Receipt', '2026-11-18')")
            conn.execute("INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at) "
                         "VALUES (7, 0, 'stock__places', '{\"name\": \"Shed\"}', '2026-11-18')")
        migrations.migrate(conn, {migrations.CORE_TRACK: core})
        batch = conn.execute("SELECT * FROM core__helper_batches").fetchone()
        self.assertEqual((batch["id"], batch["kind"], batch["helper_id"], batch["source_name"]),
                         (7, "helper", 1, None))
        self.assertEqual(conn.execute("SELECT batch_id, source_row FROM core__proposals").fetchone()[:], (7, None))
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        with self.assertRaises(db.sqlite3.IntegrityError):  # still points at a real batch
            conn.execute("INSERT INTO core__proposals (batch_id, position, table_name, values_json, created_at) "
                         "VALUES (99, 0, 'x', '{}', 'now')")
        with self.assertRaises(db.sqlite3.IntegrityError):  # a helper batch needs its helper
            conn.execute("INSERT INTO core__helper_batches (kind, request_key, body_hash, why, created_at) "
                         "VALUES ('helper', 'r2', 'h', 'w', 'now')")


if __name__ == "__main__":
    import unittest
    unittest.main()
