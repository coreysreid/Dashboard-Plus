"""Tests for money back on a priced Stock in, a price typed on Review and the read-only line total (decision 0133)."""
import io
import re
import shutil
import zipfile
from datetime import date, datetime, timezone

from support import ROOT, TempDirTestCase
from test_receipt_review import ReceiptTestCase
from dashboard import __version__
from dashboard.core import db, export, helpers, modules, proposals, records, settings, startup, sync
from dashboard.web.app import create_app

PORT = 5154
BASE = f"http://127.0.0.1:{PORT}"
ITEMS, MOVES, REFUNDS = "stock__items", "stock__movements", "stock__refunds"
TODAY = date(2026, 11, 20)
NOW = datetime(2026, 11, 20, 1, 0, tzinfo=timezone.utc)
SENTINEL = "876.54"  # an invented note that must never leave the private places
DAY = "2026-11-20"


def words(page: str) -> str:
    main = page[page.index("<main>"):page.index("</main>")]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", main))


class RefundTestCase(TempDirTestCase):
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
        # 2 tins at 3.80 in all (November), and 1 bottle at 4.20 (September).
        self.nov = self.bought(self.beans, "2026-11-18", 2, "3.80")
        self.sep = self.bought(self.soap, "2026-09-05", 1, "4.20")

    def bought(self, item, on, amount=1, price=None, **more):
        values = {"item": item, "reason": "bought", "amount": amount, "happened_on": on}
        if price:
            values.update(price=price, price_basis="total")
        return self.store.create(MOVES, dict(values, **more))

    def back(self, movement, amount, on="2026-11-19", **more):
        return self.store.create(REFUNDS, dict({"movement": movement, "amount": amount, "happened_on": on}, **more))

    def row(self, refund):
        return self.store.get(REFUNDS, refund)

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


class RefundRulesTests(RefundTestCase):
    def test_money_back_is_linked_to_its_stock_in_and_takes_its_currency(self):
        refund = self.back(self.nov, "1.00")
        saved = self.row(refund)
        self.assertEqual((saved["movement"], saved["amount"], saved["currency"]), (self.nov, 100, "AUD"))
        other = self.bought(self.beans, "2026-11-10", 1, "9.00", currency="nzd")
        self.assertEqual(self.row(self.back(other, "2.00"))["currency"], "NZD", "the Stock in's own currency")
        with self.assertRaises(records.ValidationError) as caught:
            self.back(self.nov, "1.00", currency="NZD")
        self.assertIn("always the one the Stock in was paid in (AUD)", caught.exception.problems["currency"])

    def test_money_back_never_changes_the_stock_amount_or_the_price(self):
        before = self.quantity()
        self.back(self.nov, "3.00")
        self.assertEqual(self.quantity(), before)
        moved = self.store.get(MOVES, self.nov)
        self.assertEqual((moved["price"], moved["paid_total"]), (380, 380))

    def test_a_stock_in_with_no_price_cannot_have_money_back(self):
        plain = self.bought(self.beans, "2026-11-12")
        with self.assertRaises(records.ValidationError) as caught:
            self.back(plain, "1.00")
        self.assertIn("has no price saved", caught.exception.problems["movement"])
        self.assertEqual(self.store.count(REFUNDS), 0)

    def test_money_back_is_more_than_nothing_and_not_more_than_was_paid_unless_confirmed(self):
        with self.assertRaises(records.ValidationError) as caught:
            self.back(self.nov, "0")
        self.assertIn("must be more than 0", caught.exception.problems["amount"])
        self.back(self.nov, "3.00")
        with self.assertRaises(records.ValidationError) as caught:
            self.back(self.nov, "1.00")  # 4.00 in all against 3.80 paid
        self.assertIn("above what was paid", caught.exception.problems["amount"])
        self.assertIn("This is more than was paid", caught.exception.problems["amount"])
        self.assertEqual(self.store.count(REFUNDS), 1, "nothing was saved")
        confirmed = self.back(self.nov, "1.00", over_paid="yes")
        self.assertEqual(self.row(confirmed)["amount"], 100)

    def test_correcting_a_refund_is_not_counted_against_itself(self):
        refund = self.back(self.nov, "3.00")
        self.store.update(REFUNDS, refund, {"amount": "3.80"})
        self.assertEqual(self.row(refund)["amount"], 380)
        with self.assertRaises(records.ValidationError):
            self.store.update(REFUNDS, refund, {"amount": "3.90"})
        self.assertEqual(self.row(refund)["amount"], 380)
        self.store.update(REFUNDS, refund, {"notes": "Receipt checked"})
        self.assertEqual([h["action"] for h in self.store.history(REFUNDS, refund)].count("update"), 2)

    def test_a_deleted_refund_no_longer_counts(self):
        refund = self.back(self.nov, "3.00")
        self.store.delete(REFUNDS, refund)
        self.back(self.nov, "3.80")

    def test_the_declaration_is_checked_in_plain_words(self):
        tables = ('[tables.log]\ntitle = "Log"\ncolumns.paid = { type = "money" }\n\n[tables.back]\ntitle = "Back"\n'
                  'columns.log = { type = "link", to = "log" }\ncolumns.day = { type = "date" }\n'
                  'columns.cash = { type = "money" }\ncolumns.code = { type = "text" }\n\n'
                  '[tables.back.refund]\nof = "log"\nwhen = "day"\npaid = "paid"\ncurrency_of = "code"\n'
                  'amount = "cash"\ncurrency = "code"\nconfirm = "log"\ncolour = "red"\n')
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(self.make_module(tables=tables, labels=None))
        text = str(caught.exception)
        for said in ("'of' must name a required link column", "'when' must name a required date column",
                     "'amount' must name a required money column", "private (sensitive = true)",
                     "four different columns", "unknown setting 'colour'"):
            self.assertIn(said, text)

    def test_a_returned_stock_out_is_a_separate_choice_that_takes_the_goods_off_the_shelf(self):
        self.bought(self.beans, "2026-11-01", 3)
        self.back(self.nov, "1.00")
        self.assertEqual(self.quantity(), 5)
        self.store.create(MOVES, {"item": self.beans, "reason": "returned", "amount": 1, "happened_on": "2026-11-19"})
        self.assertEqual(self.quantity(), 4)
        with self.assertRaises(records.ValidationError):
            self.store.create(MOVES, {"item": self.beans, "reason": "returned", "amount": 1,
                                      "happened_on": "2026-11-19", "price": "1.00", "price_basis": "total"})


