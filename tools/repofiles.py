"""Shared helper that lists the files belonging to the repository."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def repo_files(root: Path) -> list[str]:
    """Return repository-relative file paths using forward slashes.

    Inside a git checkout this is every file that is committed or waiting to be
    committed, and nothing that .gitignore excludes. Elsewhere (for example in
    a test folder) it is every file under the root except git's own folder.
    """
    root = Path(root)
    if (root / ".git").exists():
        try:
            result = subprocess.run(
                ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                cwd=root,
                capture_output=True,
                check=True,
            )
            names = [n for n in result.stdout.decode("utf-8").split("\0") if n]
            return sorted(n for n in names if (root / n).is_file())
        except (OSError, subprocess.CalledProcessError):
            pass
    found: list[str] = []
    for folder, subfolders, filenames in os.walk(root):
        subfolders[:] = [d for d in subfolders if d not in {".git", "__pycache__"}]
        for filename in filenames:
            found.append(Path(folder, filename).relative_to(root).as_posix())
    return sorted(found)


def read_text(path: Path) -> str:
    """Read a text file as UTF-8 with Windows line endings normalised."""
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
