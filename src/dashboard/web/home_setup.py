"""Set up my home: rooms and areas, the storage spots inside them, and which rooms connect, on one page."""
from __future__ import annotations

import csv

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from dashboard.core import records
from dashboard.web import display

home_setup = Blueprint("home_setup", __name__)
PLACES = "stock__places"
CONNECTIONS = "stock__connections"
OUTSIDE = "outside"  # the "Connects to" choice for a door straight outside: no place is stored
NAME_LIMIT = 80


def _store() -> records.Records:
    return records.Records(current_app.config["CONNECT"](), current_app.config["REGISTRY_FOR_REQUEST"]())


def _ready(store: records.Records) -> bool:
    """True when Household stock is switched on with its places and the connections between them."""
    return PLACES in store.registry and CONNECTIONS in store.registry


def summary(conn, registry: dict) -> dict | None:
    """How many rooms, storage spots and connections are recorded, for the Set up my home card on Home."""
    if PLACES not in registry or CONNECTIONS not in registry:
        return None
    rooms, spots = conn.execute(f"SELECT COALESCE(SUM(inside IS NULL), 0), COALESCE(SUM(inside IS NOT NULL), 0) "
                                f"FROM {PLACES} WHERE deleted_at IS NULL").fetchone()
    joined = conn.execute(f"SELECT COUNT(*) FROM {CONNECTIONS} WHERE deleted_at IS NULL").fetchone()[0]
    return {"rooms": rooms, "spots": spots, "connections": joined}


def _common_names(info) -> dict[str, list[str]]:
    """Room names and storage-spot names to pick from while typing, from the module's places.csv."""
    found = {"rooms": [], "spots": []}
    path = info.module.folder / "places.csv"
    if not path.exists():
        return found
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            found["rooms" if row.get("kind") == "room" else "spots"].append(row.get("name", ""))
    return found


def _places(store: records.Records) -> tuple[list[dict], dict[int, dict]]:
    """Every place with its full path and depth, sorted so each room is followed by what is inside it."""
    info = store.registry[PLACES]
    rows = {r["id"]: dict(r) for r in store.page(PLACES, limit=records.MAX_PAGE)}
    offset = records.MAX_PAGE
    while len(rows) == offset:  # a household with very many places: read them all
        rows.update({r["id"]: dict(r) for r in store.page(PLACES, offset=offset, limit=records.MAX_PAGE)})
        offset += records.MAX_PAGE
    places = []
    for place_id, row in rows.items():
        path = display.path_name(info, rows, row)
        places.append({"id": place_id, "name": row["name"], "path": path, "inside": row["inside"],
                       "depth": path.count(display.PATH_SEPARATOR), "notes": row.get("notes")})
    places.sort(key=lambda p: p["path"].lower())
    return places, {p["id"]: p for p in places}


def _top(places: list[dict], by_id: dict[int, dict], place: dict) -> int:
    """The room or area (a place inside nothing) that a place sits in."""
    seen = set()
    while place["inside"] in by_id and place["id"] not in seen:
        seen.add(place["id"])
        place = by_id[place["inside"]]
    return place["id"]


def _connections(store: records.Records, by_id: dict[int, dict]) -> dict[int, list[dict]]:
    """Each place's connections, seen from that place: the other side (or outside) and how."""
    info = store.registry[CONNECTIONS]
    kinds = {c.key: c.label for c in info.table.columns["kind"].choices}
    found: dict[int, list[dict]] = {}
    for row in store.page(CONNECTIONS, limit=records.MAX_PAGE):
        ends = [(row["place"], row["connects_to"]), (row["connects_to"], row["place"])]
        for here, there in ends:
            if here not in by_id:
                continue
            found.setdefault(here, []).append({
                "id": row["id"], "kind": row["kind"], "how": kinds.get(row["kind"], row["kind"]),
                "other": by_id[there]["path"] if there in by_id else None, "notes": row.get("notes"),
                "outside": row["kind"] == "outside_door" or there is None})
    for listed in found.values():
        listed.sort(key=lambda c: (c["other"] is None, (c["other"] or "").lower()))
    return found


def _rooms(places: list[dict], by_id: dict[int, dict], joined: dict[int, list[dict]]) -> list[dict]:
    """The page's cards: one per room or area, with the spots inside it and every connection."""
    rooms: dict[int, dict] = {}
    for place in places:
        top = _top(places, by_id, place)
        room = rooms.setdefault(top, {"place": by_id[top], "inside": [], "connections": joined.get(top, [])})
        if place["id"] != top:
            room["inside"].append(dict(place, connections=joined.get(place["id"], [])))
    return [rooms[p["id"]] for p in places if p["id"] in rooms]


def _within(places: list[dict], by_id: dict[int, dict], room_id: int) -> list[dict]:
    """A room and everything inside it, for choosing where a new storage spot goes."""
    return [p for p in places if _top(places, by_id, p) == room_id]


def _problem_text(info, problems: dict[str, str]) -> str:
    """"Name is required." from a refused save, in the household's own labels."""
    parts = []
    for field, message in problems.items():
        column = info.table.columns.get(field)
        label = display.column_label(info, column) if column is not None else ""
        parts.append(f"{label} {message}".strip() if label else message[:1].upper() + message[1:])
    return " ".join(parts)


