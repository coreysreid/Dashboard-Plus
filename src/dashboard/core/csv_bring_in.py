"""Bring in earlier entries: a person's own spreadsheet of a dated log, checked row by row, added at once with one Undo.

Decision 0137. A table opts in with `[tables.<t>.bring_in]` (`when` and `per`, checked at module load). Unlike
Import from a spreadsheet (decision 0080), rows do not wait on Review: the person has already looked at every row on
the preview, so the accepted rows are added in one transaction with a history entry each, and one Undo removes
exactly those rows again. Only a person's own pages reach this; a helper never can. Nothing here keeps the file:
it is read from text the caller holds in memory. A linked record (a pet, a person, a medicine) is never created:
it is matched by its exact name, ignoring capitals and extra spaces, or chosen by the person from existing ones.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from dashboard.core import csv_import, daily, dates, db, naming
from dashboard.core.modules import Column
from dashboard.core.proposals import HIDDEN_CHARACTERS
from dashboard.core.records import Records, TableInfo, ValidationError
from dashboard.core.schema import target_table
from dashboard.errors import PlainError

ACTION = "bring_in"  # the one history entry that lists what one bring-in added (record_id 0: the list as a whole)
UNDO_ACTION = "bring_in_undo"
PRIVATE_ACTOR = "import:earlier-entries"  # a private list's history never names the file
TIME = "@time"  # the mapping value for a separate time-of-day column, after the date-and-time field's name
SKIP = "skip"  # the person's choice to leave the rows with one unknown name out
_TIME = re.compile(r"(\d{1,2})(?:[:.](\d{2}))?(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?")
_NUMBER_UNIT = re.compile(r"^([+-]?[\d.,]+)\s*([^\d\s].*)?$")
_DATE_WORDS = {"date", "day", "when", "date and time", "datetime", "date time"}
_TIME_WORDS = {"time", "time of day", "at"}


class StaleOrChanged(PlainError):
    """The rows checked on the preview are no longer the rows that would be added."""


# ----- which lists, and which fields ---------------------------------------------------------------------

def offered(info: TableInfo) -> bool:
    return bool(info.table.bring_in)


def needs_show(info: TableInfo) -> bool:
    """Whether this list's values are private, so the person must press Show before choosing a file (0121, 0123)."""
    return info.table.private or any(c.sensitive or c.link_rule.get("shows") for c in info.table.columns.values())


def entry_words(info: TableInfo) -> tuple[str, str]:
    """("dose", "doses"): the list's own word for one entry, from its declaration or its daily or timeline words."""
    for rule in (info.table.bring_in, info.table.daily, info.table.timeline, info.table.calendar):
        words = (rule or {}).get("entry")
        if words:
            return words[0], words[1]
    return "entry", "entries"


def _why_not(store: Records, info: TableInfo, column: Column) -> str | None:
    if column.type == "file":
        return "files"
    if column.type in ("link", "links") and target_table(info.module.name, column) not in store.registry:
        return "off"
    if column.name in store._derived(info):
        return "worked out"
    return None  # a private column is fine: a list with one is reached only after Show (needs_show)


def fields(store: Records, info: TableInfo) -> list[Column]:
    """The fields a column can be matched to, in the order the add form shows them; private ones included, since a
    list with any is reached only after Show."""
    form = info.module.labels.get("tables", {}).get(info.table.name, {}).get("form") or []
    ordered = [info.table.columns[n] for n in form if n in info.table.columns]
    ordered += [c for c in info.table.columns.values() if c not in ordered]
    return [c for c in ordered if _why_not(store, info, c) is None]


def options(store: Records, info: TableInfo) -> list[tuple[str, str, bool]]:
    """(value, label, needed) for the match lists: each field, and "time of day only" after a date-and-time one."""
    found = []
    for column in fields(store, info):
        needed = column.required and column.default is None or column.name == info.table.bring_in["when"]
        found.append((column.name, csv_import.label(info, column), needed))
        if column.type == "datetime":
            found.append((column.name + TIME, f"{csv_import.label(info, column)}: time of day only", False))
    return found


