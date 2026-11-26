"""Tests for Bring in earlier entries (decision 0137): a person's own CSV of doses, weigh-ins or feedings, previewed, added at once and undone at once."""
import html
import io
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import csv_bring_in as bring_in, csv_import, daily, db, helpers, modules, records, settings, startup
from dashboard.web.app import create_app

PORT = 5161
BASE = f"http://127.0.0.1:{PORT}"
DOSES = "medicine_doses__doses"
WEIGHS = "pets__weigh_ins"
FEEDS = "pet_feeding__servings"
INFO = "people__important_info"
SECRET = "Zebra sentinel medicine 41"  # an invented medication detail: never shown before Show
AMOUNT = "7.25"  # an invented private amount
DOSE_CSV = (
    "Date,Time,Given to,Medicine,Amount,Unit,Who gave it\n"
    f"13/02/26,8:00 am,Rosa Garcia,{SECRET},{AMOUNT},tablet,Maria Garcia\n"
    f"13/02/26,8:00 pm,rosa garcia,  zebra SENTINEL medicine 41 ,1,tablet,\n"
    "14/02/26,08:00,Rosa Garcia,Invented eye drops,2,drop,Maria Garcia\n"
)


def plain(page: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", page)).split())


class BringInTestCase(TempDirTestCase):
    MODULES = ("people", "medicine_doses", "pets", "pet_feeding")

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
        settings.put(self.conn, "household.country", "Australia")
        settings.put(self.conn, daily.ZONE_KEY, "Australia/Sydney")
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        person = lambda name: self.store.create("people__people", {"name": name, "lives_here": True})  # noqa: E731
        self.rosa, self.maria = person("Rosa Garcia"), person("Maria Garcia")
        detail = lambda who, text: self.store.create(INFO, {"person": who, "kind": "medication", "detail": text})  # noqa: E731
        self.med, self.drops = detail(self.rosa, SECRET), detail(self.rosa, "Invented eye drops")
        self.maria_med = detail(self.maria, "Invented inhaler")
        self.pet = self.store.create("pets__pets", {"name": "Biscuit", "species": "dog"})
        self.app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)
        self.csrf = self.app.config["CSRF_TOKEN"]

    # ----- helpers -------------------------------------------------------------------------------------------
    def post(self, path, data=None, token=True, **kwargs):
        return self.client.post(path, base_url=BASE, data=dict(data or {}, **({"_csrf": self.csrf} if token else {})),
                                **kwargs)

    def upload(self, table, text, name="old-tracker.csv", shown=True, raw=None):
        body = raw if raw is not None else text.encode("utf-8")
        data = {"file": (io.BytesIO(body), name)}
        if shown:
            data["shown"] = "1"
        return self.post(f"/bring-in/{table}/read", data, content_type="multipart/form-data")

    @staticmethod
    def form(page):
        """The hidden fields, matches and choices of a page, as the browser would send them back."""
        found = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', page))
        found.pop("_csrf", None)
        for name in re.findall(r'<select id="((?:match|pick)_\w+)"', page):
            block = re.search(rf'<select id="{name}".*?</select>', page, re.S).group(0)
            chosen = re.search(r'<option value="([\w@]*)" selected', block)
            found[name] = chosen.group(1) if chosen else ""
        for name in re.findall(r'<input type="checkbox" name="(\w+)" value="1" checked', page):
            found[name] = "1"
        return {k: html.unescape(v) for k, v in found.items()}

    def check(self, table, text, changes=None, **kwargs):
        page = self.upload(table, text, **kwargs).get_data(as_text=True)
        reply = self.post(f"/bring-in/{table}/check", dict(self.form(page), **(changes or {})))
        return reply, reply.get_data(as_text=True)

    def again(self, table, page, changes=None):
        reply = self.post(f"/bring-in/{table}/check", dict(self.form(page), **(changes or {})))
        return reply, reply.get_data(as_text=True)

    def add(self, table, page, **extra):
        return self.post(f"/bring-in/{table}/add", dict(self.form(page), **extra))

    def live(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE deleted_at IS NULL").fetchone()[0]

    def audits(self):
        return self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]

    def files(self):
        return sorted(str(p.relative_to(self.data)) for p in self.data.rglob("*") if p.is_file())


