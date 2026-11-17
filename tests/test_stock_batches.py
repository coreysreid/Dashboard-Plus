"""Tests for batches: layered use-by dates in Household stock (decision 0053, DESIGN.md 5.7).

They follow Lane B's acceptance checks (workbench/drafts/stock_lots/ACCEPTANCE.md): 3 tins of
kidney beans at Kitchen › Pantry › Shelf 3 use by next month, 10 in the garage in six months."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5131
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date.today()


def day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


class BatchTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.records = records.Records(self.conn, self.registry)
        place = lambda name, inside=None: self.records.create("stock__places", {"name": name, "inside": inside})  # noqa: E731
        self.shelf = place("Shelf 3", place("Pantry", place("Kitchen")))
        self.garage = place("Grey shelves", place("Garage"))

    def beans(self):
        """Kidney beans: 3 tins on Shelf 3 use by next month, then 10 bought for the garage."""
        item = self.records.create("stock__items", {"name": "Kidney beans", "unit": "tins", "minimum": 6,
                                                    "quantity": 3, "place": self.shelf, "expires": day(30)})
        self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 10,
                                                 "expires": day(180), "place": self.garage})
        return item

    def batches(self, item):
        return [(r["quantity"], r["expires"], r["place"]) for r in self.conn.execute(
            "SELECT * FROM stock__lots WHERE item = ? AND deleted_at IS NULL ORDER BY id", (item,))]

    def amount(self, item):
        return self.records.get("stock__items", item)["quantity"]

    def test_an_item_added_with_an_amount_starts_its_first_batch(self):
        item = self.records.create("stock__items", {"name": "Kidney beans", "unit": "tins", "quantity": 5,
                                                    "place": self.shelf, "expires": day(30)})
        self.assertEqual(self.batches(item), [(5, day(30), self.shelf)])
        self.assertEqual(self.amount(item), 5)
        self.assertEqual(self.records.get("stock__items", item)["expires"], day(30))

    def test_stock_in_starts_a_new_batch_and_the_item_adds_them_up(self):  # check 2
        item = self.beans()
        self.assertEqual(self.batches(item), [(3, day(30), self.shelf), (10, day(180), self.garage)])
        self.assertEqual(self.amount(item), 13)
        self.assertEqual(self.records.get("stock__items", item)["expires"], day(30))  # the earliest

    def test_using_some_takes_from_the_earliest_use_by_first(self):  # check 3
        item = self.beans()
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 2})
        self.assertEqual([b[0] for b in self.batches(item)], [1, 10])
        self.assertEqual(self.amount(item), 11)

    def test_an_undated_batch_is_not_used_before_a_dated_one(self):  # check 3
        item = self.records.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})  # no date
        self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 1,
                                                 "expires": day(60)})
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 1})
        self.assertEqual([b[0] for b in self.batches(item)], [2, 0])

    def test_using_more_than_the_first_batch_asks_to_go_batch_by_batch(self):  # check 3
        item = self.beans()
        with self.assertRaises(records.ValidationError) as caught:
            self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 5})
        self.assertIn("more than the batch to use first holds (3", caught.exception.problems["amount"])
        with self.assertRaises(records.ValidationError) as caught:
            self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 20})
        self.assertIn("only 13 left", caught.exception.problems["amount"])
        self.assertEqual(self.amount(item), 13)  # nothing changed

    def test_a_chosen_batch_must_be_the_items_own(self):
        beans = self.beans()
        rice = self.records.create("stock__items", {"name": "Rice", "quantity": 2})
        rice_batch = self.conn.execute("SELECT id FROM stock__lots WHERE item = ?", (rice,)).fetchone()[0]
        with self.assertRaises(records.ValidationError) as caught:
            self.records.create("stock__movements", {"item": beans, "reason": "used", "amount": 1,
                                                     "lot": rice_batch})
        self.assertIn("different item", caught.exception.problems["lot"])

    def test_throwing_out_an_expired_batch_keeps_its_history_and_stops_the_warning(self):  # check 5
        item = self.beans()
        may = self.conn.execute("SELECT id FROM stock__lots WHERE item = ? ORDER BY id", (item,)).fetchone()[0]
        self.records.create("stock__movements", {"item": item, "reason": "expired", "amount": 3, "lot": may})
        self.assertEqual(self.amount(item), 10)
        self.assertEqual(self.records.get("stock__lots", may)["quantity"], 0)  # still there, as history
        self.assertEqual(watch.expiring(self.conn, self.registry, TODAY), [])

    def test_needs_attention_speaks_about_each_batch(self):  # check 6
        item = self.beans()
        found = watch.expiring(self.conn, self.registry, TODAY)
        self.assertEqual([(i.table, i.name) for i in found],
                         [("stock__lots", "Kidney beans, 3 tins at Kitchen › Pantry › Shelf 3")])
        self.assertIn("(in 30 days)", found[0].detail)
        self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 2, "expires": day(10)})
        self.assertEqual([i.name for i in watch.expiring(self.conn, self.registry, TODAY)],
                         ["Kidney beans, 2 tins", "Kidney beans, 3 tins at Kitchen › Pantry › Shelf 3"])

    def test_running_low_compares_the_total_with_keep_at_least(self):  # check 6
        item = self.beans()
        self.assertEqual(watch.running_low(self.conn, self.registry), [])
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 3})
        garage = self.conn.execute("SELECT id FROM stock__lots WHERE item = ? ORDER BY id DESC", (item,)).fetchone()[0]
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 5, "lot": garage})
        self.assertEqual([i.name for i in watch.running_low(self.conn, self.registry)], ["Kidney beans"])

    def test_a_stocktake_changes_the_batch_and_the_item_follows(self):  # check 1
        item = self.beans()
        may = self.conn.execute("SELECT id FROM stock__lots WHERE item = ? ORDER BY id", (item,)).fetchone()[0]
        self.records.update("stock__lots", may, {"quantity": 5})
        self.assertEqual(self.amount(item), 15)
        changes = [h for h in self.records.history("stock__items", item) if h["action"] == "update"]
        self.assertEqual(changes[-1]["after"], {"quantity": 15})

    def test_the_items_own_amount_cannot_be_typed_over(self):
        item = self.beans()
        with self.assertRaises(records.ValidationError) as caught:
            self.records.update("stock__items", item, {"quantity": 99})
        self.assertIn("worked out from its batches", caught.exception.problems["quantity"])

    def test_deleting_and_restoring_keep_the_counts_right(self):
        item = self.beans()
        used = self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 2})
        self.records.delete("stock__movements", used)
        self.assertEqual(self.amount(item), 13)
        garage = self.conn.execute("SELECT id FROM stock__lots WHERE item = ? ORDER BY id DESC", (item,)).fetchone()[0]
        self.records.delete("stock__lots", garage)
        self.assertEqual(self.amount(item), 3)
        self.records.restore("stock__lots", garage)
        self.assertEqual(self.amount(item), 13)
        self.records.delete("stock__items", item)
        self.records.restore("stock__items", item)
        self.assertEqual(self.amount(item), 13)
        self.assertEqual([b[0] for b in self.batches(item)], [3, 10])

    def test_deleting_a_batch_then_its_stock_in_and_restoring_both_counts_once(self):
        """Independent review finding 3: restore order must not add the same stock twice."""
        item = self.records.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        bought = self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 5})
        batch = self.records.get("stock__movements", bought)["lot"]
        self.records.delete("stock__lots", batch)
        self.records.delete("stock__movements", bought)
        self.records.restore("stock__lots", batch)
        self.records.restore("stock__movements", bought)
        self.assertEqual(self.records.get("stock__lots", batch)["quantity"], 5)
        self.assertEqual(self.amount(item), 7)

    def test_a_batch_with_stock_in_or_out_cannot_move_to_another_item(self):
        """Independent review finding 4: its stock in and out would be stranded on the old item."""
        beans = self.beans()
        rice = self.records.create("stock__items", {"name": "Rice", "quantity": 2})
        garage = self.conn.execute("SELECT id FROM stock__lots WHERE item = ? ORDER BY id DESC", (beans,)).fetchone()[0]
        with self.assertRaises(records.ValidationError) as caught:
            self.records.update("stock__lots", garage, {"item": rice})
        self.assertIn("can't change once stock in or out is recorded", caught.exception.problems["item"])

    def test_a_batch_started_by_stock_in_waiting_for_review_waits_too(self):
        """Independent review finding 6."""
        item = self.records.create("stock__items", {"name": "Rice", "quantity": 2})
        bought = self.records.create("stock__movements", {"item": item, "reason": "bought", "amount": 5},
                                     review_status="needs_review")
        batch = self.records.get("stock__movements", bought)["lot"]
        self.assertEqual(self.records.get("stock__lots", batch)["review_status"], "needs_review")

    def test_a_private_column_cannot_name_a_batch(self):
        """Independent review finding 5: a batch's name shows on lists, pickers and sheets."""
        from dashboard.core import modules
        folder = self.tmp / "modules" / "stock"
        text = (folder / "tables.toml").read_text(encoding="utf-8")
        text = text.replace('columns.notes = { type = "longtext" }',
                            'columns.notes = { type = "longtext" }\ncolumns.secret = { type = "text", sensitive = true }', 1)
        text = text.replace('record_name = "{item}', 'record_name = "{item.secret} {item}')
        (folder / "tables.toml").write_text(text, encoding="utf-8")
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        self.assertIn("is private", " ".join(caught.exception.problems))

    def test_pages_show_batches_and_the_sheet_lists_them(self):
        item = self.beans()
        self.records.create("stock__movements", {"item": item, "reason": "used", "amount": 3})  # May used up
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", "Australia")
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        page = client.get(f"/t/stock__items/{item}", base_url=BASE).get_data(as_text=True)
        november = date.fromisoformat(day(180)).strftime("%d/%m/%y")
        self.assertIn(f"Kidney beans, 10 tins at Garage › Grey shelves, use by {november}", page)
        self.assertNotIn('name="quantity"', page)  # the amount comes from the batches once added
        self.assertIn("Amount on hand: 10 tins, in 1 batch", page)
        sheet = client.get("/sheet/stock/supplies", base_url=BASE).get_data(as_text=True)
        self.assertIn("Garage › Grey shelves", sheet)
        self.assertNotIn("Kitchen › Pantry › Shelf 3", sheet)  # a used-up batch is not printed
        new_form = client.get("/t/stock__items/new", base_url=BASE).get_data(as_text=True)
        self.assertIn('name="quantity"', new_form)  # the first batch is typed in with the item

    def client(self):
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", "Australia")
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def lot_ids(self, item):
        return [r[0] for r in self.conn.execute("SELECT id FROM stock__lots WHERE item = ? ORDER BY id", (item,))]

    def test_which_batch_knows_each_batchs_item_and_says_what_blank_does(self):  # decision 0057
        beans = self.beans()
        rice = self.records.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        client = self.client()
        page = client.get(f"/t/stock__movements/new?item={beans}", base_url=BASE).get_data(as_text=True)
        self.assertIn('<select id="f-lot" name="lot" aria-describedby="f-lot-help" data-follows="item">', page)
        for lot in self.lot_ids(beans):
            self.assertIn(f'<option value="{lot}" data-owner="{beans}"', page)
        self.assertIn(f'<option value="{self.lot_ids(rice)[0]}" data-owner="{rice}"', page)
        # Leaving it blank is said in plain words, for the reason already chosen and for every other.
        lot_box = page.split('<select id="f-lot"')[1].split("</select>")[0]
        self.assertNotIn("(none)", lot_box)
        self.assertIn(">Start a new batch</option>", lot_box)
        self.assertIn('data-blank-follows="reason"', lot_box)
        self.assertIn("&#34;used&#34;: &#34;Use the batch with the earliest use-by date&#34;", lot_box)
        self.assertIn("&#34;bought&#34;: &#34;Start a new batch&#34;", lot_box)
        # "Use by" and "Where you put it" are for a new batch only: they go away once a batch is chosen.
        self.assertIn('data-show-when="reason" data-show-value="bought" data-only-when-blank="lot"', page)
        self.assertEqual(page.count('data-only-when-blank="lot"'), 2)
        # Other forms are as they were.
        item_form = client.get("/t/stock__items/new", base_url=BASE).get_data(as_text=True)
        self.assertNotIn("data-follows=", item_form)
        self.assertNotIn("data-blank-follows=", item_form)
        self.assertIn("(none)", item_form)

    def test_blank_words_come_from_the_rule_and_follow_the_reason(self):
        from dashboard.web import display
        beans = self.beans()
        info = self.registry["stock__movements"]
        fields = {f.name: f for f in display.build_fields(
            self.records, info, {"item": beans, "reason": "used"}, {}, False)}
        self.assertEqual(fields["lot"].blank, "Use the batch with the earliest use-by date")
        self.assertEqual(fields["lot"].follows, "item")
        self.assertEqual(set(fields["lot"].blank_words), {"bought", "used", "expired", "thrown_away", "given_away"})
        self.assertEqual(fields["expires"].only_when_blank, "lot")
        self.assertEqual(fields["place"].only_when_blank, "lot")
        self.assertIsNone(fields["item"].follows)
        # Without the module's own words, the core's are worked out from the batch's date column.
        del info.module.labels["tables"]["movements"]["columns"]["lot"]["blank"]
        fields = {f.name: f for f in display.build_fields(
            self.records, info, {"item": beans, "reason": "used"}, {}, False)}
        self.assertEqual(fields["lot"].blank, "Use the batch with the earliest use by date")
        # A saved record keeps its batch when the box is left blank, and the form says so.
        movement = self.records.create("stock__movements", {"item": beans, "reason": "used", "amount": 1})
        saved = self.records.get("stock__movements", movement)
        fields = {f.name: f for f in display.build_fields(self.records, info, saved, {}, False, editing=True)}
        self.assertEqual(fields["lot"].blank, "Keep the batch it has")

    def test_without_scripts_a_batch_of_another_item_is_still_refused(self):  # the server is the safeguard
        beans = self.beans()
        rice = self.records.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        client = self.client()
        form = client.get(f"/t/stock__movements/new?item={beans}", base_url=BASE).get_data(as_text=True)
        token = form.split('name="_csrf" value="')[1].split('"')[0]
        sent = {"_csrf": token, "item": str(beans), "reason": "used", "amount": "1",
                "happened_on": TODAY.strftime("%d/%m/%y"), "lot": str(self.lot_ids(rice)[0]), "then": "done"}
        reply = client.post("/t/stock__movements/new", data=sent, base_url=BASE)
        page = reply.get_data(as_text=True)
        self.assertEqual(reply.status_code, 422)
        self.assertIn("Which batch is a batch of a different item. Choose one of this item&#39;s batches, "
                      "or leave it blank.", page)
        self.assertIn(f'<option value="{self.lot_ids(rice)[0]}" data-owner="{rice}" selected>', page)
        self.assertEqual(self.amount(beans), 13)
        self.assertEqual(self.amount(rice), 2)
        sent["lot"] = str(self.lot_ids(beans)[1])  # one of its own batches is taken
        self.assertEqual(client.post("/t/stock__movements/new", data=sent, base_url=BASE).status_code, 302)
        self.assertEqual(self.batches(beans)[1][0], 9)

    def test_blank_words_in_labels_are_checked(self):
        from dashboard.core import modules
        folder = self.tmp / "modules" / "stock"
        labels = (folder / "labels.toml").read_text(encoding="utf-8")
        (folder / "labels.toml").write_text(
            labels + '\ncolumns.notes = { blank = { takes = "Use the oldest" } }\n', encoding="utf-8")
        with self.assertRaises(modules.ModuleError) as caught:
            modules.load_module(folder)
        self.assertIn("blank only applies to the batch link", " ".join(caught.exception.problems))


