"""Tests for Things to do and Routines (decision 0107): the eleven checks in Lane B's routine checklist draft, and more.

The draft (workbench/drafts/routine_checklists/ACCEPTANCE.md, now in git history) lists eleven checks; each
test below names the check it covers. All jobs, dates and households are invented."""
import io
import json
import re
import shutil
import time
import zipfile
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import actions, checklist, dates, db, export, records, settings, startup, sync, watch
from dashboard.core.records import ActionNotAvailable
from dashboard.web.app import create_app
from dashboard.web.checklist import EMPTY, week_range

PORT = 5141
BASE = f"http://127.0.0.1:{PORT}"
JOBS, GARDEN, EQUIPMENT = "home_care__jobs", "garden__jobs", "home_layout__equipment"
ROUTINES, TIMES, WORK = "routines__routines", "routines__times", "home_care__work_done"


class ChecklistTestCase(TempDirTestCase):
    MODULES = ("people", "stock", "home_layout", "home_care", "garden", "routines")

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
        self.place = self.store.create("stock__places", {"name": "Garage roof"})

    def day(self, offset=0) -> str:
        return (self.today + timedelta(days=offset)).isoformat()

    def tasks(self, window="today", today=None, first_day="monday", only=None):
        return checklist.tasks(self.conn, self.registry, window, today or self.today, first_day, only)

    def keys(self, window="today", **kw):
        return [(t.source.info.name, t.row["id"]) for t in self.tasks(window, **kw)]

    def client(self, today=None):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        if today is not None:
            app.config["TODAY"] = lambda: today
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        self.csrf = app.config["CSRF_TOKEN"]
        return client

    def page(self, client, path):
        response = client.get(path, base_url=BASE)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def form_fields(self, html):
        return dict(re.findall(r'name="(operation|revision)" value="([^"]*)"', html))

    def routine(self, name="Put the bins out", count=1, unit="weeks", due=0, **values):
        return self.store.create(ROUTINES, {"name": name, "repeat_count": count, "repeat_unit": unit,
                                            "first_due": values.pop("first_due", self.day(due)),
                                            "next_due": self.day(due), "paused": False, **values})

    def tick(self, routine_id, key="done", choice="repeat", next_date=None, op=None, done_on=None, **kw):
        answers = {"done_on": done_on or self.day()}
        return actions.complete(self.store, ROUTINES, routine_id, key, answers,
                                actions.revision(self.store, self.registry[ROUTINES], routine_id),
                                op or actions.new_operation(), next_choice=choice, next_date=next_date, **kw)