class DeclarationTests(BringInTestCase):
    def test_the_dated_logs_opt_in_and_other_lists_do_not(self):
        for table, when, per in ((DOSES, "given_at", "recipient"), (WEIGHS, "day", "pet"), (FEEDS, "given_at", "pet")):
            rule = self.registry[table].table.bring_in
            self.assertEqual((rule["when"], rule["per"]), (when, per))
        self.assertFalse(self.registry["pets__pets"].table.bring_in)
        self.assertEqual(self.client.get("/bring-in/pets__pets", base_url=BASE).status_code, 404)
        self.assertEqual(self.client.get("/bring-in/nothing__here", base_url=BASE).status_code, 404)

    def test_the_module_checker_refuses_a_wrong_declaration_at_load(self):
        bad = {
            'bring_in = { when = "notes", per = "pet" }': "'when' must name a required date",
            'bring_in = { when = "day", per = "secret" }': "'per' must name a required link",
            'bring_in = { when = "day", per = "pet", colour = "red" }': "colour",
            'bring_in = { when = "day", per = "pet", entry = ["one"] }': "'entry' must be two words",
            'bring_in = "yes"': "write it as",
        }
        for line, words in bad.items():
            with self.subTest(line=line):
                folder = self.make_module("demo", tables=(
                    '[tables.pets]\ntitle = "Pets"\ncolumns.name = { type = "text", required = true }\n\n'
                    '[tables.logs]\ntitle = "Logs"\ncolumns.pet = { type = "link", to = "pets", required = true }\n'
                    'columns.day = { type = "date", required = true }\ncolumns.notes = { type = "text" }\n'
                    'columns.secret = { type = "link", to = "pets", required = true, sensitive = true }\n'
                    f'{line}\n'), labels=None, root=f"bad{abs(hash(line))}")
                _found, problems = modules.discover(folder.parent)
                self.assertTrue(any(words in p for ps in problems.values() for p in ps), problems)

    def test_list_pages_and_the_import_page_lead_here(self):
        for table in (DOSES, WEIGHS, FEEDS):
            page = self.client.get(f"/t/{table}", base_url=BASE).get_data(as_text=True)
            self.assertIn(f'href="/bring-in/{table}"', page)
        page = self.client.get("/settings/import", base_url=BASE).get_data(as_text=True)
        self.assertIn(f'href="/bring-in/{DOSES}"', page)
        self.assertNotIn(f'value="{DOSES}"', page)  # Import to Review still never offers private doses (0120)