def auto_match(store: Records, info: TableInfo, headers: list[str]) -> list[str]:
    """A field for each heading by its label or key (as decision 0080), plus "Date" and "Time" for the list's own
    date and time; each field is matched once and "" skips a column."""
    when = info.table.columns[info.table.bring_in["when"]]
    by_words = {}
    for value, text, _needed in options(store, info):
        if not value.endswith(TIME):
            by_words.setdefault(csv_import._words(value), value)
        by_words.setdefault(csv_import._words(text), value)
    chosen, taken = [], set()
    for header in headers:
        words = csv_import._words(header)
        name = by_words.get(words, "")
        if not name and words in _DATE_WORDS:
            name = when.name
        if not name and words in _TIME_WORDS and when.type == "datetime":
            name = when.name + TIME
        if name in taken:
            name = ""
        taken.add(name)
        chosen.append(name)
    return chosen


def mapping_problems(store: Records, info: TableInfo, mapping: list[str]) -> list[str]:
    """What is wrong with the matches as a whole: an unknown or doubled field, a needed field not matched."""
    allowed = {value: text for value, text, _n in options(store, info)}
    problems, seen = [], set()
    for name in mapping:
        if not name:
            continue
        if name not in allowed:
            problems.append("One of the matches is not a field of this list. Choose again.")
        elif name in seen:
            problems.append(f"{allowed[name]} is matched to more than one column. Choose one, and skip the other.")
        seen.add(name)
    for value, text, needed in options(store, info):
        if needed and value not in seen:
            problems.append(f"Every row needs {text}. Match one of the columns to it.")
    return problems


# ----- reading one cell --------------------------------------------------------------------------------------

def parse_time(text: str) -> tuple[int, int, int]:
    """(hour, minute, second) from "8:00", "8:00 am", "8am", "20:15" or "8.30 pm", or ValueError."""
    found = _TIME.fullmatch(text.strip().lower())
    if not found:
        raise ValueError
    hour, minute, second, half = found.groups()
    hour, minute, second = int(hour), int(minute or 0), int(second or 0)
    if half:
        if not 1 <= hour <= 12:
            raise ValueError
        hour = hour % 12 + (12 if half.startswith("p") else 0)
    elif found.group(2) is None:
        raise ValueError  # a bare "8" could be a count, not a time
    if hour > 23 or minute > 59 or second > 59:
        raise ValueError
    return hour, minute, second


def parse_when(text: str, time_text: str, style: str) -> str:
    """The stored form of a date and time: 2026-03-04T08:00, kept as the household's own local time when it has no
    offset (decision 0110), or with its offset kept (an instant) when the spreadsheet gives one. ValueError if not."""
    example = f"{dates.show('2027-05-20', style)} 8:00 am"
    text, time_text = text.strip(), (time_text or "").strip()
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}[T ]\d", text):
        if time_text:
            raise ValueError("has a time in two columns. Keep the time in one of them.")
        try:
            return datetime.fromisoformat(text).isoformat(timespec="minutes")
        except ValueError:
            raise ValueError(f"must be a date and time like {example} or 2027-05-20 08:00.") from None
    day_text, _, rest = text.partition(" ")
    try:
        day = dates.parse(day_text, style)
    except ValueError:
        raise ValueError(f"must be a date and time like {example}.") from None
    rest = rest.strip()
    if rest and time_text:
        raise ValueError("has a time in two columns. Keep the time in one of them.")
    if not (rest or time_text):
        raise ValueError("has a date but no time. Add the time, like 8:00 am, or match a column to the time of day.")
    try:
        hour, minute, second = parse_time(rest or time_text)
    except ValueError:
        raise ValueError("has a time that could not be read. Write it like 8:00 am or 20:00.") from None
    return f"{day}T{hour:02d}:{minute:02d}" + (f":{second:02d}" if second else "")


