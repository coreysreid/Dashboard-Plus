"""Load a made-up example household into an empty data folder, for demos, screenshots and testing."""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import tomllib
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dashboard.core import db, records, settings, startup  # noqa: E402
from dashboard.core.schema import table_name, target_table  # noqa: E402

HOUSEHOLDS = ROOT / "examples" / "households"
RELATIVE_DATE = re.compile(r"^today(?:([+-])(\d+))?$")
PEOPLE_TABLE = "people__people"
PETS_TABLE = "pets__pets"
SETUP_TABLES = (PEOPLE_TABLE, PETS_TABLE)  # the setup page creates these; the file then fills them in


class ExampleError(Exception):
    """A problem with an example file or the folder it is loaded into, in plain words."""


def household_path(name: str) -> Path:
    """The file for an example household, given its short name (like "smith") or a path."""
    path = Path(name)
    if path.suffix == ".toml" and path.exists():
        return path
    path = HOUSEHOLDS / f"{name}.toml"
    if not path.exists():
        known = ", ".join(sorted(p.stem for p in HOUSEHOLDS.glob("*.toml")))
        raise ExampleError(f"There is no example household called '{name}'. Choose one of: {known}.")
    return path


def read(name: str) -> dict:
    """Read an example household file."""
    with open(household_path(name), "rb") as handle:
        data = tomllib.load(handle)
    for key in ("title", "summary", "setup"):
        if key not in data:
            raise ExampleError(f"The example '{name}' is missing '{key}'.")
    return data


def rows_by_table(data: dict) -> list[tuple[str, list[dict]]]:
    """The records in the file as (real table name, rows), in the order they are written."""
    tables = []
    for module, section in data.items():
        if module in ("title", "summary", "setup") or not isinstance(section, dict):
            continue
        for table, rows in section.items():
            tables.append((table_name(module, table), rows))
    return tables


def _date(value, today: date):
    if isinstance(value, str):
        match = RELATIVE_DATE.match(value)
        if match:
            days = int(match.group(2) or 0) * (-1 if match.group(1) == "-" else 1)
            return (today + timedelta(days=days)).isoformat()
    return value


def _name_column(info) -> str | None:
    """The column an example names a row by, or None for a history table with no short text
    (such as kit checks, which are only links, dates and a note)."""
    texts = [c for c in info.table.columns.values() if c.type == "text"]
    required = [c for c in texts if c.required]
    return (required or texts)[0].name if texts else None


def _find(conn: sqlite3.Connection, info, name: str) -> int | None:
    if _name_column(info) is None:
        raise ExampleError(f"{info.name} has no name column, so other rows cannot link to it by name.")
    row = conn.execute(f"SELECT id FROM {info.name} WHERE deleted_at IS NULL AND {_name_column(info)} = ?",
                       (name,)).fetchone()
    return row["id"] if row else None


def apply_setup(conn: sqlite3.Connection, registry: dict, module_names: list[str], setup: dict) -> None:
    """Save the setup answers the way the first-run wizard does, without a browser."""
    store = records.Records(conn, registry)
    if PEOPLE_TABLE in registry:
        for name in setup.get("people", []):
            if _find(conn, registry[PEOPLE_TABLE], name) is None:
                store.create(PEOPLE_TABLE, {"name": name, "lives_here": True})
    else:
        settings.put(conn, "household.people", len(setup.get("people", [])))
    pets = setup.get("pets", [])
    chosen = set(setup.get("modules", module_names))
    if PETS_TABLE in registry and "pets" in chosen:
        for pet in pets:
            if _find(conn, registry[PETS_TABLE], pet["name"]) is None:
                store.create(PETS_TABLE, {"name": pet["name"], "species": pet["kind"]})
    settings.put(conn, "household.pets", len(pets))
    for key in ("country", "region", "home_type", "storeys", "mobility_needs", "hazards"):
        if key in setup:
            settings.put(conn, f"household.{key}", setup[key])
    settings.put(conn, "backups.second_copy", False)
    for module in module_names:
        settings.set_module_enabled(conn, module, module in chosen)
    settings.put(conn, "setup.done", True)


def _starting_amounts(registry: dict, tables: list[tuple[str, list[dict]]]) -> dict[tuple[str, str], float]:
    """How much each counted record changes through the file's in-and-out records (DESIGN 5.3).

    Amounts in the file are what is on hand today, so each record is created with
    today's amount minus these changes, and the in-and-out records then bring it
    back to today's amount, leaving a true history."""
    changes: dict[tuple[str, str], float] = {}
    for name, rows in tables:
        rule = registry[name].table.adjusts if name in registry else None
        if not rule:
            continue
        target, link = _counted(registry, name, rule)
        for row in rows:
            sign = 1 if row.get(rule["direction"]) in rule["adds"] else -1
            key = (target, row[link])
            changes[key] = changes.get(key, 0) + sign * float(row[rule["amount"]])
    return changes