class PrivateDoseTests(BringInTestCase):
    def test_nothing_private_and_no_file_choice_before_show(self):
        self.store.create(DOSES, {"recipient": self.rosa, "medication": self.med, "given_at": "2026-01-01T08:00",
                                  "amount": AMOUNT, "unit": "tablet"})
        page = self.client.get(f"/bring-in/{DOSES}", base_url=BASE).get_data(as_text=True)
        self.assertIn("data-show-bring-in", page)
        self.assertNotIn('type="file"', page)
        self.assertNotIn(SECRET, page)
        self.assertNotIn(AMOUNT, page)
        self.assertIn("never saved to disk and never sent anywhere", plain(page))
        shown = self.post(f"/bring-in/{DOSES}/show").get_data(as_text=True)
        self.assertIn('type="file"', shown)
        self.assertNotIn(SECRET, shown)  # Show leads to the file choice; it does not list existing doses
        refused = self.upload(DOSES, DOSE_CSV, shown=False)  # a file sent without the pressed Show
        self.assertEqual(refused.status_code, 400)
        self.assertNotIn(SECRET, refused.get_data(as_text=True))
        for step in ("check", "add"):
            reply = self.post(f"/bring-in/{DOSES}/{step}", {"data": "", "match_0": "given_at"})
            self.assertEqual(reply.status_code, 400)
            self.assertNotIn(SECRET, reply.get_data(as_text=True))

    def test_the_full_preview_after_show_writes_nothing(self):
        before, files = (self.live(DOSES), self.audits()), self.files()
        reply, page = self.check(DOSES, DOSE_CSV)
        self.assertEqual(reply.status_code, 200)
        text = plain(page)
        self.assertIn("3 doses to bring in", text)
        self.assertIn(SECRET, text)  # after Show, this page shows the person's own private values
        self.assertIn("Invented eye drops", text)
        self.assertIn("7.25", text)
        self.assertIn("13/02/26 20:00", text)
        self.assertIn("Nothing has been added yet", text)
        self.assertEqual((self.live(DOSES), self.audits()), before)
        self.assertEqual(self.files(), files)  # the file is not written into the data folder
        self.assertEqual(reply.headers["Cache-Control"], "no-store")

    def test_bring_in_adds_every_row_in_one_go_with_history_and_one_undo(self):
        existing = self.store.create(DOSES, {"recipient": self.rosa, "medication": self.drops,
                                             "given_at": "2026-01-10T09:00"})
        _reply, page = self.check(DOSES, DOSE_CSV)
        added = self.add(DOSES, page)
        self.assertEqual(added.status_code, 302)
        location = added.headers["Location"]
        self.assertRegex(location, r"/bring-in/medicine_doses__doses/done/\d+$")  # nothing private in the address
        self.assertEqual(self.live(DOSES), 4)
        rows = self.conn.execute(f"SELECT * FROM {DOSES} WHERE id != ? ORDER BY given_at", (existing,)).fetchall()
        self.assertEqual([r["given_at"] for r in rows],
                         ["2026-02-13T08:00:00", "2026-02-13T20:00:00", "2026-02-14T08:00:00"])
        self.assertEqual([r["medication"] for r in rows], [self.med, self.med, self.drops])
        self.assertEqual([r["given_by"] for r in rows], [self.maria, None, self.maria])
        self.assertEqual(rows[0]["amount"], 7.25)
        for row in rows:
            history = self.store.history(DOSES, row["id"])
            self.assertEqual([(h["action"], h["actor"]) for h in history], [("create", "import:earlier-entries")])
        again = self.add(DOSES, page)  # a second press of the same page adds nothing more
        self.assertEqual(again.headers["Location"], location)
        self.assertEqual(self.live(DOSES), 4)
        done = self.client.get(location, base_url=BASE).get_data(as_text=True)
        self.assertIn("3 doses brought in", plain(done))
        self.assertNotIn(SECRET, done)
        self.assertNotIn("old-tracker", done)  # a private list never names the file
        audit_id = int(location.rsplit("/", 1)[1])
        undone = self.post(f"/bring-in/{DOSES}/undo", {"bring_in": audit_id})
        self.assertEqual(undone.status_code, 200)
        self.assertIn("Undone: 3 doses taken off again", plain(undone.get_data(as_text=True)))
        live = [r[0] for r in self.conn.execute(f"SELECT id FROM {DOSES} WHERE deleted_at IS NULL")]
        self.assertEqual(live, [existing])  # exactly the imported rows went; the earlier dose stays
        twice = self.post(f"/bring-in/{DOSES}/undo", {"bring_in": audit_id})
        self.assertEqual(twice.status_code, 409)
        self.assertEqual(self.live(DOSES), 1)

    def test_undo_is_refused_once_an_imported_entry_changed(self):
        _reply, page = self.check(DOSES, DOSE_CSV)
        audit_id = int(self.add(DOSES, page).headers["Location"].rsplit("/", 1)[1])
        first = bring_in.summary(self.store, self.registry[DOSES], audit_id)["ids"][0]
        self.store.update(DOSES, first, {"given_by": self.rosa})
        reply = self.post(f"/bring-in/{DOSES}/undo", {"bring_in": audit_id})
        self.assertEqual(reply.status_code, 409)
        self.assertIn("changed or deleted since", plain(reply.get_data(as_text=True)))
        self.assertEqual(self.live(DOSES), 3)

    def test_an_unknown_medicine_is_only_ever_matched_to_existing_details_by_the_persons_choice(self):
        text = DOSE_CSV + "15/02/26,9:00 am,Rosa Garcia,Mystery pill,1,tablet,\n" \
                          "16/02/26,9:00 am,Rosa Garcia,Mystery pill,1,tablet,\n" \
                          "16/02/26,9:00 am,Rosa Garcia,Invented inhaler,1,puff,\n"  # Maria's, not Rosa's
        details = self.live(INFO)
        _reply, page = self.check(DOSES, text)
        self.assertIn("Names to match", page)
        self.assertIn("3 doses to bring in", plain(page))
        self.assertIn("needs your choice", plain(page))
        keys = re.findall(r'name="pick_(\w+)"', page)
        self.assertEqual(len(keys), 2)  # each unknown name once, for Rosa
        self.assertNotIn(f'value="{self.maria_med}"', re.search(r'<select id="pick_.*', page, re.S).group(0)
                         .split("</select>")[0])  # another person's medicine is never offered
        pick = {f"pick_{k}": "" for k in keys}
        mystery = next(k for k in keys if re.search(rf'for="pick_{k}"[^>]*>Medicine “<bdi>Mystery pill', page))
        inhaler = next(k for k in keys if k != mystery)
        _reply, page = self.again(DOSES, page, dict(pick, **{f"pick_{mystery}": str(self.drops),
                                                            f"pick_{inhaler}": "skip"}))
        text_now = plain(page)
        self.assertIn("5 doses to bring in", text_now)
        self.assertIn("1 row left out as you chose", text_now)
        self.add(DOSES, page)
        self.assertEqual(self.live(INFO), details)  # nothing new was made in People
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {DOSES} WHERE medication = ?",
                                           (self.drops,)).fetchone()[0], 3)

    def test_a_dose_at_the_same_minute_as_one_recorded_is_skipped_unless_chosen(self):
        self.store.create(DOSES, {"recipient": self.rosa, "medication": self.drops, "given_at": "2026-02-13T08:00"})
        _reply, page = self.check(DOSES, DOSE_CSV)
        text = plain(page)
        self.assertIn("2 doses to bring in", text)
        self.assertIn("Row 2:", text.split("Possible repeats", 1)[1])
        self.assertIn("is already recorded", text)
        _reply, page = self.again(DOSES, page, {"add_2": "1"})
        self.assertIn("3 doses to bring in", plain(page))
        self.add(DOSES, page)
        self.assertEqual(self.live(DOSES), 4)


