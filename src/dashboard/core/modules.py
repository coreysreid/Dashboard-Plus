"""Find module folders, check their files, and explain any mistakes in plain words."""
from __future__ import annotations

import csv
import difflib
import re
import string
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
TABLE_KEYS = ("title", "description", "columns", "watch", "adjusts", "parent", "total", "record_name")
ADJUST_KEYS = ("link", "quantity", "amount", "direction", "adds")
# Optional, for batches (DESIGN.md 5.7): the record a batch belongs to, how to pick or start one,
# and the two reasons a stocktake count records its difference with (decision 0070).
ADJUST_BATCH_KEYS = ("belongs_to", "new_batch", "oldest_first", "counts")
TOTAL_KEYS = ("link", "amount", "into", "earliest", "starts_from")
WATCH_KEYS = ("running_low", "expiring", "supply", "gaps")
GAP_KEYS = ("missing", "none", "where", "message")
COLUMN_KEYS = ("type", "required", "required_when", "default", "min", "max", "unit", "choices", "help", "sensitive",
               "to", "on_delete")
LABEL_TABLE_KEYS = ("title", "columns", "form", "list", "empty", "home")
HOME_PLACES = ("main", "more")  # where a table sits on the home page: shown large, or in the line of links
LABEL_COLUMN_KEYS = ("label", "help", "show_when", "suggest_from", "fills", "answers", "blank")


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
    required_when: dict = field(default_factory=dict)  # required only while another choice has a value


@dataclass
class Table:
    name: str
    title: str
    description: str | None
    columns: dict[str, Column]
    watch: dict = field(default_factory=dict)  # checked `watch` section (DESIGN.md 5.1)
    adjusts: dict = field(default_factory=dict)  # checked `adjusts` section (DESIGN.md 5.3)
    parent: str | None = None  # a link to this same table that nests records (DESIGN.md 5.6)
    total: dict = field(default_factory=dict)  # checked `total` section: batches add up into a record (5.7)
    record_name: str | None = None  # how to name a record with no name of its own, like "{quantity} {item.unit} of {item}"


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
    sheets: list = field(default_factory=list)  # checked printable sheets (DESIGN.md 5.2)
    # Lists of common things to pick from while typing, by (table, column) (DESIGN.md 5.5).
    catalogues: dict = field(default_factory=dict)


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
    if name is not None and not NAME.match(str(name)):
        problems.append(f"{where}: name must start with a letter and use only lower-case letters, digits and "
                        f"underscores, like \"garden\".")
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
                    to=raw.get("to"), on_delete=raw.get("on_delete", "restrict"),
                    required_when=raw.get("required_when") if isinstance(raw.get("required_when"), dict) else {})
    if "required_when" in raw and (not isinstance(raw["required_when"], dict) or len(raw["required_when"]) != 1):
        problems.append(f"{where}: required_when names one choice column and a value, like {{ category = \"water\" }}.")
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
            problems.extend(_unknown_keys(f"{where}, expiring", expiring,
                                          ("date", "warn_days", "wording", "what", "only_positive", "where")))
            days = expiring.get("warn_days", 30)
            wording = expiring.get("wording", "expires")
            what = expiring.get("what", "")
            if not isinstance(days, int) or isinstance(days, bool) or days < 1:
                problems.append(f"{where}, expiring: warn_days must be a whole number of days, 1 or more.")
            elif wording not in ("expires", "due"):
                problems.append(f"{where}, expiring: wording must be \"expires\" (use-by dates) or \"due\" "
                                f"(things to do by a date).")
            elif not isinstance(what, str):
                problems.append(f"{where}, expiring: 'what' must be a few words, like \"vaccinations\".")
            elif column("expiring", "date", expiring.get("date"), ("date",)) and (
                    "only_positive" not in expiring
                    or column("expiring", "only_positive", expiring["only_positive"], numbers)) and (
                    # Only rows matching every filter are watched: not a loan already returned (decision 0072).
                    "where" not in expiring
                    or _check_where(f"{where}, expiring, where", expiring["where"], columns, problems)):
                watch["expiring"] = {"date": expiring["date"], "warn_days": days, "wording": wording, "what": what}
                if "only_positive" in expiring:  # a batch that is used up has nothing left to warn about
                    watch["expiring"]["only_positive"] = expiring["only_positive"]
                if "where" in expiring:
                    watch["expiring"]["where"] = dict(expiring["where"])

    supply = raw.get("supply")
    if supply is not None:
        keys = ("quantity", "per_person_per_day", "per_pet_per_day", "target_days", "unit", "label", "where",
                "counts_only", "unit_from", "unit_words")
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
            unit_from = supply.get("unit_from")
            if unit_from is not None and (unit_from not in columns or columns[unit_from].type != "text"
                                          or columns[unit_from].sensitive):
                problems.append(f"{where}, supply: 'unit_from' must name a text column holding each row's unit, "
                                f"not a private one.")
                ok = False
            words = supply.get("unit_words", [])
            if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
                problems.append(f"{where}, supply: 'unit_words' must be a list of other ways to write the unit.")
                ok = False
            counts_only = supply.get("counts_only", {})
            if not isinstance(counts_only, dict):
                problems.append(f"{where}, supply: 'counts_only' must be settings like {{ drinking = true }}.")
                ok = False
            else:
                for name, value in counts_only.items():
                    if name not in columns or columns[name].type != "boolean" or not isinstance(value, bool):
                        problems.append(f"{where}, supply: 'counts_only' must name a yes/no column with true or "
                                        f"false, like {{ drinking = true }}.")
                        ok = False
            if ok:
                watch["supply"] = {"quantity": supply["quantity"],
                                   "per_person_per_day": supply["per_person_per_day"],
                                   "per_pet_per_day": supply.get("per_pet_per_day", 0),
                                   "target_days": supply["target_days"],
                                   "unit": str(supply.get("unit", "")),
                                   "label": str(supply.get("label", "supplies")), "where": dict(filters),
                                   "counts_only": dict(supply.get("counts_only", {})),
                                   "unit_from": supply.get("unit_from"),
                                   "unit_words": [str(w).lower() for w in supply.get("unit_words", [])]}
    return watch


