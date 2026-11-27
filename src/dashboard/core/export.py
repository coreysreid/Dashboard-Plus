"""Export my records: one zip with a spreadsheet file for every table, a manifest and a plain-words README."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from dashboard.core import fraud_guard, optional_links, reminder_moves
from dashboard.core.records import Records, TableInfo
from dashboard.core.schema import join_table_name, target_table
from dashboard.web import display

# A text cell starting with one of these can be run as a formula by a spreadsheet (decision 0078).
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
LIST_SEPARATOR = "; "  # between the names (or ids) of several linked records in one cell
PATH_SEPARATOR = " > "  # between the places of a nested record, in plain keyboard characters

README = """Your Dashboard Plus records, as spreadsheets
============================================

Made on {made} by Dashboard Plus {version}.

What this is
------------
A copy of your records that opens in Excel, Google Sheets, Numbers or LibreOffice.
It is NOT a backup: you cannot restore Dashboard Plus from it. Your backups are
the files in the "backups" folder inside your data folder (see Settings).

Keep it private
---------------
This file holds your household's details, such as names, phone numbers and where
things are kept. Anyone who can open it can read them. Do not email it or put it
in a shared folder. Details you marked private (such as medical notes or access
codes) are NOT in it, and neither are the program's keys and passwords.

What is in it
-------------
{files}
manifest.json lists every column: the heading used here and the name the
program uses inside, for people or programs that want exact names.

How the columns are written
---------------------------
- The first row of every file is the column headings, as they appear in Dashboard Plus.
- "ID" is the number Dashboard Plus gave the record. A column that points at another
  record shows its name (for a place inside a place, the whole path, such as
  "Kitchen > Pantry") and, in the column beside it called "... (id)", that record's ID.
  Names can repeat; an ID never does.
- A link into a list that is switched off keeps its "... (id)" so nothing is lost, and
  its name column only says that a link is saved. Switch that list on and export again
  to see the name. A link whose record is no longer there says so, with its old ID.
- A "Reminder" column appears where a reminder was moved between lists (for example
  from Vehicle insurance to Bills and insurance). It says which record reminds and
  gives the other record's ID. An earlier record that says "it does not remind" is
  kept with its history; it is not a second reminder.
- Dates are written year-month-day, like 2027-05-20, and times like 2027-05-20T14:35.
- Money is in whole units with two decimals, like 12.50 (not cents).
- Yes or no answers are written Yes or No.
- A choice is written as the words you see in Dashboard Plus.
- Amounts have no unit in the cell; the unit is in the heading, like "Weight (kg)".
- Files are UTF-8, so accents and other alphabets come through. If Excel shows odd
  letters, use Data > From Text/CSV and choose UTF-8.

A leading apostrophe
--------------------
A spreadsheet runs text that begins with = + - or @ as a formula. To stop that, any
text cell that begins with one of those characters (or with a tab or a line return)
has an apostrophe added at the front, like '=1+1. The apostrophe is not part of your
original text; take it off if you need the original. Numbers, dates and IDs are
never changed.

{deleted}
{left_out}"""


def _guard(text: str) -> str:
    """Keep a spreadsheet from running a text cell as a formula by putting an apostrophe in front."""
    return "'" + text if text.startswith(FORMULA_STARTS) else text


def _number(value) -> str:
    text = f"{Decimal(str(value)):f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _unique(headers: list[str]) -> list[str]:
    """Headings that never repeat inside one file, so each can be told from the others."""
    seen: dict[str, int] = {}
    out = []
    for header in headers:
        seen[header] = seen.get(header, 0) + 1
        out.append(header if seen[header] == 1 else f"{header} ({seen[header]})")
    return out


@dataclass
class Col:
    """One column of a file: its heading, the program's name for it and how to read its cell from a row."""
    heading: str
    key: str
    cell: Callable[[dict], object]
    unit: str | None = None
    choices: dict | None = None


