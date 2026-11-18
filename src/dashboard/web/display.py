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
    follows: str | None = None  # for a link to batches: the field (Item) whose batches these are
    owners: dict | None = None  # with `follows`: each option's owner id, so the list can follow the Item
    things: str | None = None  # with `follows`: what the options are called ("batches"), for a one-line note
    blank: str | None = None  # what leaving a link blank does, in words, instead of "(none)"
    blank_follows: str | None = None  # the choice field (Reason) that the blank words depend on
    blank_words: dict | None = None  # with `blank_follows`: the blank words for each of its choices
    only_when_blank: str | None = None  # shown only while this link field (Which batch) is left blank

    kept_private: bool = False  # a saved private value, not sent until the person chooses Show

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


BLANK_STARTS_NEW = "Start a new batch"
BLANK_KEEPS = "Keep the batch it has"
BLANK_COUNTED = "Choose the batch you counted"


def owner_field(records: Records, info: TableInfo, column: Column, on_form: list[Column]) -> tuple[str, str] | None:
    """For a link to records that add up into another record (batches of an item): the field on this
    form that chooses that other record, and the batch column that says which one each belongs to.

    Known from the declarations alone: the link's table has a `total` rule whose link points at the
    same table as another link on this form (movements.item and lots.item both point at items)."""
    if column.type != "link":
        return None
    target = records.registry[target_table(info.module.name, column)]
    total = target.table.total
    if not total:
        return None
    owner_table = target_table(target.module.name, target.table.columns[total["link"]])
    rule = info.table.adjusts or {}
    others = [c for c in on_form if c.type == "link" and c.name != column.name
              and target_table(info.module.name, c) == owner_table]
    others.sort(key=lambda c: not (rule.get("link") == column.name and rule.get("belongs_to") == c.name))
    return (others[0].name, total["link"]) if others else None


def blank_choice(records: Records, info: TableInfo, column: Column, on_form: list[Column],
                 editing: bool) -> tuple[str, dict] | None:
    """What leaving "Which batch" blank does, for each reason: (the reason field, {reason: words}).

    Worked out from the `adjusts` rule: reasons that add start a new batch; the others take from the
    batch with the earliest date. labels.toml's `blank = { adds = "…", takes = "…" }` changes the words."""
    rule = info.table.adjusts
    if not rule or rule.get("link") != column.name or not rule.get("belongs_to") or column.required:
        return None
    direction = info.table.columns[rule["direction"]]
    if direction.name not in {c.name for c in on_form}:
        return None
    if editing:  # a saved record keeps its batch when the box is left blank
        return direction.name, {c.key: BLANK_KEEPS for c in direction.choices}
    own = _labels(info).get("columns", {}).get(column.name, {}).get("blank", {})
    takes = "Use the first batch that still has some"
    if rule.get("oldest_first"):
        target = records.registry[target_table(info.module.name, column)]
        date_label = column_label(target, target.table.columns[rule["oldest_first"]]).lower()
        takes = f"Use the batch with the earliest {date_label} date"
    adds, takes = own.get("adds", BLANK_STARTS_NEW), own.get("takes", takes)
    words = {c.key: adds if c.key in rule["adds"] else takes for c in direction.choices}
    for key in (rule.get("counts") or {}).values():  # a stocktake correction always names its batch
        if key in words:
            words[key] = BLANK_COUNTED
    return direction.name, words


def build_fields(records: Records, info: TableInfo, values: dict, errors: dict, from_form: bool,
                 editing: bool = False) -> list[Field]:
    """Fields for a form. `values` are stored values, or raw form text when `from_form`."""
    formatter = Formatter(records)
    fields = []
    on_form = form_columns(info, batch_columns(records, info) if editing else ())
    rule = info.table.adjusts or {}
    batch_field = rule["link"] if rule.get("belongs_to") and rule["link"] in {c.name for c in on_form} else None
    for column in on_form:
        options: list[tuple[str, str]] = []
        follows = owners = None
        if column.type == "choice":
            options = [(c.key, c.label) for c in column.choices]
        elif column.type in ("link", "links"):
            target = formatter.target(info, column)
            name_col = name_column(target)
            rows = records.page(target.name, limit=OPTION_LIMIT, order_by=name_col.name if name_col else "id")
            if target.table.total:  # a used-up batch is history, not something to choose
                rows = [r for r in rows if r[target.table.total["amount"]] or str(r["id"]) == str(values.get(column.name))]
            current = values.get(column.name)
            if current not in (None, "") and str(current).isdecimal() and str(current).isascii() and \
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
            related = owner_field(records, info, column, on_form)
            if related:  # batches: the form shows only those of the item chosen
                follows = related[0]
                owners = {str(r["id"]): str(r[related[1]]) for r in rows if r[related[1]] is not None}
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
            if name_col is not None and not follows:  # a batch is not started by typing a name for it
                add_new = f"/t/{target.name}/new?{name_col.name}="
                if len(options) >= OPTION_LIMIT:
                    search = f"/t/{target.name}/suggest?column={name_col.name}"
        field = Field(column, column_label(info, column), help_text,
                      value, errors.get(column.name), options,
                      next(iter(shown.items())) if shown else None,
                      (info.table.name, column.name) in info.module.catalogues, add_new, search,
                      _labels(info).get("columns", {}).get(column.name, {}).get("answers"),
                      formatter.date_style if column.type == "date" else None, follows, owners)
        if follows:
            field.things = table_title(formatter.target(info, column)).lower()
        words = blank_choice(records, info, column, on_form, editing)
        if words:
            field.blank_follows, field.blank_words = words
            field.blank = words[1].get(values.get(words[0])) or "(none)"
        if batch_field and column.name in rule["new_batch"].values() and column.name != batch_field:
            field.only_when_blank = batch_field  # a use-by date and place typed here are for a new batch only
        # A saved private value is sent only when the person chooses Show; one still unopened when a save
        # was refused stays closed and kept, so the next save cannot erase it (decision 0064).
        if column.sensitive and (field.value not in (None, "") if not from_form else
                                 editing and column.name in (values.get("_keep_private") or ())):
            field.kept_private, field.value = True, ""
        fields.append(field)
    return fields


def values_from_form(info: TableInfo, form, date_style: str = dates.DAY_FIRST, hide=()) -> tuple[dict, dict]:
    """Read the submitted form into values for the record service, and any dates that could not be read.

    Dates are typed the household's way (20/05/27) and handed on as 2027-05-20."""
    values, problems = {}, {}
    kept = set(form.getlist("_keep_private")) if hasattr(form, "getlist") else set()
    for column in form_columns(info, hide):
        if column.name in kept and column.sensitive:
            continue  # a private detail the person didn't open stays exactly as saved
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


def action_words(info: TableInfo, action: dict) -> tuple[str, str]:
    """A one-step action's button words and its notice once pressed; labels.toml may reword both (decision 0075)."""
    words = _labels(info).get("actions", {}).get(action["key"], {})
    return words.get("label") or action["label"], words.get("done") or action["done"]


def actions_for(info: TableInfo, record: dict | None) -> list[dict]:
    """The one-step buttons a record's page offers now: those whose `show_when` matches the record."""
    if not record or record.get("deleted_at"):
        return []
    return [{"key": a["key"], "label": action_words(info, a)[0]} for a in info.table.actions
            if all(record.get(k) == v for k, v in a["show_when"].items())]


def done_words(info: TableInfo, key: str | None) -> str | None:
    """The notice after an action was pressed, such as "Marked as returned today.", or None."""
    action = next((a for a in info.table.actions if a["key"] == key), None)
    return action_words(info, action)[1] if action else None
