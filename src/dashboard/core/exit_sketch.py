"""The way-out sketch's facts: rooms by floor, recorded connections and doors to outside, and what still needs checking.

Decision 0118, from Lane B's exit map draft. Everything is read fresh from Set up my home's Places and
Connections (decision 0103) plus four household answers kept in Settings, so a renamed, moved or deleted room
changes the sketch at once and nothing stale is kept. Only names, floors, kinds and the household's own
confirmations are read: notes, Home layout access details and People's private details never are. Nothing
here works out a safe, fastest or independent route; it says what was recorded and what needs checking.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field

from dashboard.core import settings

PLACES, CONNECTIONS = "stock__places", "stock__connections"
FLOORS = [("below", "Below street level"), ("street", "Street level"), ("up1", "One floor up"),
          ("up2", "Two floors up"), ("up3", "Three or more floors up"), (None, "Floor not given")]
FLOOR_WORDS = dict(FLOORS)
LEFT_OFF = "off"
KIND_WORDS = {"door": "Door", "opening": "Open doorway", "stairs": "Stairs", "outside_door": "Door to outside",
              "other": "Other connection"}
SOLID = ("door", "opening", "stairs")  # a recorded way between two rooms; "other" needs a household label first
HELP = {"discussed": "Discussed privately", "needs": "Needs discussion"}
BUILDING = {"checked": "I have checked its plan", "check": "I need to check", "not_shared": "Not a shared building"}
SHARED_HOMES = ("apartment", "townhouse")
MEETING_LIMIT = 120
KEY = "exit_sketch."  # the four household answers and the review, in core__settings

# The exact words, from Lane B's SKETCH.md and PRINT.md. None of them says a route is safe.
TITLE = "Our way-out sketch"
PRINT_TITLE = "Our way-out sketch — draft for practice"
INTRO = ("This shows rooms and ways out that your household recorded. Check each route in person, practise "
         "together and follow your building's and local fire service's guidance. It is not an emergency "
         "instruction.")
PRACTICE = "Practice aid only. This sketch is not a certified or safe route."
TWO_WAYS = "Check two ways out of every room in person, and practise them together."
FOOTER = ("This is a drawing of what you recorded. Check ways out in person, practise together and follow "
          "your building's and local fire service's instructions. It does not say a route is safe.")
LAYOUT_WARNING = "This page shows your home's layout. Keep copies where your household wants them."
DRAFT_MARK = "Draft — check ways out in person"
FLAT_BANNER = ("This sketch does not replace your building's fire plan. Ask the responsible manager or local fire "
               "service what applies here.")
NO_WAY = "No way out recorded for this room."
ONE_WAY = "Only one way out recorded. Check for another possible way with your household."
SHARED_WAY = "These ways may share the same exit. Check them in person."
NOT_OUTSIDE = "No possible way outside is recorded from this room yet."
# The same notes, shorter, under a room on the drawing; the legend and the text version carry the full words.
SHORT = {NO_WAY: "No way out recorded", ONE_WAY: "Only one way out recorded", NOT_OUTSIDE: "No way outside recorded yet"}
POSSIBLE = "Possible way outside · check in person"
WINDOW = "Possible window exit · check locally"
NEEDS_CHECKING = "Needs checking"
RECORDED = "Recorded"
LOCAL_NUMBER = "your local emergency number"


@dataclass
class Link:
    """One recorded connection seen from one room: its words, and whether it may be drawn as a way."""
    id: int
    kind: str
    other: int | None           # the room on the other side, when it is on the sketch
    other_name: str | None      # the other side's name, even when it is left off the sketch
    words: str                  # "Stairs to Front hall (Street level)", "Door to outside: destination needs checking"
    short: str                  # the label on a line: Door, Open doorway, Stairs, Other · needs checking
    solid: bool                 # recorded by the household as a door, doorway or stairs, or a confirmed door out
    outside: bool = False       # a door to outside (whatever its destination)
    exit: bool = False          # a door to outside the household confirmed reaches outside


@dataclass
class Room:
    """A room or area on the sketch, with its connections and what still needs checking about it."""
    id: int
    name: str
    floor: str | None
    sleeping: bool
    window: bool
    links: list[Link] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)   # the exact route words: No way out recorded, …

    @property
    def floor_words(self) -> str:
        return FLOOR_WORDS[self.floor]


@dataclass
class Sketch:
    """Everything the drawing, the text version and the sheet show: the same facts, read once."""
    rooms: list[Room]
    floors: list[tuple[str | None, str, list[Room]]]
    left_off: list[dict]                 # places the household chose to leave off ({"id", "name"})
    connections: list[int]               # every connection the sketch shows, by record ID
    meeting: str
    help: str | None
    building: str | None
    home_type: str
    checks: list[dict]
    reviewed_on: str | None
    stamp: str
    number: str | None                   # the checked emergency number for the household's country
    reviewed_stamp: str | None = None    # the fingerprint saved with the household's last review

    @property
    def shared_building(self) -> bool:
        """A flat or shared building: its own fire plan comes first, and the sketch says so."""
        if self.building == "not_shared":
            return False
        return self.home_type in SHARED_HOMES or self.building in ("checked", "check")

    @property
    def reviewed_current(self) -> bool:
        return bool(self.reviewed_on) and self.reviewed_stamp == self.stamp

    @property
    def changed_since_review(self) -> bool:
        return bool(self.reviewed_on) and self.reviewed_stamp != self.stamp

    @property
    def ready(self) -> bool:
        """Ready to print for practice: every fact recorded and reviewed since the last change. Not a safety check."""
        return all(c["recorded"] for c in self.checks) and self.reviewed_current

    @property
    def fire_words(self) -> str:
        return f"In a fire: get out, stay out, and call {self.number or LOCAL_NUMBER}."

    def inventory(self) -> dict:
        """The facts both versions must show, by record ID, for comparing the drawing with the text."""
        return {"rooms": sorted(r.id for r in self.rooms), "connections": sorted(self.connections),
                "floors": {r.id: r.floor for r in self.rooms}, "meeting": self.meeting,
                "checks": [(c["key"], c["recorded"]) for c in self.checks]}


def ready_to_read(registry: dict) -> bool:
    """True when Household stock is on with its places and connections, so the sketch has something to read."""
    return PLACES in registry and CONNECTIONS in registry


def household(conn: sqlite3.Connection) -> dict:
    """The household's four answers for the sketch, as saved, each blank when never given."""
    get = lambda name: settings.get(conn, KEY + name)  # noqa: E731
    meeting = get("meeting_place")
    return {"meeting": meeting.strip() if isinstance(meeting, str) else "",
            "help": get("help") if get("help") in HELP else None,
            "building": get("building") if get("building") in BUILDING else None,
            "reviewed": get("reviewed") if isinstance(get("reviewed"), dict) else None}


