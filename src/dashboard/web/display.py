"""Turn declared tables and stored values into friendly labels, form fields and text."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dashboard.core.modules import Column
from dashboard.core.records import Records, TableInfo
from dashboard.core.schema import target_table

LIST_COLUMN_LIMIT = 6
OPTION_LIMIT = 500


def _labels(info: TableInfo) -> dict:
    return info.module.labels.get("tables", {}).get(info.table.name, {})


def table_title(info: TableInfo) -> str:
    """The friendly name of a table, from labels.toml if it gives one."""
    return _labels(info).get("title") or info.table.title


def empty_hint(info: TableInfo) -> str | None:
    """What to do first when this table has no records yet, from labels.toml."""
    return _labels(info).get("empty")


def column_label(info: TableInfo, column: Column) -> str:
    """The friendly name of a column."""
    label = _labels(info).get("columns", {}).get(column.name, {}).get("label")
    return label or column.name.replace("_", " ").capitalize()


def column_help(info: TableInfo, column: Column) -> str | None:
    """The help text shown under a field."""
    return _labels(info).get("columns", {}).get(column.name, {}).get("help") or column.help


def form_columns(info: TableInfo) -> list[Column]:
    """Columns in the order the form should show them.

    labels.toml's `form` sets the order; any required column it leaves out is
    added at the end, so a form can never be impossible to save.
    """
    columns = info.table.columns
    order = _labels(info).get("form")
    if not order:
        return list(columns.values())
    chosen = [columns[name] for name in order if name in columns]
    chosen += [c for c in columns.values() if c.required and c not in chosen]
    return chosen


def list_columns(info: TableInfo) -> list[Column]:
    """Columns shown in the grid: labels.toml's `list`, or the first few short ones."""
    columns = info.table.columns
    order = _labels(info).get("list")
    if order:
        return [columns[name] for name in order if name in columns]
    short = [c for c in columns.values() if c.type not in ("longtext", "links", "file")]
    return short[:LIST_COLUMN_LIMIT]


def name_column(info: TableInfo) -> Column | None:
    """The column that best names a record: a required text column, else any text column."""
    texts = [c for c in info.table.columns.values() if c.type == "text"]
    required = [c for c in texts if c.required]
    return (required or texts or [None])[0]


def display_name(info: TableInfo, row: dict) -> str:
    """A short human name for a record, used wherever another record links to it."""
    column = name_column(info)
    value = row.get(column.name) if column else None
    return str(value) if value not in (None, "") else f"{table_title(info)} #{row['id']}"


def money_text(cents) -> str:
    return f"{Decimal(int(cents)) / 100:,.2f}"


def _number_text(value) -> str:
    number = Decimal(str(value))
    text = f"{number:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


class Formatter:
    """Formats values for display, looking up linked records once per page."""

    def __init__(self, records: Records):
        self.records = records
        self._names: dict[tuple[str, int], str] = {}

    def target(self, info: TableInfo, column: Column) -> TableInfo:
        return self.records.registry[target_table(info.module.name, column)]

    def link_name(self, target: TableInfo, record_id) -> str:
        key = (target.name, int(record_id))
        if key not in self._names:
            try:
                row = self.records.get(target.name, int(record_id), include_deleted=True)
                name = display_name(target, row)
                self._names[key] = name + (" (deleted)" if row.get("deleted_at") else "")
            except Exception:  # noqa: BLE001 - a missing link should never break a page
                self._names[key] = "(missing)"
        return self._names[key]

    def text(self, info: TableInfo, column: Column, value) -> str:
        """The value as a person should read it."""
        if value is None or value == "" or value == []:
            return ""
        kind = column.type
        if kind == "choice":
            return next((c.label for c in column.choices if c.key == value), str(value))
        if kind == "boolean":
            return "Yes" if int(value) else "No"
        if kind == "money":
            return money_text(value)
        if kind in ("measure", "decimal", "integer"):
            text = _number_text(value)
            return f"{text} {column.unit}" if column.unit else text
        if kind == "datetime":
            return str(value).replace("T", " ")[:16]
        if kind == "link":
            return self.link_name(self.target(info, column), value)
        if kind == "links":
            target = self.target(info, column)
            return ", ".join(self.link_name(target, v) for v in value)
        return str(value)


@dataclass
class Field:
    """Everything a form needs to draw one input."""
    column: Column
    label: str
    help: str | None
    value: object
    error: str | None
    options: list[tuple[str, str]]  # (value, label) for choices and links

    @property
    def name(self) -> str:
        return self.column.name

    @property
    def kind(self) -> str:
        return self.column.type


def input_value(column: Column, value):
    """The stored value as it should appear inside a form input."""
    if value is None:
        return [] if column.type == "links" else ""
    if column.type == "money" and isinstance(value, int):
        return f"{Decimal(value) / 100:.2f}"
    if column.type in ("measure", "decimal") and isinstance(value, float):
        return _number_text(value)
    if column.type == "datetime":
        return str(value)[:16]
    if column.type == "links":
        return [str(v) for v in value]
    return value


def build_fields(records: Records, info: TableInfo, values: dict, errors: dict, from_form: bool) -> list[Field]:
    """Fields for a form. `values` are stored values, or raw form text when `from_form`."""
    formatter = Formatter(records)
    fields = []
    for column in form_columns(info):
        options: list[tuple[str, str]] = []
        if column.type == "choice":
            options = [(c.key, c.label) for c in column.choices]
        elif column.type in ("link", "links"):
            target = formatter.target(info, column)
            name_col = name_column(target)
            rows = records.page(target.name, limit=OPTION_LIMIT, order_by=name_col.name if name_col else "id")
            options = [(str(r["id"]), display_name(target, r)) for r in rows]
        raw = values.get(column.name)
        value = raw if from_form else input_value(column, raw)
        if column.type == "link" and value not in (None, ""):
            value = str(value)
        fields.append(Field(column, column_label(info, column), column_help(info, column),
                            value, errors.get(column.name), options))
    return fields


def values_from_form(info: TableInfo, form) -> dict:
    """Read the submitted form into values for the record service."""
    values = {}
    for column in form_columns(info):
        if column.type == "links":
            values[column.name] = form.getlist(column.name)
        elif column.type == "boolean":
            values[column.name] = "yes" if form.get(column.name) else "no"
        else:
            values[column.name] = form.get(column.name, "")
    return values


def actor_text(actor: str) -> str:
    """Who made a change, in plain words."""
    if actor == "person":
        return "You"
    kind, _, name = actor.partition(":")
    return {"agent": f"Helper '{name}'", "module": f"The {name} module", "import": f"Import '{name}'"}.get(
        kind, "The program")


ACTION_TEXT = {"create": "added this", "update": "changed", "delete": "deleted this", "restore": "restored this"}
