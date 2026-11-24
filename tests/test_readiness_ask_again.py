"""Tests for decision 0113: a confirmed Readiness answer comes back only when a field its question lists changed.

Lane B's field rules for the eight record-backed questions (workbench/drafts/readiness_review, now in git history),
drill steps that point at records, the upgrade from decision 0104's revision fingerprint, privacy, a module switched
off and a deleted record."""
import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timezone

from dashboard import __version__
from dashboard.core import drills, export, questions, settings, startup
from test_module_readiness import BASE, SECRET, TODAY, ReadinessTestCase


class AskAgainTestCase(ReadinessTestCase):
    def confirm(self, prompt_id, record_id=None):
        """Answer Yes with the offered record (the one with `record_id`, else the only one)."""
        found = self.state(prompt_id).candidates
        chosen = next(c for c in found if record_id is None or c.record_id == record_id)
        questions.save(self.store, self.prompt_set, prompt_id, "yes", record=chosen.key, today=TODAY)
        self.assertEqual(self.state(prompt_id).state, "looked_at", prompt_id)
        return chosen

    def quiet(self, prompt_id, what):
        q = self.state(prompt_id)
        self.assertEqual((q.state, q.review_reason), ("looked_at", None), f"{prompt_id}: {what}")

    def asks(self, prompt_id, what, reason="record_changed", again=True):
        q = self.state(prompt_id)
        self.assertEqual((q.state, q.review_reason), ("review", reason), f"{prompt_id}: {what}")
        if again:
            self.confirm(prompt_id)

    def edit(self, table, record_id, **values):
        self.store.update(table, record_id, values)


