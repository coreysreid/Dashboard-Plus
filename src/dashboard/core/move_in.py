"""Move-in checks on helper suggestions: a starting amount counted twice, a link sent as a name, private details copied into text.

Lane B's first-move read-through (batch 20 item 94, decision 0112) ranked three traps a careful assistant can
still fall into. None of these checks changes a record or keeps anything new:

- `count_twice` finds a new item sent with its starting amount together with a Stock in for that same new item
  in one send. Both are allowed (2 on hand and 1 more bought is real), so it is a warning for Review and the
  helper's answer, never a refusal.
- `name_hint` turns a link sent as a name or part of a path ("Shelf 3", "Pantry > Shelf 3") into the exact
  full-path matches, with their ids, for the refusal the helper already gets.
- `private_copies` says which private fields of the household's own records appear word for word in a
  suggestion's ordinary text. It is for the household's Review page only: it never names or repeats the value,
  and it is never part of a helper's answer, so a helper cannot use it to guess a private detail.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from dashboard.core.schema import table_name, target_table
from dashboard.core.units import unit_for

PATH_SEPARATOR = " › "
_SPLIT = re.compile(r"\s*(?:›|>|/|\\|»)\s*")
MAX_MATCHES = 5
MAX_ROWS = 5000
MAX_TYPED = 60
# A private value shorter than this (letters and digits only) is too common to compare: "2026", "Flat".
SHORTEST_PRIVATE = 5


def _ref(value) -> int | None:
    if isinstance(value, dict) and set(value) == {"ref"} and isinstance(value["ref"], int) \
            and not isinstance(value["ref"], bool):
        return value["ref"]
    return None


def name_column(info):
    """The column that names a record: a required public text column first, else any public text column."""
    texts = [c for c in info.table.columns.values() if c.type == "text" and not c.sensitive]
    required = [c for c in texts if c.required]
    return (required or texts or [None])[0]


def _number(value) -> Decimal | None:
    try:
        number = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _text(number: Decimal) -> str:
    text = f"{number:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _amount(number: Decimal, unit) -> str:
    unit = unit.strip() if isinstance(unit, str) else ""
    return f"{_text(number)} {unit_for(_text(number), unit)}" if unit else _text(number)


def _movement_noun(info) -> str:
    """"Stock in", from a list called "Stock in and out"."""
    title = info.table.title
    return f"{title[:-len(' in and out')]} in" if title.endswith(" in and out") else "entry"


def _starting(registry: dict, info) -> str | None:
    """The field of a new record that starts its first batch's amount (Stock items: quantity), or None."""
    for other in registry.values():
        rule = other.table.total
        if rule and table_name(other.module.name, rule["target"]) == info.name and rule["amount"] in rule["starts_from"]:
            return rule["amount"]
    return None


def count_twice(registry: dict, rows: list[dict]) -> dict[int, str]:
    """{position of a Stock in: warning} for each Stock in that points with {"ref": N} at a new item sent in the
    same send with its own starting amount. `rows` have `position`, `table_name` and `values` (and optionally
    `status`; a rejected row is left out). The same amount twice is "would count the amount twice"."""
    by_position = {r["position"]: r for r in rows if r.get("status") != "rejected" and r.get("table_name")}
    found = {}
    for row in by_position.values():
        info = registry.get(row["table_name"])
        rule = info.table.adjusts if info else None
        if not rule or not rule.get("belongs_to"):
            continue
        values = row["values"]
        direction = values.get(rule["direction"]) or info.table.columns[rule["direction"]].default
        ref = _ref(values.get(rule["belongs_to"]))
        added = _number(values.get(rule["amount"]))
        if direction not in rule["adds"] or ref is None or ref not in by_position or added is None:
            continue
        item_row = by_position[ref]
        item_info = registry.get(item_row["table_name"])
        owner = registry.get(target_table(info.module.name, info.table.columns[rule["belongs_to"]]))
        if item_info is None or owner is None or item_info.name != owner.name:
            continue
        field = _starting(registry, item_info)
        start = _number(item_row["values"].get(field)) if field else None
        if start is None or start <= 0:
            continue
        unit = item_row["values"].get("unit") if "unit" in item_info.table.columns else None
        column = name_column(item_info)
        name = item_row["values"].get(column.name) if column else None
        what = f"the new item “{name.strip()[:MAX_TYPED]}”" if isinstance(name, str) and name.strip() \
            else "the new item"
        noun = _movement_noun(info)
        both = _amount(start + added, unit)
        if start == added:
            found[row["position"]] = (
                f"This would count the amount twice: {what} already starts with {_amount(start, unit)}, and this "
                f"{noun} adds {_amount(added, unit)} more, {both} in all. If {_amount(start, unit)} is what is on "
                f"hand now, reject this {noun} and accept only the new item.")
        else:
            found[row["position"]] = (
                f"Check the amount: {what} already starts with {_amount(start, unit)}, and this {noun} adds "
                f"{_amount(added, unit)} more, {both} in all. If the starting amount already includes what was "
                f"bought, reject this {noun}.")
    return found


