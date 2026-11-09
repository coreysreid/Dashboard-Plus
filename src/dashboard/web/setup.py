"""The first-run wizard and the settings page: who lives here, the home, modules and backups."""
from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from dashboard.core import records, settings
from dashboard.core.backups import default_extra_dir

setup_pages = Blueprint("setup", __name__)
NAME_SLOTS = 8
HOME_TYPES = [("house", "House"), ("apartment", "Apartment or flat"), ("townhouse", "Townhouse or unit"),
              ("other", "Something else")]
HAZARDS = [("bushfire", "Bushfire or wildfire"), ("flood", "Flood"), ("storm", "Cyclone or severe storm"),
           ("earthquake", "Earthquake"), ("heat", "Extreme heat"), ("snow", "Snow or extreme cold"),
           ("power", "Long power cuts")]
COUNTRIES = ["Australia", "Canada", "Ireland", "New Zealand", "South Africa", "United Kingdom", "United States"]
PEOPLE_TABLE = "people__people"


def _conn():
    return current_app.config["CONNECT"]()


def _people_table_ready() -> bool:
    """True when the People module is switched on and has the columns the wizard fills in."""
    info = current_app.config["REGISTRY_FOR_REQUEST"]().get(PEOPLE_TABLE)
    return bool(info and "name" in info.table.columns and "lives_here" in info.table.columns)


def _whole(text: str, low: int, high: int, label: str, errors: dict, field: str, allow_blank=True):
    text = (text or "").strip()
    if not text:
        if not allow_blank:
            errors[field] = f"{label} is needed."
        return None
    try:
        value = int(text)
    except ValueError:
        errors[field] = f"{label} must be a whole number."
        return None
    if not low <= value <= high:
        errors[field] = f"{label} must be between {low} and {high}."
        return None
    return value


def _current() -> dict:
    conn = _conn()
    get = lambda key, default=None: settings.get(conn, key, default)  # noqa: E731
    return {"people": get("household.people"), "pets": get("household.pets", 0),
            "country": get("household.country", ""), "region": get("household.region", ""),
            "home_type": get("household.home_type", ""), "storeys": get("household.storeys"),
            "mobility_needs": get("household.mobility_needs", False),
            "hazards": get("household.hazards", []), "second_copy": get("backups.second_copy", True)}


def _render(mode: str, values: dict, errors: dict, status: int = 200, saved: bool = False):
    conn = _conn()
    on = settings.enabled_modules(conn)
    modules = [{"name": m.name, "title": m.title, "description": m.description, "on": m.name in on}
               for m in current_app.config["LOADED"]]
    people_count = 0
    if _people_table_ready():
        people_count = conn.execute(
            f"SELECT COUNT(*) FROM {PEOPLE_TABLE} WHERE deleted_at IS NULL AND lives_here = 1").fetchone()[0]
    return render_template("setup.html", mode=mode, values=values, errors=errors, saved=saved,
                           modules=modules, people_table=_people_table_ready(), people_count=people_count,
                           name_slots=NAME_SLOTS, home_types=HOME_TYPES, hazards=HAZARDS, countries=COUNTRIES,
                           data_backups=current_app.config["DATA_DIR"] / "backups",
                           extra_backups=default_extra_dir()), status


def _save(form, mode: str):
    """Check the form and save it. Returns a dict of problems (empty when saved)."""
    conn = _conn()
    errors: dict[str, str] = {}
    names = [form.get(f"name_{i}", "").strip() for i in range(1, NAME_SLOTS + 1)]
    names = [n for n in names if n]
    use_people_table = mode == "setup" and _people_table_ready() and not _existing_people(conn)
    pets = _whole(form.get("pets"), 0, 50, "Number of pets", errors, "pets")
    storeys = _whole(form.get("storeys"), 1, 20, "Number of storeys", errors, "storeys")
    people = None
    if not use_people_table or not names:
        people = _whole(form.get("people"), 1, 30, "Number of people", errors, "people",
                        allow_blank=mode == "settings" or bool(names) or
                        (_people_table_ready() and _existing_people(conn) > 0))
    home_type = form.get("home_type", "")
    if home_type and home_type not in dict(HOME_TYPES):
        errors["home_type"] = "Choose one of the listed kinds of home."
    hazards = [h for h in form.getlist("hazards") if h in dict(HAZARDS)]
    chosen_modules = set(form.getlist("modules"))
    if errors:
        return errors

    if use_people_table and names:
        store = records.Records(conn, current_app.config["REGISTRY_FOR_REQUEST"]())
        for name in names:
            store.create(PEOPLE_TABLE, {"name": name, "lives_here": True})
        people = len(names)
    values = {"household.pets": pets or 0, "household.country": form.get("country", "").strip(),
              "household.region": form.get("region", "").strip(), "household.home_type": home_type,
              "household.storeys": storeys, "household.mobility_needs": bool(form.get("mobility_needs")),
              "household.hazards": hazards, "backups.second_copy": bool(form.get("second_copy"))}
    if people is not None:
        values["household.people"] = people
    if form.get("timezone"):
        values["household.timezone"] = form.get("timezone")[:64]
    for key, value in values.items():
        settings.put(conn, key, value)
    for module in current_app.config["LOADED"]:
        settings.set_module_enabled(conn, module.name, module.name in chosen_modules)
    if mode == "setup":
        settings.put(conn, "setup.done", True)
    return {}


def _existing_people(conn) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {PEOPLE_TABLE} WHERE deleted_at IS NULL").fetchone()[0]


def _form_values(form) -> dict:
    return {"people": form.get("people"), "pets": form.get("pets"), "country": form.get("country", ""),
            "region": form.get("region", ""), "home_type": form.get("home_type", ""),
            "storeys": form.get("storeys"), "mobility_needs": bool(form.get("mobility_needs")),
            "hazards": form.getlist("hazards"), "second_copy": bool(form.get("second_copy")),
            "names": [form.get(f"name_{i}", "") for i in range(1, NAME_SLOTS + 1)]}


@setup_pages.get("/setup")
def setup_page():
    return _render("setup", _current(), {})


@setup_pages.post("/setup")
def setup_save():
    errors = _save(request.form, "setup")
    if errors:
        return _render("setup", _form_values(request.form), errors, status=422)
    return redirect(url_for("home"))


@setup_pages.get("/settings")
def settings_page():
    return _render("settings", _current(), {}, saved=request.args.get("saved") == "1")


@setup_pages.post("/settings")
def settings_save():
    errors = _save(request.form, "settings")
    if errors:
        return _render("settings", _form_values(request.form), errors, status=422)
    return redirect(url_for("setup.settings_page", saved="1"))
