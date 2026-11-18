"""Read a spreadsheet saved as CSV, match its columns to a table's fields, and check every row before it goes to Review.

Nothing here writes a record. The dry run uses the same checks a helper's suggestion gets (Records.check_create),
inside a transaction that is always rolled back; rows that pass are staged by proposals.stage_import and added only
when a person accepts them on Review (decision 0080). The file itself is never written anywhere.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from dashboard.core import dates, naming
from dashboard.core.modules import Column
from dashboard.core.proposals import HIDDEN_CHARACTERS
from dashboard.core.records import Records, TableInfo
from dashboard.core.schema import target_table
from dashboard.errors import PlainError

MAX_BYTES = 1_000_000
MAX_ROWS = 2000
LIMIT_TEXT = "1 MB"
SEVERAL = ";"  # separates names in a column that links to several records
PATH_PARTS = re.compile(r"\s*[›>]\s*")
THOUSANDS = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$")
CURRENCY = re.compile(r"^([+-]?)\s*[$£€¥]\s*")
QUESTION_WORDS = ("is ", "must ", "has ", "points ", "can't ", "cannot ", "matches ", "uses ", "contains ")


class FileProblem(PlainError):
    """The whole file cannot be used, with the plain reason (too large, not UTF-8, a broken quote)."""


@dataclass
class Sheet:
    """A parsed CSV: its headings and each data row with its spreadsheet row number (the heading row is row 1)."""
    headers: list[str]
    rows: list[tuple[int, list[str]]]
    delimiter: str


@dataclass
class DryRun:
    """What would happen: rows ready to send (row number, values) and rows that need fixing (row number, reasons)."""
    ready: list[tuple[int, dict]] = field(default_factory=list)
    problems: list[tuple[int, list[str]]] = field(default_factory=list)


# ----- reading the file ---------------------------------------------------------------------------------

def decode(data: bytes) -> str:
    """The file's text, or FileProblem. UTF-8 with or without a byte order mark; nothing is ever replaced."""
    if len(data) > MAX_BYTES:
        raise FileProblem(f"This file is {len(data) / 1_000_000:.1f} MB. The limit is {LIMIT_TEXT}: "
                          f"split it into smaller files and import each one.")
    if not data.strip():
        raise FileProblem("This file is empty.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FileProblem("This file is not saved as UTF-8 text, so some letters could be read wrongly. "
                          "In your spreadsheet choose Save As, then \"CSV UTF-8\", and try again.") from None


def _delimiter(text: str) -> str:
    """Comma or semicolon, whichever the heading row uses more (spreadsheets set to a comma decimal use ;)."""
    first = text.split("\n", 1)[0]
    return ";" if first.count(";") > first.count(",") else ","


def parse(text: str) -> Sheet:
    """Headings and rows of a CSV text. Quoted commas, quoted line breaks, CRLF and LF are all understood."""
    delimiter = _delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    found: list[list[str]] = []
    try:
        for record in reader:
            found.append(record)
            if len(found) > MAX_ROWS + 1:
                raise FileProblem(f"This file has more than {MAX_ROWS:,} rows. Split it into smaller files "
                                  f"and import each one.")
    except csv.Error:
        raise FileProblem(f"Row {len(found) + 1} could not be read: check its quote marks (\"). "
                          f"Nothing was imported.") from None
    if not found or not any(cell.strip() for cell in found[0]):
        raise FileProblem("The first row should hold the column headings, such as name, unit, notes.")
    headers = [cell.strip() for cell in found[0]]
    rows = [(number, record) for number, record in enumerate(found[1:], start=2)
            if any(cell.strip() for cell in record)]
    if not rows:
        raise FileProblem("This file has headings but no rows under them.")
    return Sheet(headers, rows, delimiter)


# ----- which fields can be filled in ----------------------------------------------------------------------

def label(info: TableInfo, column: Column) -> str:
    """A column's friendly name, as labels.toml gives it."""
    named = info.module.labels.get("tables", {}).get(info.table.name, {}).get("columns", {}).get(column.name, {})
    return named.get("label") or column.name.replace("_", " ").capitalize()


def table_title(info: TableInfo) -> str:
    return info.module.labels.get("tables", {}).get(info.table.name, {}).get("title") or info.table.title


def why_not_table(info: TableInfo) -> str | None:
    """Why a whole table cannot be imported into in this version, or None."""
    if any(c.required and c.sensitive for c in info.table.columns.values()):
        return f"{table_title(info)} needs a private detail, and private details can't be imported in this version."
    if any(c.required and c.type == "file" for c in info.table.columns.values()):
        return f"{table_title(info)} needs a file, and files can't be imported."
    return None