class AcceptanceChecks(ChecklistTestCase):
    def test_check_1_home_care_job_is_one_linked_row_and_only_home_cares_mark_done_completes_it(self):
        job = self.store.create(JOBS, {"name": "Clean the gutters", "kind": "gutters", "place": self.place,
                                       "next_due": self.day()})
        for window in checklist.WINDOWS:
            self.assertEqual(self.keys(window).count((JOBS, job)), 1, window)
        client = self.client()
        html = self.page(client, "/to-do")
        self.assertIn(f'href="/t/{JOBS}/{job}/do/done?back=/to-do"', html)
        self.assertIn("Garage roof", html)
        form = self.page(client, f"/t/{JOBS}/{job}/do/done?back=/to-do")
        self.assertIn('name="back" value="/to-do"', form)
        self.assertIn("When do you want to do it again?", form)  # decision 0091's own form
        fields = self.form_fields(form)
        sent = {"_csrf": self.csrf, "done_on": dates.show(self.day(), dates.DAY_FIRST), "next_choice": "date",
                "next_date": dates.show(self.day(90), dates.DAY_FIRST), "back": "/to-do", **fields}
        response = client.post(f"/t/{JOBS}/{job}/do/done", data=sent, base_url=BASE)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith(f"/to-do?table={JOBS}&record={job}&op="))
        again = client.post(f"/t/{JOBS}/{job}/do/done", data=sent, base_url=BASE)  # a double click
        self.assertEqual(again.status_code, 302)
        self.assertEqual(self.store.count(WORK), 1)
        self.assertEqual(self.store.count(TIMES), 0)  # no routine tick, no second completion
        self.assertEqual(self.store.get(JOBS, job)["next_due"], self.day(90))
        after = self.page(client, response.headers["Location"])
        self.assertIn("Marked done on", after)
        self.assertIn("Undo this completion", after)
        self.assertIn("Done today", after)
        self.assertNotIn((JOBS, job), self.keys("week"))

    def test_check_2_garden_mark_done_sets_done_and_makes_no_new_job(self):
        job = self.store.create(GARDEN, {"title": "Water seedlings", "due_on": self.day(), "done": False})
        self.assertIn((GARDEN, job), self.keys())
        client = self.client()
        html = self.page(client, "/to-do")
        self.assertIn(f'action="/t/{GARDEN}/{job}/do/done"', html)
        response = client.post(f"/t/{GARDEN}/{job}/do/done", data={"_csrf": self.csrf, "back": "/to-do"},
                               base_url=BASE)
        self.assertEqual(response.headers["Location"], f"/to-do?table={GARDEN}&record={job}&pressed=done")
        self.assertIn("Marked as done.", self.page(client, response.headers["Location"]))
        self.assertTrue(self.store.get(GARDEN, job)["done"])
        self.assertNotIn((GARDEN, job), self.keys("year"))
        self.assertNotIn(GARDEN, [i.table for i in watch.expiring(self.conn, self.registry, self.today)])
        self.assertEqual(self.store.count(GARDEN), 1)  # still in its history, and no job for next week
        # Pressed again from an old page: nothing changes, and Things to do says so in its own words.
        stale = client.post(f"/t/{GARDEN}/{job}/do/done", data={"_csrf": self.csrf, "back": "/to-do"},
                            base_url=BASE)
        self.assertEqual(stale.headers["Location"], "/to-do?changed=1")
        self.assertIn("This task changed while you were looking at it. Check the current date and try again. "
                      "Nothing was saved.", self.page(client, stale.headers["Location"]))

    def test_check_3_alarm_check_opens_its_record_and_is_never_ticked(self):
        alarm = self.store.create(EQUIPMENT, {"name": "Hall smoke alarm", "kind": "smoke_alarm",
                                              "place": self.place, "next_check": self.day()})
        client = self.client()
        html = self.page(client, "/to-do")
        self.assertIn(f'href="/t/{EQUIPMENT}/{alarm}" aria-label="Open record to update: Hall smoke alarm"', html)
        self.page(client, f"/t/{EQUIPMENT}/{alarm}")  # opened, not changed
        self.assertIn((EQUIPMENT, alarm), self.keys())
        self.assertIn(EQUIPMENT, [i.table for i in watch.expiring(self.conn, self.registry, self.today)])

    def test_check_4_new_routines_keep_their_repeat_and_one_open_date_and_save_once(self):
        made = {unit: self.routine(f"Every {unit}", 1, unit) for unit in ("days", "weeks", "months", "years")}
        for unit, rid in made.items():
            row = self.store.get(ROUTINES, rid)
            self.assertEqual((row["repeat_count"], row["repeat_unit"], row["next_due"]), (1, unit, self.day()))
            self.assertEqual(self.keys().count((ROUTINES, rid)), 1)
        client = self.client()
        rid = made["weeks"]
        form = self.page(client, f"/t/{ROUTINES}/{rid}/do/done?back=/to-do")
        offered = dates.show(self.day(7), dates.DAY_FIRST)
        self.assertIn(f"Use {offered} from your repeat", form)
        self.assertEqual(self.store.get(ROUTINES, rid)["next_due"], self.day())  # offered, not chosen
        with self.assertRaises(records.ValidationError):  # no choice made: nothing happens without a person
            self.tick(rid, choice=None)
        op = actions.new_operation()
        first = self.tick(rid, op=op)
        second = self.tick(rid, op=op)  # a retry with the same one-use number
        self.assertEqual((first["repeated"], second["repeated"]), (False, True))
        self.assertEqual(self.store.count(TIMES), 1)
        self.assertEqual(self.store.get(ROUTINES, rid)["next_due"], self.day(7))
        done = self.store.page(TIMES)[0]
        self.assertEqual((done["outcome"], done["planned_for"], done["done_on"]), ("done", self.day(), self.day()))

    def test_check_5_a_missed_weekly_routine_is_one_calm_row_and_nothing_is_backfilled(self):
        rid = self.routine(due=-21)
        today_rows = [t for t in self.tasks() if t.row["id"] == rid]
        self.assertEqual(len(today_rows), 1)
        html = self.page(self.client(), "/to-do")
        self.assertEqual(html.count(f"Due since {dates.show(self.day(-21), dates.DAY_FIRST)}"), 1)
        for word in ("streak", "missed", "overdue", "penalty", "urgent", "%"):
            self.assertNotIn(word, re.sub(r"<style>.*?</style>", "", html, flags=re.S).lower(), word)
        skipped = self.tick(rid, "skip", choice="date", next_date=self.day(3))
        self.assertEqual(self.store.page(TIMES)[0]["outcome"], "skipped")
        self.assertEqual(self.store.get(ROUTINES, rid)["last_done"], None)  # a skip is not work done
        actions.undo(self.store, ROUTINES, rid, skipped["operation"])  # and it can be taken back
        self.assertEqual(self.store.get(ROUTINES, rid)["next_due"], self.day(-21))
        result = self.tick(rid)
        self.assertTrue(result["missed"])
        rows = [r for r in self.store.page(TIMES) if not r["deleted_at"]]
        self.assertEqual(len(rows), 1)  # one real completion, not three made-up ones
        self.assertEqual((rows[0]["planned_for"], rows[0]["done_on"]), (self.day(-21), self.day()))
        self.assertEqual(self.store.get(ROUTINES, rid)["next_due"], self.day(7))  # stepped on from the plan
        client = self.client()
        notice = self.page(client, f"/to-do?table={ROUTINES}&record={rid}&op={result['operation']}")
        self.assertIn("Earlier times were not recorded.", notice)

    def test_check_6_the_view_follows_current_records_and_modules(self):
        job = self.store.create(JOBS, {"name": "Clean the gutters", "kind": "gutters", "next_due": self.day()})
        rid = self.routine()
        self.store.update(JOBS, job, {"next_due": self.day(400)})
        self.assertNotIn((JOBS, job), self.keys("year"))
        self.store.update(JOBS, job, {"next_due": self.day()})
        self.assertIn((JOBS, job), self.keys())
        client = self.client()
        settings.set_module_enabled(self.conn, "home_care", False)
        html = self.page(client, "/to-do")
        self.assertNotIn("Clean the gutters", html)
        self.assertIn("Put the bins out", html)
        settings.set_module_enabled(self.conn, "home_care", True)
        self.assertIn("Clean the gutters", self.page(client, "/to-do"))
        result = self.tick(rid)
        start, end = checklist.bounds("week", self.today)
        self.assertEqual(len(checklist.done(self.conn, self.registry, start, end)), 1)
        before = self.conn.execute(f"SELECT next_due, last_done FROM {JOBS} WHERE id = ?", (job,)).fetchone()
        self.store.delete(ROUTINES, rid)
        self.assertNotIn((ROUTINES, rid), self.keys("year"))
        self.assertEqual(checklist.done(self.conn, self.registry, start, end), [])  # no stale tick survives
        self.store.restore(ROUTINES, rid)
        self.assertNotIn((ROUTINES, rid), self.keys("week"))  # its next date is after this week
        self.assertIn((ROUTINES, rid), self.keys("year"))
        self.assertEqual(tuple(before), tuple(self.conn.execute(f"SELECT next_due, last_done FROM {JOBS} "
                                                                f"WHERE id = ?", (job,)).fetchone()))
        self.assertTrue(result["operation"])

    def test_check_7_calendar_edges_follow_the_household(self):
        # 31 January monthly: 28 February, then back to 31 March, keeping the anchor day.
        self.assertEqual(dates.next_after("2027-01-31", 1, "months", "2027-01-31", 31), "2027-02-28")
        self.assertEqual(dates.next_after("2027-02-28", 1, "months", "2027-02-28", 31), "2027-03-31")
        self.assertEqual(dates.next_after("2028-01-31", 1, "months", "2028-01-31", 31), "2028-02-29")
        # 29 February yearly: 28 February in a common year, 29 again in the next leap year.
        self.assertEqual(dates.next_after("2028-02-29", 1, "years", "2028-02-29", 29), "2029-02-28")
        self.assertEqual(dates.next_after("2031-02-28", 1, "years", "2031-02-28", 29), "2032-02-29")
        # Daylight saving (Sydney 4 October 2026, New York 1 November 2026): one calendar day, no repeat.
        self.assertEqual(dates.add_period("2026-10-03", 1, "days"), "2026-10-04")
        self.assertEqual(dates.add_period("2026-10-31", 1, "days"), "2026-11-01")
        # Through the routine itself: the anchor comes from First date.
        rid = self.routine("Pay the strata levy", 1, "months", first_due="2027-01-31")
        self.store.update(ROUTINES, rid, {"next_due": "2027-02-28"})
        offered = actions.offer(actions.form_action(self.registry[ROUTINES], "done"),
                                self.store.get(ROUTINES, rid), "2027-02-28")
        self.assertEqual(offered, "2027-03-31")
        # Two week starts: Saturday 21 November 2026.
        saturday = date(2026, 11, 21)
        self.assertEqual(checklist.bounds("week", saturday, "monday"), (date(2026, 11, 16), date(2026, 11, 22)))
        self.assertEqual(checklist.bounds("week", saturday, "sunday"), (date(2026, 11, 15), date(2026, 11, 21)))
        self.assertEqual(checklist.bounds("week", saturday, "saturday"), (date(2026, 11, 21), date(2026, 11, 27)))
        self.assertEqual(checklist.bounds("month", date(2027, 2, 10)), (date(2027, 2, 1), date(2027, 2, 28)))
        self.assertEqual(week_range(date(2026, 11, 16), date(2026, 11, 22), dates.DAY_FIRST), "Mon 16–Sun 22 Nov")
        self.assertEqual(week_range(date(2026, 11, 30), date(2026, 12, 6), dates.DAY_FIRST),
                         "Mon 30 Nov–Sun 6 Dec")
        settings.put(self.conn, checklist.WEEK_START_KEY, "sunday")
        html = self.page(self.client(today=saturday), "/to-do/week")
        self.assertIn("Sun 15–Sat 21 Nov", html)
        self.assertIn("Your weeks start on Sunday", html)
        # A week starting on Sunday groups a Sunday-due task into this week, a Monday start into next week.
        due = self.routine("Sunday task", due=(date(2026, 11, 15) - self.today).days)
        self.assertIn((ROUTINES, due), [(t.source.info.name, t.row["id"]) for t in
                                        self.tasks("week", today=saturday, first_day="sunday") if t.group == "late"])
        # UTC and local midnight: a completion saved at 23:30 UTC the evening before is counted on its own day.
        self.store.clock = lambda: (self.today - timedelta(days=1)).isoformat() + "T23:30:00+00:00"
        rid2 = self.routine("Feed the fish", 1, "days")
        self.tick(rid2)
        on_day = checklist.done(self.conn, self.registry, self.today, self.today)
        self.assertEqual([d.record_id for d in on_day], [rid2])
        day_before = self.today - timedelta(days=1)
        self.assertEqual(checklist.done(self.conn, self.registry, day_before, day_before), [])

    def test_check_8_use_by_dates_and_questions_are_not_tasks_and_nothing_is_auto_ticked(self):
        item = self.store.create("stock__items", {"name": "Bottled water", "unit": "litres", "minimum": 4})
        lot = self.store.create("stock__lots", {"item": item, "quantity": 10, "expires": self.day()})
        names = {s.info.name for s in checklist.sources(self.registry)}
        self.assertNotIn("stock__lots", names)  # a use-by date is not a task
        self.assertTrue({JOBS, GARDEN, EQUIPMENT, ROUTINES} <= names)
        rid = self.routine("Check the water store")
        before = dict(self.store.get("stock__lots", lot))
        self.tick(rid)
        after = dict(self.store.get("stock__lots", lot))
        self.assertEqual(before, after)  # ticking a routine never moves or checks the stock it may mention

    def test_check_9_undo_restores_the_open_date_and_refuses_after_a_later_change(self):
        rid = self.routine(due=-2, last_done=self.day(-9))
        result = self.tick(rid)
        self.assertEqual(self.store.get(ROUTINES, rid)["next_due"], self.day(5))
        client = self.client()
        page = self.page(client, "/to-do/week")
        self.assertIn(f'action="/t/{ROUTINES}/{rid}/undo/{result["operation"]}"', page)
        response = client.post(f"/t/{ROUTINES}/{rid}/undo/{result['operation']}",
                               data={"_csrf": self.csrf, "back": "/to-do/week"}, base_url=BASE)
        self.assertTrue(response.headers["Location"].startswith("/to-do/week?"))
        row = self.store.get(ROUTINES, rid)
        self.assertEqual((row["next_due"], row["last_done"]), (self.day(-2), self.day(-9)))
        self.assertEqual(self.store.count(TIMES), 0)
        self.assertIn("Undone.", self.page(client, response.headers["Location"]))
        second = self.tick(rid)
        self.store.update(ROUTINES, rid, {"notes": "Green bin too"})  # a later change depends on the tick
        self.assertNotIn(f"/undo/{second['operation']}", self.page(client, "/to-do/week"))
        with self.assertRaises(ActionNotAvailable) as refused:
            actions.undo(self.store, ROUTINES, rid, second["operation"])
        self.assertEqual(str(refused.exception), "This routine has changed since that tick. Nothing was undone. "
                                                 "Check its dates and its Done or skipped list before changing them.")
        self.assertEqual(self.store.count(TIMES), 1)
        self.assertEqual(self.store.get(ROUTINES, rid)["notes"], "Green bin too")
        # Home care keeps its own Undo rules, reached from the same notice.
        job = self.store.create(JOBS, {"name": "Clean the gutters", "kind": "gutters", "next_due": self.day()})
        op = actions.complete(self.store, JOBS, job, "done", {"done_on": self.day()},
                              actions.revision(self.store, self.registry[JOBS], job), actions.new_operation(),
                              next_choice="none")["operation"]
        self.assertIn("Undo this completion", self.page(client, f"/to-do?table={JOBS}&record={job}&op={op}"))
        client.post(f"/t/{JOBS}/{job}/undo/{op}", data={"_csrf": self.csrf, "back": "/to-do"}, base_url=BASE)
        self.assertEqual(self.store.get(JOBS, job)["next_due"], self.day())

    def test_check_10_empty_views_make_no_claim_and_needs_attention_shares_the_same_reminder(self):
        client = self.client(today=self.today)
        for path, key in (("/to-do", "today"), ("/to-do/week", "week"), ("/to-do/month", "month"),
                          ("/to-do/year", "year")):
            html = self.page(client, path)
            self.assertIn(EMPTY[key], html)
            for claim in ("safe", "all done", "all caught up", "everything is done"):
                self.assertNotIn(claim, html.lower())
        self.assertIn("This does not mean every household task is done.", EMPTY["today"])
        undated = self.store.create(JOBS, {"name": "Service the heater", "kind": "heating_cooling"})
        self.assertNotIn((JOBS, undated), self.keys("year"))
        self.assertIn((JOBS, undated), self.keys("undated"))
        self.assertIn("Service the heater", self.page(client, "/to-do/no-date"))
        job = self.store.create(JOBS, {"name": "Clean the gutters", "kind": "gutters", "next_due": self.day()})
        attention = [(i.table, i.record_id) for i in watch.expiring(self.conn, self.registry, self.today)]
        self.assertEqual(attention, [(JOBS, job)])
        self.assertEqual(self.keys(), [(JOBS, job)])  # the same one record, not two states
        actions.complete(self.store, JOBS, job, "done", {"done_on": self.day()},
                         actions.revision(self.store, self.registry[JOBS], job), actions.new_operation(),
                         next_choice="none")
        self.assertEqual(watch.expiring(self.conn, self.registry, self.today), [])
        self.assertNotIn((JOBS, job), self.keys())

    def test_check_11_a_thousand_routines_and_ten_thousand_times_stay_quick_and_rows_keep_their_actions(self):
        now = "2026-01-01T00:00:00+00:00"
        rows = [(now, now, f"Routine {n}", 1, "weeks", self.day(-(n % 60) + 30), 1 if n % 10 == 0 else 0, f"g{n:05d}")
                for n in range(1000)]
        with db.transaction(self.conn):
            self.conn.executemany(f"INSERT INTO {ROUTINES} (created_at, updated_at, name, repeat_count, "
                                  f"repeat_unit, next_due, paused, global_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
            ids = [r[0] for r in self.conn.execute(f"SELECT id FROM {ROUTINES} ORDER BY id")]
            times, audit = [], []
            for n in range(10000):
                rid, on = ids[n % 1000], (self.today - timedelta(days=n % 700)).isoformat()
                times.append((now, now, rid, "done", on, on, f"t{n:05d}"))
            self.conn.executemany(f"INSERT INTO {TIMES} (created_at, updated_at, routine, outcome, planned_for, "
                                  f"done_on, global_id) VALUES (?, ?, ?, ?, ?, ?, ?)", times)
            added = [r[0] for r in self.conn.execute(f"SELECT id FROM {TIMES} ORDER BY id")]
            for n, time_id in enumerate(added):
                on = times[n][5]
                audit.append((on + "T08:00:00+00:00", "person", "action", ROUTINES, ids[n % 1000], json.dumps(
                    {"key": "done", "operation": f"op{n:05d}", "added_table": TIMES, "added": time_id,
                     "answers": {"done_on": on}, "counts_as": "done", "copied": {"planned_for": on}})))
            self.conn.executemany("INSERT INTO core__audit (at, actor, action, table_name, record_id, after) "
                                  "VALUES (?, ?, ?, ?, ?, ?)", audit)
        started = time.perf_counter()
        today_rows = self.tasks()
        took = time.perf_counter() - started
        self.assertLess(took, 2.0)
        self.assertTrue(today_rows)
        self.assertTrue(all(t.due <= self.today and not t.row["paused"] for t in today_rows))
        started = time.perf_counter()
        months = checklist.by_month(self.conn, self.registry, self.today.year)
        self.assertLess(time.perf_counter() - started, 5.0)
        self.assertEqual(len(months), 12)
        self.assertEqual(sum(m["done"] for m in months),
                         sum(1 for t in times if t[5][:4] == str(self.today.year)))
        html = self.page(self.client(), "/to-do")
        body = html.split("<h1>Things to do</h1>", 1)[1].split("</main>", 1)[0]
        self.assertNotIn("<script", body)  # every action is a link or a small form: no script needed
        first = body.index('class="todo-row')
        words, button = body.index("todo-when", first), body.index("Mark this occurrence done", first)
        self.assertLess(words, button)  # the date and source come before the button in reading order
        self.assertIn('aria-label="Mark this occurrence done: Routine', body)


class SwitchingAndHouseholds(ChecklistTestCase):
    def test_routines_switched_off_and_on(self):
        rid = self.routine()
        client = self.client()
        settings.set_module_enabled(self.conn, "routines", False)
        self.assertNotIn("Put the bins out", self.page(client, "/to-do"))
        self.assertEqual(client.get(f"/t/{ROUTINES}/{rid}/do/done", base_url=BASE).status_code, 404)
        settings.set_module_enabled(self.conn, "routines", True)
        self.assertIn("Put the bins out", self.page(client, "/to-do"))

    def test_nothing_switched_on_that_keeps_a_date(self):
        for name in ("home_layout", "home_care", "garden", "routines"):
            settings.set_module_enabled(self.conn, name, False)
        client = self.client()
        self.assertIn("None of the lists you track keep a due date yet", self.page(client, "/to-do"))
        self.assertNotIn('id="to-do"', self.page(client, "/"))

    def test_home_card_and_nav_link(self):
        self.routine(due=-1)
        self.routine("Water the pot plants", 1, "days")
        html = self.page(self.client(), "/")
        self.assertIn('<a href="/to-do">Things to do</a>', html)
        self.assertIn("2 due or late today", html)

    def test_settings_week_start(self):
        client = self.client()
        settings.put(self.conn, "household.country", "United States")
        self.assertEqual(checklist.week_start(self.conn), "sunday")
        page = self.page(client, "/settings")
        self.assertIn('id="week_starts"', page)
        settings.put(self.conn, checklist.WEEK_START_KEY, "monday")
        self.assertEqual(checklist.week_start(self.conn), "monday")
        settings.put(self.conn, checklist.WEEK_START_KEY, "someday")
        self.assertEqual(checklist.week_start(self.conn), "sunday")

    def test_back_goes_only_to_things_to_do(self):
        rid = self.routine()
        client = self.client()
        form = self.page(client, f"/t/{ROUTINES}/{rid}/do/done?back=https://example.com/")
        self.assertNotIn('name="back"', form)
        response = client.post(f"/t/{ROUTINES}/{rid}/do/done", data={
            "_csrf": self.csrf, "done_on": dates.show(self.day(), dates.DAY_FIRST), "next_choice": "repeat",
            "back": "//example.com/to-do", **self.form_fields(form)}, base_url=BASE)
        self.assertTrue(response.headers["Location"].startswith(f"/t/{ROUTINES}/{rid}"))

    def test_routines_module_rules(self):
        module = self.registry[ROUTINES].module
        self.assertEqual(module.requires, ["people", "stock"])
        self.assertFalse([c for t in module.tables.values() for c in t.columns.values() if c.sensitive])
        done, skip = (actions.form_action(self.registry[ROUTINES], k) for k in ("done", "skip"))
        self.assertEqual((done["counts_as"], skip["counts_as"]), ("done", "skipped"))
        self.assertEqual(skip["adds"]["values"], {"outcome": "skipped"})
        self.assertNotIn("into", skip["latest"])  # a skip never sets Last done

    def test_paused_routine_stays_out(self):
        rid = self.routine(due=-5)
        self.store.update(ROUTINES, rid, {"paused": True})
        self.assertNotIn((ROUTINES, rid), self.keys("year"))
        self.assertNotIn((ROUTINES, rid), self.keys("undated"))


class ExampleHouseholds(TempDirTestCase):
    PAGES = ("/", "/to-do", "/to-do/week", "/to-do/month", "/to-do/year", "/to-do/no-date")

    def load(self, household):
        import load_example
        data = self.tmp / household
        load_example.load(household, data)
        report = startup.prepare(data, ROOT / "modules")
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        app = create_app("t", lambda: None, report, data_dir=data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        return conn, records.build_registry(report.loaded), client

    def private_values(self, conn, registry):
        found = set()
        for name, info in registry.items():
            for column in info.table.columns.values():
                if column.sensitive and column.type != "links":
                    found |= {str(v[0]) for v in conn.execute(f"SELECT {column.name} FROM {name} WHERE "
                                                               f"{column.name} IS NOT NULL AND {column.name} != ''")
                              if len(str(v[0])) >= 4}
        return found

    def test_three_households_show_their_tasks_and_no_private_values(self):
        expected = {"smith": ["Put the bins out", "Water the pot plants"], "garcia": [], "taylor": []}
        for household, today_names in expected.items():
            with self.subTest(household):
                conn, registry, client = self.load(household)
                secrets = self.private_values(conn, registry)
                self.assertTrue(secrets, household)
                for path in self.PAGES:
                    response = client.get(path, base_url=BASE)
                    self.assertEqual(response.status_code, 200, path)
                    html = response.get_data(as_text=True)
                    for secret in secrets:
                        self.assertNotIn(secret, html, f"{household} {path}")
                today = [t.name for t in checklist.tasks(conn, registry, "today", date.today(),
                                                         checklist.week_start(conn)) if t.group in ("late", "today")]
                self.assertEqual(sorted(n for n in today if n in {"Put the bins out", "Water the pot plants",
                                                                     "Sort the recycling",
                                                                     "Water the windowsill herbs"}),
                                 sorted(today_names))

    def test_taylor_has_a_routine_with_no_date_yet(self):
        conn, registry, client = self.load("taylor")
        self.assertIn("Defrost the freezer", [t.name for t in checklist.tasks(conn, registry, "undated", date.today())])
        self.assertIn("Defrost the freezer", client.get("/to-do/no-date", base_url=BASE).get_data(as_text=True))


class SyncAndExport(ChecklistTestCase):
    def test_routines_get_permanent_ids_change_lines_and_travel_rules(self):
        rid = self.routine()
        self.tick(rid)
        self.assertEqual(sync.check(self.conn, self.registry), [])
        for name in (ROUTINES, TIMES):
            self.assertTrue(sync.has_identity(self.conn, name))
        logged = {c["table_name"] for c in sync.changes(self.conn)}
        self.assertTrue({ROUTINES, TIMES} <= logged)

    def test_looking_at_things_to_do_writes_nothing(self):
        self.routine(due=-3)
        self.store.create(JOBS, {"name": "Clean the gutters", "kind": "gutters", "next_due": self.day()})
        client = self.client()
        counts = lambda: [self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: E731
                          for t in ("core__audit", "core__sync_changes", ROUTINES, TIMES, JOBS, WORK)]
        before = counts()
        for path in ("/to-do", "/to-do/week", "/to-do/month", "/to-do/year", "/to-do/no-date", "/"):
            self.page(client, path)
        self.assertEqual(counts(), before)

    def test_export_has_routines_and_nothing_extra(self):
        rid = self.routine()
        self.tick(rid)
        data = export.build(self.conn, self.registry, "test")
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        self.assertIn(f"{ROUTINES}.csv", names)
        self.assertIn(f"{TIMES}.csv", names)
        self.assertFalse([n for n in names if "checklist" in n or "to_do" in n])
