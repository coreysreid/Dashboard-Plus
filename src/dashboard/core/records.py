"""Create, change, delete and read records, checking every value and keeping a history."""
from __future__ import annotations

import difflib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable

from dashboard.core import dates, db
from dashboard.core.modules import Column, Module, Table
from dashboard.core.schema import join_table_name, table_name, target_table
from dashboard.errors import PlainError

ACTOR = re.compile(r"^(person|system|agent:[a-z0-9_-]+|module:[a-z0-9_]+|import:[a-z0-9_-]+)$")
TRUE_WORDS = {"true", "yes", "y", "1", "on"}
FALSE_WORDS = {"false", "no", "n", "0", "off"}
MAX_PAGE = 500


class ValidationError(PlainError):
    """Some values could not be saved. `problems` maps a field to what is wrong with it."""

    def __init__(self, problems: dict[str, str]):
        self.problems = problems
        super().__init__(" ".join(f"{field}: {message}" for field, message in problems.items()))


class RecordNotFound(PlainError):
    """The record does not exist (or has been deleted)."""


class CountOutOfDate(ValidationError):
    """A batch changed after its count was reviewed; `current` is the amount it holds now (decision 0070)."""

    def __init__(self, problems: dict[str, str], current: Decimal):
        self.current = current
        super().__init__(problems)


@dataclass
class TableInfo:
    """One real table: its module, its declaration and its database name."""
    module: Module
    table: Table

    @property
    def name(self) -> str:
        return table_name(self.module.name, self.table.name)


def build_registry(modules: list[Module]) -> dict[str, TableInfo]:
    """Map every real table name (e.g. pets__weights) to its declaration."""
    return {table_name(m.name, t.name): TableInfo(m, t) for m in modules for t in m.tables.values()}


def resolve_default(column: Column):
    """A column's default value, with "today" and "now" turned into the actual date or time."""
    default = column.default
    if column.type == "date" and default == "today":
        return date.today().isoformat()
    if column.type == "datetime" and default == "now":
        return datetime.now().isoformat(timespec="minutes")
    return default


