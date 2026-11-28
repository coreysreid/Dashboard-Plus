"""Tests for stocktake corrections: "Count this batch" saves one correction, never the count on top (decision 0070).

They follow Lane B's acceptance checks (workbench/drafts/stocktake_corrections/ACCEPTANCE.md, on its
branch): made-up Kidney beans, 3 tins at Kitchen › Pantry › Shelf 3 and 10 in the garage, 13 in all."""
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase, freeze_today
from dashboard.core import db, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5132
BASE = f"http://127.0.0.1:{PORT}"
TODAY = date.today()


def day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


class StocktakeTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        freeze_today(self, TODAY)  # TODAY was read when this file loaded; the app must agree with it
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
        self.garage = place("Garage shelves", place("Garage"))
        self.item = self.records.create("stock__items", {"name": "Kidney beans", "unit": "tins", "minimum": 6,
                                                         "quantity": 3, "place": self.shelf, "expires": day(30)})
        self.records.create("stock__movements", {"item": self.item, "reason": "bought", "amount": 10,
                                                 "expires": day(180), "place": self.garage})
        self.first, self.second = [r[0] for r in self.conn.execute(
            "SELECT id FROM stock__lots WHERE item = ? ORDER BY id", (self.item,))]

    # ----- helpers -------------------------------------------------------------
    def amounts(self):
        """(first batch, second batch, item total)."""
        lot = lambda i: self.records.get("stock__lots", i)["quantity"]  # noqa: E731
        return lot(self.first), lot(self.second), self.records.get("stock__items", self.item)["quantity"]

    def corrections(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM stock__movements WHERE reason IN ('counted_more', 'counted_less') "
            "AND deleted_at IS NULL ORDER BY id")]

    def count(self, counted, recorded=3, batch=None, **kwargs):
        return self.records.count_batch("stock__lots", batch or self.first, counted, recorded, **kwargs)

    def audit_rows(self):
        return self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]

    def client(self, country="Australia"):
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", country)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return client

    def page(self, client, path):
        response = client.get(path, base_url=BASE)
        return response.status_code, response.get_data(as_text=True)

    def post(self, client, path, **form):
        response = client.post(path, data=dict(form, _csrf=client.application.config["CSRF_TOKEN"]), base_url=BASE)
        return response

    # ----- the core: one correction, never the count on top --------------------------------
    def test_counting_more_saves_the_difference_once(self):  # check 2
        result = self.count(5)
        self.assertEqual((result["status"], result["difference"]), ("saved", 2))
        self.assertEqual(self.amounts(), (5, 10, 15))  # not 3 + 5, not 13 + 5
        [movement] = self.corrections()
        self.assertEqual((movement["reason"], movement["amount"], movement["lot"], movement["item"]),
                         ("counted_more", 2, self.first, self.item))
        self.assertEqual(movement["notes"], "Stocktake: counted 5; 3 were recorded.")
        self.assertEqual(movement["happened_on"], TODAY.isoformat())

    def test_counting_fewer_takes_away_only_the_difference(self):  # check 3
        self.count(1)
        self.assertEqual(self.amounts(), (1, 10, 11))
        [movement] = self.corrections()
        self.assertEqual((movement["reason"], movement["amount"]), ("counted_less", 2))
        reasons = {r[0] for r in self.conn.execute("SELECT reason FROM stock__movements")}
        self.assertFalse(reasons & {"used", "thrown_away", "expired"})  # never counted as waste or use

    def test_counting_what_is_recorded_saves_nothing(self):  # check 4
        before = self.audit_rows()
        result = self.count(3)
        self.assertEqual((result["status"], result["movement"]), ("same", None))
        self.assertEqual(self.corrections(), [])
        self.assertEqual(self.audit_rows(), before)

    def test_counting_zero_keeps_the_batch_as_history_and_stops_its_warning(self):  # check 5
        self.assertEqual(len(watch.expiring(self.conn, self.registry, TODAY)), 1)
        self.count(0)
        self.assertEqual(self.amounts(), (0, 10, 10))
        self.assertEqual(self.records.get("stock__lots", self.first)["deleted_at"], None)  # still there
        self.assertEqual(watch.expiring(self.conn, self.registry, TODAY), [])
        self.assertEqual(self.records.get("stock__items", self.item)["expires"], day(180))  # the garage date now

    def test_a_count_that_cannot_be_read_changes_nothing(self):  # check 6
        before = self.audit_rows()
        for typed in ("", "  ", "-1", "five", "1.1234567", "1e20"):
            with self.subTest(typed=typed), self.assertRaises(records.ValidationError) as caught:
                self.count(typed)
            self.assertIn("counted", caught.exception.problems)
        self.assertEqual(self.amounts(), (3, 10, 13))
        self.assertEqual(self.audit_rows(), before)

    def test_a_deleted_batch_cannot_be_counted(self):  # check 6
        self.records.delete("stock__lots", self.first)
        with self.assertRaises(records.RecordNotFound):
            self.count(5)

    def test_a_correction_must_name_one_of_the_items_batches(self):  # check 6
        with self.assertRaises(records.ValidationError) as caught:  # never a new batch, never a guess
            self.records.create("stock__movements", {"item": self.item, "reason": "counted_more", "amount": 2})
        self.assertIn("Count this batch", caught.exception.problems["lot"])
        rice = self.records.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        with self.assertRaises(records.ValidationError):
            self.records.create("stock__movements", {"item": rice, "reason": "counted_less", "amount": 1,
                                                     "lot": self.first})
        self.assertEqual(self.amounts(), (3, 10, 13))

    def test_an_undated_batch_can_be_counted_without_a_date(self):  # check 6
        rice = self.records.create("stock__items", {"name": "Rice", "unit": "kg", "quantity": 2})
        batch = self.conn.execute("SELECT id FROM stock__lots WHERE item = ?", (rice,)).fetchone()[0]
        self.records.count_batch("stock__lots", batch, "2.5", 2)
        lot = self.records.get("stock__lots", batch)
        self.assertEqual((lot["quantity"], lot["expires"]), (2.5, None))

    def test_a_count_reviewed_before_another_change_is_refused(self):  # check 7
        self.records.update("stock__lots", self.first, {"quantity": 4})  # in another window
        with self.assertRaises(records.CountOutOfDate) as caught:
            self.count(5, recorded=3)
        self.assertEqual(caught.exception.current, 4)
        self.assertEqual(self.corrections(), [])
        self.assertEqual(self.amounts(), (4, 10, 14))  # +2 was never applied to the new amount

    def test_saving_the_same_count_twice_makes_one_correction(self):  # check 7
        self.count(5)
        second = self.count(5)  # a second click on Save, with the same review
        self.assertEqual(second["status"], "same")
        self.assertEqual(len(self.corrections()), 1)
        self.assertEqual(self.amounts(), (5, 10, 15))

    def test_history_shows_the_count_before_and_after(self):  # check 8
        self.count(5)
        changes = [h for h in self.records.history("stock__lots", self.first) if h["action"] == "update"]
        self.assertEqual((changes[-1]["before"], changes[-1]["after"]), ({"quantity": 3}, {"quantity": 5}))
        changes = [h for h in self.records.history("stock__items", self.item) if h["action"] == "update"]
        self.assertEqual((changes[-1]["before"], changes[-1]["after"]), ({"quantity": 13}, {"quantity": 15}))

    def test_deleting_and_restoring_a_correction_applies_it_once(self):  # check 9
        movement = self.count(5)["movement"]
        self.records.delete("stock__movements", movement)
        self.assertEqual(self.amounts(), (3, 10, 13))
        self.records.restore("stock__movements", movement)
        self.assertEqual(self.amounts(), (5, 10, 15))
        self.records.restore("stock__movements", movement)  # already back: nothing replayed
        self.assertEqual(self.amounts(), (5, 10, 15))
        less = self.count(4, recorded=5)["movement"]
        self.records.delete("stock__movements", less)  # undoing "counted less" adds it back
        self.assertEqual(self.amounts(), (5, 10, 15))

    def test_an_undo_that_would_go_below_zero_is_refused(self):  # check 9
        movement = self.count(5)["movement"]
        self.records.create("stock__movements", {"item": self.item, "reason": "used", "amount": 4, "lot": self.first})
        with self.assertRaises(records.ValidationError):
            self.records.delete("stock__movements", movement)
        self.assertEqual(self.amounts(), (1, 10, 11))
        self.assertEqual(len(self.corrections()), 1)

    def test_later_use_and_editing_the_correction_change_only_by_the_difference(self):  # check 10
        movement = self.count(5)["movement"]
        self.records.create("stock__movements", {"item": self.item, "reason": "used", "amount": 1})
        self.assertEqual(self.amounts(), (4, 10, 14))  # the earliest use-by batch, as usual
        self.records.update("stock__movements", movement, {"amount": 3})  # it was really +3
        self.assertEqual(self.amounts(), (5, 10, 15))
        with self.assertRaises(records.ValidationError):
            self.records.update("stock__movements", movement, {"reason": "counted_less", "amount": 3})
        self.assertEqual(self.amounts(), (5, 10, 15))

    def test_a_correction_keeps_the_batchs_own_use_by_date(self):  # check 11
        self.count(5)
        self.assertEqual(self.records.get("stock__lots", self.first)["expires"], day(30))
        self.records.count_batch("stock__lots", self.first, 6, 5, happened_on="2026-11-18")
        self.assertEqual(self.corrections()[-1]["happened_on"], "2026-11-18")

    def test_a_direct_batch_edit_is_not_turned_into_a_correction(self):  # check 12
        self.records.update("stock__lots", self.first, {"quantity": 4})
        self.assertEqual(self.corrections(), [])
        self.assertEqual(self.amounts(), (4, 10, 14))

    def test_counts_in_tables_toml_are_checked(self):
        from dashboard.core import modules
        stock = next(m for m in self.report.loaded if m.name == "stock")
        table = stock.tables["movements"]
        for counts in ({"more": "used", "less": "counted_less"}, {"more": "counted_more"},
                       {"more": "counted_more", "less": "bought"},
                       {"more": "counted_more", "less": "counted_less", "note": "amount"}):
            with self.subTest(counts=counts):
                table.adjusts = dict(link="lot", quantity="quantity", amount="amount", direction="reason",
                                     adds=["bought", "counted_more"], belongs_to="item", counts=counts)
                problems = []
                self.assertEqual(modules._check_adjusts("tables.toml", table, stock.tables, problems), {})
                self.assertIn("'counts'", problems[0])

    # ----- the screens ------------------------------------------------------------------------
    def test_count_this_batch_shows_the_exact_batch(self):  # check 1
        client = self.client()
        status, item_page = self.page(client, f"/t/stock__items/{self.item}")
        self.assertIn(f'href="/t/stock__lots/{self.first}/count"', item_page)
        self.assertEqual(self.page(client, f"/t/stock__items/{self.item}/count")[0], 404)  # never the total
        status, batch_page = self.page(client, f"/t/stock__lots/{self.first}")
        self.assertIn("Count this batch", batch_page)
        status, page = self.page(client, f"/t/stock__lots/{self.first}/count")
        self.assertEqual(status, 200)
        use_by = date.fromisoformat(day(30)).strftime("%d/%m/%y")
        self.assertIn(f"Kidney beans · Kitchen › Pantry › Shelf 3 · Use by {use_by}", page)
        self.assertIn("Recorded here: 3 tins", page)
        self.assertEqual(page.count('name="counted"'), 1)

    def test_a_difference_of_one_reads_in_the_singular(self):  # Lane B, batch 14 item 55
        client = self.client()
        path = f"/t/stock__lots/{self.first}/count"
        review = self.post(client, path, step="review", counted="4", recorded="3").get_data(as_text=True)
        self.assertIn("This adds <strong>1 tin</strong> as a <strong>stocktake correction</strong>.", review)
        self.assertNotIn("1 tins", review)

    def test_review_then_save_a_higher_count(self):  # checks 2 and 8
        client = self.client()
        path = f"/t/stock__lots/{self.first}/count"
        review = self.post(client, path, step="review", counted="5", recorded="3").get_data(as_text=True)
        self.assertIn("You counted <strong>5 tins</strong>; <strong>3 tins</strong> are recorded here.", review)
        self.assertIn("This adds <strong>2 tins</strong> as a <strong>stocktake correction</strong>. "
                      "It is not a purchase.", review)
        self.assertIn("Kidney beans will show 15 tins across 2 batches.", review)
        self.assertEqual(self.amounts(), (3, 10, 13))  # nothing saved by reviewing
        saved = self.post(client, path, step="save", counted="5", recorded="3")
        self.assertEqual(saved.status_code, 302)
        status, done = self.page(client, saved.headers["Location"])
        self.assertIn("Count updated. This batch has 5 tins; Kidney beans has 15 tins across 2 batches. "
                      f"Stocktake correction: +2 tins, {TODAY.strftime('%d/%m/%y')}.", done)
        again = self.post(client, path, step="save", counted="5", recorded="3")  # a second click
        self.assertIn("This batch already shows 5 tins. No correction was saved.", again.get_data(as_text=True))
        self.assertEqual(len(self.corrections()), 1)
        status, listing = self.page(client, "/t/stock__movements")
        self.assertIn("Stocktake: more than recorded", listing)

    def test_review_a_lower_count_and_dates_the_us_way(self):  # checks 3 and 11
        client = self.client("United States")
        path = f"/t/stock__lots/{self.first}/count"
        review = self.post(client, path, step="review", counted="1", recorded="3").get_data(as_text=True)
        self.assertIn("This removes <strong>2 tins</strong> as a <strong>stocktake correction</strong>. "
                      "This does not record use or waste.", review)
        self.assertIn("Kidney beans will show 11 tins across 2 batches.", review)
        saved = self.post(client, path, step="save", counted="1", recorded="3")
        status, done = self.page(client, saved.headers["Location"])
        self.assertIn(f"Stocktake correction: −2 tins, {TODAY.strftime('%m/%d/%y')}.", done)

    def test_the_screens_refuse_a_bad_or_stale_count(self):  # checks 4, 6 and 7
        client = self.client()
        path = f"/t/stock__lots/{self.first}/count"
        same = self.post(client, path, step="review", counted="3", recorded="3").get_data(as_text=True)
        self.assertIn("This batch already shows 3 tins. No correction was saved.", same)
        bad = self.post(client, path, step="review", counted="-1", recorded="3")
        self.assertEqual(bad.status_code, 422)
        self.assertIn("The number you counted must be at least 0.", bad.get_data(as_text=True))
        self.records.update("stock__lots", self.first, {"quantity": 4})  # another window
        stale = self.post(client, path, step="save", counted="5", recorded="3")
        self.assertEqual(stale.status_code, 409)
        self.assertIn("This batch now shows 4 tins, so the count you reviewed is out of date. "
                      "Check it again before saving.", stale.get_data(as_text=True))
        self.assertIn("Recorded here: 4 tins", stale.get_data(as_text=True))
        self.assertEqual(self.corrections(), [])
        self.assertEqual(self.post(client, path, step="review", counted="5", recorded="3").status_code, 409)
        self.records.delete("stock__lots", self.first)
        self.assertEqual(self.post(client, path, step="save", counted="5", recorded="4").status_code, 409)
        self.assertEqual(self.records.get("stock__items", self.item)["quantity"], 10)
        self.assertEqual(self.corrections(), [])

    def test_the_count_form_needs_the_safety_token(self):
        client = self.client()
        response = client.post(f"/t/stock__lots/{self.first}/count", data={"step": "save", "counted": "5",
                                                                           "recorded": "3"}, base_url=BASE)
        self.assertNotEqual(response.status_code, 302)
        self.assertEqual(self.amounts(), (3, 10, 13))


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
