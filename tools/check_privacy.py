"""Fail the build if anything private or machine-specific is committed."""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repofiles import repo_files  # noqa: E402

FORBIDDEN_SUFFIXES = (
    ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".db-journal",
    ".pem", ".key", ".pfx", ".p12",
)
FORBIDDEN_NAMES = {"config.toml"}
FORBIDDEN_TOP_FOLDERS = {"data", "secrets"}
MAX_SCAN_BYTES = 2_000_000

# Words that are clearly placeholders when they appear as a user folder name.
PLACEHOLDER_USERS = {
    "name", "yourname", "your-name", "your_name", "username", "example", "you",
    "someone", "me", "public", "default", "all",
}
PLACEHOLDER_EMAIL_DOMAINS = {
    "example.com", "example.org", "example.net", "users.noreply.github.com",
}
PLACEHOLDER_HINTS = (
    "example", "your", "xxxx", "changeme", "placeholder", "<", "dummy",
    "sample", "redacted", "token_here",
)

# Patterns are written so that this file does not match them itself.
SECRET_PATTERNS = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key", re.compile("-----BEGIN" + r" (?:[A-Z]+ )*PRIVATE KEY")),
    ("bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{30,}")),
]
SECRET_ASSIGNMENT = re.compile(
    r"""(?ix)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b["']?\s*[:=]\s*["']?([A-Za-z0-9+/_-]{24,})"""
)
WINDOWS_PATH = re.compile(r"""(?i)\b[a-z]:[\\/]+users[\\/]+([^\\/\s"'<>*:]+)""")
MAC_PATH = re.compile(r"""(?<![\w.])/Us""" + r"""ers/([^/\s"'<>*]+)""")
LINUX_PATH = re.compile(r"""(?<![\w.])/ho""" + r"""me/([^/\s"'<>*]+)""")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")


@dataclass
class Finding:
    path: str
    line: int
    reason: str
    excerpt: str = ""

    def __str__(self) -> str:
        where = self.path if not self.line else f"{self.path}:{self.line}"
        extra = f" ({self.excerpt})" if self.excerpt else ""
        return f"{where}: {self.reason}{extra}"


def mask(value: str) -> str:
    """Show only the start of a suspicious value so the report does not leak it."""
    return f"{value[:3]}... {len(value)} characters"


def check_name(path: str) -> list[Finding]:
    """Flag files that must never be committed, judged by name and location."""
    parts = path.split("/")
    name = parts[-1].lower()
    problems = []
    if name.endswith(FORBIDDEN_SUFFIXES):
        problems.append("database, key or certificate file")
    if name in FORBIDDEN_NAMES:
        problems.append("real config file (only config.example.toml may be committed)")
    if name.startswith(".env") and name != ".env.example":
        problems.append("environment file")
    if len(parts) > 1 and parts[0].lower() in FORBIDDEN_TOP_FOLDERS:
        problems.append("belongs in the data folder, which is never committed")
    return [Finding(path, 0, p) for p in problems]


def check_text(path: str, text: str) -> list[Finding]:
    """Flag secrets, personal paths and real email addresses inside a text file."""
    problems: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                problems.append(Finding(path, number, f"looks like a {label}", mask(match.group(0))))
        assign = SECRET_ASSIGNMENT.search(line)
        if assign:
            value = assign.group(1)
            lowered = value.lower()
            looks_real = (
                any(c.isdigit() for c in value)
                and any(c.isalpha() for c in value)
                and not any(h in lowered for h in PLACEHOLDER_HINTS)
                and not any(h in line.lower() for h in PLACEHOLDER_HINTS)
            )
            if looks_real:
                problems.append(Finding(path, number, "looks like a secret value", mask(value)))
        for label, pattern in (
            ("Windows user folder", WINDOWS_PATH),
            ("Mac user folder", MAC_PATH),
            ("Linux home folder", LINUX_PATH),
        ):
            for match in pattern.finditer(line):
                if match.group(1).lower() not in PLACEHOLDER_USERS:
                    problems.append(Finding(path, number, f"personal path ({label})", mask(match.group(0))))
        for match in EMAIL.finditer(line):
            if match.group(1).lower() not in PLACEHOLDER_EMAIL_DOMAINS:
                problems.append(Finding(path, number, "real-looking email address", mask(match.group(0))))
    return problems


def scan(root: Path) -> list[Finding]:
    """Scan every file in the repository and return everything suspicious."""
    root = Path(root)
    problems: list[Finding] = []
    for path in repo_files(root):
        problems.extend(check_name(path))
        full = root / path
        try:
            if full.stat().st_size > MAX_SCAN_BYTES:
                continue
            data = full.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue
        problems.extend(check_text(path, data.decode("utf-8", errors="replace")))
    return problems


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns 1 when anything suspicious is found."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    problems = scan(Path(args.root))
    if problems:
        print("Privacy check FAILED. This repository is public, so none of this may be committed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("Privacy check passed: no databases, secrets, personal paths or real emails found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
