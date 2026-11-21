"""Tests for receipts on Review (decision 0105): clearer group words, lines a helper could not match, and repeat receipts."""
import io
import json
import re
import shutil
import time
import zipfile

from support import ROOT, TempDirTestCase
from dashboard.core import db, export, helpers, proposals, receipts, records, settings, startup
from dashboard.core.proposals import ProposalError
from dashboard.errors import PlainError
from dashboard.web.app import create_app

PORT = 5143
BASE = f"http://127.0.0.1:{PORT}"
WHY = "Invented Example Market receipt, 20/11/26"
DAY = "2026-11-20"
CONTEXT = {"purchase_date": DAY, "shop_label": "Example Market"}
LINE = "TOM SPECIAL 400G  1 @ $1.50"


class ReceiptTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", "Australia")
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.beans = self.store.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 13})
        self.tomatoes = self.store.create("stock__items", {"name": "Tinned tomatoes", "unit": "tins", "quantity": 1})
        self.rice = self.store.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        self.helper, self.key = helpers.issue(self.conn, self.data, "Example receipt helper", "suggest", ["stock"])
        self.app = create_app("shutdown-token", lambda: None, self.report, data_dir=self.data, session_key="session-key")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=session-key", base_url=BASE)
        self.csrf = self.app.config["CSRF_TOKEN"]

    # ----- sending ------------------------------------------------------------------------------------
    @staticmethod
    def bought(item, amount=1, source=None, day=DAY):
        entry = {"table": "stock__movements", "values": {"item": item, "reason": "bought", "amount": amount,
                                                          "happened_on": day}}
        if source:
            entry["source"] = {"line": source}
        return entry

    @staticmethod
    def line(text=LINE, **hints):
        return dict({"kind": "unmatched_product_line", "source": {"line": text, "price": "$1.50"}}, **hints)

    def send(self, entries, key="receipt-1", context=None, helper=None, why=WHY):
        body = {"request_key": key, "why": why, "entries": entries}
        if context is not None:
            body["receipt_context"] = context
        return proposals.submit(self.conn, self.registry, helper or self.helper, body)[0]

    def refused(self, entries, status, code, **more):
        with self.assertRaises(ProposalError) as caught:
            self.send(entries, **more)
        self.assertEqual((caught.exception.status, caught.exception.code), (status, code))
        self.assertEqual(self.count("core__proposals"), 0)
        return caught.exception

    def basket(self, key="receipt-1", **more):
        """Three goods from one invented receipt."""
        return self.send([self.bought(self.beans, 2), self.bought(self.tomatoes, 3), self.bought(self.rice, 1)],
                         key=key, context=CONTEXT, **more)

    # ----- reading --------------------------------------------------------------------------------------
    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def amount(self, item):
        return self.store.get("stock__items", item)["quantity"]

    def page(self, path="/review"):
        return self.client.get(path, base_url=BASE).get_data(as_text=True)

    def post(self, path, data=None):
        return self.client.post(path, data=dict(data or {}, _csrf=self.csrf), base_url=BASE)

    def follow(self, path, data=None):
        response = self.post(path, data)
        self.assertEqual(response.status_code, 302, response.get_data(as_text=True)[:300])
        return self.page(response.headers["Location"])

    def status(self, page):
        return re.search(r'role="status">([^<]*)<', page).group(1)

    def line_id(self, result, position=-1):
        return result["proposals"][position]["id"]