def why_not_column(store: Records, info: TableInfo, column: Column) -> str | None:
    """Why one field cannot be filled from a spreadsheet, or None when it can."""
    if column.sensitive:
        return f"{label(info, column)} is a private detail. Private details can't be imported in this version."
    if column.type == "file":
        return f"{label(info, column)} is a file, and files can't be imported."
    if column.type in ("link", "links") and target_table(info.module.name, column) not in store.registry:
        return f"{label(info, column)} links to a part of your records that is switched off."
    starts = {c for other in store._totals_into(info) for c in other.table.total["starts_from"]}
    if column.name in store._derived(info) - starts:
        return f"{label(info, column)} is worked out from other records."
    return None


def fields(store: Records, info: TableInfo) -> tuple[list[Column], list[Column]]:
    """(fields a column can be matched to, private fields that can't), in the order the add form shows them."""
    form = info.module.labels.get("tables", {}).get(info.table.name, {}).get("form") or []
    ordered = [info.table.columns[n] for n in form if n in info.table.columns]
    ordered += [c for c in info.table.columns.values() if c not in ordered]
    usable = [c for c in ordered if why_not_column(store, info, c) is None]
    private = [c for c in ordered if c.sensitive]
    return usable, private


def _words(text: str) -> str:
    return " ".join(re.sub(r"[_\-?:.]+", " ", text).casefold().split())


def auto_match(store: Records, info: TableInfo, headers: list[str]) -> list[str]:
    """A field for each heading, matched by its label or key ignoring case, spaces and underscores; "" to skip.

    A private field is never matched. Each field is matched to the first heading that names it."""
    usable, _private = fields(store, info)
    by_words = {}
    for column in usable:
        by_words.setdefault(_words(column.name), column.name)
        by_words.setdefault(_words(label(info, column)), column.name)
    chosen, taken = [], set()
    for header in headers:
        name = by_words.get(_words(header), "")
        if name in taken:
            name = ""
        taken.add(name)
        chosen.append(name)
    return chosen


def private_headers(store: Records, info: TableInfo, headers: list[str]) -> dict[int, str]:
    """Headings that name a private field: their position and the plain reason they will be skipped."""
    _usable, private = fields(store, info)
    named = {}
    for column in private:
        named[_words(column.name)] = column
        named[_words(label(info, column))] = column
    return {i: why_not_column(store, info, named[_words(h)]) for i, h in enumerate(headers) if _words(h) in named}


def mapping_problems(store: Records, info: TableInfo, mapping: list[str]) -> list[str]:
    """What is wrong with the chosen matches as a whole: a field chosen twice, a private one, a required one missing."""
    problems, seen = [], set()
    for name in mapping:
        if not name:
            continue
        column = info.table.columns.get(name)
        if column is None:
            problems.append("One of the matches is not a field of this table. Choose again.")
            continue
        reason = why_not_column(store, info, column)
        if reason:
            problems.append(reason)
        elif name in seen:
            problems.append(f"{label(info, column)} is matched to more than one column. Choose one, and skip the other.")
        seen.add(name)
    for column in info.table.columns.values():
        if column.required and column.default is None and column.name not in seen \
                and why_not_column(store, info, column) is None:
            problems.append(f"Every row needs {label(info, column)}. Match one of the columns to it.")
    return problems


# ----- turning cells into values ----------------------------------------------------------------------------

def _key(text: str) -> str:
    return naming.PATH_SEPARATOR.join(" ".join(part.split()).casefold() for part in PATH_PARTS.split(text.strip()))


