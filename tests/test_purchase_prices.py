"""Tests for confirmed purchase prices on a Stock in and Spent per month (decision 0128): what a price means, its currency, privacy, the additive migration and the bars."""
import io
import re
import shutil
import zipfile
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import db, export, helpers, modules, proposals, records, settings, startup, sync
from dashboard.web.app import create_app

PORT = 5153
BASE = f"http://127.0.0.1:{PORT}"
ITEMS, MOVES = "stock__items", "stock__movements"
TODAY = date(2026, 11, 20)
NOW = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)
SENTINEL = "987.65"  # an invented price that must never leave the private places


def words(page: str) -> str:
    main = page[page.index("<main>"):page.index("</main>")]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", main))


class PriceTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        settings.put(self.conn, "household.country", "Australia")
        self.beans = self.store.create(ITEMS, {"name": "Kidney beans", "category": "pantry", "unit": "tins"})
        self.soap = self.store.create(ITEMS, {"name": "Hand soap", "category": "toiletries", "unit": "bottles"})

    def bought(self, item=None, amount=2, on="2026-11-18", **price):
        return self.store.create(MOVES, dict({"item": item or self.beans, "reason": "bought", "amount": amount,
                                              "happened_on": on}, **price))

    def row(self, record_id):
        return self.store.get(MOVES, record_id)

    def quantity(self, item=None):
        return self.store.get(ITEMS, item or self.beans)["quantity"]

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        app.config["NOW"] = lambda: NOW
        app.config["TODAY"] = lambda: TODAY
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, client, path, status=200):
        response = client.get(path, base_url=BASE)
        self.assertEqual(response.status_code, status, path)
        return response.get_data(as_text=True)

    def post(self, client, path, **data):
        return client.post(path, base_url=BASE, data=dict(data, _csrf=client.csrf))


