"""Tests for Bills and insurance (decision 0117): dated bills and policies beside Utilities, private details that never travel, and one reminder per vehicle policy.

They automate the checks in Lane B's draft (its ACCEPTANCE.md and RENEWAL.md, now in git history) that a computer can run:
the household's choice for existing Vehicle insurance, moving by exact ID and back, never two reminders, Vehicles or
Household stock switched off, privacy and travel, helpers, export, and the module off and on. Reading at 320 pixels and
printing on A4 and Letter are checked in the browser check and screenshots."""
import io
import shutil
import sqlite3
import zipfile
from datetime import date, datetime, timedelta, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import (backups, checklist, db, export, helpers, modules, proposals, records, reminder_moves,
                            restore, settings, startup, sync, watch)
from dashboard.core.proposals import ProposalError
from dashboard.errors import PlainError
from dashboard.web.app import create_app
import load_example

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
BILLS = "bills_insurance__commitments"
INSURANCE = "vehicles__insurance"
TODAY = date.today()
AMOUNT, COVERS = "43.21", "Invented cover sentinel 8812"
STORED = 4321  # money is kept in cents
REFERENCE, NOTE = "DEMO-REF-SENTINEL-55", "Invented private bill note 6603"
VEHICLE_NOTE = "Invented vehicles note marker 7719"
NEEDS_CHOICE = "Choose first where vehicle insurance reminders are kept"


