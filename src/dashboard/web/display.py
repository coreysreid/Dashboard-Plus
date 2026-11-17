"""Turn declared tables and stored values into friendly labels, form fields and text."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dashboard.core import dates, naming
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


def form_columns(info: TableInfo, hide=()) -> list[Column]:
    """Columns in the order the form should show them, leaving out `hide`.

    labels.toml's `form` sets the order; any required column it leaves out is
    added at the end, so a form can never be impossible to save.
    """
    columns = info.table.columns
    order = _labels(info).get("form")
    if not order:
        return [c for c in columns.values() if c.name not in hide]
    chosen = [columns[name] for name in order if name in columns]
    chosen += [c for c in columns.values() if c.required and c not in chosen]
    return [c for c in chosen if c.name not in hide]


def batch_columns(records: Records, info: TableInfo) -> set[str]:
    """Columns an item's form shows only when it is first added: its amount, use-by date and place
    start its first batch; afterwards they belong to its batches (DESIGN.md 5.7)."""
    hide = set(records._derived(info))
    for other in records._totals_into(info):
        hide |= set(other.table.total["starts_from"])
    return hide


def list_columns(info: TableInfo) -> list[Column]:
    """Columns shown in the grid: labels.toml's `list`, or the first few short ones."""
    columns = info.table.columns
    order = _labels(info).get("list")
    if order:
        return [columns[name] for name in order if name in columns]
    short = [c for c in columns.values() if c.type not in ("longtext", "links", "file")]
    return short[:LIST_COLUMN_LIMIT]


def name_column(info: TableInfo) -> Column | None:
    """The column that best names a record: a required text column, else any text column; never a private one."""
    texts = [c for c in info.table.columns.values() if c.type == "text" and not c.sensitive]
    required = [c for c in texts if c.required]
    return (required or texts or [None])[0]


PATH_SEPARATOR = " › "


def path_name(info: TableInfo, rows_by_id: dict, row: dict) -> str:
    """"Kitchen › Pantry › Shelf 3" for a nested record, from rows already loaded by id."""
    names, seen = [], set()
    while row is not None and row["id"] not in seen and len(names) < 12:
        seen.add(row["id"])
        names.append(display_name(info, row))
        parent = row.get(info.table.parent)
        row = rows_by_id.get(int(parent)) if parent not in (None, "") else None
    return PATH_SEPARATOR.join(reversed(names))


def display_name(info: TableInfo, row: dict, records: Records | None = None) -> str:
    """A short human name for a record, used wherever another record links to it."""
    if info.table.record_name and records is not None:
        return naming.record_name(records.conn, records.registry, info, row)  # "3 tins of Kidney beans"
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
        self._date_style: str | None = None

    @property
    def date_style(self) -> str:
        if self._date_style is None:
            self._date_style = dates.household_style(self.records.conn)
        return self._date_style

    def target(self, info: TableInfo, column: Column) -> TableInfo:
        return self.records.registry[target_table(info.module.name, column)]

    def link_name(self, target: TableInfo, record_id) -> str:
        key = (target.name, int(record_id))
        if key not in self._names:
            try:
                row = self.records.get(target.name, int(record_id), include_deleted=True)
                if target.table.parent:
                    chain = self.records.ancestors(target, int(record_id))
                    name = path_name(target, {r["id"]: r for r in chain}, chain[-1]) if chain else display_name(target, row)
                else:
                    name = display_name(target, row, self.records)
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
        if kind == "date":
            return dates.show(value, self.date_style)
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
    show_when: tuple[str, str] | None = None  # shown only while another choice field has this value
    suggest: bool = False  # offer matches while typing (labels.toml `suggest_from`)
    add_new: str | None = None  # for a link: where to add a new record, with the typed name appended
    search: str | None = None  # for a long link list: where to look past the first OPTION_LIMIT records
    help_answers: list | None = None  # the words for yes and no, for a yes/no that must be answered
    date_style: str | None = None  # for a date: dmy, mdy or ymd, the household's way of writing dates

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


