"""Tests for Medicine doses (decision 0120): same person and medication kind on every save, no helpers or imports, private until Show.

They follow the checks in Lane B's draft (its ACCEPTANCE.md, now in git history) that a computer can run, plus the
household's own day around midnight, each medicine's own totals, the possible-repeat question on the form, switching
the module off and on, and the example. Member phones and pairing are not built, so offline saves are not tested."""
import io
import json
import re
import shutil
import zipfile
from datetime import date, datetime, timezone
from urllib.parse import parse_qs, urlparse

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import csv_import, daily, db, export, helpers, modules, proposals, records, settings, startup, sync
from dashboard.core.schema import next_migration_sql
from dashboard.web.app import create_app
import load_example

PORT = 5147
BASE = f"http://127.0.0.1:{PORT}"
TABLE = "medicine_doses__doses"
INFO = "people__important_info"
SECRET = "Zebra sentinel medicine 41"  # an invented medication detail: never on an ordinary page or file
AMOUNT = "7.25"  # an invented amount: hidden until Show
MODULE_TOML = (ROOT / "modules" / "medicine_doses" / "module.toml").read_text(encoding="utf-8").replace(
    'name = "medicine_doses"', 'name = "demo"')
SYDNEY_NOON = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)  # 20 Nov 2026, 12:00 in Sydney


class DoseTestCase(TempDirTestCase):
    MODULES = ("people", "medicine_doses")

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
        self.records = records.Records(self.conn, self.registry)
        self.info = self.registry[TABLE]
        self.rule = self.info.table.daily
        settings.put(self.conn, daily.ZONE_KEY, "Australia/Sydney")
        self.zone = daily.household_zone(self.conn)
        person = lambda name: self.records.create("people__people", {"name": name, "lives_here": True})
        self.rosa, self.maria, self.sofia = person("Rosa Garcia"), person("Maria Garcia"), person("Sofia Garcia")
        detail = lambda who, kind, text: self.records.create(INFO, {"person": who, "kind": kind, "detail": text})
        self.med = detail(self.rosa, "medication", SECRET)
        self.med2 = detail(self.rosa, "medication", "Invented eye drops")
        self.allergy = detail(self.rosa, "allergy", "Invented allergy")
        self.sofia_med = detail(self.sofia, "medication", "Invented inhaler")

    def dose(self, med=None, at="2026-11-20T08:00:00", who=None, **values):
        return self.records.create(TABLE, {"recipient": who or self.rosa, "medication": med or self.med,
                                           "given_at": at, "given_by": self.maria, **values})

    def refused(self, call, field="medication"):
        with self.assertRaises(records.ValidationError) as caught:
            call()
        self.assertIn(field, caught.exception.problems)
        self.assertNotIn(SECRET, str(caught.exception))
        return caught.exception.problems[field]

    def client(self, now=SYDNEY_NOON):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: now
        app.config["TODAY"] = lambda: now.astimezone(self.zone).date()
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None, status=200):
        response = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)

    def post(self, client, path, **data):
        return client.post(path, base_url=BASE, data={"_csrf": client.csrf, **data})

    def count(self):
        return self.conn.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE deleted_at IS NULL").fetchone()[0]


