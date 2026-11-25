"""Find module folders, check their files, and explain any mistakes in plain words."""
from __future__ import annotations

import csv
import difflib
import re
import string
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dashboard.core import prompts as prompt_files
from dashboard.core.settings import HOUSEHOLD_CHOICES
from dashboard.core.migrations import Migration, load_track, MigrationError
from dashboard.errors import PlainError

CORE_API = "1"
NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
RESERVED_NAMES = {"core"}  # the program's own tables begin "core__"; no module may take that name (decision 0069)
CHOICE_KEY = re.compile(r"^[a-z0-9][a-z0-9_]*$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
KINDS = ("declarative", "code")
TYPES = ("text", "longtext", "integer", "decimal", "boolean", "date", "datetime", "choice",
         "link", "links", "money", "measure", "file")
NUMERIC_TYPES = ("integer", "decimal", "money", "measure")
ON_DELETE = ("restrict", "cascade", "clear")
# Columns every table gets automatically (DESIGN.md section 3); modules may not declare them.
SYSTEM_COLUMNS = ("id", "created_at", "updated_at", "review_status", "source", "batch_id",
                  "edited_by_person", "deleted_at", "global_id", "row_revision")  # the last two: decision 0100
# Whether a column's value may travel to another computer of the household later (decision 0100).
TRAVELS = ("always", "never")

MODULE_KEYS = ("name", "title", "version", "description", "core_api", "kind", "requires", "optional_requires",
               "outbound_hosts")
MODULE_REQUIRED = ("name", "title", "version", "description", "core_api", "kind")
TABLE_KEYS = ("title", "description", "columns", "watch", "adjusts", "parent", "total", "record_name", "actions",
              "pair", "suggestions", "chart", "daily", "confirm", "takes_over", "calendar", "private", "bars", "timeline",
              "price")
# One reminder per policy (decision 0117): records of an older list in another module (Vehicle insurance) that
# the household may choose, one by one, to have reminded from this table instead. `where` is what such a record
# is here (a vehicle policy), `copy` which of this table's columns take which of the other's, the date included.
TAKES_OVER_KEYS = ("from", "where", "copy")
# The household's words around that choice (labels.toml `takes_over`); each has a plain default in the core.
TAKES_OVER_WORDS = ("title", "intro", "keep", "review", "later", "warning", "question", "no_date", "moved",
                    "source_kept", "source_moved", "target_moved", "target_off", "returned", "needs_choice",
                    "duplicate", "duplicate_source", "back")
# A chart of one subject's dated readings, such as one pet's weigh-ins as dots (decision 0109); `unit`, `latest`
# and `caveat` let readings carry their own unit, as an odometer's km or mi, and say what they are (decision 0111).
CHART_KEYS = ("kind", "x", "y", "per", "what", "entry", "subject", "unit", "latest", "caveat", "ranges", "change",
              "line", "scale")
# Trends on a dots chart (decision 0119): date range presets, change since the last reading and since the start of
# the range in words, a connecting line only where allowed (broken across long gaps), and a fitted value scale only
# when asked for (with its start said on the axis); otherwise the scale starts at zero, as in 0109.
CHART_RANGES = ("3m", "1y", "all")
CHART_SCALES = ("zero", "fitted")
# A month calendar of a table's dated or timed records by the household's own day (decision 0119). Each record has
# one of a few fixed looks (colour, symbol and pattern together); a linked record's open due date is shown only when
# the table says `due = true`, and an empty day is never called missed. Without `per` it is a calendar of the
# table's own records (decision 0122): each one's own open due date, and when each was done. `history = true` also
# shows each earlier date its `when` column was moved on from, read from the record's saved history (decision 0129).
CALENDAR_KEYS = ("when", "per", "show", "title", "entry", "state", "looks", "look", "due", "history")
CALENDAR_ENTRY_LOOKS = ("recorded", "done", "skipped")
CALENDAR_SHOW = ("one", "all")
# Bars over time (decision 0124): how often (`measure = "count"`) or how much of one number column in one unit
# (`"sum"`) per day, week or month, by the household's own day. A table may declare several, each with its own key.
# Without `per` one chart covers the whole list (decision 0128); `history = true` counts each day a record's
# own "last done" date says it was done, earlier ones from its saved history included (decision 0129).
BARS_KEYS = ("key", "title", "when", "per", "measure", "amount", "unit", "where", "group", "by", "entry", "verb",
             "subject", "caveat", "missing", "history")
# A confirmed purchase price on a Stock in (decision 0128): the price a person typed (`paid`), whether it is the
# total or the price for each one (`basis`, choices "total" and "each"), the line total worked out from them
# (`total`), its currency (`currency`), the bought amount a price for each is multiplied by (`amount`), and which
# records may carry a price at all (`only`, like reason = "bought", with `only_words` saying so).
PRICE_KEYS = ("paid", "basis", "total", "currency", "amount", "only", "only_words")
BARS_MEASURES = ("count", "sum")
BARS_BY = ("day", "week", "month")
# One timeline on a record's page (decision 0126): "What happened, newest first", every dated entry of every table
# that links to the record and declares `timeline`. Each kind has a fixed look (a symbol beside its words, never a
# colour alone); `summarise = "day"` makes one line a day, as a private table must, so it says only how many.
TIMELINE_KEYS = ("when", "per", "entry", "words", "look", "summarise", "change", "change_unit")
TIMELINE_LOOKS = ("recorded", "done", "measured", "visit")
TIMELINE_WORD = re.compile(r"\{([^{}]*)\}")
# A gentle check before a form saves, such as an odometer reading lower than the last one: Go back, or Save as
# entered. Never a block, and nothing is worked out from it (decision 0111).
CONFIRM_KEYS = ("key", "when", "column", "per", "order", "among", "message", "later")
CONFIRM_WHEN = ("lower", "different")
CHART_KINDS = ("dots",)
# Daily totals of one subject's timed entries by the household's own day, like a pet's feedings (decision 0110).
DAILY_KEYS = ("when", "per", "amount", "unit", "entry", "what", "verb", "add", "sheet", "caveat", "repeat", "group")
# `repeat` may also ask on the household's own form before saving (`form` is the sentence, `keep` the button that
# saves anyway), for a table helpers never write to, such as medicine doses (decision 0120).
REPEAT_KEYS_DAILY = ("minutes", "same", "form", "keep")
# Which linked records a link may point at (decision 0120): `where` fixes choices of the linked record, `same` says
# a link of the linked record must equal a link of this one, `shows` is its private column a person may Show.
LINK_RULE_KEYS = ("where", "same", "shows")
DAILY_WORDS = ("what", "verb", "add", "sheet", "caveat")
# A record that joins two records of one table, like two rooms with a door between them (decision 0103).
PAIR_KEYS = ("columns", "blank_when")
# A one-step button on a record's page, such as "Mark returned" (decision 0075).
ACTION_KEYS = ("key", "label", "show_when", "set", "done")
# An action that also adds a linked record through a small form, like Home care's "Mark done" (decision 0091).
FORM_ACTION_KEYS = ("title", "intro", "adds", "latest", "next_date", "help", "undo", "messages", "counts_as")
# What a saved form counts as on Things to do (decision 0107): work done, or a decision to skip this time.
COUNTS_AS = ("done", "skipped")
ADDS_KEYS = ("table", "link", "ask", "values", "add_button", "copy")
LATEST_KEYS = ("date", "into")
NEXT_DATE_KEYS = ("into", "question", "repeat")
# `from` steps the repeat from a date of this record (its planned date) instead of the day it was done, and
# `anchor` keeps the day of the month of another date, so the 31st comes back after February (decision 0107).
REPEAT_KEYS = ("count", "unit", "from", "anchor")
REPEAT_UNITS = ("days", "weeks", "months", "years")
MESSAGE_KEYS = ("stale", "same_day", "undo_refused")
DEFAULT_MESSAGES = {
    "stale": "This record changed while the form was open. Check it and try again. Nothing was saved.",
    "same_day": "This is already recorded for {date}. Use the ordinary add form if you need another entry.",
    "undo_refused": "This record has changed since then. Nothing was undone. Check it before changing it.",
}
ADJUST_KEYS = ("link", "quantity", "amount", "direction", "adds")
# Optional, for batches (DESIGN.md 5.7): the record a batch belongs to, how to pick or start one,
# and the two reasons a stocktake count records its difference with (decision 0070).
ADJUST_BATCH_KEYS = ("belongs_to", "new_batch", "oldest_first", "counts")
TOTAL_KEYS = ("link", "amount", "into", "earliest", "starts_from")
WATCH_KEYS = ("running_low", "expiring", "supply", "gaps")
GAP_KEYS = ("missing", "none", "where", "message")
COLUMN_KEYS = ("type", "required", "required_when", "default", "min", "max", "unit", "choices", "help", "sensitive",
               "to", "on_delete", "not_before", "travels", "travels_when", "with_place", "default_from",
               "link_rule")
LABEL_TABLE_KEYS = ("title", "columns", "form", "list", "empty", "home", "actions", "add_button", "under",
                    "takes_over")
# A table's records listed on the page of the record they link to, like a service's quotes (decision 0111).
UNDER_KEYS = ("link", "title", "intro", "columns", "order", "reveal")
LABEL_ACTION_KEYS = ("label", "done", "title", "intro", "undo")  # new words for an action's button, form, notice
HOME_PLACES = ("main", "more")  # where a table sits on the home page: shown large, or in the line of links
LABEL_COLUMN_KEYS = ("label", "help", "show_when", "suggest_from", "fills", "answers", "blank", "optional", "mismatch")
# The household words for a link into a module listed under optional_requires (decision 0115): the sentence
# beside a hidden picker, a link kept while that module is off (on the form, and short for lists and sheets),
# no link, and a saved link whose record is no longer there (short, and on the form with what to do).
OPTIONAL_WORDS = ("off_help", "kept_help", "kept", "none", "gone", "missing")


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
    with_place: str | None = None  # for link: a link column of the target that is shown after its name ("Water meter — Front yard › Meter box")
    on_delete: str = "restrict"
    required_when: dict = field(default_factory=dict)  # required only while another choice has a value
    not_before: str | None = None  # a date column of this table this date may not come before (decision 0075)
    # Decision 0100: "always", "never" (stays on the computer where it was typed) or "when" (travels only
    # while the one choice column in `travels_when` holds a listed choice, e.g. {"kind": ["allergy"]}).
    travels: str = "always"
    travels_when: dict = field(default_factory=dict)
    travels_reviewed: bool = True  # False for a private column that does not say; it is then kept local
    # For a link into a module listed under optional_requires (decision 0115): that module may be off or not
    # installed, so the link is hidden and kept as saved instead of being shown, changed or cleared.
    optional: bool = False
    default_from: str | None = None  # a household choice (HOUSEHOLD_CHOICES) that fills an empty form (0111)
    # Decision 0120: which linked records may be chosen, checked on every save, like a medicine dose's medication,
    # which must be a `kind = medication` detail of the same person: {"where": {...}, "same": {...}, "shows": ...}.
    link_rule: dict = field(default_factory=dict)


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
    actions: list = field(default_factory=list)  # checked one-step buttons, like "Mark returned" (decision 0075)
    # False: records are made only on this program's own screens, never suggested by a helper or imported
    # from a spreadsheet; helpers may still look, as their grant allows (decision 0104).
    suggestions: bool = True
    pair: dict = field(default_factory=dict)  # checked `pair`: joins two different records, each pair once (5.6)
    chart: dict = field(default_factory=dict)  # checked `chart`: one subject's dated readings drawn as dots (0109)
    daily: dict = field(default_factory=dict)  # checked `daily`: totals by the household's own day (0110)
    confirm: list = field(default_factory=list)  # checked gentle checks before a form saves (decision 0111)
    takes_over: dict = field(default_factory=dict)  # checked `takes_over`: one reminder per policy (0117)
    calendar: dict = field(default_factory=dict)  # checked `calendar`: a month grid by the household's day (0119)
    bars: list = field(default_factory=list)  # checked `bars`: how often or how much per day, week or month (0124)
    timeline: dict = field(default_factory=dict)  # checked `timeline`: its entries on a record's timeline (0126)
    price: dict = field(default_factory=dict)  # checked `price`: a confirmed purchase price on a Stock in (0128)
    # Decision 0120: every record is private history, such as medicine given. Never on Home, a sheet, a helper
    # or the spreadsheet export; made only on this program's own screens (suggestions = false is required).
    private: bool = False


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
    prompts: object = None  # checked prompts.toml, a prompts.PromptSet, or None (decision 0104)
    # Modules this one may link into but does not need: it loads and works while they are off or not
    # installed, and its links into them are optional (decision 0115).
    optional_requires: list[str] = field(default_factory=list)


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
    if isinstance(name, str) and NAME.match(name):
        if name in RESERVED_NAMES:
            problems.append(f"{where}: '{name}' is reserved for the program itself. Choose another name.")
        elif "__" in name or name.endswith("_"):
            problems.append(f"{where}: the name '{name}' may not contain two underscores in a row or end with an "
                            f"underscore, because that could be mistaken for another module's tables.")
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
    for key in ("requires", "optional_requires", "outbound_hosts"):
        if key in data and (not isinstance(data[key], list) or not all(isinstance(x, str) for x in data[key])):
            problems.append(f"{where}: '{key}' must be a list of names, like [\"people\"].")
    optional = data.get("optional_requires", [])
    if isinstance(optional, list) and all(isinstance(x, str) for x in optional):
        hard = data.get("requires", []) if isinstance(data.get("requires", []), list) else []
        for other in optional:
            if other == name:
                problems.append(f"{where}: optional_requires can't name this module itself.")
            elif other in hard:
                problems.append(f"{where}: '{other}' is under both requires and optional_requires. Keep it under "
                                f"requires if this module can't work without it, otherwise only under "
                                f"optional_requires.")
            elif not NAME.match(other):
                problems.append(f"{where}: '{other}' in optional_requires is not a module name.")
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


def _parse_travels(where: str, raw: dict, column: Column, problems: list[str]) -> None:
    """Read `travels` or `travels_when` (decision 0100). A private column that says neither stays on this
    computer and is listed as not yet reviewed; anything unclear is a problem, never a guess."""
    if "travels" in raw and "travels_when" in raw:
        problems.append(f"{where}: use either travels or travels_when, not both.")
        column.travels, column.travels_reviewed = "never", False
        return
    if "travels" in raw:
        if raw["travels"] not in TRAVELS:
            problems.append(f"{where}: travels must be \"always\" or \"never\" (never keeps the value on the "
                            f"computer where it was typed).")
            column.travels, column.travels_reviewed = "never", False
        else:
            column.travels = raw["travels"]
        return
    if "travels_when" in raw:
        rule = raw["travels_when"]
        values = next(iter(rule.values()), None) if isinstance(rule, dict) and len(rule) == 1 else None
        if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            problems.append(f"{where}: travels_when names one choice column and the choices that let the value "
                            f"travel, like {{ kind = [\"allergy\", \"medication\"] }}.")
            column.travels, column.travels_reviewed = "never", False
            return
        column.travels, column.travels_when = "when", {next(iter(rule)): list(values)}
        return
    if column.sensitive:
        column.travels, column.travels_reviewed = "never", False


def _check_travels_when(file: str, table: Table, problems: list[str]) -> None:
    """A travels_when rule must name another choice column of the same table that itself always travels,
    and only that column's own choices."""
    for column in table.columns.values():
        if column.travels != "when":
            continue
        (other, allowed), = column.travels_when.items()
        target = table.columns.get(other)
        keys = [c.key for c in target.choices] if target is not None else []
        if column.type == "links" or target is None or target is column or target.type != "choice" \
                or target.travels != "always" or not set(allowed) <= set(keys):
            problems.append(f"In {file}, table '{table.name}', column '{column.name}': travels_when must name "
                            f"another choice column of this table that always travels, and some of its choices.")
            column.travels, column.travels_when, column.travels_reviewed = "never", {}, False


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
                    required_when=raw.get("required_when") if isinstance(raw.get("required_when"), dict) else {},
                    not_before=raw.get("not_before"), with_place=raw.get("with_place"),
                    default_from=raw.get("default_from"))
    if "required_when" in raw and (not isinstance(raw["required_when"], dict) or len(raw["required_when"]) != 1):
        problems.append(f"{where}: required_when names one choice column and a value, like {{ category = \"water\" }}.")
    _parse_travels(where, raw, column, problems)
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
    if "default_from" in raw:
        wanted = HOUSEHOLD_CHOICES.get(raw["default_from"]) if isinstance(raw["default_from"], str) else None
        if kind != "choice" or wanted is None or not set(wanted) <= {c.key for c in column.choices} \
                or "default" in raw:
            problems.append(f"{where}: 'default_from' names a household choice ({', '.join(HOUSEHOLD_CHOICES)}) "
                            f"for a choice column that offers all of its choices, instead of 'default'.")
            column.default_from = None
    if kind in ("link", "links"):
        if not column.to:
            problems.append(f"{where}: a {kind} column needs 'to', naming the table it points at.")
        if column.on_delete not in ON_DELETE:
            problems.append(f"{where}: on_delete '{column.on_delete}' is not known.{_suggest(column.on_delete, ON_DELETE)}")
        if "with_place" in raw and (kind != "link" or not isinstance(raw["with_place"], str)):
            problems.append(f"{where}: 'with_place' names a link column of the linked table and only applies to a single link.")
    else:
        for key in ("to", "on_delete", "with_place"):
            if key in raw:
                problems.append(f"{where}: '{key}' only applies to link columns.")
    if "link_rule" in raw:
        rule = raw["link_rule"]
        parts = [rule.get(k, {}) for k in ("where", "same")] if isinstance(rule, dict) else []
        if kind != "link" or not isinstance(rule, dict) or set(rule) - set(LINK_RULE_KEYS) \
                or not all(isinstance(p, dict) and all(isinstance(v, str) and v for v in p.values()) for p in parts) \
                or not any(parts) or ("shows" in rule and not isinstance(rule["shows"], str)):
            problems.append(f"{where}: link_rule says which linked records may be chosen, like {{ where = {{ kind = "
                            f"\"medication\" }}, same = {{ person = \"recipient\" }} }}, and only applies to a "
                            f"single link.")
        else:
            column.link_rule = {"where": dict(rule.get("where", {})), "same": dict(rule.get("same", {})),
                                "shows": rule.get("shows")}
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
                                          ("date", "warn_days", "wording", "what", "only_positive", "where",
                                           "what_when")))
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
                if "what_when" in expiring:  # words for some rows, like "bill check" (decision 0117)
                    found = _check_what_when(f"{where}, expiring, what_when", expiring["what_when"], columns,
                                             problems)
                    if found:
                        watch["expiring"]["what_when"] = found

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


