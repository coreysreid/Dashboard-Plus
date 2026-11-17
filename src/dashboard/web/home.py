"""Group the home page by area: each module's main lists shown large, its other lists as one line of links."""
from __future__ import annotations

from dashboard.core.modules import HOME_PLACES
from dashboard.web.display import empty_hint, table_title

# The areas a household meets first, in the order of decision 0056. Any other module follows, A to Z by title.
HOUSEHOLD_FIRST = ("people", "stock", "home_layout", "medical", "pets")


def home_places(module) -> dict[str, str]:
    """Where each of a module's tables sits on the home page: "main" (large) or "more" (the line of links).

    A table says so with `home` in labels.toml. Tables that say nothing are "more", except that when
    no table asks to be "main" the first table that says nothing is.
    """
    labels = (module.labels or {}).get("tables", {})
    said = {name: labels.get(name, {}).get("home") for name in module.tables}
    places = {name: value if value in HOME_PLACES else "more" for name, value in said.items()}
    if "main" not in places.values():
        first = next((name for name, value in said.items() if value is None), None)
        if first is not None:
            places[first] = "main"
    return places


def home_groups(registry: dict, count, sheets: list[dict]) -> list[dict]:
    """One group per switched-on module, household areas first, each with its main and other lists and its sheets.

    `count` gives the number of records in a table, by its real name.
    """
    groups: dict[str, dict] = {}
    for name, info in registry.items():
        module = info.module
        group = groups.get(module.name)
        if group is None:
            group = groups[module.name] = {
                "name": module.name, "title": module.title, "main": [], "more": [],
                "places": home_places(module), "sheets": [s for s in sheets if s["module"] == module.name]}
        entry = {"name": name, "title": table_title(info), "module": module.title, "count": count(name),
                 "empty": empty_hint(info)}
        group[group["places"][info.table.name]].append(entry)

    def position(group: dict):
        known = group["name"] in HOUSEHOLD_FIRST
        return (0, HOUSEHOLD_FIRST.index(group["name"]), "") if known else (1, 0, group["title"].lower())

    return sorted(groups.values(), key=position)