def save_household(conn: sqlite3.Connection, meeting: str, help_answer: str, building: str) -> dict:
    """Save the meeting place, help-to-leave and building-plan answers; return problems in plain words."""
    problems = {}
    meeting = " ".join((meeting or "").split())
    if len(meeting) > MEETING_LIMIT:
        problems["meeting_place"] = f"Keep the meeting place to {MEETING_LIMIT} characters: broad words, no address."
    if help_answer not in ("", *HELP):
        problems["help"] = "Choose one of the listed answers about help to leave."
    if building not in ("", *BUILDING):
        problems["building"] = "Choose one of the listed answers about the building's fire plan."
    if not problems:
        settings.put(conn, KEY + "meeting_place", meeting)
        settings.put(conn, KEY + "help", help_answer or None)
        settings.put(conn, KEY + "building", building or None)
    return problems


def mark_reviewed(conn: sqlite3.Connection, sketch: Sketch, today: str) -> list[str]:
    """Record that the household reviewed the sketch today; refused, with what is missing, until all is recorded."""
    missing = [c["title"] for c in sketch.checks if not c["recorded"]]
    if not missing:
        settings.put(conn, KEY + "reviewed", {"on": today, "stamp": sketch.stamp})
    return missing


def _top(rows: dict[int, dict], place_id: int | None) -> int | None:
    """The room or area (a place inside nothing) a place sits in; a storage spot's connection is its room's."""
    seen = set()
    while place_id in rows and rows[place_id]["inside"] is not None and place_id not in seen:
        seen.add(place_id)
        place_id = rows[place_id]["inside"]
    return place_id if place_id in rows else None