def _number(column: Column, text: str) -> str:
    """A number cell, with the column's own unit allowed after it ("21.3 kg"); another unit is never converted."""
    found = _NUMBER_UNIT.match(text)
    if found and found.group(2) and column.type != "money":
        unit = found.group(2).strip()
        if column.unit and unit.casefold() == column.unit.casefold():
            text = found.group(1)
        elif column.unit:
            raise ValueError(f"is in {unit}, and this list records {column.unit}. Nothing is converted: change it in "
                             f"your spreadsheet, or leave this row out.")
    return csv_import._number(column, text)


def _unit_in_amount(info: TableInfo, column: Column, text: str, mapping: list[str], values: dict) -> None:
    """"120g" or "0.5 pouch" in an amount cell, when the list has a unit field that no column was matched to: the
    unit must be one of the list's own units, and is never converted (decision 0144)."""
    rule = info.table.daily or {}
    unit_column = info.table.columns.get(rule.get("unit", ""))
    if rule.get("amount") != column.name or unit_column is None or not unit_column.choices \
            or unit_column.name in mapping:
        return
    found = _NUMBER_UNIT.match(text)
    if not found or not found.group(2):
        return
    unit = found.group(2).strip()
    words = [c.key for c in unit_column.choices]
    chosen = next((w for w in words if w.casefold() == unit.casefold()), None)
    if chosen is None:
        raise ValueError(f"has “{text}”, and “{unit}” is not one of this list's units ({', '.join(words)}). Nothing "
                         f"is converted: change it in your spreadsheet, or leave this row out.")
    values[column.name] = found.group(1)
    values[unit_column.name] = chosen


def _not_after_today(store: Records, column: Column, value: str, zone) -> bool:
    """Whether an earlier entry's date, or date and time, is not later than the household's today."""
    if column.type == "date":
        return str(value)[:10] <= daily.today(store.conn).isoformat()
    return daily.local(value, zone).isoformat(timespec="minutes") <= daily.now_text(store.conn)


def _key(text: str) -> str:
    return " ".join(str(text or "").split()).casefold()


def _when_key(value: str, column: Column, zone) -> str:
    """The moment two entries are compared by: the household's own minute for a time, the day for a date."""
    if column.type == "date":
        return str(value)[:10]
    return daily.local(value, zone).isoformat(timespec="minutes")


# ----- names of linked records -------------------------------------------------------------------------------

@dataclass
class Pick:
    """A name in the file that matched no record, or more than one: the person chooses one, or leaves its rows out."""
    key: str
    column: str
    label: str
    text: str
    context: str  # "for Rosa Garcia" when the choice depends on the row's own person
    candidates: list[tuple[int, str]]
    rows: list[int] = field(default_factory=list)
    several: bool = False  # True: the name matched more than one record
    chosen: str = ""


