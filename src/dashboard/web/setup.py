"""The first-run wizard and the settings page: who lives here, the home, modules and backups."""
from __future__ import annotations

from flask import Blueprint, current_app, g, redirect, render_template, request, url_for

from dashboard.core import checklist, records, settings
from datetime import datetime

from dashboard.core import backups
from dashboard.core.backups import default_extra_dir

setup_pages = Blueprint("setup", __name__)
NAME_SLOTS = 8
HOME_TYPES = [("house", "House"), ("apartment", "Apartment or flat"), ("townhouse", "Townhouse or unit"),
              ("other", "Something else")]
HAZARDS = [("bushfire", "Bushfire or wildfire"), ("flood", "Flood"), ("storm", "Cyclone or severe storm"),
           ("earthquake", "Earthquake"), ("heat", "Extreme heat"), ("snow", "Snow or extreme cold"),
           ("power", "Long power cuts")]
REGIONS = {
    "Australia": ["Australian Capital Territory", "New South Wales", "Northern Territory", "Queensland",
                  "South Australia", "Tasmania", "Victoria", "Western Australia"],
    "Canada": ["Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
               "Northwest Territories", "Nova Scotia", "Nunavut", "Ontario", "Prince Edward Island", "Quebec",
               "Saskatchewan", "Yukon"],
    "Ireland": ["Connacht", "Leinster", "Munster", "Ulster"],
    "New Zealand": ["Auckland", "Bay of Plenty", "Canterbury", "Gisborne", "Hawke's Bay", "Manawatū-Whanganui",
                    "Marlborough", "Nelson", "Northland", "Otago", "Southland", "Taranaki", "Tasman", "Waikato",
                    "Wellington", "West Coast"],
    "South Africa": ["Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo", "Mpumalanga",
                     "North West", "Northern Cape", "Western Cape"],
    "United Kingdom": ["England", "Northern Ireland", "Scotland", "Wales"],
    "United States": ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
                      "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois",
                      "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
                      "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
                      "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
                      "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
                      "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
                      "West Virginia", "Wisconsin", "Wyoming"],
}
COUNTRIES = list(REGIONS)
# A first guess at country and state from the computer's time zone (no internet needed). Only zones that
# pin down one state name it; the rest suggest the country alone. The household can always change it.
TIMEZONE_GUESS = {
    "Australia/Sydney": ["Australia", "New South Wales"], "Australia/Broken_Hill": ["Australia", "New South Wales"],
    "Australia/Melbourne": ["Australia", "Victoria"], "Australia/Brisbane": ["Australia", "Queensland"],
    "Australia/Lindeman": ["Australia", "Queensland"], "Australia/Adelaide": ["Australia", "South Australia"],
    "Australia/Perth": ["Australia", "Western Australia"], "Australia/Hobart": ["Australia", "Tasmania"],
    "Australia/Darwin": ["Australia", "Northern Territory"],
    "Australia/Canberra": ["Australia", "Australian Capital Territory"],
    "Pacific/Auckland": ["New Zealand", ""], "Pacific/Chatham": ["New Zealand", ""],
    "Europe/London": ["United Kingdom", ""], "Europe/Belfast": ["United Kingdom", "Northern Ireland"],
    "Europe/Dublin": ["Ireland", ""], "Africa/Johannesburg": ["South Africa", ""],
    "America/Toronto": ["Canada", ""], "America/Vancouver": ["Canada", "British Columbia"],
    "America/Edmonton": ["Canada", "Alberta"], "America/Winnipeg": ["Canada", "Manitoba"],
    "America/Regina": ["Canada", "Saskatchewan"], "America/Halifax": ["Canada", ""],
    "America/St_Johns": ["Canada", "Newfoundland and Labrador"], "America/Moncton": ["Canada", "New Brunswick"],
    "America/Whitehorse": ["Canada", "Yukon"], "America/Yellowknife": ["Canada", "Northwest Territories"],
    "America/Iqaluit": ["Canada", "Nunavut"],
    "America/New_York": ["United States", ""], "America/Chicago": ["United States", ""],
    "America/Denver": ["United States", ""], "America/Los_Angeles": ["United States", ""],
    "America/Phoenix": ["United States", "Arizona"], "America/Anchorage": ["United States", "Alaska"],
    "America/Juneau": ["United States", "Alaska"], "Pacific/Honolulu": ["United States", "Hawaii"],
    "America/Boise": ["United States", "Idaho"], "America/Detroit": ["United States", "Michigan"],
    "America/Indiana/Indianapolis": ["United States", "Indiana"],
    "America/Kentucky/Louisville": ["United States", "Kentucky"],
}
OTHER_COUNTRY = "other"
PEOPLE_TABLE = "people__people"
PETS_TABLE = "pets__pets"
PET_SLOTS = 6


