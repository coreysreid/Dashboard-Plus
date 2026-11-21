"""Tests for decision 0112: one-press actions leave a named history entry with Undo, and the move-in traps from Lane B's read-through.

Lane B's draft (workbench/drafts/helper_move_in/) ranks thirteen traps and lists nine acceptance checks; the
tests below name the trap or check they cover. Every household, place, item and registration is invented."""
import json
import re
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.connector import tools
from dashboard.core import actions, checklist, db, helpers, move_in, proposals, records, settings, startup
from dashboard.core.proposals import ProposalError
from dashboard.core.records import ActionNotAvailable
from dashboard.web.app import create_app

PORT = 5143
BASE = f"http://127.0.0.1:{PORT}"
GARDEN, LOANS = "garden__jobs", "lent_out__loans"
PRIVATE = "QX-7731-INVENTED"  # a made-up private vehicle registration
WHY = "Moving the invented Taylor pantry list in"


class DoneHistoryCase(TempDirTestCase):
    MODULES = ("people", "stock", "garden", "lent_out", "vehicles")

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
        self.store = records.Records(self.conn, self.registry)
        self.today = date.today()
        self.friend = self.store.create("people__people", {"name": "Person Garcia"})

    def day(self, offset=0) -> str:
        return (self.today + timedelta(days=offset)).isoformat()

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        self.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, client, path):
        response = client.get(path, base_url=BASE)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def loan(self, **values):
        return self.store.create(LOANS, {"name": "Invented ladder", "borrower": self.friend,
                                         "lent_on": self.day(-5), "due_back": self.day(), **values})

    def job(self):
        return self.store.create(GARDEN, {"title": "Water seedlings", "due_on": self.day(), "done": False})

    def done_keys(self):
        return [(d.source.info.name, d.record_id, d.key) for d in
                checklist.done(self.conn, self.registry, self.today, self.today)]


