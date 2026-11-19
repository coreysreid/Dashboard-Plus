"""Where the connector finds Dashboard Plus and its key: two environment values or a small file, checked before use."""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

URL_VARIABLE = "DASHBOARD_PLUS_URL"
KEY_VARIABLE = "DASHBOARD_PLUS_KEY"
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
API_PATHS = {"", "/", "/api/v1", "/api/v1/"}
KEY_SHAPE = re.compile(r"^dph_[A-Za-z0-9_-]{8,100}$")
WHERE = "Copy it from Settings, Helpers in Dashboard Plus."


@dataclass(frozen=True)
class Settings:
    """What the connector needs to call the helper API. `problem` says, in plain words, why it cannot."""
    base: str | None = None  # http://127.0.0.1:<port>/api/v1, never with the key in it
    key: str | None = field(default=None, repr=False)  # never printed, logged or returned
    problem: str | None = None


def check_url(text: str | None) -> tuple[str | None, str | None]:
    """Return (the API address, None) for an address on this computer, or (None, the reason it is refused).

    Only `http://127.0.0.1:<port>` or `http://localhost:<port>` is accepted, optionally ending in `/api/v1`.
    Anything else could send the key to another computer, so it is never contacted."""
    if not text or not text.strip():
        return None, f"The address of Dashboard Plus is missing ({URL_VARIABLE}). {WHERE}"
    refused = ("The connector only talks to Dashboard Plus on this computer, at an address like "
               "http://127.0.0.1:5123/api/v1. " + WHERE)
    try:
        parts = urlsplit(text.strip())
        port = parts.port
    except ValueError:
        return None, refused
    if (parts.scheme != "http" or parts.hostname not in LOCAL_HOSTS or parts.username is not None
            or parts.password is not None or port is None or not 1 <= port <= 65535 or parts.query
            or parts.fragment or parts.path not in API_PATHS or "@" in parts.netloc):
        return None, refused
    return f"http://{parts.hostname}:{port}/api/v1", None


def check_key(text: str | None) -> tuple[str | None, str | None]:
    """Return (the key, None) if it has the shape of a helper key, or (None, the reason). Never repeats it."""
    if not text or not text.strip():
        return None, f"The helper key is missing ({KEY_VARIABLE}). Make one in Settings, Helpers in Dashboard Plus."
    key = text.strip()
    if not KEY_SHAPE.match(key):
        return None, ("The helper key does not look right: it should start with dph_. "
                      "Copy it again, or make a new one in Settings, Helpers.")
    return key, None


def _read_file(path: Path) -> tuple[dict, str | None]:
    try:
        with open(path, "rb") as handle:
            raw = tomllib.load(handle)
    except OSError:
        return {}, "The connector's settings file could not be opened. Check the path given after --config."
    except tomllib.TOMLDecodeError:
        return {}, ('The connector\'s settings file could not be read. It needs two lines: '
                    'url = "http://127.0.0.1:<port>/api/v1" and key = "<your key>".')
    return {k: v for k, v in raw.items() if k in ("url", "key") and isinstance(v, str)}, None


def load(config_path: str | None = None, environ: dict | None = None) -> Settings:
    """Read the address and key: from the file given by --config, then the environment, which wins.

    Tool calls can never change either: an assistant cannot point the connector somewhere else."""
    environ = os.environ if environ is None else environ
    values, problem = ({}, None) if not config_path else _read_file(Path(config_path))
    if problem:
        return Settings(problem=problem)
    url = environ.get(URL_VARIABLE) or values.get("url")
    base, problem = check_url(url)
    if problem:
        return Settings(problem=problem)
    key, problem = check_key(environ.get(KEY_VARIABLE) or values.get("key"))
    if problem:
        return Settings(problem=problem)
    return Settings(base=base, key=key)


def readable_by_others(config_path: str | None) -> bool:
    """True if the settings file holding the key can be read by other people using this computer (POSIX only)."""
    if not config_path or os.name != "posix":
        return False
    try:
        return bool(Path(config_path).stat().st_mode & 0o077)
    except OSError:
        return False
