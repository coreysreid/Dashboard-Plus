"""Our way-out sketch: the drawing with its text version, the few facts it asks for, and the printable sheet and text.

Decision 0118. Reads Set up my home's rooms and connections fresh on every page (core/exit_sketch.py), so
nothing stale is printed. The household gives each room a floor, marks sleeping rooms and any window it
checked, confirms where each door to outside leads, and answers three questions kept in Settings. The sheet
needs as many pages as it takes to show every room and connection; it never cuts one off.
"""
from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from dashboard.core import dates, drills, exit_sketch as facts, records, settings
from dashboard.web import exit_drawing

exit_pages = Blueprint("exit_sketch", __name__)
PAPERS = {"a4": "A4", "letter": "Letter"}
DESTINATIONS = [("", "Needs checking"), ("outside", "Outside"), ("shared", "Shared building area")]


def _registry():
    return current_app.config["REGISTRY_FOR_REQUEST"]()


def _conn():
    return current_app.config["CONNECT"]()


def _today() -> date:
    return current_app.config.get("TODAY", date.today)()


def _number(registry) -> str | None:
    """The checked emergency number for the household's country, from a drill module's list; None elsewhere."""
    country = settings.get(_conn(), "household.country", "") or ""
    for prompt_set in drills.drill_sets(registry).values():
        found = drills.emergency(prompt_set, country)
        if found:
            return found["number"]
    return None


def _href(what: str, record_id: int) -> str:
    return f"/t/{facts.PLACES if what == 'room' else facts.CONNECTIONS}/{record_id}"


def _sketch():
    registry = _registry()
    if not facts.ready_to_read(registry):
        return None
    return facts.read(_conn(), registry, _number(registry))


def _common(sketch) -> dict:
    style = dates.household_style(_conn())
    return {"sketch": sketch, "f": facts, "reviewed_words": dates.show(sketch.reviewed_on, style)
            if sketch.reviewed_on else None, "printed": dates.show(_today().isoformat(), style)}


@exit_pages.get("/exit-sketch")
def page(problem: str | None = None, status: int = 200):
    sketch = _sketch()
    if sketch is None:
        return render_template("exit_sketch.html", ready=False)
    blocks, pages = exit_drawing.drawn(sketch, _href)
    doors = [(room, link) for room in sketch.rooms for link in room.links if link.outside]
    destinations = dict(_conn().execute(
        f"SELECT id, destination FROM {facts.CONNECTIONS} WHERE deleted_at IS NULL AND kind = 'outside_door'"
    ).fetchall())
    return render_template("exit_sketch.html", ready=True, blocks=blocks, pages=pages, doors=doors,
                           destinations=destinations, destination_choices=DESTINATIONS,
                           floor_choices=[(k, w) for k, w in facts.FLOORS if k] + [(facts.LEFT_OFF, "Leave off the sketch")],
                           notice=request.args.get("done"), problem=problem, **_common(sketch)), status


def _back(done: str, anchor: str):
    return redirect(url_for("exit_sketch.page", done=done) + "#" + anchor)


@exit_pages.post("/exit-sketch/rooms")
def save_rooms():
    """Each room's floor (or left off the sketch), whether someone sleeps there, and a window the household checked."""
    registry = _registry()
    if not facts.ready_to_read(registry):
        abort(404)
    store = records.Records(_conn(), registry)
    allowed = {k for k, _ in facts.FLOORS if k} | {facts.LEFT_OFF}
    rows = _conn().execute(f"SELECT id, floor, sleeping, window_exit FROM {facts.PLACES} "
                           f"WHERE deleted_at IS NULL AND inside IS NULL").fetchall()
    for row in rows:
        if f"floor-{row['id']}" not in request.form:
            continue  # a room added since the page was opened keeps what it has
        floor = request.form.get(f"floor-{row['id']}", "")
        values = {"floor": floor if floor in allowed else None,
                  "sleeping": bool(request.form.get(f"sleeping-{row['id']}")),
                  "window_exit": bool(request.form.get(f"window-{row['id']}"))}
        if (values["floor"], values["sleeping"], values["window_exit"]) != \
                (row["floor"], bool(row["sleeping"]), bool(row["window_exit"])):
            store.update(facts.PLACES, row["id"], values)
    return _back("rooms", "rooms")


@exit_pages.post("/exit-sketch/doors")
def save_doors():
    """Where each door to outside leads, as the household confirmed it; blank stays Needs checking."""
    registry = _registry()
    if not facts.ready_to_read(registry):
        abort(404)
    store = records.Records(_conn(), registry)
    allowed = {k for k, _ in DESTINATIONS if k} | {"check"}
    for row in _conn().execute(f"SELECT id, destination FROM {facts.CONNECTIONS} "
                               f"WHERE deleted_at IS NULL AND kind = 'outside_door'").fetchall():
        key = f"destination-{row['id']}"
        if key not in request.form:
            continue
        chosen = request.form.get(key) if request.form.get(key) in allowed else None
        if chosen != row["destination"]:
            store.update(facts.CONNECTIONS, row["id"], {"destination": chosen})
    return _back("doors", "doors")


@exit_pages.post("/exit-sketch/household")
def save_household():
    if not facts.ready_to_read(_registry()):
        abort(404)
    problems = facts.save_household(_conn(), request.form.get("meeting_place", ""), request.form.get("help", ""),
                                    request.form.get("building", ""))
    if problems:
        return page(" ".join(problems.values()) + " Nothing was changed.", 422)
    return _back("household", "household")


@exit_pages.post("/exit-sketch/reviewed")
def reviewed():
    sketch = _sketch()
    if sketch is None:
        abort(404)
    missing = facts.mark_reviewed(_conn(), sketch, _today().isoformat())
    if missing:
        return page("Not marked as reviewed yet. Still needs checking: " + "; ".join(missing) + ".", 422)
    return _back("reviewed", "check")


@exit_pages.get("/exit-sketch/print")
def sheet():
    """The printable sheet: page 1 with warnings, meeting place, legend and Check together, then every block."""
    sketch = _sketch()
    if sketch is None:
        abort(404)
    paper = request.args.get("paper", "a4")
    if paper not in PAPERS:
        paper = "a4"
    blocks, pages = exit_drawing.drawn(sketch, _href)
    return render_template("exit_sheet.html", blocks=blocks, pages=pages, paper=paper, papers=PAPERS,
                           by_page=[[b for b in blocks if b["page"] == n] for n in range(1, pages + 1)],
                           **_common(sketch))


@exit_pages.get("/exit-sketch/text")
def text():
    """Print as text: every room, connection, destination and fact in order, with the same warnings."""
    sketch = _sketch()
    if sketch is None:
        abort(404)
    return render_template("exit_text.html", **_common(sketch))
