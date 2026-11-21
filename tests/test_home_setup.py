"""Tests for Set up my home: rooms, storage spots inside them and the connections between rooms (decision 0103)."""
import json
import shutil
from datetime import datetime, timezone

from support import ROOT, TempDirTestCase
from dashboard import __version__
from dashboard.core import backups, db, export, helpers, modules, records, restore, settings, startup, sync
from dashboard.web.app import create_app
from test_export import read_csv, read_zip

PORT = 5131
BASE = f"http://127.0.0.1:{PORT}"
PLACES, CONNECTIONS = "stock__places", "stock__connections"


class HomeSetupTestCase(TempDirTestCase):
    """A fresh household with People and Household stock, signed in to the pages."""

    def setUp(self):
        super().setUp()
        for name in ("people", "stock"):
            shutil.copytree(ROOT / "modules" / name, self.tmp / "modules" / name)
        self.data = self.tmp / "data"
        self.report = startup.prepare(self.data, self.tmp / "modules")
        self.assertEqual(self.report.module_problems, {})
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.registry = records.build_registry(self.report.loaded)
        self.store = records.Records(self.conn, self.registry)
        self.app = create_app("t", lambda: None, self.report, data_dir=self.data, session_key="k")
        self.app.config["PORT"] = PORT
        self.client = self.app.test_client()
        self.client.get("/?key=k", base_url=BASE)

    def get(self, path):
        return self.client.get(path, base_url=BASE)

    def post(self, path, data=None):
        return self.client.post(path, data=dict(data or {}, _csrf=self.app.config["CSRF_TOKEN"]), base_url=BASE)

    def place(self, name, inside=None):
        return self.store.create(PLACES, {"name": name, "inside": inside})

    def live(self, table):
        return [dict(r) for r in self.conn.execute(f"SELECT * FROM {table} WHERE deleted_at IS NULL ORDER BY id")]


class ReachableTests(HomeSetupTestCase):
    def test_welcome_ends_by_offering_it_and_it_can_be_skipped(self):
        response = self.post("/setup", {"name_1": "Person A", "modules": ["people", "stock"]})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/set-up-home?welcome=1", response.headers["Location"])
        page = self.get("/set-up-home?welcome=1").get_data(as_text=True)
        self.assertIn("Setup is saved.", page)
        self.assertIn('href="/" id="skip"', page)  # skippable: one link straight to Home
        self.assertEqual(self.get("/").status_code, 200)  # setup is done whether or not the step is used

    def test_without_household_stock_the_welcome_goes_straight_home(self):
        response = self.post("/setup", {"name_1": "Person A", "modules": ["people"]})
        self.assertEqual(response.headers["Location"], "/")
        page = self.get("/set-up-home").get_data(as_text=True)
        self.assertIn("Switch it on in", page)
        self.assertNotIn('id="my-home"', self.get("/").get_data(as_text=True))
        self.assertEqual(self.post("/set-up-home/places", {"name": "Kitchen"}).status_code, 404)

    def test_home_and_settings_always_link_to_it_even_with_places_recorded(self):
        settings.put(self.conn, "setup.done", True)
        home = self.get("/").get_data(as_text=True)
        self.assertIn('href="/set-up-home"', home)
        self.assertIn("Nothing added yet.", home)
        kitchen = self.place("Kitchen")
        self.place("Pantry", kitchen)
        home = self.get("/").get_data(as_text=True)
        self.assertIn('href="/set-up-home"', home)
        self.assertIn("1 room or area, 1 storage spot, 0 connections", home)
        self.assertIn('href="/set-up-home"', self.get("/settings").get_data(as_text=True))


