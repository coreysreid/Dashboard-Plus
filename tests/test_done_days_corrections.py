"""Tests for correcting earlier done days: Not a done day with Undo, a cleared date kept, and a press with its typed date counted once (decision 0132)."""
import inspect
import json
import re
from datetime import date

from test_done_history import (GARDEN, LOANS, SECRET, SERVICES, TODAY, EARLIER, HistoryCase, done_days, main)
from dashboard.core import actions, bars, calendars, dates, calendars_corrections, sync

NOT_DONE = "Not a done day — remove from the calendar"


def press_without_a_date(case, record_id: int, day: str, op: str):
    """A Garden Mark done saved before decision 0129: it set only the tick, so the job keeps no done date."""
    case.conn.execute(f"UPDATE {GARDEN} SET done = 1 WHERE id = ?", (record_id,))
    case.conn.execute(
        "INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after) VALUES "
        "(?, 'person', 'action', ?, ?, ?, ?)",
        (f"{day}T12:00:00+00:00", GARDEN, record_id, '{"done": false}',
         '{"key": "done", "operation": "%s", "one_step": true, "added_table": null, "added": null, '
         '"before": {"done": false}, "after": {"done": true}, "next": null, "answers": {}, "copied": {}, '
         '"counts_as": "done", "missed": false, "on": "%s"}' % (op, day)))
    case.conn.commit()


class Case(HistoryCase):
    def history_rows(self):
        return [tuple(r) for r in self.conn.execute("SELECT * FROM core__audit ORDER BY id")]

    def post(self, path, data, token=True):
        client = self.client()
        form = dict(data, **({"_csrf": client.application.config["CSRF_TOKEN"]} if token else {}))
        return client.post(path, base_url=BASE_URL, data=form)


BASE_URL = "http://127.0.0.1:5148"


class NotADoneDayTests(Case):
    """(a) A date fixed forward on a later day: the household can take the wrong day off, and put it back."""

    def setUp(self):
        super().setUp()
        self.on("2026-09-02", SERVICES, self.service, {"last_done": "2026-09-01"})
        self.on("2026-09-10", SERVICES, self.service, {"last_done": "2026-09-10"})  # really done on the 10th

    def test_the_wrong_day_can_be_taken_off_and_put_back(self):
        self.assertIn((self.service, "2026-09-01", "earlier"), done_days(self.conn, self.registry, SERVICES,
                                                                        "last_done"))
        page = main(self.page(f"/calendar/{SERVICES}?month=2026-09"))
        self.assertIn(f'action="/calendar/{SERVICES}/not-done"', page)
        self.assertEqual(page.count(NOT_DONE), 1, "only the day read from history, never the date it keeps now")
        self.assertIn('name="day" value="2026-09-01"', page)
        before = self.history_rows()
        reply = self.post(f"/calendar/{SERVICES}/not-done",
                          {"record": self.service, "day": "2026-09-01", "month": "2026-09"})
        self.assertEqual(reply.status_code, 302)
        op = re.search(r"removed=([A-Za-z0-9_-]+)", reply.headers["Location"]).group(1)
        after = self.history_rows()
        self.assertEqual(after[:len(before)], before, "earlier history is never changed")
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[-1][3], calendars_corrections.OFF)
        self.assertEqual([d for _, d, _ in done_days(self.conn, self.registry, SERVICES, "last_done")],
                         ["2026-03-02", "2026-09-10"])
        self.assertEqual(self.store.get(SERVICES, self.service)["last_done"], "2026-09-10", "the record is unchanged")
        notice = self.page(reply.headers["Location"].replace(BASE_URL, ""))
        self.assertIn("Taken off the calendar: Example hatchback: Oil change", notice)
        self.assertIn(f'name="op" value="{op}"', notice)
        self.assertNotIn(NOT_DONE, main(notice))
        record = self.page(f"/t/{SERVICES}/{self.service}")
        style = dates.household_style(self.conn)
        self.assertIn(f"said {dates.show(date(2026, 9, 1), style)} was not a done day: taken off the calendar", record)
        self.assertIn("Put back on the calendar", record)
        reply = self.post(f"/calendar/{SERVICES}/put-back", {"op": op, "back": "record"})
        self.assertEqual((reply.status_code, reply.headers["Location"].endswith(f"/t/{SERVICES}/{self.service}")),
                         (302, True))
        self.assertIn((self.service, "2026-09-01", "earlier"), done_days(self.conn, self.registry, SERVICES,
                                                                        "last_done"))
        record = self.page(f"/t/{SERVICES}/{self.service}")
        self.assertIn(f"put {dates.show(date(2026, 9, 1), style)} back on the calendar", record)
        self.assertNotIn("Put back on the calendar</button>", record)
        self.assertEqual(self.history_rows()[:len(after)], after)
        self.assertEqual(self.post(f"/calendar/{SERVICES}/put-back", {"op": op}).status_code, 302, "twice is harmless")

    def test_pressing_twice_writes_one_entry(self):
        info = self.registry[SERVICES]
        first = calendars_corrections.take_off(self.store, info, self.service, date(2026, 9, 1))
        count = len(self.history_rows())
        self.assertEqual(calendars_corrections.take_off(self.store, info, self.service, date(2026, 9, 1)), first)
        self.assertEqual(len(self.history_rows()), count)

    def test_the_date_it_keeps_now_and_other_days_cannot_be_taken_off(self):
        before = self.history_rows()
        for day in ("2026-09-10", "2026-09-05"):
            reply = self.post(f"/calendar/{SERVICES}/not-done", {"record": self.service, "day": day, "month": "2026-09"})
            self.assertIn("unchanged=1", reply.headers["Location"])
        self.assertEqual(self.history_rows(), before)
        self.assertIn("Nothing was changed.", self.page(f"/calendar/{SERVICES}?month=2026-09&unchanged=1"))

    def test_the_session_check_and_unknown_lists(self):
        before = self.history_rows()
        self.assertEqual(self.post(f"/calendar/{SERVICES}/not-done", {"record": self.service, "day": "2026-09-01"},
                                   token=False).status_code, 400)
        self.assertEqual(self.post("/calendar/nothing_here/not-done", {"record": 1, "day": "2026-09-01"}).status_code,
                         404)
        self.assertEqual(self.post(f"/calendar/{SERVICES}/not-done", {"record": self.service, "day": "soon"})
                         .status_code, 404)
        self.assertEqual(self.post(f"/calendar/{SERVICES}/put-back", {"op": "not-a-real-operation"}).status_code, 404)
        self.assertEqual(self.history_rows(), before)

    def test_the_calendar_rules_still_hold(self):
        text = main(self.page(f"/calendar/{SERVICES}?month=2026-09"))
        self.assertNotIn("<script", text)
        self.assertNotIn(SECRET, text)
        self.assertIn('name="_csrf"', text)
        plain = re.sub(r"<[^>]+>", " ", text).replace("earlier times are never filled in as missed", "")
        plain = plain.replace("does not mean anything was missed", "")  # the bars under the calendar (decision 0131)
        for word in ("missed", "Missed", "overdue"):
            self.assertNotIn(word, plain)
        together = self.page("/to-do/calendar?month=2026-09")
        self.assertIn(f"Oil change: Service or check done {EARLIER}", together)
        self.assertNotIn(NOT_DONE, together, "taken off on the list's own calendar only")