def _check_adjusts(file: str, table: Table, tables: dict[str, Table], problems: list[str]) -> dict:
    """Check an `adjusts` section: each record here adds to or takes from a quantity on a linked record."""
    raw = table.adjusts
    where = f"In {file}, table '{table.name}', adjusts"
    if not isinstance(raw, dict):
        problems.append(f"{where}: describe it as settings (link, quantity, amount, direction, adds).")
        return {}
    problems.extend(_unknown_keys(where, raw, ADJUST_KEYS + ADJUST_BATCH_KEYS))
    for key in ADJUST_KEYS:
        if key not in raw:
            problems.append(f"{where}: '{key}' is missing.")
    if any(key not in raw for key in ADJUST_KEYS):
        return {}
    columns = table.columns
    numbers = ("integer", "decimal", "measure")
    link = columns.get(raw["link"])
    if link is None or link.type != "link" or "." in (link.to or "") or link.to not in tables:
        problems.append(f"{where}: 'link' must name a link column to another table of this module.")
        return {}
    target = tables[link.to]
    quantity = target.columns.get(raw["quantity"])
    if quantity is None or quantity.type not in numbers:
        problems.append(f"{where}: 'quantity' must name a number column of '{link.to}'."
                        f"{_suggest(raw['quantity'], list(target.columns))}")
        return {}
    amount = columns.get(raw["amount"])
    if amount is None or amount.type not in numbers:
        problems.append(f"{where}: 'amount' must name a number column of this table.{_suggest(raw['amount'], list(columns))}")
        return {}
    direction = columns.get(raw["direction"])
    if direction is None or direction.type != "choice":
        problems.append(f"{where}: 'direction' must name a choice column of this table.")
        return {}
    keys = [c.key for c in direction.choices]
    adds = raw["adds"] if isinstance(raw["adds"], list) else []
    unknown = [a for a in adds if a not in keys]
    if not isinstance(raw["adds"], list) or unknown:
        problems.append(f"{where}: 'adds' must list choices of '{raw['direction']}' that add to the quantity; "
                        f"not choices: {', '.join(map(str, unknown)) or raw['adds']}. Allowed: {', '.join(keys)}.")
        return {}
    rule = {"link": raw["link"], "target": link.to, "quantity": raw["quantity"], "amount": raw["amount"],
            "direction": raw["direction"], "adds": list(adds)}
    if "belongs_to" in raw:  # records here change batches (DESIGN.md 5.7)
        owner = columns.get(raw["belongs_to"])
        batch_owner = target.columns.get(raw["belongs_to"])
        if owner is None or owner.type != "link" or batch_owner is None or batch_owner.type != "link" \
                or owner.to != batch_owner.to:
            problems.append(f"{where}: 'belongs_to' must name a link column that both this table and "
                            f"'{link.to}' have, pointing at the same table (such as \"item\").")
            return {}
        rule["belongs_to"] = raw["belongs_to"]
        new_batch = raw.get("new_batch", {})
        if not isinstance(new_batch, dict) or any(
                k not in target.columns or v not in columns for k, v in new_batch.items()):
            problems.append(f"{where}: 'new_batch' maps columns of '{link.to}' to columns of this table, "
                            f"like {{ expires = \"expires\" }}.")
            return {}
        rule["new_batch"] = dict(new_batch)
        oldest = raw.get("oldest_first")
        if oldest is not None and (oldest not in target.columns or target.columns[oldest].type != "date"):
            problems.append(f"{where}: 'oldest_first' must name a date column of '{link.to}'.")
            return {}
        rule["oldest_first"] = oldest
        if "counts" in raw:  # a stocktake count of one batch (decision 0070)
            counts = raw["counts"]
            note = counts.get("note") if isinstance(counts, dict) else None
            if not isinstance(counts, dict) or not {"more", "less"} <= set(counts) <= {"more", "less", "note"} or \
                    counts.get("more") not in adds or counts.get("less") not in keys or counts["less"] in adds or \
                    (note is not None and (note not in columns or columns[note].type not in ("text", "longtext"))):
                problems.append(f"{where}: 'counts' names the reason for counting more than recorded (one that "
                                f"adds), the reason for counting less (one that takes away) and, if wanted, a "
                                f"text column for the count, like "
                                f"{{ more = \"counted_more\", less = \"counted_less\", note = \"notes\" }}.")
                return {}
            rule["counts"] = {"more": counts["more"], "less": counts["less"], "note": note}
    elif any(k in raw for k in ("new_batch", "oldest_first", "counts")):
        problems.append(f"{where}: 'new_batch', 'oldest_first' and 'counts' need 'belongs_to'.")
        return {}
    return rule


