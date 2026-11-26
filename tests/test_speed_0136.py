"""Tests for the speed work (decision 0136): faster reads give exactly the answers the full reads gave, and pages stay within loose query limits."""
import json
import sqlite3
import unittest
from datetime import date, timedelta

from support import TempDirTestCase
import time_pages
from dashboard.core import calendars, daily, db, records, settings, startup, timeline


def reference_history(conn, info, column, zone):
    """The history reader as it was before decision 0136: every line of the table, each one read in full."""
    values, last, waiting, belongs = {}, {}, {}, {}
    for row in conn.execute("SELECT record_id, at, action, after FROM core__audit WHERE table_name = ? "
                            "AND action IN ('create', 'update', 'action', 'undo') ORDER BY id", (info.name,)):
        record_id, action = row["record_id"], row["action"]
        try:
            after = json.loads(row["after"]) if row["after"] else {}
        except ValueError:
            after = {}
        after = after if isinstance(after, dict) else {}
        saved_value = None
        if action in ("create", "update"):
            if column in after:
                try:
                    saved = daily.local_day(row["at"], zone)
                except (TypeError, ValueError):
                    saved = None
                if saved is not None:
                    values.setdefault(record_id, []).append([calendars._as_day(after[column]), saved, False])
                    saved_value = len(values[record_id]) - 1
            press = waiting.get(record_id)
            if press is not None:
                if any(k in after and after[k] != v for k, v in press[1].items()):
                    del waiting[record_id]
                elif calendars._as_day(after.get(column)) is not None:
                    belongs[press[0]] = (record_id, calendars._as_day(after[column]))
                    del waiting[record_id]
        elif action == "undo":
            if last.get(record_id) is not None:
                values[record_id][last[record_id]][2] = True
            if record_id in waiting and waiting[record_id][0] == after.get("operation"):
                del waiting[record_id]
        else:
            fields = after.get("after") if isinstance(after.get("after"), dict) else {}
            if after.get("one_step") and column not in fields and after.get("operation"):
                waiting[record_id] = (after["operation"], fields)
            else:
                waiting.pop(record_id, None)
        last[record_id] = saved_value
    earlier = {}
    for record_id, held in values.items():
        for (before, saved, _), (after, moved, by_undo) in zip(held, held[1:]):
            if before is None or moved <= saved:
                continue
            if (after is None and not by_undo) or (after is not None and after > before):
                earlier.setdefault(record_id, set()).add(before)
    return earlier, belongs


def in_window(earlier, window):
    found = {r: {d for d in days if window[0] <= d <= window[1]} for r, days in earlier.items()}
    return {r: days for r, days in found.items() if days}


def shape(shown, earlier):
    """What a timeline page is made of: each line's table, day, entries and the entry it compares with."""
    return ([(i.info.name, i.day, [r["id"] for r in i.rows], (i.previous or {}).get("id")) for i in shown], earlier)


