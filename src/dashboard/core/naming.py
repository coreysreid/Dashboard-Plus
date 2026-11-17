"""What to call a record wherever it appears: its name, or for a batch "Kidney beans, 3 tins".

A table names its records by its first required text column (or any text column; never a
private one). A table with no name of its own, such as batches of a stock item, can declare
`record_name = "{item}, {quantity}[ {item.unit}][ at {place}]"` (DESIGN.md 5.7).
"""
from __future__ import annotations

import re
import sqlite3
import string
from decimal import Decimal

from dashboard.core import dates
from dashboard.core.schema import target_table

PATH_SEPARATOR = " › "


def name_column(info):
    """The column that best names a record: a required text column, else any text column; never a private one."""
    texts = [c for c in info.table.columns.values() if c.type == "text" and not c.sensitive]
    required = [c for c in texts if c.required]
    return (required or texts or [None])[0]


def plain_number(value) -> str:
    text = f"{Decimal(str(value)):f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def record_name(conn: sqlite3.Connection, registry: dict, info, row, style: str | None = None,
                depth: int = 0, leave_out=()) -> str:
    """A short human name for a record. `row` is a dict or sqlite Row.

    `leave_out` drops optional parts that mention those columns, so a use-by warning need
    not repeat the date it is already about."""
    row = dict(row)
    if info.table.record_name and depth < 3:
        return _from_template(conn, registry, info, row, style, depth, leave_out)
    column = name_column(info)
    value = row.get(column.name) if column else None
    return str(value) if value not in (None, "") else f"{info.table.title} #{row['id']}"


def _linked(conn, registry, info, column, record_id):
    target = registry.get(target_table(info.module.name, column))
    if target is None or record_id in (None, ""):
        return None, None
    found = conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (record_id,)).fetchone()
    return target, (dict(found) if found else None)


def _path(conn, registry, info, row, style, depth) -> str:
    """"Kitchen › Pantry › Shelf 3" for a nested record."""
    names, seen = [], set()
    while row is not None and row["id"] not in seen and len(names) < 12:
        seen.add(row["id"])
        names.append(record_name(conn, registry, info, row, style, depth + 1))
        parent = row.get(info.table.parent)
        row = conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (parent,)).fetchone() if parent else None
        row = dict(row) if row else None
    return PATH_SEPARATOR.join(reversed(names))


def _from_template(conn, registry, info, row, style, depth, leave_out=()) -> str:
    """Fill in "{quantity} {item.unit} of {item}[ at {place}]": a part in [square brackets] is
    left out when any column it mentions is blank."""
    style = style or dates.household_style(conn)
    template = info.table.record_name

    def fill(text: str) -> str | None:
        out = text
        for _, field_spec, _, _ in string.Formatter().parse(text):
            if not field_spec:
                continue
            link, _, field_name = field_spec.partition(".")
            column = info.table.columns[link]
            if field_name:
                target, linked = _linked(conn, registry, info, column, row.get(link))
                value = _text(conn, registry, target, target.table.columns[field_name], linked.get(field_name),
                              style, depth) if linked else ""
            else:
                value = _text(conn, registry, info, column, row.get(link), style, depth)
            out = out.replace("{" + field_spec + "}", value)
        return out

    def optional(match) -> str:
        part = match.group(1)
        fields = [f for _, f, _, _ in string.Formatter().parse(part) if f]
        if any(f.partition(".")[0] in leave_out for f in fields):
            return ""
        filled = [fill("{" + f + "}") for f in fields]
        return "" if any(v == "" for v in filled) else fill(part)

    text = fill(re.sub(r"\[([^\]]*)\]", optional, template))
    return " ".join(text.split()) or f"{info.table.title} #{row['id']}"


def _text(conn, registry, info, column, value, style, depth) -> str:
    if value in (None, ""):
        return ""
    if column.type == "link":
        target, linked = _linked(conn, registry, info, column, value)
        if linked is None:
            return ""
        if target.table.parent:
            return _path(conn, registry, target, linked, style, depth)
        return record_name(conn, registry, target, linked, style, depth + 1)
    if column.type in ("decimal", "measure", "integer"):
        return plain_number(value)
    if column.type == "date":
        return dates.show(value, style)
    if column.type == "choice":
        return next((c.label for c in column.choices if c.key == value), str(value))
    return str(value)