def _segments(text: str) -> list[str]:
    return [part.casefold() for part in _SPLIT.split(text.strip()) if part.strip()]


def link_matches(conn, info) -> dict[int, str]:
    """{id: full path or name} of the live records of a table, nested ones by full path ("Kitchen › Pantry")."""
    column = name_column(info)
    if column is None:
        return {}
    parent = info.table.parent
    fields = f"id, {column.name} AS name" + (f", {parent} AS parent" if parent else "")
    rows = {r["id"]: dict(r) for r in conn.execute(
        f"SELECT {fields} FROM {info.name} WHERE deleted_at IS NULL ORDER BY id LIMIT {MAX_ROWS}")}
    found = {}
    for record_id, row in rows.items():
        names, seen, current = [], set(), row
        while current is not None and current["id"] not in seen and len(names) < 12:
            seen.add(current["id"])
            names.append(str(current["name"] or f"#{current['id']}"))
            up = current.get("parent") if parent else None
            current = rows.get(int(up)) if up not in (None, "") else None
        found[record_id] = PATH_SEPARATOR.join(reversed(names))
    return found


def name_hint(conn, registry: dict, target: str, typed) -> str | None:
    """For a link sent as a name or part of a path: the exact full-path matches with their ids, or that there
    are none. None when the value is not a name (a number, a ref) or the linked list has no names."""
    if isinstance(typed, list):
        typed = next((v for v in typed if isinstance(v, str)), None)
    if not isinstance(typed, str) or not typed.strip() or typed.strip().isdecimal():
        return None
    info = registry.get(target)
    if info is None or name_column(info) is None:
        return None
    wanted = _segments(typed)
    if not wanted:
        return None
    shown = typed.strip()[:MAX_TYPED]
    paths = link_matches(conn, info)
    hits = sorted(((rid, path) for rid, path in paths.items()
                   if _segments(path)[-len(wanted):] == wanted), key=lambda hit: hit[1].casefold())
    title = info.table.title
    if not hits:
        return (f"“{shown}” is a name, not an id, and no record in {title} has that name or path. Do not guess "
                f"one that looks close.")
    listed = "; ".join(f"{path} (id {rid})" for rid, path in hits[:MAX_MATCHES])
    more = f" and {len(hits) - MAX_MATCHES} more" if len(hits) > MAX_MATCHES else ""
    if len(hits) == 1:
        return f"“{shown}” is a name, not an id. The record in {title} with that name is {listed}. Send its id."
    return (f"“{shown}” is a name, not an id, and {len(hits)} records in {title} match it: {listed}{more}. They are "
            f"different records. Ask the household which one is meant, then send its id.")


def _compact(text: str) -> str:
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def _texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)


def private_values(conn, registry: dict) -> dict[str, tuple[str, str]]:
    """{compacted private value: (table, column)} for the household's own private text, for Review only.

    Kept in memory for one page view and never shown, logged or sent anywhere."""
    found = {}
    for info in registry.values():
        for column in info.table.columns.values():
            if not column.sensitive or column.type not in ("text", "longtext"):
                continue
            for (value,) in conn.execute(f"SELECT {column.name} FROM {info.name} WHERE deleted_at IS NULL "
                                         f"AND {column.name} IS NOT NULL AND {column.name} != ''"):
                compact = _compact(str(value))
                if len(compact) >= SHORTEST_PRIVATE:
                    found.setdefault(compact, (info.name, column.name))
    return found


def private_copies(known: dict[str, tuple[str, str]], *values) -> list[tuple[str, str]]:
    """The (table, column) of each private value in `known` that appears in the ordinary text of `values`
    (a suggestion's values, its why, its receipt line). Never the value itself."""
    if not known:
        return []
    joined = " ".join(_compact(t) for v in values for t in _texts(v))
    if not joined:
        return []
    hits = []
    for compact, where in known.items():
        if compact in joined and where not in hits:
            hits.append(where)
    return hits