def _check_what_when(where: str, raw, columns: dict[str, Column], problems: list[str]) -> list[dict]:
    """`what_when`: other words for the rows matching each filter, the first match winning, like
    [{ where = { kind = "bill" }, what = "bill check" }] (decision 0117). Rows matching none keep `what`."""
    if not isinstance(raw, list) or not raw:
        problems.append(f"{where}: write it as a list like [{{ where = {{ kind = \"bill\" }}, what = \"bill check\" }}].")
        return []
    found = []
    for number, entry in enumerate(raw, start=1):
        here = f"{where}, entry {number}"
        if not isinstance(entry, dict):
            problems.append(f"{here}: write it like {{ where = {{ kind = \"bill\" }}, what = \"bill check\" }}.")
            continue
        problems.extend(_unknown_keys(here, entry, ("where", "what")))
        what = entry.get("what")
        if not isinstance(what, str) or not what.strip():
            problems.append(f"{here}: 'what' must be a few words, like \"bill check\".")
            continue
        if _check_where(f"{here}, where", entry.get("where"), columns, problems):
            found.append({"where": dict(entry["where"]), "what": what})
    return found


def _check_takes_over(file: str, table: Table, raw, requires: list[str], optional: list[str],
                      problems: list[str]) -> dict:
    """Check `takes_over` (decision 0117) as far as this module alone can; the other module's side is checked
    once it is loaded (`_takes_over_problems`)."""
    where = f"In {file}, table '{table.name}', takes_over"
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it like {{ from = \"vehicles.insurance\", where = {{ ... }}, "
                        f"copy = {{ ... }} }}.")
        return {}
    problems.extend(_unknown_keys(where, raw, TAKES_OVER_KEYS))
    source = raw.get("from")
    other, _, other_table = source.partition(".") if isinstance(source, str) else ("", "", "")
    ok = True
    if not other or not NAME.match(other_table) or other not in (*requires, *optional):
        problems.append(f"{where}: 'from' names a table of another module listed under requires or "
                        f"optional_requires, like \"vehicles.insurance\".")
        ok = False
    ok = _check_where(f"{where}, where", raw.get("where"), table.columns, problems) and ok
    rule = table.watch.get("expiring") if isinstance(table.watch, dict) else None
    if not rule or rule.get("wording") != "due":
        problems.append(f"{where}: this table needs a watch.expiring with wording = \"due\": the reminder it "
                        f"takes over.")
        ok = False
    copy = raw.get("copy")
    if not isinstance(copy, dict) or not copy or not all(isinstance(v, str) for v in copy.values()):
        problems.append(f"{where}: 'copy' names this table's columns and the other table's, like "
                        f"{{ name = \"name\", next_due = \"renew_by\" }}.")
        return {}
    for name in copy:
        column = table.columns.get(name)
        if column is None:
            problems.append(f"{where}, copy: there is no column '{name}'.{_suggest(name, list(table.columns))}")
            ok = False
        elif column.sensitive or column.type in ("links", "file"):
            problems.append(f"{where}, copy: '{name}' can't be copied into: only ordinary, non-private columns "
                            f"are, so nothing private moves between lists.")
            ok = False
    if rule and rule.get("date") not in copy:
        problems.append(f"{where}, copy: it must copy the reminder's date, '{rule.get('date')}'.")
        ok = False
    if isinstance(raw.get("where"), dict) and set(copy) & set(raw["where"]):
        problems.append(f"{where}: a column can't be both in 'where' and in 'copy'.")
        ok = False
    if not ok:
        return {}
    return {"from": source, "where": dict(raw["where"]), "copy": dict(copy)}


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


def _check_pair(file: str, table: Table, raw, problems: list[str]) -> dict:
    """Check `pair`: two link columns of this table that point at the same table, such as two places joined
    by a door. Saving then refuses a record that joins a place to itself, or a pair already joined either way
    round. `blank_when` names the one choice that lets the second be left blank, like a door straight outside."""
    where = f"In {file}, table '{table.name}', pair"
    example = 'pair = { columns = ["place", "connects_to"] }'
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it like {example}.")
        return {}
    problems.extend(_unknown_keys(where, raw, PAIR_KEYS))
    names = raw.get("columns")
    ok_names = isinstance(names, list) and len(names) == 2 and all(isinstance(n, str) for n in names)
    columns = [table.columns.get(n) for n in names] if ok_names else []
    if len(columns) != 2 or None in columns or names[0] == names[1] \
            or any(c.type != "link" for c in columns) or columns[0].to != columns[1].to:
        problems.append(f"{where}: columns names two different link columns of this table that point at the same "
                        f"table, like {example}.")
        return {}
    if not columns[0].required:
        problems.append(f"{where}: the first column, '{names[0]}', must be required.")
        return {}
    rule = {"columns": list(names), "blank_when": {}}
    if "blank_when" in raw:
        blank = raw["blank_when"]
        key, value = next(iter(blank.items())) if isinstance(blank, dict) and len(blank) == 1 else (None, None)
        choice = table.columns.get(key) if isinstance(key, str) else None
        if choice is None or choice.type != "choice" or value not in [c.key for c in choice.choices]:
            problems.append(f"{where}: blank_when names one choice column of this table and one of its choices, "
                            f"like blank_when = {{ kind = \"outside_door\" }}.")
            return {}
        rule["blank_when"] = {key: value}
    return rule


def _check_chart(file: str, table: Table, raw, problems: list[str]) -> dict:
    """Check `chart`: one subject's dated readings drawn as dots, like one pet's weigh-ins (decision 0109).
    `what` and `entry` are the words for one reading and for one record, singular then plural."""
    where = f"In {file}, table '{table.name}', chart"
    example = ('chart = { kind = "dots", x = "day", y = "weight", per = "pet", what = ["weight", "weights"], '
               'entry = ["weigh-in", "weigh-ins"], subject = "pet" }')
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it like {example}.")
        return {}
    problems.extend(_unknown_keys(where, raw, CHART_KEYS))
    before = len(problems)
    if raw.get("kind") not in CHART_KINDS:
        problems.append(f"{where}: 'kind' must be \"dots\", not {raw.get('kind')!r}.")
    x, y, per = (table.columns.get(raw.get(k)) if isinstance(raw.get(k), str) else None for k in ("x", "y", "per"))
    if x is None or x.type not in ("date", "datetime") or not x.required:
        problems.append(f"{where}: 'x' must name a required date or date-and-time column of this table.")
    if y is None or y.type not in ("integer", "decimal", "measure") or not y.required or y.sensitive:
        problems.append(f"{where}: 'y' must name a required number column of this table that is not private.")
    if per is None or per.type != "link" or not per.required:
        problems.append(f"{where}: 'per' must name a required link column, so each chart shows one subject.")
    for key in ("what", "entry"):
        words = raw.get(key)
        if not (isinstance(words, list) and len(words) == 2 and all(isinstance(w, str) and w.strip() for w in words)):
            problems.append(f"{where}: '{key}' must be two words, singular then plural, like {example}.")
    if not (isinstance(raw.get("subject"), str) and raw["subject"].strip()):
        problems.append(f"{where}: 'subject' must be the word for one subject, like \"pet\".")
    unit = table.columns.get(raw["unit"]) if isinstance(raw.get("unit"), str) else None
    if "unit" in raw and (unit is None or unit.type != "choice" or not unit.required or y is None or y.unit):
        problems.append(f"{where}: 'unit' names a required choice column holding each reading's unit, for a "
                        f"number column with no 'unit' of its own.")
    for key in ("latest", "caveat"):
        if key in raw and not (isinstance(raw[key], str) and raw[key].strip()):
            problems.append(f"{where}: '{key}' must be a few words, like \"Last recorded\".")
    ranges = raw.get("ranges", [])
    if not (isinstance(ranges, list) and ranges and all(isinstance(r, str) and r in CHART_RANGES for r in ranges)
            and len(set(ranges)) == len(ranges)) and "ranges" in raw:
        problems.append(f"{where}: 'ranges' must list some of \"3m\", \"1y\" and \"all\", each once, like "
                        f"ranges = [\"3m\", \"1y\", \"all\"].")
        ranges = []
    if "change" in raw and not isinstance(raw["change"], bool):
        problems.append(f"{where}: 'change' must be true or false.")
    line, gap = raw.get("line", False), None
    if isinstance(line, dict):
        gap = line.get("gap_days")
        if set(line) - {"gap_days"} or isinstance(gap, bool) or not isinstance(gap, int) or not 1 <= gap <= 3650:
            problems.append(f"{where}: 'line' must be true, false or {{ gap_days = 365 }}: a whole number of days, "
                            f"from 1 to 3650, after which the line is broken.")
    elif not isinstance(line, bool):
        problems.append(f"{where}: 'line' must be true, false or {{ gap_days = 365 }}.")
    scale = raw.get("scale", "zero")
    if scale not in CHART_SCALES:
        problems.append(f"{where}: 'scale' must be \"zero\" (the scale starts at 0) or \"fitted\" (it starts near "
                        f"the lowest reading and says so on the axis), not {scale!r}.")
    if len(problems) > before:
        return {}
    return {"kind": raw["kind"], "x": raw["x"], "y": raw["y"], "per": raw["per"], "what": list(raw["what"]),
            "entry": list(raw["entry"]), "subject": raw["subject"].strip(), "unit": raw.get("unit"),
            "latest": raw.get("latest"), "caveat": raw.get("caveat"), "ranges": list(ranges),
            "change": bool(raw.get("change", False)), "line": bool(line), "gap_days": gap, "scale": scale}


def _check_confirm(file: str, table: Table, raw, problems: list[str]) -> list[dict]:
    """Check `confirm`: gentle checks before a form saves, like an odometer reading lower than the last one for
    the same vehicle (decision 0111). Each compares one column with the nearest record before it in `order`."""
    where = f"In {file}, table '{table.name}', confirm"
    example = ('[[tables.readings.confirm]] with key = "lower", when = "lower", column = "distance", '
               'per = "vehicle", order = "read_at", message = "This is lower than the last reading."')
    if not isinstance(raw, list) or not raw:
        problems.append(f"{where}: write each check as {example}.")
        return []
    checks, keys = [], set()
    for rule in raw:
        if not isinstance(rule, dict):
            problems.append(f"{where}: write each check as {example}.")
            continue
        problems.extend(_unknown_keys(where, rule, CONFIRM_KEYS))
        before = len(problems)
        key, when = rule.get("key"), rule.get("when")
        if not isinstance(key, str) or not CHOICE_KEY.match(key) or key in keys:
            problems.append(f"{where}: each check needs its own 'key', lower-case letters and underscores.")
        if when not in CONFIRM_WHEN:
            problems.append(f"{where}: 'when' must be \"lower\" or \"different\", not {when!r}.")
        column, per, order = (table.columns.get(rule.get(k)) if isinstance(rule.get(k), str) else None
                              for k in ("column", "per", "order"))
        if column is None or column.sensitive or (when == "lower" and column.type not in NUMERIC_TYPES):
            problems.append(f"{where}: 'column' must name a column of this table that is not private "
                            f"(a number column for \"lower\").")
        if per is None or per.type != "link" or not per.required:
            problems.append(f"{where}: 'per' must name a required link column, so records are compared for one "
                            f"subject only.")
        if order is None or order.type not in ("date", "datetime") or not order.required:
            problems.append(f"{where}: 'order' must name a required date or date-and-time column.")
        among = rule.get("among")
        if among is not None and (not isinstance(among, str) or among not in table.columns
                                  or among == rule.get("column") or table.columns[among].sensitive):
            problems.append(f"{where}: 'among' names another column of this table that is not private; only "
                            f"records with the same value there are compared.")
        for words in ("message",) + (("later",) if when == "lower" else ()):
            if not (isinstance(rule.get(words), str) and rule[words].strip()):
                problems.append(f"{where}: '{words}' must be the sentence shown before saving.")
        if when != "lower" and "later" in rule:
            problems.append(f"{where}: 'later' only applies to a \"lower\" check.")
        if len(problems) > before:
            continue
        keys.add(key)
        checks.append({k: rule.get(k) for k in CONFIRM_KEYS})
    return checks


def _check_daily(file: str, table: Table, raw, problems: list[str]) -> dict:
    """Check `daily`: one subject's timed entries added up by the household's own day, like a pet's feedings
    (decision 0110). `amount` and `unit` are optional together: totals only ever add matching units."""
    where = f"In {file}, table '{table.name}', daily"
    example = ('[tables.servings.daily] with when = "given_at", per = "pet", amount = "amount", unit = "unit", '
               'entry = ["feeding", "feedings"] and the words what, verb, add, sheet and caveat')
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it as {example}.")
        return {}
    problems.extend(_unknown_keys(where, raw, DAILY_KEYS))
    before = len(problems)
    named = {k: table.columns.get(raw.get(k)) if isinstance(raw.get(k), str) else None
             for k in ("when", "per", "amount", "unit")}
    if named["when"] is None or named["when"].type != "datetime" or not named["when"].required:
        problems.append(f"{where}: 'when' must name a required date-and-time column of this table.")
    if named["per"] is None or named["per"].type != "link" or not named["per"].required:
        problems.append(f"{where}: 'per' must name a required link column, so each total belongs to one subject.")
    amount, unit = named["amount"], named["unit"]
    private = table.private  # a private table's amounts are shown only after Show (decision 0120)
    if amount is None or amount.type not in ("integer", "decimal", "measure") or amount.required or \
            (amount.sensitive and not private):
        problems.append(f"{where}: 'amount' must name an optional number column that is not private.")
    if unit is None or unit.type not in ("choice", "text") or unit.required or (unit.sensitive and not private):
        problems.append(f"{where}: 'unit' must name an optional choice or text column that is not private.")
    group = raw.get("group")
    if group is not None and (not isinstance(group, str) or group not in table.columns
                              or table.columns[group].type != "link" or not table.columns[group].required
                              or group == raw.get("per")):
        problems.append(f"{where}: 'group' must name another required link column, whose records each get their "
                        f"own totals, like group = \"medication\".")
    words = raw.get("entry")
    if not (isinstance(words, list) and len(words) == 2 and all(isinstance(w, str) and w.strip() for w in words)):
        problems.append(f"{where}: 'entry' must be two words, singular then plural, like [\"feeding\", \"feedings\"].")
    for key in DAILY_WORDS:
        if not (isinstance(raw.get(key), str) and raw[key].strip()):
            problems.append(f"{where}: '{key}' must be the words to show, like {example}.")
    repeat = raw.get("repeat", {})
    if not isinstance(repeat, dict) or set(repeat) - set(REPEAT_KEYS_DAILY):
        problems.append(f"{where}: 'repeat' must be like {{ minutes = 30, same = [\"food\", \"amount\"] }}.")
        repeat = {}
    for key in ("form", "keep"):
        if key in repeat and not (isinstance(repeat[key], str) and repeat[key].strip()):
            problems.append(f"{where}: repeat '{key}' must be the words to show.")
    if ("keep" in repeat) != ("form" in repeat):
        problems.append(f"{where}: repeat 'form' (the sentence asked before saving) and 'keep' (the button that "
                        f"saves anyway) go together.")
    minutes = repeat.get("minutes", 0)
    if repeat and (isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 240):
        problems.append(f"{where}: repeat 'minutes' must be a whole number from 1 to 240.")
    same = repeat.get("same", [])
    if not isinstance(same, list) or any(not isinstance(c, str) or c not in table.columns
                                         or table.columns[c].sensitive for c in same):
        problems.append(f"{where}: repeat 'same' must list columns of this table that are not private.")
    if len(problems) > before:
        return {}
    rule = {k: raw[k] for k in ("when", "per", "amount", "unit")}
    rule.update({k: raw[k].strip() for k in DAILY_WORDS})
    rule["entry"] = [w.strip() for w in raw["entry"]]
    rule["repeat"] = {"minutes": minutes, "same": list(same)} if repeat else {}
    if repeat and "form" in repeat:
        rule["repeat"].update(form=repeat["form"].strip(), keep=repeat["keep"].strip())
    rule["group"] = group
    return rule


def _check_calendar(file: str, module: str, table: Table, tables: dict[str, Table], raw,
                    problems: list[str]) -> dict:
    """Check `calendar`: a month grid of this table's dated or timed records by the household's own day, like a
    pet's feedings or each time a routine was done or skipped (decision 0119). Looks are a fixed set, so every state
    has a colour, a symbol and a pattern; `due = true` also shows the linked record's own open due date."""
    where = f"In {file}, table '{table.name}', calendar"
    example = ('[tables.times.calendar] with when = "done_on", per = "routine", show = "all", title = "Routines '
               'calendar", entry = ["time", "times"]')
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it as {example}.")
        return {}
    problems.extend(_unknown_keys(where, raw, CALENDAR_KEYS))
    if "per" not in raw:
        return _check_own_calendar(where, table, raw, problems)
    before = len(problems)
    if "history" in raw:
        problems.append(f"{where}: 'history' is only for a calendar of a table's own records (no 'per') whose 'when' "
                        f"date says when each was last done. Here every entry is already its own record.")
    when, per =(table.columns.get(raw.get(k)) if isinstance(raw.get(k), str) else None for k in ("when", "per"))
    if when is None or when.type not in ("date", "datetime") or not when.required:
        problems.append(f"{where}: 'when' must name a required date or date-and-time column of this table.")
    if per is None or per.type != "link" or not per.required:
        problems.append(f"{where}: 'per' must name a required link column, so each mark belongs to one record.")
    if raw.get("show") not in CALENDAR_SHOW:
        problems.append(f"{where}: 'show' must be \"one\" (one record's month at a time, like one pet) or \"all\" "
                        f"(every record together, like all routines), not {raw.get('show')!r}.")
    if not (isinstance(raw.get("title"), str) and raw["title"].strip()):
        problems.append(f"{where}: 'title' must be the calendar's name, like \"Feeding calendar\".")
    words = raw.get("entry")
    if not (isinstance(words, list) and len(words) == 2 and all(isinstance(w, str) and w.strip() for w in words)):
        problems.append(f"{where}: 'entry' must be two words, singular then plural, like [\"feeding\", \"feedings\"].")
    looks = raw.get("looks")
    if "state" in raw:
        state = table.columns.get(raw["state"]) if isinstance(raw["state"], str) else None
        if state is None or state.type != "choice" or not state.required or state.sensitive:
            problems.append(f"{where}: 'state' must name a required choice column of this table that is not private.")
        elif not isinstance(looks, dict) or set(looks) != {c.key for c in state.choices} \
                or any(v not in CALENDAR_ENTRY_LOOKS for v in looks.values()):
            keys = ", ".join(c.key for c in state.choices)
            problems.append(f"{where}: 'looks' must give each choice of '{raw['state']}' ({keys}) one of the looks "
                            f"\"recorded\", \"done\" or \"skipped\", like looks = {{ done = \"done\", skipped = "
                            f"\"skipped\" }}.")
        if "look" in raw:
            problems.append(f"{where}: use 'looks' for each choice of 'state', not 'look'.")
    elif looks is not None:
        problems.append(f"{where}: 'looks' needs 'state', the choice column whose choices it gives a look.")
    if "look" in raw and raw["look"] not in CALENDAR_ENTRY_LOOKS:
        problems.append(f"{where}: 'look' must be \"recorded\", \"done\" or \"skipped\", not {raw['look']!r}.")
    due = raw.get("due", False)
    if not isinstance(due, bool):
        problems.append(f"{where}: 'due' must be true or false.")
    elif due and per is not None and per.type == "link" and per.to:
        other, _, name = per.to.partition(".") if "." in per.to else (module, ".", per.to)
        target = tables.get(name) if other == module else None
        expiring = (target.watch or {}).get("expiring") if target is not None else None
        if not expiring or expiring.get("wording") != "due":
            problems.append(f"{where}: 'due = true' shows the open due date of the record '{raw.get('per')}' points "
                            f"at, so that table must be in this module and have a reminder with wording = \"due\".")
    if table.private:  # decision 0121: a private calendar shows one plain mark and a count, never a state or due
        for key in ("state", "due"):
            if key in raw and raw[key] not in (False, None):
                problems.append(f"{where}: a private table's calendar can't use '{key}': it shows only a mark and "
                                f"how many each day, never what kind or whether something is due.")
        if raw.get("look", "recorded") != "recorded":
            problems.append(f"{where}: a private table's calendar uses the look \"recorded\" only.")
    if len(problems) > before:
        return {}
    return {"when": raw["when"], "per": raw["per"], "show": raw["show"], "title": raw["title"].strip(),
            "entry": [w.strip() for w in raw["entry"]], "state": raw.get("state"), "looks": dict(looks or {}),
            "look": raw.get("look", "recorded"), "due": due}


def _check_price(file: str, table: Table, raw, problems: list[str]) -> dict:
    """Check `price`: a confirmed purchase price on a record such as a Stock in (decision 0128). The price, its
    basis, the line total and the currency are private columns that never travel, so a helper, a spreadsheet
    import, a list, a sheet or the export never carries them and only a person types them."""
    where = f"In {file}, table '{table.name}', price"
    example = ('[tables.movements.price] with paid = "price", basis = "price_basis", total = "paid_total", '
               'currency = "currency", amount = "amount", only = { reason = "bought" }, '
               'only_words = "can only be saved on a Stock in that was bought."')
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it as {example}.")
        return {}
    problems.extend(_unknown_keys(where, raw, PRICE_KEYS))
    before = len(problems)
    columns = {k: table.columns.get(raw.get(k)) if isinstance(raw.get(k), str) else None
               for k in ("paid", "basis", "total", "currency", "amount")}
    for key, kind, words in (("paid", "money", "a money column: the price as the person typed it"),
                             ("total", "money", "a money column for the line total worked out from it"),
                             ("basis", "choice", "a choice column with the choices \"total\" and \"each\""),
                             ("currency", "text", "a text column for the currency code")):
        column = columns[key]
        if column is None or column.type != kind or column.required or not column.sensitive \
                or column.travels != "never" or not column.travels_reviewed:
            problems.append(f"{where}: '{key}' must name {words}, not required, private (sensitive = true) and "
                            f"kept on this computer (travels = \"never\").")
    basis = columns["basis"]
    if basis is not None and basis.type == "choice" and sorted(c.key for c in basis.choices) != ["each", "total"]:
        problems.append(f"{where}: '{raw.get('basis')}' must offer exactly the choices \"total\" and \"each\".")
    if len({raw.get(k) for k in ("paid", "basis", "total", "currency")}) != 4:
        problems.append(f"{where}: 'paid', 'basis', 'total' and 'currency' must be four different columns.")
    amount = columns["amount"]
    if amount is None or amount.type not in ("integer", "decimal", "measure") or amount.sensitive:
        problems.append(f"{where}: 'amount' must name the number column a price for each one is multiplied by.")
    only = raw.get("only", {})
    if not isinstance(only, dict) or not only or any(
            not isinstance(c, str) or c not in table.columns or table.columns[c].type != "choice"
            or v not in [x.key for x in table.columns[c].choices] for c, v in only.items()):
        problems.append(f"{where}: 'only' names the choice a record must have to carry a price, like only = "
                        f"{{ reason = \"bought\" }}.")
    if not (isinstance(raw.get("only_words"), str) and raw["only_words"].strip()):
        problems.append(f"{where}: 'only_words' must say where a price may be saved, like \"can only be saved on "
                        f"a Stock in that was bought.\"")
    if len(problems) > before:
        return {}
    return {k: raw[k] for k in ("paid", "basis", "total", "currency", "amount")} | {
        "only": dict(only), "only_words": raw["only_words"].strip()}


def _check_bars(file: str, table: Table, tables: dict[str, Table], raw, problems: list[str]) -> list[dict]:
    """Check `bars`: bars over time of one subject's records, or of the whole list when there is no `per`, counted
    (how often) or one number column added up in one unit at a time (how much), per day, week or month by the
    household's own day (decisions 0124 and 0128). A private table may only count, never add amounts or filter by
    a choice, and names its groups only after Show; a private amount is added up only after a pressed Show."""
    where = f"In {file}, table '{table.name}', bars"
    example = ('[[tables.servings.bars]] with key = "food", title = "Food put out", when = "given_at", per = "pet", '
               'measure = "sum", amount = "amount", unit = "unit", verb = "put out", by = ["day", "week", "month"], '
               'entry = ["feeding", "feedings"], subject = "pet"')
    if not isinstance(raw, list) or not raw:
        problems.append(f"{where}: write each chart as {example}.")
        return []
    found, keys = [], set()
    for rule in raw:
        if not isinstance(rule, dict):
            problems.append(f"{where}: write each chart as {example}.")
            continue
        problems.extend(_unknown_keys(where, rule, BARS_KEYS))
        before = len(problems)
        key = rule.get("key")
        if not isinstance(key, str) or not CHOICE_KEY.match(key) or key in keys:
            problems.append(f"{where}: each chart needs its own 'key', lower-case letters and underscores.")
        if not (isinstance(rule.get("title"), str) and rule["title"].strip()):
            problems.append(f"{where}: 'title' must be what the bars show, like \"Food put out\".")
        when, per = (table.columns.get(rule.get(k)) if isinstance(rule.get(k), str) else None for k in ("when", "per"))
        history = rule.get("history", False)
        if not isinstance(history, bool):
            problems.append(f"{where}: 'history' must be true or false.")
        elif history:  # decision 0129: each day a "last done" date says it was done, earlier ones from history
            if when is None or when.type != "date" or when.sensitive:
                problems.append(f"{where}: with history = true, 'when' must name a date column of this table that "
                                f"says when each was last done, like \"last_done\", and is not private.")
            if rule.get("measure") != "count" or "where" in rule or "group" in rule or table.private:
                problems.append(f"{where}: with history = true the bars count done days only: measure = \"count\", "
                                f"no 'where' or 'group', and not on a private table.")
        elif when is None or when.type not in ("date", "datetime") or not when.required:
            problems.append(f"{where}: 'when' must name a required date or date-and-time column of this table.")
        whole = "per" not in rule  # one chart of the whole list, like a household's spending (decision 0128)
        if whole and table.private:
            problems.append(f"{where}: a private table's bars need 'per', so each chart shows one person.")
        elif not whole and (per is None or per.type != "link" or not per.required):
            problems.append(f"{where}: 'per' must name a required link column, so each chart shows one subject, "
                            f"or be left out for one chart of the whole list.")
        measure = rule.get("measure")
        if measure not in BARS_MEASURES:
            problems.append(f"{where}: 'measure' must be \"count\" (how many entries) or \"sum\" (one number column "
                            f"added up), not {measure!r}.")
        amount = table.columns.get(rule["amount"]) if isinstance(rule.get("amount"), str) else None
        unit = table.columns.get(rule["unit"]) if isinstance(rule.get("unit"), str) else None
        fixed = None
        if measure == "sum":
            if table.private:
                problems.append(f"{where}: a private table's bars can only count entries (measure = \"count\"): "
                                f"its amounts stay behind Show.")
            if amount is None or amount.type not in ("integer", "decimal", "measure", "money"):
                problems.append(f"{where}: 'amount' must name a number or money column of this table.")
            hidden = amount is not None and amount.sensitive  # added up only after a pressed Show (0128)
            if "unit" in rule:
                if unit is None or unit.type not in ("choice", "text") or (unit.sensitive and not hidden):
                    problems.append(f"{where}: 'unit' must name a choice or text column holding each entry's unit, "
                                    f"that is not private unless the amount is.")
            elif amount is not None and amount.unit:
                fixed = amount.unit
            else:
                problems.append(f"{where}: a sum needs a unit: name a 'unit' column, or give '{rule.get('amount')}' "
                                f"its own unit, so different units are never added together.")
            if not (isinstance(rule.get("verb"), str) and rule["verb"].strip()):
                problems.append(f"{where}: 'verb' must be the words after an amount, like \"put out\".")
        else:
            for name in ("amount", "unit"):
                if name in rule:
                    problems.append(f"{where}: '{name}' only applies to measure = \"sum\".")
        choices = rule.get("where", {})
        if not isinstance(choices, dict) or any(
                not isinstance(c, str) or c not in table.columns or table.columns[c].type != "choice"
                or table.columns[c].sensitive or v not in [x.key for x in table.columns[c].choices]
                for c, v in choices.items()):
            problems.append(f"{where}: 'where' names choice columns of this table that are not private and one "
                            f"choice each, like where = {{ outcome = \"done\" }}.")
            choices = {}
        elif choices and table.private:
            problems.append(f"{where}: a private table's bars can't use 'where': they count every entry, so no "
                            f"kind of entry can be told from the bars.")
        group, through = rule.get("group"), None
        first, _, second = group.partition(".") if isinstance(group, str) else ("", "", "")
        if second:  # a choice of the linked record, like item.category: each choice gets its own bars (0128)
            link = table.columns.get(first)
            hop = tables.get(link.to) if link is not None and link.type == "link" and link.to else None
            choice = hop.columns.get(second) if hop is not None else None
            if link is None or not link.required or choice is None or choice.type != "choice" or choice.sensitive \
                    or table.private:
                problems.append(f"{where}: in group = \"{group}\", '{first}' must be a required link to a table "
                                f"of this module and '{second}' a choice column of that table that is not private.")
            else:
                through = {"link": first, "table": link.to, "column": second}
        elif group is not None and (not isinstance(group, str) or group not in table.columns
                                    or table.columns[group].type != "link" or not table.columns[group].required
                                    or group == rule.get("per")):
            problems.append(f"{where}: 'group' must name another required link column, whose records each get "
                            f"their own bars, like group = \"medication\", or a choice of the linked record, "
                            f"like group = \"item.category\".")
        by = rule.get("by")
        if not (isinstance(by, list) and by and all(isinstance(b, str) and b in BARS_BY for b in by)
                and len(set(by)) == len(by)):
            problems.append(f"{where}: 'by' must list some of \"day\", \"week\" and \"month\", each once, the one "
                            f"shown first first, like by = [\"week\", \"month\"].")
        words = rule.get("entry")
        if not (isinstance(words, list) and len(words) == 2 and all(isinstance(w, str) and w.strip() for w in words)):
            problems.append(f"{where}: 'entry' must be two words, singular then plural, like [\"feeding\", "
                            f"\"feedings\"].")
        if not whole and not (isinstance(rule.get("subject"), str) and rule["subject"].strip()):
            problems.append(f"{where}: 'subject' must be the word for one subject, like \"pet\".")
        elif whole and "subject" in rule:
            problems.append(f"{where}: 'subject' names the record each chart is for, so it needs 'per'.")
        if "missing" in rule and not (isinstance(rule["missing"], str) and rule["missing"].strip()):
            problems.append(f"{where}: 'missing' must be the word for an entry's amount, like \"price\".")
        if "caveat" in rule and not (isinstance(rule["caveat"], str) and rule["caveat"].strip()):
            problems.append(f"{where}: 'caveat' must be a sentence, like \"Food put out, not necessarily eaten.\"")
        if len(problems) > before:
            continue
        keys.add(key)
        found.append({"key": key, "title": rule["title"].strip(), "when": rule["when"], "per": rule.get("per"),
                      "history": history, "measure": measure, "amount": rule.get("amount"),
                      "unit": rule.get("unit"),
                      "fixed_unit": fixed, "where": dict(choices), "group": group, "by": list(by),
                      "entry": [w.strip() for w in rule["entry"]], "verb": (rule.get("verb") or "").strip(),
                      "subject": (rule.get("subject") or "").strip(),
                      "caveat": (rule.get("caveat") or "").strip() or None,
                      "money": measure == "sum" and amount.type == "money",
                      "hidden": measure == "sum" and amount.sensitive, "through": through,
                      "missing": (rule.get("missing") or "amount").strip()})
    return found


def _check_timeline(file: str, module: str, table: Table, tables: dict[str, Table], raw,
                    problems: list[str]) -> dict:
    """Check `timeline`: this table's dated entries on the timeline of the record `per` points at, like a pet's
    weigh-ins or a person's doses (decision 0126). `per` may go through one link of this module ("treatment.pet");
    `words` names ordinary columns only; `change` says the change since the entry before in one fixed unit; a
    private table must summarise by day and never says a change."""
    where = f"In {file}, table '{table.name}', timeline"
    example = ('[tables.weigh_ins.timeline] with when = "day", per = "pet", entry = ["weigh-in", "weigh-ins"], '
               'words = "{weight}", look = "measured"')
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it as {example}.")
        return {}
    problems.extend(_unknown_keys(where, raw, TIMELINE_KEYS))
    before = len(problems)
    when = table.columns.get(raw.get("when")) if isinstance(raw.get("when"), str) else None
    if when is None or when.type not in ("date", "datetime") or not when.required:
        problems.append(f"{where}: 'when' must name a required date or date-and-time column of this table.")
    per = raw.get("per")
    first, _, second = per.partition(".") if isinstance(per, str) else ("", "", "")
    link = table.columns.get(first)
    if link is None or link.type != "link" or not link.required:
        problems.append(f"{where}: 'per' must name a required link column, so each entry belongs to one record, "
                        f"like per = \"pet\", or go through one link of this module, like per = \"treatment.pet\".")
    elif second:
        other, _, name = link.to.partition(".") if "." in link.to else (module, ".", link.to)
        hop = tables.get(name) if other == module else None
        column = hop.columns.get(second) if hop is not None else None
        # A link into another module is checked once that module is loaded (_cross_module_timeline_problems).
        if other != module and "." not in second and second:
            pass
        elif column is None or column.type != "link" or not column.required or "." in second:
            problems.append(f"{where}: in per = \"{per}\", '{first}' must point at a table of this module or of a "
                            f"module this one requires, and '{second}' must be a required link column of that "
                            f"table.")
    words = raw.get("entry")
    if not (isinstance(words, list) and len(words) == 2 and all(isinstance(w, str) and w.strip() for w in words)):
        problems.append(f"{where}: 'entry' must be two words, singular then plural, like [\"weigh-in\", "
                        f"\"weigh-ins\"].")
    text = raw.get("words", "")
    if not isinstance(text, str):
        problems.append(f"{where}: 'words' must be a short text with column names in braces, like \"{{weight}}\".")
        text = ""
    for name in TIMELINE_WORD.findall(text):
        column = table.columns.get(name)
        if column is None or column.sensitive:
            problems.append(f"{where}: 'words' can only name columns of this table that are not private; "
                            f"'{{{name}}}' is not one.")
    if "{" in TIMELINE_WORD.sub("", text) or "}" in TIMELINE_WORD.sub("", text):
        problems.append(f"{where}: 'words' has a brace without its pair; write a column as {{name}}.")
    look = raw.get("look", "recorded")
    if look not in TIMELINE_LOOKS:
        problems.append(f"{where}: 'look' must be one of {', '.join(TIMELINE_LOOKS)}, not {look!r}. Each has its "
                        f"own symbol, so a kind is never told apart by colour alone.")
    summarise = raw.get("summarise")
    if summarise not in (None, "day"):
        problems.append(f"{where}: 'summarise' can only be \"day\" (one line a day, such as \"3 feedings recorded "
                        f"on Tue 24 Nov\"), not {summarise!r}.")
    change = raw.get("change")
    if change is not None:
        column = table.columns.get(change) if isinstance(change, str) else None
        if column is None or column.type not in ("integer", "decimal", "measure") or column.sensitive \
                or not (column.unit or raw.get("change_unit")):
            problems.append(f"{where}: 'change' must name a number column of this table with its own unit (or with "
                            f"change_unit naming the choice column that says the unit) and not private, like "
                            f"change = \"weight\", so a change is never across units.")
        if summarise:
            problems.append(f"{where}: 'change' compares one entry with the one before, so it can't be used with "
                            f"summarise.")
    change_unit = raw.get("change_unit")
    if change_unit is not None:
        unit_column = table.columns.get(change_unit) if isinstance(change_unit, str) else None
        if change is None or unit_column is None or unit_column.type != "choice" or unit_column.sensitive \
                or not unit_column.required:
            problems.append(f"{where}: 'change_unit' goes with 'change' and must name a required choice column of "
                            f"this table that is not private, like change_unit = \"unit\". A change is then only "
                            f"said between two entries in the same unit, never converted.")
    if table.private:  # decisions 0121 and 0123: how many each day until Show, never an amount or a change
        if summarise != "day":
            problems.append(f"{where}: a private table's timeline must say summarise = \"day\", so before Show it "
                            f"says only how many each day.")
        if change is not None:
            problems.append(f"{where}: a private table's timeline can't use 'change': it would show a private "
                            f"value.")
    if len(problems) > before:
        return {}
    return {"when": raw["when"], "per": per, "link": first, "through": second or None,
            "entry": [w.strip() for w in raw["entry"]], "words": text.strip(), "look": look,
            "summarise": summarise, "change": change, "change_unit": change_unit}


def _check_own_calendar(where: str, table: Table, raw: dict, problems: list[str]) -> dict:
    """Check a calendar of a table's own records, with no `per` (decision 0122): each record's one open due date
    from this table's own reminder, and the days it was done, from an optional date column (`when`, such as
    "last_done") or else from this table's own Mark done buttons saved in history (decision 0112)."""
    before = len(problems)
    expiring = (table.watch or {}).get("expiring") if isinstance(table.watch, dict) else None
    if raw.get("due") is not True:
        problems.append(f"{where}: without 'per' it is a calendar of this table's own records, so it needs "
                        f"due = true. To show entries that belong to another record, name it with 'per'.")
    elif not expiring or expiring.get("wording") != "due":
        problems.append(f"{where}: 'due = true' without 'per' shows each record's own due date, so this table needs "
                        f"a reminder with wording = \"due\".")
    if table.private:
        problems.append(f"{where}: a private table's calendar needs 'per' and never shows a due date.")
    if raw.get("show", "all") != "all":
        problems.append(f"{where}: a calendar of this table's own records shows them all together: leave out "
                        f"'show' or write show = \"all\".")
    for key in ("state", "looks"):
        if key in raw:
            problems.append(f"{where}: '{key}' needs 'per'; a calendar of this table's own records shows only "
                            f"when each was done and when each is due.")
    when = raw.get("when")
    if when is not None:
        column = table.columns.get(when) if isinstance(when, str) else None
        if column is None or column.type != "date" or column.sensitive or \
                (expiring is not None and when == expiring.get("date")):
            problems.append(f"{where}: 'when' must name a date column of this table that says when it was last "
                            f"done, like \"last_done\": not private, and not the due date itself.")
    if not (isinstance(raw.get("title"), str) and raw["title"].strip()):
        problems.append(f"{where}: 'title' must be the calendar's name, like \"Garden calendar\".")
    words = raw.get("entry")
    if not (isinstance(words, list) and len(words) == 2 and all(isinstance(w, str) and w.strip() for w in words)):
        problems.append(f"{where}: 'entry' must be two words, singular then plural, like [\"job\", \"jobs\"].")
    if raw.get("look", "done") not in CALENDAR_ENTRY_LOOKS:
        problems.append(f"{where}: 'look' must be \"recorded\", \"done\" or \"skipped\", not {raw['look']!r}.")
    history = raw.get("history", False)
    if not isinstance(history, bool):
        problems.append(f"{where}: 'history' must be true or false.")
    elif history and when is None:
        problems.append(f"{where}: 'history = true' shows each earlier date the 'when' column was moved on from, so "
                        f"it needs 'when': a date column that says when each was last done, like \"last_done\".")
    if len(problems) > before:
        return {}
    return {"when": when, "per": None, "show": "all", "title": raw["title"].strip(),
            "entry": [w.strip() for w in raw["entry"]], "state": None, "looks": {},
            "look": raw.get("look", "done"), "due": True, "history": history}


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


def _check_tables(module: str, data: dict, requires: list[str], problems: list[str],
                  optional: list[str] = ()) -> dict[str, Table]:
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
        if "suggestions" in raw:
            if isinstance(raw["suggestions"], bool):
                tables[tname].suggestions = raw["suggestions"]
            else:
                problems.append(f"{where}: 'suggestions' must be true or false.")
        if "private" in raw:  # decision 0120: the whole table is private history
            if not isinstance(raw["private"], bool):
                problems.append(f"{where}: 'private' must be true or false.")
            elif raw["private"]:
                tables[tname].private = True
                if tables[tname].suggestions:
                    problems.append(f"{where}: a private table must also say suggestions = false, so no helper or "
                                    f"spreadsheet import can add to it.")
                for key in ("watch", "chart", "actions", "takes_over"):
                    if key in raw:
                        problems.append(f"{where}: a private table can't use '{key}', which would show its records "
                                        f"on other pages.")
    for table in tables.values():
        _check_travels_when(file, table, problems)
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
            if "pair" in raw:
                tables[tname].pair = _check_pair(file, tables[tname], raw["pair"], problems)
            if "chart" in raw:
                tables[tname].chart = _check_chart(file, tables[tname], raw["chart"], problems)
            if "daily" in raw:
                tables[tname].daily = _check_daily(file, tables[tname], raw["daily"], problems)
            if "calendar" in raw:
                tables[tname].calendar = _check_calendar(file, module, tables[tname], tables, raw["calendar"],
                                                         problems)
            if "price" in raw:
                tables[tname].price = _check_price(file, tables[tname], raw["price"], problems)
            if "bars" in raw:
                tables[tname].bars = _check_bars(file, tables[tname], tables, raw["bars"], problems)
            if "timeline" in raw:
                tables[tname].timeline = _check_timeline(file, module, tables[tname], tables, raw["timeline"],
                                                         problems)
            if "confirm" in raw:
                tables[tname].confirm = _check_confirm(file, tables[tname], raw["confirm"], problems)
            if "takes_over" in raw:
                tables[tname].takes_over = _check_takes_over(file, tables[tname], raw["takes_over"], requires,
                                                             list(optional), problems)
    for table in tables.values():  # decision 0122: one record's due date is on one calendar only
        rule = table.calendar
        if rule and rule.get("due") and rule.get("per"):
            target = table.columns[rule["per"]].to
            if target in tables and tables[target].calendar and not tables[target].calendar.get("per"):
                problems.append(f"In {file}, table '{target}', calendar: '{table.name}' already shows its due dates "
                                f"on its own calendar (due = true). Keep one of the two, so each date shows once.")
    for table in tables.values():
        for column in table.columns.values():
            if column.type in ("link", "links") and column.to:
                where = f"In {file}, table '{table.name}', column '{column.name}'"
                if "." in column.to:
                    target_module, _, target_table = column.to.partition(".")
                    if target_module != module and target_module in optional:
                        column.optional = True  # decision 0115: nullable, and kept while that module is off
                        if column.required or column.required_when:
                            problems.append(f"{where}: it points at the '{target_module}' module, which is only "
                                            f"under optional_requires, so it can't be required. Leave it optional, "
                                            f"or move '{target_module}' to requires.")
                        if column.on_delete == "cascade":
                            problems.append(f"{where}: a link into an optional module can't use on_delete = "
                                            f"\"cascade\": a record that makes sense without the link must not be "
                                            f"deleted with it. Use \"clear\" or \"restrict\".")
                    elif target_module != module and target_module not in requires:
                        problems.append(f"{where}: it points at the '{target_module}' module, which must be listed "
                                        f"in module.toml under requires (or optional_requires, if this module "
                                        f"works without it).")
                    if not NAME.match(target_table):
                        problems.append(f"{where}: '{column.to}' is not a valid table name.")
                elif column.to not in tables:
                    problems.append(f"{where}: it points at a table '{column.to}' that this module does not declare."
                                    f"{_suggest(column.to, list(tables))}")
    for table in tables.values():
        for column in table.columns.values():
            for local in column.link_rule.get("same", {}).values():
                other = table.columns.get(local)
                if other is None or other is column or other.type != "link" or column.optional or other.optional:
                    problems.append(f"In {file}, table '{table.name}', column '{column.name}': link_rule 'same' "
                                    f"must name another link column of this table, like same = {{ person = "
                                    f"\"recipient\" }}.")
                    column.link_rule = {}
                    break
    for table in tables.values():
        for column in table.columns.values():
            if column.not_before is not None:
                other = table.columns.get(column.not_before) if isinstance(column.not_before, str) else None
                if column.type != "date" or other is None or other.type != "date" or other is column:
                    problems.append(f"In {file}, table '{table.name}', column '{column.name}': not_before names "
                                    f"another date column of this table, like not_before = \"lent_on\", and only "
                                    f"applies to a date column.")
                    column.not_before = None
    computed = _computed_columns(tables)
    for tname, raw in raw_tables.items():
        if isinstance(raw, dict) and tname in tables and "actions" in raw:
            tables[tname].actions = _check_actions(file, tables[tname], raw["actions"], computed, tables, problems)
    for tname, raw in raw_tables.items():
        gaps = raw.get("watch", {}).get("gaps") if isinstance(raw, dict) and isinstance(raw.get("watch"), dict) else None
        if gaps is not None and tname in tables:
            tables[tname].watch["gaps"] = _check_gaps(file, tables[tname], tables, gaps, problems)
    return tables


def _computed_columns(tables: dict[str, Table]) -> dict[str, set[str]]:
    """Columns worked out from other records, by table: an item's total and earliest use-by from its batches,
    and a batch's amount changed by stock in and out. Nobody types over these, so no action may set them."""
    computed: dict[str, set[str]] = {}
    for table in tables.values():
        if table.total:
            into = computed.setdefault(table.total["target"], set())
            into.add(table.total["into"])
            if table.total.get("earliest"):
                into.add(table.total["earliest"]["into"])
        if table.adjusts:
            computed.setdefault(table.adjusts["target"], set()).add(table.adjusts["quantity"])
    return computed


def _action_value(column: Column, value) -> str | None:
    """Why `value` cannot be set on `column` by an action, or None when it can."""
    if column.type in ("link", "links", "file"):
        return "links and files can't be set by an action"
    if column.type == "choice":
        keys = [c.key for c in column.choices]
        return None if value in keys else f"it is not one of the choices. Allowed: {', '.join(keys)}"
    if column.type == "boolean":
        return None if isinstance(value, bool) else "it is a yes/no column, so write true or false"
    if column.type == "date":
        if value == "today":
            return None
        try:
            date.fromisoformat(str(value))
            return None
        except ValueError:
            return "write \"today\" or a date like 2027-05-20"
    if column.type == "datetime":
        return None if value == "now" else "write \"now\""
    if column.type in NUMERIC_TYPES:
        if not _number(value):
            return "it is a number column, so write a number"
        if (column.min is not None and value < column.min) or (column.max is not None and value > column.max):
            return "the number is outside the column's min and max"
        return None
    return None if isinstance(value, str) and value.strip() else "write the words to fill in"


def _check_actions(file: str, table: Table, raw, computed_by_table: dict[str, set[str]], tables: dict[str, Table],
                   problems: list[str]) -> list[dict]:
    """Check `actions`: buttons on a record's page that set a few fields, like "Mark returned", or that add a
    linked record through a small form, like "Mark done" (decisions 0075 and 0091)."""
    computed = computed_by_table.get(table.name, set())
    where = f"In {file}, table '{table.name}', actions"
    if not isinstance(raw, list):
        problems.append(f"{where}: write each action as a [[tables.{table.name}.actions]] section.")
        return []
    actions, keys = [], set()
    columns = table.columns
    for number, action in enumerate(raw, start=1):
        a_where = f"{where} {number}"
        if not isinstance(action, dict):
            problems.append(f"{a_where}: describe it with key, label, show_when, set and done.")
            continue
        problems.extend(_unknown_keys(a_where, action, ACTION_KEYS + FORM_ACTION_KEYS))
        form = "adds" in action
        missing = [k for k in (("key", "label", "done") if form else ACTION_KEYS) if k not in action]
        if missing:
            problems.append(f"{a_where}: {', '.join(repr(k) for k in missing)} "
                            f"{'is' if len(missing) == 1 else 'are'} missing.")
            continue
        # A one-step button may name its Undo words too (decision 0112); the rest belong to a small form.
        extra = [k for k in FORM_ACTION_KEYS if k in action and k not in ("adds", "undo")]
        if extra and not form:
            problems.append(f"{a_where}: {', '.join(repr(k) for k in extra)} only work in an action that adds a "
                            f"record, with adds = {{ table = ..., link = ..., ask = [...] }}.")
            continue
        key = action["key"]
        if not isinstance(key, str) or not NAME.match(key):
            problems.append(f"{a_where}: 'key' must be lower-case letters, digits and underscores, like \"returned\".")
            continue
        a_where = f"{where} '{key}'"
        if key in keys:
            problems.append(f"{a_where}: two actions have this key.")
            continue
        keys.add(key)
        if any(not isinstance(action[k], str) or not action[k].strip() for k in ("label", "done")):
            problems.append(f"{a_where}: 'label' (the button's words) and 'done' (what it says afterwards) must "
                            f"be short sentences, like label = \"Mark returned\".")
            continue
        shown, values = action.get("show_when"), action.get("set")
        if shown is not None or not form:
            if not _check_where(f"{a_where}, show_when", shown, columns, problems):
                continue
            private = [c for c in shown if columns[c].sensitive]
            if private:  # whether the button shows would give the private value away
                problems.append(f"{a_where}, show_when: '{private[0]}' is private, so it can't decide when a "
                                f"button shows.")
                continue
        shown = shown or {}
        if values is not None or not form:
            if not isinstance(values, dict) or not values:
                problems.append(f"{a_where}: 'set' lists the fields to fill in, like {{ status = \"returned\" }}.")
                continue
            if not _check_set(a_where, values, columns, computed, problems):
                continue
        values = values or {}
        if not form and not any(name in values and values[name] != value for name, value in shown.items()):
            # Pressed twice (a double click, an old page), the second press must find nothing to do.
            problems.append(f"{a_where}: 'set' must change a column named in show_when, so the button goes away "
                            f"once pressed, like show_when = {{ status = \"out\" }} with "
                            f"set = {{ status = \"returned\" }}.")
            continue
        needed = [c.name for c in columns.values() if c.required_when and c.name not in values
                  and all(values.get(k) == v for k, v in c.required_when.items())] if values else []
        if needed:
            problems.append(f"{a_where}: what it sets makes '{needed[0]}' required, so set that too.")
            continue
        if not form and "undo" in action and not _words(action["undo"]):
            problems.append(f"{a_where}: 'undo' must be a short sentence, like undo = \"Undo Mark returned\".")
            continue
        checked = {"key": key, "label": action["label"].strip(), "done": action["done"].strip(),
                   "show_when": dict(shown), "set": dict(values), "adds": None,
                   "undo": (action.get("undo") or "").strip() or None if not form else None}
        if form:  # a double press is caught by the form's one-use number instead (decision 0091)
            more = _check_form_action(a_where, table, tables, action, values, computed_by_table, problems)
            if more is None:
                continue
            checked.update(more)
        actions.append(checked)
    return actions


def _check_set(where: str, values: dict, columns: dict[str, Column], computed: set[str], problems: list[str],
               part: str = "set") -> bool:
    """Check fixed values an action fills in: real, public columns that are typed in, with fitting values."""
    ok = True
    for name, value in values.items():
        column = columns.get(name)
        if column is None:
            problems.append(f"{where}, {part}: there is no column '{name}'.{_suggest(name, list(columns))}")
        elif column.sensitive:
            problems.append(f"{where}, {part}: '{name}' is private, so an action can't change it.")
        elif name in computed:
            problems.append(f"{where}, {part}: '{name}' is worked out from other records, so an action can't "
                            f"set it.")
        elif (why := _action_value(column, value)) is not None:
            problems.append(f"{where}, {part}: '{name}' can't be set to {value!r}: {why}.")
        else:
            continue
        ok = False
    return ok


def _words(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _date_column(table: Table, name, computed: set[str]) -> str | None:
    """Why `name` is not a public, typed-in date column of `table`, or None when it is."""
    column = table.columns.get(name) if isinstance(name, str) else None
    if column is None:
        return f"there is no column {name!r}.{_suggest(str(name), list(table.columns))}"
    if column.type != "date":
        return f"'{name}' is not a date column"
    if column.sensitive:
        return f"'{name}' is private"
    if name in computed:
        return f"'{name}' is worked out from other records"
    return None


def _placeholders(text: str) -> set[str]:
    return set(re.findall(r"{(\w*)}", text))


def _check_form_action(where: str, table: Table, tables: dict[str, Table], action: dict, values: dict,
                       computed_by_table: dict[str, set[str]], problems: list[str]) -> dict | None:
    """Check an action that adds a linked record through a small form, like Home care's "Mark done"
    (decision 0091): which record it adds and what it asks, and the optional latest date, next date and Undo."""
    count = len(problems)
    computed = computed_by_table.get(table.name, set())
    adds = action["adds"]
    example = 'adds = { table = "work_done", link = "job", ask = ["done_on", "notes"] }'
    if not isinstance(adds, dict):
        problems.append(f"{where}: 'adds' names the record the action adds, like {example}.")
        return None
    problems.extend(_unknown_keys(f"{where}, adds", adds, ADDS_KEYS))
    other = tables.get(adds.get("table")) if isinstance(adds.get("table"), str) else None
    if other is None or other is table:
        problems.append(f"{where}, adds: 'table' must name another table of this module, like {example}."
                        f"{_suggest(str(adds.get('table')), [t for t in tables if t != table.name])}")
        return None
    link = other.columns.get(adds.get("link")) if isinstance(adds.get("link"), str) else None
    if link is None or link.type != "link" or link.to != table.name:
        problems.append(f"{where}, adds: 'link' must name the column of '{other.name}' that points at "
                        f"'{table.name}'.")
        return None
    other_computed = computed_by_table.get(other.name, set())
    ask = adds.get("ask")
    if not isinstance(ask, list) or not ask or not all(isinstance(a, str) for a in ask) or len(set(ask)) != len(ask):
        problems.append(f"{where}, adds: 'ask' lists the fields the form asks for, each once, like "
                        f"ask = [\"done_on\", \"notes\"].")
        return None
    for name in ask:
        column = other.columns.get(name)
        if column is None:
            problems.append(f"{where}, adds, ask: '{other.name}' has no column '{name}'."
                            f"{_suggest(name, list(other.columns))}")
        elif name == link.name:
            problems.append(f"{where}, adds, ask: '{name}' is filled in by the action itself, so it is not asked.")
        elif column.sensitive:
            problems.append(f"{where}, adds, ask: '{name}' is private, so this form can't ask for it.")
        elif name in other_computed:
            problems.append(f"{where}, adds, ask: '{name}' is worked out from other records, so it is not asked.")
        elif column.type in ("links", "file"):
            problems.append(f"{where}, adds, ask: '{name}' is a list of links or a file, which this form can't ask.")
    fixed = adds.get("values", {})
    if not isinstance(fixed, dict):
        problems.append(f"{where}, adds: 'values' fills in fixed values, like values = {{ kind = \"check\" }}.")
        fixed = {}
    clash = [n for n in fixed if n in ask or n == link.name]
    if clash:
        problems.append(f"{where}, adds, values: '{clash[0]}' is asked or linked already, so it can't also be fixed.")
    else:
        _check_set(f"{where}, adds", fixed, other.columns, other_computed, problems, part="values")
    copy = adds.get("copy", {})
    if not isinstance(copy, dict):
        problems.append(f"{where}, adds: 'copy' fills fields from this record, like copy = {{ scheduled_on = "
                        f"\"next_due\" }}.")
        copy = {}
    for into, source in copy.items():
        target, origin = other.columns.get(into), table.columns.get(source) if isinstance(source, str) else None
        if target is None or into in ask or into in fixed or into == link.name or target.sensitive or \
                into in other_computed:
            problems.append(f"{where}, adds, copy: '{into}' must be a public column of '{other.name}' that is not "
                            f"asked, fixed or the link.")
        elif origin is None or origin.sensitive or origin.type != target.type or origin.type not in \
                ("date", "text", "integer", "choice", "boolean"):
            problems.append(f"{where}, adds, copy: '{source}' must be a public column of '{table.name}' of the "
                            f"same kind as '{into}'.")
    for column in other.columns.values():
        if column.required and column.default is None and column.name not in ask and column.name not in fixed \
                and column.name != link.name:
            problems.append(f"{where}, adds: '{column.name}' is required in '{other.name}', so ask for it or give "
                            f"it a value.")
    if "add_button" in adds and not _words(adds["add_button"]):
        problems.append(f"{where}, adds: 'add_button' is the words for the ordinary add button, like "
                        f"add_button = \"Add an older entry\".")
    latest = action.get("latest")
    if latest is not None and not isinstance(latest, dict):
        problems.append(f"{where}: write latest like latest = {{ date = \"done_on\", into = \"last_done\" }}.")
    elif latest is not None:
        problems.extend(_unknown_keys(f"{where}, latest", latest, LATEST_KEYS))
        if latest.get("date") not in ask or _date_column(other, latest.get("date"), other_computed) is not None:
            problems.append(f"{where}, latest: 'date' must be one of the asked fields and a date, like "
                            f"date = \"done_on\".")
        if "into" in latest and (why := _date_column(table, latest.get("into"), computed)) is not None:
            problems.append(f"{where}, latest: 'into' must be a date column of '{table.name}': {why}.")
        elif latest.get("into") in values:
            problems.append(f"{where}, latest: '{latest['into']}' is in set as well; choose one.")
    next_date = action.get("next_date")
    if next_date is not None and not isinstance(next_date, dict):
        problems.append(f"{where}: write next_date like next_date = {{ into = \"next_due\", question = "
                        f"\"When do you want to do it again?\" }}.")
    elif next_date is not None:
        problems.extend(_unknown_keys(f"{where}, next_date", next_date, NEXT_DATE_KEYS))
        if not isinstance(latest, dict):
            problems.append(f"{where}, next_date: it needs 'latest' too, so the next date can be compared with the "
                            f"day the work was done.")
        if (why := _date_column(table, next_date.get("into"), computed)) is not None:
            problems.append(f"{where}, next_date: 'into' must be a date column of '{table.name}': {why}.")
        elif next_date.get("into") in values or \
                (isinstance(latest, dict) and latest.get("into") and next_date.get("into") == latest.get("into")):
            problems.append(f"{where}, next_date: '{next_date['into']}' is filled in elsewhere in this action.")
        if not _words(next_date.get("question")):
            problems.append(f"{where}, next_date: 'question' is the heading above the choices, like "
                            f"question = \"When do you want to do it again?\".")
        repeat = next_date.get("repeat")
        if repeat is not None:
            if isinstance(repeat, dict):
                problems.extend(_unknown_keys(f"{where}, next_date, repeat", repeat, REPEAT_KEYS))
            count_col = table.columns.get(repeat.get("count")) if isinstance(repeat, dict) else None
            unit_col = table.columns.get(repeat.get("unit")) if isinstance(repeat, dict) else None
            if count_col is None or count_col.type != "integer" or count_col.sensitive:
                problems.append(f"{where}, next_date, repeat: 'count' must name a whole-number column of "
                                f"'{table.name}', like count = \"repeat_count\".")
            if unit_col is None or unit_col.type != "choice" or unit_col.sensitive or \
                    not {c.key for c in unit_col.choices} <= set(REPEAT_UNITS):
                problems.append(f"{where}, next_date, repeat: 'unit' must name a choice column of '{table.name}' "
                                f"whose choices are among {', '.join(REPEAT_UNITS)}.")
            for part in ("from", "anchor"):
                if isinstance(repeat, dict) and part in repeat and \
                        (why := _date_column(table, repeat.get(part), computed)) is not None:
                    problems.append(f"{where}, next_date, repeat: '{part}' must be a date column of "
                                    f"'{table.name}': {why}.")
    helps = action.get("help", {})
    if not isinstance(helps, dict) or any(n not in ask or not _words(t) for n, t in helps.items()):
        problems.append(f"{where}: 'help' gives words under asked fields, like help = {{ done_on = \"The day the "
                        f"work was finished.\" }}.")
    for name in ("title", "intro", "undo"):
        if name in action and not _words(action[name]):
            problems.append(f"{where}: '{name}' must be a short sentence.")
    if _words(action.get("title")) and _placeholders(action["title"]) - {"record"}:
        problems.append(f"{where}: 'title' may name only {{record}}, like title = \"Mark {{record}} done\".")
    unknown = _placeholders(action["done"]) - set(ask) - set(copy)
    if unknown:
        problems.append(f"{where}: 'done' may name only asked fields, like {{{ask[0]}}}, not "
                        f"{{{sorted(unknown)[0]}}}.")
    messages = action.get("messages", {})
    if not isinstance(messages, dict):
        problems.append(f"{where}: write messages like messages = {{ stale = \"...\" }}.")
        messages = {}
    problems.extend(_unknown_keys(f"{where}, messages", messages, MESSAGE_KEYS))
    if any(not _words(t) for t in messages.values()):
        problems.append(f"{where}, messages: each message must be a short sentence.")
    elif _placeholders(messages.get("same_day", "")) - {"date"}:
        problems.append(f"{where}, messages: 'same_day' may name only {{date}}.")
    counts_as = action.get("counts_as", "done")
    if counts_as not in COUNTS_AS:
        problems.append(f"{where}: 'counts_as' is \"done\" or \"skipped\", for Things to do.")
    if len(problems) > count:
        return None
    return {"adds": {"table": other.name, "link": link.name, "ask": list(ask), "values": dict(fixed),
                     "add_button": (adds.get("add_button") or "").strip() or None, "copy": dict(copy)},
            "counts_as": counts_as,
            "latest": dict(latest) if latest else None,
            "next_date": {"into": next_date["into"], "question": next_date["question"].strip(),
                          "repeat": dict(next_date["repeat"]) if next_date.get("repeat") else None}
            if next_date else None,
            "help": {k: v.strip() for k, v in helps.items()},
            "title": (action.get("title") or "").strip() or None,
            "intro": (action.get("intro") or "").strip() or None,
            "undo": (action.get("undo") or "").strip() or None,
            "messages": {k: messages.get(k, "").strip() or DEFAULT_MESSAGES[k] for k in MESSAGE_KEYS}}


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
        actions = {a["key"] for a in tables[tname].actions}
        raw_actions = raw.get("actions", {})
        if not isinstance(raw_actions, dict):
            problems.append(f"{where}: write actions like actions.returned = {{ label = \"Back now\" }}.")
            raw_actions = {}
        for key, words in raw_actions.items():
            a_where = f"{where}, action '{key}'"
            if key not in actions:
                problems.append(f"{a_where}: tables.toml declares no such action.{_suggest(key, sorted(actions))}")
            elif not isinstance(words, dict):
                problems.append(f"{a_where}: write it like {{ label = \"Back now\", done = \"Marked as back.\" }}.")
            else:
                problems.extend(_unknown_keys(a_where, words, LABEL_ACTION_KEYS))
                if any(not isinstance(v, str) or not v.strip() for k, v in words.items() if k in LABEL_ACTION_KEYS):
                    problems.append(f"{a_where}: 'label' and 'done' must be short sentences.")
        for cname, craw in raw.get("columns", {}).items():
            if cname not in known:
                problems.append(f"{where}: there is no column '{cname}'.{_suggest(cname, list(known))}")
            elif isinstance(craw, dict):
                problems.extend(_unknown_keys(f"{where}, column '{cname}'", craw, LABEL_COLUMN_KEYS))
                if "optional" in craw:
                    _check_optional_words(f"{where}, column '{cname}'", tables[tname].columns.get(cname),
                                          craw["optional"], problems)
                column = known[cname]
                if "blank" in craw and isinstance(craw["blank"], str):  # "I do not know" for an optional link (0120)
                    if not craw["blank"].strip() or column.type != "link" or column.required or \
                            (tables[tname].adjusts or {}).get("link") == cname:
                        problems.append(f"{where}, column '{cname}': blank as words, like blank = \"I do not know\", "
                                        f"only applies to an optional single link.")
                elif "blank" in craw:  # the words for leaving "Which batch" blank (DESIGN.md 5.7)
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
        if "takes_over" in raw:  # the household's words around moving a reminder (decision 0117)
            words = raw["takes_over"]
            if not tables[tname].takes_over:
                problems.append(f"{where}: 'takes_over' words only apply to a table whose tables.toml declares "
                                f"takes_over.")
            elif not isinstance(words, dict) or set(words) - set(TAKES_OVER_WORDS) or \
                    any(not isinstance(v, str) or not v.strip() for v in words.values()):
                problems.append(f"{where}: takes_over gives the household's words, each a short sentence, using "
                                f"only {', '.join(TAKES_OVER_WORDS)}.")
        if "add_button" in raw and (not isinstance(raw["add_button"], str) or not raw["add_button"].strip()):
            problems.append(f"{where}: 'add_button' must be a few words, like \"Add a reading\".")
        if "under" in raw:
            _check_under(where, raw["under"], tables[tname], problems)
        for listing in ("form", "list"):
            for cname in raw.get(listing, []):
                if cname not in known:
                    problems.append(f"{where}: '{listing}' names a column '{cname}' that does not exist."
                                    f"{_suggest(cname, list(known))}")
    return data


def _check_under(where: str, raw, table: Table, problems: list[str]) -> None:
    """Check `under`: this table's records listed on the page of the record one link points at (decision 0111)."""
    where = f"{where}, under"
    if not isinstance(raw, dict):
        problems.append(f"{where}: write it like {{ link = \"service\", title = \"Cost estimates\", "
                        f"columns = [\"kind\", \"quoted_on\"] }}.")
        return
    problems.extend(_unknown_keys(where, raw, UNDER_KEYS))
    link = table.columns.get(raw.get("link")) if isinstance(raw.get("link"), str) else None
    if link is None or link.type != "link":
        problems.append(f"{where}: 'link' must name a link column of this table.")
    for key in ("title", "intro", "reveal"):
        if (key in raw or key == "title") and not (isinstance(raw.get(key), str) and raw[key].strip()):
            problems.append(f"{where}: '{key}' must be a short heading or sentence.")
    columns = raw.get("columns")
    if not isinstance(columns, list) or not columns or any(c not in table.columns or c == raw.get("link")
                                                           or table.columns[c].type == "links" for c in columns):
        problems.append(f"{where}: 'columns' lists other columns of this table to show.")
        columns = []
    order = table.columns.get(raw.get("order")) if isinstance(raw.get("order"), str) else None
    if "order" in raw and (order is None or order.sensitive or order.type in ("links", "longtext")):
        problems.append(f"{where}: 'order' names a column of this table that is not private.")
    if "reveal" in raw and not any(table.columns[c].sensitive for c in columns):
        problems.append(f"{where}: 'reveal' is the words for showing private columns, and none are listed.")


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
            if tables[table].private:  # decision 0120: private history is never printed on an ordinary sheet
                problems.append(f"{s_where}: '{table}' is a private table, so no sheet may print it.")
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


def _check_optional_uses(tables: dict[str, Table], sheets: dict, problems: list[str]) -> None:
    """A link into an optional module (decision 0115) may be on forms, lists and sheets as itself, where the core
    shows neutral words while that module is off. It may not be a gap question (the household could not answer
    it with that module off) or lead a sheet to a column of the other module (which may not be there)."""
    for table in tables.values():
        optional = {c.name for c in table.columns.values() if c.optional}
        if not optional:
            continue
        for gap in table.watch.get("gaps", []) if isinstance(table.watch, dict) else []:
            missing = gap.get("missing") if isinstance(gap, dict) else None
            if isinstance(missing, str) and missing.partition(".")[0] in optional:
                problems.append(f"In tables.toml, table '{table.name}', watch.gaps: '{missing}' is a link into an "
                                f"optional module, so it can't be a question; a record makes sense without it.")
        for sheet in sheets.get("sheet", []) if isinstance(sheets.get("sheet", []), list) else []:
            for section in sheet.get("section", []) if isinstance(sheet, dict) else []:
                if not isinstance(section, dict) or section.get("table") != table.name:
                    continue
                for spec in section.get("columns", []) if isinstance(section.get("columns"), list) else []:
                    if isinstance(spec, str) and "." in spec and spec.partition(".")[0] in optional:
                        problems.append(f"In sheets.toml, sheet '{sheet.get('name')}': '{spec}' reads a column "
                                        f"through a link into an optional module, which may be off. Print "
                                        f"'{spec.partition('.')[0]}' itself instead.")


def _check_optional_words(where: str, column: Column | None, words, problems: list[str]) -> None:
    """labels.toml `optional = { off_help = "…", kept = "…", … }` for a link into an optional module."""
    if column is None or not column.optional:
        problems.append(f"{where}: 'optional' words only apply to a link into a module under optional_requires.")
    elif not isinstance(words, dict) or not words or set(words) - set(OPTIONAL_WORDS) or \
            any(not isinstance(v, str) or not v.strip() for v in words.values()):
        problems.append(f"{where}: optional gives the household's words, each a short sentence, using only "
                        f"{', '.join(OPTIONAL_WORDS)}.")


def load_module(folder: Path) -> Module:
    """Read and check one module folder. Raises ModuleError listing every problem found."""
    folder = Path(folder)
    problems: list[str] = []
    meta = _read_toml(folder / "module.toml", problems, required=True)
    if meta:
        _check_module_toml(folder, meta, problems)
    requires = meta.get("requires", []) if isinstance(meta.get("requires", []), list) else []
    optional = meta.get("optional_requires", [])
    optional = [x for x in optional if isinstance(x, str)] if isinstance(optional, list) else []
    tables = _check_tables(folder.name, _read_toml(folder / "tables.toml", problems, required=True),
                           requires, problems, optional)
    _check_optional_uses(tables, _read_toml(folder / "sheets.toml", [], required=False), problems)
    labels = _check_labels(_read_toml(folder / "labels.toml", problems, required=False), tables, problems)
    sheets = _check_sheets(_read_toml(folder / "sheets.toml", problems, required=False), tables, problems)
    catalogues = _load_catalogues(folder, labels, tables, problems)
    prompt_set = prompt_files.load(folder, folder.name, tables, _read_toml, problems)
    try:
        migrations = load_track(folder.name, folder / "migrations")
    except MigrationError as error:
        problems.append(str(error))
        migrations = []
    if problems:
        raise ModuleError(folder.name, problems)
    return Module(name=meta["name"], title=meta["title"], version=meta["version"],
                  description=meta["description"], kind=meta["kind"], requires=list(requires),
                  optional_requires=list(optional),
                  outbound_hosts=list(meta.get("outbound_hosts", [])), folder=folder,
                  tables=tables, labels=labels, migrations=migrations, sheets=sheets, catalogues=catalogues,
                  prompts=prompt_set)


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


def _cross_module_timeline_problems(module: Module, by_name: dict[str, Module]) -> list[str]:
    """Check a timeline `per` like "service.vehicle" whose first link points into another module, once that module
    is loaded: the table it names must have that column, as a required link (decision 0130)."""
    problems = []
    for table in module.tables.values():
        rule = table.timeline
        link = table.columns.get(rule["link"]) if rule and rule.get("through") else None
        if link is None or "." not in (link.to or ""):
            continue
        other, _, other_table = link.to.partition(".")
        target = by_name[other].tables.get(other_table) if other in by_name else None
        column = target.columns.get(rule["through"]) if target is not None else None
        if column is None or column.type != "link" or not column.required:
            problems.append(f"In tables.toml, table '{table.name}', timeline: in per = \"{rule['per']}\", "
                            f"'{link.to}' must have a required link column '{rule['through']}'.")
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


def _needs(by_name: dict[str, Module], start: str, wanted: str) -> bool:
    """True if module `start` requires `wanted`, directly or through the modules it requires."""
    seen, todo = set(), [start]
    while todo:
        name = todo.pop()
        if name == wanted:
            return True
        if name in seen or name not in by_name:
            continue
        seen.add(name)
        todo.extend(by_name[name].requires)
    return False


def _optional_target_problems(module: Module, by_name: dict[str, Module]) -> list[str]:
    """A link into an optional module that is installed must name one of its tables (decision 0115). A module
    that is not installed, or could not be loaded, is simply off: the link is kept and hidden."""
    problems = []
    for table in module.tables.values():
        for column in table.columns.values():
            if not column.optional:
                continue
            other, _, other_table = column.to.partition(".")
            target = by_name.get(other)
            if target is not None and other_table not in target.tables:
                problems.append(f"In tables.toml, table '{table.name}', column '{column.name}': the '{other}' module "
                                f"has no table '{other_table}'.{_suggest(other_table, list(target.tables))}")
            elif target is not None and column.with_place:
                place = target.tables[other_table].columns.get(column.with_place)
                if place is None or place.type != "link":
                    problems.append(f"In tables.toml, table '{table.name}', column '{column.name}': with_place names "
                                    f"'{column.with_place}', which is not a link column of '{column.to}'.")
    return problems


def _takes_over_problems(module: Module, by_name: dict[str, Module]) -> list[str]:
    """`takes_over` (decision 0117) once the other module is loaded: its table exists, reminds by the date that is
    copied, and every copied column of it is ordinary (never private) and of the same kind, links to the same
    list. A module that is not installed is simply off: nothing can be moved from it."""
    problems = []
    for table in module.tables.values():
        rule = table.takes_over
        if not rule:
            continue
        where = f"In tables.toml, table '{table.name}', takes_over"
        other, _, other_table = rule["from"].partition(".")
        if other not in by_name:
            continue
        source = by_name[other].tables.get(other_table)
        if source is None:
            problems.append(f"{where}: the '{other}' module has no table '{other_table}'."
                            f"{_suggest(other_table, list(by_name[other].tables))}")
            continue
        watched = source.watch.get("expiring") if isinstance(source.watch, dict) else None
        date_column = table.watch["expiring"]["date"]
        if not watched or rule["copy"].get(date_column) != watched["date"]:
            problems.append(f"{where}: '{rule['from']}' must remind by the date copied into '{date_column}'.")
        for mine, theirs in rule["copy"].items():
            column, given = table.columns[mine], source.columns.get(theirs)
            if given is None:
                problems.append(f"{where}, copy: '{rule['from']}' has no column '{theirs}'."
                                f"{_suggest(theirs, list(source.columns))}")
            elif given.sensitive or given.type in ("links", "file"):
                problems.append(f"{where}, copy: '{theirs}' is private or not a single value in '{rule['from']}', "
                                f"so it is never copied.")
            elif given.type != column.type or (column.type == "link" and _linked_name(module.name, column) !=
                                               _linked_name(other, given)):
                problems.append(f"{where}, copy: '{mine}' and '{rule['from']}' '{theirs}' are not the same kind of "
                                f"value.")
    return problems


def _link_rule_problems(module: Module, by_name: dict[str, Module]) -> list[str]:
    """`link_rule` once the linked module is loaded (decision 0120): `where` names choice columns of the linked table
    and their choices, `same` links of it that point where this table's own link points, and `shows` one of its
    private text columns. None of the compared columns may be private: the check must never read a secret."""
    problems = []
    for table in module.tables.values():
        for column in table.columns.values():
            rule = column.link_rule
            if not rule:
                continue
            where = f"In tables.toml, table '{table.name}', column '{column.name}', link_rule"
            other, _, other_table = _linked_name(module.name, column).partition(".")
            target = by_name[other].tables.get(other_table) if other in by_name else None
            if target is None:
                problems.append(f"{where}: '{column.to}' could not be found.")
                continue
            for name, value in rule["where"].items():
                found = target.columns.get(name)
                if found is None or found.type != "choice" or found.sensitive or \
                        value not in [c.key for c in found.choices]:
                    problems.append(f"{where}: where '{name}' must be a choice column of '{column.to}' that is not "
                                    f"private, and '{value}' one of its choices.")
            for name, local in rule["same"].items():
                found = target.columns.get(name)
                if found is None or found.type != "link" or found.sensitive or \
                        _linked_name(other, found) != _linked_name(module.name, table.columns[local]):
                    problems.append(f"{where}: same '{name}' must be a link column of '{column.to}' that points "
                                    f"where '{local}' points.")
            shows = rule.get("shows")
            if shows is not None and (shows not in target.columns or not target.columns[shows].sensitive
                                      or target.columns[shows].type not in ("text", "longtext")):
                problems.append(f"{where}: shows '{shows}' must be a private text column of '{column.to}'.")
    return problems


def _linked_name(module: str, column: Column) -> str:
    """The module and table a link points at, as "vehicles.vehicles"."""
    return column.to if "." in column.to else f"{module}.{column.to}"


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
        for name in module.optional_requires:  # decision 0115: loaded first when it is there, never needed
            if name in by_name and name not in path and not _needs(by_name, name, module.name):
                visit(by_name[name], path + [module.name])
        problems = _optional_target_problems(module, {n: m for n, m in by_name.items() if state.get(n) != "failed"})
        if problems:
            failures.setdefault(module.name, []).extend(problems)
            state[module.name] = "failed"
            return False
        problems = _cross_module_gap_problems(module, by_name) + _cross_module_sheet_problems(module, by_name)
        problems += _cross_module_timeline_problems(module, by_name)
        problems += _link_rule_problems(module, by_name)
        problems += _takes_over_problems(module, {n: m for n, m in by_name.items() if state.get(n) == "done"})
        if module.prompts is not None:
            problems += prompt_files.cross_module_problems(module.prompts, by_name)
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