def _counted(registry: dict, name: str, rule: dict) -> tuple[str, str]:
    """The table whose amount stock in and out changes, and the column naming it in the file.

    With batches, the file names the item; its amount is the sum of its batches (DESIGN 5.7)."""
    module = registry[name].module.name
    if rule.get("belongs_to"):
        owner = registry[name].table.columns[rule["belongs_to"]]
        return table_name(module, owner.to), rule["belongs_to"]
    return table_name(module, rule["target"]), rule["link"]


def load_records(conn: sqlite3.Connection, registry: dict, data: dict, today: date | None = None) -> int:
    """Create every record in the example as if the household had typed it in; return how many."""
    today = today or date.today()
    store = records.Records(conn, registry)
    tables = rows_by_table(data)
    changes = _starting_amounts(registry, tables)
    count = 0
    for name, rows in tables:
        if name not in registry:
            raise ExampleError(f"The example uses a table '{name}' that is not switched on.")
        info = registry[name]
        quantity = None
        for other, _ in tables:
            rule = registry[other].table.adjusts if other in registry else None
            if rule and _counted(registry, other, rule)[0] == name:
                batches = registry[table_name(registry[other].module.name, rule["target"])]
                quantity = batches.table.total["into"] if rule.get("belongs_to") else rule["quantity"]
        for row in rows:
            values = {}
            for column, value in row.items():
                col = info.table.columns.get(column)
                if col is None:
                    raise ExampleError(f"{name}: there is no column '{column}'.")
                if col.type == "link":
                    target = registry[target_table(info.module.name, col)]
                    found = _find(conn, target, value)
                    if found is None:
                        raise ExampleError(f"{name}: '{value}' must be added before it is linked to.")
                    value = found
                elif col.type == "links":
                    target = registry[target_table(info.module.name, col)]
                    ids = [_find(conn, target, v) for v in value]
                    if None in ids:
                        raise ExampleError(f"{name}: '{value[ids.index(None)]}' must be added before it is linked to.")
                    value = ids
                elif col.type == "date":
                    value = _date(value, today)
                elif col.type == "datetime" and isinstance(value, str) and "T" in value:
                    day, _, clock = value.partition("T")  # "today-1T07:15": a time on a day relative to today
                    value = f"{_date(day, today)}T{clock}"
                values[column] = value
            name_column = _name_column(info)
            label = row.get(name_column) if name_column else None
            if quantity and (name, label) in changes:
                start = float(values.get(quantity) or 0) - changes[(name, label)]
                if start < 0:
                    raise ExampleError(f"{name}: '{label}' would start below zero; raise its amount.")
                values[quantity] = round(start, 3)
            rule = info.table.adjusts
            if rule and rule.get("belongs_to") and values.get(rule["link"]) is None \
                    and values.get(rule["belongs_to"]) is not None:
                # Stock in and out in the file belongs to the item's first batch unless it says otherwise.
                batches = registry[table_name(info.module.name, rule["target"])]
                first = conn.execute(f"SELECT id FROM {batches.name} WHERE deleted_at IS NULL AND "
                                     f"{rule['belongs_to']} = ? ORDER BY id LIMIT 1",
                                     (values[rule["belongs_to"]],)).fetchone()
                if first is not None:
                    values[rule["link"]] = first["id"]
            existing = _find(conn, info, label) if name in SETUP_TABLES and label else None
            if existing is not None:
                store.update(name, existing, values)
            else:
                store.create(name, values)
            count += 1
    return count


def load(name: str, data_dir: Path, modules_dir: Path = ROOT / "modules", today: date | None = None) -> int:
    """Set up an empty data folder with an example household; return how many records were added."""
    data_dir = Path(data_dir)
    if (data_dir / "dashboard.db").exists():
        raise ExampleError(f"{data_dir} already has a database. Examples only go into an empty folder, "
                           f"so real records are never mixed with made-up ones.")
    example = read(name)
    report = startup.prepare(data_dir, modules_dir)
    conn = db.connect(data_dir / "dashboard.db")
    try:
        registry = records.build_registry(report.loaded)
        apply_setup(conn, registry, [m.name for m in report.loaded], example["setup"])
        return load_records(conn, registry, example, today)
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("household", help="smith, garcia or taylor (see examples/households)")
    parser.add_argument("--data", required=True, help="an empty folder to create the example's data in")
    args = parser.parse_args(argv)
    try:
        added = load(args.household, Path(args.data))
    except ExampleError as error:
        print(error)
        return 1
    print(f"Loaded {added} records into {args.data}. Open it with: python -m dashboard --data {args.data}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