def _page(store: records.Records, problem: str | None = None, typed: dict | None = None, status: int = 200):
    welcome = request.values.get("welcome") == "1"
    if not _ready(store):
        return render_template("home_setup.html", ready=False, welcome=welcome), status
    places, by_id = _places(store)
    joined = _connections(store, by_id)
    info = store.registry[CONNECTIONS]
    kinds = [(c.key, c.label) for c in info.table.columns["kind"].choices]
    rooms = _rooms(places, by_id, joined)
    for room in rooms:
        room["within"] = _within(places, by_id, room["place"]["id"])
    every = {c["id"]: c for listed in joined.values() for c in listed}
    return render_template("home_setup.html", ready=True, welcome=welcome, rooms=rooms, places=places,
                           kinds=kinds, outside=OUTSIDE, problem=problem, typed=typed or {},
                           names=_common_names(store.registry[PLACES]), notice=_notice(store, by_id),
                           connection_count=len(every), ways_out=sum(1 for c in every.values() if c["outside"])), status


def _notice(store: records.Records, by_id: dict[int, dict]) -> dict | None:
    """The words shown after a change, worked out from the record it was about (nothing typed is in the address)."""
    done, record_id = request.args.get("done"), request.args.get("id", type=int)
    if not done or record_id is None:
        return None
    if done in ("added", "changed"):
        place = by_id.get(record_id)
        return {"text": f"{'Added' if done == 'added' else 'Saved'} {place['path']}."} if place else None
    if done == "deleted":
        try:
            row = store.get(PLACES, record_id, include_deleted=True)
        except records.RecordNotFound:
            return None
        return {"text": f"Deleted {row['name']}, and its connections with it.", "undo": record_id}
    if done in ("joined", "unjoined"):
        try:
            row = store.get(CONNECTIONS, record_id, include_deleted=True)
        except records.RecordNotFound:
            return None
        name = display.display_name(store.registry[CONNECTIONS], row, store)
        return {"text": f"{'Connected' if done == 'joined' else 'Removed'}: {name}."}
    return None


def _back(done: str, record_id: int, anchor: int | None = None):
    target = url_for("home_setup.page", done=done, id=record_id,
                     **({"welcome": "1"} if request.form.get("welcome") == "1" else {}))
    return redirect(target + (f"#place-{anchor}" if anchor else ""))


def _place_id(text) -> int | None:
    try:
        return int(text) if text not in (None, "") else None
    except ValueError:
        return None


@home_setup.get("/set-up-home")
def page():
    return _page(_store())


@home_setup.post("/set-up-home/places")
def add_place():
    """Add a room or area (inside nothing), or a storage spot inside one."""
    store = _store()
    if not _ready(store):
        abort(404)
    name = request.form.get("name", "").strip()[:NAME_LIMIT]
    inside = _place_id(request.form.get("inside"))
    try:
        new_id = store.create(PLACES, {"name": name, "inside": inside})
    except records.ValidationError as error:
        typed = {"form": request.form.get("form", "room"), "name": name}
        what = "That storage spot" if inside else "That room"
        return _page(store, f"{what} was not added. {_problem_text(store.registry[PLACES], error.problems)}",
                     typed, status=422)
    return _back("added", new_id, inside or new_id)


@home_setup.post("/set-up-home/places/<int:place_id>")
def change_place(place_id):
    """Rename a place, or move it into another place (or out of every place, making it a room)."""
    store = _store()
    if not _ready(store):
        abort(404)
    try:
        store.get(PLACES, place_id)
    except records.RecordNotFound:
        abort(404)
    values = {"name": request.form.get("name", "").strip()[:NAME_LIMIT],
              "inside": _place_id(request.form.get("inside"))}
    try:
        store.update(PLACES, place_id, values)
    except records.ValidationError as error:
        return _page(store, f"Nothing was changed. {_problem_text(store.registry[PLACES], error.problems)}",
                     status=422)
    return _back("changed", place_id, place_id)


@home_setup.post("/set-up-home/places/<int:place_id>/delete")
def delete_place(place_id):
    store = _store()
    if not _ready(store):
        abort(404)
    try:
        store.delete(PLACES, place_id)
    except records.RecordNotFound:
        abort(404)
    except records.ValidationError as error:
        name = store.get(PLACES, place_id)["name"]
        return _page(store, f"{name} was not deleted: it {error.problems['delete']}", status=409)
    return _back("deleted", place_id)


@home_setup.post("/set-up-home/connections")
def add_connection():
    """Say that two places connect, or that a place has a door straight outside."""
    store = _store()
    if not _ready(store):
        abort(404)
    place = _place_id(request.form.get("place"))
    other = request.form.get("connects_to", "")
    kind = request.form.get("kind", "door")
    values = {"place": place, "kind": kind}
    if other == OUTSIDE:
        values["kind"] = "outside_door"  # straight outside is always a door to outside
    else:
        values["connects_to"] = _place_id(other) if other else None
    try:
        new_id = store.create(CONNECTIONS, values)
    except records.ValidationError as error:
        problems = dict(error.problems)
        if set(problems) == {"connects_to"} and not other:
            problems = {"connects_to": "needs choosing: another place, or Outside."}
        return _page(store, f"Nothing was connected. {_problem_text(store.registry[CONNECTIONS], problems)}",
                     status=422)
    return _back("joined", new_id, place)


@home_setup.post("/set-up-home/connections/<int:connection_id>/delete")
def remove_connection(connection_id):
    store = _store()
    if not _ready(store):
        abort(404)
    try:
        row = store.get(CONNECTIONS, connection_id)
        store.delete(CONNECTIONS, connection_id)
    except records.RecordNotFound:
        abort(404)
    return _back("unjoined", connection_id, _place_id(request.form.get("from")) or row["place"])