class EightQuestionTests(AskAgainTestCase):
    def test_first_aid_kit_ignores_its_check_dates_and_notes_and_asks_for_kept_place_and_path(self):
        kitchen = self.place("Kitchen")
        cupboard = self.place("Cupboard", inside=kitchen)
        hall = self.place("Hall")
        kit = self.store.create("medical__kits", {"name": "Kitchen kit", "kept": "home", "place": cupboard})
        self.confirm("medical-kit-location")
        self.edit("medical__kits", kit, last_checked="2026-11-01")
        self.edit("medical__kits", kit, next_check="2027-05-01")
        self.edit("medical__kits", kit, notes="Plasters restocked")
        self.store.create("medical__kit_checks", {"kit": kit, "checked_on": "2026-11-20", "next_check": "2027-05-20"})
        self.edit("stock__places", kitchen, notes="Tiles replaced")
        self.store.create("medical__kits", {"name": "Car kit", "kept": "vehicle", "place": hall})  # another kit
        self.quiet("medical-kit-location", "check dates, notes, kit checks, a place note and another kit")
        self.edit("medical__kits", kit, kept="vehicle")
        self.asks("medical-kit-location", "kept moved from home to a vehicle")
        self.edit("medical__kits", kit, place=hall)
        self.asks("medical-kit-location", "its place changed")
        self.edit("medical__kits", kit, place=cupboard)
        self.asks("medical-kit-location", "back in the cupboard")
        self.edit("stock__places", kitchen, name="Big kitchen")
        self.asks("medical-kit-location", "an ancestor place renamed")
        self.edit("stock__places", cupboard, inside=hall)
        self.asks("medical-kit-location", "the cupboard moved by its parent")
        self.edit("medical__kits", kit, name="First aid box")
        self.asks("medical-kit-location", "renamed", again=False)
        self.confirm("medical-kit-location", kit)
        self.edit("medical__kits", kit, place=None)
        self.asks("medical-kit-location", "no place: no longer offered", reason="record_missing", again=False)
        self.assertNotIn(kit, [c.record_id for c in self.state("medical-kit-location").candidates])

    def test_drinking_water_ignores_use_while_positive_and_asks_at_zero_and_for_item_changes(self):
        shelf = self.place("Garage shelf")
        item = self.store.create("stock__items", {"name": "Bottled water", "category": "water", "drinking": True,
                                                  "unit": "litres"})
        lot = self.store.create("stock__lots", {"item": item, "quantity": 6, "place": shelf})
        self.confirm("heat-heat-water")
        self.store.create("stock__movements", {"item": item, "reason": "used", "amount": 1, "lot": lot})
        self.store.create("stock__movements", {"item": item, "reason": "bought", "amount": 2, "lot": lot})
        self.store.create("stock__lots", {"item": item, "quantity": 10, "place": shelf})  # another lot
        self.edit("stock__items", item, unit="L")  # the same litre kind
        self.edit("stock__items", item, minimum=4, notes="Rotate in spring")
        self.edit("stock__lots", lot, expires="2027-08-01", notes="From the shop")
        self.quiet("heat-heat-water", "using, adding, another lot, unit spelling, minimum, notes and use-by")
        self.store.create("stock__movements", {"item": item, "reason": "used", "amount": 7, "lot": lot})
        self.asks("heat-heat-water", "its last litre used", reason="record_missing", again=False)
        self.store.create("stock__movements", {"item": item, "reason": "bought", "amount": 3, "lot": lot})
        self.asks("heat-heat-water", "a positive amount back does not clear it", again=False)
        self.store.create("stock__lots", {"item": item, "quantity": 1})  # an unrelated edit while it waits
        self.asks("heat-heat-water", "still waiting for a person", reason="record_changed", again=False)
        self.confirm("heat-heat-water", lot)
        self.edit("stock__items", item, unit="packs")
        self.asks("heat-heat-water", "unit no longer litres", reason="record_missing", again=False)
        self.edit("stock__items", item, unit="litre")
        self.asks("heat-heat-water", "undoing the unit does not clear it", again=False)
        self.confirm("heat-heat-water", lot)
        self.edit("stock__items", item, name="Spring water")
        self.asks("heat-heat-water", "item renamed", again=False)
        self.confirm("heat-heat-water", lot)
        self.edit("stock__items", item, drinking=False)
        self.asks("heat-heat-water", "no longer drinking water", reason="record_missing", again=False)

    def test_smoke_alarm_ignores_battery_next_check_and_notes_and_asks_for_tested_place_and_room(self):
        hall, landing = self.place("Hall"), self.place("Landing")
        nook = self.place("Ceiling", inside=hall)
        alarm = self.store.create("home_layout__equipment", {"name": "Hall alarm", "kind": "smoke_alarm",
                                                             "place": nook, "last_tested": "2026-10-01"})
        self.confirm("fire-alarm-location")
        self.edit("home_layout__equipment", alarm, battery_changed="2026-11-01", next_check="2027-02-01",
                  notes="Ten-year battery", access_details="Ladder in the shed")
        self.edit("stock__places", hall, notes="Painted")
        self.store.create("home_layout__equipment", {"name": "Bedroom alarm", "kind": "smoke_alarm", "place": landing,
                                                     "last_tested": "2026-10-01"})
        self.quiet("fire-alarm-location", "battery, next check, notes, access, a room note, a new alarm")
        self.edit("home_layout__equipment", alarm, last_tested="2026-11-15")
        self.asks("fire-alarm-location", "last tested")
        self.edit("stock__places", nook, inside=landing)
        self.asks("fire-alarm-location", "its place moved inside another room")
        self.edit("stock__places", landing, name="Upstairs landing")
        self.asks("fire-alarm-location", "an ancestor room renamed")

    def test_shut_off_ignores_private_access_details_and_meters_and_asks_for_how_to_find_kind_and_path(self):
        laundry = self.place("Laundry")
        tap = self.store.create("home_layout__shutoffs", {"name": "Main tap", "kind": "water", "place": laundry,
                                                          "how_to_find": "Behind the panel"})
        self.confirm("flood-flood-utilities")
        self.edit("home_layout__shutoffs", tap, access_details="Code 4821", notes="Stiff")
        self.store.create("home_layout__meters", {"name": "Water meter", "kind": "water", "place": laundry})
        self.quiet("flood-flood-utilities", "private access details, notes and a meter")
        client = self.client()
        for path in ("/", "/attention", "/questions/readiness", "/questions/readiness/flood-flood-utilities"):
            self.assertNotIn("4821", self.page(path, client), path)
        self.edit("home_layout__shutoffs", tap, how_to_find="Under the sink")
        self.asks("flood-flood-utilities", "how to find it")
        self.edit("home_layout__shutoffs", tap, kind="gas")
        self.asks("flood-flood-utilities", "its kind")
        self.edit("stock__places", laundry, name="Wash room")
        self.asks("flood-flood-utilities", "its place path")

    def private_detail(self, prompt_id, kind):
        alex = self.store.create("people__people", {"name": "Alex Example", "lives_here": True, "phone": "0491 570 101"})
        detail = self.store.create("people__important_info", {"person": alex, "kind": kind, "detail": SECRET})
        self.confirm(prompt_id)
        self.edit("people__people", alex, birthday="1990-01-01", phone="0491 570 102", notes="Prefers texts",
                  email="alex@example.org")
        self.store.create("people__important_info", {"person": alex, "kind": kind, "detail": "Another invented"})
        self.quiet(prompt_id, "birthday, phone, email, notes and another detail")
        self.edit("people__important_info", detail, detail=SECRET + " (changed)")
        self.asks(prompt_id, "the private detail changed")
        client = self.client()
        self.edit("people__important_info", detail, detail=SECRET + " (changed again)")
        for path in ("/", "/attention", "/questions/readiness", "/questions/readiness?show=review",
                     f"/questions/readiness/{prompt_id}", "/sheet/people/emergency", "/t/readiness__answers"):
            self.assertNotIn("Synthetic-medicine-name", self.page(path, client), path)
        self.confirm(prompt_id, detail)
        self.edit("people__people", alex, name="Alex Sample")
        self.asks(prompt_id, "the person renamed", again=False)
        self.confirm(prompt_id, detail)
        self.edit("people__people", alex, lives_here=False)
        self.asks(prompt_id, "no longer lives here", reason="record_missing", again=False)
        self.assertNotIn(detail, [c.record_id for c in self.state(prompt_id).candidates])

    def test_prescriptions_ask_only_for_the_detail_its_person_and_where_they_live(self):
        self.private_detail("medical-prescriptions", "medication")

    def test_special_food_asks_only_for_the_detail_its_person_and_where_they_live(self):
        self.private_detail("medical-special-food", "dietary")

    def contact(self, prompt_id, role, other_role):
        sam = self.person("Sam Example", lives_here=False, phone="0491 570 110")
        kim = self.person("Kim Example", lives_here=False, phone="0491 570 120")
        chosen = self.store.create("people__roles", {"person": sam, "role": role, "priority": 1})
        other = self.store.create("people__roles", {"person": kim, "role": role, "priority": 2})
        self.confirm(prompt_id, chosen)
        self.edit("people__people", sam, email="sam@example.org", birthday="1980-02-02",
                  address="1 Invented Street", notes="Works late")
        self.edit("people__roles", chosen, notes="Call after 6")
        self.edit("people__roles", other, priority=3)
        self.edit("people__people", kim, phone="0491 570 121")
        self.quiet(prompt_id, "email, birthday, address, notes, another contact's priority and phone")
        self.edit("people__people", sam, phone="0491 570 111")
        self.asks(prompt_id, "the chosen person's phone", again=False)
        self.confirm(prompt_id, chosen)
        self.edit("people__roles", chosen, priority=2)
        self.asks(prompt_id, "priority", again=False)
        self.confirm(prompt_id, chosen)
        self.edit("people__roles", chosen, role=other_role)
        self.asks(prompt_id, "role changed", reason="record_missing", again=False)
        self.edit("people__roles", chosen, role=role)
        self.asks(prompt_id, "role changed back does not clear it", again=False)
        self.confirm(prompt_id, chosen)
        self.store.delete("people__roles", chosen)
        q = self.state(prompt_id)
        self.assertEqual((q.state, q.review_reason), ("review", "record_missing"))
        self.assertEqual([c.record_id for c in q.candidates], [other])  # offered again, never swapped in
        self.assertEqual(q.answer["record"].split(":")[0], "people__roles")
        self.store.restore("people__roles", chosen)
        self.asks(prompt_id, "restored after a delete still asks", again=False)

    def test_care_contact_asks_for_role_person_priority_name_and_phone_only(self):
        self.contact("medical-care-contact", "doctor", "neighbour")

    def test_contact_after_leaving_asks_for_role_person_priority_name_and_phone_only(self):
        self.contact("leaving-contact-away", "emergency_contact", "family")

    def test_one_review_for_many_edits_and_answers_without_a_record_follow_only_their_date(self):
        kit = self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        self.confirm("medical-kit-location")
        for name in ("Kit 2", "Kit 3", "Kit 4"):
            self.edit("medical__kits", kit, name=name)
        self.edit("medical__kits", kit, name="Kit")  # back to the old value: still asks
        self.edit("medical__kits", kit, notes="Unrelated")
        self.asks("medical-kit-location", "several edits, one review", again=False)
        self.assertEqual(len([q for q in questions.next_up(self.conn, self.registry, 10, TODAY)
                              if q.prompt.id == "medical-kit-location"]), 1)
        for answer in ("not_yet", "not_relevant", "yes"):
            questions.save(self.store, self.prompt_set, "medical-kit-location", answer, review_on="2027-03-01",
                           today=TODAY)
            self.edit("medical__kits", kit, kept="vehicle" if answer != "not_relevant" else "home")
            self.store.create("medical__kits", {"name": f"New {answer}", "kept": "home", "place": self.place("Den")})
            self.quiet("medical-kit-location", f"{answer} with no record follows its date only")
        self.today = date(2027, 3, 1)
        self.asks("medical-kit-location", "its date arrived", reason="due", again=False)

    def test_a_confirmed_yes_still_comes_back_on_its_date_when_nothing_changed(self):
        self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        self.confirm("medical-kit-location")
        self.today = date(2027, 11, 21)
        self.asks("medical-kit-location", "twelve months later", reason="due", again=False)