def _check_total(file: str, table: Table, tables: dict[str, Table], raw, problems: list[str]) -> dict:
    """Check a `total` section: these records (batches) add up into a column of the record they belong to."""
    where = f"In {file}, table '{table.name}', total"
    if not isinstance(raw, dict):
        problems.append(f"{where}: describe it as settings (link, amount, into).")
        return {}
    problems.extend(_unknown_keys(where, raw, TOTAL_KEYS))
    numbers = ("integer", "decimal", "measure")
    link = table.columns.get(raw.get("link"))
    if link is None or link.type != "link" or "." in (link.to or "") or link.to not in tables:
        problems.append(f"{where}: 'link' must name a link column to another table of this module.")
        return {}
    target = tables[link.to]
    amount, into = table.columns.get(raw.get("amount")), target.columns.get(raw.get("into"))
    if amount is None or amount.type not in numbers or into is None or into.type not in numbers:
        problems.append(f"{where}: 'amount' must name a number column of this table and 'into' a number "
                        f"column of '{link.to}'.")
        return {}
    rule = {"link": raw["link"], "target": link.to, "amount": raw["amount"], "into": raw["into"],
            "earliest": None, "starts_from": []}
    earliest = raw.get("earliest")
    if earliest is not None:
        ok = isinstance(earliest, dict) and set(earliest) == {"date", "into"}
        here = table.columns.get(earliest.get("date")) if ok else None
        there = target.columns.get(earliest.get("into")) if ok else None
        if not ok or here is None or here.type != "date" or there is None or there.type != "date":
            problems.append(f"{where}: 'earliest' must be like {{ date = \"expires\", into = \"expires\" }}, "
                            f"naming date columns here and in '{link.to}'.")
            return {}
        rule["earliest"] = dict(earliest)
    starts = raw.get("starts_from", [])
    if not isinstance(starts, list) or any(c not in table.columns or c not in target.columns for c in starts):
        problems.append(f"{where}: 'starts_from' lists columns that both this table and '{link.to}' have.")
        return {}
    rule["starts_from"] = list(starts)
    return rule