class RefundPrivacyTests(RefundTestCase):
    def test_every_money_back_column_is_private_and_stays_on_this_computer(self):
        columns = self.registry[REFUNDS].table.columns
        for name in ("amount", "currency", "over_paid", "notes"):
            self.assertTrue(columns[name].sensitive, name)
            self.assertEqual((columns[name].travels, columns[name].travels_reviewed), ("never", True), name)

    def test_the_change_log_and_the_export_never_carry_money_back(self):
        self.back(self.nov, "2.46", notes="Invented note about " + SENTINEL)
        for entry in sync.changes(self.conn):
            if entry["table_name"] == REFUNDS:
                self.assertFalse({"amount", "currency", "over_paid", "notes"} & set(entry["patch"]))
        raw = export.build(self.conn, self.registry, __version__, True, NOW)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for name in archive.namelist():
                text = archive.read(name).decode("utf-8", "replace")
                self.assertNotIn(SENTINEL, text, name)
                self.assertNotIn("2.46", text, name)

    def test_a_helper_may_not_suggest_money_back(self):
        helper = helpers.Helper(1, "k", "pantry", "Pantry helper", "suggest", ["stock"], "2026-11-01", None, None)
        with self.assertRaises(proposals.ProposalError) as caught:
            proposals._check_tables(helper, self.registry, [(REFUNDS, {"movement": self.nov, "amount": "1.00"})])
        self.assertEqual(caught.exception.code, "private_detail")

    def test_the_list_and_the_stock_in_page_never_show_an_amount_before_show(self):
        self.back(self.nov, "1.23")
        client = self.client()
        self.assertNotIn("1.23", self.page(client, f"/t/{REFUNDS}"))
        stock_in = self.page(client, f"/t/{MOVES}/{self.nov}")
        self.assertNotIn("1.23", stock_in)
        self.assertIn("Money back", stock_in)
        self.assertIn("Record money back", stock_in)
        revealed = self.post(client, f"/t/{REFUNDS}/1/reveal", column="amount")
        self.assertEqual(revealed.headers.get("Cache-Control"), "no-store")
        self.assertIn("1.23", revealed.get_data(as_text=True))

    def test_the_form_asks_for_money_back_and_says_stock_is_separate(self):
        client = self.client()
        form = self.page(client, f"/t/{REFUNDS}/new?movement={self.nov}")
        for said in ("Which Stock in", "Money back", "This is more than was paid", "Returned to the shop"):
            self.assertIn(said, form)
        saved = self.post(client, f"/t/{REFUNDS}/new", movement=self.nov, amount="1.00", happened_on="19/11/26",
                          then="done")
        self.assertIn(saved.status_code, (200, 302))
        self.assertEqual(self.store.count(REFUNDS), 1)