def build_fields(records: Records, info: TableInfo, values: dict, errors: dict, from_form: bool,
                 editing: bool = False) -> list[Field]:
    """Fields for a form. `values` are stored values, or raw form text when `from_form`."""
    formatter = Formatter(records)
    fields = []
    for column in form_columns(info, batch_columns(records, info) if editing else ()):
        options: list[tuple[str, str]] = []
        if column.type == "choice":
            options = [(c.key, c.label) for c in column.choices]
        elif column.type in ("link", "links"):
            target = formatter.target(info, column)
            name_col = name_column(target)
            rows = records.page(target.name, limit=OPTION_LIMIT, order_by=name_col.name if name_col else "id")
            if target.table.total:  # a used-up batch is history, not something to choose
                rows = [r for r in rows if r[target.table.total["amount"]] or str(r["id"]) == str(values.get(column.name))]
            current = values.get(column.name)
            if current not in (None, "") and str(current).isdigit() and \
                    int(current) not in {r["id"] for r in rows}:  # always offer the record already chosen
                try:
                    rows = list(rows) + [records.get(target.name, int(current), include_deleted=True)]
                except Exception:  # noqa: BLE001 - a missing link should never break a form
                    pass
            if target.table.parent:
                by_id = {r["id"]: dict(r) for r in rows}
                for row in list(by_id.values()):  # parents beyond the first records still name the path
                    parent = row.get(target.table.parent)
                    if parent not in (None, "") and int(parent) not in by_id:
                        for above in records.ancestors(target, int(parent)):
                            by_id.setdefault(above["id"], above)
                options = sorted(((str(r["id"]), path_name(target, by_id, dict(r))) for r in rows),
                                 key=lambda option: option[1].lower())
            else:
                options = [(str(r["id"]), display_name(target, r, records)) for r in rows]
        raw = values.get(column.name)
        value = raw if from_form else input_value(column, raw)
        help_text = column_help(info, column)
        if column.type == "date":
            if value and dates.is_stored(str(value)):  # a stored or default date, not what was typed
                value = dates.show(value, formatter.date_style)
            hint = dates.HINTS[formatter.date_style] + "."
            help_text = f"{hint} {help_text}" if help_text else hint
        if column.type == "link" and value not in (None, ""):
            value = str(value)
        shown = _labels(info).get("columns", {}).get(column.name, {}).get("show_when")
        add_new = search = None
        if column.type == "link":
            target = formatter.target(info, column)
            name_col = name_column(target)
            if name_col is not None:
                add_new = f"/t/{target.name}/new?{name_col.name}="
                if len(options) >= OPTION_LIMIT:
                    search = f"/t/{target.name}/suggest?column={name_col.name}"
        fields.append(Field(column, column_label(info, column), help_text,
                            value, errors.get(column.name), options,
                            next(iter(shown.items())) if shown else None,
                            (info.table.name, column.name) in info.module.catalogues, add_new, search,
                            _labels(info).get("columns", {}).get(column.name, {}).get("answers"),
                            formatter.date_style if column.type == "date" else None))
    return fields


def values_from_form(info: TableInfo, form, date_style: str = dates.DAY_FIRST, hide=()) -> tuple[dict, dict]:
    """Read the submitted form into values for the record service, and any dates that could not be read.

    Dates are typed the household's way (20/05/27) and handed on as 2027-05-20."""
    values, problems = {}, {}
    for column in form_columns(info, hide):
        if column.type == "date" and form.get(column.name, "").strip():
            try:
                values[column.name] = dates.parse(form.get(column.name), date_style)
            except ValueError as error:
                problems[column.name] = str(error)
        elif column.type == "links":
            values[column.name] = form.getlist(column.name)
        elif column.type == "boolean" and column.required_when:
            values[column.name] = form.get(column.name, "")  # an explicit yes or no, or no answer yet
        elif column.type == "boolean":
            values[column.name] = "yes" if form.get(column.name) else "no"
        else:
            values[column.name] = form.get(column.name, "")
    return values, problems


def actor_text(actor: str) -> str:
    """Who made a change, in plain words."""
    if actor == "person":
        return "You"
    kind, _, name = actor.partition(":")
    return {"agent": f"Helper '{name}'", "module": f"The {name} module", "import": f"Import '{name}'"}.get(
        kind, "The program")


ACTION_TEXT = {"create": "added this", "update": "changed", "delete": "deleted this", "restore": "restored this"}