class OnePressHistoryTests(DoneHistoryCase):
    def test_a_press_writes_one_named_entry_with_its_number_the_fields_and_the_day(self):
        loan = self.loan()
        op = actions.new_operation()
        changed = self.store.action(LOANS, loan, "returned", op=op, today=self.today)
        self.assertEqual(changed["status"], ["out", "returned"])
        saved = actions.operation(self.store, self.registry[LOANS], loan, op)
        self.assertEqual((saved["key"], saved["on"], saved["one_step"], saved["added_table"]),
                         ("returned", self.day(), True, None))
        self.assertEqual(saved["before"], {"status": "out", "returned_on": None})
        self.assertEqual(saved["after"], {"status": "returned", "returned_on": self.day()})
        self.assertFalse(saved["undone"])

    def test_garden_and_loan_presses_appear_as_done_today_and_in_this_years_counts(self):
        job, loan = self.job(), self.loan()
        self.store.action(GARDEN, job, "done")
        self.store.action(LOANS, loan, "returned")
        self.assertEqual(sorted(self.done_keys()), [(GARDEN, job, "done"), (LOANS, loan, "returned")])
        month = checklist.by_month(self.conn, self.registry, self.today.year)[self.today.month - 1]
        self.assertEqual((month["done"], month["skipped"]), (2, 0))
        self.assertEqual(checklist.done(self.conn, self.registry, self.today, self.today, only=GARDEN)[0].name,
                         "Water seedlings")

    def test_undo_puts_the_fields_back_and_the_task_returns(self):
        job = self.job()
        op = actions.new_operation()
        self.store.action(GARDEN, job, "done", op=op)
        self.assertNotIn((GARDEN, job), [(t.source.info.name, t.row["id"]) for t in
                                         checklist.tasks(self.conn, self.registry, "today", self.today)])
        self.assertTrue(actions.can_undo(self.store, self.registry[GARDEN], job, op))
        actions.undo(self.store, GARDEN, job, op)
        self.assertFalse(self.store.get(GARDEN, job)["done"])
        self.assertIn((GARDEN, job), [(t.source.info.name, t.row["id"]) for t in
                                      checklist.tasks(self.conn, self.registry, "today", self.today)])
        self.assertEqual(self.done_keys(), [])  # an undone press is not counted
        with self.assertRaises(ActionNotAvailable) as caught:
            actions.undo(self.store, GARDEN, job, op)
        self.assertIn("already undone", str(caught.exception))

    def test_undo_is_refused_after_any_later_change_and_nothing_changes(self):
        loan = self.loan()
        op = actions.new_operation()
        self.store.action(LOANS, loan, "returned", op=op)
        self.store.update(LOANS, loan, {"notes": "Came back with a scuff"})
        self.assertFalse(actions.can_undo(self.store, self.registry[LOANS], loan, op))
        with self.assertRaises(ActionNotAvailable) as caught:
            actions.undo(self.store, LOANS, loan, op)
        self.assertIn("Nothing was undone", str(caught.exception))
        self.assertEqual(self.store.get(LOANS, loan)["status"], "returned")
        self.assertEqual(self.done_keys(), [(LOANS, loan, "returned")])  # still done: it was not undone

    def test_a_used_number_and_a_bad_number_are_refused_and_change_nothing(self):
        first, second = self.job(), self.job()
        op = actions.new_operation()
        self.store.action(GARDEN, first, "done", op=op)
        with self.assertRaises(ActionNotAvailable):
            self.store.action(GARDEN, second, "done", op=op)
        with self.assertRaises(ActionNotAvailable):
            self.store.action(GARDEN, second, "done", op="short")
        self.assertFalse(self.store.get(GARDEN, second)["done"])

    def test_a_deleted_record_drops_out_of_done(self):
        job = self.job()
        self.store.action(GARDEN, job, "done")
        self.store.delete(GARDEN, job)
        self.assertEqual(self.done_keys(), [])

    def test_history_names_the_press_and_its_undo_with_no_added_record(self):
        loan = self.loan()
        op = actions.new_operation()
        client = self.client()
        self.store.action(LOANS, loan, "returned", op=op)
        actions.undo(self.store, LOANS, loan, op)
        html = self.page(client, f"/t/{LOANS}/{loan}")
        self.assertIn("used Mark returned", html)
        self.assertIn("undid Mark returned", html)
        self.assertNotIn("added a record", html)

    def test_things_to_do_shows_the_press_under_done_today_with_undo_and_undo_brings_it_back(self):
        job = self.job()
        client = self.client()
        response = client.post(f"/t/{GARDEN}/{job}/do/done", data={"_csrf": self.csrf, "back": "/to-do"},
                               base_url=BASE)
        location = response.headers["Location"]
        op = re.search(r"&op=([A-Za-z0-9_-]+)", location).group(1)
        html = self.page(client, location)
        self.assertIn("Marked as done.", html)
        self.assertIn("Done today", html)
        self.assertIn(f'action="/t/{GARDEN}/{job}/undo/{op}"', html)
        self.assertIn('aria-label="Undo Mark done: Water seedlings"', html)
        back = client.post(f"/t/{GARDEN}/{job}/undo/{op}", data={"_csrf": self.csrf, "back": "/to-do"},
                           base_url=BASE)
        self.assertEqual(back.status_code, 302)
        after = self.page(client, back.headers["Location"])
        self.assertIn("Undone. Mark done was taken back, so this is as it was before.", after)
        self.assertNotIn("Done today", after)
        self.assertFalse(self.store.get(GARDEN, job)["done"])

    def test_the_record_page_offers_undo_straight_after_the_press(self):
        loan = self.loan()
        client = self.client()
        response = client.post(f"/t/{LOANS}/{loan}/do/returned", data={"_csrf": self.csrf}, base_url=BASE)
        html = self.page(client, response.headers["Location"])
        self.assertIn("Marked returned today.", html)
        undo = re.search(r'action="(/t/lent_out__loans/\d+/undo/[^"]+)"', html).group(1)
        self.assertEqual(client.post(undo, data={"_csrf": self.csrf}, base_url=BASE).status_code, 302)
        row = self.store.get(LOANS, loan)
        self.assertEqual((row["status"], row["returned_on"]), ("out", None))
        again = client.post(undo, data={"_csrf": self.csrf}, base_url=BASE)
        self.assertEqual(again.status_code, 409)
        self.assertIn("already undone", again.get_data(as_text=True))

    def test_a_one_step_action_may_name_its_undo_words_and_they_must_be_words(self):
        from dashboard.core import modules
        problems = []
        table = self.registry[LOANS].table
        raw = [{"key": "back", "label": "Back now", "show_when": {"status": "out"}, "set": {"status": "returned",
                "returned_on": "today"}, "done": "Back.", "undo": "   "}]
        self.assertEqual(modules._check_actions("tables.toml", table, raw, {}, {}, problems), [])
        self.assertIn("'undo' must be a short sentence", problems[0])
        problems = []
        raw[0]["undo"] = "Put it back out"
        checked = modules._check_actions("tables.toml", table, raw, {}, {}, problems)
        self.assertEqual((problems, checked[0]["undo"]), ([], "Put it back out"))