class WordingTests(ReceiptTestCase):
    """Item 82: words that are true under group-by-group Accept (0101), and amounts with their unit."""

    def receipt(self):
        return self.send([self.bought(self.beans, 2), self.bought(self.tomatoes, 3),
                          {"table": "stock__items", "values": {"name": "Demo red lentils", "category": "pantry",
                                                                "unit": "packs"}},
                          self.bought({"ref": 2}, 1)])

    def test_a_bought_row_says_its_amount_unit_item_and_date(self):
        self.receipt()
        page = self.page()
        self.assertIn("<bdi>Add 1 pack of Demo red lentils on 20/11/26</bdi>", page)
        self.assertIn("<bdi>Add 2 tins of Kidney beans on 20/11/26</bdi>", page)
        self.assertIn("<bdi>Add 3 tins of Tinned tomatoes on 20/11/26</bdi>", page)
        self.assertNotIn("Amount to add or use", page)
        self.assertNotIn("Reason: <bdi>Bought or added", page)

    def test_a_row_taking_some_away_says_so_with_its_reason(self):
        self.send([{"table": "stock__movements", "values": {"item": self.beans, "reason": "used", "amount": 1,
                                                            "happened_on": DAY}}])
        page = self.page()
        self.assertIn("<bdi>Take away 1 tin of Kidney beans on 20/11/26</bdi> · Reason: <bdi>Used</bdi>", page)

    def test_the_group_says_what_each_button_does(self):
        self.receipt()
        page = self.page()
        self.assertIn("Accepting the Stock in also adds its new Stock item. Accepting only the Stock item leaves the "
                      "Stock in waiting. Rejecting the Stock item rejects the Stock in too. Ticking one ticks both, "
                      "and Accept all or Accept ticked adds both or neither.", page)
        self.assertIn("Accepting this Stock in also adds its new Stock item above.", page)
        self.assertIn("Accepting only this leaves the 1 row below waiting.", page)
        self.assertIn('Accept<span class="hidden-words"> Stock in and its new Stock item</span>', page)

    def test_the_group_words_are_true(self):
        """Accept on the item alone leaves its Stock in waiting; Accept on the Stock in adds both."""
        result = self.receipt()
        item, movement = result["proposals"][2]["id"], result["proposals"][3]["id"]
        page = self.follow(f"/review/{item}/accept")
        self.assertIn("Added to Stock items.", page)
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals WHERE id = ?", (movement,)).fetchone()[0],
                         "pending")

    def test_the_result_line_names_what_was_added(self):
        result = self.receipt()
        page = self.follow(f"/review/batch/{result['batch_id']}/accept-all")
        self.assertIn("Added 3 to Stock in and out and 1 to Stock items.", page)
        self.assertEqual(self.amount(self.beans), 15)

    def test_the_result_line_cannot_be_made_to_name_other_tables(self):
        page = self.page("/review?done=added_many&added=2&n=%3Cb%3Eevil:2&n=stock__items:99999")
        self.assertIn("Added 10000 to Stock items.", page)
        self.assertNotIn("evil", page)


class GuideTests(ReceiptTestCase):
    def test_the_helper_guide_explains_one_receipt_and_unmatched_lines(self):
        from dashboard.web import helper_guide
        with self.app.test_request_context(base_url=BASE):
            text = helper_guide.guide_text(self.conn, self.registry, self.helper)
            self.assertIn('"receipt_context": {"purchase_date": "2026-11-20"', text)
            self.assertIn('{"kind": "unmatched_product_line"', text)
            self.assertIn("Never send totals, tax, discounts, coupons, payments, refunds, card or loyalty numbers.", text)
            shutil.copytree(ROOT / "modules" / "pets", self.tmp / "modules" / "pets")
            registry = records.build_registry(startup.prepare(self.data, self.tmp / "modules").loaded)
            pets, _ = helpers.issue(self.conn, self.data, "Pets helper", "suggest", ["pets"])
            self.assertNotIn("unmatched_product_line", helper_guide.guide_text(self.conn, registry, pets))