class ClearedDateTests(Case):
    """(b) A date that stood a day or more and was then cleared is kept as a done day."""

    def setUp(self):
        super().setUp()
        neighbour = self.store.create("people__people", {"name": "Example Neighbour"})
        self.saved_on = "2026-10-01"
        self.drill = self.store.create(LOANS, {"name": "Example drill", "borrower": neighbour, "lent_on": "2026-10-01",
                                               "due_back": "2026-10-20", "status": "out"})

    def test_lending_again_keeps_the_earlier_return(self):
        self.saved_on = "2026-10-10"
        self.store.action(LOANS, self.drill, "returned", op="0b5f3c1e-2222-4a6b-9e7d-000000000301",
                          today=date(2026, 10, 10))
        self.on("2026-11-01", LOANS, self.drill, {"status": "out", "returned_on": None, "lent_on": "2026-11-01",
                                                  "due_back": "2026-11-25"})
        self.saved_on = "2026-11-20"
        self.store.action(LOANS, self.drill, "returned", op="0b5f3c1e-2222-4a6b-9e7d-000000000302", today=TODAY)
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"),
                         [(self.drill, "2026-10-10", "earlier"), (self.drill, "2026-11-20", "now")])

    def test_a_same_day_clear_and_a_late_undo_never_count(self):
        self.saved_on = "2026-10-10"
        self.store.action(LOANS, self.drill, "returned", op="0b5f3c1e-2222-4a6b-9e7d-000000000303",
                          today=date(2026, 10, 10))
        self.saved_on = "2026-10-12"  # undone two days later: the return did not happen
        actions.undo(self.store, LOANS, self.drill, "0b5f3c1e-2222-4a6b-9e7d-000000000303")
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"), [])
        self.on("2026-10-13", LOANS, self.drill, {"status": "returned", "returned_on": "2026-10-13"})
        self.on("2026-10-13", LOANS, self.drill, {"status": "out", "returned_on": None})  # a slip, fixed at once
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"), [])

    def test_a_wrong_cleared_date_can_be_taken_off(self):
        self.on("2026-10-05", LOANS, self.drill, {"status": "returned", "returned_on": "2026-10-04"})
        self.on("2026-10-07", LOANS, self.drill, {"status": "out", "returned_on": None})
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"),
                         [(self.drill, "2026-10-04", "earlier")])
        calendars_corrections.take_off(self.store, self.registry[LOANS], self.drill, date(2026, 10, 4))
        self.assertEqual(done_days(self.conn, self.registry, LOANS, "returned_on"), [])