class SamePersonAndKindTests(DoseTestCase):
    def test_a_dose_must_be_the_recipients_own_medication_on_create_and_change(self):
        self.assertIn("one of this person's own medication details",
                      self.refused(lambda: self.dose(med=self.sofia_med)))  # another person's medicine
        self.refused(lambda: self.dose(med=self.allergy))  # the right person, but an allergy
        self.refused(lambda: self.dose(med=999), "medication")  # nothing there at all
        entry = self.dose()
        self.refused(lambda: self.records.update(TABLE, entry, {"recipient": self.sofia}))
        self.refused(lambda: self.records.update(TABLE, entry, {"medication": self.sofia_med}))
        self.records.update(TABLE, entry, {"medication": self.med2})  # another of Rosa's own: fine
        self.assertEqual(self.records.get(TABLE, entry)["medication"], self.med2)
        self.assertEqual(self.count(), 1)

    def test_the_medication_detail_cannot_move_away_from_its_doses_but_its_words_can_change(self):
        self.dose()
        self.refused(lambda: self.records.update(INFO, self.med, {"kind": "allergy"}), "kind")
        self.refused(lambda: self.records.update(INFO, self.med, {"person": self.sofia}), "person")
        self.records.update(INFO, self.med, {"detail": "Invented new wording"})  # the summary itself may change
        self.records.update(INFO, self.sofia_med, {"kind": "allergy"})  # a detail with no doses is free

    def test_deleting_the_person_or_the_medicine_is_refused_while_doses_point_at_them(self):
        self.dose()
        for table, record in (("people__people", self.rosa), (INFO, self.med), ("people__people", self.maria)):
            with self.assertRaises(records.ValidationError):
                self.records.delete(table, record)
            self.assertIsNone(self.records.get(table, record)["deleted_at"])

    def test_a_deleted_dose_comes_back_only_if_it_still_fits(self):
        entry = self.dose()
        self.records.delete(TABLE, entry)
        self.records.update(INFO, self.med, {"kind": "condition"})  # allowed: no live dose points at it now
        with self.assertRaises(records.ValidationError) as caught:
            self.records.restore(TABLE, entry)
        self.assertIn("no longer fits", caught.exception.problems["restore"])
        self.records.update(INFO, self.med, {"kind": "medication"})
        self.records.restore(TABLE, entry)
        self.assertIsNone(self.records.get(TABLE, entry)["deleted_at"])

    def test_the_dry_run_used_by_review_and_imports_refuses_it_too(self):
        problems = self.records.check_create([(TABLE, {"recipient": self.rosa, "medication": self.sofia_med,
                                                       "given_at": "2026-11-20T08:00"})], "person")
        self.assertIn("medication", problems[0])

    def test_a_crafted_form_is_refused_whatever_the_list_showed(self):
        client = self.client()
        reply = self.post(client, f"/t/{TABLE}/new", recipient=str(self.rosa), medication=str(self.sofia_med),
                          given_at="2026-11-20T08:00", then="done")
        self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.count(), 0)
        self.assertNotIn(SECRET, reply.get_data(as_text=True))
        entry = self.dose()
        reply = self.post(client, f"/t/{TABLE}/{entry}", recipient=str(self.sofia), medication=str(self.med),
                          given_at="2026-11-20T08:00")
        self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.records.get(TABLE, entry)["recipient"], self.rosa)

    def test_the_form_lists_only_medication_details_by_kind_and_number_following_the_person(self):
        form = self.page(f"/t/{TABLE}/new?recipient={self.rosa}")
        select = re.search(r'<select id="f-medication".*?</select>', form, re.S).group(0)
        self.assertIn('data-follows="recipient"', select)
        self.assertIn(f'<option value="{self.med}" data-owner="{self.rosa}" >Medication #{self.med}</option>', select)
        self.assertIn(f'data-owner="{self.sofia}"', select)  # hidden by the page while Rosa is chosen
        self.assertNotIn(f'value="{self.allergy}"', select)
        for words in (SECRET, "Invented eye drops", "Invented inhaler"):
            self.assertNotIn(words, form)
        self.assertIn(f'data-reveal-link="/t/{INFO}/{{id}}/reveal?column=detail"', form)
        self.assertIn('<option value="">I do not know</option>', form)


class NoHelpersOrImportsTests(DoseTestCase):
    def test_helpers_never_see_or_suggest_doses_even_when_given_the_module(self):
        self.dose()
        helper, key = helpers.issue(self.conn, self.data, "Care helper", "suggest", ["people", "medicine_doses"])
        self.assertNotIn(TABLE, helpers.allowed_registry(self.registry, helper))
        with self.assertRaises(proposals.ProposalError) as caught:
            proposals.submit(self.conn, self.registry, helper, {"request_key": "d1", "why": "From the chart",
                             "entries": [{"table": TABLE, "values": {"recipient": self.rosa, "medication": self.med,
                                                                      "given_at": "2026-11-20T08:00:00"}}]})
        self.assertEqual(caught.exception.code, "not_found")
        client = self.client()
        auth = {"Authorization": f"Bearer {key}"}
        listed = client.get("/api/v1/tables", base_url=BASE, headers=auth).get_data(as_text=True)
        self.assertNotIn(TABLE, listed)
        self.assertEqual(client.get(f"/api/v1/tables/{TABLE}/records", base_url=BASE, headers=auth).status_code, 404)
        guide = client.get("/api/v1/guide", base_url=BASE, headers=auth).get_data(as_text=True)
        self.assertNotIn("Medicine doses", guide)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)
        settings_page = self.page("/settings/helpers", client)
        self.assertNotIn('value="medicine_doses"', settings_page)  # nothing a helper could use

    def test_a_spreadsheet_import_is_refused(self):
        self.assertIn("filled in on its own screens only", csv_import.why_not_table(self.info))