class UpgradeTests(TempDirTestCase):
    """Check 12: items recorded before batches each become one batch, with nothing lost or counted twice."""

    def test_existing_items_become_one_batch_each(self):
        modules_dir = self.tmp / "modules"
        shutil.copytree(ROOT / "modules" / "stock", modules_dir / "stock")
        newest = modules_dir / "stock" / "migrations" / "0005_batches.sql"
        held_back = newest.read_text(encoding="utf-8")
        newest.unlink()  # start as a household did before this update
        data = self.tmp / "data"
        startup.prepare(data, modules_dir)
        conn = db.connect(data / "dashboard.db")
        stamp = "2026-11-01T09:00:00+00:00"
        conn.execute("INSERT INTO stock__places (id, name, created_at, updated_at) VALUES (1, 'Shelf 3', ?, ?)",
                     (stamp, stamp))
        rows = [(1, "Kidney beans", 5, "2027-05-20", 1, None), (2, "Rice", 0, "2027-01-01", None, None),
                (3, "Torch", None, None, None, None), (4, "Old soup", 2, None, None, stamp)]
        for rid, name, quantity, expires, place, deleted in rows:
            conn.execute("INSERT INTO stock__items (id, name, category, quantity, expires, place, deleted_at, "
                         "created_at, updated_at) VALUES (?, ?, 'pantry', ?, ?, ?, ?, ?, ?)",
                         (rid, name, quantity, expires, place, deleted, stamp, stamp))
        conn.execute("INSERT INTO stock__movements (item, reason, amount, happened_on, created_at, updated_at) "
                     "VALUES (1, 'bought', 5, '2026-10-01', ?, ?)", (stamp, stamp))
        conn.commit()
        conn.close()

        newest.write_text(held_back, encoding="utf-8")
        report = startup.prepare(data, modules_dir)
        self.assertEqual(report.module_problems, {})
        self.assertTrue(list((data / "backups").glob("*before-update*")), "a backup is made before the change")
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        batches = [tuple(r) for r in conn.execute(
            "SELECT item, quantity, expires, place, deleted_at IS NOT NULL FROM stock__lots ORDER BY item")]
        self.assertEqual(batches, [(1, 5, "2027-05-20", 1, 0), (2, 0, "2027-01-01", None, 0), (4, 2, None, None, 1)])
        self.assertEqual(conn.execute("SELECT lot FROM stock__movements").fetchone()[0],
                         conn.execute("SELECT id FROM stock__lots WHERE item = 1").fetchone()[0])
        self.assertEqual(conn.execute("SELECT quantity FROM stock__items WHERE id = 1").fetchone()[0], 5)
        self.assertIsNone(conn.execute("SELECT expires FROM stock__items WHERE id = 2").fetchone()[0])
        registry = records.build_registry(report.loaded)
        store = records.Records(conn, registry)
        store.create("stock__movements", {"item": 1, "reason": "used", "amount": 2})  # the old item works on
        self.assertEqual(store.get("stock__items", 1)["quantity"], 3)
        expiring = watch.expiring(conn, registry, date(2027, 5, 1))
        self.assertEqual([i.name for i in expiring], ["Kidney beans, 3 at Shelf 3"])
        # Independent review finding 2: the item's old place no longer holds the place.
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM stock__items WHERE place IS NOT NULL").fetchone()[0], 0)
        # Independent review finding 1: an item deleted before the update comes back with its stock.
        store.restore("stock__items", 4)
        self.assertEqual(store.get("stock__items", 4)["quantity"], 2)
        self.assertEqual(conn.execute("SELECT quantity FROM stock__lots WHERE item = 4 AND deleted_at IS NULL")
                         .fetchone()[0], 2)
        store.create("stock__movements", {"item": 4, "reason": "used", "amount": 1})
        self.assertEqual(store.get("stock__items", 4)["quantity"], 1)
