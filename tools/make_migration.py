"""Write a module's next numbered migration from its tables.toml."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dashboard.core.modules import ModuleError, load_module  # noqa: E402
from dashboard.core.schema import SchemaChangeError, next_migration_sql  # noqa: E402


def make(module_dir: Path, name: str) -> Path | None:
    """Write the next migration for the module in `module_dir`; return its path, or None if up to date."""
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise SystemExit("The migration name must use lower-case letters, digits and underscores.")
    module = load_module(module_dir)
    sql = next_migration_sql(module)
    if sql is None:
        return None
    folder = Path(module_dir) / "migrations"
    folder.mkdir(exist_ok=True)
    path = folder / f"{len(module.migrations) + 1:04d}_{name}.sql"
    path.write_text(sql, encoding="utf-8", newline="\n")
    return path


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", help="the module's folder name, e.g. people")
    parser.add_argument("--name", default="update_tables", help="a short name for the migration file")
    parser.add_argument("--modules-dir", default=str(ROOT / "modules"))
    args = parser.parse_args(argv)
    try:
        path = make(Path(args.modules_dir) / args.module, args.name)
    except ModuleError as error:
        print("The module's files need fixing first:")
        for problem in error.problems:
            print(f"  - {problem}")
        return 1
    except SchemaChangeError as error:
        print(str(error))
        return 1
    if path is None:
        print("Nothing to do: the migrations already match tables.toml.")
    else:
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
