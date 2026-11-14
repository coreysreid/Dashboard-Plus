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


def _name_column(info) -> str:
    texts = [c for c in info.table.columns.values() if c.type == "text"]
    required = [c for c in texts if c.required]
    return (required or texts)[0].name


def _find(conn: sqlite3.Connection, info, name: str) -> int | None:
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
    for key in ("pets", "country", "region", "home_type", "storeys", "mobility_needs", "hazards"):
        if key in setup:
            settings.put(conn, f"household.{key}", setup[key])
    settings.put(conn, "backups.second_copy", False)
    chosen = set(setup.get("modules", module_names))
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
        target = table_name(registry[name].module.name, rule["target"])
        for row in rows:
            sign = 1 if row.get(rule["direction"]) in rule["adds"] else -1
            key = (target, row[rule["link"]])
            changes[key] = changes.get(key, 0) + sign * float(row[rule["amount"]])
    return changes


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
            if rule and table_name(registry[other].module.name, rule["target"]) == name:
                quantity = rule["quantity"]
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
                elif col.type == "date":
                    value = _date(value, today)
                values[column] = value
            label = row.get(_name_column(info))
            if quantity and (name, label) in changes:
                start = float(values.get(quantity) or 0) - changes[(name, label)]
                if start < 0:
                    raise ExampleError(f"{name}: '{label}' would start below zero; raise its amount.")
                values[quantity] = round(start, 3)
            existing = _find(conn, info, label) if name == PEOPLE_TABLE else None
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
