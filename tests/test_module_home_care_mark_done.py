"""Tests for Home care's Mark done: Lane B's 16 acceptance checks, with invented Smith, Garcia and Taylor households (decision 0091)."""
import html
import re
import shutil
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import actions, dates, db, records, settings, startup, watch
from dashboard.web.app import create_app

PORT = 5134
BASE = f"http://127.0.0.1:{PORT}"
JOBS, WORK = "home_care__jobs", "home_care__work_done"
STALE = "This job changed while you were marking it done. Check its dates and try again. Nothing was saved."
UNDO_REFUSED = ("This job has changed since that completion. Nothing was undone. Check the job dates and Work done "
                "history before changing them.")


class MarkDoneBase(TempDirTestCase):
    """A household with John Smith and his gutters job, last done 120 days ago and due in 10 days."""
    MODULES = ("people", "stock", "home_layout", "home_care")

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
        self.records = records.Records(self.conn, self.registry)
        self.today = date.today()
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", "Australia")
        self.app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)
        self.john = self.records.create("people__people", {"name": "John Smith"})
        self.gutters = self.job("Clean the gutters", who_does_it=self.john, last_done=self.day(-120),
                                next_due=self.day(10))

    # ----- helpers -------------------------------------------------------------------------------
    def day(self, offset: int) -> str:
        return (self.today + timedelta(days=offset)).isoformat()

    def shown(self, stored: str) -> str:
        return dates.show(stored, dates.household_style(self.conn))

    def job(self, name, **values):
        return self.records.create(JOBS, {"name": name, "kind": "gutters", **values})

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def post(self, path, data):
        return self.client.post(path, data=dict(data, _csrf=self.app.config["CSRF_TOKEN"]), base_url=BASE)

    def open_form(self, job=None):
        page = self.get(f"/t/{JOBS}/{job or self.gutters}/do/done").get_data(as_text=True)
        op = re.search(r'name="operation" value="([^"]+)"', page).group(1)
        rev = re.search(r'name="revision" value="(\d+)"', page).group(1)
        return page, {"operation": op, "revision": rev}

    def save(self, form, job=None, **fields):
        body = dict(form, done_on=self.shown(self.day(0)), done_by="", notes="")
        body.update(fields)
        return self.post(f"/t/{JOBS}/{job or self.gutters}/do/done", body)

    def jobrow(self, job=None):
        return self.records.get(JOBS, job or self.gutters)

    def work(self, job=None):
        return [dict(r) for r in self.conn.execute(f"SELECT * FROM {WORK} WHERE job = ? AND deleted_at IS NULL",
                                                   (job or self.gutters,))]

    def audits(self, kind):
        return self.conn.execute("SELECT COUNT(*) FROM core__audit WHERE action = ?", (kind,)).fetchone()[0]

    def due(self):
        return {i.name: i.detail for i in watch.expiring(self.conn, self.registry, self.today)
                if i.table.startswith("home_care__")}

    def text(self, response):
        return html.unescape(response.get_data(as_text=True))