class Names:
    """Finds linked records by their exact name (ignoring capitals and spaces), and lists those a person may choose."""

    def __init__(self, store: Records):
        self.store = store
        self.links = csv_import.LinkNames(store)
        self.style = dates.household_style(store.conn)

    def target(self, info: TableInfo, column: Column) -> TableInfo:
        return self.store.registry[target_table(info.module.name, column)]

    def ruled(self, info: TableInfo, column: Column, values: dict) -> list[dict]:
        """The records a `link_rule` allows for this row (decision 0120): its `where` choices and `same` links."""
        target, rule = self.target(info, column), column.link_rule
        clauses, params = ["deleted_at IS NULL"], []
        for name, value in rule.get("where", {}).items():
            clauses.append(f"{name} = ?")
            params.append(value)
        for theirs, mine in rule.get("same", {}).items():
            clauses.append(f"{theirs} = ?")
            params.append(values.get(mine))
        return [dict(r) for r in self.store.conn.execute(
            f"SELECT * FROM {target.name} WHERE {' AND '.join(clauses)} ORDER BY id", params)]

    def words(self, info: TableInfo, column: Column, row: dict) -> str:
        """What a candidate is called on the choice list: its private words for a `shows` rule (only ever after
        Show), else its usual name."""
        shows = column.link_rule.get("shows")
        target = self.target(info, column)
        if shows:
            return f"{str(row.get(shows) or '').strip()} (#{row['id']})"
        return naming.record_name(self.store.conn, self.store.registry, target, row, self.style)

    def candidates(self, info: TableInfo, column: Column, values: dict) -> list[tuple[int, str]]:
        if column.link_rule:
            rows = self.ruled(info, column, values)
        else:
            target = self.target(info, column)
            rows = [dict(r) for r in self.store.conn.execute(
                f"SELECT * FROM {target.name} WHERE deleted_at IS NULL ORDER BY id")]
        return [(r["id"], self.words(info, column, r)) for r in rows]

    def find(self, info: TableInfo, column: Column, values: dict, text: str) -> list[int]:
        """The ids of the records with exactly this name (for a `shows` rule, these private words)."""
        shows = column.link_rule.get("shows")
        if shows:
            return [r["id"] for r in self.ruled(info, column, values) if _key(r.get(shows)) == _key(text)]
        full, leaf = self.links._load(self.target(info, column))
        found = full.get(csv_import._key(text)) or leaf.get(csv_import._key(text)) or []
        ids = sorted({record_id for record_id, _shown in found})
        if column.link_rule:
            allowed = {r["id"] for r in self.ruled(info, column, values)}
            ids = [i for i in ids if i in allowed]
        return ids


def pick_key(column: str, context: str, text: str) -> str:
    """A short, stable name for one choice, the same however the file's rows are ordered."""
    return hashlib.sha256(f"{column}\n{context}\n{_key(text)}".encode("utf-8")).hexdigest()[:12]


# ----- the plan ---------------------------------------------------------------------------------------------

@dataclass
class Row:
    number: int
    values: dict
    duplicate: str | None = None  # "the same pet and time as row 4" or "already recorded"


@dataclass
class Plan:
    """What pressing Bring in would do: rows ready, rows that need fixing, choices to make and dates to confirm."""
    ready: list[Row] = field(default_factory=list)
    problems: list[tuple[int, list[str]]] = field(default_factory=list)
    picks: list[Pick] = field(default_factory=list)
    unclear: dict[int, list[str]] = field(default_factory=dict)
    left_out: list[int] = field(default_factory=list)  # rows left out by the person's own choice

    def chosen(self, add_anyway: set[int]) -> list[Row]:
        """The rows to add: every ready row, and a possible repeat only when the person ticked Add anyway."""
        return [r for r in self.ready if r.duplicate is None or r.number in add_anyway]


def actor(info: TableInfo, file_label: str) -> str:
    """Who each entry's history names: the file for an ordinary list, never for a private one."""
    if needs_show(info):
        return PRIVATE_ACTOR
    from dashboard.core.proposals import import_actor
    return import_actor(file_label)