def guide(case, helper) -> str:
    """The starting message for one helper, as Settings, Helpers and GET /api/v1/guide show it."""
    from dashboard.web import helper_guide
    with case.client().application.app_context():
        return helper_guide.guide_text(case.conn, case.registry, helper)


class MoveInCase(DoneHistoryCase):
    def setUp(self):
        super().setUp()
        kitchen = self.store.create("stock__places", {"name": "Kitchen"})
        garage = self.store.create("stock__places", {"name": "Garage"})
        pantry = self.store.create("stock__places", {"name": "Pantry", "inside": kitchen})
        self.pantry_shelf = self.store.create("stock__places", {"name": "Shelf 3", "inside": pantry})
        self.garage_shelf = self.store.create("stock__places", {"name": "Shelf 3", "inside": garage})
        self.car = self.store.create("vehicles__vehicles", {"name": "Invented hatchback", "registration": PRIVATE})
        self.helper, self.key = helpers.issue(self.conn, self.data, "Move-in helper", "suggest",
                                              ["stock", "vehicles"])

    def rice(self, **more):
        return {"table": "stock__items", "values": dict({"name": "Invented rice", "category": "pantry", "unit": "kg",
                                                         "quantity": 2, "place": self.pantry_shelf}, **more)}

    def stock_in(self, amount=2, ref=0):
        return {"table": "stock__movements", "values": {"item": {"ref": ref}, "reason": "bought", "amount": amount,
                                                        "happened_on": self.day()}}

    def send(self, entries, key="move-1", why=WHY):
        return proposals.submit(self.conn, self.registry, self.helper,
                                {"request_key": key, "why": why, "entries": entries})[0]

    def refused(self, entries):
        with self.assertRaises(ProposalError) as caught:
            self.send(entries)
        self.assertEqual(caught.exception.code, "invalid")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0], 0)
        return caught.exception.problems[0]["message"]