def _check_record_name(file: str, table: Table, tables: dict[str, Table], template, problems: list[str]) -> str | None:
    """Check `record_name`: a pattern like "{quantity} {item.unit} of {item}" naming a record."""
    where = f"In {file}, table '{table.name}', record_name"
    try:
        parsed = list(string.Formatter().parse(template.replace("[", "").replace("]", ""))) \
            if isinstance(template, str) else []
        fields = [f for _, f, _, _ in parsed if f is not None] or None
        if any(spec or conversion for _, f, spec, conversion in parsed if f is not None):
            fields = None  # {quantity:>5} and {item!r} are not filled in; plain {name} only
    except ValueError:
        fields = None
    if not fields:
        problems.append(f"{where}: write it like \"{{quantity}} {{item.unit}} of {{item}}\".")
        return None
    for name in fields:
        link, _, field_name = name.partition(".")
        column = table.columns.get(link)
        if column is None or (field_name and (column.type != "link" or "." in (column.to or "")
                                              or field_name not in tables.get(column.to, Table("", "", None, {})).columns)):
            problems.append(f"{where}: '{{{name}}}' must name a column of this table, or a link column and a "
                            f"column of the table it points at.")
            return None
        named = tables[column.to].columns[field_name] if field_name else column
        if named.sensitive:  # a record's name shows on lists, pickers and sheets
            problems.append(f"{where}: '{{{name}}}' is private, so it can't be part of a record's name.")
            return None
    return template


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
        tables[tname] = Table(tname, str(raw.get("title", tname)), raw.get("description"), columns, watch,
                              raw.get("adjusts", {}))
    for table in tables.values():
        for column in table.columns.values():
            for other, value in column.required_when.items():
                col = table.columns.get(other)
                if col is None or col.type != "choice" or value not in [c.key for c in col.choices]:
                    problems.append(f"In {file}, table '{table.name}', column '{column.name}': required_when must "
                                    f"name a choice column of this table and one of its choices.")
    for tname, raw in raw_tables.items():
        parent = raw.get("parent") if isinstance(raw, dict) else None
        if parent is not None and tname in tables:
            column = tables[tname].columns.get(parent)
            if column is None or column.type != "link" or column.to != tname:
                problems.append(f"In {file}, table '{tname}': 'parent' must name a link column of this table that "
                                f"points at '{tname}' itself, like parent = \"inside\".")
            else:
                tables[tname].parent = parent
    for table in tables.values():
        if table.adjusts:
            table.adjusts = _check_adjusts(file, table, tables, problems)
    for tname, raw in raw_tables.items():
        if isinstance(raw, dict) and tname in tables:
            if "total" in raw:
                tables[tname].total = _check_total(file, tables[tname], tables, raw["total"], problems)
            if "record_name" in raw:
                tables[tname].record_name = _check_record_name(file, tables[tname], tables, raw["record_name"],
                                                               problems)
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
    for tname, raw in raw_tables.items():
        gaps = raw.get("watch", {}).get("gaps") if isinstance(raw, dict) and isinstance(raw.get("watch"), dict) else None
        if gaps is not None and tname in tables:
            tables[tname].watch["gaps"] = _check_gaps(file, tables[tname], tables, gaps, problems)
    return tables


def _check_where(where: str, filters, columns: dict[str, Column], problems: list[str]) -> bool:
    """Check equality filters like { role = "doctor" } or { lives_here = true }."""
    if not isinstance(filters, dict) or not filters:
        problems.append(f"{where}: write it as settings, like {{ role = \"doctor\" }}.")
        return False
    ok = True
    for name, value in filters.items():
        column = columns.get(name)
        if column is None:
            problems.append(f"{where}: there is no column '{name}'.{_suggest(name, list(columns))}")
            ok = False
        elif column.type == "choice" and value not in [c.key for c in column.choices]:
            problems.append(f"{where}: '{value}' is not one of the choices for '{name}'. "
                            f"Allowed: {', '.join(c.key for c in column.choices)}.")
            ok = False
        elif column.type == "boolean" and not isinstance(value, bool):
            problems.append(f"{where}: '{name}' is a yes/no column, so write true or false.")
            ok = False
        elif column.type in ("links", "file"):
            problems.append(f"{where}: '{name}' cannot be used as a filter.")
            ok = False
    return ok