class _Snapshot:
    """The rows of every table, read inside one read transaction, with names for links."""

    def __init__(self, conn: sqlite3.Connection, registry: dict[str, TableInfo]):
        self.conn, self.registry = conn, registry
        self.records = Records(conn, registry)
        self._rows: dict[str, dict[int, dict]] = {}
        self._names: dict[tuple[str, int], str] = {}

    def rows(self, info: TableInfo) -> dict[int, dict]:
        """Every row of a table, deleted ones too (a link may still point at one), by id."""
        if info.name not in self._rows:
            found = self.conn.execute(f"SELECT * FROM {info.name} ORDER BY id").fetchall()
            self._rows[info.name] = {r["id"]: dict(r) for r in found}
        return self._rows[info.name]

    def name_of(self, target: TableInfo, record_id) -> str:
        key = (target.name, int(record_id))
        if key not in self._names:
            rows = self.rows(target)
            row = rows.get(int(record_id))
            if row is None:
                name = ""
            elif target.table.parent:
                name = display.path_name(target, rows, row).replace(display.PATH_SEPARATOR, PATH_SEPARATOR)
            else:
                name = display.display_name(target, row, self.records)
            self._names[key] = name
        return self._names[key]

    def many(self, info: TableInfo, column, row: dict) -> list[int]:
        join = join_table_name(info.module.name, info.table.name, column.name)
        return [r[0] for r in self.conn.execute(
            f"SELECT to_id FROM {join} WHERE from_id = ? ORDER BY to_id", (row["id"],))]


def _value(column, value):
    """One stored value as a spreadsheet cell: ISO dates, money in whole units, Yes/No, choice words."""
    if value is None or value == "":
        return ""
    kind = column.type
    if kind == "boolean":
        return "Yes" if int(value) else "No"
    if kind == "money":
        return f"{Decimal(int(value)) / 100:.2f}"
    if kind in ("integer", "decimal", "measure"):
        return _number(value)
    if kind == "choice":
        return _guard(next((c.label for c in column.choices if c.key == value), str(value)))
    # text, longtext, date, datetime, file: dates and times stay as stored (ISO); a card number saved before
    # decision 0141 is written only as ••••1234
    return _guard(fraud_guard.mask_cards(str(value)))


def _optional_link_cols(snap: _Snapshot, info: TableInfo, column, label: str) -> list[Col]:
    """An optional link (decision 0115): its saved ID always, and a name only when its list is on and the record
    is there. A link into a list that is off says it is saved, unresolved, and never reads that list."""
    def ids(r):
        return [r[column.name]] if column.type == "link" else snap.many(info, column, r)

    def name(r):
        found = [i for i in ids(r) if i not in (None, "")]
        if not found:
            return ""
        state = optional_links.state(snap.conn, snap.registry, info, column, found[0])
        if state == optional_links.OFF:
            return _guard(display.optional_words(info, column, "kept"))
        target = snap.registry[target_table(info.module.name, column)]
        names = [snap.name_of(target, i) if optional_links.state(snap.conn, snap.registry, info, column, i)
                 == optional_links.LIVE else display.optional_words(info, column, "gone") for i in found]
        return _guard(LIST_SEPARATOR.join(names))
    return [Col(label, column.name, name),
            Col(f"{label} (id)", f"{column.name}:id",
                lambda r: LIST_SEPARATOR.join(str(i) for i in ids(r) if i not in (None, "")))]


def _link_cols(snap: _Snapshot, info: TableInfo, column, label: str) -> list[Col]:
    if column.optional:
        return _optional_link_cols(snap, info, column, label)
    target = snap.registry[target_table(info.module.name, column)]
    if column.type == "link":
        return [Col(label, column.name, lambda r: _guard(snap.name_of(target, r[column.name]))
                    if r[column.name] not in (None, "") else ""),
                Col(f"{label} (id)", f"{column.name}:id", lambda r: r[column.name] if r[column.name] not in (None, "") else "")]
    return [Col(label, column.name, lambda r: _guard(LIST_SEPARATOR.join(snap.name_of(target, i) for i in snap.many(info, column, r)))),
            Col(f"{label} (id)", f"{column.name}:id", lambda r: LIST_SEPARATOR.join(str(i) for i in snap.many(info, column, r)))]


