"""Tests for What your other computers get: sharing choices per list and detail, enforced in the change log (decision 0140)."""
import re
import shutil
from pathlib import Path

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, settings, startup, sync
from dashboard.core import sync_sharing as sharing
from dashboard.web.app import create_app

PORT = 5161
BASE = f"http://127.0.0.1:{PORT}"
ITEMS, MOVES, REFUNDS = "stock__items", "stock__movements", "stock__refunds"
EXITS, PEOPLE, INFO = "home_layout__exits", "people__people", "people__important_info"
TEMPLATES = ROOT / "src" / "dashboard" / "web" / "templates"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class SharingTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("stock", "home_layout", "people"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        settings.put(self.conn, "household.country", "Australia")

    def fill(self):
        """A few invented records of every kind the rules treat differently."""
        beans = self.store.create(ITEMS, {"name": "Kidney beans", "category": "pantry", "unit": "tins"})
        bought = self.store.create(MOVES, {"item": beans, "reason": "bought", "amount": 2, "happened_on": "2026-11-18",
                                           "price": "3.80", "price_basis": "total"})
        self.store.create(REFUNDS, {"movement": bought, "amount": "1.20", "happened_on": "2026-11-19"})
        self.bought = bought
        self.store.create(EXITS, {"name": "Back door", "access_details": "Invented code 4321"})
        person = self.store.create(PEOPLE, {"name": "User 1"})
        self.store.create(INFO, {"person": person, "kind": "allergy", "detail": "Invented allergy"})
        self.store.create(INFO, {"person": person, "kind": "access", "detail": "Invented key place"})
        return beans

    def lines(self, table=None):
        return [e for e in sync.changes(self.conn, limit=10_000) if table is None or e["table_name"] == table]

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def post(self, client, path, **data):
        return client.post(path, base_url=BASE, data=dict(data, _csrf=client.csrf))


def _shape(entry: dict) -> tuple:
    """A change-log line without what is random (IDs, operation, times), for comparing two households."""
    patch = {k: ("<id>" if isinstance(v, str) and UUID.match(v) else v) for k, v in entry["patch"].items()}
    return (entry["table_name"], entry["action"], tuple(entry["columns"]), tuple(sorted(patch.items())),
            tuple(entry["withheld"]), entry["base_revision"], entry["revision"], entry["effect"])


class DefaultTests(SharingTestCase):
    def test_every_default_is_exactly_the_modules_own_rule(self):
        for name, info in self.registry.items():
            rules = sharing.rules(self.conn, info)
            for column in info.table.columns.values():
                for kind in [None] + [c.key for c in info.table.columns.get("kind", column).choices]:
                    row = {"kind": kind}
                    for held in (False, True):
                        if name == REFUNDS:
                            self.assertFalse(rules.allows(column, row, held), column.name)
                        else:
                            self.assertEqual(rules.allows(column, row, held), sync.travels(column, row, held),
                                             f"{name}.{column.name}")

    def test_the_change_log_is_identical_before_any_choice(self):
        self.fill()
        ours = [_shape(e) for e in self.lines()]
        # The same records in a second household whose sharing step is turned off: the rules of decision 0100.
        other = self.tmp / "other"
        shutil.copytree(self.tmp / "modules", other / "modules")
        report = startup.prepare(other / "data", other / "modules")
        conn = db.connect(other / "data" / "dashboard.db")
        self.addCleanup(conn.close)
        settings.put(conn, "household.country", "Australia")
        legacy, usual = sharing.Rules.allows, sharing.list_default
        try:
            sharing.Rules.allows = lambda self, column, row, held=False: sync.travels(column, row, held)
            sharing.list_default = lambda info: "shared"  # before 0140 no list started kept here
            self.conn, self.registry = conn, records.build_registry(report.loaded)
            self.store = records.Records(conn, self.registry)
            self.fill()
        finally:
            sharing.Rules.allows, sharing.list_default = legacy, usual
        before = [_shape(e) for e in sync.changes(conn, limit=10_000)]
        self.assertEqual(ours, [s for s in before if s[0] != REFUNDS])
        self.assertTrue([s for s in before if s[0] == REFUNDS])  # money back is now only on this computer

    def test_money_back_starts_only_on_this_computer_and_writes_nothing(self):
        self.fill()
        self.assertEqual(sharing.current(self.conn, self.registry)[REFUNDS], "local")
        self.assertEqual(self.lines(REFUNDS), [])
        snap = sync.snapshot(self.conn, self.registry)
        self.assertFalse([r for r in snap["records"] if r["table"] == REFUNDS])

    def test_nothing_is_stored_until_the_household_chooses(self):
        self.fill()
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__sharing_choices").fetchone()[0], 0)
        self.assertEqual(sharing.history(self.conn), [])


class TighteningTests(SharingTestCase):
    def test_a_list_kept_here_leaves_the_change_log_at_once_and_writes_nothing_more(self):
        beans = self.fill()
        self.assertTrue(self.lines(ITEMS))
        sharing.apply(self.conn, self.registry, {ITEMS: "local"})
        self.assertEqual(self.lines(ITEMS), [])  # waiting lines are cleaned: nothing has been sent
        self.store.update(ITEMS, beans, {"name": "Red kidney beans"})
        self.store.create(ITEMS, {"name": "Rice", "category": "pantry", "unit": "kg"})
        self.assertEqual(self.lines(ITEMS), [])
        self.assertFalse([r for r in sync.snapshot(self.conn, self.registry)["records"] if r["table"] == ITEMS])
        self.assertTrue(self.lines(MOVES))  # other lists are untouched

    def test_a_detail_kept_here_is_withheld_by_name_only(self):
        beans = self.fill()
        sharing.apply(self.conn, self.registry, {f"{ITEMS}.name": "local"})
        for entry in self.lines(ITEMS):
            self.assertNotIn("name", entry["patch"])
            if entry["action"] == "create":
                self.assertIn("name", entry["withheld"])
        self.store.update(ITEMS, beans, {"name": "Red kidney beans"})
        last = self.lines(ITEMS)[-1]
        self.assertEqual(last["patch"], {})
        self.assertIn("name", last["withheld"])
        self.assertNotIn("Red kidney beans", str(self.lines()))

    def test_shared_but_not_the_amount_keeps_the_private_details_here(self):
        self.fill()
        self.assertEqual(sharing.list_words(self.registry[REFUNDS], "shared_not_private"), "Shared, but not the amount")
        # loosen money back to "but not the amount" and the amount itself to shared: the list choice still wins
        sharing.apply(self.conn, self.registry, {REFUNDS: "shared_not_private", f"{REFUNDS}.amount": "shared"})
        movement = self.bought
        self.store.create(REFUNDS, {"movement": movement, "amount": "0.40", "happened_on": "2026-11-20"})
        (line,) = self.lines(REFUNDS)
        self.assertEqual(set(line["patch"]), {"movement", "happened_on"})
        self.assertIn("amount", line["withheld"])


class FixedTests(SharingTestCase):
    def test_codes_are_fixed_with_a_reason_and_cannot_be_shared(self):
        column = self.registry[EXITS].table.columns["access_details"]
        self.assertIn("passwords", sharing.fixed_reason(column))
        self.assertEqual(sharing.detail_options(column), [])
        with self.assertRaises(sharing.SharingError):
            sharing.apply(self.conn, self.registry, {f"{EXITS}.access_details": "shared"})
        client = self.client()
        page = client.get("/settings/sharing", base_url=BASE).get_data(as_text=True)
        self.assertIn("always only on this computer", page)
        self.assertNotIn(f'name="c:{EXITS}.access_details"', page)
        refused = self.post(client, "/settings/sharing", **{f"c:{EXITS}.access_details": "shared"})
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__sharing_choices").fetchone()[0], 0)
        self.fill()
        self.assertNotIn("4321", str(self.lines()))

    def test_a_module_can_only_fix_a_value_that_never_travels(self):
        problems = []
        modules._parse_column("tables.toml", "t", "code", {"type": "text", "travels_fixed": "Because."}, problems)
        self.assertTrue(any("travels_fixed" in p for p in problems))

    def test_core_code_names_no_module(self):
        source = (ROOT / "src" / "dashboard" / "core" / "sync_sharing.py").read_text(encoding="utf-8")
        for name in ("stock", "refund", "home_layout", "people", "medicine"):
            self.assertNotIn(f'"{name}', source)

    def test_medical_details_are_choosable_once_confirmed(self):
        # User 1: sharing is consent based; only passwords and the like may never be shared.
        column = self.registry[INFO].table.columns["detail"]
        self.assertEqual(sharing.detail_options(column), ["kinds", "local"])
        self.assertTrue(sharing.needs_confirmation(sharing.starts(self.conn, self.registry, {f"{MOVES}.price": "shared"})))


class WebTests(SharingTestCase):
    def test_the_page_lists_every_list_grouped_with_plain_choices_and_no_script(self):
        client = self.client()
        response = client.get("/settings/sharing", base_url=BASE)
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        for said in ("What your other computers get", "Household stock", "Money back", "Shared with your other computers",
                     "Only on this computer", "Shared, but not the amount", "when your computers are paired",
                     "Settings, Helpers", "not taken back", "Usual:"):
            self.assertIn(said, page)
        self.assertIn(f'name="c:{REFUNDS}" value="local" checked', page)
        for name in ("sharing.html", "sharing_confirm.html"):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertNotIn("<script", text)
            self.assertIsNone(re.search(r"\son[a-z]+=", text))
            self.assertNotIn("style=", text)  # nothing fixed-width: it reflows at 320px
            self.assertNotIn("<table", text)
        self.assertIn('href="/settings/sharing"', client.get("/settings", base_url=BASE).get_data(as_text=True))

    def test_every_post_needs_the_page_token(self):
        client = self.client()
        for path in ("/settings/sharing", "/settings/sharing/confirm", "/settings/sharing/undo"):
            refused = client.post(path, base_url=BASE, data={f"c:{ITEMS}": "local", "confirm": "yes", "entry": "1"})
            self.assertEqual(refused.status_code, 400, path)
        self.assertEqual(sharing.current(self.conn, self.registry)[ITEMS], "shared")

    def test_keeping_here_is_immediate_and_recorded_in_history(self):
        client = self.client()
        saved = self.post(client, "/settings/sharing", **{f"c:{ITEMS}": "local"})
        self.assertEqual(saved.status_code, 303)
        self.assertEqual(sharing.current(self.conn, self.registry)[ITEMS], "local")
        (entry,) = sharing.history(self.conn)
        self.assertEqual((entry["before"], entry["after"], entry["loosened"]), ({ITEMS: "shared"}, {ITEMS: "local"}, False))
        page = client.get(saved.headers["Location"], base_url=BASE).get_data(as_text=True)
        self.assertIn("Saved. From now on:", page)
        self.assertIn("Stock items: Shared with your other computers → Only on this computer", page)

    def test_sharing_something_private_asks_first_then_can_be_undone(self):
        self.fill()
        client = self.client()
        asked = self.post(client, "/settings/sharing", **{f"c:{REFUNDS}": "shared", f"c:{ITEMS}": "local"})
        page = asked.get_data(as_text=True)
        self.assertEqual(asked.status_code, 200)
        self.assertIn("Start sharing these private things?", page)
        self.assertIn("that its records exist", page)
        self.assertIn("Yes, start sharing these", page)
        now = sharing.current(self.conn, self.registry)
        self.assertEqual((now[REFUNDS], now[ITEMS]), ("local", "local"))  # keeping here was saved at once
        # Go back: nothing is shared. Out of date: nothing is shared.
        stale = self.post(client, "/settings/sharing/confirm", confirm="yes",
                          **{f"want:{REFUNDS}": "shared", f"was:{REFUNDS}": "shared"})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(sharing.current(self.conn, self.registry)[REFUNDS], "local")
        done = self.post(client, "/settings/sharing/confirm", confirm="yes",
                         **{f"want:{REFUNDS}": "shared", f"was:{REFUNDS}": "local"})
        self.assertEqual(done.status_code, 303)
        self.assertEqual(sharing.current(self.conn, self.registry)[REFUNDS], "shared")
        self.assertEqual(self.lines(REFUNDS), [])  # future changes only: the earlier refund is not added
        movement = self.bought
        self.store.create(REFUNDS, {"movement": movement, "amount": "0.40", "happened_on": "2026-11-20"})
        (line,) = self.lines(REFUNDS)
        self.assertNotIn("amount", line["patch"])  # the amount keeps its own choice: only on this computer
        entry = sharing.history(self.conn)[0]
        self.assertTrue(entry["loosened"])
        self.assertIn("Undo", client.get(done.headers["Location"], base_url=BASE).get_data(as_text=True))
        undone = self.post(client, "/settings/sharing/undo", entry=str(entry["id"]))
        self.assertEqual(undone.status_code, 303)
        self.assertEqual(sharing.current(self.conn, self.registry)[REFUNDS], "local")
        self.assertEqual(self.lines(REFUNDS), [])  # the waiting line is held back again
        self.assertEqual(sharing.history(self.conn)[0]["action"], "sharing_undo")
        again = self.post(client, "/settings/sharing/undo", entry=str(entry["id"]))
        self.assertEqual(again.status_code, 409)

    def test_sharing_an_ordinary_detail_again_needs_no_confirmation_but_has_undo(self):
        client = self.client()
        self.post(client, "/settings/sharing", **{f"c:{ITEMS}.name": "local"})
        back = self.post(client, "/settings/sharing", **{f"c:{ITEMS}.name": "shared"})
        self.assertEqual(back.status_code, 303)
        self.assertEqual(sharing.current(self.conn, self.registry)[f"{ITEMS}.name"], "shared")
        self.assertTrue(sharing.undoable(self.conn, self.registry, sharing.history(self.conn)[0]))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__sharing_choices").fetchone()[0], 0)

    def test_a_private_price_needs_confirmation_on_the_page(self):
        client = self.client()
        asked = self.post(client, "/settings/sharing", **{f"c:{MOVES}.price": "shared"})
        self.assertIn("What you paid", asked.get_data(as_text=True))
        self.assertIn("(private)", asked.get_data(as_text=True))
        self.assertEqual(sharing.current(self.conn, self.registry)[f"{MOVES}.price"], "local")


class FilesTests(TempDirTestCase):
    def test_the_decision_is_recorded_and_indexed(self):
        found = list((ROOT / "docs" / "decisions").glob("0140-*.md"))
        self.assertEqual(len(found), 1)
        text = found[0].read_text(encoding="utf-8")
        self.assertIn("consent based", text)
        self.assertIn("0140", (ROOT / "docs" / "decisions" / "INDEX.md").read_text(encoding="utf-8"))
        self.assertIn("0140", Path(ROOT / "docs" / "decisions" / "0100-sync-stage-1-stable-ids-and-change-log.md")
                      .read_text(encoding="utf-8").split("\n", 3)[2])
