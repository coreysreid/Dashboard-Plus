"""Tests for decision 0134: the privacy and security review of decisions 0119-0133, one test per finding fixed and the checks that held.

Uses the invented dose household of the 0121 and 0123 tests (Rosa Garcia, a medicine word, an amount and a giver)
and the invented Stock household of the 0133 tests (prices and money back). Every name and number is made up."""
import re

from support import ROOT, TempDirTestCase
from test_module_medicine_doses import AMOUNT, BASE, SECRET, TABLE
from test_private_lists_and_dose_calendar import CAL, GIVER, PrivateDoseCase
from test_receipt_review import ReceiptTestCase
from test_refunds_and_review_price import BASE as STOCK_BASE, MOVES, REFUNDS, RefundTestCase
from dashboard.core import modules, proposals, settings

NAME = "Rosa Garcia"
BARS = f"/bars/{TABLE}/doses"


def section(text: str, start: str) -> str:
    """The part of a page from `start` to the end of its section."""
    found = text[text.index(start):]
    return found[:found.index("</section>")]


def tag(text: str, field_id: str) -> str:
    """The opening tag of the form field with this id."""
    return re.search(r'<(?:input|select|textarea)[^>]*id="%s"[^>]*>' % re.escape(field_id), text).group(0)


class PrivateBarsNameNobodyTests(PrivateDoseCase):
    """Finding 1: the dose bars page named the person (and listed everyone with a medicine by name) before Show,
    where the Dose calendar says only "this person" and "Given to #1" (decision 0123)."""

    def test_the_bars_page_and_its_chooser_name_nobody_until_show(self):
        for path in (BARS, f"{BARS}?subject={self.rosa}", f"{BARS}?subject={self.rosa}&by=day", f"{BARS}?show=1"):
            text = self.page(path, self.web)
            for words in (NAME, "Sofia Garcia", GIVER, SECRET, AMOUNT):
                self.assertNotIn(words, text, f"{path}: {words}")
            self.assertIn(f"Given to #{self.rosa}", text)
            self.assertIn("this person", text)
            self.assertIn("Open the person's page", text)
        shown = self.shown(BARS, subject=str(self.rosa))
        self.assertIn(NAME, shown)
        self.assertIn(SECRET, shown)  # each medicine on its own, after the pressed Show (decision 0124)

    def test_the_panel_on_the_persons_page_says_this_person_like_the_dose_calendar(self):
        text = self.page(f"/t/people__people/{self.rosa}", self.web)
        panel = section(text, f'id="bars-{TABLE}-doses-{self.rosa}"')
        self.assertNotIn(NAME, panel)
        self.assertIn("This person", panel)


class PrivateFieldsAutocompleteTests(PrivateDoseCase):
    """Finding 2: private fields let the browser remember what was typed in them (its own form history)."""

    def test_every_private_field_on_a_form_asks_the_browser_not_to_remember_it(self):
        form = self.page(f"/t/{TABLE}/new?recipient={self.rosa}", self.web)
        self.assertIn('autocomplete="off"', tag(form, "f-amount"))
        detail = self.page("/t/people__important_info/new", self.web)
        self.assertIn('autocomplete="off"', tag(detail, "f-detail"))
        self.assertNotIn('autocomplete="off"', tag(self.page("/t/people__people/new", self.web), "f-name"),
                         "ordinary fields keep the browser's help")


