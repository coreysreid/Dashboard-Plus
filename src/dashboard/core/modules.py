"""Find module folders, check their files, and explain any mistakes in plain words."""
from __future__ import annotations

import difflib
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dashboard.core.migrations import Migration, load_track, MigrationError
from dashboard.errors import PlainError

CORE_API = "1"
NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
CHOICE_KEY = re.compile(r"^[a-z0-9][a-z0-9_]*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
KINDS = ("declarative", "code")
TYPES = ("text", "longtext", "integer", "decimal", "boolean", "date", "datetime", "choice",
         "link", "links", "money", "measure", "file")
NUMERIC_TYPES = ("integer", "decimal", "money", "measure")
ON_DELETE = ("restrict", "cascade", "clear")
# Columns every table gets automatically (DESIGN.md section 3); modules may not declare them.
SYSTEM_COLUMNS = ("id", "created_at", "updated_at", "review_status", "source", "batch_id",
                  "edited_by_person", "deleted_at")

MODULE_KEYS = ("name", "title", "version", "description", "core_api", "kind", "requires", "outbound_hosts")
MODULE_REQUIRED = ("name", "title", "version", "description", "core_api", "kind")
TABLE_KEYS = ("title", "description", "columns", "watch")
WATCH_KEYS = ("running_low", "expiring", "supply")
COLUMN_KEYS = ("type", "required", "default", "min", "max", "unit", "choices", "help", "sensitive", "to", "on_delete")
LABEL_TABLE_KEYS = ("title", "columns", "form", "list")
LABEL_COLUMN_KEYS = ("label", "help")


class ModuleError(PlainError):
    """A module's files have mistakes. `problems` lists each one in plain words."""

    def __init__(self, module: str, problems: list[str]):
        self.module = module
        self.problems = problems
        super().__init__(f"The '{module}' module has {len(problems)} problem(s): " + " ".join(problems))


@dataclass
class Choice:
    key: str
    label: str


@dataclass
class Column:
    name: str
    type: str
    required: bool = False
    default: object = None
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    choices: list[Choice] = field(default_factory=list)
    help: str | None = None
    sensitive: bool = False
    to: str | None = None          # for link/links: "table" or "module.table"
    on_delete: str = "restrict"


@dataclass
class Table:
    name: str
    title: str
    description: str | None
    columns: dict[str, Column]
    watch: dict = field(default_factory=dict)  # checked `watch` section (DESIGN.md 5.1)


@dataclass
class Module:
    name: str
    title: str
    version: str
    description: str
    kind: str
    requires: list[str]
    outbound_hosts: list[str]
    folder: Path
    tables: dict[str, Table]
    labels: dict
    migrations: list[Migration]


def _suggest(word: str, options) -> str:
    close = difflib.get_close_matches(str(word), list(options), n=1)
    hint = f" Did you mean '{close[0]}'?" if close else ""
    return f"{hint} Allowed: {', '.join(options)}."


def _read_toml(path: Path, problems: list[str], required: bool) -> dict:
    if not path.exists():
        if required:
            problems.append(f"The file {path.name} is missing.")
        return {}
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        problems.append(f"{path.name} could not be read: {error}.")
        return {}


def _unknown_keys(where: str, data: dict, allowed) -> list[str]:
    return [f"{where}: unknown setting '{key}'.{_suggest(key, allowed)}" for key in data if key not in allowed]


def _check_module_toml(folder: Path, data: dict, problems: list[str]) -> None:
    where = "In module.toml"
    problems.extend(_unknown_keys(where, data, MODULE_KEYS))
    for key in MODULE_REQUIRED:
        if key not in data:
            problems.append(f"{where}: '{key}' is missing.")
    name = data.get("name")
    if name is not None and name != folder.name:
        problems.append(f"{where}: name is '{name}' but the folder is called '{folder.name}'; they must match.")
    if "version" in data and not VERSION.match(str(data["version"])):
        problems.append(f"{where}: version '{data['version']}' should look like 1.0.0.")
    if "core_api" in data and str(data["core_api"]) != CORE_API:
        problems.append(f"{where}: this module needs core_api '{data['core_api']}', but this program provides "
                        f"'{CORE_API}'. It needs a different version of Dashboard Plus.")
    kind = data.get("kind")
    if kind is not None and kind not in KINDS:
        problems.append(f"{where}: kind '{kind}' is not known.{_suggest(kind, KINDS)}")
    for key in ("requires", "outbound_hosts"):
        if key in data and (not isinstance(data[key], list) or not all(isinstance(x, str) for x in data[key])):
            problems.append(f"{where}: '{key}' must be a list of names, like [\"people\"].")
    if kind == "declarative" and data.get("outbound_hosts"):
        problems.append(f"{where}: a declarative module cannot contact anything, so outbound_hosts must be empty.")
    if kind == "code" and not (folder / "sources.py").exists():
        problems.append(f"{where}: kind is 'code' but there is no sources.py.")


def _parse_choices(where: str, raw, problems: list[str]) -> list[Choice]:
    if not isinstance(raw, list) or not raw:
        problems.append(f"{where}: 'choices' must be a non-empty list.")
        return []
    choices: list[Choice] = []
    for item in raw:
        if isinstance(item, str):
            key, label = item, item.replace("_", " ").capitalize()
        elif isinstance(item, dict) and "key" in item:
            key, label = item["key"], item.get("label", str(item["key"]).replace("_", " ").capitalize())
        else:
            problems.append(f"{where}: each choice must be a word like \"dry_food\" or {{ key = \"dry_food\", label = \"Dry food\" }}.")
            continue
        if not isinstance(key, str) or not CHOICE_KEY.match(key):
            problems.append(f"{where}: choice '{key}' must be lower-case letters, digits and underscores; "
                            "put the friendly wording in a label.")
            continue
        choices.append(Choice(key, str(label)))
    keys = [c.key for c in choices]
    for key in sorted({k for k in keys if keys.count(k) > 1}):
        problems.append(f"{where}: the choice '{key}' appears twice.")
    return choices


def _parse_column(file: str, table: str, name: str, raw, problems: list[str]) -> Column | None:
    where = f"In {file}, table '{table}', column '{name}'"
    if not NAME.match(name):
        problems.append(f"{where}: the name must start with a letter and use only lower-case letters, digits and underscores.")
    if name in SYSTEM_COLUMNS:
        problems.append(f"{where}: '{name}' is added automatically to every table; choose another name.")
        return None
    if not isinstance(raw, dict):
        problems.append(f"{where}: describe the column like {{ type = \"text\" }}.")
        return None
    problems.extend(_unknown_keys(where, raw, COLUMN_KEYS))
    kind = raw.get("type")
    if kind is None:
        problems.append(f"{where}: 'type' is missing.{_suggest('', TYPES)}")
        return None
    if kind not in TYPES:
        problems.append(f"{where}: unknown type '{kind}'.{_suggest(kind, TYPES)}")
        return None
    column = Column(name=name, type=kind, required=bool(raw.get("required", False)), default=raw.get("default"),
                    unit=raw.get("unit"), help=raw.get("help"), sensitive=bool(raw.get("sensitive", False)),
                    to=raw.get("to"), on_delete=raw.get("on_delete", "restrict"))
    for bound in ("min", "max"):
        if bound in raw:
            if kind not in NUMERIC_TYPES:
                problems.append(f"{where}: '{bound}' only applies to number columns.")
            elif not isinstance(raw[bound], (int, float)) or isinstance(raw[bound], bool):
                problems.append(f"{where}: '{bound}' must be a number.")
            else:
                setattr(column, bound, raw[bound])
    if column.min is not None and column.max is not None and column.min > column.max:
        problems.append(f"{where}: min is larger than max.")
    if kind == "choice":
        column.choices = _parse_choices(where, raw.get("choices"), problems)
        if column.default is not None and column.default not in [c.key for c in column.choices]:
            problems.append(f"{where}: the default '{column.default}' is not one of the choices.")
    elif "choices" in raw:
        problems.append(f"{where}: 'choices' only applies to columns of type 'choice'.")
    if kind in ("link", "links"):
        if not column.to:
            problems.append(f"{where}: a {kind} column needs 'to', naming the table it points at.")
        if column.on_delete not in ON_DELETE:
            problems.append(f"{where}: on_delete '{column.on_delete}' is not known.{_suggest(column.on_delete, ON_DELETE)}")
    else:
        for key in ("to", "on_delete"):
            if key in raw:
                problems.append(f"{where}: '{key}' only applies to link columns.")
    if "unit" in raw and kind not in ("measure", "decimal", "integer"):
        problems.append(f"{where}: 'unit' only applies to number columns.")
    return column


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_watch(file: str, table: str, raw, columns: dict[str, Column], problems: list[str]) -> dict:
    """Check a table's `watch` section (running low, expiring soon, days of cover)."""
    where = f"In {file}, table '{table}', watch"
    if not raw:
        return {}
    if not isinstance(raw, dict):
        problems.append(f"{where}: describe it as settings, like running_low = {{ ... }}.")
        return {}
    problems.extend(_unknown_keys(where, raw, WATCH_KEYS))
    numbers = ("integer", "decimal", "measure", "money")
    watch: dict = {}

    def column(part: str, key: str, value, kinds) -> bool:
        if value not in columns:
            problems.append(f"{where}, {part}: '{key}' names a column '{value}' that does not exist."
                            f"{_suggest(value, list(columns))}")
            return False
        if columns[value].type not in kinds:
            problems.append(f"{where}, {part}: '{key}' must be a {' or '.join(kinds)} column, "
                            f"but '{value}' is {columns[value].type}.")
            return False
        return True

    low = raw.get("running_low")
    if low is not None:
        if not isinstance(low, dict):
            problems.append(f"{where}, running_low: write it like {{ quantity = \"quantity\", minimum = \"minimum\" }}.")
        else:
            problems.extend(_unknown_keys(f"{where}, running_low", low, ("quantity", "minimum")))
            ok = all(column("running_low", k, low.get(k), numbers) for k in ("quantity", "minimum"))
            if ok:
                watch["running_low"] = {"quantity": low["quantity"], "minimum": low["minimum"]}

    expiring = raw.get("expiring")
    if expiring is not None:
        if not isinstance(expiring, dict):
            problems.append(f"{where}, expiring: write it like {{ date = \"expires\", warn_days = 30 }}.")
        else:
            problems.extend(_unknown_keys(f"{where}, expiring", expiring, ("date", "warn_days")))
            days = expiring.get("warn_days", 30)
            if not isinstance(days, int) or isinstance(days, bool) or days < 1:
                problems.append(f"{where}, expiring: warn_days must be a whole number of days, 1 or more.")
            elif column("expiring", "date", expiring.get("date"), ("date",)):
                watch["expiring"] = {"date": expiring["date"], "warn_days": days}

    supply = raw.get("supply")
    if supply is not None:
        keys = ("quantity", "per_person_per_day", "per_pet_per_day", "target_days", "unit", "where")
        if not isinstance(supply, dict):
            problems.append(f"{where}, supply: write it as settings, like {{ quantity = \"quantity\", ... }}.")
        else:
            problems.extend(_unknown_keys(f"{where}, supply", supply, keys))
            ok = column("supply", "quantity", supply.get("quantity"), numbers)
            for key, required in (("per_person_per_day", True), ("per_pet_per_day", False), ("target_days", True)):
                value = supply.get(key)
                if value is None and not required:
                    continue
                if not _number(value) or value < 0 or (key == "target_days" and value <= 0):
                    problems.append(f"{where}, supply: '{key}' must be a number"
                                    f"{' above 0' if key == 'target_days' else ', 0 or more'}.")
                    ok = False
            filters = supply.get("where", {})
            if not isinstance(filters, dict):
                problems.append(f"{where}, supply: 'where' must be settings like {{ category = \"water\" }}.")
                ok = False
            else:
                for name, value in filters.items():
                    if name not in columns:
                        problems.append(f"{where}, supply: 'where' names a column '{name}' that does not exist."
                                        f"{_suggest(name, list(columns))}")
                        ok = False
                    elif columns[name].type == "choice" and value not in [c.key for c in columns[name].choices]:
                        problems.append(f"{where}, supply: '{value}' is not one of the choices for '{name}'.")
                        ok = False
            if ok:
                watch["supply"] = {"quantity": supply["quantity"],
                                   "per_person_per_day": supply["per_person_per_day"],
                                   "per_pet_per_day": supply.get("per_pet_per_day", 0),
                                   "target_days": supply["target_days"],
                                   "unit": str(supply.get("unit", "")), "where": dict(filters)}
    return watch


def _check_tables(module: str, data: dict, requires: list[str], problems: list[str]) -> dict[str, Table]:
    file = "tables.toml"
    problems.extend(_unknown_keys(f"In {file}", data, ("tables",)))
    raw_tables = data.get("tables", {})
    if not isinstance(raw_tables, dict) or not raw_tables:
        problems.append(f"In {file}: no tables are declared. Add at least one [tables.<name>] section.")
        return {}
    tables: dict[str, Table] = {}
    for tname, raw in raw_tables.items():
        where = f"In {file}, table '{tname}'"
        if not NAME.match(tname):
            problems.append(f"{where}: the name must start with a letter and use only lower-case letters, digits and underscores.")
            continue
        if not isinstance(raw, dict):
            problems.append(f"{where}: describe the table with a title and columns.")
            continue
        problems.extend(_unknown_keys(where, raw, TABLE_KEYS))
        if "title" not in raw:
            problems.append(f"{where}: 'title' is missing (the friendly name people see).")
        raw_columns = raw.get("columns", {})
        if not isinstance(raw_columns, dict) or not raw_columns:
            problems.append(f"{where}: no columns are declared.")
            raw_columns = {}
        columns = {}
        for cname, craw in raw_columns.items():
            column = _parse_column(file, tname, cname, craw, problems)
            if column:
                columns[cname] = column
        watch = _check_watch(file, tname, raw.get("watch", {}), columns, problems)
        tables[tname] = Table(tname, str(raw.get("title", tname)), raw.get("description"), columns, watch)
    for table in tables.values():
        for column in table.columns.values():
            if column.type in ("link", "links") and column.to:
                where = f"In {file}, table '{table.name}', column '{column.name}'"
                if "." in column.to:
                    target_module, _, target_table = column.to.partition(".")
                    if target_module != module and target_module not in requires:
                        problems.append(f"{where}: it points at the '{target_module}' module, which must be listed "
                                        f"in module.toml under requires.")
                    if not NAME.match(target_table):
                        problems.append(f"{where}: '{column.to}' is not a valid table name.")
                elif column.to not in tables:
                    problems.append(f"{where}: it points at a table '{column.to}' that this module does not declare."
                                    f"{_suggest(column.to, list(tables))}")
    return tables


def _check_labels(data: dict, tables: dict[str, Table], problems: list[str]) -> dict:
    file = "labels.toml"
    problems.extend(_unknown_keys(f"In {file}", data, ("tables",)))
    for tname, raw in data.get("tables", {}).items():
        where = f"In {file}, table '{tname}'"
        if tname not in tables:
            problems.append(f"{where}: there is no such table in tables.toml.{_suggest(tname, list(tables))}")
            continue
        if not isinstance(raw, dict):
            problems.append(f"{where}: describe the labels as settings.")
            continue
        problems.extend(_unknown_keys(where, raw, LABEL_TABLE_KEYS))
        known = tables[tname].columns
        for cname, craw in raw.get("columns", {}).items():
            if cname not in known:
                problems.append(f"{where}: there is no column '{cname}'.{_suggest(cname, list(known))}")
            elif isinstance(craw, dict):
                problems.extend(_unknown_keys(f"{where}, column '{cname}'", craw, LABEL_COLUMN_KEYS))
        for listing in ("form", "list"):
            for cname in raw.get(listing, []):
                if cname not in known:
                    problems.append(f"{where}: '{listing}' names a column '{cname}' that does not exist."
                                    f"{_suggest(cname, list(known))}")
    return data


def load_module(folder: Path) -> Module:
    """Read and check one module folder. Raises ModuleError listing every problem found."""
    folder = Path(folder)
    problems: list[str] = []
    meta = _read_toml(folder / "module.toml", problems, required=True)
    if meta:
        _check_module_toml(folder, meta, problems)
    requires = meta.get("requires", []) if isinstance(meta.get("requires", []), list) else []
    tables = _check_tables(folder.name, _read_toml(folder / "tables.toml", problems, required=True),
                           requires, problems)
    labels = _check_labels(_read_toml(folder / "labels.toml", problems, required=False), tables, problems)
    try:
        migrations = load_track(folder.name, folder / "migrations")
    except MigrationError as error:
        problems.append(str(error))
        migrations = []
    if problems:
        raise ModuleError(folder.name, problems)
    return Module(name=meta["name"], title=meta["title"], version=meta["version"],
                  description=meta["description"], kind=meta["kind"], requires=list(requires),
                  outbound_hosts=list(meta.get("outbound_hosts", [])), folder=folder,
                  tables=tables, labels=labels, migrations=migrations)


def discover(modules_dir: Path) -> tuple[list[Module], dict[str, list[str]]]:
    """Load every module folder. A broken module is reported, never fatal to the others."""
    modules: list[Module] = []
    failures: dict[str, list[str]] = {}
    modules_dir = Path(modules_dir)
    if not modules_dir.is_dir():
        return modules, failures
    for folder in sorted(p for p in modules_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        try:
            modules.append(load_module(folder))
        except ModuleError as error:
            failures[folder.name] = error.problems
    return dependency_order(modules, failures), failures


def dependency_order(modules: list[Module], failures: dict[str, list[str]]) -> list[Module]:
    """Order modules so each comes after the ones it requires; drop any whose requirements fail."""
    by_name = {m.name: m for m in modules}
    ordered: list[Module] = []
    state: dict[str, str] = {}

    def visit(module: Module, path: list[str]) -> bool:
        if state.get(module.name) == "done":
            return True
        if state.get(module.name) == "failed":
            return False
        if module.name in path:
            cycle = " -> ".join(path[path.index(module.name):] + [module.name])
            failures.setdefault(module.name, []).append(f"Modules require each other in a loop ({cycle}).")
            state[module.name] = "failed"
            return False
        for name in module.requires:
            if name not in by_name:
                reason = "has problems of its own" if name in failures else "is not installed"
                failures.setdefault(module.name, []).append(f"It requires the '{name}' module, which {reason}.")
                state[module.name] = "failed"
                return False
            if not visit(by_name[name], path + [module.name]):
                failures.setdefault(module.name, []).append(f"It requires the '{name}' module, which could not be loaded.")
                state[module.name] = "failed"
                return False
        state[module.name] = "done"
        ordered.append(module)
        return True

    for module in modules:
        visit(module, [])
    return ordered
