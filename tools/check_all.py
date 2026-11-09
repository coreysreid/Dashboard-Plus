"""Run every check a change must pass before it is pushed, with one command."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("Privacy check", [sys.executable, "tools/check_privacy.py"]),
    ("Index check", [sys.executable, "tools/check_indexes.py"]),
    ("Project map is up to date", [sys.executable, "tools/make_project_map.py", "--check"]),
    ("Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]),
]


def main() -> int:
    """Run each check in turn and print a one-line verdict for each; return 1 if any failed."""
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    failed = []
    for name, command in CHECKS:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"PASS  {name}")
        else:
            failed.append(name)
            print(f"FAIL  {name}")
            print((result.stdout + result.stderr).strip()[-3000:])
    if failed:
        print(f"\n{len(failed)} check(s) failed. Fix them before pushing.")
        if "Project map is up to date" in failed:
            print("For the project map, run: python tools/make_project_map.py")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