class WeighInAndFeedingTests(BringInTestCase):
    def test_weigh_ins_by_pet_name_in_kg_only_with_unclear_dates_asked(self):
        text = ("Pet,Date,Weight,Notes\n"
                "biscuit,20/01/26,21.3 kg,Before the walk\n"
                "Biscuit,3/2/26,21.5,\"=HYPERLINK(\"\"http://example.invalid\"\",\"\"x\"\")\"\n"
                "Biscuit,10/02/26,47 lb,\n"
                "Biscuit,10/02/26,21.9,<script>alert(1)</script>\n")
        _reply, page = self.check(WEIGHS, text)
        words = plain(page)
        self.assertIn("is in lb, and this list records kg. Nothing is converted", words)
        self.assertIn("could be read either way", words)
        self.assertIn("3 weigh-ins to bring in", words)
        self.assertNotIn("<script>alert(1)</script>", page)  # shown as words, never run
        self.assertIn("&lt;script&gt;", page)
        blocked = self.add(WEIGHS, page)
        self.assertEqual(blocked.status_code, 200)  # the dates box was not ticked
        self.assertEqual(self.live(WEIGHS), 0)
        _reply, page = self.again(WEIGHS, page, {"dates_ok": "1"})
        location = self.add(WEIGHS, page).headers["Location"]
        rows = self.conn.execute(f"SELECT day, weight, notes, source FROM {WEIGHS} ORDER BY day").fetchall()
        self.assertEqual([(r["day"], r["weight"]) for r in rows],
                         [("2026-01-20", 21.3), ("2026-02-03", 21.5), ("2026-02-10", 21.9)])
        self.assertEqual(rows[1]["notes"], '=HYPERLINK("http://example.invalid","x")')  # kept as words, not worked out
        self.assertEqual(rows[0]["source"], "import:old-tracker.csv")
        done = self.client.get(location, base_url=BASE).get_data(as_text=True)
        self.assertIn("old-tracker.csv", done)  # an ordinary list names its file, as Import does

    def test_an_unknown_pet_is_never_created(self):
        _reply, page = self.check(WEIGHS, "Pet,Date,Weight\nRex,20/01/26,30\n")
        self.assertIn("Names to match", page)
        self.assertIn("0 weigh-ins to bring in", plain(page))
        self.assertRegex(page, r'formaction="/bring-in/pets__weigh_ins/add" disabled')
        self.assertEqual(self.live("pets__pets"), 1)

    def test_feedings_with_a_date_and_time_or_a_separate_time_column_by_the_households_clock(self):
        text = ("Pet,When,Food,Amount,Unit\n"
                "Biscuit,2026-02-01 07:30,Dry food,120,g\n"
                "Biscuit,2026-02-01T18:00+00:00,Dry food,100,g\n"
                "Biscuit,01/02/26,Treat,1,piece\n")
        _reply, page = self.check(FEEDS, text)
        self.assertIn("has a date but no time", plain(page))
        self.assertIn("2 feedings to bring in", plain(page))
        self.add(FEEDS, page)
        stored = [r[0] for r in self.conn.execute(f"SELECT given_at FROM {FEEDS} ORDER BY id")]
        self.assertEqual(stored, ["2026-02-01T07:30:00", "2026-02-01T18:00:00+00:00"])  # local kept, an instant kept
        zone = daily.household_zone(self.conn)
        self.assertEqual(daily.local_day(stored[1], zone), "2026-02-02")  # 5 am the next day in Sydney
        separate = ("Pet,Date,Time,Food\nBiscuit,20/02/26,7.15 pm,Wet food\nBiscuit,20/02/26,,Wet food\n")
        _reply, page = self.check(FEEDS, separate)
        self.assertIn("1 feeding to bring in", plain(page))
        self.add(FEEDS, page)
        self.assertEqual(self.conn.execute(f"SELECT given_at FROM {FEEDS} ORDER BY id DESC").fetchone()[0],
                         "2026-02-20T19:15:00")

    def test_a_repeated_row_inside_the_file_is_a_possible_repeat_too(self):
        _reply, page = self.check(WEIGHS, "Pet,Date,Weight\nBiscuit,20/01/26,21\nBiscuit,20/01/26,21\n")
        words = plain(page)
        self.assertIn("1 weigh-in to bring in", words)
        self.assertIn("Row 2 has the same pet and the same day", words)