class RoomsAndSpotsTests(HomeSetupTestCase):
    def setUp(self):
        super().setUp()
        settings.put(self.conn, "setup.done", True)

    def test_rooms_and_nested_storage_spots_show_as_one_tree(self):
        response = self.post("/set-up-home/places", {"name": "Kitchen", "form": "room"})
        self.assertEqual(response.status_code, 302)
        kitchen = self.live(PLACES)[0]["id"]
        self.assertIn(f"#place-{kitchen}", response.headers["Location"])
        self.post("/set-up-home/places", {"name": "Pantry", "inside": str(kitchen)})
        pantry = self.live(PLACES)[1]["id"]
        self.post("/set-up-home/places", {"name": "Shelf 3", "inside": str(pantry)})
        self.assertEqual([(p["name"], p["inside"]) for p in self.live(PLACES)],
                         [("Kitchen", None), ("Pantry", kitchen), ("Shelf 3", pantry)])
        page = self.get(f"/set-up-home?done=added&id={self.live(PLACES)[2]['id']}").get_data(as_text=True)
        self.assertIn("Added Kitchen › Pantry › Shelf 3.", page)
        self.assertIn(f'id="place-{kitchen}"', page)
        self.assertNotIn(f'id="place-{pantry}"', page)  # a storage spot sits in its room's card
        self.assertIn("1 room or area · 2 storage spots", page)

    def test_a_blank_name_is_refused_in_plain_words_and_nothing_is_added(self):
        response = self.post("/set-up-home/places", {"name": "  ", "form": "room"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("That room was not added. Name is required.", response.get_data(as_text=True))
        self.assertEqual(self.live(PLACES), [])

    def test_rename_and_move_and_a_place_cannot_go_inside_itself(self):
        kitchen, shed = self.place("Kitchen"), self.place("Shed")
        pantry = self.place("Pantry", kitchen)
        self.post(f"/set-up-home/places/{pantry}", {"name": "Tool rack", "inside": str(shed)})
        self.assertEqual(self.store.get(PLACES, pantry)["name"], "Tool rack")
        self.assertEqual(self.store.get(PLACES, pantry)["inside"], shed)
        response = self.post(f"/set-up-home/places/{shed}", {"name": "Shed", "inside": str(pantry)})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Nothing was changed.", response.get_data(as_text=True))
        self.post(f"/set-up-home/places/{pantry}", {"name": "Tool rack", "inside": ""})  # out of every place
        self.assertIsNone(self.store.get(PLACES, pantry)["inside"])

    def test_a_room_with_spots_or_things_in_it_is_not_deleted(self):
        kitchen = self.place("Kitchen")
        self.place("Pantry", kitchen)
        response = self.post(f"/set-up-home/places/{kitchen}/delete")
        self.assertEqual(response.status_code, 409)
        self.assertIn("Kitchen was not deleted", response.get_data(as_text=True))
        self.assertEqual(len(self.live(PLACES)), 2)

    def test_the_page_works_without_scripts_and_labels_every_field(self):
        kitchen = self.place("Kitchen")
        self.place("Pantry", kitchen)
        page = self.get("/set-up-home").get_data(as_text=True)
        body = page.split("<main>")[1].split("</main>")[0]
        self.assertNotIn("<script", body)  # every change is an ordinary form
        for field in (f"spot-{kitchen}", f"join-{kitchen}", f"join-kind-{kitchen}", f"name-{kitchen}", "new-room"):
            self.assertIn(f'for="{field}"', body)
            self.assertIn(f'id="{field}"', body)
        self.assertIn("<summary>Connect Kitchen to another place</summary>", body)


class ConnectionTests(HomeSetupTestCase):
    def setUp(self):
        super().setUp()
        settings.put(self.conn, "setup.done", True)
        self.hall, self.kitchen = self.place("Hallway"), self.place("Kitchen")

    def join(self, place, other, kind="door"):
        return self.post("/set-up-home/connections", {"place": str(place), "connects_to": str(other), "kind": kind})

    def test_connections_show_on_both_rooms_and_can_be_removed(self):
        self.assertEqual(self.join(self.hall, self.kitchen, "opening").status_code, 302)
        page = self.get("/set-up-home").get_data(as_text=True)
        self.assertEqual(page.count("Open doorway or archway</span>"), 2)  # on the Hallway and the Kitchen
        connection = self.live(CONNECTIONS)[0]["id"]
        self.assertIn("Connected: Hallway to Kitchen: Open doorway or archway.",
                      self.get(f"/set-up-home?done=joined&id={connection}").get_data(as_text=True))
        self.post(f"/set-up-home/connections/{connection}/delete", {"from": str(self.kitchen)})
        self.assertEqual(self.live(CONNECTIONS), [])

    def test_the_same_two_rooms_either_way_round_and_a_room_to_itself_are_refused(self):
        self.join(self.hall, self.kitchen)
        again = self.join(self.kitchen, self.hall, "opening")
        self.assertEqual(again.status_code, 422)
        self.assertIn("Connects to is already joined to it.", again.get_data(as_text=True))
        itself = self.join(self.hall, self.hall)
        self.assertEqual(itself.status_code, 422)
        self.assertIn("Connects to can&#39;t be the same as “From”", itself.get_data(as_text=True))
        self.assertEqual(len(self.live(CONNECTIONS)), 1)
        with self.assertRaises(records.ValidationError):  # the same rule holds on the ordinary form and for helpers
            self.store.create(CONNECTIONS, {"place": self.kitchen, "connects_to": self.hall})
        with self.assertRaises(records.ValidationError):
            self.store.update(CONNECTIONS, self.live(CONNECTIONS)[0]["id"], {"connects_to": self.hall})

    def test_doors_to_outside_and_blank_needs_outside(self):
        response = self.post("/set-up-home/connections", {"place": str(self.hall), "connects_to": "outside",
                                                          "kind": "door"})
        self.assertEqual(response.status_code, 302)
        row = self.live(CONNECTIONS)[0]
        self.assertEqual((row["connects_to"], row["kind"]), (None, "outside_door"))
        self.post("/set-up-home/connections", {"place": str(self.hall), "connects_to": "outside"})  # a side door too
        self.assertEqual(len(self.live(CONNECTIONS)), 2)
        blank = self.post("/set-up-home/connections", {"place": str(self.kitchen), "connects_to": "", "kind": "door"})
        self.assertEqual(blank.status_code, 422)
        self.assertIn("another place, or Outside", blank.get_data(as_text=True))
        with self.assertRaises(records.ValidationError):
            self.store.create(CONNECTIONS, {"place": self.kitchen, "kind": "door"})
        yard = self.place("Backyard")
        self.join(self.kitchen, yard, "outside_door")  # a door into a yard listed as a place leads outside too
        page = self.get("/set-up-home").get_data(as_text=True)
        self.assertIn("3 doors to outside", page)

    def test_deleting_a_room_takes_its_connections_and_restoring_brings_them_back(self):
        shed = self.place("Shed")
        self.join(self.hall, self.kitchen)
        self.join(self.kitchen, shed)
        response = self.post(f"/set-up-home/places/{self.kitchen}/delete")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.live(CONNECTIONS), [])
        page = self.get(response.headers["Location"]).get_data(as_text=True)
        self.assertIn("Deleted Kitchen, and its connections with it.", page)
        self.assertIn(f'href="/t/stock__places/{self.kitchen}"', page)
        self.store.restore(PLACES, self.kitchen)
        self.assertEqual(len(self.live(CONNECTIONS)), 2)

    def test_restoring_a_removed_connection_that_was_added_again_is_refused(self):
        self.join(self.hall, self.kitchen)
        first = self.live(CONNECTIONS)[0]["id"]
        self.store.delete(CONNECTIONS, first)
        self.join(self.kitchen, self.hall, "opening")
        with self.assertRaises(records.ValidationError):
            self.store.restore(CONNECTIONS, first)
        self.assertEqual(len(self.live(CONNECTIONS)), 1)


class DataTests(HomeSetupTestCase):
    """The new table is declared like any other, so export, backups, sync and helpers cover it."""

    def setUp(self):
        super().setUp()
        self.hall, self.kitchen = self.place("Hallway"), self.place("Kitchen")
        self.joined = self.store.create(CONNECTIONS, {"place": self.hall, "connects_to": self.kitchen})
        self.out = self.store.create(CONNECTIONS, {"place": self.hall, "kind": "outside_door", "notes": "Front door"})

    def test_export_has_a_file_for_connections_with_place_names(self):
        files = read_zip(export.build(self.conn, self.registry, __version__, False,
                                      datetime(2026, 11, 21, tzinfo=timezone.utc)))
        rows = read_csv(files[f"{CONNECTIONS}.csv"])
        text = json.dumps(rows)
        self.assertEqual(len(rows), 3)
        self.assertIn("Kitchen", text)
        self.assertIn("Door to outside", text)
        manifest = json.loads(files["manifest.json"])
        self.assertIn(f"{CONNECTIONS}.csv", {t["file"] for t in manifest["tables"]})

    def test_a_backup_restored_brings_the_connections_back(self):
        backups.daily(self.data)
        self.store.delete(PLACES, self.kitchen)
        self.conn.close()
        name = next(p.name for p in (self.data / "backups").glob("daily-*.db"))
        restore.restore(self.data, restore.get({"data": self.data / "backups"}, "data", name), self.report.loaded)
        self.conn = db.connect(self.data / "dashboard.db")
        self.addCleanup(self.conn.close)
        self.assertEqual(len(self.live(CONNECTIONS)), 2)

    def test_the_change_log_covers_connections_with_permanent_ids(self):
        gid = lambda table, rid: self.conn.execute(  # noqa: E731
            f"SELECT global_id FROM {table} WHERE id = ?", (rid,)).fetchone()[0]
        made = [e for e in sync.changes(self.conn, 0, limit=1000) if e["global_id"] == gid(CONNECTIONS, self.joined)]
        self.assertEqual([(e["action"], e["revision"]) for e in made], [("create", 1)])
        self.assertEqual(made[0]["patch"]["place"], gid(PLACES, self.hall))
        self.assertEqual(made[0]["patch"]["connects_to"], gid(PLACES, self.kitchen))
        start = self.conn.execute("SELECT MAX(seq) FROM core__sync_changes").fetchone()[0]
        self.store.delete(PLACES, self.kitchen)
        after = [(e["table_name"], e["action"]) for e in sync.changes(self.conn, start, limit=1000)]
        self.assertIn((CONNECTIONS, "delete"), after)  # the connection goes with the room, in the log too
        self.assertTrue(all(c.travels == "always" for c in self.registry[CONNECTIONS].table.columns.values()))
        self.assertEqual(sync.check(self.conn, self.registry), [])

    def test_helpers_read_connections_only_when_given_household_stock(self):
        stock, stock_key = helpers.issue(self.conn, self.data, "Pantry helper", "read", ["stock"])
        people, people_key = helpers.issue(self.conn, self.data, "People helper", "read", ["people"])
        self.assertIn(CONNECTIONS, helpers.allowed_registry(self.registry, stock))
        self.assertNotIn(CONNECTIONS, helpers.allowed_registry(self.registry, people))
        ok = self.client.get(f"/api/v1/tables/{CONNECTIONS}/records", base_url=BASE,
                             headers={"Authorization": f"Bearer {stock_key}"})
        self.assertEqual(ok.status_code, 200)
        self.assertIn("Front door", ok.get_data(as_text=True))
        refused = self.client.get(f"/api/v1/tables/{CONNECTIONS}/records", base_url=BASE,
                                  headers={"Authorization": f"Bearer {people_key}"})
        self.assertIn(refused.status_code, (403, 404))
        self.assertNotIn("Front door", refused.get_data(as_text=True))


class PairDeclarationTests(TempDirTestCase):
    def problems(self, pair):
        tables = ('[tables.rooms]\ntitle = "Rooms"\ncolumns.name = { type = "text", required = true }\n\n'
                  '[tables.links]\ntitle = "Links"\n'
                  'columns.a = { type = "link", to = "rooms", required = true, on_delete = "cascade" }\n'
                  'columns.b = { type = "link", to = "rooms", on_delete = "cascade" }\n'
                  'columns.how = { type = "choice", choices = ["door", "outside"] }\n' + pair)
        self.make_module(tables=tables, labels=None)
        found, failures = modules.discover(self.tmp / "modules")
        return " ".join(p for listed in failures.values() for p in listed) if failures \
            else found[0].tables["links"].pair

    def test_a_good_pair_loads_and_mistakes_are_explained(self):
        self.assertEqual(self.problems('pair = { columns = ["a", "b"], blank_when = { how = "outside" } }\n'),
                         {"columns": ["a", "b"], "blank_when": {"how": "outside"}})
        self.assertIn("two different link columns", self.problems('pair = { columns = ["a", "a"] }\n'))
        self.assertIn("two different link columns", self.problems('pair = { columns = ["a", "how"] }\n'))
        self.assertIn("must be required", self.problems('pair = { columns = ["b", "a"] }\n'))
        self.assertIn("blank_when names one choice", self.problems(
            'pair = { columns = ["a", "b"], blank_when = { how = "window" } }\n'))
        self.assertIn("unknown setting", self.problems('pair = { columns = ["a", "b"], unique = true }\n'))