def _linked_column(spec: str, table: Table, tables: dict[str, Table]) -> Column | None:
    """The column a name like "phone" or "person.phone" refers to, within this module."""
    if "." not in spec:
        return table.columns.get(spec)
    link, _, field_name = spec.partition(".")
    column = table.columns.get(link)
    if column is None or column.type != "link" or "." in (column.to or "") or column.to not in tables:
        return None
    return tables[column.to].columns.get(field_name)


def _check_gaps(file: str, table: Table, tables: dict[str, Table], raw, problems: list[str]) -> list[dict]:
    """Check `gaps`: details worth filling in, such as an emergency contact with no phone number."""
    where = f"In {file}, table '{table.name}', watch.gaps"
    if not isinstance(raw, list):
        problems.append(f"{where}: write each gap as a [[tables.{table.name}.watch.gaps]] section.")
        return []
    gaps = []
    for number, gap in enumerate(raw, start=1):
        g_where = f"{where} {number}"
        if not isinstance(gap, dict):
            problems.append(f"{g_where}: describe it with 'missing' or 'none', and a 'message'.")
            continue
        problems.extend(_unknown_keys(g_where, gap, GAP_KEYS))
        message = gap.get("message")
        if not isinstance(message, str) or not message.strip():
            problems.append(f"{g_where}: 'message' is missing (the question people see).")
            continue
        try:
            parsed = list(string.Formatter().parse(message))
            fields = [f for _, f, _, _ in parsed if f is not None]
            if any(spec or conversion for _, f, spec, conversion in parsed if f is not None):
                problems.append(f"{g_where}: 'message' can only use plain {{column}} names, with nothing after them.")
                continue
        except ValueError:
            problems.append(f"{g_where}: 'message' has an unmatched {{ or }}.")
            continue
        if ("missing" in gap) == ("none" in gap):
            problems.append(f"{g_where}: use either 'missing' (a detail left blank) or 'none' (nothing recorded yet), "
                            f"not both or neither.")
            continue
        if "none" in gap:
            if "where" in gap:
                problems.append(f"{g_where}: 'where' goes with 'missing'; for 'none' put the filters in 'none' itself.")
                continue
            if fields:
                problems.append(f"{g_where}: a 'none' message has no record to fill in, so it cannot use {{...}}.")
                continue
            # An empty filter, none = {}, asks when the table has no records at all.
            if gap["none"] == {} or _check_where(f"{g_where}, none", gap["none"], table.columns, problems):
                gaps.append({"none": dict(gap["none"]), "message": message})
            continue
        missing = gap["missing"]
        link = table.columns.get(missing.partition(".")[0]) if isinstance(missing, str) and "." in missing else None
        if link is not None and link.type == "link" and "." in (link.to or ""):
            # A link into a module this one requires (like vet.phone into People): its column is
            # checked once every module has loaded (see dependency_order).
            pass
        elif not isinstance(missing, str) or _linked_column(missing, table, tables) is None:
            problems.append(f"{g_where}: 'missing' must name a column of this table, or a link column and a column "
                            f"of the table it points at, like \"person.phone\".{_suggest(missing, list(table.columns))}")
            continue
        filters = gap.get("where", {})
        if filters and not _check_where(f"{g_where}, where", filters, table.columns, problems):
            continue
        bad = [f for f in fields if f == "" or f not in table.columns]
        if bad:
            problems.append(f"{g_where}: 'message' can only fill in columns of this table, like {{name}}; "
                            f"not {', '.join('{' + b + '}' for b in bad)}.{_suggest(bad[0], list(table.columns))}")
            continue
        private = [f for f in fields if table.columns[f].sensitive]
        if private:  # the question shows on the home page and Needs attention
            problems.append(f"{g_where}: '{{{private[0]}}}' is private, so it can't be part of a question.")
            continue
        gaps.append({"missing": missing, "where": dict(filters), "message": message})
    return gaps


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
        if "empty" in raw and (not isinstance(raw["empty"], str) or not raw["empty"].strip()):
            problems.append(f"{where}: 'empty' must be a short sentence, like \"Add a few things from the pantry.\"")
        if "home" in raw and raw["home"] not in HOME_PLACES:
            problems.append(f"{where}: 'home' must be \"main\" (shown large on the home page) or \"more\" "
                            f"(in the line of other lists), not {raw['home']!r}.")
        known = tables[tname].columns
        for cname, craw in raw.get("columns", {}).items():
            if cname not in known:
                problems.append(f"{where}: there is no column '{cname}'.{_suggest(cname, list(known))}")
            elif isinstance(craw, dict):
                problems.extend(_unknown_keys(f"{where}, column '{cname}'", craw, LABEL_COLUMN_KEYS))
                if "blank" in craw:  # the words for leaving "Which batch" blank (DESIGN.md 5.7)
                    blank = craw["blank"]
                    rule = tables[tname].adjusts or {}
                    if not isinstance(blank, dict) or not blank or set(blank) - {"adds", "takes"} or \
                            any(not isinstance(v, str) or not v.strip() for v in blank.values()):
                        problems.append(f"{where}, column '{cname}': blank gives the words for leaving it blank, "
                                        f"like {{ adds = \"Start a new batch\", takes = \"Use the oldest batch\" }}.")
                    elif rule.get("link") != cname or not rule.get("belongs_to"):
                        problems.append(f"{where}, column '{cname}': blank only applies to the batch link of a "
                                        f"table whose 'adjusts' has 'belongs_to'.")
                if "show_when" in craw:
                    shown = craw["show_when"]
                    if not isinstance(shown, dict) or len(shown) != 1:
                        problems.append(f"{where}, column '{cname}': show_when names one choice column and a value, "
                                        f"like {{ category = \"water\" }}.")
                    else:
                        (other, value), = shown.items()
                        col = known.get(other)
                        if col is None or col.type != "choice" or value not in [c.key for c in col.choices]:
                            problems.append(f"{where}, column '{cname}': show_when must name a choice column of "
                                            f"this table and one of its choices.")
        for listing in ("form", "list"):
            for cname in raw.get(listing, []):
                if cname not in known:
                    problems.append(f"{where}: '{listing}' names a column '{cname}' that does not exist."
                                    f"{_suggest(cname, list(known))}")
    return data