def plan(store: Records, info: TableInfo, sheet: csv_import.Sheet, mapping: list[str], picks: dict[str, str],
         file_label: str) -> Plan:
    """Check every row as if it were being added, keep nothing, and say what would happen.

    Each cell is read the household's way (dates, numbers with the column's own unit, a time of day); each linked
    record is found by its exact name or the person's choice in `picks` (key -> record id or "skip"); the rows that
    pass are then tried together through the real create path and rolled back. Ready rows with the same subject and
    the same moment as an entry already recorded, or as an earlier row of the file, are marked as possible repeats."""
    rule = info.table.bring_in
    when_column, per_column = info.table.columns[rule["when"]], info.table.columns[rule["per"]]
    style, zone = dates.household_style(store.conn), daily.household_zone(store.conn)
    names = Names(store)
    result = Plan()
    found_picks: dict[str, Pick] = {}
    time_at = next((i for i, m in enumerate(mapping) if m == when_column.name + TIME), None)
    columns = [(i, info.table.columns[m]) for i, m in enumerate(mapping) if m and not m.endswith(TIME)]
    columns.sort(key=lambda pair: bool(pair[1].link_rule))  # a rule's own link (the person) is read first
    converted = []
    for number, cells in sheet.rows:
        cell = lambda i: cells[i] if i is not None and i < len(cells) else ""  # noqa: E731
        values, problems, waiting, skipped = {}, [], False, False
        if any(c.strip() for c in cells[len(mapping):]):
            problems.append("This row has more cells than there are column headings.")
        for position, column in columns:
            text = cell(position).replace("\r\n", "\n").replace("\r", "\n")
            if column.type not in ("text", "longtext"):
                text = text.strip()
            name = csv_import.label(info, column)
            if not text.strip():
                if column is when_column:  # decision 0144: an entry's date is never filled in as today
                    problems.append(f"{name} is empty. Every earlier entry needs its own "
                                    f"{'date' if when_column.type == 'date' else 'date and time'}; it is never "
                                    f"filled in as today.")
                continue
            if HIDDEN_CHARACTERS.search(text) or (column.name == when_column.name and HIDDEN_CHARACTERS.search(
                    cell(time_at))):
                problems.append(f"{name}: contains a hidden character, such as a tab. Remove it in your spreadsheet.")
                continue
            try:
                if column.type == "datetime":
                    values[column.name] = parse_when(text, cell(time_at) if column is when_column else "", style)
                    reading = dates.ambiguous(text.partition(" ")[0], style)
                    if reading:
                        result.unclear.setdefault(number, []).append(
                            csv_import.unclear_date_text(name, text.partition(" ")[0], reading, style))
                elif column.type == "date":
                    values[column.name] = csv_import.convert(store, None, info, column, text, style)
                    reading = dates.ambiguous(text, style)
                    if reading:
                        result.unclear.setdefault(number, []).append(
                            csv_import.unclear_date_text(name, text, reading, style))
                elif column.type in ("integer", "decimal", "measure", "money"):
                    values[column.name] = _number(column, text)
                    _unit_in_amount(info, column, text, mapping, values)
                elif column.type == "link":
                    outcome = _link(names, info, column, values, text, picks, found_picks, number)
                    if outcome == SKIP:
                        skipped = True
                    elif outcome is None:
                        waiting = True
                    else:
                        values[column.name] = outcome
                elif column.type == "links":
                    ids = []
                    for part in (p for p in text.split(csv_import.SEVERAL) if p.strip()):
                        outcome = _link(names, info, column, values, part.strip(), picks, found_picks, number)
                        if outcome == SKIP:
                            skipped = True
                        elif outcome is None:
                            waiting = True
                        else:
                            ids.append(outcome)
                    values[column.name] = sorted(set(ids))
                else:
                    values[column.name] = text
            except ValueError as error:
                problems.append(csv_import.say(info, column.name, str(error)))
        if skipped:
            result.left_out.append(number)
            continue
        if when_column.name in values and not _not_after_today(store, when_column, values[when_column.name], zone):
            shown = dates.show(str(values[when_column.name])[:10], style)
            problems.append(f"{shown} is after today. Earlier entries must be on or before today: check the date "
                            f"order.")
        if waiting:
            problems.append("A name in this row needs your choice under “Names to match” above, or leave its rows out.")
        if problems:
            result.problems.append((number, problems))
        else:
            converted.append((number, values))
    result.picks = list(found_picks.values())
    who = actor(info, file_label)
    wrong = store.check_create([(info.name, v) for _n, v in converted], who) if converted else {}
    seen: dict[tuple, int] = {}
    known = _recorded(store, info, when_column, per_column, zone)
    for position, (number, values) in enumerate(converted):
        if position in wrong:
            result.problems.append((number, [csv_import.say(info, f, m).strip() if f else m
                                             for f, m in wrong[position].items()]))
            continue
        row = Row(number, values)
        moment = (values.get(per_column.name), _when_key(values[when_column.name], when_column, zone))
        word = entry_words(info)[0]
        if moment in known:
            row.duplicate = f"A {word} with the same {csv_import.label(info, per_column).lower()} and the same " \
                            f"{'day' if when_column.type == 'date' else 'time'} is already recorded."
        elif moment in seen:
            row.duplicate = f"Row {seen[moment]} has the same {csv_import.label(info, per_column).lower()} and the " \
                            f"same {'day' if when_column.type == 'date' else 'time'}."
        seen.setdefault(moment, number)
        result.ready.append(row)
    result.problems.sort()
    result.unclear = {n: t for n, t in result.unclear.items() if any(r.number == n for r in result.ready)}
    return result