class PrivacyTests(DoseTestCase):
    def test_no_medicine_or_amount_on_home_lists_person_page_export_or_helpers_until_show(self):
        entry = self.dose(amount=AMOUNT, unit="drop")
        client = self.client()
        for path in ("/", f"/t/{TABLE}", f"/t/people__people/{self.rosa}", f"/t/{TABLE}/{entry}",
                     f"/daily/{TABLE}?subject={self.rosa}", "/attention", "/settings/export"):
            text = self.page(path, client)
            self.assertNotIn(SECRET, text, path)
            self.assertNotIn(AMOUNT, text, path)
        self.assertNotIn("Medicine doses", self.page("/", client))  # not on Home at all, not even a count
        self.page(f"/daily/{TABLE}/sheet?subject={self.rosa}", client, status=404)  # no printable sheet
        self.assertNotIn(SECRET, self.page(f"/daily/{TABLE}?subject={self.rosa}&show=1", client))  # a link: no
        shown = self.post(client, f"/daily/{TABLE}", subject=str(self.rosa)).get_data(as_text=True)  # pressed Show
        self.assertIn(SECRET, shown)
        self.assertIn("7.25 drops", shown)
        reveal = client.get(f"/t/{TABLE}/{entry}/reveal?column=amount", base_url=BASE).get_json()
        self.assertEqual(reveal["value"], AMOUNT)
        data = export.build(self.conn, self.registry, __version__)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            everything = b"".join(archive.read(n) for n in names).decode("utf-8", "replace")
        self.assertNotIn(f"{TABLE}.csv", names)
        self.assertNotIn(AMOUNT, everything)
        self.assertIn("Whole lists left out because every record in them is private history: Medicine doses",
                      everything)

    def test_every_column_travels_by_decision_and_the_log_holds_ids_not_medicine_words(self):
        start = self.conn.execute("SELECT COALESCE(MAX(seq), 0) FROM core__sync_changes").fetchone()[0]
        entry = self.dose(amount=1, unit="tablet")
        self.records.update(TABLE, entry, {"amount": 2})
        self.assertTrue(all(c.travels == "always" and c.travels_reviewed for c in self.info.table.columns.values()))
        self.assertEqual(sync.unreviewed(self.registry), [])
        self.assertEqual(sync.check(self.conn, self.registry), [])
        lines = [c for c in sync.changes(self.conn, start) if c["table_name"] == TABLE]
        self.assertEqual([c["action"] for c in lines], ["create", "update"])
        self.assertEqual(lines[0]["patch"]["amount"], 1.0)  # medical safety details travel to members (0089)
        medication = lines[0]["patch"]["medication"]
        self.assertNotEqual(str(medication), str(self.med))  # the permanent ID, not a local number or words
        self.assertNotIn(SECRET, json.dumps(lines))

    def test_the_module_checker_keeps_private_tables_off_sheets_and_away_from_helpers(self):
        tables = (ROOT / "modules" / "medicine_doses" / "tables.toml").read_text(encoding="utf-8")
        self.make_module("dosebad", module=MODULE_TOML,
                         tables=tables.replace("suggestions = false\n", "")
                         .replace('kind = "medication"', 'kind = "shopping"')
                         .replace('same = { person = "recipient" }', 'same = { person = "given_at" }'),
                         labels=None, root="bad")
        self.write("bad/dosebad/sheets.toml", '[[sheet]]\nname = "doses"\ntitle = "Doses"\n[[sheet.section]]\n'
                                              'table = "doses"\ncolumns = ["given_at"]\n')
        shutil.copytree(ROOT / "modules" / "people", self.tmp / "bad" / "people")
        _, failures = modules.discover(self.tmp / "bad")
        text = " ".join(failures.get("dosebad", []))
        self.assertIn("a private table must also say suggestions = false", text)
        self.assertIn("'doses' is a private table, so no sheet may print it", text)
        self.assertIn("link_rule 'same' must name another link column", text)
        shutil.rmtree(self.tmp / "bad" / "dosebad")
        self.make_module("dosebad", module=MODULE_TOML,
                         tables=tables.replace('kind = "medication"', 'kind = "shopping"'), labels=None, root="bad")
        _, failures = modules.discover(self.tmp / "bad")
        self.assertIn("'shopping' one of its choices", " ".join(failures.get("dosebad", [])))


