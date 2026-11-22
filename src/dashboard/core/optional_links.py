"""Links into an optional module (decision 0115): kept by exact ID while it is off, shown in neutral words, never guessed."""
from __future__ import annotations

from dashboard.core.modules import Column
from dashboard.core.records import TableInfo
from dashboard.core.schema import target_table

# What a saved optional link is right now. BLANK: nothing saved. OFF: an ID is saved but the module it points
# into is switched off or not installed, so nothing about the record is read. GONE: that module is on, but the
# saved ID is not a live record there (deleted, or never there). LIVE: an ordinary link.
BLANK, OFF, GONE, LIVE = "blank", "off", "gone", "live"

# The household's words when a module gives none (labels.toml `optional`, decision 0115). {Thing} and {thing}
# are the field's label; {module} is the title of the module the link points into.
DEFAULT_WORDS = {
    "off_help": "{Thing} links appear when {module} is switched on. You can save this record without one.",
    "kept_help": "A {thing} link is saved. Switch on {module} to see or change it.",
    "kept": "{Thing} link saved; switch on {module} to see it.",
    "none": "No {thing} linked.",
    "gone": "The linked {thing} is no longer there.",
    "missing": "The linked {thing} is no longer there. Choose another, or leave it blank.",
}


def target_module(column: Column) -> str:
    """The name of the module an optional link points into."""
    return column.to.partition(".")[0]


def is_off(registry: dict, info: TableInfo, column: Column) -> bool:
    """True for an optional link whose module is switched off or not installed (not in this registry)."""
    return column.optional and target_table(info.module.name, column) not in registry


def state(conn, registry: dict, info: TableInfo, column: Column, value) -> str:
    """BLANK, OFF, GONE or LIVE for one saved value of an optional link. Only the ID is looked at: a record of
    a switched-off module is never read, and a missing one is never replaced by another with the same name."""
    if value in (None, "", []):
        return BLANK
    if is_off(registry, info, column):
        return OFF
    try:
        record_id = int(value)
    except (TypeError, ValueError):
        return GONE
    row = conn.execute(f"SELECT deleted_at FROM {target_table(info.module.name, column)} WHERE id = ?",
                       (record_id,)).fetchone()
    return LIVE if row is not None and not row["deleted_at"] else GONE


def words(info: TableInfo, column: Column, key: str, module_title: str) -> str:
    """One of the household's sentences for an optional link: the module's own from labels.toml, or the default."""
    labels = info.module.labels.get("tables", {}).get(info.table.name, {}).get("columns", {}).get(column.name, {})
    own = (labels.get("optional") or {}).get(key)
    if own:
        return own
    thing = (labels.get("label") or column.name.replace("_", " ")).strip()
    return DEFAULT_WORDS[key].format(Thing=thing[:1].upper() + thing[1:], thing=thing[:1].lower() + thing[1:],
                                     module=module_title)
