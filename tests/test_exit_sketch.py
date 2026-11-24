"""Tests for the way-out sketch (decision 0118): Lane B's exit map checks, steady layout, continuation pages and privacy."""
import re
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, exit_sketch, records, settings, startup
from dashboard.web import exit_drawing
from dashboard.web.app import create_app

PORT = 5137
BASE = f"http://127.0.0.1:{PORT}"
PLACES, CONNECTIONS = "stock__places", "stock__connections"
MODULES = ("people", "stock", "home_layout", "utilities", "readiness")
# Made-up private values planted in every private field near the sketch; none may ever print.
SECRETS = ("KEYSAFE-4821", "ALARM-CODE-7730", "ACCOUNT-99-1234", "SPARE-KEY-UNDER-POT", "ASTHMA-SENTINEL",
           "NOTE-SENTINEL-ROOM", "NOTE-SENTINEL-DOOR")
PAGES = ("/exit-sketch", "/exit-sketch/print?paper=a4", "/exit-sketch/print?paper=letter", "/exit-sketch/text")


class SketchTestCase(TempDirTestCase):
    """A household with Household stock, Home layout, People, Utilities and Readiness, signed in."""

    def setUp(self):
        super().setUp()
        for name in MODULES:
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        settings.put(self.conn, "setup.done", True)
        settings.put(self.conn, "household.country", "Australia")
        settings.put(self.conn, "household.home_type", "house")
        self.app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    @property
    def registry(self):
        on = settings.enabled_modules(self.conn)
        return records.build_registry([m for m in self.report.loaded if m.name in on])

    @property
    def store(self):
        return records.Records(self.conn, self.registry)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def text(self, path):
        reply = self.get(path)
        self.assertEqual(reply.status_code, 200, path)
        return reply.get_data(as_text=True)

    def post(self, path, data=None):
        return self.client.post(path, data=dict(data or {}, _csrf=self.app.config["CSRF_TOKEN"]), base_url=BASE)

    def room(self, name, floor="street", sleeping=False, inside=None, **more):
        return self.store.create(PLACES, dict({"name": name, "inside": inside, "floor": floor,
                                               "sleeping": sleeping}, **more))

    def join(self, a, b=None, kind="door", destination=None):
        values = {"place": a, "connects_to": b, "kind": kind}
        if destination:
            values["destination"] = destination
        return self.store.create(CONNECTIONS, values)

    def sketch(self):
        return exit_sketch.read(self.conn, self.registry, "000")

    def note(self, room_id):
        return " ".join(next(r for r in self.sketch().rooms if r.id == room_id).notes)

    def smith(self):
        """Smith's invented two-floor path: Main bedroom → Hallway → Stairs → Front hall → front door."""
        self.front = self.room("Front hall")
        self.hall = self.room("Hallway", "up1")
        self.bed = self.room("Main bedroom", "up1", sleeping=True)
        self.stairs = self.join(self.front, self.hall, "stairs")
        self.bed_door = self.join(self.hall, self.bed)
        self.front_door = self.join(self.front, None, "outside_door", "outside")


class FromSetUpMyHomeTests(SketchTestCase):
    def test_rooms_and_connections_come_from_places_and_a_rename_changes_both_versions(self):
        self.smith()
        cupboard = self.room("Linen cupboard", None, inside=self.hall)
        page = self.text("/exit-sketch")
        self.assertIn(f'data-room="{self.bed}"', page)
        self.assertNotIn(f'data-room="{cupboard}"', page)  # storage spots never become boxes
        self.store.update(PLACES, self.bed, {"name": "Big bedroom"})
        for path in PAGES:
            page = self.text(path)
            self.assertIn("Big bedroom", page, path)
            self.assertNotIn("Main bedroom", page, path)

    def test_a_storage_spots_connection_counts_for_its_room(self):
        self.smith()
        spot = self.room("Pantry", None, inside=self.front)
        self.join(spot, self.hall, "opening")
        front = next(r for r in self.sketch().rooms if r.id == self.front)
        self.assertIn("Open doorway to Hallway (One floor up)", [l.words for l in front.links])

    def test_set_up_my_home_and_home_link_to_the_sketch(self):
        self.smith()
        self.assertIn('href="/exit-sketch"', self.text("/set-up-home"))
        self.assertIn('href="/exit-sketch"', self.text("/"))