SHEET_KEYS = ("name", "title", "intro", "section")
SECTION_KEYS = ("title", "table", "where", "columns", "order_by")


def _check_sheets(data: dict, tables: dict[str, Table], problems: list[str]) -> list[dict]:
    """Check sheets.toml: one-page printable sheets built from the module's tables."""
    file = "sheets.toml"
    if not data:
        return []
    problems.extend(_unknown_keys(f"In {file}", data, ("sheet",)))
    raw_sheets = data.get("sheet", [])
    if not isinstance(raw_sheets, list):
        problems.append(f"In {file}: write each sheet as a [[sheet]] section.")
        return []
    sheets, names = [], set()
    for number, raw in enumerate(raw_sheets, start=1):
        where = f"In {file}, sheet {number}"
        if not isinstance(raw, dict):
            continue
        problems.extend(_unknown_keys(where, raw, SHEET_KEYS))
        name = raw.get("name")
        if not isinstance(name, str) or not NAME.match(name):
            problems.append(f"{where}: 'name' must be lower-case letters, digits and underscores, like \"emergency\".")
            continue
        where = f"In {file}, sheet '{name}'"
        if name in names:
            problems.append(f"{where}: two sheets have this name.")
        names.add(name)
        if "title" not in raw:
            problems.append(f"{where}: 'title' is missing.")
        sections = []
        raw_sections = raw.get("section", [])
        if not isinstance(raw_sections, list) or not raw_sections:
            problems.append(f"{where}: add at least one [[sheet.section]].")
            raw_sections = []
        for s_number, section in enumerate(raw_sections, start=1):
            s_where = f"{where}, section {s_number}"
            if not isinstance(section, dict):
                continue
            problems.extend(_unknown_keys(s_where, section, SECTION_KEYS))
            table = section.get("table")
            if table not in tables:
                problems.append(f"{s_where}: 'table' names '{table}', which this module does not declare."
                                f"{_suggest(table, list(tables))}")
                continue
            columns = tables[table].columns
            chosen = section.get("columns", [])
            if not isinstance(chosen, list) or not chosen:
                problems.append(f"{s_where}: list the columns to print, like columns = [\"name\", \"phone\"].")
                chosen = []
            bad = []
            for c in chosen:
                if not isinstance(c, str):
                    bad.append(c)
                    continue
                if "." in c:  # a column of the record a link points at, e.g. "person.phone"
                    link, _, field_name = c.partition(".")
                    target = columns.get(link)
                    if target is not None and target.type == "link" and "." in (target.to or ""):
                        # A link into a module this one requires (like roadside_contact.phone into People):
                        # its column is checked once every module has loaded (see dependency_order).
                        continue
                    if target is None or target.type != "link" or target.to not in tables:
                        problems.append(f"{s_where}: '{c}' must start with a link column, like \"person.phone\".")
                        bad.append(c)
                    elif field_name not in tables[target.to].columns:
                        problems.append(f"{s_where}: there is no column '{field_name}' in '{target.to}'."
                                        f"{_suggest(field_name, list(tables[target.to].columns))}")
                        bad.append(c)
                elif c not in columns:
                    problems.append(f"{s_where}: there is no column '{c}' in '{table}'.{_suggest(c, list(columns))}")
                    bad.append(c)
            filters = section.get("where", {})
            if not isinstance(filters, dict):
                problems.append(f"{s_where}: 'where' must be settings like {{ lives_here = true }}.")
                filters = {}
            for c in filters:
                link, _, field_name = c.partition(".")
                if field_name:  # a column of the linked record, e.g. "item.category"
                    target = columns.get(link)
                    if target is None or target.type != "link" or target.to not in tables \
                            or field_name not in tables[target.to].columns:
                        problems.append(f"{s_where}: 'where' names '{c}', which must be a link column and a "
                                        f"column of the table it points at.")
                elif c not in columns:
                    problems.append(f"{s_where}: 'where' names a column '{c}' that does not exist.{_suggest(c, list(columns))}")
            order_by = section.get("order_by", "id")
            if order_by != "id" and order_by not in columns:
                problems.append(f"{s_where}: 'order_by' names a column '{order_by}' that does not exist."
                                f"{_suggest(order_by, list(columns))}")
            sections.append({"title": str(section.get("title", tables[table].title)), "table": table,
                             "where": dict(filters), "columns": [c for c in chosen if c not in bad],
                             "order_by": order_by})
        sheets.append({"name": name, "title": str(raw.get("title", name)), "intro": raw.get("intro"),
                       "sections": sections})
    return sheets