class SpeedCase(TempDirTestCase):
    """One small invented household with years of history, shared by the tests (a few seconds to build)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import tempfile
        from pathlib import Path
        cls._keep = tempfile.TemporaryDirectory()
        cls.root = Path(cls._keep.name)
        time_pages.build(cls.root / "data", cls.root / "modules", scale=0.12)

    @classmethod
    def tearDownClass(cls):
        cls._keep.cleanup()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.report = startup.prepare(self.root / "data", self.root / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.root / "data" / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.zone = daily.household_zone(self.conn)


class HistoryTests(SpeedCase):
    TABLES = ("vehicles__services", "garden__jobs", "home_layout__equipment", "lent_out__loans")

    def test_a_window_gives_the_same_earlier_days_as_reading_everything(self):
        windows = [(date(2026, 11, 1), date(2026, 11, 30)), (date(2026, 1, 1), date(2026, 3, 31)),
                   (date(2025, 12, 1), date(2026, 11, 30)), (date(2020, 1, 1), date(2030, 12, 31)),
                   (date(2031, 1, 1), date(2031, 2, 1))]
        found_any = False
        for name in self.TABLES:
            info = self.registry[name]
            column = info.table.calendar["when"]
            want_earlier, want_belongs = reference_history(self.conn, info, column, self.zone)
            self.assertEqual(calendars._history(self.conn, info, column, self.zone)[0], want_earlier, name)
            for window in windows:
                got_earlier, got_belongs = calendars._history(self.conn, info, column, self.zone, window)
                self.assertEqual(in_window(got_earlier, window), in_window(want_earlier, window), (name, window))
                self.assertEqual(got_belongs, want_belongs, (name, window))
                found_any = found_any or bool(in_window(want_earlier, window))
        self.assertTrue(found_any, "the household should have earlier done days to compare")

    def test_done_days_are_the_same_with_and_without_the_window(self):
        for name in self.TABLES:
            info = self.registry[name]
            column = info.table.calendar["when"]
            start, end = date(2025, 6, 1), date(2026, 6, 30)
            got = calendars.done_days(self.conn, self.registry, info, column, start, end)
            earlier, belongs = reference_history(self.conn, info, column, self.zone)
            self.assertEqual({(d.record_id, d.day) for d in got if d.kind == "earlier"},
                             {(r, d) for r, days in in_window(earlier, (start, end)).items() for d in days}
                             - {(d.record_id, d.day) for d in got if d.kind == "now"}, name)

    def test_a_record_never_held_a_date_in_the_window_is_left_out_not_misread(self):
        info = self.registry["vehicles__services"]
        earlier = calendars._history(self.conn, info, "last_done", self.zone,
                                     (date(2031, 1, 1), date(2031, 1, 31)))[0]
        self.assertEqual(earlier, {})


class TimelineTests(SpeedCase):
    SUBJECTS = ("pets__pets", "people__people", "vehicles__vehicles", "routines__routines", "home_care__jobs")

    def check(self, table, subject_id, before, limit):
        subject = self.registry[table]
        want = shape(*timeline.page(timeline.items(self.conn, self.registry, subject, subject_id), before, limit))
        lines, cut = timeline.window(self.conn, self.registry, subject, subject_id, before, limit)
        self.assertEqual(shape(*timeline.page(lines, before, limit, cut)), want, (table, subject_id, before, limit))
        return want

    def test_every_page_of_every_timeline_is_the_same(self):
        pages = 0
        for table in self.SUBJECTS:
            for (subject_id,) in self.conn.execute(f"SELECT id FROM {table} ORDER BY id LIMIT 2").fetchall():
                for limit in (timeline.PANEL, timeline.PAGE, 1):
                    before = None
                    for _ in range(40):
                        shown, earlier = self.check(table, subject_id, before, limit)
                        pages += 1
                        if earlier is None:
                            break
                        before = earlier
        self.assertGreater(pages, 100)

    def test_a_day_before_the_history_and_a_day_after_it(self):
        pet = self.conn.execute("SELECT MIN(id) FROM pets__pets").fetchone()[0]
        for before in (date(2000, 1, 1), date(2026, 6, 15), date(2030, 1, 1)):
            self.check("pets__pets", pet, before, timeline.PAGE)

    def test_times_written_with_an_offset_count_on_the_household_day(self):
        settings.put(self.conn, "household.timezone", "Pacific/Auckland")
        self.zone = daily.household_zone(self.conn)
        store = records.Records(self.conn, self.registry)
        pet = self.conn.execute("SELECT MIN(id) FROM pets__pets").fetchone()[0]
        made = []
        try:
            for stamp in ("2026-11-19T11:30:00+00:00", "2026-11-19T12:30:00+00:00", "2026-11-18T23:59:00+00:00",
                          "2026-11-20T00:00:00-10:00", "2026-10-31T11:00:00+00:00"):
                made.append(store.create("pet_feeding__servings", {"pet": pet, "given_at": stamp,
                                                                   "kind": "bowl", "food": "Example kibble"}))
            for limit in (timeline.PANEL, timeline.PAGE, 3):
                before = None
                for _ in range(8):
                    shown, earlier = self.check("pets__pets", pet, before, limit)
                    if earlier is None:
                        break
                    before = earlier
        finally:
            settings.put(self.conn, "household.timezone", "UTC")
            for record_id in made:
                self.conn.execute("DELETE FROM pet_feeding__servings WHERE id = ?", (record_id,))

    def test_a_long_history_reads_only_its_newest_rows(self):
        subject = self.registry["pets__pets"]
        pet = self.conn.execute("SELECT MIN(id) FROM pets__pets").fetchone()[0]
        everything = timeline.items(self.conn, self.registry, subject, pet)
        lines, cut = timeline.window(self.conn, self.registry, subject, pet, None, timeline.PAGE)
        self.assertTrue(cut)
        self.assertLess(len(lines), len(everything) // 2)


class QueryLimitTests(SpeedCase):
    """A loose ceiling on SQL statements per page, so a page that starts asking once for every record is noticed."""
    LIMITS = {"Home": 200, "Needs attention": 100, "Feeding calendar, this month": 30,
              "Vehicle services calendar": 150, "Things to do: Calendar, all lists": 200,
              "Feeding bars by month": 30, "Spent per month: after Show": 80, "Pet timeline, first page": 30,
              "Pet timeline, Earlier": 30, "Pet page with panels": 90, "Vehicle page with panels": 50}

    def test_pages_answer_within_their_query_limits(self):
        app, client, bucket = time_pages.client_for(self.root / "data", self.root / "modules")
        self.addCleanup(lambda: setattr(db, "connect", self._real_connect))
        conn = sqlite3.connect(self.root / "data" / "dashboard.db")
        conn.row_factory = sqlite3.Row
        self.addCleanup(conn.close)
        csrf = app.config["CSRF_TOKEN"]
        checked = 0
        for label, method, path in time_pages.pages(conn, app):
            bucket.clear()
            if method == "POST":
                response = client.post(path, base_url=time_pages.BASE, data={"_csrf": csrf})
            else:
                response = client.get(path, base_url=time_pages.BASE)
            self.assertEqual(response.status_code, 200, path)
            if label in self.LIMITS:
                checked += 1
                self.assertLessEqual(len(bucket), self.LIMITS[label], f"{label}: {len(bucket)} statements")
        self.assertEqual(checked, len(self.LIMITS))

    def setUp(self):
        super().setUp()
        self._real_connect = db.connect


if __name__ == "__main__":
    unittest.main()