class CountTwiceTests(MoveInCase):
    def test_trap_1_and_check_3_same_amount_is_kept_with_a_plain_warning(self):
        result = self.send([self.rice(), self.stock_in(2)])
        self.assertEqual(result["state"], "waiting")  # nothing refused: Review decides
        self.assertEqual([w["entry"] for w in result["warnings"]], [1])
        self.assertEqual(result["warnings"][0]["code"], "may_count_twice")
        self.assertEqual(result["warnings"][0]["message"],
                         "This would count the amount twice: the new item “Invented rice” already starts with 2 kg, "
                         "and this Stock in adds 2 kg more, 4 kg in all. If 2 kg is what is on hand now, reject this "
                         "Stock in and accept only the new item.")
        again = self.send([self.rice(), self.stock_in(2)])  # the exact retry gets the same answer
        self.assertEqual(again["warnings"], result["warnings"])

    def test_a_different_amount_asks_for_a_check_and_a_lone_item_or_stock_in_has_no_warning(self):
        result = self.send([self.rice(), self.stock_in(1)])
        self.assertTrue(result["warnings"][0]["message"].startswith("Check the amount: the new item “Invented rice” "
                                                                    "already starts with 2 kg, and this Stock in adds 1 "
                                                                    "kg more, 3 kg in all."))
        self.assertNotIn("warnings", self.send([self.rice()], key="move-2"))
        plain = {"table": "stock__items", "values": {"name": "Invented lentils", "category": "pantry", "unit": "bags"}}
        self.assertNotIn("warnings", self.send([plain, self.stock_in(3)], key="move-3"))  # no starting amount
        used = dict(self.stock_in(2), values=dict(self.stock_in(2)["values"], reason="used"))
        self.assertNotIn("warnings", self.send([self.rice(name="Invented oats"), used], key="move-4"))

    def test_review_warns_on_the_stock_in_and_in_accept_all_and_rejecting_it_keeps_one_count(self):
        result = self.send([self.rice(), self.stock_in(2)])
        client = self.client()
        html = self.page(client, "/review")
        self.assertIn("data-count-twice", html)
        self.assertIn("This would count the amount twice", html)
        self.assertIn("1 Stock in below may count a new item's starting amount twice", html)
        proposals.reject(self.conn, result["proposals"][1]["id"])
        proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])
        row = self.conn.execute("SELECT quantity FROM stock__items WHERE name = 'Invented rice'").fetchone()
        self.assertEqual(row["quantity"], 2)  # counted once
        self.assertNotIn("data-count-twice", self.page(client, "/review"))

    def test_the_warning_stays_while_the_item_is_accepted_alone_and_the_stock_in_waits(self):
        result = self.send([self.rice(), self.stock_in(2)])
        proposals.accept(self.conn, self.registry, result["proposals"][0]["id"])
        html = self.page(self.client(), "/review")
        self.assertIn("This would count the amount twice", html)

    def test_the_reply_and_the_batch_fit_the_published_description(self):
        from test_api_contract import SPEC, check
        result = self.send([self.rice(), self.stock_in(2)])
        self.assertEqual(check(result, SPEC["components"]["schemas"]["Batch"]), [])
        detail = proposals.batch_result(self.conn, result["batch_id"], detail=True, registry=self.registry)
        self.assertEqual(check(detail, SPEC["components"]["schemas"]["BatchDetail"]), [])
        self.assertEqual(detail["warnings"], result["warnings"])


class NameHintTests(MoveInCase):
    def test_trap_2_a_name_with_two_full_path_matches_names_both_and_says_ask(self):
        message = self.refused([self.rice(place="Shelf 3")])
        self.assertIn("“Shelf 3” is a name, not an id, and 2 records in Places match it: "
                      f"Garage › Shelf 3 (id {self.garage_shelf}); Kitchen › Pantry › Shelf 3 (id {self.pantry_shelf}). "
                      "They are different records. Ask the household which one is meant, then send its id.", message)
        self.assertIn("compare the full path, never only the last name", message)

    def test_a_partial_path_finds_the_one_full_path(self):
        for typed in ("Pantry > Shelf 3", "pantry › shelf 3", "Kitchen/Pantry/Shelf 3"):
            with self.subTest(typed):
                message = self.refused([self.rice(place=typed)])
                self.assertIn(f"The record in Places with that name is Kitchen › Pantry › Shelf 3 "
                              f"(id {self.pantry_shelf}). Send its id.", message)

    def test_no_match_says_so_and_does_not_guess(self):
        message = self.refused([self.rice(place="Shelf 9")])
        self.assertIn("no record in Places has that name or path. Do not guess one that looks close.", message)
        self.assertIn("Look up Places first", message)

    def test_a_number_that_is_not_there_keeps_the_plain_next_step(self):
        message = self.refused([self.rice(place=99999)])
        self.assertNotIn("is a name", message)
        self.assertIn("Look up Places first", message)

    def test_name_hint_leaves_ids_and_unnamed_lists_alone(self):
        self.assertIsNone(move_in.name_hint(self.conn, self.registry, "stock__places", "12"))
        self.assertIsNone(move_in.name_hint(self.conn, self.registry, "stock__places", {"ref": 0}))
        self.assertIsNone(move_in.name_hint(self.conn, self.registry, "nothing__here", "Shelf 3"))