class UnmatchedLineTests(ReceiptTestCase):
    """Item 83 and the checks in workbench/drafts/receipt_entry/UNMATCHED_LINES.md."""

    def two(self, **hints):
        return self.send([self.bought(self.tomatoes, 3, source="TINNED TOMATOES 400G x3"),
                          self.line(**dict({"receipt_date": DAY, "quantity_hint": "1", "unit_hint": "tin"}, **hints))])

    # check 1
    def test_a_line_waits_in_source_order_and_changes_nothing(self):
        result = self.two()
        self.assertEqual([p.get("kind") for p in result["proposals"]], [None, "unmatched_product_line"])
        self.assertEqual(result["message"], "1 suggestion is ready to check and 1 receipt line needs the household's "
                                            "choice. Nothing has changed yet.")
        self.assertEqual((self.amount(self.tomatoes), self.count("stock__movements")), (1, 0))
        page = self.page()
        self.assertLess(page.index("Add 3 tins of Tinned tomatoes"), page.index("Could not match this receipt line"))
        self.assertIn("Example receipt helper read 2 goods. 1 row is ready to check; 1 line needs your choice. "
                      "Nothing has been added.", page)
        self.assertIn("<bdi>Date on the paper: 20/11/26</bdi> · <bdi>Amount as the helper read it: 1 tin</bdi>", page)
        self.assertIn("No Stock amount will change until you choose an item and confirm the amount.", page)
        self.assertIn(">Choose item</a>", page)
        self.assertIn(">Skip line</button>", page)

    def test_a_line_is_never_a_ref_target_and_is_left_out_of_the_dry_run(self):
        error = self.refused([self.line(), self.bought({"ref": 0})], 422, "invalid")
        self.assertIn("receipt line the helper could not match", error.problems[0]["message"])
        # A ref past a line is counted as the request numbers it.
        result = self.send([self.line(), {"table": "stock__items", "values": {"name": "Oats", "unit": "bags"}},
                            self.bought({"ref": 1}, 2)])
        self.assertEqual(result["proposals"][2]["depends_on"], [1])
        too_many = {"table": "stock__movements", "values": {"item": {"ref": 1}, "reason": "used", "amount": 5}}
        self.conn.execute("DELETE FROM core__proposals")
        self.conn.commit()
        error = self.refused([self.line(), {"table": "stock__items", "values": {"name": "Oats2", "unit": "bags"}},
                              self.bought({"ref": 1}, 2), too_many], 422, "invalid", key="r2")
        self.assertEqual(error.problems[0]["entry"], 3)

    # check 2
    def test_a_bad_line_refuses_the_whole_request(self):
        cases = [({"kind": "unmatched_product_line"}, 400, "bad_request"),
                 ({"kind": "unmatched_product_line", "source": {"price": "1.50"}}, 400, "bad_request"),
                 (self.line("x" * 201), 400, "bad_request"),
                 (self.line("dph_abcdefgh12345678"), 400, "looks_like_a_key"),
                 (self.line("TOM‮SPECIAL"), 400, "hidden_characters"),
                 (dict(self.line(), table="stock__movements"), 400, "bad_request"),
                 (dict(self.line(), values={}), 400, "bad_request"),
                 (dict(self.line(), guess=5), 400, "bad_request"),
                 (dict(self.line(), kind="other"), 400, "bad_request"),
                 (self.line(receipt_date="2026-02-30"), 400, "bad_request"),
                 (self.line(quantity_hint="-1"), 400, "bad_request"),
                 (self.line(quantity_hint="lots"), 400, "bad_request"),
                 (self.line(quantity_hint=2), 400, "bad_request"),
                 (self.line(unit_hint="x" * 31), 400, "bad_request")]
        for entry, status, code in cases:
            with self.subTest(entry=entry):
                self.refused([self.bought(self.beans), entry], status, code)
        self.assertEqual(self.count("stock__movements"), 0)

    # check 3
    def test_only_a_helper_that_may_suggest_into_stock_can_send_one(self):
        looker, _ = helpers.issue(self.conn, self.data, "Look only helper", "read", ["stock"])
        self.refused([self.line()], 403, "look_only", helper=looker)
        shutil.copytree(ROOT / "modules" / "pets", self.tmp / "modules" / "pets")
        report = startup.prepare(self.data, self.tmp / "modules")
        self.registry = records.build_registry(report.loaded)
        pets_only, _ = helpers.issue(self.conn, self.data, "Pets helper", "suggest", ["pets"])
        self.refused([self.line()], 404, "not_found", helper=pets_only)
        result = self.two()
        helpers.turn_off(self.conn, self.data, self.helper.id)
        self.assertIn("TOM SPECIAL 400G", self.page())  # its earlier lines still wait for the person
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals WHERE id = ?",
                                           (self.line_id(result),)).fetchone()[0], "pending")

    # check 4
    def test_a_retry_gives_the_same_line_and_a_changed_hint_is_refused(self):
        first = self.two()
        self.assertEqual(self.two(), first)
        self.assertEqual(self.count("core__proposals"), 2)
        with self.assertRaises(ProposalError) as caught:
            self.two(quantity_hint="2")
        self.assertEqual(caught.exception.code, "request_key_reused")
        plain = [("stock__movements", {"item": 1})]
        self.assertEqual(proposals._body_hash("why", plain), proposals._body_hash("why", plain, [None], None))

    # check 5
    def test_the_line_is_escaped_and_shown_as_the_helpers_words(self):
        self.send([self.line("<b>TOM</b> SPECIAL")])
        page = self.page()
        self.assertIn("&lt;b&gt;TOM&lt;/b&gt; SPECIAL", page)
        self.assertNotIn("<b>TOM", page)
        self.assertIn("As Example receipt helper read it; shown for checking only, not saved in your records.", page)

    # check 6
    def test_choose_an_existing_item_adds_one_stock_in_once(self):
        result = self.two()
        line = self.line_id(result)
        pick = self.page(f"/review/line/{line}")
        self.assertIn("What did this line add to your Stock?", pick)
        self.assertIn("Tinned tomatoes (in tins)", pick)
        form = self.page(f"/review/line/{line}?item={self.tomatoes}")
        self.assertIn('name="amount" value="1"', form)
        self.assertIn('name="when" value="20/11/26"', form)
        revision = re.search(r'name="revision" value="(\d+)"', form).group(1)
        fields = {"item": self.tomatoes, "revision": revision, "amount": "1", "when": "20/11/26"}
        page = self.follow(f"/review/line/{line}/save", fields)
        self.assertIn("Added 1 tin of Tinned tomatoes on 20/11/26 from this line. Review the remaining lines.", page)
        self.assertEqual((self.amount(self.tomatoes), self.count("stock__movements")), (2, 1))
        self.assertIn("Receipt line: added", page)
        self.assertIn("Tinned tomatoes now has 2 tins.", page)
        # Pressed again, or refreshed: nothing more.
        again = self.follow(f"/review/line/{line}/save", fields)
        self.assertIn("This receipt line was already decided. Nothing more was added.", again)
        self.assertEqual(self.count("stock__movements"), 1)
        movement = self.conn.execute("SELECT * FROM stock__movements").fetchone()
        self.assertEqual((movement["source"], movement["reason"], movement["happened_on"]), ("person", "bought", DAY))
        for table in ("stock__items", "stock__movements", "stock__lots"):
            text = json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {table}")])
            self.assertNotIn("TOM SPECIAL", text, table)
            self.assertNotIn("1.50", text, table)

    # check 7
    def test_make_a_new_item_adds_it_and_its_stock_in_together_or_neither(self):
        result = self.send([self.line(quantity_hint="2")])
        line = self.line_id(result)
        form = self.page(f"/review/line/{line}?new=1")
        self.assertIn('name="name"', form)
        self.assertIn('name="category"', form)
        bad = self.post(f"/review/line/{line}/save", {"new": "1", "name": "Special tomatoes", "category": "pantry",
                                                       "unit": "tins", "amount": "0", "when": "20/11/26"})
        self.assertEqual(bad.status_code, 400)
        self.assertIn("as a number above 0", bad.get_data(as_text=True))
        bad = self.post(f"/review/line/{line}/save", {"new": "1", "name": "Special tomatoes", "category": "pantry",
                                                       "unit": "tins", "amount": "2", "when": "31/02/26"})
        self.assertEqual(bad.status_code, 400)
        bad = self.post(f"/review/line/{line}/save", {"new": "1", "name": "", "category": "pantry",
                                                       "unit": "tins", "amount": "2", "when": "20/11/26"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual((self.count("stock__items"), self.count("stock__movements")), (3, 0))
        page = self.follow(f"/review/line/{line}/save", {"new": "1", "name": "Special tomatoes", "category": "pantry",
                                                          "unit": "tins", "amount": "2", "when": "20/11/26"})
        self.assertIn("Added 2 tins of Special tomatoes", page)
        made = self.conn.execute("SELECT id, quantity, source FROM stock__items WHERE name = 'Special tomatoes'").fetchone()
        self.assertEqual((made["quantity"], made["source"]), (2, "person"))

    # check 8
    def test_a_hint_in_another_unit_is_never_converted(self):
        result = self.send([self.line("RICE 0.820 KG", quantity_hint="12", unit_hint="PK")])
        form = self.page(f"/review/line/{self.line_id(result)}?item={self.rice}")
        self.assertIn('name="amount" value=""', form)
        self.assertIn("The helper read the amount as 12 PK, but Rice is counted in kg.", form)
        self.assertEqual(self.count("stock__movements"), 0)
        self.assertTrue(receipts.units_fit("tin", "tins"))
        self.assertFalse(receipts.units_fit("12PK", "tins"))

    # check 9
    def test_skip_undo_skip_and_finish(self):
        result = self.two()
        line = self.line_id(result)
        self.follow(f"/review/{result['proposals'][0]['id']}/accept")
        page = self.follow(f"/review/line/{line}/skip")
        self.assertIn("Skipped this line. No Stock amount changed.", page)
        self.assertIn("Receipt line: skipped", page)
        self.assertIn("1 row added; 1 line skipped. No Stock was added for the skipped line.", page)
        page = self.follow(f"/review/line/{line}/undo-skip")
        self.assertIn("This line is waiting again. Nothing was added.", page)
        self.assertEqual(self.count("stock__movements"), 1)
        self.follow(f"/review/line/{line}/skip")
        page = self.follow(f"/review/batch/{result['batch_id']}/finish")
        self.assertIn("Finished this receipt: 1 row added; 1 line skipped.", page)
        self.assertNotIn("TOM SPECIAL", page)
        with self.assertRaises(PlainError):
            receipts.undo_skip(self.conn, line)
        self.assertEqual(self.count("stock__movements"), 1)
        actions = [r[0] for r in self.conn.execute("SELECT action FROM core__audit WHERE table_name IN "
                                                   "('core__proposals', 'core__helper_batches') ORDER BY id")]
        self.assertEqual(actions[-4:], ["line_skip", "line_unskip", "line_skip", "receipt_finish"])

    def test_finish_waits_until_every_line_is_decided(self):
        result = self.two()
        self.assertNotIn("Finish receipt review", self.page())
        with self.assertRaises(PlainError):
            receipts.finish(self.conn, result["batch_id"])

    # check 10
    def test_totals_tax_and_payments_are_not_goods(self):
        for text in ("TOTAL 12.40", "Subtotal 11.00", "GST included 1.13", "EFTPOS PURCHASE", "Coupon -1.00",
                     "REFUND 2.00", "Change 0.60"):
            with self.subTest(text=text):
                self.refused([self.line(text)], 400, "bad_request")
        self.assertFalse(receipts.not_a_good("TOTALLY NUTS 200G"))

    # check 11
    def test_a_changed_item_refuses_the_save_and_adds_nothing(self):
        result = self.two()
        line = self.line_id(result)
        form = self.page(f"/review/line/{line}?item={self.tomatoes}")
        revision = re.search(r'name="revision" value="(\d+)"', form).group(1)
        self.store.create("stock__movements", {"item": self.tomatoes, "reason": "used", "amount": 1})
        response = self.post(f"/review/line/{line}/save", {"item": self.tomatoes, "revision": revision,
                                                            "amount": "1", "when": "20/11/26"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("This Stock item changed while you were checking the line. Check its current amount and try "
                      "again. Nothing was added.", response.get_data(as_text=True))
        self.assertEqual((self.amount(self.tomatoes), self.count("stock__movements")), (0, 1))
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals WHERE id = ?", (line,)).fetchone()[0],
                         "pending")

    # check 12
    def test_accept_all_takes_only_ready_rows_and_reject_all_skips_no_line(self):
        result = self.send([self.bought(self.tomatoes, 3), self.bought(self.beans, 2), self.line()])
        page = self.page()
        self.assertIn("Accept 2 ready rows; 1 line still needs your choice", page)
        self.assertIn("The 1 receipt line that needs your choice stays waiting; nothing is added for it.", page)
        page = self.follow(f"/review/batch/{result['batch_id']}/accept-all")
        self.assertIn("Added 2 to Stock in and out.", page)
        self.assertIn("Could not match this receipt line", page)
        other = self.send([self.bought(self.beans, 1), self.line("SECOND LINE")], key="receipt-2")
        proposals.reject_batch(self.conn, other["batch_id"])
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals WHERE id = ?",
                                           (self.line_id(other),)).fetchone()[0], "pending")
        self.assertEqual(proposals.accept_ticked(self.conn, self.registry, [self.line_id(other)]), (0, []))
        with self.assertRaises(PlainError):
            proposals.accept(self.conn, self.registry, self.line_id(other))
        with self.assertRaises(PlainError):
            proposals.reject(self.conn, self.line_id(other))

    # check 13
    def test_an_export_has_the_stock_in_but_never_the_line(self):
        result = self.two()
        line = self.line_id(result)
        form = self.page(f"/review/line/{line}?item={self.tomatoes}")
        revision = re.search(r'name="revision" value="(\d+)"', form).group(1)
        self.follow(f"/review/line/{line}/save", {"item": self.tomatoes, "revision": revision, "amount": "1",
                                                  "when": "20/11/26"})
        with zipfile.ZipFile(io.BytesIO(export.build(self.conn, self.registry, "test"))) as packed:
            text = "".join(packed.read(name).decode("utf-8", "replace") for name in packed.namelist())
        self.assertIn("Tinned tomatoes", text)
        self.assertNotIn("TOM SPECIAL", text)
        self.assertNotIn("1.50", text)


class RepeatReceiptTests(ReceiptTestCase):
    """Item 86 and the checks in workbench/drafts/receipt_entry/DUPLICATE_RECEIPT.md."""

    def held(self, result):
        return receipts.held(self.conn, self.registry, result["batch_id"])

    # check 1
    def test_the_same_request_key_is_still_the_safe_retry(self):
        first = self.basket()
        self.assertEqual(self.basket(), first)
        self.assertIsNone(self.held(first))
        self.assertEqual(self.count("core__helper_batches"), 1)

    # check 2
    def test_a_second_copy_waits_with_a_warning_and_adds_nothing(self):
        self.basket()
        second = self.basket(key="receipt-2")
        self.assertTrue(self.held(second))
        page = self.page()
        self.assertIn("This may be the same receipt again. Nothing from this copy has been added.", page)
        self.assertIn("These 3 goods, amounts and purchase date match a receipt put on Review on", page)
        self.assertIn("by Example receipt helper", page)
        self.assertIn("Still waiting: 3 rows.", page)
        self.assertIn(">Reject this copy</button>", page)
        self.assertIn(">Keep this as another purchase</button>", page)
        self.assertIn(f'href="#batch-{second["batch_id"] - 1}">Open earlier receipt', page)
        before = self.amount(self.beans)
        self.assertIn(receipts.HELD, self.follow(f"/review/batch/{second['batch_id']}/accept-all"))
        self.assertIn(receipts.HELD, self.follow(f"/review/{second['proposals'][0]['id']}/accept"))
        added, failed = proposals.accept_ticked(self.conn, self.registry, [second["proposals"][0]["id"]])
        self.assertEqual((added, len(failed)), (0, 1))
        with self.assertRaises(receipts.RepeatHeld):
            proposals.accept(self.conn, self.registry, second["proposals"][1]["id"])
        self.assertEqual(self.amount(self.beans), before)

    def test_a_batch_without_receipt_context_is_never_compared(self):
        self.basket()
        plain = self.send([self.bought(self.beans, 2), self.bought(self.tomatoes, 3), self.bought(self.rice, 1)],
                          key="no-context")
        self.assertIsNone(receipts.possible_repeat(self.conn, self.registry, plain["batch_id"]))
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, plain["batch_id"]), (3, []))

    # check 3
    def test_a_receipt_import_matches_a_helper_receipt(self):
        self.basket()
        rows = [(n + 2, "stock__movements", {"item": item, "reason": "bought", "amount": amount, "happened_on": DAY})
                for n, (item, amount) in enumerate([(self.rice, 1), (self.beans, 2), (self.tomatoes, 3)])]
        batch = proposals.stage_import(self.conn, "shop.csv", rows, receipt={"purchase_date": DAY})
        self.assertTrue(receipts.held(self.conn, self.registry, batch))
        plain = proposals.stage_import(self.conn, "shop.csv", rows)
        self.assertIsNone(receipts.possible_repeat(self.conn, self.registry, plain))

    def test_the_import_page_offers_one_receipt_and_warns_early(self):
        self.basket()
        text = "Item,Amount,Date\r\nKidney beans,2,2026-11-20\r\nTinned tomatoes,3,2026-11-20\r\nRice,1,2026-11-20\r\n"
        page = self.post("/settings/import", {"table": "stock__movements", "file": (io.BytesIO(text.encode()), "a.csv")})
        page = page.get_data(as_text=True)
        found = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', page))
        found.update(match_0="item", match_1="amount", match_2="happened_on")
        checked = self.post("/settings/import/check", found).get_data(as_text=True)
        self.assertIn("These rows are from one receipt", checked)
        self.assertNotIn("data-lookalike", checked)
        checked = self.post("/settings/import/check", dict(found, receipt="1", purchase_date="20/11/26"))
        checked = checked.get_data(as_text=True)
        self.assertIn("These receipt rows look like one put on Review on", checked)
        fields = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', checked))
        fields.update(match_0="item", match_1="amount", match_2="happened_on", receipt="1", purchase_date="")
        refused = self.post("/settings/import/send", fields).get_data(as_text=True)
        self.assertIn("Type the date on the receipt", refused)
        sent = self.post("/settings/import/send", dict(fields, purchase_date="20/11/26"))
        self.assertEqual(sent.status_code, 302)
        batch = self.conn.execute("SELECT id, receipt_json FROM core__helper_batches ORDER BY id DESC").fetchone()
        self.assertEqual(json.loads(batch["receipt_json"]), {"purchase_date": DAY})
        self.assertTrue(receipts.held(self.conn, self.registry, batch["id"]))
        self.assertIn("by Example receipt helper", self.page())

    # check 4
    def test_order_case_spacing_and_price_do_not_hide_a_repeat_and_repeated_lines_count_twice(self):
        self.send([self.bought(self.beans, 2, "KIDNEY BEANS x2"), self.bought(self.tomatoes, 3, "TOMS x3")],
                  key="a", context=CONTEXT)
        moved = self.send([self.bought(self.tomatoes, 3, "toms   X3 $9.99"), self.bought(self.beans, 2, "kidney beans")],
                          key="b", context=CONTEXT)
        self.assertTrue(self.held(moved))
        twice = self.send([self.bought(self.beans, 1), self.bought(self.beans, 1)], key="c", context=CONTEXT)
        once = self.send([self.bought(self.beans, 1)], key="d", context=CONTEXT)
        self.assertTrue(self.held(self.send([self.bought(self.beans, 1), self.bought(self.beans, 1)], key="e",
                                            context=CONTEXT)))
        found = receipts.possible_repeat(self.conn, self.registry, once["batch_id"])
        self.assertNotEqual(found and found["level"], "repeat")  # one line is not the two of "twice"
        self.assertIsNotNone(twice)

    # check 5
    def test_a_changed_amount_a_line_or_a_new_item_is_only_similar(self):
        self.basket()
        cases = {
            "amount": [self.bought(self.beans, 5), self.bought(self.tomatoes, 3), self.bought(self.rice, 1)],
            "line": [self.bought(self.beans, 2), self.bought(self.tomatoes, 3), self.bought(self.rice, 1), self.line()],
            "new item": [self.bought(self.beans, 2), self.bought(self.tomatoes, 3),
                         {"table": "stock__items", "values": {"name": "RICE", "unit": "kg"}}, self.bought({"ref": 2}, 1)],
        }
        for n, (what, entries) in enumerate(cases.items()):
            with self.subTest(what):
                result = self.send(entries, key=f"case-{n}", context=CONTEXT)
                found = receipts.possible_repeat(self.conn, self.registry, result["batch_id"])
                self.assertEqual(found["level"], "similar")
                self.assertIsNone(self.held(result))
        page = self.page()
        self.assertIn("Some lines look like an earlier receipt.", page)
        self.assertIn("Only in this copy: <bdi>5 tins of Kidney beans on 20/11/26</bdi>.", page)
        self.assertIn("Only in the earlier receipt: <bdi>2 tins of Kidney beans on 20/11/26</bdi>.", page)

    # check 6
    def test_keep_expires_when_the_earlier_receipt_changes_and_is_rechecked_under_the_lock(self):
        first = self.basket()
        second = self.basket(key="receipt-2")
        self.follow(f"/review/batch/{second['batch_id']}/keep")
        self.assertIsNone(self.held(second))
        proposals.accept_batch(self.conn, self.registry, first["batch_id"])  # the earlier one changes meanwhile
        self.assertTrue(self.held(second))
        page = self.page()
        self.assertIn("Already added: 3 rows.", page)
        before = self.amount(self.beans)
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, second["batch_id"])[0], 0)
        self.assertEqual(self.amount(self.beans), before)

    def test_the_guard_runs_inside_the_write_transaction(self):
        first = self.basket()
        second = self.basket(key="receipt-2")
        receipts.keep(self.conn, self.registry, second["batch_id"])
        elsewhere = self.store.create("stock__movements", {"item": self.beans, "reason": "bought", "amount": 2})
        real = receipts.guard
        calls = []

        def guard_then_change(conn, registry, batch_id):
            calls.append(conn.in_transaction)
            if conn.in_transaction and len(calls) == 2:  # a second window accepts the first copy just now
                conn.execute("UPDATE core__proposals SET status = 'accepted', record_id = ? WHERE id = ?",
                             (elsewhere, first["proposals"][0]["id"]))
            real(conn, registry, batch_id)

        receipts.guard = guard_then_change
        try:
            added, failed = proposals.accept_batch(self.conn, self.registry, second["batch_id"])
        finally:
            receipts.guard = real
        self.assertEqual(calls[:2], [False, True])
        # The first group saw the change under the lock and added nothing (that window's change was rolled back
        # with it, so the other two groups, checked afterwards, still went in under the person's Keep).
        self.assertEqual((added, failed), (2, [receipts.HELD]))
        self.assertEqual(self.conn.execute("SELECT status FROM core__proposals WHERE id = ?",
                                           (second["proposals"][0]["id"],)).fetchone()[0], "pending")
        self.assertEqual(self.amount(self.beans), 15)  # only the Stock in made elsewhere, not this copy's

    # check 7
    def test_keep_as_another_purchase_lets_it_be_accepted_and_a_third_warns_again(self):
        first = self.basket()
        proposals.accept_batch(self.conn, self.registry, first["batch_id"])
        second = self.basket(key="receipt-2")
        page = self.follow(f"/review/batch/{second['batch_id']}/keep")
        self.assertIn("Treat this as a separate purchase. Check each row before accepting.", page)
        self.assertIn("You chose to keep this as another purchase", page)
        self.assertEqual(proposals.accept_batch(self.conn, self.registry, second["batch_id"]), (3, []))
        self.assertEqual(self.amount(self.beans), 17)
        third = self.basket(key="receipt-3")
        self.assertTrue(self.held(third))
        self.assertEqual(self.conn.execute("SELECT action FROM core__audit WHERE action = 'receipt_keep'").fetchone()[0],
                         "receipt_keep")

    def test_open_earlier_receipt_shows_what_became_of_each_row(self):
        first = self.basket()
        proposals.accept_batch(self.conn, self.registry, first["batch_id"])
        self.store.delete("stock__movements", self.conn.execute(
            "SELECT record_id FROM core__proposals WHERE id = ?", (first["proposals"][2]["id"],)).fetchone()[0])
        second = self.basket(key="receipt-2")
        page = self.page()
        self.assertIn(f'href="/review/batch/{first["batch_id"]}">Open earlier receipt', page)
        earlier = self.page(f"/review/batch/{first['batch_id']}")
        self.assertIn("Earlier receipt", earlier)
        self.assertIn("Add 2 tins of Kidney beans on 20/11/26", earlier)
        self.assertEqual(earlier.count("<bdi>Added.</bdi>"), 2)
        self.assertIn("Added, then undone: it has since been deleted.", earlier)
        self.assertEqual(self.client.get(f"/review/batch/{second['batch_id'] + 9}", base_url=BASE).status_code, 302)

    # check 8
    def test_reject_this_copy_leaves_the_earlier_receipt_alone(self):
        first = self.basket()
        proposals.accept_batch(self.conn, self.registry, first["batch_id"])
        second = self.send([self.bought(self.beans, 2), self.bought(self.tomatoes, 3), self.bought(self.rice, 1)],
                           key="receipt-2", context=CONTEXT)
        page = self.follow(f"/review/batch/{second['batch_id']}/reject-copy")
        self.assertIn("Rejected this copy. No Stock amount changed from it.", page)
        self.assertEqual(self.amount(self.beans), 15)
        statuses = [r[0] for r in self.conn.execute("SELECT status FROM core__proposals ORDER BY batch_id, position")]
        self.assertEqual(statuses, ["accepted"] * 3 + ["rejected"] * 3)

    # check 9
    def test_a_partly_added_earlier_receipt_says_so(self):
        first = self.basket()
        proposals.accept(self.conn, self.registry, first["proposals"][0]["id"])
        self.basket(key="receipt-2")
        self.assertIn("Partly added: 1 of 3 rows. 2 still waiting.", self.page())

    # check 10
    def test_an_undone_earlier_receipt_is_not_an_active_repeat(self):
        first = self.basket()
        proposals.accept_batch(self.conn, self.registry, first["batch_id"])
        made = [r[0] for r in self.conn.execute("SELECT record_id FROM core__proposals ORDER BY position")]
        self.store.delete("stock__movements", made[0])
        second = self.basket(key="receipt-2")
        self.assertIn("Partly added: 2 of 3 rows. 1 was undone.", self.page())
        for record_id in made[1:]:
            self.store.delete("stock__movements", record_id)
        found = receipts.possible_repeat(self.conn, self.registry, second["batch_id"])
        self.assertEqual(found["level"], "undone")
        self.assertIsNone(self.held(second))
        self.assertIn("Earlier receipt was undone: none of its Stock in rows remain.", self.page())

    # check 12
    def test_a_card_number_is_refused_and_nothing_raw_is_kept(self):
        for text in ("CARD 4111 1111 1111 1111", "4111-1111-1111-1111", "378282246310005"):
            with self.subTest(text=text):
                self.refused([self.bought(self.beans, source=text)], 400, "payment_detail")
        self.assertFalse(receipts.looks_like_a_card("BARCODE 9300000000001"))  # 13 digits: a barcode
        self.assertFalse(receipts.looks_like_a_card("4111 1111 1111 1112"))  # fails the check digit
        self.refused([self.bought(self.beans)], 400, "payment_detail",
                     context={"purchase_date": DAY, "shop_label": "Shop 4111111111111111"})
        first = self.basket()
        second = self.basket(key="receipt-2")
        receipts.keep(self.conn, self.registry, second["batch_id"])
        kept = self.conn.execute("SELECT receipt_json, repeat_ok_json FROM core__helper_batches WHERE id = ?",
                                 (second["batch_id"],)).fetchone()
        self.assertEqual(json.loads(kept["receipt_json"]), CONTEXT)
        self.assertEqual(set(json.loads(kept["repeat_ok_json"])), {"earlier", "earlier_rows", "undone", "rows"})
        self.assertNotIn("Kidney", kept["repeat_ok_json"])
        self.assertIsNotNone(first)

    # check 14
    def test_many_earlier_receipts_and_a_long_candidate_stay_quick(self):
        entries = [self.bought(self.beans, n + 1) for n in range(50)]
        proposals.allow_more(self.conn, self.helper.id)  # 301 suggestions today: the household allowed more
        for n in range(201):
            self.send([self.bought(self.tomatoes, n + 1)], key=f"old-{n}", context=CONTEXT)
        self.send(entries, key="long-1", context=CONTEXT)
        started = time.monotonic()
        second = self.send(entries, key="long-2", context=CONTEXT)
        self.assertTrue(self.held(second))
        self.assertLess(time.monotonic() - started, 10)
        with self.assertRaises(ProposalError):
            self.send(entries + [self.bought(self.beans)], key="too-long", context=CONTEXT)

    def test_receipt_context_is_checked(self):
        for context in ({}, {"purchase_date": "20/11/26"}, {"purchase_date": DAY, "shop_label": "x" * 81},
                        {"purchase_date": DAY, "card": "1"}, "2026-11-20"):
            with self.subTest(context=context):
                self.refused([self.bought(self.beans)], 400, "bad_request", context=context)
