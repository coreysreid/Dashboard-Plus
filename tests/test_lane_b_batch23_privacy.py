"""Tests for decision 0143: Lane B's batch 23 privacy findings: card spacing, codes, bank and ID numbers, helpers, Review and sharing words.

Every card number is a published test number and every other number is invented."""
import json
import shutil
import unittest
from datetime import date, timedelta

from support import ROOT, TempDirTestCase
from dashboard.core import db, fraud_guard, helpers, records, settings, startup
from dashboard.web import helper_guide
from dashboard.web.app import create_app

PORT = 5143
BASE = f"http://127.0.0.1:{PORT}"
NBSP_CARD = "4111 1111 1111 1111"  # copied from a bank web page or a PDF


class CardSpacingTests(unittest.TestCase):
    def test_a_card_number_is_found_however_it_is_spaced_or_typed(self):
        for text in (NBSP_CARD, "4111  1111  1111  1111", "4111.1111.1111.1111", "4111/1111/1111/1111",
                     "4111_1111_1111_1111", "4111 1111\n1111 1111", "4111 1111 1111 1111",
                     "４１１１" + "１" * 12, "4111 - 1111 - 1111 - 1111",
                     "4111 1111 1111 1111 12/27", "Amex 3782-822463-10005"):
            with self.subTest(text=text):
                self.assertEqual(fraud_guard.check(text, None), fraud_guard.CARD)

    def test_numbers_that_are_not_cards_stay_allowed(self):
        for text in ("Phone 0491 570 156", "Call 0491 570 156 or 0412 345 678", "(555) 123-4567 555-987-6543",
                     "Meter 004512.3 on 2026-11-01", "NMI 41031234567", "Microchip 985000000777888",
                     "Barcode 4006381333931", "Old phone IMEI 353456789012348 for the insurer",
                     "27/11/2026 04/12/2026", "2026.11.27 2026.12.04", "Serial 4111111111111112",
                     "Parcel 1234567890123456789012",
                     # a record's permanent ID: digits in a dashed identifier are never a card (decision 0141)
                     "41111111-1111-1111-1234-567890123456", "a1b2c3d4-4111-1111-1111-111100000000"):
            with self.subTest(text=text):
                self.assertIsNone(fraud_guard.check(text, None))

    def test_an_old_card_with_odd_spaces_is_masked_in_the_right_place(self):
        self.assertEqual(fraud_guard.mask_cards(f"Card {NBSP_CARD} on file"), "Card ••••1111 on file")


class AnyTextTests(unittest.TestCase):
    def test_codes_passwords_bank_and_id_numbers_are_refused_in_any_text(self):
        for text, refusal in (("Alarm code 4321", fraud_guard.SECRET), ("alarm code 1984", fraud_guard.SECRET),
                              ("password: hunter2", fraud_guard.SECRET), ("CVV 123", fraud_guard.SECRET),
                              ("Gate PIN 4821", fraud_guard.SECRET),
                              ("BSB 062-000 account 12345678", fraud_guard.BANK),
                              ("sort code 12-34-56 account 12345678", fraud_guard.BANK),
                              ("GB82 WEST 1234 5698 7654 32", fraud_guard.BANK),
                              ("routing 021000021 acct 000123456789", fraud_guard.BANK),
                              ("TFN 123 456 782", fraud_guard.ID_NUMBER), ("SSN 078-05-1120", fraud_guard.ID_NUMBER),
                              ("Medicare 2123 45670 1", fraud_guard.ID_NUMBER),
                              ("NHS 943 476 5919", fraud_guard.ID_NUMBER)):
            with self.subTest(text=text):
                self.assertEqual(fraud_guard.check(text, None), refusal)

    def test_ordinary_words_near_those_words_stay_allowed(self):
        for text in ("Post code 4000", "promo code SAVE10", "The password is in the manager",
                     "Wi-Fi password: in the router drawer", "Ask Bob for the side gate code", "BSB 062-000",
                     "Electricity account 1234567", "Code 128 barcode", "Takes 2000 units at breakfast"):
            with self.subTest(text=text):
                self.assertIsNone(fraud_guard.check(text, None))

    def test_no_refusal_repeats_a_number(self):
        for message in fraud_guard.REFUSALS:
            self.assertNotRegex(message, r"\d{5}")

    def test_who_to_ask_may_hold_their_phone_number_but_not_a_card_security_code(self):
        for text in ("Ask Bob next door on 0491 570 156", "Ask Ann on +44 20 7946 0999", "Call 555-123-4567"):
            with self.subTest(text=text):
                self.assertIsNone(fraud_guard.check(text, "where_kept"))
        for text in ("CVV 123", "1-9-8-4", "the code is 7319"):
            with self.subTest(text=text):
                self.assertEqual(fraud_guard.check(text, "where_kept"), fraud_guard.WHERE_KEPT)

    def test_last_four_digits_may_be_said_naturally(self):
        for text in ("ends in 1098", "last four 1098", "acct ending 1098", "xxxx-xxxx-1098"):
            with self.subTest(text=text):
                self.assertIsNone(fraud_guard.check(text, "last_digits"))
                self.assertEqual(fraud_guard.stored_last_digits(text), "••••1098")
        self.assertEqual(fraud_guard.check("Account 9876 5432 1098", "last_digits"), fraud_guard.LAST_DIGITS)


class HouseholdTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        for name in ("people", "stock", "home_layout"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        settings.put(self.conn, "household.country", "United Kingdom")

    def client(self):
        settings.put(self.conn, "setup.done", True)
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        app.config["PORT"] = PORT
        client = app.test_client()
        client.get("/?key=k", base_url=BASE)
        client.csrf = app.config["CSRF_TOKEN"]
        return client

    def send(self, client, key, body):
        return client.post("/api/v1/proposals", data=json.dumps(body), base_url=BASE,
                           headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})

    def waiting(self):
        return self.conn.execute("SELECT COUNT(*) FROM core__proposals").fetchone()[0]


class HelperTests(HouseholdTestCase):
    def test_a_helper_send_is_refused_naming_the_entry_and_field_never_the_value(self):
        _helper, key = helpers.issue(self.conn, self.data, "Move-in helper", "suggest", ["people", "stock"])
        client = self.client()
        cases = [
            ({"name": "Card holder", "notes": NBSP_CARD}, "Read from a note", "payment_detail", "Entry 0, notes",
             fraud_guard.CARD, "1111"),
            ({"name": "Grandma", "notes": "Alarm code 4321"}, "Read from a note", "never_kept", "Entry 0, notes",
             fraud_guard.SECRET, "4321"),
            ({"name": "Bank"}, "Copied BSB 062-000 account 12345678", "never_kept", "Why", fraud_guard.BANK,
             "12345678"),
        ]
        for number, (values, why, code, where, refusal, value) in enumerate(cases):
            with self.subTest(code=code, where=where):
                reply = self.send(client, key, {"request_key": f"r-{number}", "why": why,
                                                "entries": [{"table": "people__people", "values": values}]})
                body = reply.get_json()
                self.assertEqual((reply.status_code, body["error"]), (400, code))
                self.assertEqual(body["message"], f"{where}: this {refusal}")
                self.assertNotIn(value, reply.get_data(as_text=True))
                self.assertNotIn("receipt lines", body["message"])
        self.assertEqual(self.waiting(), 0)

    def test_the_guide_says_which_way_round_the_household_writes_dates(self):
        helper, _key = helpers.issue(self.conn, self.data, "Move-in helper", "suggest", ["stock"])
        app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.enterContext(app.app_context())
        text = helper_guide.guide_text(self.conn, self.registry, helper)
        self.assertIn("This household writes dates day first (DD/MM/YY), so its 03/04/27 means 3 April 2027. Still "
                      "send dates as 2027-04-03.", text)
        self.assertIn("never_kept", text)
        self.assertIn("A person's medicines go in their private medical details, which only they type.", text)
        self.assertIn("never its use-by date", text)
        settings.put(self.conn, "household.country", "United States")
        text = helper_guide.guide_text(self.conn, self.registry, helper)
        self.assertIn("month first (MM/DD/YY), so its 04/03/27 means April 3, 2027.", text)


class ReviewTests(HouseholdTestCase):
    def test_a_stock_in_dated_after_today_gets_a_gentle_check_on_review(self):
        _helper, key = helpers.issue(self.conn, self.data, "Move-in helper", "suggest", ["stock"])
        tins = self.store.create("stock__items", {"name": "Invented paracetamol", "unit": "packs"})
        later = (date.today() + timedelta(days=120)).isoformat()
        client = self.client()
        for number, when in enumerate((later, "2026-01-02")):
            reply = self.send(client, key, {"request_key": f"in-{number}", "why": "From the notebook",
                                            "entries": [{"table": "stock__movements", "values": {
                                                "item": tins, "reason": "bought", "amount": 2,
                                                "happened_on": when}}]})
            self.assertEqual(reply.status_code, 201, reply.get_data(as_text=True))
        page = client.get("/review", base_url=BASE).get_data(as_text=True)
        self.assertEqual(page.count("data-future-date"), 1)
        self.assertIn("This date is after today. A Stock in is for something that already happened: check the date "
                      "before accepting", page)


class SharingWordsTests(HouseholdTestCase):
    def test_private_is_said_once_with_a_jump_list_and_what_was_changed(self):
        client = self.client()
        page = client.get("/settings/sharing", base_url=BASE).get_data(as_text=True)
        self.assertNotIn("(private) (private)", page)
        self.assertIn("data-sharing-jump", page)
        self.assertIn('<a href="#sharing-1">', page)
        self.assertIn("Everything is as usual.", page)
        reply = client.post("/settings/sharing", base_url=BASE,
                            data={"_csrf": client.csrf, "c:people__people.notes": "local"})
        self.assertIn(reply.status_code, (200, 302, 303))
        page = client.get("/settings/sharing", base_url=BASE).get_data(as_text=True)
        self.assertIn("You have changed 1 thing from the usual: People, Notes (Only on this computer).", page)


if __name__ == "__main__":
    unittest.main()


class FingerprintIsNotAnIbanTests(unittest.TestCase):
    """A readiness answer's record fingerprint ("2:" and 24 lower-case hex letters) once read as an Andorran IBAN."""

    def test_fingerprints_and_ids_are_not_bank_accounts(self):
        import hashlib
        from dashboard.core import fraud_guard, questions
        for seed in range(20000):
            value = questions.CHECK_PREFIX + hashlib.sha256(str(seed).encode()).hexdigest()[:24]
            self.assertIsNone(fraud_guard.check(value, None), value)
        self.assertIsNone(fraud_guard.check("2:ad46c082e9244c0cddbd168b", None))

    def test_real_ibans_are_still_refused(self):
        from dashboard.core import fraud_guard
        for text in ("GB82 WEST 1234 5698 7654 32", "DE89 3704 0044 0532 0130 00", "GB82 west 1234 5698 7654 32"):
            self.assertIsNotNone(fraud_guard.check(text, None), text)