class PrivateCopyTests(MoveInCase):
    def review(self):
        return self.page(self.client(), "/review")

    def test_trap_3_a_private_value_copied_into_notes_is_flagged_on_review_without_repeating_it(self):
        self.send([self.rice(notes=f"Bought with the car, rego {PRIVATE.lower().replace('-', ' ')}")])
        html = self.review()
        warning = re.search(r'<p class="problem" role="status" data-private-copy[^>]*>(.*?)</p>', html, re.S).group(1)
        self.assertIn("This may hold a private detail you keep in Vehicles (Registration or plate number).", warning)
        self.assertNotIn("7731", warning)

    def test_a_private_value_in_why_is_flagged_and_the_helper_reply_never_says_so(self):
        result = self.send([self.rice()], why=f"From the glovebox list for {PRIVATE}")
        self.assertNotIn("warnings", result)
        self.assertNotIn("private", json.dumps(result).lower())
        html = self.review()
        self.assertIn("The reason above: This may hold a private detail you keep in Vehicles", html)

    def test_ordinary_text_is_not_flagged_and_short_private_values_are_not_compared(self):
        self.store.update("vehicles__vehicles", self.car, {"registration": "AB12"})
        self.send([self.rice(notes="Top shelf, 2026 stock")])
        self.assertNotIn("data-private-copy", self.review())
        self.assertEqual(move_in.private_values(self.conn, self.registry), {})

    def test_the_guide_says_to_leave_private_facts_out_of_ordinary_text(self):
        text = guide(self, self.helper)
        self.assertIn("Do not copy private facts into names, notes, why or receipt lines", text)
        self.assertNotIn(PRIVATE, text)


class GuideAdditionTests(MoveInCase):
    def text(self, helper=None):
        return guide(self, helper or self.helper)

    def test_the_remaining_ranked_traps_have_their_guide_words(self):
        text = self.text()
        for words in ("You can only suggest new records. You cannot change, merge or delete a record",  # trap 11
                      "Match by the full path and details (Kitchen › Pantry › Shelf 3",  # trap 2
                      "If the list a link needs is not shown here, stop and ask the household",  # trap 10
                      "a date whose day and month could be either way round (1/2/27)",  # trap 5, check 4
                      "whether water is safe to drink now",
                      "Its warnings (such as may_count_twice) need the person's attention",  # trap 1
                      "Count from GET /api/v1/batches, not from memory",  # trap 4
                      "THE HOME'S LAYOUT", "Never invent a connection or a door to outside"):  # trap 6, check 8
            self.assertIn(words, text)

    def test_a_look_only_helper_gets_no_sending_or_layout_words(self):
        reader, _key = helpers.issue(self.conn, self.data, "Look helper", "read", ["stock"])
        text = self.text(reader)
        for words in ("THE HOME'S LAYOUT", "Count from GET /api/v1/batches", "Its warnings"):
            self.assertNotIn(words, text)

    def test_the_connector_says_the_same_in_its_tool_descriptions(self):
        suggest = tools.BY_NAME["dashboard_suggest_new_records"].description
        for words in ("counts twice", "may_count_twice", "never a name", "full place path", "ask the household",
                      "Never copy codes"):
            self.assertIn(words, suggest)
        self.assertIn("warnings", tools.BY_NAME["dashboard_get_suggestion_batch"].description)