class RouteWordsTests(SketchTestCase):
    def test_two_doors_through_one_hallway_are_never_called_two_ways_out(self):
        self.smith()
        ensuite = self.room("Ensuite", "up1")
        self.join(self.bed, ensuite)
        self.join(ensuite, self.hall)  # a loop: a second line back to the same hallway
        words = self.note(self.bed)
        self.assertIn(exit_sketch.SHARED_WAY, words)
        self.assertIn("Hallway", words)
        for path in PAGES:
            page = self.text(path).lower()
            self.assertNotIn("two ways out confirmed", page)
            self.assertNotIn("independent", page)
            self.assertNotIn("safe exit", page)

    def test_unconnected_and_one_way_sleeping_rooms_get_the_exact_words(self):
        self.smith()
        lonely = self.room("Spare bedroom", "up1", sleeping=True)
        self.assertEqual(self.note(lonely), exit_sketch.NO_WAY)
        self.assertIn(exit_sketch.ONE_WAY, self.note(self.bed))
        page = self.text("/exit-sketch/text")
        self.assertIn(exit_sketch.NO_WAY, page)
        self.assertNotIn("no exit", page.lower())

    def test_blank_balcony_and_shared_corridor_doors_need_checking_and_windows_are_never_inferred(self):
        flat = self.room("Living room")
        balcony = self.room("Balcony")
        blank = self.join(flat, None, "outside_door")
        to_balcony = self.join(flat, balcony, "outside_door", "check")
        corridor = self.join(self.room("Hall"), None, "outside_door", "shared")
        words = {l.id: l for r in self.sketch().rooms for l in r.links if l.outside}
        self.assertIn("destination needs checking", words[blank].words)
        self.assertIn("destination needs checking", words[to_balcony].words)
        self.assertIn("shared building area, not outside", words[corridor].words)
        self.assertFalse(any(l.exit for l in words.values()))
        self.assertNotIn(exit_sketch.WINDOW, self.text("/exit-sketch/text"))
        self.store.update(PLACES, flat, {"window_exit": True})
        self.assertIn(exit_sketch.WINDOW, self.text("/exit-sketch/text"))

    def test_the_household_confirms_door_destinations_on_the_page(self):
        flat = self.room("Living room")
        door = self.join(flat, None, "outside_door")
        reply = self.post("/exit-sketch/doors", {f"destination-{door}": "outside"})
        self.assertEqual(reply.status_code, 302)
        self.assertEqual(self.store.get(CONNECTIONS, door)["destination"], "outside")
        self.post("/exit-sketch/doors", {f"destination-{door}": "made-up"})
        self.assertIsNone(self.store.get(CONNECTIONS, door)["destination"])

    def test_rooms_get_floors_sleeping_and_can_be_left_off(self):
        car = self.room("Car", None)
        bed = self.room("Bedroom", None)
        self.post("/exit-sketch/rooms", {f"floor-{car}": "off", f"floor-{bed}": "up1", f"sleeping-{bed}": "yes"})
        self.assertEqual(self.store.get(PLACES, car)["floor"], "off")
        self.assertTrue(self.store.get(PLACES, bed)["sleeping"])
        sketch = self.sketch()
        self.assertEqual([r.name for r in sketch.rooms], ["Bedroom"])
        self.assertIn("Left off the sketch by the household: Car.", self.text("/exit-sketch/text"))


