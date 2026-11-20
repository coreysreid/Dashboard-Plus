"""Prepare the database at start-up: load modules, back up if needed, and migrate."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dashboard.core import db, helpers, migrations, modules

log = logging.getLogger("dashboard.startup")
DATABASE_FILE = "dashboard.db"
DEFAULT_MODULES_DIR = Path(__file__).resolve().parents[3] / "modules"


@dataclass
class StartupReport:
    """What happened at start-up, for the home page and the log."""
    database: Path
    version: int
    applied: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    module_problems: dict[str, list[str]] = field(default_factory=dict)
    loaded: list = field(default_factory=list, repr=False)  # the Module objects in use


def database_path(data_dir: Path) -> Path:
    return Path(data_dir) / DATABASE_FILE


def _missing_columns(conn, module) -> list[str]:
    """Tables and columns a module declares that are not in the database (its migrations are behind)."""
    from dashboard.core.schema import table_name
    missing = []
    for table in module.tables.values():
        name = table_name(module.name, table.name)
        have = {row[1] for row in conn.execute(f"PRAGMA table_info({name})")}
        if not have:
            missing.append(f"the table '{table.name}'")
            continue
        missing += [f"'{table.name}.{c}'" for c in table.columns
                    if c not in have and table.columns[c].type != "links"]
    return missing


def record_modules(conn, found: list) -> None:
    """Note each module in use and its version; a module seen for the first time starts switched on."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.transaction(conn):
        for module in found:
            conn.execute(
                "INSERT INTO core__modules (name, version, enabled, first_seen_at, updated_at) "
                "VALUES (?, ?, 1, ?, ?) ON CONFLICT(name) DO UPDATE SET version = excluded.version, "
                "updated_at = excluded.updated_at",
                (module.name, module.version, now, now),
            )


def prepare(data_dir: Path, modules_dir: Path | None = None) -> StartupReport:
    """Open the database, bring it up to date, and record the modules in use.

    A module with mistakes is left out and reported; it never stops the others.
    Problems that make the database unsafe raise a PlainError instead.
    """
    data_dir = Path(data_dir)
    found, failures = modules.discover(Path(modules_dir) if modules_dir else DEFAULT_MODULES_DIR)
    tracks = {migrations.CORE_TRACK: migrations.load_track(migrations.CORE_TRACK, migrations.CORE_FOLDER)}
    # Second safety net (decision 0069): module loading already refuses the name "core", but if one ever got
    # through it must not replace the program's own track or run its own migrations.
    for module in [m for m in found if m.name == migrations.CORE_TRACK]:
        failures.setdefault(module.name, []).append("'core' is reserved for the program itself, so this module was left out.")
    found = [m for m in found if m.name != migrations.CORE_TRACK]
    for module in found:
        tracks[module.name] = module.migrations
    path = database_path(data_dir)
    conn = db.connect(path)
    try:
        # One backup before anything changes, then the core must update; a module whose update fails is
        # left out and reported, like any broken module.
        if migrations.plan(conn, tracks) and any(migrations.applied(conn).values()):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            db.backup_to(conn, data_dir / "backups" / f"before-update-{stamp}.db")
        applied = migrations.migrate(conn, {migrations.CORE_TRACK: tracks[migrations.CORE_TRACK]})
        for module in list(found):
            try:
                applied += migrations.migrate(conn, {module.name: module.migrations})
            except migrations.MigrationError as error:
                failures.setdefault(module.name, []).append(f"Its database change could not be applied, so it "
                                                            f"was left out and its records were not changed. {error}")
                continue
            missing = _missing_columns(conn, module)
            if missing:
                failures.setdefault(module.name, []).append(
                    f"Its tables.toml describes {', '.join(missing)}, which its migrations do not create. "
                    f"Run tools/make_migration.py for it.")
        found = modules.dependency_order([m for m in found if m.name not in failures], failures)
        record_modules(conn, found)
        stopped = helpers.stop_unfinished_key_changes(conn, data_dir)  # decision 0093
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    for name, problems in failures.items():
        log.warning("Module %s was left out: %s", name, " ".join(problems))
    for item in applied:
        log.info("Applied database change %s", item.label)
    if stopped:
        log.warning("A helper key change did not finish; %d helper(s) need a new key", len(stopped))
    return StartupReport(database=path, version=version, applied=[m.label for m in applied],
                         modules=[m.name for m in found], module_problems=failures, loaded=found)