def _door_out_words(destination: str | None, into: str | None) -> tuple[str, str, bool]:
    """The words for a door to outside, by the destination the household confirmed (blank is Needs checking)."""
    where = f" (into {into})" if into else ""
    if destination == "outside":
        return f"Door to outside{where}: {POSSIBLE}", POSSIBLE, True
    if destination == "shared":
        return (f"Door to outside{where}: leads to a shared building area, not outside. Check your building's "
                f"plan", "Shared building area · not outside", False)
    return f"Door to outside{where}: destination {NEEDS_CHECKING.lower()}", f"? {NEEDS_CHECKING}", False


def _order(rooms: list[Room]) -> list[Room]:
    """A floor's rooms in a steady order: from each door to outside, through the rooms it connects to, then the rest.

    Ties go by name and then record ID, so the same records always give the same layout."""
    key = lambda r: (r.name.lower(), r.id)  # noqa: E731
    here = {r.id: r for r in rooms}
    starts = sorted((r for r in rooms if any(l.outside for l in r.links)), key=key)
    seen, ordered = set(), []
    for start in starts + sorted(rooms, key=key):
        if start.id in seen:
            continue
        queue = [start]
        seen.add(start.id)
        while queue:
            room = queue.pop(0)
            ordered.append(room)
            for nxt in sorted((here[l.other] for l in room.links if l.other in here), key=key):
                if nxt.id not in seen:
                    seen.add(nxt.id)
                    queue.append(nxt)
    return ordered


def _exits(rooms: dict[int, Room], start: int, without: int | None = None) -> set[int]:
    """Doors to outside the household confirmed, reachable from a room over recorded doors, doorways and stairs."""
    found, seen, queue = set(), {start}, [start]
    while queue:
        room = rooms[queue.pop(0)]
        for link in room.links:
            if link.exit:
                found.add(link.id)
            elif link.solid and link.other in rooms and link.other not in seen and link.other != without:
                seen.add(link.other)
                queue.append(link.other)
    return found


def _route_notes(rooms: dict[int, Room], room: Room) -> list[str]:
    """What the recorded connections cannot show about a room. Never "two ways out": only possibilities and gaps."""
    if not room.links:
        return [NO_WAY]
    notes = []
    if len(room.links) == 1:
        notes.append(ONE_WAY)
    reachable = _exits(rooms, room.id)
    if not reachable:
        notes.append(NOT_OUTSIDE)
        return notes
    if len(room.links) > 1:
        shared = []
        for other in sorted(rooms.values(), key=lambda r: (r.name.lower(), r.id)):
            if other.id != room.id and not _exits(rooms, room.id, without=other.id) - \
                    {l.id for l in other.links if l.exit}:
                shared.append(other.name)
        doors = [] if len(reachable) > 1 else ["the same door to outside"]
        if shared or doors:
            notes.append(f"{SHARED_WAY} Shared: {', '.join(shared + doors)}.")
    return notes


def _stamp(rooms: list[Room], facts: dict) -> str:
    """A fingerprint of what the household reviewed: names, floors, kinds and answers, never kept as text."""
    data = {"rooms": [(r.id, r.name, r.floor, r.sleeping, r.window, [(l.id, l.kind, l.other, l.words)
                                                                       for l in r.links]) for r in rooms],
            "facts": [facts["meeting"], facts["help"], facts["building"]]}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def _checks(rooms: list[Room], facts: dict, home_type: str) -> list[dict]:
    """The five Check together facts, each Recorded or Needs checking: a completeness check, never a safety score."""
    sleeping = [r for r in rooms if r.sleeping]
    unreviewed = [r.name for r in sleeping if r.floor is None or not r.links]
    doors = [l for r in rooms for l in r.links if l.outside and l.kind == "outside_door"]
    unconfirmed = sorted({l.id for l in doors if l.short.startswith("?")})
    checks = [
        {"key": "sleeping", "title": "Each sleeping room reviewed",
         "recorded": bool(sleeping) and not unreviewed,
         "detail": ("Mark the rooms people sleep in." if not sleeping else
                    f"Give a floor and a connection for: {', '.join(unreviewed)}." if unreviewed else
                    f"{len(sleeping)} sleeping room{'s' if len(sleeping) != 1 else ''}, each with a floor and a connection.")},
        {"key": "destinations", "title": "Outside destination confirmed",
         "recorded": bool(doors) and not unconfirmed,
         "detail": ("No door to outside is recorded yet." if not doors else
                    (f"{len(unconfirmed)} doors to outside still say Needs checking." if len(unconfirmed) != 1
                     else "1 door to outside still says Needs checking.")
                    if unconfirmed else "Every door to outside has the destination your household confirmed.")},
        {"key": "meeting", "title": "A broad outside meeting place recorded", "recorded": bool(facts["meeting"]),
         "detail": facts["meeting"] or "Not recorded."},
        {"key": "help", "title": "Help to leave discussed privately", "recorded": facts["help"] == "discussed",
         "detail": HELP.get(facts["help"], "Needs discussion") + "."},
    ]
    relevant = home_type in SHARED_HOMES or facts["building"] in ("checked", "check") or not home_type
    if facts["building"] in ("checked", "not_shared"):
        building = {"recorded": True, "detail": BUILDING[facts["building"]] + "."}
    elif relevant:
        building = {"recorded": False, "detail": BUILDING.get(facts["building"], NEEDS_CHECKING) + "."}
    else:
        building = {"recorded": True, "detail": "Not a shared building (the kind of home in Settings)."}
    checks.append(dict(building, key="building", title="Building's own fire plan checked, when relevant"))
    return checks


