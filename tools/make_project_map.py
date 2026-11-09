"""Build PROJECT_MAP.md from every INDEX.md in the repository."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repofiles import read_text, repo_files  # noqa: E402

# The second agent's workbench changes often and is not part of the program, so it is
# left out of the map; this keeps its work from conflicting with everyone else's.
EXCLUDED = ("workbench/",)

HEADER = """# Project map

Every part of the project in one page. Generated from the `INDEX.md` in each
folder by `tools/make_project_map.py`; do not edit by hand. To change a
description, edit the folder's `INDEX.md` and run the tool again.
"""


def build(root: Path) -> str:
    """Return the full text of the project map."""
    root = Path(root)
    indexes = [f for f in repo_files(root) if f.split("/")[-1] == "INDEX.md"
               and not any(p.startswith(".") for p in f.split("/"))
               and not f.startswith(EXCLUDED)]
    indexes.sort(key=lambda f: ("/".join(f.split("/")[:-1])))
    parts = [HEADER.rstrip("\n")]
    for rel in indexes:
        lines = read_text(root / rel).strip("\n").splitlines()
        if not lines:
            continue
        title = lines[0].lstrip("#").strip() if lines[0].startswith("#") else rel
        body = lines[1:] if lines[0].startswith("#") else lines
        parts.append(f"## {title}\n" + "\n".join(body).strip("\n"))
    return "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the map, or with --check, fail if the written map is out of date."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--check", action="store_true", help="fail if PROJECT_MAP.md is stale")
    args = parser.parse_args(argv)
    root = Path(args.root)
    target = root / "PROJECT_MAP.md"
    expected = build(root)
    if args.check:
        current = read_text(target) if target.exists() else ""
        if current != expected:
            print("PROJECT_MAP.md is out of date. Run: python tools/make_project_map.py")
            return 1
        print("Project map is up to date.")
        return 0
    target.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {target.name} from {expected.count('## ')} indexes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