class DrillStepTests(AskAgainTestCase):
    def step_answer(self, run_id, step_id):
        return drills.run_answers(self.conn, self.prompt_set, run_id)[step_id]

    def changed(self, run_id, step_id):
        return drills.record_changed(self.conn, self.registry, self.prompt_set, self.step_answer(run_id, step_id))

    def test_a_drill_step_asks_again_for_the_same_fields_only(self):
        laundry = self.place("Laundry")
        tap = self.store.create("home_layout__shutoffs", {"name": "Main tap", "kind": "water", "place": laundry})
        step = self.prompt_set.step("pipe-shutoff")
        key = questions.candidates(self.conn, self.registry, step)[0].key
        run_id = drills.start(self.store, self.prompt_set, "pipe-in-wall", today=TODAY)
        drills.save_step(self.store, self.prompt_set, run_id, "pipe-shutoff", "plan", record=key, today=TODAY)
        self.assertTrue(self.step_answer(run_id, "pipe-shutoff")["record_check"].startswith("2:"))
        self.edit("home_layout__shutoffs", tap, notes="Stiff", access_details="Code 4821")
        self.assertFalse(self.changed(run_id, "pipe-shutoff"))
        self.edit("home_layout__shutoffs", tap, how_to_find="Behind the washing machine")
        self.assertTrue(self.changed(run_id, "pipe-shutoff"))

    def test_a_shared_drill_step_and_its_question_agree(self):
        alarm = self.store.create("home_layout__equipment", {"name": "Hall alarm", "kind": "smoke_alarm",
                                                             "place": self.place("Hall"), "last_tested": "2026-10-01"})
        key = self.state("fire-alarm-location").candidates[0].key
        run_id = drills.start(self.store, self.prompt_set, "bedroom-fire-night", today=TODAY)
        drills.save_step(self.store, self.prompt_set, run_id, "fire-alarm-location", "plan", record=key, today=TODAY)
        self.edit("home_layout__equipment", alarm, battery_changed="2026-11-10", notes="New battery")
        self.assertFalse(self.changed(run_id, "fire-alarm-location"))
        self.quiet("fire-alarm-location", "battery and notes")
        self.edit("home_layout__equipment", alarm, last_tested="2026-11-15")
        self.assertTrue(self.changed(run_id, "fire-alarm-location"))
        self.asks("fire-alarm-location", "last tested", again=False)

    def test_water_stored_step_ignores_use_while_positive(self):
        item = self.store.create("stock__items", {"name": "Water", "category": "water", "drinking": True,
                                                  "unit": "l"})
        lot = self.store.create("stock__lots", {"item": item, "quantity": 4, "place": self.place("Shed")})
        step = self.prompt_set.step("water-stored")
        key = questions.candidates(self.conn, self.registry, step)[0].key
        run_id = drills.start(self.store, self.prompt_set, "water-warning", today=TODAY)
        drills.save_step(self.store, self.prompt_set, run_id, "water-stored", "plan", record=key, today=TODAY)
        self.store.create("stock__movements", {"item": item, "reason": "used", "amount": 1, "lot": lot})
        self.assertFalse(self.changed(run_id, "water-stored"))
        self.store.create("stock__movements", {"item": item, "reason": "used", "amount": 3, "lot": lot})
        self.assertTrue(self.changed(run_id, "water-stored"))
        self.store.create("stock__movements", {"item": item, "reason": "bought", "amount": 3, "lot": lot})
        self.assertTrue(self.changed(run_id, "water-stored"))  # a positive amount back does not clear it