class DayAndRepeatTests(DoseTestCase):
    def test_days_follow_the_household_zone_and_each_medicine_has_its_own_totals(self):
        self.dose(at="2026-11-20T08:00:00", amount=1, unit="tablet")
        self.dose(at="2026-11-20T13:30:00+00:00", amount=1, unit="tablet")  # 00:30 on 21 Nov in Sydney
        self.dose(med=self.med2, at="2026-11-20T21:00:00", amount=2, unit="drop")
        self.dose(at="2026-11-20T23:30:00")  # typed local time, no amount
        day = daily.days(self.conn, self.info, self.rosa, "2026-11-20", "2026-11-20", self.zone)[0]
        self.assertEqual(daily.count_words(self.rule, day), "3 dose entries recorded today")
        groups = {key: daily.totals_words(self.rule, part) if part.totals else "" for key, part in
                  daily.by_group(self.rule, day)}
        self.assertEqual(groups, {self.med: "1 tablet given", self.med2: "2 drops given"})  # never added together
        next_day = daily.days(self.conn, self.info, self.rosa, "2026-11-21", "2026-11-21", self.zone)[0]
        self.assertEqual(daily.count_words(self.rule, next_day, "on 21/11/26"), "1 dose entry recorded on 21/11/26")
        empty = daily.days(self.conn, self.info, self.sofia, "2026-11-20", "2026-11-20", self.zone)[0]
        self.assertEqual(daily.count_words(self.rule, empty), "No dose entry recorded today")
        page = self.post(self.client(), f"/daily/{TABLE}", subject=str(self.rosa), day="2026-11-20").get_data(as_text=True)
        self.assertIn(SECRET, page)
        self.assertIn("2 doses · 1 tablet given · 1 without an amount", page)
        for words in ("missed", "overdue", "due now", "not given"):
            self.assertNotIn(words, page.replace(self.rule["caveat"], "").lower())

    def test_a_close_dose_of_the_same_medicine_asks_first_and_can_still_be_kept(self):
        self.dose(at="2026-11-20T08:00:00")
        client = self.client()
        values = {"recipient": str(self.rosa), "medication": str(self.med), "given_at": "2026-11-20T09:30",
                  "given_by": str(self.maria), "then": "back", "back": f"/t/people__people/{self.rosa}"}
        held = self.post(client, f"/t/{TABLE}/new", **values)
        text = held.get_data(as_text=True)
        self.assertEqual(held.status_code, 200)
        self.assertIn("A dose of this medicine is already recorded for this person near this time.", text)
        self.assertIn("Already recorded: 8:00 am on 20/11/26.", text)
        self.assertIn(">Keep this as another dose</button>", text)
        self.assertEqual(self.count(), 1)  # a double press of Save stops here too
        token = re.search(r'name="_confirm" value="([^"]+)"', text).group(1)
        kept = self.post(client, f"/t/{TABLE}/new", _confirm=token, **values)
        self.assertEqual(kept.status_code, 302)
        self.assertEqual(self.count(), 2)
        other = self.post(client, f"/t/{TABLE}/new", **dict(values, medication=str(self.med2)))
        self.assertEqual((other.status_code, self.count()), (302, 3))  # another medicine: no question
        later = self.post(client, f"/t/{TABLE}/new", **dict(values, given_at="2026-11-20T12:00"))
        self.assertEqual((later.status_code, self.count()), (302, 4))  # more than two hours after both
        last = self.conn.execute(f"SELECT MAX(id) FROM {TABLE}").fetchone()[0]
        edit = self.post(client, f"/t/{TABLE}/{last}", recipient=str(self.rosa), medication=str(self.med),
                         given_at="2026-11-20T12:00", given_by="")
        self.assertEqual(edit.status_code, 302)  # changing an entry never matches itself

    def test_record_a_dose_fills_in_the_last_medicine_and_giver_but_never_the_amount(self):
        client = self.client()
        page = self.page(f"/t/people__people/{self.rosa}", client)
        self.assertIn("Medicine given today", page)
        self.assertIn("No dose entry recorded today", page)
        link = re.search(r'href="([^"]+)" data-add-entry>Record a dose<', page).group(1).replace("&amp;", "&")
        args = {k: v[0] for k, v in parse_qs(urlparse(link).query).items()}
        self.assertEqual(args, {"recipient": str(self.rosa), "given_at": "2026-11-20T12:00"})  # two medicines
        self.dose(at="2026-11-20T08:00:00", amount=AMOUNT, unit="drop")
        page = self.page(f"/t/people__people/{self.rosa}", client)
        self.assertIn("1 dose entry recorded today", page)
        self.assertIn("8:00 am · dose · Who gave it: Maria Garcia", page)
        self.assertNotIn(AMOUNT, page)
        link = re.search(r'href="([^"]+)" data-add-entry>Record a dose<', page).group(1).replace("&amp;", "&")
        args = {k: v[0] for k, v in parse_qs(urlparse(link).query).items()}
        self.assertEqual(args, {"recipient": str(self.rosa), "medication": str(self.med), "given_by": str(self.maria),
                                "given_at": "2026-11-20T12:00", "from": "last"})
        form = self.page(link, client)
        self.assertIn("Filled in from a recent entry. Check each answer before you save.", form)
        self.assertNotIn(AMOUNT, form)
        self.assertIn(f'name="back" value="/t/people__people/{self.rosa}"', form)  # Save goes back to Rosa
        self.assertNotIn("Medicine given today", self.page(f"/t/people__people/{self.maria}", client))  # no medicine
        self.assertNotIn("Add to medicine doses", page)  # no second, confusing add button