def _catalogue_value(column: Column, text: str):
    """A catalogue cell as the value it fills in, or None when blank or not valid for that column."""
    text = (text or "").strip()
    if not text:
        return None
    if column.type == "boolean":
        return {"yes": True, "no": False}.get(text.lower())
    if column.type == "choice":
        return text if text in [c.key for c in column.choices] else None
    return text


def _load_catalogues(folder: Path, labels: dict, tables: dict[str, Table], problems: list[str]) -> dict:
    """Read the CSV lists named by `suggest_from` in labels.toml: things to pick from while typing."""
    catalogues = {}
    for tname, raw in (labels or {}).get("tables", {}).items():
        for cname, craw in (raw.get("columns", {}) if isinstance(raw, dict) else {}).items():
            if not isinstance(craw, dict) or "suggest_from" not in craw or tname not in tables:
                continue
            where = f"In labels.toml, table '{tname}', column '{cname}'"
            table = tables[tname]
            if cname not in table.columns or table.columns[cname].type != "text":
                problems.append(f"{where}: suggest_from only works on a text column.")
                continue
            path = folder / str(craw["suggest_from"])
            if path.suffix != ".csv" or path.parent != folder or not path.is_file():
                problems.append(f"{where}: suggest_from must name a .csv file in the module folder.")
                continue
            fills = craw.get("fills", {})
            bad = [c for c in (fills or {}) if c not in table.columns] if isinstance(fills, dict) else ["?"]
            if bad:
                problems.append(f"{where}: fills names columns that do not exist: {', '.join(bad)}.")
                continue
            with open(path, encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                header = reader.fieldnames or []
                missing = [h for h in ["name", *fills.values()] if h not in header]
                if missing:
                    problems.append(f"In {path.name}: the first line needs the columns {', '.join(missing)}.")
                    continue
                entries = []
                for row in reader:
                    name = (row.get("name") or "").strip()
                    if not name:
                        continue
                    also = [a.strip() for a in (row.get("also_called") or "").split("|") if a.strip()]
                    filled = {target: _catalogue_value(table.columns[target], row.get(source))
                              for target, source in fills.items()}
                    entries.append({"name": name, "also": also,
                                    "fills": {k: v for k, v in filled.items() if v is not None}})
            catalogues[(tname, cname)] = entries
    return catalogues


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
    sheets = _check_sheets(_read_toml(folder / "sheets.toml", problems, required=False), tables, problems)
    catalogues = _load_catalogues(folder, labels, tables, problems)
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
                  tables=tables, labels=labels, migrations=migrations, sheets=sheets, catalogues=catalogues)


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
        except Exception as error:  # noqa: BLE001 - a malformed file must never stop the program
            failures[folder.name] = [f"Its files could not be read ({type(error).__name__}: {error}). "
                                     f"Check them against docs/DESIGN.md section 6."]
    return dependency_order(modules, failures), failures