class ReadyAndFlatTests(SketchTestCase):
    def test_draft_until_every_fact_is_recorded_and_reviewed_and_again_after_a_change(self):
        self.smith()
        self.assertIn("Draft home sketch.", self.text("/exit-sketch"))
        refused = self.post("/exit-sketch/reviewed")
        self.assertEqual(refused.status_code, 422)
        self.assertIn("A broad outside meeting place recorded", refused.get_data(as_text=True))
        self.post("/exit-sketch/household", {"meeting_place": "Letterbox at the front path", "help": "discussed",
                                             "building": "not_shared"})
        self.assertEqual(self.post("/exit-sketch/reviewed").status_code, 302)
        self.assertTrue(self.sketch().ready)
        self.assertIn("Ready to print for practice.", self.text("/exit-sketch/print"))
        self.store.update(PLACES, self.hall, {"name": "Landing"})
        self.assertFalse(self.sketch().ready)
        self.assertIn("Changed since the household's review", self.text("/exit-sketch"))

    def test_a_long_meeting_place_is_refused_in_plain_words(self):
        reply = self.post("/exit-sketch/household", {"meeting_place": "x" * 200})
        self.assertEqual(reply.status_code, 422)
        self.assertIn("Nothing was changed.", reply.get_data(as_text=True))

    def test_a_flat_asks_for_its_building_plan_and_never_chooses_leave_or_stay(self):
        settings.put(self.conn, "household.home_type", "apartment")
        self.room("Living room")
        for path in PAGES:
            page = self.text(path)
            self.assertIn(exit_sketch.FLAT_BANNER, page.replace("&#39;", "'"), path)
            self.assertNotIn("stay put in your flat", page.lower())
        check = next(c for c in self.sketch().checks if c["key"] == "building")
        self.assertFalse(check["recorded"])
        self.post("/exit-sketch/household", {"building": "checked"})
        self.assertTrue(next(c for c in self.sketch().checks if c["key"] == "building")["recorded"])

    def test_every_version_carries_the_warnings_and_the_countrys_number(self):
        self.smith()
        for path in PAGES:
            page = self.text(path).replace("&#39;", "'")
            for words in (exit_sketch.PRACTICE, exit_sketch.TWO_WAYS, "get out, stay out, and call 000",
                          exit_sketch.FOOTER):
                self.assertIn(words, page, path)
        settings.put(self.conn, "household.country", "New Zealand")
        self.assertIn("call your local emergency number", self.text("/exit-sketch/text"))


class DrawingTests(SketchTestCase):
    def ids(self, page, what):
        return set(int(i) for i in re.findall(rf'data-{what}="(\d+)"', page))

    def test_text_version_shows_the_same_rooms_and_connections_as_the_drawing(self):
        self.smith()
        self.join(self.room("Kitchen"), self.front, "opening")
        self.join(self.room("Study", "up1"), self.hall, "other")
        sketch = self.sketch()
        page = self.text("/exit-sketch")
        drawing = page[page.index('class="sketch-scroll"'):page.index('id="as-text"')]
        text = page[page.index('id="as-text"'):page.index('id="rooms"')]
        self.assertEqual(self.ids(drawing, "room"), set(sketch.inventory()["rooms"]))
        self.assertEqual(self.ids(text, "room"), set(sketch.inventory()["rooms"]))
        self.assertEqual(self.ids(drawing, "connection"), set(sketch.connections))
        self.assertEqual(self.ids(text, "connection"), set(sketch.connections))
        printed = self.text("/exit-sketch/print")
        self.assertEqual(self.ids(printed, "connection"), set(sketch.connections))
        self.assertEqual(self.ids(self.text("/exit-sketch/text"), "room"), set(sketch.inventory()["rooms"]))

    def test_the_same_records_always_give_the_same_layout(self):
        self.smith()
        self.join(self.room("Kitchen"), self.front, "opening")
        first = self.text("/exit-sketch/print")
        self.assertEqual(first, self.text("/exit-sketch/print"))
        order = [p.room.name for b in exit_drawing.blocks(self.sketch()) for p in b.placed]
        self.assertEqual(order, ["Front hall", "Kitchen", "Hallway", "Main bedroom"])

    def test_insertion_order_does_not_change_the_order(self):
        names = ["Zeta room", "Alpha room", "Middle room"]
        for name in names:
            self.room(name)
        order = [p.room.name for b in exit_drawing.blocks(self.sketch()) for p in b.placed]
        self.assertEqual(order, sorted(names))

    def test_many_rooms_continue_on_numbered_pages_and_none_is_cut_off(self):
        rooms = [self.room(f"Made-up room with a long name number {i:02d}", ("street", "up1", "up2")[i % 3])
                 for i in range(45)]
        for a, b in zip(rooms, rooms[3:]):
            self.join(a, b)
        sheet = self.text("/exit-sketch/print?paper=letter")
        pages = int(re.search(r"This sketch needs (\d+) pages", sheet).group(1))
        self.assertGreater(pages, 1)
        self.assertEqual(sheet.count(exit_sketch.DRAFT_MARK), pages)
        for n in range(1, pages + 1):
            self.assertIn(f"Page {n} of {pages}", sheet)
        self.assertEqual(self.ids(sheet, "room"), set(rooms))
        self.assertIn("(continued)", sheet)
        blocks = exit_drawing.blocks(self.sketch())
        exit_drawing.paginate(blocks)
        for n in range(1, pages + 1):
            used = sum(b.height for b in blocks if b.page == n)
            room = exit_drawing.FIRST_PAGE if n == 1 else exit_drawing.OTHER_PAGE
            self.assertTrue(used <= room or len([b for b in blocks if b.page == n]) == 1, n)

    def test_long_names_wrap_whole_and_are_never_cut(self):
        long = "Made-up very long room name that keeps going well past one line"
        self.room(long)
        block = exit_drawing.blocks(self.sketch())[0]
        self.assertEqual(" ".join(block.placed[0].name_lines), long)

    def test_with_no_rooms_the_page_says_what_to_do(self):
        self.assertIn("Add rooms and connections in Set up my home", self.text("/exit-sketch"))