class ModuleTests(DoseTestCase):
    def test_module_files_and_migration(self):
        module = modules.load_module(ROOT / "modules" / "medicine_doses")
        self.assertEqual((module.requires, module.outbound_hosts), (["people"], []))
        self.assertIsNone(next_migration_sql(module))
        table = module.tables["doses"]
        self.assertTrue(table.private)
        self.assertFalse(table.suggestions)
        self.assertEqual(table.columns["medication"].link_rule, {"where": {"kind": "medication"},
                                                                 "same": {"person": "recipient"}, "shows": "detail"})
        self.assertTrue(table.columns["amount"].sensitive and table.columns["unit"].sensitive)
        self.assertEqual(self.rule["repeat"]["minutes"], 120)

    def test_switched_off_it_has_no_pages_and_on_again_it_keeps_its_doses(self):
        entry = self.dose()
        settings.set_module_enabled(self.conn, "medicine_doses", False)
        client = self.client()
        self.page(f"/daily/{TABLE}", client, status=404)
        self.page(f"/t/{TABLE}", client, status=404)
        self.assertNotIn("Medicine given today", self.page(f"/t/people__people/{self.rosa}", client))
        settings.set_module_enabled(self.conn, "medicine_doses", True)
        client = self.client()
        self.assertIn("Medicine given today", self.page(f"/t/people__people/{self.rosa}", client))
        self.assertIsNotNone(self.records.get(TABLE, entry))

    def test_examples_garcia_has_two_doses_from_rosas_own_medication_and_the_others_none(self):
        found = {}
        for name in ("smith", "garcia", "taylor"):
            data = self.tmp / name
            load_example.load(name, data, ROOT / "modules", today=date(2026, 11, 21))
            conn = db.connect(data / "dashboard.db")
            try:
                on = "medicine_doses" in settings.enabled_modules(conn)
                rows = [tuple(r) for r in conn.execute(
                    f"SELECT p.name, i.kind, i.person = d.recipient, d.given_at, d.amount, d.unit, g.name "
                    f"FROM {TABLE} d JOIN people__people p ON p.id = d.recipient "
                    f"JOIN {INFO} i ON i.id = d.medication LEFT JOIN people__people g ON g.id = d.given_by "
                    f"ORDER BY d.id")] if on else []
                found[name] = (on, rows)
            finally:
                conn.close()
        self.assertEqual(found["garcia"], (True, [
            ("Rosa Garcia", "medication", 1, "2026-11-20T08:00:00", 1.0, "tablet", "Maria Garcia"),
            ("Rosa Garcia", "medication", 1, "2026-11-20T18:30:00", None, None, None)]))
        self.assertEqual(found["smith"], (False, []))
        self.assertEqual(found["taylor"], (False, []))