class MoneyBackInSpentTests(RefundTestCase):
    def setUp(self):
        super().setUp()
        self.back(self.nov, "3.00", on="2026-11-19")
        self.back(self.sep, "1.00", on="2026-09-20")
        self.web = self.client()
        self.path = f"/bars/{MOVES}/spending"

    def shown(self, **data):
        return words(self.post(self.web, self.path, by="month", **data).get_data(as_text=True))

    def test_before_show_nothing_of_the_money_back_is_on_the_page(self):
        text = words(self.page(self.web, self.path))
        for secret in ("3.00", "refunded", "less"):
            self.assertNotIn(secret, text)

    def test_show_says_less_refunded_in_words_and_in_the_table_and_never_a_negative_bar(self):
        reply = self.post(self.web, self.path, by="month")
        text = words(reply.get_data(as_text=True))
        self.assertIn("November 2026 (so far) 3.80 AUD spent, less 3.00 refunded", text)
        self.assertIn("September 2026 4.20 AUD spent, less 1.00 refunded", text)
        self.assertIn("8.00 AUD spent, from 2 Stock ins, less 4.00 refunded (4.00 AUD after money back)", text)
        self.assertNotIn("3.80 AUD spent, less 4.00", text)
        self.assertNotRegex(text, r"-\d")

    def test_money_back_in_a_month_with_no_stock_in_is_said_and_not_taken_off_another_month(self):
        self.store.update(REFUNDS, 2, {"happened_on": "2026-10-03"})
        text = self.shown()
        self.assertIn("October 2026 Nothing spent, 1.00 refunded", text)
        self.assertIn("September 2026 4.20 AUD spent 1 Stock in recorded", text, "money back is not taken off")
        self.assertNotIn("September 2026 4.20 AUD spent, less", text)

    def test_each_category_has_its_own_money_back_and_other_currencies_are_said_not_taken_off(self):
        other = self.bought(self.soap, "2026-09-06", 1, "9.00", currency="NZD")
        self.back(other, "2.00", on="2026-09-07")
        text = self.shown()
        self.assertIn("also 2.00 NZD refunded, not in this chart", text)
        self.assertIn("Also refunded in another currency, not taken off and never converted: 2.00 NZD.", text)
        self.assertIn("Toiletries", text)
        self.assertIn("less 1.00 refunded", text)
        self.assertIn("Pantry", text)
        self.assertIn("less 3.00 refunded", text)

    def test_a_deleted_refund_or_stock_in_stops_showing(self):
        self.store.delete(REFUNDS, 1)
        self.assertNotIn("3.00 refunded", self.shown())


class StockInPageTests(RefundTestCase):
    def test_the_line_total_is_read_only_and_behind_show(self):
        each = self.bought(self.beans, "2026-11-10", 3, price=None)
        self.store.update(MOVES, each, {"price": "1.50", "price_basis": "each"})
        client = self.client()
        page = self.page(client, f"/t/{MOVES}/{each}")
        self.assertIn("Line total (worked out from the price, not typed)", page)
        self.assertNotIn("4.50", page)
        self.assertNotIn('name="paid_total"', page, "no field to type one")
        revealed = self.post(client, f"/t/{MOVES}/{each}/reveal", column="paid_total")
        self.assertIn("4.50 AUD", revealed.get_data(as_text=True))
        plain = self.bought(self.beans, "2026-11-11")
        self.assertNotIn("data-line-total", self.page(client, f"/t/{MOVES}/{plain}"))