def _table_file(snap: _Snapshot, info: TableInfo, include_deleted: bool) -> tuple[bytes, dict]:
    """The CSV for one table and what the manifest says about it. Private columns are never touched."""
    cols = [Col("ID", "id", lambda r: r["id"])]
    private = []
    for column in info.table.columns.values():
        label = display.column_label(info, column)
        if column.sensitive:
            private.append(label)
        elif column.type in ("link", "links"):
            cols += _link_cols(snap, info, column, label)
        else:
            measured = column.unit and column.type in ("integer", "decimal", "measure")
            cols.append(Col(f"{label} ({column.unit})" if measured else label, column.name,
                            lambda r, c=column: _value(c, r[c.name]), column.unit if measured else None,
                            {c.key: c.label for c in column.choices} if column.type == "choice" else None))
    moves = {}  # one reminder per policy (decision 0117): say which record reminds, by ID
    for move in reminder_moves.all_moves(snap.conn):
        if move["source_table"] == info.name:
            moves[move["source_id"]] = move
        elif move["target_table"] == info.name and move["target_id"] is not None:
            moves[move["target_id"]] = move
    if moves:
        titles = {name: display.table_title(other) for name, other in snap.registry.items()}
        cols.append(Col("Reminder", "reminder_move", lambda r: _guard(reminder_moves.export_words(
            moves[r["id"]], info.name, titles)) if r["id"] in moves else ""))
    cols += [Col("Created", "created_at", lambda r: r["created_at"]),
             Col("Last changed", "updated_at", lambda r: r["updated_at"])]
    if include_deleted:
        cols.append(Col("Deleted on", "deleted_at", lambda r: r["deleted_at"] or ""))
    headings = _unique([c.heading for c in cols])
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow([_guard(h) for h in headings])
    count = 0
    for row in snap.rows(info).values():
        if row["deleted_at"] and not include_deleted:
            continue
        writer.writerow([c.cell(row) for c in cols])
        count += 1
    described = [{"heading": h, "key": c.key, **({"unit": c.unit} if c.unit else {}),
                  **({"choices": c.choices} if c.choices else {})} for h, c in zip(headings, cols)]
    return out.getvalue().encode("utf-8-sig"), {"rows": count, "columns": described, "left_out_as_private": private}


def build(conn: sqlite3.Connection, registry: dict[str, TableInfo], app_version: str,
          include_deleted: bool = False, now: datetime | None = None) -> bytes:
    """The export as the bytes of one zip file, read from one consistent moment in the database."""
    made = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    files: dict[str, bytes] = {}
    tables, modules, private_tables = [], {}, []
    conn.execute("BEGIN")  # one read transaction: every table is read as of the same instant
    try:
        snap = _Snapshot(conn, registry)
        for info in registry.values():
            modules[info.module.name] = info.module
            if info.table.private:  # private history, such as medicine doses, is never written here (0120)
                private_tables.append(display.table_title(info))
                continue
            data, facts = _table_file(snap, info, include_deleted)
            files[f"{info.name}.csv"] = data
            tables.append({"file": f"{info.name}.csv", "module": info.module.name, "table": info.table.name,
                           "title": display.table_title(info), **facts})
    finally:
        conn.execute("ROLLBACK")
    manifest = {
        "app": "Dashboard Plus", "app_version": app_version, "created": made.isoformat(),
        "includes_deleted_records": include_deleted,
        "modules": [{"name": m.name, "title": m.title, "version": m.version} for m in modules.values()],
        "tables": tables,
        "private_columns": "Columns marked private are left out of every file; each table lists them above by label only.",
        "private_tables_left_out": private_tables,
        "formula_guard": "A text cell starting with = + - @, a tab or a line return has an apostrophe added in front.",
    }
    listing = "".join(f"- {t['file']}: {t['title']} ({t['rows']} record{'' if t['rows'] == 1 else 's'})\n" for t in tables)
    listing += "- manifest.json: the same list for programs, with every column\n"
    left_out = [(t["title"], t["left_out_as_private"]) for t in tables if t["left_out_as_private"]]
    notes = ("Left out because they are private:\n" + "".join(f"- {title}: {', '.join(labels)}\n" for title, labels in left_out)
             if left_out else "Nothing private was left out because no table has private columns.\n")
    if private_tables:
        notes += ("Whole lists left out because every record in them is private history: "
                  + ", ".join(private_tables) + ". They stay in Dashboard Plus and in your backups.\n")
    deleted = ("Deleted records are included, with the date each was deleted in the \"Deleted on\" column.\n"
               if include_deleted else "Records you deleted are not included.\n")
    readme = README.format(made=f"{made.day} {made:%B %Y at %H:%M} UTC", version=app_version, files=listing,
                           deleted=deleted, left_out=notes)
    stamp = max((made.year, made.month, made.day, made.hour, made.minute, made.second), (1980, 1, 1, 0, 0, 0))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in [("README.txt", readme.encode("utf-8")),
                              ("manifest.json", json.dumps(manifest, indent=1, ensure_ascii=False).encode("utf-8")),
                              *sorted(files.items())]:
            entry = zipfile.ZipInfo(name, date_time=stamp)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o600 << 16
            archive.writestr(entry, content)
    return buffer.getvalue()
