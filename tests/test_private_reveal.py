"""Tests for decision 0123: private calendars name nobody until Show, the Record a dose link copies nothing private, and Show on one private detail is a POST that is never cached.

Uses the invented dose household of the 0121 tests: a person (Rosa Garcia), a medicine word, an amount and a giver."""
import re
from html.parser import HTMLParser

from test_module_medicine_doses import AMOUNT, BASE, SECRET, TABLE
from test_private_lists_and_dose_calendar import CAL, GIVER, PrivateDoseCase

NAME = "Rosa Garcia"
JSON = {"Accept": "application/json"}


class Forms(HTMLParser):
    """Collects every form and button so a test can check how Show is wired, as a browser would use it."""

    def __init__(self):
        super().__init__()
        self.buttons, self.forms = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "button":
            self.buttons.append(dict(attrs))
        if tag == "form":
            self.forms.append(dict(attrs))


def parse(text):
    found = Forms()
    found.feed(text)
    return found


class PrivateCalendarNamesTests(PrivateDoseCase):
    def test_no_calendar_page_names_the_person_before_show_and_every_one_does_after(self):
        before = [f"{CAL}?subject={self.rosa}&month=2026-11", f"{CAL}?month=2026-11", f"/t/people__people/{self.rosa}#cal",
                  f"/daily/{TABLE}?subject={self.rosa}&day=2026-11-19", f"{CAL}?subject={self.rosa}&month=2026-10"]
        for path in before:
            text = self.page(path.split("#")[0], self.web)
            if path.startswith("/t/people"):
                text = text[text.index("<h2>Dose calendar"):]  # the person's own page names them in its heading; the panel must not
                text = text[:text.index("</section>")]
            self.assertNotIn(NAME, text, path)
            self.assertNotIn(GIVER, text, path)
            self.assertNotIn(SECRET, text, path)
        text = self.page(f"{CAL}?subject={self.rosa}&month=2026-11", self.web)
        self.assertIn("2 doses recorded", text)
        self.assertIn(f"Person 1", text)
        self.assertNotIn("See the person", text)
        self.assertIn("Open the person's page", text)
        shown = self.shown(CAL, subject=str(self.rosa), month="2026-11")
        self.assertIn(NAME, shown)
        self.assertIn(f"Who gave it: {GIVER}", shown)
        day = self.shown(f"/daily/{TABLE}", subject=str(self.rosa), day="2026-11-19")
        self.assertIn(NAME, day)
        self.assertNotIn(NAME, self.page(f"/daily/{TABLE}?subject={self.rosa}&day=2026-11-19&show=1", self.web))

    def test_the_chooser_lists_people_by_number_before_show_and_by_name_after(self):
        text = self.page(f"{CAL}?month=2026-11", self.web)
        self.assertIn(f"subject={self.sofia}", text)
        for words in (NAME, "Sofia"):
            self.assertNotIn(words, text.split("<h1>")[1].split("cal-wrap")[0])
        shown = self.shown(CAL, subject=str(self.rosa), month="2026-11")
        self.assertIn(NAME, shown)


class RecordLinkTests(PrivateDoseCase):
    def test_the_record_link_carries_only_the_person_and_the_time(self):
        for path in (f"/t/people__people/{self.rosa}", f"/daily/{TABLE}?subject={self.rosa}", f"{CAL}?subject={self.rosa}"):
            text = self.page(path, self.web)
            for link in re.findall(r'href="(/t/%s/new[^"]*)"' % TABLE, text):
                self.assertNotIn("from=last", link)
                self.assertNotIn("given_by", link)
                self.assertNotIn("medication", link)
                self.assertIn(f"recipient={self.rosa}", link)
        link = re.search(r'href="(/t/%s/new[^"]*)"' % TABLE, self.page(f"/daily/{TABLE}?subject={self.rosa}", self.web)).group(1)
        form = self.page(link.replace("&amp;", "&"), self.web)
        self.assertNotIn("Filled in from a recent entry", form)
        for field in ("medication", "given_by"):  # nothing is chosen for them from an earlier dose
            select = re.search(r'<select id="f-%s".*?</select>' % field, form, re.S).group(0)
            self.assertNotIn("selected", select, field)


class RevealTests(PrivateDoseCase):
    def reveal(self, column, token=True, headers=None, record=None):
        data = {"column": column}
        if token:
            data["_csrf"] = self.web.csrf
        return self.web.post(f"/t/{TABLE}/{record or self.first}/reveal", data=data, base_url=BASE, headers=headers or {})

    def test_a_get_never_reveals(self):
        reply = self.web.get(f"/t/{TABLE}/{self.first}/reveal?column=amount", base_url=BASE)
        self.assertEqual(reply.status_code, 405)
        self.assertNotIn(AMOUNT, reply.get_data(as_text=True))
        self.assertNotIn("reveal?column", self.page(f"/t/{TABLE}/{self.first}", self.web))

    def test_a_post_without_the_session_token_is_refused(self):
        reply = self.reveal("amount", token=False, headers=JSON)
        self.assertEqual(reply.status_code, 400)
        self.assertNotIn(AMOUNT, reply.get_data(as_text=True))

    def test_a_post_with_the_token_reveals_and_is_never_cached(self):
        reply = self.reveal("amount", headers=JSON)
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply.get_json()["value"], AMOUNT)
        self.assertEqual(reply.headers["Cache-Control"], "no-store")
        self.assertEqual(self.reveal("given_at", headers=JSON).status_code, 404)  # only private columns

    def test_without_a_page_script_the_button_opens_a_small_page_with_the_words(self):
        shown = self.shown(f"/t/{TABLE}/{self.first}/show")
        buttons = [b for b in parse(shown).buttons if "data-reveal" in b or "data-reveal-field" in b]
        self.assertTrue(buttons)
        for button in buttons:
            self.assertEqual(button["type"], "submit")  # a real submit button: it works with no script
            self.assertEqual(button["form"], "reveal-form")
            self.assertEqual(button["formmethod"], "post")
            self.assertTrue(button["formaction"].endswith("/reveal"))
            self.assertIn("aria-label", button)  # a screen reader hears which detail it shows
        self.assertNotIn(AMOUNT, shown)
        forms = [f for f in parse(shown).forms if f.get("id") == "reveal-form"]
        self.assertEqual(len(forms), 1)
        self.assertIn(f'name="_csrf" value="{self.web.csrf}"', shown)
        page = self.reveal("amount")  # a browser asks for a page, not JSON
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.headers["Cache-Control"], "no-store")
        text = page.get_data(as_text=True)
        self.assertIn("data-revealed", text)
        self.assertIn(AMOUNT, text)
        self.assertEqual(page.mimetype, "text/html")
