"""Check that every folder has a short, complete and current INDEX.md."""
from __future__ import annotations

import argparse
import ast
import fnmatch
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repofiles import read_text, repo_files  # noqa: E402

MAX_LINES = 25
# Folders that hold a long catalogue of similar items may exceed the usual limit.
LINE_LIMIT_OVERRIDES = {"docs/decisions": 80}
PLACEHOLDER = "DESCRIBE ME"
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


def is_ignored(name: str) -> bool:
    """Hidden files, caches and compiled files need no index entry."""
    return name.startswith(".") or name == "__pycache__" or name.endswith(".pyc")


def normalise(text: str) -> str:
    """Collapse whitespace and case so a quoted summary can be matched loosely."""
    return " ".join(text.split()).casefold()


def parse_rows(text: str) -> list[tuple[str, str]]:
    """Return (entry name, whole row text) for each data row of the index table."""
    rows: list[tuple[list[str], str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(SEPARATOR_CELL.match(c) for c in cells if c):
            if rows:
                rows.pop()  # the row above a separator is the table header
            continue
        rows.append((cells, stripped))
    entries = []
    for cells, raw in rows:
        first = cells[0]
        link = LINK.search(first)
        name = link.group(1) if link else first
        name = name.strip().strip("`").strip()
        if name.startswith("./"):
            name = name[2:]
        entries.append((name, raw))
    return entries


def build_tree(files: list[str]) -> dict[str, dict[str, set[str]]]:
    """Map each folder ('' is the root) to the files and subfolders directly inside."""
    tree: dict[str, dict[str, set[str]]] = {"": {"files": set(), "dirs": set()}}
    for path in files:
        parts = path.split("/")
        for i, part in enumerate(parts):
            parent = "/".join(parts[:i])
            tree.setdefault(parent, {"files": set(), "dirs": set()})
            if i == len(parts) - 1:
                tree[parent]["files"].add(part)
            else:
                tree[parent]["dirs"].add(part)
                tree.setdefault("/".join(parts[: i + 1]), {"files": set(), "dirs": set()})
    return tree


def python_summary(path: Path) -> str | None:
    """Return the first line of a Python file's module docstring, if it has one."""
    try:
        doc = ast.get_docstring(ast.parse(read_text(path)))
    except (SyntaxError, OSError):
        return None
    if not doc:
        return None
    for line in doc.splitlines():
        if line.strip():
            return line.strip()
    return None


def check_folder(root: Path, folder: str, node: dict[str, set[str]]) -> list[str]:
    """Return the problems with one folder's INDEX.md (empty list means fine)."""
    label = folder or "(root)"
    index_rel = f"{folder}/INDEX.md" if folder else "INDEX.md"
    if "INDEX.md" not in node["files"]:
        return [f"{label}: no INDEX.md"]
    text = read_text(root / index_rel)
    problems = []
    limit = LINE_LIMIT_OVERRIDES.get(folder, MAX_LINES)
    count = len(text.splitlines())
    if count > limit:
        problems.append(f"{label}: INDEX.md is {count} lines; the limit is {limit}")
    if PLACEHOLDER in text:
        problems.append(f"{label}: INDEX.md still contains the placeholder '{PLACEHOLDER}'")

    visible_files = {f for f in node["files"] if not is_ignored(f) and f != "INDEX.md"}
    visible_dirs = {d for d in node["dirs"] if not is_ignored(d)}
    visible = visible_files | visible_dirs
    everything = node["files"] | node["dirs"]

    rows = parse_rows(text)
    covered: set[str] = set()
    row_for: dict[str, str] = {}
    for name, raw in rows:
        base = name.rstrip("/")
        if any(ch in base for ch in "*?["):
            matches = {v for v in visible if fnmatch.fnmatch(v, base)}
            if not matches:
                problems.append(f"{label}: INDEX.md lists '{name}' but nothing matches it")
            covered |= matches
        elif base in everything:
            covered.add(base)
            row_for[base] = raw
        else:
            problems.append(f"{label}: INDEX.md lists '{name}' which does not exist (stale entry)")
    for missing in sorted(visible - covered):
        problems.append(f"{label}: '{missing}' is not listed in INDEX.md")

    for filename in sorted(visible_files):
        if not filename.endswith(".py"):
            continue
        full = root / folder / filename if folder else root / filename
        summary = python_summary(full)
        rel = f"{folder}/{filename}" if folder else filename
        if summary is None:
            problems.append(f"{rel}: the file must start with a one-line summary (a module docstring)")
        elif filename in row_for and normalise(summary) not in normalise(row_for[filename]):
            problems.append(f"{label}: the INDEX.md row for '{filename}' must quote its summary: {summary}")
    return problems


def check(root: Path) -> list[str]:
    """Check every non-hidden folder in the repository."""
    root = Path(root)
    tree = build_tree(repo_files(root))
    problems: list[str] = []
    for folder in sorted(tree):
        if any(is_ignored(part) for part in folder.split("/") if part):
            continue
        problems.extend(check_folder(root, folder, tree[folder]))
    return problems


def skeleton(root: Path) -> str:
    """Print table rows for entries missing from each INDEX.md, ready to describe."""
    root = Path(root)
    tree = build_tree(repo_files(root))
    out = []
    for folder in sorted(tree):
        if any(is_ignored(part) for part in folder.split("/") if part):
            continue
        node = tree[folder]
        visible = {n for n in node["files"] | node["dirs"] if not is_ignored(n) and n != "INDEX.md"}
        index_rel = f"{folder}/INDEX.md" if folder else "INDEX.md"
        listed: set[str] = set()
        if "INDEX.md" in node["files"]:
            listed = {n.rstrip("/") for n, _ in parse_rows(read_text(root / index_rel))}
        todo = sorted(visible - listed)
        if todo:
            out.append(f"## {folder or '(root)'}")
            for name in todo:
                suffix = "/" if name in node["dirs"] else ""
                out.append(f"| {name}{suffix} | {PLACEHOLDER} | {PLACEHOLDER} |")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns 1 when any index is wrong."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--skeleton", action="store_true", help="print rows for missing entries")
    args = parser.parse_args(argv)
    if args.skeleton:
        print(skeleton(Path(args.root)))
        return 0
    problems = check(Path(args.root))
    if problems:
        print("Index check FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        print("Tip: run with --skeleton to see rows for entries that are missing.")
        return 1
    print("Index check passed: every folder has a complete, current INDEX.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
