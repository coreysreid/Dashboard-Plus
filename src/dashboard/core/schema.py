"""Turn a module's declared tables into SQL, and work out its next migration."""
from __future__ import annotations

import sqlite3

from dashboard.core import db
from dashboard.core.modules import Column, Module, Table
from dashboard.errors import PlainError

SQL_TYPES = {
    "text": "TEXT", "longtext": "TEXT", "choice": "TEXT", "date": "TEXT", "datetime": "TEXT", "file": "TEXT",
    "integer": "INTEGER", "boolean": "INTEGER", "link": "INTEGER",
    "money": "INTEGER",   # whole minor units (cents); the household currency is a setting
    "decimal": "REAL", "measure": "REAL",
}
ON_DELETE_SQL = {"restrict": "RESTRICT", "cascade": "CASCADE", "clear": "SET NULL"}
SYSTEM_COLUMNS_SQL = [
    "id INTEGER PRIMARY KEY",
    "created_at TEXT NOT NULL",
    "updated_at TEXT NOT NULL",
    "review_status TEXT NOT NULL DEFAULT 'confirmed'",
    "source TEXT NOT NULL DEFAULT 'person'",
    "batch_id INTEGER",
    "edited_by_person INTEGER NOT NULL DEFAULT 0",
    "deleted_at TEXT",
]
SYSTEM_COLUMN_NAMES = {c.split()[0] for c in SYSTEM_COLUMNS_SQL}


class SchemaChangeError(PlainError):
    """A change to tables.toml cannot be turned into a migration automatically."""


def table_name(module: str, table: str) -> str:
    """The real database table name for a module's table, e.g. pets__weights."""
    return f"{module}__{table}"


def target_table(module: str, column: Column) -> str:
    """The real table a link column points at."""
    if "." in column.to:
        other, _, name = column.to.partition(".")
        return table_name(other, name)
    return table_name(module, column.to)


def join_table_name(module: str, table: str, column: str) -> str:
    """The table holding a many-to-many ('links') column."""
    return f"{module}__{table}__{column}"


def column_sql(module: str, column: Column) -> str:
    """The SQL definition of one declared column. Rules such as 'required' are checked by
    the program when saving, so they can change without rebuilding the table."""
    sql = f"{column.name} {SQL_TYPES[column.type]}"
    if column.type == "link":
        sql += f" REFERENCES {target_table(module, column)}(id) ON DELETE {ON_DELETE_SQL[column.on_delete]}"
    return sql


def _indexes(module: str, table: Table, columns) -> list[str]:
    real = table_name(module, table.name)
    return [f"CREATE INDEX {real}__{c.name}__idx ON {real}({c.name});"
            for c in columns if c.type in ("link", "date", "datetime")]


def _join_table(module: str, table: Table, column: Column) -> str:
    real = table_name(module, table.name)
    return (f"CREATE TABLE {join_table_name(module, table.name, column.name)} (\n"
            f"    from_id INTEGER NOT NULL REFERENCES {real}(id) ON DELETE CASCADE,\n"
            f"    to_id INTEGER NOT NULL REFERENCES {target_table(module, column)}(id) ON DELETE CASCADE,\n"
            f"    PRIMARY KEY (from_id, to_id)\n);")


def create_table_sql(module: str, table: Table) -> list[str]:
    """SQL to create a declared table, its indexes and any many-to-many tables."""
    stored = [c for c in table.columns.values() if c.type != "links"]
    lines = SYSTEM_COLUMNS_SQL + [column_sql(module, c) for c in stored]
    body = ",\n    ".join(lines)
    statements = [f"-- {table.title}\nCREATE TABLE {table_name(module, table.name)} (\n    {body}\n);"]
    statements += _indexes(module, table, stored)
    statements += [_join_table(module, table, c) for c in table.columns.values() if c.type == "links"]
    return statements


def existing_schema(module: Module) -> dict[str, list[str]]:
    """Replay the module's committed migrations in memory and return {table: [columns]}."""
    conn = sqlite3.connect(":memory:")
    try:
        for migration in module.migrations:
            for statement in db.split_statements(migration.sql):
                conn.execute(statement)
        prefix = f"{module.name}__"
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE ? ESCAPE '\\'",
            (prefix.replace("_", "\\_") + "%",))]
        return {n: [r[1] for r in conn.execute(f"PRAGMA table_info({n})")] for n in names}
    finally:
        conn.close()


def next_migration_sql(module: Module) -> str | None:
    """SQL for the next migration so the database matches tables.toml, or None if it already does.

    Only additions are automatic (new tables, new columns). Removing or renaming
    needs a hand-written migration, because it can lose data.
    """
    existing = existing_schema(module)
    expected_tables = {}
    for table in module.tables.values():
        expected_tables[table_name(module.name, table.name)] = table
    expected_joins = {join_table_name(module.name, t.name, c.name)
                      for t in module.tables.values() for c in t.columns.values() if c.type == "links"}

    problems = []
    for name, columns in existing.items():
        if name in expected_joins:
            continue
        if name not in expected_tables:
            problems.append(f"the table '{name}' exists in earlier migrations but is no longer in tables.toml")
            continue
        declared = {c.name for c in expected_tables[name].columns.values() if c.type != "links"}
        for column in columns:
            if column not in declared and column not in SYSTEM_COLUMN_NAMES:
                problems.append(f"the column '{name}.{column}' is no longer in tables.toml")
    if problems:
        raise SchemaChangeError(
            "These changes remove or rename something, which could lose data, so they need a hand-written "
            "migration: " + "; ".join(problems) + "."
        )

    statements: list[str] = []
    for name, table in expected_tables.items():
        if name not in existing:
            statements += create_table_sql(module.name, table)
            continue
        new = [c for c in table.columns.values() if c.type != "links" and c.name not in existing[name]]
        statements += [f"ALTER TABLE {name} ADD COLUMN {column_sql(module.name, c)};" for c in new]
        statements += _indexes(module.name, table, new)
        statements += [_join_table(module.name, table, c) for c in table.columns.values()
                       if c.type == "links" and join_table_name(module.name, table.name, c.name) not in existing]
    if not statements:
        return None
    header = (f"-- Generated by tools/make_migration.py from modules/{module.name}/tables.toml.\n"
              "-- Released migrations must never be edited; make a new one instead.\n\n")
    return header + "\n\n".join(statements) + "\n"