class PressAndTypedDateTests(Case):
    """(c) An old press and a Done on typed afterwards for the same completion count once, on the typed date."""

    def setUp(self):
        super().setUp()
        self.saved_on = "2026-11-01"
        self.weed = self.store.create(GARDEN, {"title": "Weed the beds", "due_on": "2026-11-18", "notes": SECRET})

    def test_the_typed_date_replaces_the_press(self):
        press_without_a_date(self, self.weed, "2026-11-19", "0b5f3c1e-3333-4a6b-9e7d-000000000401")
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [(self.weed, "2026-11-19", "press")])
        self.on("2026-11-21", GARDEN, self.weed, {"done_on": "2026-11-17"})  # the day it was really done
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [(self.weed, "2026-11-17", "now")])
        found = bars.build(self.conn, self.registry[GARDEN], self.registry[GARDEN].table.bars[0], None, "month",
                           TODAY, "monday", TODAY, registry=self.registry)
        self.assertEqual(sum(p.count for p in found), 1)

    def test_a_new_round_keeps_both(self):
        press_without_a_date(self, self.weed, "2026-11-05", "0b5f3c1e-3333-4a6b-9e7d-000000000402")
        self.on("2026-11-08", GARDEN, self.weed, {"done": False, "due_on": "2026-11-18"})  # needs doing again
        self.on("2026-11-19", GARDEN, self.weed, {"done": True, "done_on": "2026-11-19"})
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"),
                         [(self.weed, "2026-11-05", "press"), (self.weed, "2026-11-19", "now")])

    def test_an_old_press_can_be_taken_off(self):
        press_without_a_date(self, self.weed, "2026-11-19", "0b5f3c1e-3333-4a6b-9e7d-000000000403")
        page = main(self.page(f"/calendar/{GARDEN}?month=2026-11"))
        self.assertIn(NOT_DONE, page)
        self.assertNotIn(SECRET, page)
        calendars_corrections.take_off(self.store, self.registry[GARDEN], self.weed, date(2026, 11, 19))
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [])

    def test_taking_a_day_off_never_blocks_undo_of_mark_done(self):
        self.on("2026-09-02", GARDEN, self.weed, {"done": True, "done_on": "2026-09-01"})
        self.on("2026-10-01", GARDEN, self.weed, {"done": False})
        self.saved_on = "2026-11-20"
        op = "0b5f3c1e-3333-4a6b-9e7d-000000000404"
        self.store.action(GARDEN, self.weed, "done", op=op, today=TODAY)
        calendars_corrections.take_off(self.store, self.registry[GARDEN], self.weed, date(2026, 9, 1))
        self.assertTrue(actions.can_undo(self.store, self.registry[GARDEN], self.weed, op))
        actions.undo(self.store, GARDEN, self.weed, op)
        # Undo puts Done on back to 1 September: the date a record keeps now always shows (change it on its page).
        self.assertEqual(done_days(self.conn, self.registry, GARDEN, "done_on"), [(self.weed, "2026-09-01", "now")])


class CoreTests(Case):
    def test_core_names_no_module(self):
        text = (inspect.getsource(calendars_corrections) + inspect.getsource(calendars._history)
                + inspect.getsource(calendars.done_days)).lower()
        for module in ("vehicle", "garden", "lent_out", "home_layout", "alarm", "loan"):
            self.assertNotIn(module, text)

    def test_no_new_table_nothing_private_and_nothing_travels(self):
        tables = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.on("2026-09-02", SERVICES, self.service, {"last_done": "2026-09-01"})
        self.on("2026-09-10", SERVICES, self.service, {"last_done": "2026-09-10"})
        changes = self.conn.execute(f"SELECT COUNT(*) FROM {sync.LOG}").fetchone()[0]
        calendars_corrections.take_off(self.store, self.registry[SERVICES], self.service, date(2026, 9, 1))
        row = self.conn.execute("SELECT before, after FROM core__audit WHERE action = ?",
                                (calendars_corrections.OFF,)).fetchone()
        self.assertIsNone(row["before"])
        self.assertEqual(set(json.loads(row["after"])), {"calendar_day", "operation"})
        self.assertNotIn(SECRET, row["after"])
        self.assertEqual({r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")},
                         tables)
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {sync.LOG}").fetchone()[0], changes,
                         "kept in this computer's history only, like every history line")