def _plain_number(value) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Records:
    """The only way the program writes records. Every write is checked and recorded in history."""

    def __init__(self, conn: sqlite3.Connection, registry: dict[str, TableInfo],
                 clock: Callable[[], str] = _now):
        self.conn = conn
        self.registry = registry
        self.clock = clock

    # ----- looking things up -------------------------------------------------
    def info(self, name: str) -> TableInfo:
        if name not in self.registry:
            hint = difflib.get_close_matches(name, list(self.registry), n=1)
            raise RecordNotFound(f"There is no table called '{name}'." + (f" Did you mean '{hint[0]}'?" if hint else ""))
        return self.registry[name]

    def _row(self, info: TableInfo, record_id: int, include_deleted: bool = False) -> dict:
        row = self.conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (record_id,)).fetchone()
        if row is None or (row["deleted_at"] and not include_deleted):
            raise RecordNotFound(f"That {info.table.title.lower()} record does not exist or has been deleted.")
        result = dict(row)
        for column in info.table.columns.values():
            if column.type == "links":
                join = join_table_name(info.module.name, info.table.name, column.name)
                result[column.name] = [r[0] for r in self.conn.execute(
                    f"SELECT to_id FROM {join} WHERE from_id = ? ORDER BY to_id", (record_id,))]
        return result

    def get(self, name: str, record_id: int, include_deleted: bool = False) -> dict:
        """Return one record as a dict, with many-to-many links as lists of ids."""
        return self._row(self.info(name), record_id, include_deleted)

    def count(self, name: str, include_deleted: bool = False) -> int:
        info = self.info(name)
        where = "" if include_deleted else " WHERE deleted_at IS NULL"
        return self.conn.execute(f"SELECT COUNT(*) FROM {info.name}{where}").fetchone()[0]

    def page(self, name: str, offset: int = 0, limit: int = 50, order_by: str = "id",
             descending: bool = False, include_deleted: bool = False) -> list[dict]:
        """Return one page of records, for the grid that loads a page at a time."""
        info = self.info(name)
        allowed = {"id", "created_at", "updated_at"} | {c.name for c in info.table.columns.values() if c.type != "links"}
        if order_by not in allowed:
            raise ValidationError({"order_by": f"cannot sort by '{order_by}'."})
        limit = max(1, min(int(limit), MAX_PAGE))
        where = "" if include_deleted else " WHERE deleted_at IS NULL"
        direction = "DESC" if descending else "ASC"
        rows = self.conn.execute(
            f"SELECT * FROM {info.name}{where} ORDER BY {order_by} {direction}, id {direction} LIMIT ? OFFSET ?",
            (limit, max(0, int(offset))))
        return [dict(r) for r in rows]

    def history(self, name: str, record_id: int) -> list[dict]:
        """Every change to one record, oldest first."""
        info = self.info(name)
        rows = self.conn.execute(
            "SELECT at, actor, action, before, after FROM core__audit WHERE table_name = ? AND record_id = ? "
            "ORDER BY id", (info.name, record_id))
        return [{"at": r["at"], "actor": r["actor"], "action": r["action"],
                 "before": json.loads(r["before"]) if r["before"] else None,
                 "after": json.loads(r["after"]) if r["after"] else None} for r in rows]

    # ----- checking values ---------------------------------------------------
    def _clean_value(self, info: TableInfo, column: Column, value):
        """Return the stored form of a value, or raise ValueError with a plain message."""
        kind = column.type
        if isinstance(value, str):
            value = value.strip()
        if value is None or value == "" or value == []:
            return [] if kind == "links" else None
        if kind in ("text", "longtext"):
            return str(value)
        if kind == "file":
            text = str(value).replace("\\", "/")
            if text.startswith("/") or ".." in text.split("/") or re.match(r"^[A-Za-z]:", text):
                raise ValueError("must be a file inside the data folder's attachments.")
            return text
        if kind == "boolean":
            if isinstance(value, bool):
                return int(value)
            word = str(value).lower()
            if word in TRUE_WORDS:
                return 1
            if word in FALSE_WORDS:
                return 0
            raise ValueError("must be yes or no.")
        if kind in ("integer", "decimal", "measure", "money"):
            try:
                number = Decimal(str(value).replace(",", ""))
            except InvalidOperation:
                raise ValueError("must be a number.") from None
            if not number.is_finite():
                raise ValueError("must be a number.")
            if abs(number) >= Decimal("1e12"):
                raise ValueError("is too large.")
            if kind == "integer" and number != number.to_integral_value():
                raise ValueError("must be a whole number.")
            if column.min is not None and number < Decimal(str(column.min)):
                raise ValueError(f"must be at least {column.min}.")
            if column.max is not None and number > Decimal(str(column.max)):
                raise ValueError(f"must be at most {column.max}.")
            if kind == "integer":
                return int(number)
            if kind == "money":
                return int((number * 100).quantize(Decimal("1")))  # stored as whole cents
            return float(round(number, 6))
        if kind == "date":
            try:
                return date.fromisoformat(str(value)).isoformat()
            except ValueError:
                raise ValueError("must be a date like 2026-06-03.") from None
        if kind == "datetime":
            try:
                return datetime.fromisoformat(str(value)).isoformat(timespec="seconds")
            except ValueError:
                raise ValueError("must be a date and time like 2026-06-03T18:30.") from None
        if kind == "choice":
            keys = {c.key: c.key for c in column.choices}
            labels = {c.label.lower(): c.key for c in column.choices}
            text = str(value)
            if text in keys:
                return text
            if text.lower() in labels:
                return labels[text.lower()]
            raise ValueError("must be one of: " + ", ".join(c.label for c in column.choices) + ".")
        if kind == "link":
            return self._existing_id(info, column, value)
        if kind == "links":
            items = value if isinstance(value, (list, tuple)) else [value]
            return sorted({self._existing_id(info, column, v) for v in items})
        raise ValueError(f"has an unsupported type '{kind}'.")  # pragma: no cover - checked when loading

    def _existing_id(self, info: TableInfo, column: Column, value) -> int:
        try:
            record_id = int(value)
        except (TypeError, ValueError):
            raise ValueError("must point at a record.") from None
        target = target_table(info.module.name, column)
        row = self.conn.execute(f"SELECT deleted_at FROM {target} WHERE id = ?", (record_id,)).fetchone()
        if row is None or row["deleted_at"]:
            raise ValueError("points at a record that does not exist or has been deleted.")
        return record_id

    def clean(self, info: TableInfo, values: dict, creating: bool) -> dict:
        """Check and convert values; raise ValidationError listing every problem."""
        problems: dict[str, str] = {}
        columns = info.table.columns
        cleaned: dict = {}
        for field, value in values.items():
            if field not in columns:
                hint = difflib.get_close_matches(field, list(columns), n=1)
                problems[field] = "is not a field of this table." + (f" Did you mean '{hint[0]}'?" if hint else "")
                continue
            try:
                cleaned[field] = self._clean_value(info, columns[field], value)
            except ValueError as error:
                problems[field] = str(error)
        if creating:
            for column in columns.values():
                if cleaned.get(column.name) in (None, []) and column.default is not None and column.name not in problems:
                    default = resolve_default(column)
                    try:
                        cleaned[column.name] = self._clean_value(info, column, default)
                    except ValueError as error:
                        problems[column.name] = f"has a default that {error}"
        for column in columns.values():
            missing = (creating and cleaned.get(column.name) in (None, [])) or \
                      (not creating and column.name in cleaned and cleaned[column.name] in (None, []))
            if column.required and missing and column.name not in problems:
                problems[column.name] = "is required."
        if problems:
            raise ValidationError(problems)
        return cleaned

    # ----- writing ------------------------------------------------------------
    def _audit(self, actor: str, action: str, info: TableInfo, record_id: int, before, after,
               batch_id: int | None = None) -> None:
        self.conn.execute(
            "INSERT INTO core__audit (at, actor, action, table_name, record_id, before, after, batch_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.clock(), actor, action, info.name, record_id,
             json.dumps(before, sort_keys=True) if before is not None else None,
             json.dumps(after, sort_keys=True) if after is not None else None, batch_id))

    @staticmethod
    def _check_actor(actor: str) -> None:
        if not ACTOR.match(actor):
            raise ValueError(f"Unknown actor '{actor}'.")

    def _write_links(self, info: TableInfo, record_id: int, values: dict) -> None:
        for column in info.table.columns.values():
            if column.type == "links" and column.name in values:
                join = join_table_name(info.module.name, info.table.name, column.name)
                self.conn.execute(f"DELETE FROM {join} WHERE from_id = ?", (record_id,))
                self.conn.executemany(f"INSERT INTO {join} (from_id, to_id) VALUES (?, ?)",
                                      [(record_id, to) for to in values[column.name]])

    def _effect(self, info: TableInfo, row: dict) -> tuple[int, Decimal] | None:
        """What a record adds to (or takes from) its linked quantity: (linked id, signed amount)."""
        rule = info.table.adjusts
        if not rule or row.get("deleted_at") or row.get(rule["link"]) is None or row.get(rule["amount"]) is None:
            return None
        amount = Decimal(str(row[rule["amount"]]))
        return row[rule["link"]], amount if row[rule["direction"]] in rule["adds"] else -amount

    def _adjust(self, info: TableInfo, row: dict, sign: int, actor: str, skip: set | None = None) -> None:
        """Apply (sign=+1) or undo (sign=-1) a record's effect on a linked quantity.

        Used for tables with an `adjusts` section, such as stock in and out: buying
        adds to an item's quantity, using takes from it. Refuses to go below zero.
        """
        effect = self._effect(info, row)
        if effect is not None:
            self._shift(info, effect[0], sign * effect[1], actor, skip, undoing=sign < 0)

    def _shift(self, info: TableInfo, target_id: int, delta: Decimal, actor: str, skip: set | None = None,
               undoing: bool = True) -> None:
        """Change the linked quantity by `delta`, in exact decimals, refusing to go below zero."""
        rule = info.table.adjusts
        target = self.registry[table_name(info.module.name, rule["target"])]
        if skip and (target.name, target_id) in skip:
            return  # the linked record is itself being deleted
        current = self.conn.execute(f"SELECT {rule['quantity']}, deleted_at FROM {target.name} WHERE id = ?",
                                    (target_id,)).fetchone()
        if current is None or current["deleted_at"] or not delta:
            return
        before = current[rule["quantity"]] or 0
        after = Decimal(str(before)) + delta
        if after < 0:
            label = self._label(target, rule["quantity"])
            raise ValidationError({rule["amount"]: f"is more than there is: only {_plain_number(before)} "
                                   f"{'would remain' if undoing else 'left'}. If the count was wrong, correct "
                                   f"“{label}” on the {target.table.title.lower()} record first."})
        after = int(after) if target.table.columns[rule["quantity"]].type == "integer" else float(round(after, 6))
        assignments = {rule["quantity"]: after, "updated_at": self.clock()}
        if actor == "person":
            assignments["edited_by_person"] = 1
        self.conn.execute(f"UPDATE {target.name} SET {', '.join(f'{k} = ?' for k in assignments)} WHERE id = ?",
                          list(assignments.values()) + [target_id])
        self._audit(actor, "update", target, target_id, {rule["quantity"]: before}, {rule["quantity"]: after})
        if target.table.total:
            owner = self.conn.execute(f"SELECT {target.table.total['link']} FROM {target.name} WHERE id = ?",
                                      (target_id,)).fetchone()[0]
            self._retotal(target, owner, actor)

    MAX_DEPTH = 8  # how deep nested records (Kitchen › Pantry › Shelf 3 › Box) may go

    def ancestors(self, info: TableInfo, record_id: int | None) -> list[dict]:
        """The chain of records `record_id` sits inside, outermost first (for a table with `parent`)."""
        chain, seen = [], set()
        while record_id is not None and record_id not in seen and len(chain) <= self.MAX_DEPTH + 1:
            seen.add(record_id)
            row = self.conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (record_id,)).fetchone()
            if row is None:
                break
            chain.append(dict(row))
            record_id = row[info.table.parent]
        return list(reversed(chain))

    def _check_nesting(self, info: TableInfo, record_id: int | None, cleaned: dict) -> None:
        """Refuse putting a record inside itself, or nesting deeper than MAX_DEPTH."""
        parent = info.table.parent
        if not parent or cleaned.get(parent) in (None, ""):
            return
        chain = self.ancestors(info, int(cleaned[parent]))
        if record_id is not None and any(row["id"] == record_id for row in chain):
            raise ValidationError({parent: "can't be this place itself, or a place inside it."})
        if len(chain) + self._levels_below(info, record_id) >= self.MAX_DEPTH:
            raise ValidationError({parent: f"is too deep; places can go {self.MAX_DEPTH} levels deep."})

    def _levels_below(self, info: TableInfo, record_id: int | None) -> int:
        """How many levels of records sit inside this one (0 when none), so moving a branch stays in bounds."""
        levels, current = 0, [record_id] if record_id is not None else []
        while current and levels <= self.MAX_DEPTH:
            marks = ", ".join("?" * len(current))
            current = [r[0] for r in self.conn.execute(
                f"SELECT id FROM {info.name} WHERE deleted_at IS NULL AND {info.table.parent} IN ({marks})", current)]
            levels += 1 if current else 0
        return levels

    @staticmethod
    def _check_required_when(info: TableInfo, record: dict) -> None:
        """Refuse a record that leaves blank a field its other answers make necessary (e.g. "Safe to drink")."""
        problems = {c.name: "Please choose one." for c in info.table.columns.values()
                    if c.required_when and record.get(c.name) is None
                    and all(record.get(k) == v for k, v in c.required_when.items())}
        if problems:
            raise ValidationError(problems)

    def create(self, name: str, values: dict, actor: str = "person", review_status: str = "confirmed",
               batch_id: int | None = None) -> int:
        """Save a new record and return its id."""
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            return self._create(info, values, actor, review_status, batch_id)

    def _create(self, info: TableInfo, values: dict, actor: str, review_status: str = "confirmed",
                batch_id: int | None = None) -> int:
        values = dict(values)
        first_batch = None
        for rule_info in self._totals_into(info):  # an item typed in with an amount starts its first batch
            start = {c: values.pop(c) for c in rule_info.table.total["starts_from"]
                     if c in values and values[c] not in (None, "")}
            if start:
                first_batch = (rule_info, start)
        for column in self._derived(info):
            values.pop(column, None)  # worked out from the batches
        cleaned = self.clean(info, values, creating=True)
        self._check_required_when(info, cleaned)
        self._check_nesting(info, None, cleaned)
        self._choose_batch(info, cleaned, None, actor, review_status, batch_id)
        stored = {k: v for k, v in cleaned.items() if info.table.columns[k].type != "links"}
        now = self.clock()
        fields = ["created_at", "updated_at", "source", "review_status", "batch_id"] + list(stored)
        params = [now, now, actor, review_status, batch_id] + list(stored.values())
        cursor = self.conn.execute(
            f"INSERT INTO {info.name} ({', '.join(fields)}) VALUES ({', '.join('?' * len(fields))})", params)
        record_id = cursor.lastrowid
        self._write_links(info, record_id, cleaned)
        self._audit(actor, "create", info, record_id, None, cleaned, batch_id)
        self._adjust(info, self._row(info, record_id), +1, actor)
        self._retotal(info, cleaned.get(info.table.total.get("link")) if info.table.total else None, actor)
        if first_batch:
            batch_info, start = first_batch
            rule = batch_info.table.total
            batch_values = dict(start, **{rule["link"]: record_id})
            batch_values.setdefault(rule["amount"], 0)
            self._create(batch_info, batch_values, actor, review_status, batch_id)
        return record_id

    # ----- batches: an item's amount is the sum of its batches (DESIGN.md 5.7) --------------

    def _totals_into(self, info: TableInfo):
        """Tables whose records (batches) add up into `info` (such as stock items)."""
        for other in self.registry.values():
            rule = other.table.total
            if rule and table_name(other.module.name, rule["target"]) == info.name:
                yield other

    def _has_movements(self, info: TableInfo, record_id: int) -> bool:
        """True if any stock in or out (deleted or not) is recorded against this batch."""
        for other in self.registry.values():
            rule = other.table.adjusts
            if rule and rule.get("belongs_to") and table_name(other.module.name, rule["target"]) == info.name:
                if self.conn.execute(f"SELECT 1 FROM {other.name} WHERE {rule['link']} = ? LIMIT 1",
                                     (record_id,)).fetchone():
                    return True
        return False

    def _label(self, info: TableInfo, column: str) -> str:
        """A column's friendly label from labels.toml, for messages."""
        labels = info.module.labels.get("tables", {}).get(info.table.name, {}).get("columns", {})
        return labels.get(column, {}).get("label") or column.replace("_", " ").capitalize()

    def _derived(self, info: TableInfo) -> set[str]:
        """Columns of `info` that are worked out from its batches, never typed in."""
        derived = set()
        for other in self._totals_into(info):
            rule = other.table.total
            derived.add(rule["into"])
            if rule["earliest"]:
                derived.add(rule["earliest"]["into"])
        return derived

    def _retotal(self, info: TableInfo, owner_id, actor: str) -> None:
        """Work out the owner's amount (and earliest date) again from its batches."""
        rule = info.table.total
        if not rule or owner_id in (None, ""):
            return
        target = self.registry[table_name(info.module.name, rule["target"])]
        current = self.conn.execute(f"SELECT * FROM {target.name} WHERE id = ?", (owner_id,)).fetchone()
        if current is None or current["deleted_at"]:
            return
        amounts = [Decimal(str(r[0])) for r in self.conn.execute(
            f"SELECT {rule['amount']} FROM {info.name} WHERE deleted_at IS NULL AND {rule['link']} = ? "
            f"AND {rule['amount']} IS NOT NULL", (owner_id,))]
        total = sum(amounts, Decimal(0))
        into = target.table.columns[rule["into"]]
        new = {rule["into"]: int(total) if into.type == "integer" else float(round(total, 6))}
        if rule["earliest"]:
            date_col = rule["earliest"]["date"]
            new[rule["earliest"]["into"]] = self.conn.execute(
                f"SELECT MIN({date_col}) FROM {info.name} WHERE deleted_at IS NULL AND {rule['link']} = ? "
                f"AND {rule['amount']} > 0 AND {date_col} IS NOT NULL AND {date_col} != ''", (owner_id,)).fetchone()[0]
        changed = {k: v for k, v in new.items() if current[k] != v}
        if not changed:
            return
        self.conn.execute(f"UPDATE {target.name} SET {', '.join(f'{k} = ?' for k in changed)}, updated_at = ? "
                          f"WHERE id = ?", list(changed.values()) + [self.clock(), owner_id])
        self._audit(actor, "update", target, owner_id, {k: current[k] for k in changed}, changed)

    def _choose_batch(self, info: TableInfo, cleaned: dict, current: dict | None, actor: str,
                      review_status: str = "confirmed", batch_id: int | None = None) -> None:
        """For stock in and out: check the chosen batch is the item's, or choose one.

        Stock in with no batch chosen starts a new batch (with its use-by date and place).
        Using some with no batch chosen takes from the batch with the earliest known use-by date;
        if that batch holds too little, the person is asked to record it batch by batch."""
        rule = info.table.adjusts
        if not rule or not rule.get("belongs_to"):
            return
        link, owner_col = rule["link"], rule["belongs_to"]
        batches = self.registry[table_name(info.module.name, rule["target"])]
        merged = dict(current or {}, **cleaned)
        if current is not None and link in cleaned and cleaned[link] is None:
            cleaned[link] = merged[link] = current.get(link)  # left blank when editing: keep the batch it had
        owner = merged.get(owner_col)
        if merged.get(link) is not None:
            batch = self.conn.execute(f"SELECT {owner_col} FROM {batches.name} WHERE id = ?",
                                      (merged[link],)).fetchone()
            if batch is not None and owner is not None and batch[owner_col] != owner:
                raise ValidationError({link: "is a batch of a different item. Choose one of this item's batches, "
                                             "or leave it blank."})
            return
        if current is not None or owner is None:
            return
        counts = rule.get("counts")
        if counts and merged.get(rule["direction"]) in (counts["more"], counts["less"]):
            raise ValidationError({link: "is needed for a stocktake correction: it changes one batch. Choose the "
                                         "batch, or open it and use Count this batch."})
        if merged.get(rule["direction"]) in rule["adds"]:
            new_values = {owner_col: owner, rule["quantity"]: 0}
            new_values.update({k: merged.get(v) for k, v in rule["new_batch"].items()
                               if merged.get(v) not in (None, "")})
            cleaned[link] = self._create(batches, new_values, actor, review_status, batch_id)
            return
        oldest = rule.get("oldest_first")
        order = f"{oldest} IS NULL OR {oldest} = '', {oldest}, id" if oldest else "id"
        found = self.conn.execute(
            f"SELECT * FROM {batches.name} WHERE deleted_at IS NULL AND {owner_col} = ? "
            f"AND {rule['quantity']} > 0 ORDER BY {order} LIMIT 1", (owner,)).fetchone()
        if found is None:
            raise ValidationError({rule["amount"]: "is more than there is: none of this item is recorded. "
                                                   "Record what you have first."})
        amount = merged.get(rule["amount"])
        held = sum((Decimal(str(r[0])) for r in self.conn.execute(
            f"SELECT {rule['quantity']} FROM {batches.name} WHERE deleted_at IS NULL AND {owner_col} = ? "
            f"AND {rule['quantity']} > 0", (owner,))), Decimal(0))
        if amount is not None and Decimal(str(amount)) > held:
            raise ValidationError({rule["amount"]: f"is more than there is: only {_plain_number(held)} left."})
        if amount is not None and Decimal(str(amount)) > Decimal(str(found[rule["quantity"]])):
            when = f", use by {dates.show(found[oldest], dates.household_style(self.conn))}" \
                if oldest and found[oldest] else ""
            raise ValidationError({rule["amount"]: f"is more than the batch to use first holds "
                                   f"({_plain_number(found[rule['quantity']])}{when}). Record that batch first, "
                                   f"then the rest from the next one, or choose a batch."})
        cleaned[link] = found["id"]

    # ----- stocktake: counting one batch (decision 0070, DESIGN.md 5.7) ------------------------

    def count_table(self, batch_table: str) -> TableInfo | None:
        """The table (such as stock in and out) whose `counts` reasons record a count of `batch_table`."""
        for other in self.registry.values():
            rule = other.table.adjusts
            if rule and rule.get("counts") and table_name(other.module.name, rule["target"]) == batch_table:
                return other
        return None

    def check_count(self, batch_table: str, batch_id: int, counted) -> dict:
        """What counting one batch would change, without saving anything.

        Returns the amount recorded, the amount counted, the difference, the item it belongs to, the
        item's amount before and after, and how many of the item's batches would still hold some."""
        movements = self.count_table(batch_table)
        if movements is None:
            raise RecordNotFound("These records cannot be counted.")
        rule = movements.table.adjusts
        batches = self.info(batch_table)
        row = self._row(batches, batch_id)
        column = batches.table.columns[rule["quantity"]]
        try:
            number = self._clean_value(batches, column, counted)
        except ValueError as error:
            raise ValidationError({"counted": str(error)}) from None
        if number is None:
            raise ValidationError({"counted": "is needed: type how many you counted, or 0 if there are none."})
        if Decimal(str(counted).strip().replace(",", "")) != Decimal(str(number)):
            raise ValidationError({"counted": "has more decimal places than can be kept (6 at most)."})
        recorded, counted_now = Decimal(str(row[rule["quantity"]] or 0)), Decimal(str(number))
        owner_col, total = rule["belongs_to"], batches.table.total
        owner = row[owner_col]
        others = [Decimal(str(r[0])) for r in self.conn.execute(
            f"SELECT {rule['quantity']} FROM {batches.name} WHERE deleted_at IS NULL AND {owner_col} = ? "
            f"AND id != ? AND {rule['quantity']} > 0", (owner, batch_id))]
        owner_before = None
        if total:
            owner_info = self.registry[table_name(batches.module.name, total["target"])]
            value = self.conn.execute(f"SELECT {total['into']} FROM {owner_info.name} WHERE id = ?",
                                      (owner,)).fetchone()
            owner_before = Decimal(str(value[0] or 0)) if value else None
        difference = counted_now - recorded
        return {"batch": batch_id, "owner": owner, "recorded": recorded, "counted": counted_now,
                "difference": difference, "owner_before": owner_before,
                "owner_after": None if owner_before is None else owner_before + difference,
                "batches_holding": len(others) + (1 if counted_now > 0 else 0)}

    def count_batch(self, batch_table: str, batch_id: int, counted, recorded, actor: str = "person",
                    happened_on: str | None = None) -> dict:
        """Save a stocktake count of one batch as one stock correction (decision 0070).

        `recorded` is the amount the person saw when they reviewed the count. The difference is saved
        as its own stock in or out record ("counted more" or "counted less"), never as the count added on
        top and never by typing over the amount. If the batch already holds what was counted, nothing is
        saved (so a second click on Save adds nothing). If it changed since the review, CountOutOfDate."""
        self._check_actor(actor)
        movements = self.count_table(batch_table)
        with db.transaction(self.conn):
            plan = self.check_count(batch_table, batch_id, counted)
            if not plan["difference"]:
                return dict(plan, status="same", movement=None)
            try:
                seen = Decimal(str(recorded).strip())
            except (InvalidOperation, AttributeError):
                seen = None
            if seen != plan["recorded"]:
                raise CountOutOfDate({"counted": f"is out of date: this batch now shows "
                                                 f"{_plain_number(plan['recorded'])}. Check the count again."},
                                     plan["recorded"])
            rule = movements.table.adjusts
            counts = rule["counts"]
            values = {rule["belongs_to"]: plan["owner"], rule["link"]: batch_id,
                      rule["direction"]: counts["more"] if plan["difference"] > 0 else counts["less"],
                      rule["amount"]: str(abs(plan["difference"]))}
            if counts.get("note"):
                values[counts["note"]] = (f"Stocktake: counted {_plain_number(plan['counted'])}; "
                                          f"{_plain_number(plan['recorded'])} were recorded.")
            if happened_on:
                date_col = next((c.name for c in movements.table.columns.values()
                                 if c.type == "date" and c.default == "today"), None)
                if date_col:
                    values[date_col] = happened_on
            movement = self._create(movements, values, actor)
            return dict(plan, status="saved", movement=movement)

    def update(self, name: str, record_id: int, values: dict, actor: str = "person") -> dict:
        """Change some fields of a record; return what changed as {field: [before, after]}."""
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            current = self._row(info, record_id)
            cleaned = self.clean(info, values, creating=False)
            self._check_required_when(info, dict(current, **cleaned))
            self._check_nesting(info, record_id, cleaned)
            self._choose_batch(info, cleaned, current, actor)
            changed = {k: v for k, v in cleaned.items() if current.get(k) != v}
            total = info.table.total
            if total and total["link"] in changed and self._has_movements(info, record_id):
                raise ValidationError({total["link"]: "can't change once stock in or out is recorded for this "
                                                      "batch. Record it as used or given away here, and as bought "
                                                      "on the other item."})
            derived = self._derived(info) & set(changed)
            if derived:
                raise ValidationError({c: "is worked out from its batches. Change a batch, or record stock in "
                                          "or out." for c in derived})
            if not changed:
                return {}
            stored = {k: v for k, v in changed.items() if info.table.columns[k].type != "links"}
            assignments = dict(stored, updated_at=self.clock())
            if actor == "person":
                assignments["edited_by_person"] = 1
            self.conn.execute(
                f"UPDATE {info.name} SET {', '.join(f'{k} = ?' for k in assignments)} WHERE id = ?",
                list(assignments.values()) + [record_id])
            self._write_links(info, record_id, changed)
            self._audit(actor, "update", info, record_id, {k: current.get(k) for k in changed}, changed)
            rule = info.table.adjusts
            if rule and any(k in changed for k in (rule["link"], rule["amount"], rule["direction"])):
                old, new = self._effect(info, current), self._effect(info, self._row(info, record_id))
                if old and new and old[0] == new[0]:
                    self._shift(info, new[0], new[1] - old[1], actor, undoing=False)  # one net change
                else:
                    self._adjust(info, current, -1, actor)
                    self._adjust(info, self._row(info, record_id), +1, actor)
            if info.table.total:
                link = info.table.total["link"]
                self._retotal(info, current.get(link), actor)
                if changed.get(link, current.get(link)) != current.get(link):
                    self._retotal(info, changed[link], actor)
        return {k: [current.get(k), v] for k, v in changed.items()}

    def _dependents(self, info: TableInfo):
        """Yield (other table info, column) for every link column that points at `info`."""
        for other in self.registry.values():
            for column in other.table.columns.values():
                if column.type == "link" and target_table(other.module.name, column) == info.name:
                    yield other, column

    def delete(self, name: str, record_id: int, actor: str = "person") -> None:
        """Mark a record as deleted (it stays in history and can be restored).

        Records that link to it are handled as their column says: 'restrict' refuses,
        'cascade' deletes them too, 'clear' empties the link.
        """
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            self._delete(info, record_id, actor, set(), f"{info.name}:{record_id}")

    def _delete(self, info: TableInfo, record_id: int, actor: str, seen: set, root: str) -> None:
        """Delete one record and what its links say should go with it.

        Everything deleted or cleared along with the record is tagged with `root` (the record the
        person deleted), so restoring that record brings it all back (decision 0050)."""
        if (info.name, record_id) in seen:
            return
        seen.add((info.name, record_id))
        row = self._row(info, record_id)
        blocking = []
        for other, column in self._dependents(info):
            ids = [r[0] for r in self.conn.execute(
                f"SELECT id FROM {other.name} WHERE {column.name} = ? AND deleted_at IS NULL", (record_id,))]
            if not ids:
                continue
            if column.on_delete == "restrict":
                blocking.append(f"{len(ids)} {other.table.title.lower()} record(s)")
            elif column.on_delete == "cascade":
                for child in ids:
                    self._delete(other, child, actor, seen, root)
            else:  # clear
                for child in ids:
                    self.conn.execute(f"UPDATE {other.name} SET {column.name} = NULL, updated_at = ? WHERE id = ?",
                                      (self.clock(), child))
                    self._audit(actor, "update", other, child, {column.name: record_id},
                                {column.name: None, "_cleared_with": root})
        if blocking:
            raise ValidationError({"delete": "cannot be done yet because " + " and ".join(blocking) +
                                   " still point at it. Change or delete those first."})
        rule = info.table.adjusts
        # Nothing to undo (its batch was deleted first and its link cleared): restoring must not add it again.
        kept = bool(rule and (self._effect(info, row) is None or
                              (table_name(info.module.name, rule["target"]), row[rule["link"]]) in seen))
        self._adjust(info, row, -1, actor, skip=seen)
        now = self.clock()
        self.conn.execute(f"UPDATE {info.name} SET deleted_at = ?, updated_at = ? WHERE id = ?", (now, now, record_id))
        # kept_effect: a stock movement deleted with its item still counts in the item's amount.
        self._audit(actor, "delete", info, record_id, None, {"with": root, "kept_effect": kept})
        if info.table.total:
            self._retotal(info, row.get(info.table.total["link"]), actor)

    def restore(self, name: str, record_id: int, actor: str = "person") -> None:
        """Bring back a deleted record, with everything that was deleted or cleared along with it."""
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            row = self._row(info, record_id, include_deleted=True)
            if not row["deleted_at"]:
                return
            for column in info.table.columns.values():  # it can't come back pointing at something deleted
                if column.type == "link" and row.get(column.name) is not None:
                    target = self.registry.get(target_table(info.module.name, column))
                    linked = self.conn.execute(f"SELECT deleted_at FROM {target.name} WHERE id = ?",
                                               (row[column.name],)).fetchone() if target else None
                    if linked is not None and linked["deleted_at"]:
                        raise ValidationError({"restore": f"needs its “{self._label(info, column.name)}” back "
                                               f"first: restore that record in {target.table.title}, and this "
                                               f"one comes back with it."})
            self._restore_one(info, record_id, actor)
            key = f"{info.name}:{record_id}"
            for entry in self.conn.execute(
                    "SELECT table_name, record_id FROM core__audit WHERE action = 'delete' AND id IN ("
                    "SELECT MAX(id) FROM core__audit WHERE action = 'delete' GROUP BY table_name, record_id) "
                    "AND json_extract(after, '$.with') = ? AND NOT (table_name = ? AND record_id = ?)",
                    (key, info.name, record_id)).fetchall():
                other = self.registry.get(entry["table_name"])
                if other is not None:
                    self._restore_one(other, entry["record_id"], actor)
            for entry in self.conn.execute(
                    "SELECT table_name, record_id, before FROM core__audit WHERE action = 'update' "
                    "AND json_extract(after, '$._cleared_with') = ?", (key,)).fetchall():
                other = self.registry.get(entry["table_name"])
                if other is None:
                    continue
                for column, value in json.loads(entry["before"]).items():
                    self.conn.execute(f"UPDATE {other.name} SET {column} = ?, updated_at = ? "
                                      f"WHERE id = ? AND {column} IS NULL", (value, self.clock(), entry["record_id"]))
                    self._audit(actor, "update", other, entry["record_id"], {column: None}, {column: value})

    def _restore_one(self, info: TableInfo, record_id: int, actor: str) -> None:
        row = self.conn.execute(f"SELECT * FROM {info.name} WHERE id = ?", (record_id,)).fetchone()
        if row is None or not row["deleted_at"]:
            return
        last = self.conn.execute("SELECT after FROM core__audit WHERE action = 'delete' AND table_name = ? "
                                 "AND record_id = ? ORDER BY id DESC LIMIT 1", (info.name, record_id)).fetchone()
        kept = bool(last and last["after"] and json.loads(last["after"]).get("kept_effect"))
        self.conn.execute(f"UPDATE {info.name} SET deleted_at = NULL, updated_at = ? WHERE id = ?",
                          (self.clock(), record_id))
        self._audit(actor, "restore", info, record_id, None, None)
        if not kept:
            self._adjust(info, self._row(info, record_id), +1, actor)
        if info.table.total:
            self._retotal(info, row[info.table.total["link"]], actor)