class ReviewPriceTests(ReceiptTestCase):
    def two(self, **hints):
        return self.send([self.bought(self.tomatoes, 3, source="TINNED TOMATOES 400G x3"),
                          self.line(**dict({"receipt_date": DAY, "quantity_hint": "1", "unit_hint": "tin"}, **hints))])

    def row(self):
        return self.conn.execute("SELECT * FROM stock__movements ORDER BY id DESC").fetchone()

    def test_review_offers_a_price_but_never_fills_in_the_receipts(self):
        self.send([dict(self.bought(self.tomatoes, 3), source={"line": "TOMATOES x3", "price": "$7.77"})])
        page = self.page()
        self.assertIn("Save a price with this Stock in?", page)
        self.assertIn("The paper shows <bdi>$7.77</bdi>, for checking: it is never copied in for you.", page)
        self.assertNotRegex(page, r'name="price"[^>]*value=')
        self.assertIn('name="price_basis"', page)

    def test_accepting_without_a_price_saves_none(self):
        self.send([dict(self.bought(self.tomatoes, 3), source={"line": "TOMATOES x3", "price": "$7.77"})])
        row = self.conn.execute("SELECT id FROM core__proposals").fetchone()
        self.follow(f"/review/{row['id']}/accept")
        self.assertEqual([self.row()[c] for c in ("price", "price_basis", "paid_total", "currency")], [None] * 4)
        self.assertNotIn("7.77", str(dict(self.row())))

    def test_the_price_a_person_types_is_saved_with_the_stock_in_in_one_step(self):
        self.send([dict(self.bought(self.tomatoes, 3), source={"line": "TOMATOES x3", "price": "$7.77"})])
        row = self.conn.execute("SELECT id FROM core__proposals").fetchone()
        page = self.follow(f"/review/{row['id']}/accept", {"price": "1.90", "price_basis": "each"})
        self.assertIn("Added to", page)
        saved = self.row()
        self.assertEqual((saved["price"], saved["price_basis"], saved["paid_total"], saved["currency"]),
                         (190, "each", 570, "AUD"))
        self.assertEqual(self.amount(self.tomatoes), 4, "a price never changes the stock amount")
        self.assertEqual(saved["source"], "agent:" + self.helper.slug)

    def test_a_price_that_does_not_say_what_it_means_adds_nothing_and_says_why(self):
        self.send([self.bought(self.tomatoes, 3)])
        row = self.conn.execute("SELECT id FROM core__proposals").fetchone()
        page = self.follow(f"/review/{row['id']}/accept", {"price": "1.90"})
        self.assertIn("could not be added", page)
        self.assertIn("Nothing was added: the price was not saved. That price is say whether", page)
        self.assertEqual((self.count("stock__movements"), self.amount(self.tomatoes)), (0, 1))
        again = self.follow(f"/review/{row['id']}/accept", {"price": "1.90", "price_basis": "total"})
        self.assertIn("Added to", again)
        self.assertEqual(self.row()["paid_total"], 190)

    def test_a_helper_still_cannot_send_a_price(self):
        with self.assertRaises(ProposalError) as caught:
            self.send([dict(self.bought(self.tomatoes, 3), values={"item": self.tomatoes, "reason": "bought",
                                                                  "amount": 3, "price": "3.00"})])
        self.assertEqual(caught.exception.code, "private_detail")

    def test_a_receipt_line_chosen_by_hand_can_save_a_price_too(self):
        result = self.two()
        line = self.line_id(result)
        form = self.page(f"/review/line/{line}?item={self.tomatoes}")
        self.assertIn("Save a price with this Stock in?", form)
        self.assertIn("The paper shows <bdi>$1.50</bdi>, for checking: it is not copied in for you.", form)
        self.assertNotRegex(form, r'name="price"[^>]*value="[^"]')
        revision = re.search(r'name="revision" value="(\d+)"', form).group(1)
        fields = {"item": self.tomatoes, "revision": revision, "amount": "1", "when": "20/11/26"}
        bad = self.post(f"/review/line/{line}/save", dict(fields, price="1.50"))
        self.assertEqual(bad.status_code, 400)
        self.assertIn("say whether the price", bad.get_data(as_text=True))
        self.assertEqual(self.count("stock__movements"), 0)
        self.assertIn('value="1.50"', bad.get_data(as_text=True), "what they typed comes back")
        page = self.follow(f"/review/line/{line}/save", dict(fields, price="1.50", price_basis="total"))
        self.assertIn("Added 1 tin of Tinned tomatoes", page)
        self.assertEqual((self.row()["paid_total"], self.row()["currency"]), (150, "AUD"))

    def test_accept_all_saves_no_price(self):
        self.send([dict(self.bought(self.tomatoes, 3), source={"line": "TOMATOES x3", "price": "$7.77"})])
        batch = self.conn.execute("SELECT batch_id FROM core__proposals").fetchone()["batch_id"]
        self.follow(f"/review/batch/{batch}/accept-all")
        self.assertIsNone(self.row()["price"])