class StockFieldsTests(RefundTestCase):
    def test_prices_and_money_back_are_not_remembered_by_the_browser(self):
        client = self.client()
        stock_in = self.page(client, f"/t/{MOVES}/new")
        self.assertIn('autocomplete="off"', tag(stock_in, "f-price"))
        refund = self.page(client, f"/t/{REFUNDS}/new?movement={self.nov}")
        for field in ("f-amount", "f-notes"):
            self.assertIn('autocomplete="off"', tag(refund, field), field)

    def test_a_saved_private_number_or_choice_stays_closed_until_show(self):
        """Finding 3: a saved price showed an empty box beside "Private detail saved"; anything typed in it was
        quietly ignored, because the saved price is kept until Show."""
        page = self.page(self.client(), f"/t/{MOVES}/{self.nov}")
        self.assertNotIn("3.80", page)
        self.assertRegex(tag(page, "f-price"), r"\shidden")
        self.assertRegex(tag(page, "f-price_basis"), r"\shidden")
        self.assertIn('hidden id="f-currency-box"', page)  # a text field sits in its own closed box

    def test_a_saved_private_tick_stays_closed_and_kept_when_the_page_is_saved(self):
        """Finding 3, for a tick: "This is more than was paid" showed as an empty box, so saving the money back
        page unchanged read it as not ticked and refused (or, under the amount paid, quietly cleared it)."""
        refund = self.back(self.nov, "5.00", over_paid=True)
        client = self.client()
        page = self.page(client, f"/t/{REFUNDS}/{refund}")
        self.assertNotRegex(tag(page, "f-over_paid"), r"\schecked")
        self.assertIn('id="f-over_paid-box" hidden', page)
        self.assertIn('name="_keep_private" value="over_paid"', page)
        saved = self.post(client, f"/t/{REFUNDS}/{refund}", movement=str(self.nov), happened_on="19/11/26",
                          _keep_private=["amount", "over_paid"])
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(self.row(refund)["over_paid"], 1)
        shown = client.post(f"/t/{REFUNDS}/{refund}/reveal", base_url=STOCK_BASE,
                            data={"_csrf": client.csrf, "column": "over_paid"}, headers={"Accept": "application/json"})
        self.assertEqual(shown.get_json()["value"], "1")

    def test_far_back_dates_in_an_address_are_a_page_not_an_error(self):
        """Finding 5: an address asking for a period near the year 1 crashed the bars page."""
        client = self.client()
        for path in (f"/bars/{MOVES}/spending?end=0001-01-01", f"/bars/{MOVES}/spending?end=0001-01-01&by=month"):
            self.page(client, path)
        self.assertEqual(self.post(client, f"/bars/{MOVES}/spending", end="0001-01-01").status_code, 200)


class FarBackDoseDatesTests(PrivateDoseCase):
    def test_far_back_dates_on_the_dose_bars_and_day_pages(self):
        for path in (f"{BARS}?subject={self.rosa}&end=0001-01-08&by=day", f"{BARS}?subject={self.rosa}&end=0001-01-01",
                     f"/daily/{TABLE}?subject={self.rosa}&day=0001-01-01"):
            self.page(path, self.web)
        self.assertEqual(self.post(self.web, BARS, subject=str(self.rosa), end="0001-01-01").status_code, 200)


class PriceReasonNotForHelpersTests(ReceiptTestCase):
    """Finding 4: when a person's typed price could not be saved, the reason was written on the waiting row, which
    the helper reads back from its batch: it learned that the person was typing a price, and what was wrong."""

    def test_the_helper_never_reads_why_a_typed_price_was_not_saved(self):
        result = self.send([dict(self.bought(self.tomatoes, 3), source={"line": "TOMATOES x3", "price": "$7.77"})])
        row = self.conn.execute("SELECT id FROM core__proposals").fetchone()
        page = self.follow(f"/review/{row['id']}/accept", {"price": "1.90", "currency": "dollars"})
        self.assertIn("Nothing was added: the price was not saved.", page)  # the person still sees why
        seen = proposals.batch_result(self.conn, result["batch_id"], detail=True, registry=self.registry)
        reason = seen["proposals"][0]["reason"] or ""
        for words in ("price", "1.90", "currency", "dollars", "three-letter"):
            self.assertNotIn(words, reason.lower(), words)
        self.assertEqual(seen["proposals"][0]["status"], "pending")