class SavingTests(PriceTestCase):
    def test_a_price_is_optional_and_never_changes_the_stock_amount(self):
        moved = self.bought()
        self.assertEqual(self.quantity(), 2)
        row = self.row(moved)
        self.assertEqual([row[c] for c in ("price", "price_basis", "paid_total", "currency")], [None] * 4)

    def test_the_total_and_the_price_for_each_one_give_different_line_totals(self):
        total = self.bought(price="3.80", price_basis="total")
        each = self.bought(price="3.80", price_basis="each")
        self.assertEqual((self.row(total)["price"], self.row(total)["paid_total"]), (380, 380))
        self.assertEqual((self.row(each)["price"], self.row(each)["paid_total"]), (380, 760))
        self.assertEqual(self.row(each)["price_basis"], "each")
        self.assertEqual(self.quantity(), 4, "a price never changes the stock amount")

    def test_a_price_that_does_not_say_what_it_means_is_refused_and_nothing_is_saved(self):
        before = self.store.count(MOVES)
        with self.assertRaises(records.ValidationError) as caught:
            self.bought(price="3.80")
        self.assertIn("total for these goods or the price for each one", caught.exception.problems["price_basis"])
        self.assertEqual((self.store.count(MOVES), self.quantity()), (before, None))

    def test_a_price_on_a_stock_out_is_refused(self):
        self.bought(amount=3)
        with self.assertRaises(records.ValidationError) as caught:
            self.store.create(MOVES, {"item": self.beans, "reason": "used", "amount": 1,
                                      "happened_on": "2026-11-19", "price": "1.00", "price_basis": "total"})
        self.assertIn("A Stock out never takes money off", caught.exception.problems["price"])
        self.assertEqual(self.quantity(), 3)

    def test_the_currency_comes_from_settings_or_is_typed_and_is_never_guessed(self):
        self.assertEqual(self.row(self.bought(price="2", price_basis="total"))["currency"], "AUD")
        self.assertEqual(self.row(self.bought(price="2", price_basis="total", currency="nzd"))["currency"], "NZD")
        settings.put(self.conn, "household.currency", "EUR")
        self.assertEqual(self.row(self.bought(price="2", price_basis="total"))["currency"], "EUR")
        settings.put(self.conn, "household.currency", None)
        settings.put(self.conn, "household.country", "Somewhere invented")
        with self.assertRaises(records.ValidationError) as caught:
            self.bought(price="2", price_basis="total")
        self.assertIn("choose the household's usual currency in Settings", caught.exception.problems["currency"])
        with self.assertRaises(records.ValidationError) as caught:
            self.bought(price="2", price_basis="total", currency="dollars")
        self.assertIn("three-letter currency code", caught.exception.problems["currency"])

    def test_a_price_can_be_added_or_corrected_afterwards_without_changing_the_amount(self):
        moved = self.bought()
        self.store.update(MOVES, moved, {"price": "1.90", "price_basis": "each"})
        self.assertEqual((self.row(moved)["paid_total"], self.row(moved)["currency"]), (380, "AUD"))
        self.store.update(MOVES, moved, {"amount": 3})
        self.assertEqual(self.row(moved)["paid_total"], 570, "a price for each follows the amount")
        self.store.update(MOVES, moved, {"price_basis": "total"})
        self.assertEqual(self.row(moved)["paid_total"], 190)
        self.store.update(MOVES, moved, {"price": ""})
        self.assertEqual([self.row(moved)[c] for c in ("price_basis", "paid_total", "currency")], [None] * 3)
        self.assertEqual(self.quantity(), 3)
        actions = [h["action"] for h in self.store.history(MOVES, moved)]
        self.assertEqual(actions.count("update"), 4, "every correction is in the record's history")
        with self.assertRaises(records.ValidationError):
            self.store.update(MOVES, moved, {"price": "1.00", "price_basis": "total", "reason": "used"})

    def test_the_declaration_is_checked_in_plain_words(self):
        tables = ('[tables.log]\ntitle = "Log"\ncolumns.kind = { type = "choice", required = true, choices = '
                  '["bought", "used"] }\ncolumns.amount = { type = "decimal" }\ncolumns.paid = { type = "money" }\n'
                  'columns.basis = { type = "choice", sensitive = true, travels = "never", choices = ["total", '
                  '"some"] }\ncolumns.total = { type = "money", sensitive = true, travels = "never" }\n'
                  'columns.money = { type = "text", sensitive = true, travels = "never" }\n\n[tables.log.price]\n'
                  'paid = "paid"\nbasis = "basis"\ntotal = "total"\ncurrency = "money"\namount = "nothing"\n'
                  'only = { kind = "maybe" }\ncolour = "red"\n')
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(self.make_module(tables=tables, labels=None))
        text = str(caught.exception)
        for said in ("'paid' must name a money column", "private (sensitive = true)",
                     "must offer exactly the choices \"total\" and \"each\"", "'amount' must name the number column",
                     "'only' names the choice a record must have", "'only_words' must say where a price may be saved",
                     "unknown setting 'colour'"):
            self.assertIn(said, text)


class PrivacyTests(PriceTestCase):
    def test_every_price_column_is_private_and_stays_on_this_computer(self):
        columns = self.registry[MOVES].table.columns
        for name in ("price", "price_basis", "paid_total", "currency"):
            self.assertTrue(columns[name].sensitive, name)
            self.assertEqual((columns[name].travels, columns[name].travels_reviewed), ("never", True), name)

    def test_the_change_log_and_the_export_never_carry_a_price(self):
        self.bought(price=SENTINEL, price_basis="total", currency="AUD")
        for entry in sync.changes(self.conn):
            if entry["table_name"] == MOVES:
                self.assertFalse({"price", "paid_total", "currency", "price_basis"} & set(entry["patch"]))
                self.assertIn("price", entry["withheld"])
        raw = export.build(self.conn, self.registry, __version__, True, NOW)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for name in archive.namelist():
                self.assertNotIn(SENTINEL, archive.read(name).decode("utf-8", "replace"), name)

    def test_a_helper_may_not_suggest_a_price(self):
        helper = helpers.Helper(1, "k", "pantry", "Pantry helper", "suggest", ["stock"], "2026-11-01", None, None)
        with self.assertRaises(proposals.ProposalError) as caught:
            proposals._check_tables(helper, self.registry, [(MOVES, {"item": self.beans, "reason": "bought",
                                                                    "amount": 1, "price": "3.80"})])
        self.assertEqual(caught.exception.code, "private_detail")

    def test_the_list_never_shows_a_price_and_the_form_asks_for_one(self):
        self.bought(price=SENTINEL, price_basis="total")
        client = self.client()
        self.assertNotIn(SENTINEL, self.page(client, f"/t/{MOVES}"))
        form = self.page(client, f"/t/{MOVES}/new")
        for said in ("What you paid (optional)", "That price is", "Total for these goods", "Price for each one",
                     "Currency (optional)"):
            self.assertIn(said, form)