def _conn():
    return current_app.config["CONNECT"]()


def _pets_info():
    """The Pets table when that module is switched on and has the columns the wizard fills in."""
    info = current_app.config["REGISTRY_FOR_REQUEST"]().get(PETS_TABLE)
    return info if info and {"name", "species"} <= set(info.table.columns) else None


def _pet_count(conn) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {PETS_TABLE} WHERE deleted_at IS NULL").fetchone()[0]


def _home_setup_on() -> bool:
    """True when Set up my home can be used: Household stock, with its places and connections, is switched on."""
    from dashboard.web.home_setup import CONNECTIONS, PLACES
    registry = current_app.config["REGISTRY_FOR_REQUEST"]()
    return PLACES in registry and CONNECTIONS in registry


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
            "hazards": get("household.hazards", []), "second_copy": get("backups.second_copy", True),
            "week_starts": checklist.week_start(_conn()),
            "distance_unit": settings.household_choice(conn, "distance_unit")}


def _when(text: str | None) -> str | None:
    try:
        return datetime.fromisoformat(text).strftime("%d %b %Y %H:%M") if text else None
    except ValueError:
        return None


def backup_report(data_dir) -> dict:
    """How the last backup went, in words for the Settings and home pages."""
    found = backups.status(data_dir) if data_dir is not None else {}
    second = found.get("second", {})
    return {"main": _when(found.get("main", {}).get("at")), "second_state": second.get("state"),
            "second_at": _when(second.get("at")), "second_last_ok": _when(second.get("last_ok")),
            "second_reason": second.get("reason")}


def _render(mode: str, values: dict, errors: dict, status: int = 200, saved: bool = False):
    conn = _conn()
    on = settings.enabled_modules(conn)
    modules = [{"name": m.name, "title": m.title, "description": m.description, "on": m.name in on}
               for m in current_app.config["LOADED"]]
    people_count = 0
    if _people_table_ready():
        people_count = conn.execute(
            f"SELECT COUNT(*) FROM {PEOPLE_TABLE} WHERE deleted_at IS NULL AND lives_here = 1").fetchone()[0]
    pets_info = _pets_info()
    pet_kinds = [(c.key, c.label) for c in pets_info.table.columns["species"].choices] if pets_info else []
    return render_template("setup.html", mode=mode, values=values, errors=errors, saved=saved,
                           pets_table=bool(pets_info), pet_count=_pet_count(conn) if pets_info else 0,
                           pet_slots=PET_SLOTS, pet_kinds=pet_kinds, home_setup=_home_setup_on(),
                           modules=modules, people_table=_people_table_ready(), people_count=people_count,
                           name_slots=NAME_SLOTS, home_types=HOME_TYPES, hazards=HAZARDS, countries=COUNTRIES,
                           regions=REGIONS, timezone_guess=TIMEZONE_GUESS,
                           distance_units=list(settings.HOUSEHOLD_CHOICES["distance_unit"].items()),
                           data_backups=current_app.config["DATA_DIR"] / "backups",
                           extra_backups=default_extra_dir(),
                           backup=backup_report(current_app.config["DATA_DIR"])), status