class UpgradeTests(AskAgainTestCase):
    def legacy(self, prompt_id, table="readiness__answers", column="prompt"):
        """Make an answer look as decision 0104 wrote it: the whole-record revision fingerprint."""
        row = self.conn.execute(f"SELECT * FROM {table} WHERE {column} = ? AND deleted_at IS NULL",
                                (prompt_id,)).fetchone()
        prompt = self.prompt_set.step(prompt_id)
        same = next(c for c in questions.candidates(self.conn, self.registry, prompt) if c.key == row["record"])
        self.conn.execute(f"UPDATE {table} SET record_check = ? WHERE id = ?", (same.legacy, row["id"]))
        self.conn.commit()
        return dict(row)

    def snapshot(self):
        rows = [dict(r) for r in self.conn.execute("SELECT * FROM readiness__answers ORDER BY id")]
        history = self.conn.execute("SELECT COUNT(*) FROM core__audit").fetchone()[0]
        log = self.conn.execute("SELECT COUNT(*) FROM core__sync_changes").fetchone()[0]
        return [{k: v for k, v in r.items() if k != "record_check"} for r in rows], history, log

    def test_unchanged_answers_get_a_stamp_without_a_new_answer_and_changed_ones_stay_in_review(self):
        kit = self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        alarm = self.store.create("home_layout__equipment", {"name": "Alarm", "kind": "smoke_alarm",
                                                             "place": self.place("Landing"),
                                                             "last_tested": "2026-10-01"})
        tap = self.store.create("home_layout__shutoffs", {"name": "Tap", "kind": "water", "place": self.place("Yard")})
        for prompt_id in ("medical-kit-location", "fire-alarm-location", "flood-flood-utilities"):
            self.confirm(prompt_id)
            self.legacy(prompt_id)
        self.edit("home_layout__equipment", alarm, notes="Changed before the upgrade")  # 0104 would ask again
        self.store.delete("home_layout__shutoffs", tap)
        self.assertEqual(self.state("medical-kit-location").state, "looked_at")  # the old check still read
        self.assertEqual(self.state("fire-alarm-location").review_reason, "record_changed")
        before = self.snapshot()
        self.assertEqual(questions.upgrade_checks(self.conn, self.registry), 1)
        self.assertEqual(self.snapshot(), before)  # no answer, date, chosen record or history entry changed
        checks = dict(self.conn.execute("SELECT prompt, record_check FROM readiness__answers").fetchall())
        self.assertTrue(checks["medical-kit-location"].startswith(questions.CHECK_PREFIX))
        self.assertFalse(checks["fire-alarm-location"].startswith(questions.CHECK_PREFIX))
        self.assertEqual(self.state("fire-alarm-location").review_reason, "record_changed")
        self.assertEqual(self.state("flood-flood-utilities").review_reason, "record_missing")
        self.edit("medical__kits", kit, last_checked="2026-11-20")  # now an unrelated edit asks nothing
        self.quiet("medical-kit-location", "after the upgrade")
        self.assertEqual(questions.upgrade_checks(self.conn, self.registry), 0)  # nothing left to do
        self.store.restore("home_layout__shutoffs", tap)
        self.asks("flood-flood-utilities", "a restored record from before still asks", again=False)

    def test_start_up_upgrades_answers_and_drill_steps(self):
        self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        self.confirm("medical-kit-location")
        self.legacy("medical-kit-location")
        self.store.create("home_layout__shutoffs", {"name": "Tap", "kind": "water", "place": self.place("Yard")})
        key = questions.candidates(self.conn, self.registry, self.prompt_set.step("pipe-shutoff"))[0].key
        run_id = drills.start(self.store, self.prompt_set, "pipe-in-wall", today=TODAY)
        drills.save_step(self.store, self.prompt_set, run_id, "pipe-shutoff", "plan", record=key, today=TODAY)
        self.legacy("pipe-shutoff", "readiness__drill_steps", "step")
        startup.prepare(self.data, self.tmp / "modules")
        for table in ("readiness__answers", "readiness__drill_steps"):
            check = self.conn.execute(f"SELECT record_check FROM {table} WHERE record IS NOT NULL").fetchone()[0]
            self.assertTrue(check.startswith(questions.CHECK_PREFIX), table)