class PrivacyTests(SketchTestCase):
    def test_private_values_never_reach_the_drawing_sheet_or_text(self):
        self.smith()
        self.store.update(PLACES, self.bed, {"notes": SECRETS[5]})
        self.store.update(CONNECTIONS, self.front_door, {"notes": SECRETS[6]})
        self.store.create("home_layout__exits", {"name": "Front door", "place": self.front,
                                                 "access_details": SECRETS[0], "route": "Down the stairs"})
        self.store.create("home_layout__shutoffs", {"name": "Meter box", "kind": "other",
                                                    "place": self.front, "access_details": SECRETS[1]})
        person = self.store.create("people__people", {"name": "Made-up Person"})
        self.store.create("people__important_info", {"person": person, "kind": "condition", "detail": SECRETS[4]})
        self.store.create("utilities__services", {"name": "Power", "kind": "electricity",
                                                  "account_number": SECRETS[2], "notes": SECRETS[3]})
        for path in PAGES:
            page = self.text(path)
            for secret in SECRETS:
                self.assertNotIn(secret, page, f"{secret} on {path}")
        self.assertNotIn("Made-up Person", self.text("/exit-sketch/print"))


class SwitchedOffAndDrillTests(SketchTestCase):
    def test_with_household_stock_off_the_sketch_says_it_cannot_show_current_routes(self):
        self.smith()
        settings.set_module_enabled(self.conn, "home_layout", False)
        settings.set_module_enabled(self.conn, "stock", False)
        page = self.text("/exit-sketch")
        self.assertIn("cannot show your current rooms or ways out", page)
        self.assertNotIn("Main bedroom", page)
        self.assertEqual(self.get("/exit-sketch/print").status_code, 404)
        self.assertEqual(self.post("/exit-sketch/household", {"meeting_place": "x"}).status_code, 404)

    def test_the_bedroom_fire_drill_step_about_another_way_links_to_the_sketch(self):
        reply = self.post("/drills/readiness/bedroom-fire-night/start")
        run_id = int(re.search(r"/runs/(\d+)", reply.headers["Location"]).group(1))
        steps = [self.text(f"/drills/readiness/bedroom-fire-night/runs/{run_id}/{n}") for n in (1, 2)]
        self.assertNotIn('href="/exit-sketch"', steps[0])  # the alarm step is not about ways out
        self.assertIn('href="/exit-sketch"', steps[1])