def _link(names: Names, info: TableInfo, column: Column, values: dict, text: str, picks: dict, found: dict,
          number: int):
    """One linked record's id, SKIP when the person left its rows out, or None while it waits for their choice."""
    ids = names.find(info, column, values, text)
    if len(ids) == 1:
        return ids[0]
    context = ""
    same = column.link_rule.get("same", {})
    if same:
        subject = next(iter(same.values()))
        subject_column = info.table.columns[subject]
        if values.get(subject) is None:
            return None  # the person is not known yet; that row already waits for them
        target = names.target(info, subject_column)
        row = names.store.conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (values[subject],)).fetchone()
        context = f"for {naming.record_name(names.store.conn, names.store.registry, target, dict(row), names.style)}"
    key = pick_key(column.name, f"{context}#{values.get(next(iter(same.values()))) if same else ''}", text)
    pick = found.get(key)
    if pick is None:
        candidates = names.candidates(info, column, values)
        pick = Pick(key, column.name, csv_import.label(info, column), text.strip(), context, candidates,
                    several=len(ids) > 1)
        if len(ids) > 1:
            pick.candidates = [c for c in candidates if c[0] in ids]
        found[key] = pick
    pick.rows.append(number)
    chosen = picks.get(key, "")
    if chosen == SKIP:
        pick.chosen = SKIP
        return SKIP
    if chosen.isdigit() and int(chosen) in {c[0] for c in pick.candidates}:
        pick.chosen = chosen
        return int(chosen)
    return None


def _recorded(store: Records, info: TableInfo, when: Column, per: Column, zone) -> set[tuple]:
    """(subject, moment) of every entry already in the list, to find possible repeats."""
    found = set()
    for row in store.conn.execute(f"SELECT {per.name}, {when.name} FROM {info.name} WHERE deleted_at IS NULL"):
        if row[1]:
            try:
                found.add((row[0], _when_key(row[1], when, zone)))
            except ValueError:
                continue
    return found


def fingerprint(info: TableInfo, text: str, mapping: list[str], picks: dict, add: set[int], dates_ok: bool) -> str:
    """What the person saw on the preview: the file, the matches, their choices and ticks."""
    parts = [info.name, text, *mapping, *sorted(f"{k}={v}" for k, v in picks.items() if v),
             *sorted(str(n) for n in add), "dates" if dates_ok else ""]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


# ----- adding, and Undo -----------------------------------------------------------------------------------

def by_operation(store: Records, info: TableInfo, operation: str) -> dict | None:
    """The bring-in a page's one-use operation number already saved, or None: a second press adds nothing."""
    row = store.conn.execute("SELECT id, at, after FROM core__audit WHERE action = ? AND table_name = ? AND "
                             "json_extract(after, '$.operation') = ?", (ACTION, info.name, operation)).fetchone()
    return {"id": row["id"], "at": row["at"], **json.loads(row["after"])} if row else None


