"""Tests for helper keys: shown once, kept only as a fingerprint outside the database, and safe across restores."""
import json
import os
import shutil
import stat

from support import ROOT, TempDirTestCase
from dashboard.core import db, hello, helpers, records, startup
from dashboard.errors import PlainError


class HelperKeyTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        shutil.copytree(ROOT / "modules" / "stock", self.tmp / "modules" / "stock")
        for name in ("pets", "people"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(lambda: self.conn.close())

    def issue(self, name="Pet diary helper", access="suggest", modules=("pets",)):
        return helpers.issue(self.conn, self.data, name, access, list(modules))

    def header(self, key):
        return f"Bearer {key}"

    def test_a_key_is_made_once_and_never_stored_in_the_database(self):
        helper, key = self.issue()
        self.assertTrue(key.startswith("dph_"))
        self.assertGreaterEqual(len(key), 40)
        self.conn.close()
        self.assertNotIn(key.encode(), (self.data / "dashboard.db").read_bytes())
        self.conn = db.connect(self.data / "dashboard.db")
        for table in ("core__helpers", "core__helper_batches", "core__proposals", "core__audit"):
            for row in self.conn.execute(f"SELECT * FROM {table}"):
                self.assertNotIn(key, " ".join(str(v) for v in tuple(row)))
        self.assertEqual(helper.name, "Pet diary helper")

    def test_the_file_holds_only_a_fingerprint_and_is_private(self):
        helper, key = self.issue()
        path = self.data / "secrets" / "helper_keys.json"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(key, text)
        self.assertEqual(json.loads(text), {helpers.fingerprint(key): helper.key_id})
        self.assertEqual(len(helpers.fingerprint(key)), 64)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)

    def test_the_public_name_and_hello_secret_come_from_the_kept_fingerprint_only(self):
        _helper, key = self.issue()
        kept = helpers.active_fingerprints(self.data)
        self.assertEqual(kept, [helpers.fingerprint(key)])
        self.assertEqual(hello.fingerprint(key), helpers.fingerprint(key))  # both sides agree (decision 0086)
        name, secret = hello.key_name(kept[0]), hello.shared_secret(kept[0])
        self.assertNotIn(name, (kept[0], hello.fingerprint(key)))
        self.assertNotEqual(secret.hex(), name)
        self.assertNotIn(key, name)
        self.assertEqual(hello.answer(kept, name, "ab" * 32, "127.0.0.1:5123", b"x" * 32),
                         hello.proof(secret, "ab" * 32, "127.0.0.1:5123"))

    def test_the_right_key_is_accepted_and_wrong_ones_are_refused(self):
        helper, key = self.issue()
        self.assertEqual(helpers.verify(self.conn, self.data, self.header(key)).id, helper.id)
        wrong = key[:-1] + ("A" if key[-1] != "A" else "B")
        for bad in (None, "", "Bearer", "Bearer ", self.header(wrong), self.header("dph_" + "x" * 200),
                    f"Basic {key}", key, f"bearer {key}", self.header(key) + " extra", "Bearer " + key[4:]):
            with self.subTest(bad=str(bad)[:20]):
                self.assertIsNone(helpers.verify(self.conn, self.data, bad))

    def test_turning_off_stops_the_key_and_keeps_the_history(self):
        helper, key = self.issue()
        helpers.turn_off(self.conn, self.data, helper.id)
        self.assertIsNone(helpers.verify(self.conn, self.data, self.header(key)))
        self.assertEqual(json.loads((self.data / "secrets" / "helper_keys.json").read_text(encoding="utf-8")), {})
        self.assertIsNotNone(helpers.get(self.conn, helper.id).revoked_at)
        actions = [r["action"] for r in self.conn.execute("SELECT action FROM core__audit WHERE action LIKE 'helper_%' ORDER BY id")]
        self.assertEqual(actions, ["helper_add", "helper_off"])

    def test_restoring_an_old_copy_cannot_bring_back_a_turned_off_key(self):
        helper, key = self.issue()
        copy = self.tmp / "old.db"
        db.backup_to(self.conn, copy)
        helpers.turn_off(self.conn, self.data, helper.id)
        self.conn.close()
        shutil.copy(copy, self.data / "dashboard.db")  # the older copy, from before the key was turned off
        self.conn = db.connect(self.data / "dashboard.db")
        self.assertIsNone(helpers.get(self.conn, helper.id).revoked_at)  # the database forgot...
        self.assertIsNone(helpers.verify(self.conn, self.data, self.header(key)))  # ...but the key stays dead

    def test_a_key_made_after_a_copy_does_not_work_once_that_copy_is_restored(self):
        copy = self.tmp / "old.db"
        db.backup_to(self.conn, copy)
        first, later_key = self.issue("Receipt helper", modules=("stock",))
        self.conn.close()
        shutil.copy(copy, self.data / "dashboard.db")
        self.conn = db.connect(self.data / "dashboard.db")
        self.assertIsNone(helpers.verify(self.conn, self.data, self.header(later_key)))
        # A new helper may get the same row number, but not the old key's powers.
        second, key = self.issue("Someone else", access="read", modules=("pets",))
        self.assertEqual(second.id, first.id)
        self.assertIsNone(helpers.verify(self.conn, self.data, self.header(later_key)))
        self.assertEqual(helpers.verify(self.conn, self.data, self.header(key)).name, "Someone else")

    def test_names_become_short_labels_that_are_never_used_twice(self):
        first, _ = self.issue("Pet diary helper")
        second, _ = self.issue("Pet diary helper")
        odd, _ = self.issue("Zoë's  helper!! (v2)")
        blank_label, _ = self.issue("!!!")
        self.assertEqual(first.slug, "pet-diary-helper")
        self.assertEqual(second.slug, "pet-diary-helper-2")
        self.assertEqual(odd.slug, "zo-s-helper-v2")
        self.assertEqual(blank_label.slug, "helper")
        for helper in (first, second, odd, blank_label):
            self.assertRegex(helper.actor, records.ACTOR)
        helpers.turn_off(self.conn, self.data, first.id)
        third, _ = self.issue("Pet diary helper")
        self.assertEqual(third.slug, "pet-diary-helper-3")  # a turned-off helper's label stays taken

    def test_a_helper_needs_a_name_a_level_and_at_least_one_part(self):
        for args, words in ((("", "read", ["pets"]), "Give the helper a name."),
                            (("A" * 41, "read", ["pets"]), "40"),
                            (("Ok", "admin", ["pets"]), "Choose what the helper may do."),
                            (("Ok", "read", []), "Choose at least one part of your records.")):
            with self.subTest(words):
                with self.assertRaises(PlainError) as caught:
                    helpers.issue(self.conn, self.data, *args)
                self.assertIn(words, str(caught.exception))
        self.assertEqual(helpers.all_helpers(self.conn), [])

    def test_allowed_registry_keeps_only_the_ticked_parts_that_are_switched_on(self):
        helper, _ = self.issue(modules=("pets", "people"))
        registry = records.build_registry([m for m in self.report.loaded if m.name in ("pets", "stock")])
        allowed = helpers.allowed_registry(registry, helper)
        self.assertTrue(allowed)
        self.assertEqual({info.module.name for info in allowed.values()}, {"pets"})

    def test_last_used_is_noted_at_most_once_a_minute(self):
        helper, _ = self.issue()
        helpers.touch(self.conn, helper)
        first = helpers.get(self.conn, helper.id).last_used_at
        self.assertIsNotNone(first)
        helper.last_used_at = first
        self.conn.execute("UPDATE core__helpers SET last_used_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (helper.id,))
        helpers.touch(self.conn, helper)  # recent according to the object it was given: left alone
        self.assertEqual(helpers.get(self.conn, helper.id).last_used_at, "2000-01-01T00:00:00+00:00")