class PrivacyTests(AskAgainTestCase):
    def test_a_stamp_holds_no_value_and_no_guessable_digest_of_a_private_detail(self):
        alex = self.person("Alex Example")
        detail = self.store.create("people__important_info", {"person": alex, "kind": "medication", "detail": SECRET})
        chosen = self.confirm("medical-prescriptions")
        digests = {hashlib.sha256(SECRET.encode()).hexdigest(), hashlib.md5(SECRET.encode()).hexdigest(),
                   hashlib.sha1(SECRET.encode()).hexdigest()}
        stored = " ".join(str(v) for row in self.answers() for v in tuple(row))
        line = " ".join(str(v) for r in self.conn.execute("SELECT * FROM core__sync_changes WHERE table_name = "
                                                          "'readiness__answers'") for v in tuple(r))
        raw = export.build(self.conn, self.registry, __version__, now=datetime(2026, 11, 21, tzinfo=timezone.utc))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            answers = archive.read("readiness__answers.csv").decode("utf-8-sig")
        for text in (chosen.check, stored, line, answers):
            self.assertNotIn("Synthetic-medicine-name", text)
            for digest in digests:
                for size in (8, 12, 16, 20, 24):
                    self.assertNotIn(digest[:size], text)
        # The stamp is not worked out from the detail: changing the words outside the program's history leaves it.
        self.conn.execute("UPDATE people__important_info SET detail = ? WHERE id = ?", ("Other invented", detail))
        self.conn.commit()
        self.assertEqual(self.state("medical-prescriptions").candidates[0].check, chosen.check)
        self.quiet("medical-prescriptions", "the stamp holds no value")
        self.assertEqual(json.loads(json.dumps(chosen.check)), chosen.check)