class ExampleTests(TempDirTestCase):
    def test_the_example_households_have_a_few_invented_prices_each_on_its_own_stock_in(self):
        import load_example
        expected = {"smith": ("AUD", 1950, 3), "garcia": ("USD", 607, 2), "taylor": ("GBP", 330, 1)}
        for household, (currency, total, priced) in expected.items():
            with self.subTest(household=household):
                load_example.load(household, self.tmp / household, today=TODAY)
                conn = db.connect(self.tmp / household / "dashboard.db")
                self.addCleanup(conn.close)
                rows = [dict(r) for r in conn.execute(
                    f"SELECT item, amount, happened_on, paid_total, currency FROM {MOVES} WHERE price IS NOT NULL")]
                self.assertEqual(len(rows), priced)
                self.assertEqual({r["currency"] for r in rows}, {currency})
                self.assertEqual(sum(r["paid_total"] for r in rows), total)
                lines = [(r["item"], r["amount"], r["happened_on"]) for r in conn.execute(
                    f"SELECT item, amount, happened_on FROM {MOVES} WHERE reason = 'bought'")]
                self.assertEqual(len(lines), len(set(lines)), "no Stock in is repeated to carry a price")


class MigrationTests(TempDirTestCase):
    def test_the_change_is_additive_and_keeps_every_existing_stock_in(self):
        old = self.tmp / "old" / "stock"
        shutil.copytree(ROOT / "modules" / "stock", old)
        (old / "migrations" / "0008_purchase_prices.sql").unlink()
        text = (old / "tables.toml").read_text(encoding="utf-8")
        start, end = text.index("# A confirmed purchase price"), text.index("[tables.movements.adjusts]")
        (old / "tables.toml").write_text(text[:start] + text[end:], encoding="utf-8")
        labels = (old / "labels.toml").read_text(encoding="utf-8")
        labels = labels.replace(', "price", "price_basis", "currency"', "")
        labels = "\n".join(line for line in labels.splitlines()
                           if not line.startswith(("columns.price", "columns.paid_total", "columns.currency")))
        (old / "labels.toml").write_text(labels, encoding="utf-8")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "old")
        self.assertEqual(report.module_problems, {})
        conn = db.connect(data / "dashboard.db")
        store = records.Records(conn, records.build_registry(report.loaded))
        item = store.create(ITEMS, {"name": "Rice", "category": "pantry", "unit": "bags"})
        store.create(MOVES, {"item": item, "reason": "bought", "amount": 2, "happened_on": "2026-11-01"})
        conn.close()
        shutil.rmtree(self.tmp / "old" / "stock")
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "old" / "stock")
        report = startup.prepare(data, self.tmp / "old")
        self.assertEqual(report.module_problems, {})
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        rows = [dict(r) for r in conn.execute(f"SELECT amount, price, paid_total, currency FROM {MOVES}")]
        self.assertEqual(rows, [{"amount": 2, "price": None, "paid_total": None, "currency": None}])
        self.assertTrue(any(p.name.startswith("before-update-") for p in (data / "backups").rglob("*")),
                        "a backup is made before the change")


