"""Gentle checks before a form saves, like an odometer reading lower than the last one: shown, never a block (0111).

A table declares them as `[[tables.<t>.confirm]]` in tables.toml. Each compares the record being saved with the
nearest other record of the same subject (`per`) before it in `order`, oldest first with the record number as the
tie-breaker, and only among records with the same `among` value. "lower" also looks at the nearest record after
it, so a reading typed in late is checked both ways. Nothing is worked out, changed or refused here: the form
says the sentence and offers Go back or Save as entered.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass

from dashboard.core.records import TableInfo


@dataclass
class Warning:
    key: str
    column: str  # the field the sentence is about, so the form can take the person back to it
    message: str
    token: str  # what was checked; Save as entered carries it, so a changed value is checked again
    keep: str | None = None  # the household's words for Save as entered, such as "Keep this as another dose" (0120)


def _neighbour(conn: sqlite3.Connection, info: TableInfo, rule: dict, record: dict, record_id: int | None,
               after: bool) -> dict | None:
    order, per = rule["order"], rule["per"]
    mine = record_id if record_id is not None else 2 ** 62  # a new record comes after every saved one that day
    sign, direction = (">", "ASC") if after else ("<", "DESC")
    clause, params = "", [record[per], record[order], record[order], mine]
    if rule.get("among"):
        clause, params = f" AND {rule['among']} IS ?", params + [record.get(rule["among"])]
    row = conn.execute(
        f"SELECT * FROM {info.name} WHERE deleted_at IS NULL AND {per} = ? AND {rule['column']} IS NOT NULL "
        f"AND ({order} {sign} ? OR ({order} = ? AND id {sign} ?)){clause} "
        f"ORDER BY {order} {direction}, id {direction} LIMIT 1", params).fetchone()
    return dict(row) if row else None


def warnings(conn: sqlite3.Connection, info: TableInfo, record: dict, record_id: int | None = None,
             words=lambda column, value: str(value)) -> list[Warning]:
    """The sentences to show before saving `record` (every field, as it would be saved). `words(column, value)`
    turns a stored value into the words a person reads, for a sentence's {before}."""
    found = []
    for rule in info.table.confirm:
        name = rule["column"]
        if any(record.get(k) in (None, "") for k in (name, rule["per"], rule["order"])):
            continue
        value = record[name]
        checked = f"{value}@{record[rule['order']]}@{record[rule['per']]}@{record.get(rule.get('among') or '')}"
        token = f"{rule['key']}-{hashlib.sha256(checked.encode()).hexdigest()[:16]}"
        before = _neighbour(conn, info, rule, record, record_id, after=False)
        if rule["when"] == "different":
            if before is not None and before[name] != value:
                column = info.table.columns[name]
                found.append(Warning(rule["key"], name, rule["message"].replace("{before}", words(column, before[name])),
                                     token))
            continue
        if before is not None and value < before[name]:
            found.append(Warning(rule["key"], name, rule["message"], token))
            continue
        later = _neighbour(conn, info, rule, record, record_id, after=True)
        if later is not None and value > later[name]:
            found.append(Warning(rule["key"], name, rule["later"], token))
    return found


def unconfirmed(found: list[Warning], confirmed) -> list[Warning]:
    """The warnings Save as entered has not yet answered for these exact values."""
    said = {token for value in (confirmed or ()) for token in str(value).split()}
    return [w for w in found if w.token not in said]