class DeclarationCheckTests(TempDirTestCase):
    """Finding 6: a module could draw a private (sensitive) date or link on a calendar, bars or timeline, where it
    would be on the page before any Show. The module checker now refuses it in plain words."""

    TABLES = '''[tables.owners]
title = "Owners"
columns.name = { type = "text", required = true }

[tables.visits]
title = "Visits"
columns.owner = { type = "link", to = "owners", required = true, on_delete = "restrict"{owner} }
columns.other = { type = "link", to = "owners", required = true, on_delete = "restrict"{other} }
columns.on = { type = "date", required = true{on} }

[tables.visits.calendar]
when = "on"
per = "owner"
show = "one"
title = "Visit calendar"
entry = ["visit", "visits"]

[[tables.visits.bars]]
key = "visits"
title = "Visits"
when = "on"
per = "owner"
measure = "count"
group = "other"
by = ["month"]
entry = ["visit", "visits"]
subject = "owner"

[tables.visits.timeline]
when = "on"
per = "owner"
entry = ["visit", "visits"]
look = "done"
'''
    PRIVATE = ', sensitive = true, travels = "never"'

    def problems(self, **private):
        tables = self.TABLES
        for key in ("owner", "other", "on"):
            tables = tables.replace("{%s}" % key, self.PRIVATE if private.get(key) else "")
        self.make_module("visits", tables=tables, labels=None)
        _, failures = modules.discover(self.tmp / "modules")
        return " ".join(failures.get("visits", []))

    def test_a_plain_declaration_loads(self):
        self.assertEqual(self.problems(), "")

    def test_a_private_date_cannot_be_drawn(self):
        text = self.problems(on=True)
        for part in ("calendar", "bars", "timeline"):
            self.assertRegex(text, rf"table 'visits', {part}[^.]*: 'when' must name a [^.]*not private", part)

    def test_a_private_link_cannot_choose_the_subject_or_the_groups(self):
        text = self.problems(owner=True, other=True)
        for part in ("calendar", "bars", "timeline"):
            self.assertRegex(text, rf"table 'visits', {part}[^.]*: 'per' must name a [^.]*not private", part)
        self.assertRegex(text, r"'group' must name [^.]*not private")


class ChecksThatHeldTests(PrivateDoseCase):
    """Checks of the review that found nothing wrong, kept so they stay that way."""

    def test_every_show_is_a_post_with_the_session_check_and_never_cached(self):
        for path, data in ((CAL, {"subject": str(self.rosa)}), (BARS, {"subject": str(self.rosa)}),
                           (f"/timeline/people__people/{self.rosa}", {}),
                           (f"/t/{TABLE}/{self.first}/reveal", {"column": "amount"}),
                           (f"/t/{TABLE}/{self.first}/show", {}), (f"/t/{TABLE}/show", {})):
            refused = self.web.post(path, base_url=BASE, data=data)  # no session token
            self.assertEqual(refused.status_code, 400, path)
            self.assert_nothing_private(refused.get_data(as_text=True), path)
            shown = self.post(self.web, path, **data)
            self.assertEqual(shown.status_code, 200, path)
            self.assertEqual(shown.headers.get("Cache-Control"), "no-store", path)
        self.page(f"/t/{TABLE}/{self.first}/reveal?column=amount", self.web, status=405)
        for path in (f"/calendar/{TABLE}/not-done", f"/calendar/{TABLE}/put-back"):
            self.page(path, self.web, status=405)

    def test_another_website_cannot_press_show(self):
        reply = self.web.post(BARS, base_url=BASE, headers={"Origin": "http://example.invalid"},
                              data={"_csrf": self.web.csrf, "subject": str(self.rosa)})
        self.assertEqual(reply.status_code, 403)
        self.assertNotIn(SECRET, reply.get_data(as_text=True))

    def test_switched_off_the_private_pages_and_their_show_are_gone(self):
        settings.set_module_enabled(self.conn, "medicine_doses", False)
        client = self.client()
        for path in (CAL, BARS, f"/t/{TABLE}/{self.first}"):
            self.page(path, client, status=404)
        for path, data in ((CAL, {}), (BARS, {}), (f"/t/{TABLE}/{self.first}/reveal", {"column": "amount"})):
            self.assertEqual(self.post(client, path, **data).status_code, 404, path)

    def test_no_show_adds_anything_to_an_address_and_no_page_loads_from_another_site(self):
        for path in (CAL, BARS, f"/timeline/people__people/{self.rosa}"):
            text = self.shown(path, subject=str(self.rosa))
            for link in re.findall(r'href="([^"]*)"', text):
                self.assertNotIn("show", link.lower(), f"{path}: {link}")
                self.assertNotRegex(link, r"^(https?:)?//", f"{path}: {link}")
            self.assertNotRegex(text, r'<script[^>]+src="(?!/static/)', path)  # only the program's own files (0139)

    def test_the_print_script_in_every_page_loads_nothing_and_sends_nothing(self):
        script = (ROOT / "src" / "dashboard" / "web" / "static" / "common.js").read_text(encoding="utf-8")
        self.assertIn("beforeprint", script)
        self.assertNotIn("src=", script)
        self.assertEqual(script.count("fetch("), 1, "only Show's own POST to this program")
        self.assertNotIn("http", script)