class ModuleOffAndDeleteTests(AskAgainTestCase):
    def settings_post(self, client, chosen):
        return client.post("/settings", base_url=BASE, data={"_csrf": client.csrf, "modules": chosen, "people": "2",
                                                             "week_starts": "monday", "distance_unit": "km"})

    def test_switching_a_module_off_keeps_asking_once_it_is_back_until_a_person_answers(self):
        self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        self.confirm("medical-kit-location")
        self.store.create("home_layout__equipment", {"name": "Alarm", "kind": "smoke_alarm", "place": self.place("Yard"),
                                                     "last_tested": "2026-10-01"})
        self.confirm("fire-alarm-location")
        client = self.client()
        everything = list(settings.enabled_modules(self.conn))
        reply = self.settings_post(client, [m for m in everything if m != "medical"])
        self.assertEqual(reply.status_code, 302, reply.get_data(as_text=True)[:500])
        self.assertNotIn("medical", settings.enabled_modules(self.conn))
        self.asks("medical-kit-location", "module off", reason="record_missing", again=False)
        self.quiet("fire-alarm-location", "another module's answer")
        self.assertEqual(self.settings_post(client, everything).status_code, 302)
        self.asks("medical-kit-location", "module back on still asks", again=False)
        self.confirm("medical-kit-location")
        self.quiet("medical-kit-location", "answered again")

    def test_a_stock_place_module_off_marks_answers_whose_path_reads_it(self):
        self.store.create("medical__kits", {"name": "Kit", "kept": "home", "place": self.place("Hall")})
        self.confirm("medical-kit-location")
        self.assertEqual(questions.modules_switching_off(self.store, {"stock"}), 1)
        self.assertEqual(questions.modules_switching_off(self.store, {"stock"}), 0)  # marked once
        self.asks("medical-kit-location", "its place path is in Stock", again=False)