class SafetyTests(BringInTestCase):
    def test_a_file_that_is_too_large_or_too_long_or_not_text_is_refused_and_nothing_is_kept(self):
        files = self.files()
        big = self.upload(WEIGHS, "", raw=b"Pet,Date,Weight\n" + b"Biscuit,20/01/26,21\n" * 60_000)
        self.assertEqual(big.status_code, 413)
        self.assertIn("The limit is 1 MB", plain(big.get_data(as_text=True)))
        huge = self.upload(WEIGHS, "", raw=b"x" * (4 * csv_import.MAX_BYTES))
        self.assertEqual(huge.status_code, 413)
        long = self.upload(WEIGHS, "Pet,Date,Weight\n" + "Biscuit,20/01/26,21\n" * (csv_import.MAX_ROWS + 5))
        self.assertIn("more than 2,000 rows", plain(long.get_data(as_text=True)))
        binary = self.upload(WEIGHS, "", raw="Pet,Date\nBiscuit,20/01/26\n".encode("utf-16"))
        self.assertIn("not saved as UTF-8", plain(binary.get_data(as_text=True)))
        self.assertEqual(self.files(), files)
        self.assertEqual(self.live(WEIGHS), 0)

    def test_hidden_characters_and_a_tampered_page_are_caught(self):
        _reply, page = self.check(WEIGHS, "Pet,Date,Weight,Notes\nBiscuit,20/01/26,21,a‮b\n")
        self.assertIn("hidden character", plain(page))
        _reply, page = self.check(WEIGHS, "Pet,Date,Weight\nBiscuit,20/01/26,21\n")
        tampered = dict(self.form(page), match_2="")  # a match changed after the check
        reply = self.post(f"/bring-in/{WEIGHS}/add", tampered)
        self.assertIn("Every row needs Weight", plain(reply.get_data(as_text=True)))
        self.assertEqual(self.live(WEIGHS), 0)
        reply = self.post(f"/bring-in/{WEIGHS}/add", dict(self.form(page), count="9"))
        self.assertIn("Your records changed", plain(reply.get_data(as_text=True)))
        self.assertEqual(self.live(WEIGHS), 0)

    def test_only_the_household_signed_in_page_reaches_it_never_a_helper(self):
        _helper, key = helpers.issue(self.conn, self.data, "Care helper", "suggest", ["pets", "medicine_doses"])
        stranger = self.app.test_client()  # no session cookie: a helper or another program
        for path in (f"/bring-in/{DOSES}", f"/bring-in/{WEIGHS}"):
            reply = stranger.get(path, base_url=BASE, headers={"Authorization": f"Bearer {key}"})
            self.assertEqual(reply.status_code, 302)
            self.assertTrue(reply.headers["Location"].endswith("/start"))
        reply = stranger.post(f"/bring-in/{WEIGHS}/read", base_url=BASE, headers={"Authorization": f"Bearer {key}"},
                              data={"file": (io.BytesIO(b"Pet,Date,Weight\nBiscuit,20/01/26,21\n"), "x.csv")},
                              content_type="multipart/form-data")
        self.assertEqual(reply.status_code, 302)
        no_token = self.upload(WEIGHS, "Pet,Date,Weight\nBiscuit,20/01/26,21\n")
        self.assertEqual(no_token.status_code, 200)
        missing = self.client.post(f"/bring-in/{WEIGHS}/read", base_url=BASE,
                                   data={"file": (io.BytesIO(b"Pet,Date,Weight\n"), "x.csv")},
                                   content_type="multipart/form-data")  # no page token
        self.assertEqual(missing.status_code, 400)
        api = self.client.get(f"/api/v1/bring-in/{DOSES}", base_url=BASE, headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(api.status_code, 404)
        self.assertEqual(self.live(WEIGHS), 0)

    def test_private_values_never_reach_an_address_or_the_log(self):
        with self.assertLogs("dashboard", level="DEBUG") as logs:
            import logging
            logging.getLogger("dashboard").debug("start")
            _reply, page = self.check(DOSES, DOSE_CSV)
            location = self.add(DOSES, page).headers["Location"]
        self.assertNotIn(SECRET, "\n".join(logs.output))
        self.assertNotIn(SECRET.split()[0], location)
        summary = self.conn.execute("SELECT after FROM core__audit WHERE action = 'bring_in'").fetchone()[0]
        self.assertNotIn(SECRET, summary)
        self.assertNotIn(AMOUNT, summary)
