"""Choose the data folder: --data if given, Application Support inside a Mac app, else ./data."""
from __future__ import annotations

import os
import sys
from pathlib import Path, PurePath

from dashboard.errors import PlainError

APP_FOLDER_NAME = "Dashboard Plus"
PACKAGE_FILE = Path(__file__).resolve()


class DataFolderError(PlainError):
    """The data folder chosen cannot be used safely."""


def app_bundle(package_file: PurePath | None = None) -> PurePath | None:
    """The `.app` folder this program runs from on a Mac (such as Dashboard Plus.app), or None.

    A Mac app is a folder named `<name>.app` with a `Contents` folder inside; the program's code
    sits somewhere below `Contents`. Only the path is looked at, so tests can pass a made-up one."""
    path = _as_path(PACKAGE_FILE if package_file is None else package_file)
    parts = path.parts
    for i in range(len(parts) - 1):
        if parts[i].endswith(".app") and len(parts[i]) > 4 and parts[i + 1] == "Contents":
            return type(path)(*parts[: i + 1])  # the same kind of path that was given, on any system
    return None


def _as_path(value) -> PurePath:
    """Keep a given path's own kind (a Mac path stays a Mac path when tests run on Windows)."""
    return value if isinstance(value, PurePath) else PurePath(value)


def mac_application_support(home: PurePath) -> PurePath:
    """This Mac account's own folder for program data: ~/Library/Application Support/Dashboard Plus."""
    return _as_path(home) / "Library" / "Application Support" / APP_FOLDER_NAME


def default_data_dir(platform: str | None = None, package_file: PurePath | None = None,
                     home: PurePath | None = None) -> PurePath:
    """Where the records live when no --data is given (decision 0096).

    Inside a Mac app: the account's Application Support folder, never inside the app, so the app
    can be replaced (or run from a read-only place) without touching the records. Everywhere else
    (the Windows folder always passes --data; running from source): `data` in the current folder,
    as before, so nobody's existing records move."""
    platform = sys.platform if platform is None else platform
    if platform == "darwin" and app_bundle(package_file) is not None:
        return mac_application_support(Path.home() if home is None else home)
    return PurePath("data")


def check_not_in_bundle(data_dir: Path, package_file: PurePath | None = None) -> None:
    """Refuse a data folder inside the Mac app: replacing the app would delete the records."""
    bundle = app_bundle(package_file)
    if bundle is None:
        return
    bundle_path = Path(bundle).resolve()
    data = Path(data_dir).resolve()
    if data == bundle_path or bundle_path in data.parents:
        raise DataFolderError(
            "Dashboard Plus will not keep your records inside the app itself, because replacing the "
            "app would delete them. Leave out --data to use this Mac's Application Support folder.")


def prepare(data_dir: Path) -> Path:
    """Make the data folder if it is missing, private to this computer account (folder 0700)."""
    data_dir = Path(data_dir)
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        try:
            data_dir.chmod(0o700)
        except OSError:
            pass  # a drive that does not keep permissions (such as a FAT USB stick) is left as it is
    return data_dir