def _cross_module_gap_problems(module: Module, by_name: dict[str, Module]) -> list[str]:
    """Check gaps like "vet.phone" whose link points into another module, once that module is loaded."""
    problems = []
    for table in module.tables.values():
        for gap in table.watch.get("gaps", []):
            link_name, _, field_name = gap.get("missing", "").partition(".")
            link = table.columns.get(link_name)
            if not field_name or link is None or "." not in (link.to or ""):
                continue
            other, _, other_table = link.to.partition(".")
            target = by_name[other].tables.get(other_table) if other in by_name else None
            if target is None or field_name not in target.columns:
                choices = list(target.columns) if target else []
                problems.append(f"In tables.toml, table '{table.name}', watch.gaps: '{gap['missing']}' names a column "
                                f"'{field_name}' that '{link.to}' does not have.{_suggest(field_name, choices)}")
    return problems


def _cross_module_sheet_problems(module: Module, by_name: dict[str, Module]) -> list[str]:
    """Check sheet columns like "roadside_contact.phone" whose link points into another module.

    The column must exist there and must not be private: a sheet is printed and left out, and another
    module's private detail must not reach it by a link (decision 0072)."""
    problems = []
    for sheet in module.sheets:
        for number, section in enumerate(sheet["sections"], start=1):
            table = module.tables.get(section["table"])
            for spec in section["columns"] if table else []:
                link_name, _, field_name = spec.partition(".")
                link = table.columns.get(link_name)
                if not field_name or link is None or "." not in (link.to or ""):
                    continue
                other, _, other_table = link.to.partition(".")
                target = by_name[other].tables.get(other_table) if other in by_name else None
                where = f"In sheets.toml, sheet '{sheet['name']}', section {number}"
                if target is None or field_name not in target.columns:
                    choices = list(target.columns) if target else []
                    problems.append(f"{where}: '{spec}' names a column '{field_name}' that '{link.to}' does not "
                                    f"have.{_suggest(field_name, choices)}")
                elif target.columns[field_name].sensitive:
                    problems.append(f"{where}: '{spec}' is private in the '{other}' module, so this sheet can't "
                                    f"print it.")
    return problems


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
        problems = _cross_module_gap_problems(module, by_name) + _cross_module_sheet_problems(module, by_name)
        if problems:
            failures.setdefault(module.name, []).extend(problems)
            state[module.name] = "failed"
            return False
        state[module.name] = "done"
        ordered.append(module)
        return True

    for module in modules:
        visit(module, [])
    return ordered