def add(store: Records, info: TableInfo, rows: list[Row], file_label: str, operation: str) -> int:
    """Add every chosen row in one transaction, each through the ordinary create path with its own history entry,
    and one history entry for the whole bring-in. Returns that entry's id. Pressing twice adds them once."""
    if not offered(info):
        raise PlainError("This list does not bring in earlier entries.")
    who = actor(info, file_label)
    with db.transaction(store.conn):
        earlier = by_operation(store, info, operation)
        if earlier is not None:
            return earlier["id"]
        try:
            ids = [store.create_in(info.name, row.values, who) for row in rows]
        except ValidationError:
            raise StaleOrChanged("Your records changed since the rows were checked. Nothing was added. "
                                 "Here is the new check.") from None
        store._audit("person", ACTION, info, 0, None,
                     {"operation": operation, "ids": ids, "count": len(ids),
                      "file": "" if needs_show(info) else file_label})
        return store.conn.execute("SELECT MAX(id) FROM core__audit WHERE action = ?", (ACTION,)).fetchone()[0]


def summary(store: Records, info: TableInfo, audit_id: int) -> dict | None:
    """One bring-in as saved: when, how many, the file's name (blank for a private list), its ids, and whether it
    was undone."""
    row = store.conn.execute("SELECT id, at, after FROM core__audit WHERE id = ? AND action = ? AND table_name = ?",
                             (audit_id, ACTION, info.name)).fetchone()
    if row is None:
        return None
    found = {"id": row["id"], "at": row["at"], **json.loads(row["after"])}
    found["undone"] = store.conn.execute("SELECT 1 FROM core__audit WHERE action = ? AND table_name = ? AND "
                                         "json_extract(after, '$.bring_in') = ?",
                                         (UNDO_ACTION, info.name, audit_id)).fetchone() is not None
    return found


def recent(store: Records, info: TableInfo, limit: int = 5) -> list[dict]:
    """The latest bring-ins into this list, newest first."""
    ids = [r[0] for r in store.conn.execute("SELECT id FROM core__audit WHERE action = ? AND table_name = ? "
                                            "ORDER BY id DESC LIMIT ?", (ACTION, info.name, limit))]
    return [summary(store, info, i) for i in ids]


def undo_problem(store: Records, info: TableInfo, found: dict) -> str | None:
    """Why Undo would not remove exactly what was brought in, or None when it can."""
    if found["undone"]:
        return "This was already undone."
    changed = 0
    for record_id in found["ids"]:
        later = store.conn.execute("SELECT 1 FROM core__audit WHERE table_name = ? AND record_id = ? AND id > ? "
                                   "LIMIT 1", (info.name, record_id, found["id"])).fetchone()
        changed += later is not None
    if changed:
        many = entry_words(info)[1] if changed != 1 else entry_words(info)[0]
        return (f"{changed} of these {many} {'was' if changed == 1 else 'were'} changed or deleted since, so Undo "
                f"would not put things back exactly. Change or delete entries one by one instead.")
    return None


def undo(store: Records, info: TableInfo, audit_id: int, actor_name: str = "person") -> int:
    """Remove every entry one bring-in added, in one transaction (each kept in history and restorable, as every
    delete is). Refused, changing nothing, if any of them changed since or it was already undone."""
    with db.transaction(store.conn):
        found = summary(store, info, audit_id)
        if found is None:
            raise PlainError("That bring-in could not be found.")
        problem = undo_problem(store, info, found)
        if problem:
            raise PlainError(problem)
        for record_id in found["ids"]:
            store._delete(info, record_id, actor_name, set(), f"{info.name}:{record_id}")
        store._audit(actor_name, UNDO_ACTION, info, 0, None, {"bring_in": audit_id, "count": len(found["ids"])})
    return len(found["ids"])