def read(conn: sqlite3.Connection, registry: dict, number: str | None = None) -> Sketch:
    """Read the sketch's facts fresh from the household's places, connections and answers."""
    rows = {r["id"]: dict(r) for r in conn.execute(
        f"SELECT id, name, inside, floor, sleeping, window_exit FROM {PLACES} WHERE deleted_at IS NULL")}
    tops = {i: r for i, r in rows.items() if r["inside"] is None}
    rooms = {i: Room(i, r["name"], r["floor"] if r["floor"] in FLOOR_WORDS else None, bool(r["sleeping"]),
                     bool(r["window_exit"])) for i, r in tops.items() if r["floor"] != LEFT_OFF}
    left_off = sorted(({"id": i, "name": r["name"]} for i, r in tops.items() if r["floor"] == LEFT_OFF),
                      key=lambda p: (p["name"].lower(), p["id"]))
    shown = set()
    for c in conn.execute(f"SELECT id, place, connects_to, kind, destination FROM {CONNECTIONS} "
                          f"WHERE deleted_at IS NULL ORDER BY id"):
        a, b = _top(rows, c["place"]), _top(rows, c["connects_to"])
        kind = c["kind"] if c["kind"] in KIND_WORDS else "other"
        if a is None or a == b:
            continue  # a connection between two spots of one room is not a way between rooms
        if kind == "outside_door":
            into = rows[b]["name"] if b is not None else None
            if a in rooms:
                words, short, confirmed = _door_out_words(c["destination"], into)
                rooms[a].links.append(Link(c["id"], kind, None, into, words, short, confirmed, True, confirmed))
                shown.add(c["id"])
            if b in rooms:
                rooms[b].links.append(Link(c["id"], kind, a if a in rooms else None, rows[a]["name"],
                                           f"Door to {rows[a]['name']} (a door to outside of {rows[a]['name']})",
                                           "Door", False))
                shown.add(c["id"])
            continue
        if b is None:
            continue
        for here, there in ((a, b), (b, a)):
            if here not in rooms:
                continue
            other = rooms.get(there)
            name = rows[there]["name"]
            how = KIND_WORDS[kind]
            if other is None:
                where = " (left off the sketch)"
            elif other.floor != rooms[here].floor:
                where = f" ({other.floor_words})"
            else:
                where = ""
            solid = kind in SOLID
            words = f"{how} to {name}{where}" + ("" if solid else f": {NEEDS_CHECKING.lower()}")
            rooms[here].links.append(Link(c["id"], kind, there if other else None, name, words,
                                          how if solid else f"Other · {NEEDS_CHECKING.lower()}", solid))
            shown.add(c["id"])
    for room in rooms.values():
        room.links.sort(key=lambda l: (not l.outside, (l.other_name or "").lower(), l.id))
        room.notes = _route_notes(rooms, room)
    facts = household(conn)
    home_type = settings.get(conn, "household.home_type", "") or ""
    floors = []
    for key, words in FLOORS:
        on_floor = _order([r for r in rooms.values() if r.floor == key])
        if on_floor:
            floors.append((key, words, on_floor))
    ordered = [r for _, _, listed in floors for r in listed]
    reviewed = facts["reviewed"] or {}
    return Sketch(ordered, floors, left_off, sorted(shown), facts["meeting"], facts["help"], facts["building"],
                  home_type, _checks(ordered, facts, home_type), reviewed.get("on"), _stamp(ordered, facts), number,
                  reviewed.get("stamp"))
