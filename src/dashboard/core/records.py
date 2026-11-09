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

from dashboard.core import db
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
            return float(number)
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

    def _adjust(self, info: TableInfo, row: dict, sign: int, actor: str, skip: set | None = None) -> None:
        """Apply (sign=+1) or undo (sign=-1) a record's effect on a linked quantity.

        Used for tables with an `adjusts` section, such as stock in and out: buying
        adds to an item's quantity, using takes from it. Refuses to go below zero.
        """
        rule = info.table.adjusts
        if not rule or row.get("deleted_at") or row.get(rule["link"]) is None or row.get(rule["amount"]) is None:
            return
        target = self.registry[table_name(info.module.name, rule["target"])]
        target_id = row[rule["link"]]
        if skip and (target.name, target_id) in skip:
            return  # the linked record is itself being deleted
        current = self.conn.execute(f"SELECT {rule['quantity']}, deleted_at FROM {target.name} WHERE id = ?",
                                    (target_id,)).fetchone()
        if current is None or current["deleted_at"]:
            return
        before = current[rule["quantity"]] or 0
        amount = row[rule["amount"]] if row[rule["direction"]] in rule["adds"] else -row[rule["amount"]]
        after = before + sign * amount
        if after < 0:
            column = target.table.columns[rule["quantity"]]
            raise ValidationError({rule["amount"]: f"is more than there is: only {_plain_number(before)} "
                                   f"{'left' if sign > 0 else 'would remain'}. If the count was wrong, correct "
                                   f"{column.name.replace('_', ' ')} on the {target.table.title.lower()} record first."})
        if target.table.columns[rule["quantity"]].type == "integer":
            after = int(after)
        assignments = {rule["quantity"]: after, "updated_at": self.clock()}
        if actor == "person":
            assignments["edited_by_person"] = 1
        self.conn.execute(f"UPDATE {target.name} SET {', '.join(f'{k} = ?' for k in assignments)} WHERE id = ?",
                          list(assignments.values()) + [target_id])
        self._audit(actor, "update", target, target_id, {rule["quantity"]: before}, {rule["quantity"]: after})

    def create(self, name: str, values: dict, actor: str = "person", review_status: str = "confirmed",
               batch_id: int | None = None) -> int:
        """Save a new record and return its id."""
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            cleaned = self.clean(info, values, creating=True)
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
        return record_id

    def update(self, name: str, record_id: int, values: dict, actor: str = "person") -> dict:
        """Change some fields of a record; return what changed as {field: [before, after]}."""
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            current = self._row(info, record_id)
            cleaned = self.clean(info, values, creating=False)
            changed = {k: v for k, v in cleaned.items() if current.get(k) != v}
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
                self._adjust(info, current, -1, actor)
                self._adjust(info, self._row(info, record_id), +1, actor)
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
            self._delete(info, record_id, actor, set())

    def _delete(self, info: TableInfo, record_id: int, actor: str, seen: set) -> None:
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
                    self._delete(other, child, actor, seen)
            else:  # clear
                for child in ids:
                    self.conn.execute(f"UPDATE {other.name} SET {column.name} = NULL, updated_at = ? WHERE id = ?",
                                      (self.clock(), child))
                    self._audit(actor, "update", other, child, {column.name: record_id}, {column.name: None})
        if blocking:
            raise ValidationError({"delete": "cannot be done yet because " + " and ".join(blocking) +
                                   " still point at it. Change or delete those first."})
        self._adjust(info, row, -1, actor, skip=seen)
        now = self.clock()
        self.conn.execute(f"UPDATE {info.name} SET deleted_at = ?, updated_at = ? WHERE id = ?", (now, now, record_id))
        self._audit(actor, "delete", info, record_id, None, None)

    def restore(self, name: str, record_id: int, actor: str = "person") -> None:
        """Bring back a deleted record."""
        self._check_actor(actor)
        info = self.info(name)
        with db.transaction(self.conn):
            row = self._row(info, record_id, include_deleted=True)
            if not row["deleted_at"]:
                return
            self.conn.execute(f"UPDATE {info.name} SET deleted_at = NULL, updated_at = ? WHERE id = ?",
                              (self.clock(), record_id))
            self._audit(actor, "restore", info, record_id, None, None)
            self._adjust(info, self._row(info, record_id), +1, actor)