def _save(form, mode: str):
    """Check the form and save it. Returns a dict of problems (empty when saved)."""
    conn = _conn()
    errors: dict[str, str] = {}
    names = [form.get(f"name_{i}", "").strip() for i in range(1, NAME_SLOTS + 1)]
    names = [n for n in names if n]
    use_people_table = mode == "setup" and _people_table_ready() and not _existing_people(conn)
    pets_info = _pets_info()
    new_pets = []
    if pets_info is not None:
        kinds = {c.key for c in pets_info.table.columns["species"].choices}
        if mode == "setup" and not _pet_count(conn):
            for i in range(1, PET_SLOTS + 1):
                name, kind = form.get(f"pet_{i}", "").strip(), form.get(f"pet_kind_{i}", "")
                if name:
                    new_pets.append({"name": name[:80], "species": kind if kind in kinds else "other"})
        pets = None
    else:
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
    country, region = _place(form, errors)
    week_starts = form.get("week_starts")
    if week_starts is not None and week_starts not in checklist.WEEK_STARTS:
        errors["week_starts"] = "Choose Monday, Sunday or Saturday."
    distance_unit = form.get("distance_unit")
    if distance_unit is not None and distance_unit not in settings.HOUSEHOLD_CHOICES["distance_unit"]:
        errors["distance_unit"] = "Choose kilometres or miles."
    chosen_modules = set(form.getlist("modules"))
    for module in current_app.config["LOADED"]:
        needed = [r for r in module.requires if r not in chosen_modules]
        if module.name in chosen_modules and needed:
            titles = {m.name: m.title for m in current_app.config["LOADED"]}
            errors["modules"] = (f"{module.title} needs {', '.join(titles.get(n, n) for n in needed)}. Keep "
                                 f"{'it' if len(needed) == 1 else 'them'} switched on, or switch {module.title} off too.")
    if errors:
        return errors

    if use_people_table and names:
        store = records.Records(conn, current_app.config["REGISTRY_FOR_REQUEST"]())
        for name in names:
            store.create(PEOPLE_TABLE, {"name": name, "lives_here": True})
        people = len(names)
    if new_pets:
        store = records.Records(conn, current_app.config["REGISTRY_FOR_REQUEST"]())
        for pet in new_pets:
            store.create(PETS_TABLE, pet)
    if pets is None:  # the Pets module counts the pets itself
        pets = _pet_count(conn) if pets_info is not None else 0
    values = {"household.pets": pets or 0, "household.country": country,
              "household.region": region, "household.home_type": home_type,
              "household.storeys": storeys, "household.mobility_needs": bool(form.get("mobility_needs")),
              "household.hazards": hazards, "backups.second_copy": bool(form.get("second_copy"))}
    if people is not None:
        values["household.people"] = people
    if week_starts:  # only Settings asks; the first-run questions leave the household's usual week
        values[checklist.WEEK_START_KEY] = week_starts
    if distance_unit:  # only Settings asks; until then it follows the country (decision 0111)
        values["household.distance_unit"] = distance_unit
    if form.get("timezone"):
        values["household.timezone"] = form.get("timezone")[:64]
    for key, value in values.items():
        settings.put(conn, key, value)
    for module in current_app.config["LOADED"]:
        settings.set_module_enabled(conn, module.name, module.name in chosen_modules)
    if mode == "setup":
        settings.put(conn, "setup.done", True)
    return {}


def _place(form, errors: dict) -> tuple[str, str]:
    """The country and state from the form: a listed country with one of its states, or one typed in."""
    country = form.get("country", "").strip()
    if country == OTHER_COUNTRY:
        return form.get("country_other", "").strip()[:60], form.get("region_other", "").strip()[:60]
    if country and country not in REGIONS:
        errors["country"] = "Choose a country from the list, or \"Somewhere else\" to type it."
        return "", ""
    region = form.get("region", "").strip()
    if region and region not in REGIONS.get(country, []):
        errors["region"] = "Choose a state or region from the list for this country."
        return country, ""
    return country, region


def _existing_people(conn) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {PEOPLE_TABLE} WHERE deleted_at IS NULL").fetchone()[0]


def _form_values(form) -> dict:
    other = form.get("country") == OTHER_COUNTRY
    return {"people": form.get("people"), "pets": form.get("pets"),
            "country": form.get("country_other", "") if other else form.get("country", ""),
            "region": form.get("region_other" if other else "region", ""), "country_is_other": other, "home_type": form.get("home_type", ""),
            "storeys": form.get("storeys"), "mobility_needs": bool(form.get("mobility_needs")),
            "hazards": form.getlist("hazards"), "second_copy": bool(form.get("second_copy")),
            "week_starts": form.get("week_starts", ""), "distance_unit": form.get("distance_unit", ""),
            "names": [form.get(f"name_{i}", "") for i in range(1, NAME_SLOTS + 1)],
            "pet_names": [form.get(f"pet_{i}", "") for i in range(1, PET_SLOTS + 1)],
            "pet_kinds": [form.get(f"pet_kind_{i}", "") for i in range(1, PET_SLOTS + 1)]}


@setup_pages.get("/setup")
def setup_page():
    return _render("setup", _current(), {})


@setup_pages.post("/setup")
def setup_save():
    errors = _save(request.form, "setup")
    if errors:
        return _render("setup", _form_values(request.form), errors, status=422)
    g.pop("registry", None)  # the modules just chosen decide whether Set up my home is offered next
    if _home_setup_on():
        return redirect(url_for("home_setup.page", welcome="1"))  # the next step, offered and skippable
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