def soon(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


class BillsCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "vehicles", "utilities", "bills_insurance")

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

    # ----- helpers ------------------------------------------------------------------------------------------
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

    def rule(self, store=None):
        store = store or self.store()
        return reminder_moves.rule_for(store.registry, BILLS, self.report.loaded)

    def client(self):
        client = self.app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = self.app.config["CSRF_TOKEN"]
        return client

    def page(self, path, client=None, status=200):
        reply = (client or self.client()).get(path, base_url=BASE)
        self.assertEqual(reply.status_code, status, path)
        return reply.get_data(as_text=True)

    def post(self, path, data=None, client=None):
        client = client or self.client()
        return client.post(path, data={"_csrf": client.csrf, **(data or {})}, base_url=BASE)

    def car(self, name="Family car"):
        return self.store().create("vehicles__vehicles", {"name": name})

    def insurance(self, vehicle, name="Comprehensive cover", renew_by=None, notes=None):
        values = {"vehicle": vehicle, "name": name, "renew_by": soon(10) if renew_by is None else renew_by}
        if notes:
            values["notes"] = notes
        return self.store().create(INSURANCE, values)

    def bill(self, name="Home electricity", **values):
        values = {"kind": "bill", "category": "electricity", "next_due": soon(20), **values}
        return self.store().create(BILLS, {"name": name, **values})

    def due(self, store=None):
        """Every due reminder of the two lists as (table, record id, words), from Needs attention's own source."""
        store = store or self.store()
        return [(i.table, i.record_id, i.detail) for i in watch.expiring(self.conn, store.registry)
                if i.table in (BILLS, INSURANCE)]

    def tasks(self, store=None):
        store = store or self.store()
        return [(t.source.info.name, t.row["id"]) for t in checklist.tasks(self.conn, store.registry, "year", TODAY)
                if t.source.info.name in (BILLS, INSURANCE)]

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table} WHERE deleted_at IS NULL").fetchone()[0]

    def moves(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM core__reminder_moves ORDER BY id")]

    def export_files(self, store=None):
        raw = export.build(self.conn, (store or self.store()).registry, __version__,
                           now=datetime(2026, 11, 22, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return {n: archive.read(n).decode("utf-8-sig") for n in archive.namelist()}


class BillsModuleTests(BillsCase):
    """Lane B's ACCEPTANCE.md checks 1 to 9."""

    def test_1_it_needs_only_people_and_each_category_saves_with_exact_links(self):
        module = modules.load_module(ROOT / "modules" / "bills_insurance")
        self.assertEqual((module.requires, module.optional_requires, module.outbound_hosts),
                         (["people"], ["stock", "vehicles"], []))
        store = self.store()
        provider = store.create("people__people", {"name": "Example Insurer"})
        car = self.car()
        place = store.create("stock__places", {"name": "Kitchen"})
        for category in ("home", "contents", "health", "pet"):
            store.create(BILLS, {"name": f"Invented {category} policy", "kind": "policy", "category": category,
                                 "provider": provider, "place": place})
        store.create(BILLS, {"name": "Invented car policy", "kind": "policy", "category": "vehicle", "vehicle": car})
        self.bill(provider=provider)
        self.assertEqual(self.count(BILLS), 6)
        for column, value in (("provider", 999), ("vehicle", 999), ("place", 999), ("vehicle", "Family car")):
            with self.subTest(column=column), self.assertRaises(records.ValidationError):
                store.create(BILLS, {"name": "Typed link", "kind": "bill", "category": "other", column: value})

    def test_2_blank_links_save_and_a_deleted_link_clears_without_touching_the_rest(self):
        store = self.store()
        provider = store.create("people__people", {"name": "Example Energy"})
        car, place = self.car(), store.create("stock__places", {"name": "Hall"})
        household = store.create(BILLS, {"name": "Household policy", "kind": "policy", "category": "home"})
        self.assertIsNone(store.get(BILLS, household)["vehicle"])
        linked = self.bill(provider=provider, vehicle=car, place=place, amount=AMOUNT, notes=NOTE)
        before = store.get(BILLS, linked)
        for table, record_id in (("people__people", provider), ("vehicles__vehicles", car), ("stock__places", place)):
            store.delete(table, record_id)
        after = store.get(BILLS, linked)
        self.assertEqual((after["provider"], after["vehicle"], after["place"]), (None, None, None))
        for kept in ("name", "next_due", "amount", "notes", "kind", "category"):
            self.assertEqual(after[kept], before[kept])

    def test_3_due_words_come_30_days_before_name_the_record_and_never_claim_payment_or_cover(self):
        self.bill("Far bill", next_due=soon(31))
        self.bill("Near bill", next_due=soon(30))
        self.bill("Late bill", next_due=soon(-2))
        self.store().create(BILLS, {"name": "Home policy", "kind": "policy", "category": "home", "next_due": soon(5)})
        found = {watch._name(self.store().info(BILLS), self.store().get(BILLS, i)): words
                 for _, i, words in self.due()}
        self.assertNotIn("Far bill", found)
        self.assertTrue(found["Near bill"].startswith("bill check due "), found)
        self.assertIn("(in 30 days)", found["Near bill"])
        self.assertTrue(found["Late bill"].startswith("bill check overdue since"))
        self.assertTrue(found["Home policy"].startswith("policy check due"))
        page = self.page("/attention")
        self.assertIn("Near bill", page)
        for claim in ("paid", "lapsed", "failed", "in force", "active"):
            self.assertNotIn(claim, " ".join(found.values()))

    def test_4_how_often_never_makes_another_date_and_blank_is_allowed(self):
        bill = self.bill("Weekly bin bill", frequency="weekly", next_due=soon(-8))
        self.store().create(BILLS, {"name": "No date bill", "kind": "bill", "category": "other"})
        self.assertEqual(self.count(BILLS), 2)
        self.assertEqual(self.store().get(BILLS, bill)["next_due"], soon(-8))
        self.page("/to-do")
        self.assertEqual(self.count(BILLS), 2)
        self.assertEqual(self.store().get(BILLS, bill)["next_due"], soon(-8))

    def test_5_private_details_are_behind_show_and_out_of_lists_sheets_exports_helpers_and_the_change_log(self):
        bill = self.bill(amount=AMOUNT, covers=COVERS, reference=REFERENCE, notes=NOTE, next_due=soon(3))
        client = self.client()
        sentinels = (COVERS, REFERENCE, NOTE, "43.21")
        for path in ("/", "/attention", "/to-do", f"/t/{BILLS}", f"/t/{BILLS}/{bill}",
                     "/sheet/bills_insurance/upcoming_bills_and_policies"):
            text = self.page(path, client)
            for private in sentinels:
                with self.subTest(path=path, private=private):
                    self.assertNotIn(private, text)
        shown = client.post(f"/t/{BILLS}/{bill}/reveal", data={"column": "reference", "_csrf": client.application.config["CSRF_TOKEN"]}, base_url=BASE, headers={"Accept": "application/json"}).get_json()
        self.assertEqual(shown["value"], REFERENCE)
        for name, text in self.export_files().items():
            for private in sentinels:
                self.assertNotIn(private, text, name)
        _, key = helpers.issue(self.conn, self.data, "Bills reader", "read", ["bills_insurance"])
        reply = client.get(f"/api/v1/tables/{BILLS}/records", base_url=BASE,
                           headers={"Authorization": f"Bearer {key}"}).get_data(as_text=True)
        self.assertIn("Home electricity", reply)
        for private in sentinels + (str(STORED),):
            self.assertNotIn(private, reply)
        log = sync.changes(self.conn, 0, limit=100000)
        created = next(e for e in log if e["table_name"] == BILLS and e["action"] == "create")
        self.assertEqual(sorted(created["withheld"]), ["amount", "covers", "notes", "reference"])
        snap = sync.snapshot(self.conn, self.store().registry)
        for private in sentinels + (str(STORED),):
            self.assertNotIn(private, str(log))
            self.assertNotIn(private, str(snap))
        backups.daily(self.data, today=date(2026, 6, 1))
        kept = sqlite3.connect(self.data / "backups" / "daily-2026-06-01.db")
        self.addCleanup(kept.close)
        self.assertEqual(kept.execute(f"SELECT amount, covers, reference, notes FROM {BILLS}").fetchone(),
                         (STORED, COVERS, REFERENCE, NOTE))
        module = modules.load_module(ROOT / "modules" / "bills_insurance")
        columns = module.tables["commitments"].columns
        self.assertEqual({n for n, c in columns.items() if c.travels == "never"},
                         {"amount", "covers", "reference", "notes"})
        self.assertEqual({n for n, c in columns.items() if c.sensitive}, {"amount", "covers", "reference", "notes"})

    def test_6_a_member_copy_sees_the_due_date_but_no_private_detail_and_an_edit_never_sends_a_blank(self):
        bill = self.bill(amount=AMOUNT, covers=COVERS, reference=REFERENCE, notes=NOTE)
        seen = sync.changes(self.conn, 0, limit=100000)[-1]["seq"]
        self.store().update(BILLS, bill, {"amount": "43.22"})
        self.store().update(BILLS, bill, {"next_due": soon(9)})
        later = sync.changes(self.conn, seen)
        self.assertEqual([c["columns"] for c in later], [["amount"], ["next_due"]])
        self.assertEqual(later[0]["patch"], {})  # only the field name: nothing that could blank another copy
        self.assertEqual(later[0]["withheld"], ["amount"])
        self.assertEqual(later[1]["patch"], {"next_due": soon(9)})
        row = next(r for r in sync.snapshot(self.conn, self.store().registry)["records"] if r["table"] == BILLS)
        self.assertEqual(row["values"]["name"], "Home electricity")
        self.assertEqual(row["values"]["next_due"], soon(9))
        self.assertEqual(set(row["withheld"]), {"amount", "covers", "reference", "notes"})

    def test_7_the_sheet_prints_no_money_or_reference_and_says_when_it_is_not_complete(self):
        self.bill(amount=AMOUNT, reference=REFERENCE, provider=self.store().create(
            "people__people", {"name": "Example Provider With A Very Long Name For Printing Tests"}))
        sheet = self.page("/sheet/bills_insurance/upcoming_bills_and_policies")
        self.assertIn("Home electricity", sheet)
        self.assertIn("Example Provider With A Very Long Name", sheet)
        for private in (REFERENCE, "43.21", "Amount last quoted"):
            self.assertNotIn(private, sheet)
        self.assertNotIn("Not complete", sheet)
        store = self.store()
        with db.transaction(self.conn):
            for n in range(205):
                store.create_in(BILLS, {"name": f"Invented bill {n}", "kind": "bill", "category": "other"})
        sheet = self.page("/sheet/bills_insurance/upcoming_bills_and_policies")
        self.assertIn("Not complete:", sheet)
        self.assertIn("only the first 200 of 206 are printed", sheet)

    def test_8_utilities_stays_the_service_record_and_a_second_vehicle_reminder_is_warned_about(self):
        store = self.store()
        service = store.create("utilities__services", {"name": "Home electricity", "kind": "electricity"})
        self.bill()
        self.assertEqual(store.get("utilities__services", service)["name"], "Home electricity")
        self.assertEqual({c for c in store.info("utilities__services").table.columns} & {"amount", "next_due"}, set())
        car = self.car()
        self.insurance(car)
        reminder_moves.choose(self.conn, self.rule(), "keep")
        reply = self.post(f"/t/{BILLS}/new", {"name": "Car policy", "kind": "policy", "category": "vehicle",
                                              "vehicle": str(car)})
        text = reply.get_data(as_text=True)
        self.assertIn("Family car already has an insurance reminder in Vehicles (Family car: Comprehensive cover)",
                      text)
        self.assertEqual(self.count(BILLS), 1)  # held: nothing saved until Save as entered

    def test_9_with_vehicles_or_household_stock_off_bills_still_works_and_keeps_links_by_id(self):
        store = self.store()
        car, place = self.car(), store.create("stock__places", {"name": "Garage"})
        linked = self.bill(vehicle=car, place=place)
        self.switch(vehicles=False)
        store = self.store()
        self.assertIn(BILLS, store.registry)
        self.assertNotIn("vehicles__vehicles", store.registry)
        store.update(BILLS, linked, {"name": "Renamed bill"})
        self.assertEqual(store.get(BILLS, linked)["vehicle"], car)
        with self.assertRaises(records.ValidationError):
            store.update(BILLS, linked, {"vehicle": None})
        page = self.page(f"/t/{BILLS}/{linked}")
        self.assertIn("A vehicle link is saved. Switch on Vehicles to see or change it.", page)
        self.assertNotIn("Family car", page)
        self.switch(stock=False)
        store = self.store()
        self.assertEqual(sorted(m for m in {i.module.name for i in store.registry.values()}),
                         ["bills_insurance", "people", "utilities"])
        fresh = self.bill("Internet bill", category="internet")
        self.assertIsNotNone(fresh)
        self.assertIn("Place link saved; switch on Household stock to see it.", self.page(f"/t/{BILLS}"))
        self.assertEqual(store.get(BILLS, linked)["place"], place)
        self.switch(stock=True, vehicles=True)
        page = self.page(f"/t/{BILLS}/{linked}")
        self.assertIn("Family car", page)

    def test_module_off_and_on_hides_and_returns_every_record_and_reminder(self):
        bill = self.bill(next_due=soon(4), amount=AMOUNT)
        self.switch(bills_insurance=False)
        self.assertEqual(self.due(), [])
        self.page(f"/t/{BILLS}", status=404)
        self.switch(bills_insurance=True)
        self.assertEqual([d[:2] for d in self.due()], [(BILLS, bill)])
        self.assertEqual(self.store().get(BILLS, bill)["amount"], STORED)

    def test_a_helper_may_suggest_an_ordinary_bill_but_never_a_private_detail_or_a_second_vehicle_reminder(self):
        helper, _ = helpers.issue(self.conn, self.data, "Bills helper", "suggest", ["bills_insurance", "vehicles"])
        entry = {"table": BILLS, "values": {"name": "Home gas", "kind": "bill", "category": "gas"}}
        result, _ = proposals.submit(self.conn, self.store().registry, helper,
                                     {"request_key": "k-1", "why": "Invented.", "entries": [entry]})
        self.assertEqual(result["state"], "waiting")
        with self.assertRaises(ProposalError):
            proposals.submit(self.conn, self.store().registry, helper, {
                "request_key": "k-2", "why": "Invented.",
                "entries": [{"table": BILLS, "values": {"name": "x", "kind": "bill", "category": "gas",
                                                        "reference": REFERENCE}}]})
        car = self.car()
        self.insurance(car)
        with self.assertRaises(ProposalError) as caught:
            proposals.submit(self.conn, self.store().registry, helper, {
                "request_key": "k-3", "why": "Invented.",
                "entries": [{"table": BILLS, "values": {"name": "Car", "kind": "policy", "category": "vehicle",
                                                        "vehicle": car}}]})
        self.assertIn(NEEDS_CHOICE, str(caught.exception.problems))

    def test_the_migration_matches_tables_toml_and_writes_optional_links_without_a_database_rule(self):
        module = modules.load_module(ROOT / "modules" / "bills_insurance")
        from dashboard.core.schema import next_migration_sql
        self.assertIsNone(next_migration_sql(module))
        sql = (ROOT / "modules" / "bills_insurance" / "migrations" / "0001_initial.sql").read_text()
        self.assertIn("provider INTEGER REFERENCES people__people", sql)
        self.assertIn("vehicle INTEGER,", sql)
        self.assertIn("place INTEGER,", sql)


class OneReminderTests(BillsCase):
    """Lane B's RENEWAL.md checks 1 to 9: one owner and one due source per vehicle policy."""

    def test_1_vehicles_reminds_once_and_keep_or_decide_later_moves_nothing(self):
        car = self.car()
        policy = self.insurance(car)
        self.switch(bills_insurance=False)
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])
        self.switch(bills_insurance=True)
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])  # switching on moves nothing
        grid = self.page(f"/t/{BILLS}")
        self.assertIn("Vehicle insurance already in Vehicles", grid)
        self.assertIn("You have 1 vehicle insurance record(s) in Vehicles.", grid)
        for choice in ("later", "keep"):
            reply = self.post(f"/moves/{BILLS}/choice", {"choice": choice})
            self.assertEqual(reply.status_code, 302)
            self.assertEqual(self.count(BILLS), 0)
            self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])
            self.assertEqual(self.tasks(), [(INSURANCE, policy)])
        self.assertNotIn("Vehicle insurance already in Vehicles", self.page(f"/t/{BILLS}"))
        self.assertIn("Review and move to Bills", self.page(f"/t/{BILLS}"))  # the choice can be changed later
        self.assertEqual(self.moves(), [])

    def test_1b_until_the_household_chooses_a_vehicle_policy_can_not_be_saved_in_bills(self):
        car = self.car()
        self.insurance(car)
        with self.assertRaises(records.ValidationError) as caught:
            self.store().create(BILLS, {"name": "Car", "kind": "policy", "category": "vehicle", "vehicle": car})
        self.assertIn(NEEDS_CHOICE, caught.exception.problems["reminder"])
        reminder_moves.choose(self.conn, self.rule(), "later")
        with self.assertRaises(records.ValidationError):
            self.store().create(BILLS, {"name": "Car", "kind": "policy", "category": "vehicle"})
        self.bill()  # ordinary bills are never held up
        reminder_moves.choose(self.conn, self.rule(), "keep")
        self.store().create(BILLS, {"name": "Second car policy", "kind": "policy", "category": "vehicle"})

    def test_2_review_shows_each_record_by_id_with_no_name_match_and_no_guessed_date(self):
        car = self.car()
        first = self.insurance(car, "Same name cover")
        second = self.insurance(car, "Same name cover")
        blank = self.insurance(self.car("Trailer"), "Trailer cover", renew_by="")
        page = self.page(f"/moves/{BILLS}")
        for record_id in (first, second, blank):
            gid = self.conn.execute(f"SELECT global_id FROM {INSURANCE} WHERE id = ?", (record_id,)).fetchone()[0]
            self.assertIn(f'data-move-row="{record_id}"', page)
            self.assertIn(gid, page)
        self.assertEqual(page.count("Same name cover"), 4)  # each row shows its own title and name
        self.assertIn("No renewal date recorded. Check your policy and add the date you want to be reminded.", page)
        self.assertIn("Notes in Vehicles stay there and keep their current sharing and export rules", page)
        self.assertIn("Move this renewal date to Bills? Vehicles will stop reminding you for this policy.", page)
        self.post(f"/moves/{BILLS}/{second}/move", {"back": f"/moves/{BILLS}"})
        moved = self.moves()
        self.assertEqual([(m["source_id"], m["state"]) for m in moved], [(second, "moved")])
        self.assertEqual([d[:2] for d in self.due() if d[0] == INSURANCE], [(INSURANCE, first)])
        reminder_moves.move(self.store(), self.rule(), blank)
        target = self.moves()[-1]["target_id"]
        self.assertIsNone(self.store().get(BILLS, target)["next_due"])  # a blank date stays blank
        self.assertNotIn(target, [d[1] for d in self.due()])

    def test_3_a_moved_policy_keeps_its_vehicle_name_and_exact_date_and_reminds_once_from_bills(self):
        car = self.car()
        policy = self.insurance(car, renew_by=soon(12), notes=VEHICLE_NOTE)
        reply = self.post(f"/moves/{BILLS}/{policy}/move")
        self.assertEqual(reply.status_code, 302)
        target = self.moves()[0]["target_id"]
        self.assertTrue(reply.headers["Location"].endswith(f"/t/{BILLS}/{target}?moved=1"))
        row = self.store().get(BILLS, target)
        self.assertEqual((row["vehicle"], row["name"], row["next_due"], row["kind"], row["category"]),
                         (car, "Comprehensive cover", soon(12), "policy", "vehicle"))
        for private in ("amount", "covers", "reference", "notes", "provider", "frequency"):
            self.assertIsNone(row[private], private)
        self.assertEqual(self.store().get(INSURANCE, policy)["notes"], VEHICLE_NOTE)  # stays in the earlier row
        self.assertEqual(self.due(), [(BILLS, target, f"vehicle insurance review or renewal due "
                                                     f"{TODAY + timedelta(days=12):%d/%m/%y} (in 12 days)")])
        self.assertEqual(self.tasks(), [(BILLS, target)])
        client = self.client()
        home, attention, todo = (self.page(p, client) for p in ("/", "/attention", "/to-do/month"))
        self.assertEqual(attention.count("Comprehensive cover"), 1)
        self.assertNotIn("Family car: Comprehensive cover", attention)
        done = self.page(f"/t/{BILLS}/{target}?moved=1", client)
        self.assertIn("Moved Comprehensive cover to Bills and insurance. One reminder is active there; the "
                      "Vehicles reminder is off.", done)
        self.assertIn("This is your reminder to check the policy, not proof it is active.", done)
        self.assertIn(f'href="/t/{INSURANCE}/{policy}">Earlier Vehicle insurance record', done)
        earlier = self.page(f"/t/{INSURANCE}/{policy}", client)
        self.assertIn("Insurance reminder is in Bills and insurance. Open", earlier)
        self.assertIn(f'<a href="/t/{BILLS}/{target}">Comprehensive cover</a>', earlier)
        sheet = self.page("/sheet/vehicles/vehicles", client)
        self.assertNotIn("Comprehensive cover", sheet)
        self.assertIn("Comprehensive cover", self.page("/sheet/bills_insurance/upcoming_bills_and_policies", client))

    def test_4_a_second_press_a_restart_or_a_restore_leave_one_commitment_and_one_mapping(self):
        policy = self.insurance(self.car())
        first = self.post(f"/moves/{BILLS}/{policy}/move")
        second = self.post(f"/moves/{BILLS}/{policy}/move")
        self.assertEqual(first.headers["Location"], second.headers["Location"])
        self.assertEqual((self.count(BILLS), len(self.moves())), (1, 1))
        self.assertTrue(list((self.data / "backups").glob("before-move-*.db")))
        report = startup.prepare(self.data, self.tmp / "modules")  # a restart
        self.assertEqual(report.module_problems, {})
        self.assertEqual(reminder_moves.move(self.store(), self.rule(), policy)["status"], "already")
        self.assertEqual((self.count(BILLS), len(self.moves())), (1, 1))
        backups.daily(self.data, today=date(2026, 6, 1))
        self.store().update(BILLS, self.moves()[0]["target_id"], {"next_due": soon(3)})
        chosen = restore.get({"data": self.data / "backups"}, "data", "daily-2026-06-01.db")
        self.conn.close()
        restore.restore(self.data, chosen, report.loaded)
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.assertEqual((self.count(BILLS), len(self.moves())), (1, 1))
        self.assertEqual(len(self.due()), 1)

    def test_4b_a_failed_move_leaves_the_vehicles_reminder_and_no_partial_bills_row(self):
        policy = self.insurance(self.car())

        def no_backup():
            raise OSError("disk full")
        with self.assertRaises(PlainError) as caught:
            reminder_moves.move(self.store(), self.rule(), policy, backup=no_backup)
        self.assertIn("a backup could not be made first", str(caught.exception))
        store = self.store()
        original = store._create

        def broken(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError("invented failure after the new row")
        store._create = broken
        with self.assertRaises(RuntimeError):
            reminder_moves.move(store, self.rule(store), policy)
        self.assertEqual((self.count(BILLS), self.moves()), (0, []))
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])

    def test_5_a_private_vehicles_note_is_never_copied_into_bills_a_due_message_or_the_move_record(self):
        policy = self.insurance(self.car(), notes=VEHICLE_NOTE)
        reminder_moves.move(self.store(), self.rule(), policy)
        bills_rows = str([dict(r) for r in self.conn.execute(f"SELECT * FROM {BILLS}")])
        self.assertNotIn(VEHICLE_NOTE, bills_rows)
        self.assertNotIn(VEHICLE_NOTE, str(self.moves()))
        self.assertNotIn(VEHICLE_NOTE, str(self.due()))
        history = [dict(r) for r in self.conn.execute("SELECT * FROM core__audit WHERE action LIKE 'reminder_%'")]
        self.assertTrue(history)
        self.assertNotIn(VEHICLE_NOTE, str(history))
        self.assertNotIn("Comprehensive cover", str(history))  # names by list and number only
        self.assertNotIn(VEHICLE_NOTE, self.export_files()[f"{BILLS}.csv"])
        self.assertIn(VEHICLE_NOTE, self.export_files()[f"{INSURANCE}.csv"])  # its existing, ordinary rule

    def test_6_a_changed_bills_date_is_the_one_reminder_bills_off_never_revives_vehicles_and_back_uses_it(self):
        policy = self.insurance(self.car(), renew_by=soon(25))
        target = reminder_moves.move(self.store(), self.rule(), policy)["target_id"]
        self.store().update(BILLS, target, {"next_due": soon(6)})
        self.assertEqual([d[:2] for d in self.due()], [(BILLS, target)])
        self.assertIn("in 6 days", self.due()[0][2])
        self.switch(bills_insurance=False)
        self.assertEqual(self.due(), [])
        self.assertEqual(self.tasks(), [])
        page = self.page(f"/t/{INSURANCE}/{policy}")
        self.assertIn("Vehicle insurance reminders are in Bills and insurance, which is off. Switch it on to see "
                      "them, or choose Transfer back.", page)
        self.assertNotIn(soon(25), str(self.due()))
        reply = self.post(f"/moves/{BILLS}/{policy}/back")
        self.assertEqual(reply.status_code, 302)
        self.assertEqual(self.store().get(INSURANCE, policy)["renew_by"], soon(6))  # the current Bills date
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])
        self.switch(bills_insurance=True)
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])  # still exactly one owner
        self.assertEqual(self.tasks(), [(INSURANCE, policy)])
        page = self.page(f"/t/{BILLS}/{target}")
        self.assertIn("reminder is back in Vehicles. One reminder is active there", page)
        with self.assertRaises(records.ValidationError):
            self.store().update(BILLS, target, {"next_due": soon(2)})
        self.store().update(INSURANCE, policy, {"renew_by": soon(8)})  # Vehicles owns it again
        again = reminder_moves.move(self.store(), self.rule(), policy)
        self.assertEqual(again, {"status": "moved", "target_id": target})  # the same Bills record, never a second
        self.assertEqual(self.store().get(BILLS, target)["next_due"], soon(8))
        self.assertEqual([d[:2] for d in self.due()], [(BILLS, target)])
        self.assertEqual(self.count(BILLS), 1)

    def test_6b_the_earlier_record_is_read_only_and_can_not_be_deleted_on_its_own(self):
        policy = self.insurance(self.car())
        reminder_moves.move(self.store(), self.rule(), policy)
        with self.assertRaises(records.ValidationError) as caught:
            self.store().update(INSURANCE, policy, {"renew_by": soon(2)})
        self.assertIn("Change it there, or choose Transfer back", caught.exception.problems["reminder"])
        with self.assertRaises(records.ValidationError):
            self.store().delete(INSURANCE, policy)
        reply = self.post(f"/t/{INSURANCE}/{policy}", {"vehicle": "1", "name": "Edited", "renew_by": ""})
        self.assertEqual(reply.status_code, 422)
        self.assertEqual(self.store().get(INSURANCE, policy)["name"], "Comprehensive cover")

    def test_7_deleting_or_switching_off_vehicles_after_a_move_keeps_the_bills_row_and_never_relinks_by_name(self):
        car = self.car()
        policy = self.insurance(car)
        target = reminder_moves.move(self.store(), self.rule(), policy)["target_id"]
        self.switch(vehicles=False)
        self.assertEqual([d[:2] for d in self.due()], [(BILLS, target)])
        self.assertIn("Vehicle link saved; switch on Vehicles to see it.", self.page(f"/t/{BILLS}"))
        self.switch(vehicles=True)
        self.store().delete("vehicles__vehicles", car)
        row = self.store().get(BILLS, target)
        self.assertEqual((row["vehicle"], row["name"]), (None, "Comprehensive cover"))
        self.car("Family car")  # a new vehicle with the same name is never linked by its name
        self.assertIsNone(self.store().get(BILLS, target)["vehicle"])
        self.assertEqual([d[:2] for d in self.due()], [(BILLS, target)])

    def test_8_other_bills_keep_their_reminders_and_a_new_vehicles_policy_is_warned_about(self):
        bill = self.bill(next_due=soon(4))
        car = self.car()
        policy = self.insurance(car)
        target = reminder_moves.move(self.store(), self.rule(), policy)["target_id"]
        self.assertEqual(sorted(d[:2] for d in self.due()), sorted([(BILLS, bill), (BILLS, target)]))
        reply = self.post(f"/t/{INSURANCE}/new", {"vehicle": str(car), "name": "Another cover", "renew_by": ""})
        text = reply.get_data(as_text=True)
        self.assertIn("Family car already has a vehicle insurance reminder in Bills and insurance "
                      "(Comprehensive cover)", text)
        self.assertEqual(self.count(INSURANCE), 1)
        token = text.split('name="_confirm" value="')[1].split('"')[0]
        self.post(f"/t/{INSURANCE}/new", {"vehicle": str(car), "name": "Another cover", "renew_by": "",
                                          "_confirm": token})
        self.assertEqual(self.count(INSURANCE), 2)  # a different policy, saved on purpose

    def test_9_print_shows_one_date_and_export_keeps_both_records_marked_with_the_mapping(self):
        policy = self.insurance(self.car(), notes=VEHICLE_NOTE)
        target = reminder_moves.move(self.store(), self.rule(), policy)["target_id"]
        self.store().update(BILLS, target, {"amount": AMOUNT, "notes": NOTE})
        files = self.export_files()
        self.assertIn(f"Earlier record: its reminder moved to Bills and policies (ID {target}); it does not remind",
                      files[f"{INSURANCE}.csv"])
        self.assertIn(f"Reminds here (moved from Vehicle insurance, ID {policy})", files[f"{BILLS}.csv"])
        self.assertIn('"Reminder" column', files["README.txt"])
        for private in (NOTE, "43.21"):
            self.assertNotIn(private, files[f"{BILLS}.csv"])
        for word in ("paid", "covered"):
            self.assertNotIn(word, files[f"{BILLS}.csv"].lower())
        snap = sync.snapshot(self.conn, self.store().registry)
        ids = [self.conn.execute(f"SELECT global_id FROM {t} WHERE id = ?", (i,)).fetchone()[0]
               for t, i in ((INSURANCE, policy), (BILLS, target))]
        self.assertEqual(snap["reminder_moves"], [{"from_table": INSURANCE, "from": ids[0], "to_table": BILLS,
                                                   "to": ids[1], "state": "moved"}])
        self.assertEqual([p for p in sync.check(self.conn, self.store().registry)], [])
        both = self.page("/sheet/vehicles/vehicles") + self.page("/sheet/bills_insurance/upcoming_bills_and_policies")
        self.assertEqual(both.count("Comprehensive cover"), 1)

    def test_keep_and_decide_later_per_row_are_recorded_and_undone_without_moving_anything(self):
        policy = self.insurance(self.car())
        self.post(f"/moves/{BILLS}/{policy}/keep")
        self.assertEqual([m["state"] for m in self.moves()], ["kept"])
        self.assertIn("Kept in Vehicles.", self.page(f"/moves/{BILLS}"))
        with self.assertRaises(PlainError):  # Keep is not a way round Transfer back
            reminder_moves.move(self.store(), self.rule(), policy)
            reminder_moves.keep(self.store(), self.rule(), policy)
        self.assertEqual([m["state"] for m in self.moves()], ["moved"])

    def test_decide_later_on_one_row_asks_again(self):
        policy = self.insurance(self.car())
        reminder_moves.keep(self.store(), self.rule(), policy)
        self.post(f"/moves/{BILLS}/{policy}/later")
        self.assertEqual(self.moves(), [])
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])

    def test_a_deleted_bills_record_must_be_restored_before_transfer_back(self):
        policy = self.insurance(self.car())
        target = reminder_moves.move(self.store(), self.rule(), policy)["target_id"]
        self.store().delete(BILLS, target)
        self.assertEqual(self.due(), [])  # the household deleted the one reminder; nothing else revives
        reply = self.post(f"/moves/{BILLS}/{policy}/back")
        self.assertEqual(reply.status_code, 409)
        self.assertIn("Restore it there first", reply.get_data(as_text=True))
        self.store().restore(BILLS, target)
        self.assertEqual(self.post(f"/moves/{BILLS}/{policy}/back").status_code, 302)
        self.assertEqual([d[:2] for d in self.due()], [(INSURANCE, policy)])

    def test_with_vehicles_never_installed_bills_loads_and_has_nothing_to_move(self):
        for name in ("vehicles",):
            shutil.rmtree(self.tmp / "modules" / name)
        found, failures = modules.discover(self.tmp / "modules")
        self.assertNotIn("bills_insurance", failures)
        registry = records.build_registry(found)
        rule = reminder_moves.rule_for(registry, BILLS)
        self.assertIsNone(rule.source)
        self.assertFalse(reminder_moves.needs_choice(self.conn, rule))