class SpentTests(PriceTestCase):
    def setUp(self):
        super().setUp()
        self.bought(on="2026-11-18", price="3.80", price_basis="total")
        self.bought(on="2026-11-10", amount=3, price="1.50", price_basis="each")
        self.bought(on="2026-11-12")  # no price: counted, never read as zero
        self.bought(item=self.soap, on="2026-09-05", amount=1, price="4.20", price_basis="total")
        self.bought(item=self.soap, on="2026-09-06", amount=1, price="9.00", price_basis="total", currency="NZD")
        self.store.create(MOVES, {"item": self.beans, "reason": "used", "amount": 2, "happened_on": "2026-11-19"})
        self.web = self.client()
        self.path = f"/bars/{MOVES}/spending"

    def test_before_show_the_page_counts_stock_ins_and_shows_no_amount(self):
        page = self.page(self.web, self.path)
        text = words(page)
        self.assertIn("Stock ins per month", text)
        self.assertIn("Amounts are private — press Show to see them.", text)
        for secret in ("8.30", "4.20", "AUD", "NZD"):
            self.assertNotIn(secret, text)
        self.assertIn("data-show-bars", page)
        self.assertNotIn("8.30", words(self.page(self.web, f"{self.path}?show=1")), "an address never shows")

    def test_show_adds_up_typed_prices_in_one_currency_and_says_the_rest(self):
        reply = self.post(self.web, self.path, by="month")
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply.headers.get("Cache-Control"), "no-store")
        text = words(reply.get_data(as_text=True))
        self.assertIn("Spent per month in AUD", text)
        self.assertIn("November 2026 (so far) 8.30 AUD spent", text, "3.80 + 3 x 1.50; the Stock out takes nothing off")
        self.assertIn("1 with no price", text)
        self.assertIn("September 2026 4.20 AUD spent", text)
        self.assertIn("also 9.00 NZD, not in this chart", text)
        self.assertIn("October 2026 Nothing recorded", text)
        self.assertIn("Only prices typed in for a Stock in are added up", text)
        self.assertIn("never converted", text)
        self.assertIn("Each category on its own", text)
        self.assertIn("Toiletries", text)
        self.assertIn("Hide amounts", text)
        self.assertIn("12.50 AUD spent, from 3 Stock ins", text)
        self.assertIn("1 Stock in has no price, so it is counted but not added.", text)
        refused = self.web.post(self.path, base_url=BASE, data={"by": "month"})
        self.assertIn(refused.status_code, (400, 403), "no session check: refused")

    def test_other_months_and_currencies_are_pressed_buttons_after_show(self):
        page = self.post(self.web, self.path, by="month").get_data(as_text=True)
        self.assertIn('name="unit" value="NZD"', page)
        self.assertNotIn(f'href="{self.path}?by=week', page)
        nzd = words(self.post(self.web, self.path, by="month", unit="NZD").get_data(as_text=True))
        self.assertIn("Spent per month in NZD", nzd)
        self.assertIn("September 2026 9.00 NZD spent", nzd)

    def test_the_chart_is_on_household_stock(self):
        home = self.page(self.web, "/")
        self.assertIn(f'href="{self.path}"', home)
        self.assertIn("Spent per month", home)
        self.assertIn(f'href="{self.path}"', self.page(self.web, f"/t/{MOVES}"))

    def test_with_no_stock_in_it_says_so(self):
        self.conn.execute(f"UPDATE {MOVES} SET deleted_at = '2026-11-20T00:00:00'")
        self.conn.commit()
        self.assertIn("No Stock ins recorded for Household stock yet.", words(self.page(self.web, self.path)))

    def test_settings_offers_the_households_currency(self):
        page = self.page(self.web, "/settings")
        self.assertIn("Prices you type are usually in", page)
        self.assertIn('value="AUD" selected', page)