class MarkDoneTests(MarkDoneBase):
    """Lane B's acceptance checks, through the screens."""

    # ----- 1. Entry --------------------------------------------------------------------------------
    def test_1_each_live_job_offers_mark_done_and_cancelling_changes_nothing(self):
        page = self.text(self.get(f"/t/{JOBS}/{self.gutters}"))
        self.assertIn(f'href="/t/{JOBS}/{self.gutters}/do/done"', page)
        self.assertIn("Mark done", page)
        self.assertIn("Add an older Work done entry (does not change the job dates)", page)
        before = self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
        form, _ = self.open_form()
        self.assertIn("Mark “Clean the gutters” done", html.unescape(form))
        self.assertIn("Nothing changes until you save.", form)
        self.assertIn(f'href="/t/{JOBS}/{self.gutters}">Cancel</a>', form)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0], before)
        self.assertEqual(self.work(), [])
        self.records.delete(JOBS, self.gutters)
        self.assertNotIn("/do/done", self.get(f"/t/{JOBS}/{self.gutters}").get_data(as_text=True))
        self.assertEqual(self.get(f"/t/{JOBS}/{self.gutters}/do/done").status_code, 404)

    # ----- 2. One save -----------------------------------------------------------------------------
    def test_2_one_save_adds_one_work_done_sets_both_dates_and_names_them(self):
        _, form = self.open_form()
        response = self.save(form, next_choice="date", next_date=self.shown(self.day(90)))
        self.assertEqual(response.status_code, 302)
        work = self.work()
        self.assertEqual(len(work), 1)
        self.assertEqual(work[0]["done_on"], self.day(0))
        job = self.jobrow()
        self.assertEqual((job["last_done"], job["next_due"]), (self.day(0), self.day(90)))
        self.assertEqual(self.audits("action"), 1)
        page = self.text(self.client.get(response.headers["Location"], base_url=BASE))
        self.assertIn(f"Marked done on {self.shown(self.day(0))}. Work done was saved. "
                      f"Do again by {self.shown(self.day(90))}.", page)
        self.assertIn("used Mark done: added Clean the gutters, done", page)  # history names the completion

    # ----- 3. Actual person ------------------------------------------------------------------------
    def test_3_who_did_it_starts_blank_and_never_changes_who_usually_does_it(self):
        form_page, form = self.open_form()
        chooser = re.search(r'<select id="f-done_by".*?</select>', form_page, re.S).group(0)
        self.assertNotIn("selected", chooser)  # John usually does it, but is not guessed
        self.assertIn("Who did it (optional)", form_page)
        self.save(form, done_by=str(self.john), next_choice="none")
        self.assertEqual(self.work()[0]["done_by"], self.john)
        self.assertEqual(self.jobrow()["who_does_it"], self.john)
        other = self.job("Prune the hedge", kind="outside", who_does_it=self.john)
        _, form = self.open_form(other)
        self.save(form, job=other, next_choice="none")
        self.assertIsNone(self.work(other)[0]["done_by"])

    # ----- 4. Deliberate next date -----------------------------------------------------------------
    def test_4_the_next_date_is_chosen_on_purpose_and_no_date_yet_clears_the_reminder(self):
        page, form = self.open_form()
        self.assertNotRegex(page, r'name="next_choice" value="\w+" checked')
        for body, words in (({}, "Choose one: a date, or No date yet."),
                            ({"next_choice": "date"}, "Do again by is needed when you choose a date.")):
            response = self.save(form, **body)
            self.assertEqual(response.status_code, 422)
            self.assertIn(words, self.text(response))
        self.assertEqual(self.work(), [])
        self.assertEqual(self.jobrow()["next_due"], self.day(10))
        self.assertIn("Clean the gutters", self.due())
        self.save(form, next_choice="none")
        self.assertIsNone(self.jobrow()["next_due"])
        self.assertNotIn("Clean the gutters", self.due())

    # ----- 5. Repeat offer -------------------------------------------------------------------------
    def test_5_a_household_repeat_offers_one_date_and_a_chosen_date_overrides_it_once(self):
        page, _ = self.open_form()
        self.assertNotIn('value="repeat"', page)  # no repeat, no calculated date
        self.records.update(JOBS, self.gutters, {"repeat_count": 3, "repeat_unit": "months"})
        action = actions.form_action(self.registry[JOBS], "done")
        self.assertEqual(actions.offer(action, self.jobrow(), "2026-11-19"), "2027-02-19")
        self.assertEqual(actions.offer(action, self.jobrow(), "2026-11-30"), "2027-02-28")  # follows Done on
        page, form = self.open_form()
        offered = self.shown(dates.add_period(self.day(0), 3, "months"))
        self.assertIn(f"Use {offered} from your repeat", page)
        self.assertNotIn('value="repeat" checked', page)  # offered, never chosen for them
        self.assertEqual(self.jobrow()["next_due"], self.day(10))  # nothing saved by offering
        done_on = self.day(-1)
        self.save(form, done_on=self.shown(done_on), next_choice="repeat")
        self.assertEqual(self.jobrow()["next_due"], dates.add_period(done_on, 3, "months"))  # worked out again
        _, form = self.open_form()
        self.save(form, next_choice="date", next_date=self.shown(self.day(30)))
        job = self.jobrow()
        self.assertEqual((job["next_due"], job["repeat_count"], job["repeat_unit"]), (self.day(30), 3, "months"))

    # ----- 6. Calendar edges -----------------------------------------------------------------------
    def test_6_calendar_edges(self):
        for start, count, unit, expected in (("2027-01-31", 1, "months", "2027-02-28"),
                                             ("2028-01-31", 1, "months", "2028-02-29"),
                                             ("2028-02-29", 1, "years", "2029-02-28"),
                                             ("2026-12-15", 1, "months", "2027-01-15"),
                                             ("2026-12-28", 1, "weeks", "2027-01-04"),
                                             ("2026-11-19", 2, "weeks", "2026-12-03")):
            self.assertEqual(dates.add_period(start, count, unit), expected, (start, count, unit))
        self.assertEqual(dates.add_period(date(2026, 3, 29), 1, "weeks"), "2026-04-05")  # date only: no clock shift

    # ----- 7. Date order ---------------------------------------------------------------------------
    def test_7_dates_follow_the_household_order_and_their_rules(self):
        _, form = self.open_form()
        response = self.save(form, next_choice="date", next_date="31/04/27")
        self.assertIn("Enter a real date in DD/MM/YY format.", self.text(response))
        response = self.save(form, next_choice="date", next_date=self.shown(self.day(-1)))
        self.assertIn("Do again by can't be before Done on.", self.text(response))
        response = self.save(form, done_on=self.shown(self.day(1)), next_choice="none")
        self.assertIn("Done on can't be after today.", self.text(response))
        self.assertEqual(self.work(), [])
        self.save(form, next_choice="date", next_date=self.shown(self.day(0)))  # the same day is fine
        self.assertEqual(self.jobrow()["next_due"], self.day(0))
        settings.put(self.conn, "household.country", "United States")
        page, form = self.open_form(self.job("Air conditioner filter", kind="heating_cooling"))
        self.assertIn('data-date-style="mdy"', page)
        self.assertIn("Month / day / year (MM/DD/YY)", page)

    def test_7_a_next_date_already_passed_is_explained_and_kept_on_the_second_save(self):
        _, form = self.open_form()
        body = dict(done_on=self.shown(self.day(-10)), next_choice="date", next_date=self.shown(self.day(-5)))
        response = self.save(form, **body)
        page = self.text(response)
        self.assertIn("This date has passed, so the job will appear as overdue.", page)
        self.assertEqual(self.work(), [])
        past_ok = re.search(r'name="past_ok" value="([^"]+)"', page).group(1)
        self.assertEqual(self.save(form, past_ok=past_ok, **body).status_code, 302)
        self.assertEqual(self.jobrow()["next_due"], self.day(-5))
        self.assertIn("overdue", self.due()["Clean the gutters"])

    # ----- 8. Older work ---------------------------------------------------------------------------
    def test_8_older_work_is_refused_here_and_the_ordinary_form_leaves_dates_alone(self):
        _, form = self.open_form()
        response = self.save(form, done_on=self.shown(self.day(-200)), next_choice="none")
        page = self.text(response)
        self.assertIn(f"Done on can't be before Last done ({self.shown(self.day(-120))})", page)
        self.assertIn(f'href="/t/{WORK}/new?job={self.gutters}"', page)
        self.assertEqual(self.work(), [])
        before = self.jobrow()
        self.records.create(WORK, {"job": self.gutters, "done_on": self.day(-200)})
        after = self.jobrow()
        self.assertEqual((after["last_done"], after["next_due"]), (before["last_done"], before["next_due"]))

    # ----- 9. Reminders and sheet ------------------------------------------------------------------
    def test_9_reminders_and_the_sheet_read_the_new_dates_and_never_the_notes(self):
        self.assertIn("job due", self.due()["Clean the gutters"])
        sheet = self.text(self.get("/sheet/home_care/home_care"))
        self.assertIn(self.shown(self.day(10)), sheet)
        _, form = self.open_form()
        self.assertIn(self.shown(self.day(10)), self.text(self.get("/sheet/home_care/home_care")))  # opening: no change
        self.save(form, done_by=str(self.john), notes="Cleared the back gutter", next_choice="date",
                  next_date=self.shown(self.day(200)))
        self.assertNotIn("Clean the gutters", self.due())  # 200 days away: no reminder yet
        sheet = self.text(self.get("/sheet/home_care/home_care"))
        self.assertIn(self.shown(self.day(200)), sheet)
        self.assertIn(self.shown(self.day(0)), sheet)
        self.assertNotIn("Cleared the back gutter", sheet)
        self.assertNotIn("Who did it", sheet)

    # ----- 10. Retry -------------------------------------------------------------------------------
    def test_10_a_double_click_or_retry_saves_once_and_returns_the_same_completion(self):
        _, form = self.open_form()
        body = dict(next_choice="date", next_date=self.shown(self.day(60)))
        first, second = self.save(form, **body), self.save(form, **body)
        self.assertEqual(first.headers["Location"], second.headers["Location"])
        third = self.save(form, next_choice="none")  # a changed body with the same one-use number
        self.assertEqual(third.headers["Location"], first.headers["Location"])
        self.assertEqual(len(self.work()), 1)
        self.assertEqual(self.audits("action"), 1)
        self.assertEqual(self.jobrow()["next_due"], self.day(60))
        changes = self.conn.execute("SELECT COUNT(*) FROM core__audit WHERE action = 'update' AND table_name = ? "
                                    "AND record_id = ?", (JOBS, self.gutters)).fetchone()[0]
        self.assertEqual(changes, 1)

    # ----- 11. Stale form --------------------------------------------------------------------------
    def test_11_a_form_left_open_while_the_job_changed_saves_nothing(self):
        _, first = self.open_form()
        _, second = self.open_form()
        self.save(first, next_choice="date", next_date=self.shown(self.day(30)))
        response = self.save(second, next_choice="date", next_date=self.shown(self.day(45)))
        self.assertEqual(response.status_code, 409)
        page = self.text(response)
        self.assertIn(STALE, page)
        self.assertIn(self.shown(self.day(45)), page)  # what was typed is kept for review
        self.assertEqual(len(self.work()), 1)
        self.assertEqual(self.jobrow()["next_due"], self.day(30))
        other = self.job("Hot water system service", kind="water_heater")
        _, form = self.open_form(other)
        self.records.update(JOBS, other, {"notes": "Changed in another window"})
        response = self.save(form, job=other, next_choice="none")
        self.assertIn(STALE, self.text(response))
        self.assertEqual(self.work(other), [])

    # ----- 12. Bad link or deletion ----------------------------------------------------------------
    def test_12_a_bad_person_deleted_job_or_switched_off_module_leaves_nothing_half_saved(self):
        _, form = self.open_form()
        for person in ("99999", "not a number"):
            response = self.save(form, done_by=person, next_choice="none")
            self.assertEqual(response.status_code, 422)
        gone = self.records.create("people__people", {"name": "Example Gutters"})
        self.records.delete("people__people", gone)
        self.assertEqual(self.save(form, done_by=str(gone), next_choice="none").status_code, 422)
        self.assertEqual((self.work(), self.jobrow()["next_due"]), ([], self.day(10)))
        self.records.delete(JOBS, self.gutters)
        self.assertEqual(self.save(form, next_choice="none").status_code, 404)
        self.records.restore(JOBS, self.gutters)
        self.assertEqual((self.work(), self.audits("action")), ([], 0))  # restoring replays nothing
        settings.set_module_enabled(self.conn, "home_care", False)
        self.assertEqual(self.save(form, next_choice="none").status_code, 404)
        self.assertEqual(self.work(), [])

    # ----- 13. Same-day duplicate ------------------------------------------------------------------
    def test_13_a_second_completion_on_the_same_day_warns_instead_of_duplicating(self):
        _, form = self.open_form()
        self.save(form, next_choice="none")
        page, form = self.open_form()
        words = f"Work done is already recorded for this job on {self.shown(self.day(0))}. Add an older Work done " \
                f"entry if you need another note."
        self.assertIn(words, page)
        self.assertIn(words, self.text(self.save(form, next_choice="none")))
        self.assertEqual(len(self.work()), 1)
        self.records.create(WORK, {"job": self.gutters, "done_on": self.day(0), "notes": "Second note"})
        self.assertEqual(len(self.work()), 2)  # the separate history form still allows it

    # ----- 14. Undo succeeds -----------------------------------------------------------------------
    def test_14_undo_removes_only_that_work_done_and_puts_the_dates_back(self):
        before = self.jobrow()
        _, form = self.open_form()
        done = self.save(form, next_choice="date", next_date=self.shown(self.day(300)))
        self.assertNotIn("Clean the gutters", self.due())
        page = self.text(self.client.get(done.headers["Location"], base_url=BASE))
        undo = re.search(r'action="(/t/[^"]+/undo/[^"]+)"', page).group(1)
        self.assertIn("Undo this completion", page)
        response = self.post(undo, {})
        self.assertEqual(response.status_code, 302)
        job = self.jobrow()
        self.assertEqual((job["last_done"], job["next_due"]), (before["last_done"], before["next_due"]))
        self.assertEqual(self.work(), [])
        self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {WORK}").fetchone()[0], 1)  # kept, deleted
        self.assertIn("Clean the gutters", self.due())  # the old reminder is back
        self.assertEqual((self.audits("action"), self.audits("undo")), (1, 1))
        after = self.text(self.client.get(response.headers["Location"], base_url=BASE))
        self.assertIn("Undone. The work done entry was removed, and Last done and Do again by are back", after)
        self.assertIn("undid Mark done: removed Clean the gutters, done", after)
        self.assertNotIn("/undo/", after)

    # ----- 15. Undo refuses a conflict -------------------------------------------------------------
    def test_15_undo_refuses_after_any_later_change_and_a_second_click_changes_nothing(self):
        def complete(job, **body):
            _, form = self.open_form(job)
            response = self.save(form, job=job, **body)
            return re.search(r"op=([^&]+)", response.headers["Location"]).group(1)

        edited_job = complete(self.gutters, next_choice="none")
        self.records.update(JOBS, self.gutters, {"notes": "Edited afterwards"})
        hedge = self.job("Prune the hedge", kind="outside")
        edited_work = complete(hedge, next_choice="none")
        self.records.update(WORK, self.work(hedge)[0]["id"], {"notes": "Edited afterwards"})
        boiler = self.job("Boiler service", kind="water_heater", last_done=self.day(-30))
        older = complete(boiler, done_on=self.shown(self.day(-1)), next_choice="none")
        complete(boiler, next_choice="none")  # a later completion
        for job, op in ((self.gutters, edited_job), (hedge, edited_work), (boiler, older)):
            before = self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
            response = self.post(f"/t/{JOBS}/{job}/undo/{op}", {})
            self.assertEqual(response.status_code, 409)
            self.assertIn(UNDO_REFUSED, self.text(response))
            self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0], before)
        filter_job = self.job("Air conditioner filter", kind="heating_cooling")
        op = complete(filter_job, next_choice="none")
        self.assertEqual(self.post(f"/t/{JOBS}/{filter_job}/undo/{op}", {}).status_code, 302)
        _, form = self.open_form(filter_job)  # new unrelated work after the Undo
        self.save(form, job=filter_job, next_choice="date", next_date=self.shown(self.day(5)))
        again = self.post(f"/t/{JOBS}/{filter_job}/undo/{op}", {})
        self.assertEqual(again.status_code, 409)
        self.assertIn("That was already undone. Nothing was changed.", self.text(again))
        self.assertEqual((len(self.work(filter_job)), self.jobrow(filter_job)["next_due"]), (1, self.day(5)))

    # ----- 16. Invented examples and privacy -------------------------------------------------------
    def test_16_garcia_types_a_us_date_taylor_chooses_no_date_and_nothing_is_advice(self):
        settings.put(self.conn, "household.country", "United States")
        carlos = self.records.create("people__people", {"name": "Carlos Garcia"})
        garcia = self.job("Air conditioner filter", kind="heating_cooling", next_due=self.day(5))
        _, form = self.open_form(garcia)
        later = self.today + timedelta(days=56)
        self.save(form, job=garcia, done_on=f"{self.today:%m/%d/%y}", done_by=str(carlos), next_choice="date",
                  next_date=f"{later:%m/%d/%y}")
        self.assertEqual(self.jobrow(garcia)["next_due"], later.isoformat())
        settings.put(self.conn, "household.country", "United Kingdom")
        taylor = self.job("Boiler service", kind="water_heater", next_due=self.day(3))
        page, form = self.open_form(taylor)
        self.assertIn("Do not include alarm or access codes.", page)
        self.save(form, job=taylor, next_choice="none")
        self.assertIsNone(self.jobrow(taylor)["next_due"])
        edit = self.text(self.get(f"/t/{JOBS}/new"))
        self.assertIn("This is your own choice, not a maintenance schedule.", edit)
        self.assertNotIn("home_layout", page)