from dashboard.core.proposals import ProposalError  # noqa: E402


class ExampleTests(TempDirTestCase):
    def test_each_example_household_has_at_most_one_invented_refund_on_a_priced_stock_in(self):
        import load_example
        for household in ("smith", "garcia", "taylor"):
            with self.subTest(household=household):
                load_example.load(household, self.tmp / household, today=TODAY)
                conn = db.connect(self.tmp / household / "dashboard.db")
                self.addCleanup(conn.close)
                rows = [dict(r) for r in conn.execute(
                    f"SELECT r.amount, r.currency, m.paid_total, m.currency AS paid_in, m.happened_on, "
                    f"m.item FROM {REFUNDS} r JOIN {MOVES} m ON m.id = r.movement")]
                self.assertLessEqual(len(rows), 1)
                for row in rows:
                    self.assertEqual(row["currency"], row["paid_in"])
                    self.assertLessEqual(row["amount"], row["paid_total"])
                lines = [(r["item"], r["amount"], r["happened_on"]) for r in conn.execute(
                    f"SELECT item, amount, happened_on FROM {MOVES}")]
                self.assertEqual(len(lines), len(set(lines)), "no Stock in is repeated to carry a refund")
        smith = db.connect(self.tmp / "smith" / "dashboard.db")
        self.addCleanup(smith.close)
        self.assertEqual(smith.execute(f"SELECT COUNT(*) FROM {REFUNDS}").fetchone()[0], 1)


class MigrationTests(TempDirTestCase):
    def test_the_change_is_additive_and_keeps_every_stock_in_and_price(self):
        old = self.tmp / "old" / "stock"
        shutil.copytree(ROOT / "modules" / "stock", old)
        (old / "migrations" / "0009_money_back.sql").unlink()
        text = (old / "tables.toml").read_text(encoding="utf-8")
        start, end = text.index("[tables.refunds]"), text.index("[tables.connections]")
        text = text[:start] + text[end:]
        text = text.replace('refunds = "refunds"\n', "").replace('  { key = "returned", label = "Returned to the shop" },\n', "")
        (old / "tables.toml").write_text(text, encoding="utf-8")
        labels = (old / "labels.toml").read_text(encoding="utf-8")
        labels = labels[:labels.index("# Money back on a Stock in")] + labels[labels.index("[tables.connections]"):]
        (old / "labels.toml").write_text(labels, encoding="utf-8")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "old")
        self.assertEqual(report.module_problems, {})
        conn = db.connect(data / "dashboard.db")
        store = records.Records(conn, records.build_registry(report.loaded))
        item = store.create(ITEMS, {"name": "Rice", "category": "pantry", "unit": "bags"})
        store.create(MOVES, {"item": item, "reason": "bought", "amount": 2, "happened_on": "2026-11-01",
                             "price": "5.00", "price_basis": "total", "currency": "AUD"})
        conn.close()
        shutil.rmtree(self.tmp / "old" / "stock")
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "old" / "stock")
        report = startup.prepare(data, self.tmp / "old")
        self.assertEqual(report.module_problems, {})
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        rows = [dict(r) for r in conn.execute(f"SELECT amount, price, paid_total, currency FROM {MOVES}")]
        self.assertEqual(rows, [{"amount": 2, "price": 500, "paid_total": 500, "currency": "AUD"}])
        self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {REFUNDS}").fetchone()[0], 0)
        self.assertTrue(any(p.name.startswith("before-update-") for p in (data / "backups").rglob("*")))