class ExampleTests(TempDirTestCase):
    def test_each_household_switches_bills_on_and_only_smith_and_garcia_are_asked_about_vehicle_insurance(self):
        for household, asked in (("smith", True), ("garcia", True), ("taylor", False)):
            with self.subTest(household=household):
                self.assertIn("bills_insurance", load_example.read(household)["setup"]["modules"])
                data = self.tmp / household
                load_example.load(household, data, today=date(2026, 11, 22))
                report = startup.prepare(data)
                conn = db.connect(data / "dashboard.db")
                try:
                    registry = records.build_registry(report.loaded)
                    rule = reminder_moves.rule_for(registry, BILLS)
                    self.assertEqual(reminder_moves.show_choice(conn, rule), asked)
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM core__reminder_moves").fetchone()[0], 0)
                    rows = conn.execute(f"SELECT name, reference FROM {BILLS}").fetchall()
                    self.assertEqual(len(rows), 1)
                    self.assertTrue(rows[0]["reference"].startswith("DEMO-"))
                finally:
                    conn.close()


class LoaderTests(TempDirTestCase):
    MODULE = '''name = "demo"
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
title = "Other"
version = "1.0.0"
description = "A made-up older list."
core_api = "1"
kind = "declarative"
requires = []
outbound_hosts = []
'''
    OTHER_TABLES = '''[tables.renewals]
title = "Renewals"
columns.name = { type = "text", required = true }
columns.due = { type = "date" }
columns.secret = { type = "text", sensitive = true, travels = "never" }
[tables.renewals.watch]
expiring = { date = "due", wording = "due" }
'''
    TABLES = '''[tables.things]
title = "Things"
columns.name = { type = "text", required = true }
columns.kind = { type = "choice", choices = ["a", "b"] }
columns.when = { type = "date" }
columns.private = { type = "text", sensitive = true, travels = "never" }
[tables.things.watch.expiring]
date = "when"
wording = "due"
what = "thing check"
[[tables.things.watch.expiring.what_when]]
where = { kind = "a" }
what = "a check"
[tables.things.takes_over]
from = "other.renewals"
where = { kind = "a" }
copy = { name = "name", when = "due" }
'''

    def load(self, tables=TABLES, other=OTHER_TABLES):
        self.make_module("other", module=self.OTHER, tables=other, labels=None)
        self.make_module("demo", module=self.MODULE, tables=tables, labels=None)
        return modules.discover(self.tmp / "modules")

    def test_a_good_declaration_loads(self):
        found, failures = self.load()
        self.assertEqual(failures, {})
        demo = next(m for m in found if m.name == "demo")
        self.assertEqual(demo.tables["things"].takes_over["copy"], {"name": "name", "when": "due"})
        self.assertEqual(demo.tables["things"].watch["expiring"]["what_when"], [{"where": {"kind": "a"},
                                                                                  "what": "a check"}])

    def test_bad_declarations_are_explained(self):
        cases = {
            "private": (self.TABLES.replace('copy = { name = "name", when = "due" }',
                                            'copy = { name = "name", when = "due", private = "name" }'), "can't be copied into"),
            "theirs private": (self.TABLES.replace('copy = { name = "name", when = "due" }',
                                                   'copy = { name = "secret", when = "due" }'), "is private"),
            "no date": (self.TABLES.replace('copy = { name = "name", when = "due" }', 'copy = { name = "name" }'),
                        "must copy the reminder's date"),
            "not listed": (self.TABLES.replace('from = "other.renewals"', 'from = "elsewhere.renewals"'),
                           "'from' names a table of another module"),
            "no such table": (self.TABLES.replace('from = "other.renewals"', 'from = "other.nothing"'),
                              "has no table 'nothing'"),
            "bad what_when": (self.TABLES.replace('where = { kind = "a" }\nwhat = "a check"',
                                                  'where = { kind = "z" }\nwhat = "a check"'), "not one of the choices"),
        }
        for name, (tables, words) in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.tmp / "modules", ignore_errors=True)
                _, failures = self.load(tables)
                self.assertIn(words, " ".join(failures.get("demo", [])))