class MarkDoneCoreTests(MarkDoneBase):
    """The same operation without the screens, on fixed invented dates (Smith, 19/11/26)."""

    def complete(self, job=None, today=date(2026, 11, 19), **values):
        info = self.registry[JOBS]
        job = job or self.gutters
        answers = {"done_on": values.pop("done_on", "2026-11-19"), "done_by": values.pop("done_by", None),
                   "notes": values.pop("notes", None)}
        return actions.complete(self.records, JOBS, job, "done", answers, actions.revision(self.records, info, job),
                                values.pop("op", actions.new_operation()), today=today, **values)

    def test_smith_repeat_of_three_months_offers_19_02_27(self):
        self.records.update(JOBS, self.gutters, {"last_done": "2026-08-01", "next_due": "2026-12-01",
                                                 "repeat_count": 3, "repeat_unit": "months"})
        result = self.complete(done_by=self.john, next_choice="repeat")
        self.assertEqual(result["after"], {"last_done": "2026-11-19", "next_due": "2027-02-19"})
        self.assertEqual(result["before"], {"last_done": "2026-08-01", "next_due": "2026-12-01"})
        self.assertFalse(result["repeated"])

    def test_a_next_date_already_passed_is_explained_before_saving(self):
        self.records.update(JOBS, self.gutters, {"last_done": "2026-01-01"})
        with self.assertRaises(records.ValidationError) as caught:
            self.complete(done_on="2026-10-01", next_choice="date", next_date="2026-11-01")
        self.assertEqual(caught.exception.problems,
                         {"_past": "This date has passed, so the job will appear as overdue. Save again to keep it."})
        self.assertEqual(self.work(), [])
        self.complete(done_on="2026-10-01", next_choice="date", next_date="2026-11-01", past_ok="2026-11-01")
        self.assertEqual(self.jobrow()["next_due"], "2026-11-01")

    def test_a_missing_or_reused_operation_number_saves_nothing(self):
        with self.assertRaises(records.ValidationError):
            self.complete(op="short", next_choice="none")
        op = actions.new_operation()
        self.complete(op=op, next_choice="none")
        other = self.job("Prune the hedge", kind="outside")
        with self.assertRaises(records.ActionNotAvailable):
            self.complete(job=other, op=op, next_choice="none")
        self.assertEqual(self.work(other), [])

    def test_a_job_with_no_repeat_cannot_use_one(self):
        with self.assertRaises(records.ValidationError) as caught:
            self.complete(next_choice="repeat")
        self.assertIn("There is no repeat to use", caught.exception.problems["_next"])


if __name__ == "__main__":  # pragma: no cover
    import unittest
    unittest.main()