class LinkNames:
    """The names of the records a link column can point at, loaded once per table: full paths for nested places."""

    def __init__(self, store: Records):
        self.store, self._tables = store, {}

    def _load(self, target: TableInfo) -> tuple[dict, dict]:
        if target.name not in self._tables:
            conn, registry = self.store.conn, self.store.registry
            rows = {r["id"]: dict(r) for r in conn.execute(f"SELECT * FROM {target.name} WHERE deleted_at IS NULL")}
            style = dates.household_style(conn)
            own = {i: naming.record_name(conn, registry, target, r, style) for i, r in rows.items()}
            full, leaf = {}, {}
            for record_id, row in rows.items():
                path, seen, current = [], set(), row
                while current is not None and current["id"] not in seen and target.table.parent and len(path) < 12:
                    seen.add(current["id"])
                    path.append(own[current["id"]])
                    current = rows.get(current.get(target.table.parent))
                shown = naming.PATH_SEPARATOR.join(reversed(path)) if target.table.parent else own[record_id]
                full.setdefault(_key(shown), []).append((record_id, shown))
                leaf.setdefault(_key(own[record_id]), []).append((record_id, shown))
            self._tables[target.name] = (full, leaf)
        return self._tables[target.name]

    def find(self, target: TableInfo, text: str) -> int:
        """The id of the one record called `text`, or ValueError saying there is none or more than one."""
        full, leaf = self._load(target)
        found = full.get(_key(text)) or leaf.get(_key(text)) or []
        what = table_title(target).lower()
        if not found:
            hint = " Use the full path, like Kitchen › Pantry › Shelf 3." if target.table.parent else ""
            raise ValueError(f"has no match: there is nothing in {what} called “{text}”. Add it first, or fix the "
                             f"name.{hint}")
        if len(found) > 1:
            shown = "; ".join(sorted({s for _i, s in found})[:5])
            raise ValueError(f"“{text}” matches more than one: {shown}. Use the full path, or give them different "
                             f"names." if target.table.parent else
                             f"“{text}” matches more than one record in {what}. Give them different names first.")
        return found[0][0]


def _number(column: Column, text: str) -> str:
    if column.type == "money":
        text = CURRENCY.sub(r"\1", text)
    if "," in text and not THOUSANDS.match(text):
        raise ValueError("uses a comma. Write decimals with a full stop, like 1.5.")
    return text


def convert(store: Records, names: LinkNames, info: TableInfo, column: Column, cell: str, style: str):
    """The value the create path expects for one cell, or ValueError with a plain message. Text stays exactly
    as typed, even when it starts with = or +: it is kept as words, never worked out as a formula."""
    text = cell.replace("\r\n", "\n").replace("\r", "\n")
    if HIDDEN_CHARACTERS.search(text):
        raise ValueError("contains a hidden character, such as a tab. Remove it in your spreadsheet.")
    if column.type in ("text", "longtext"):
        return text
    text = text.strip()
    if column.type == "date":
        try:
            return dates.parse(text, style)
        except ValueError:
            raise ValueError(f"must be a date like {dates.show('2027-05-20', style)} or 2027-05-20.") from None
    if column.type in ("integer", "decimal", "measure", "money"):
        return _number(column, text)
    if column.type in ("link", "links"):
        target = store.registry[target_table(info.module.name, column)]
        if column.type == "link":
            return names.find(target, text)
        return sorted({names.find(target, part) for part in text.split(SEVERAL) if part.strip()})
    return text


def say(info: TableInfo, column_name: str, message: str) -> str:
    """"Use by must be a date like 20/05/27." from a field and its problem."""
    column = info.table.columns.get(column_name)
    if column is None:
        return message
    name = label(info, column)
    joiner = " " if message.startswith(QUESTION_WORDS) or name.endswith("?") else ": "
    return f"{name}{joiner}{message}"


def dry_run(store: Records, info: TableInfo, sheet: Sheet, mapping: list[str]) -> DryRun:
    """Check every row as if it were being added, keep nothing, and say which rows are ready and which need fixing.

    Rows that pass are checked together, in order (so a Stock out after a Stock in in the same file is fine)."""
    style = dates.household_style(store.conn)
    names = LinkNames(store)
    result, converted = DryRun(), []
    for number, cells in sheet.rows:
        values, problems = {}, []
        if any(cell.strip() for cell in cells[len(mapping):]):
            problems.append("This row has more cells than there are column headings.")
        for position, name in enumerate(mapping):
            cell = cells[position] if position < len(cells) else ""
            if not name or not cell.strip():
                continue
            column = info.table.columns[name]
            try:
                values[name] = convert(store, names, info, column, cell, style)
            except ValueError as error:
                problems.append(say(info, name, str(error)))
        if problems:
            result.problems.append((number, problems))
        else:
            converted.append((number, values))
    wrong = store.check_create([(info.name, values) for _n, values in converted], "person", starting_amounts=True)
    for position, (number, values) in enumerate(converted):
        if position in wrong:
            result.problems.append((number, [say(info, f, m) for f, m in wrong[position].items()]))
        else:
            result.ready.append((number, values))
    result.problems.sort()
    return result


def staged(info: TableInfo, run: DryRun) -> list[tuple[int, str, dict]]:
    """The ready rows in the shape proposals.stage_import keeps them."""
    return [(number, info.name, values) for number, values in run.ready]
