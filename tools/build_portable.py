"""Build the portable Windows folder and zip: bundled Python, libraries and launchers."""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER_NAME = "Dashboard Plus"

OPEN_BAT = r"""@echo off
rem Starts Dashboard Plus with the Python bundled in this folder.
rem It does not install anything or change any settings on this computer.
cd /d "%~dp0"
title Dashboard Plus
"%~dp0app\python\python.exe" -m dashboard --data "%~dp0data"
if errorlevel 1 pause
"""

CLOSE_BAT = r"""@echo off
rem Closes Dashboard Plus safely so the drive can be unplugged.
cd /d "%~dp0"
"%~dp0app\python\python.exe" -m dashboard --data "%~dp0data" --close
pause
"""

README_TXT = """Dashboard Plus
==============

Look after what your household has.

To start:   double-click "Open Dashboard".
To stop:    double-click "Close Dashboard safely" (or use the button on the page)
            before you unplug a USB drive.

Your records are kept in the "data" folder next to these files. Nothing is sent
anywhere. To update the program, replace everything except the "data" folder.

The first time you open it, Windows may say "Windows protected your PC" because
this free program is not signed by a paid certificate. Choose "More info", then
"Run anyway". The program only listens on this computer.

This is an early test version.
"""


class BuildError(Exception):
    """A problem the person building the folder needs to fix."""


def load_config(path: Path = ROOT / "tools" / "portable.toml") -> dict:
    """Read the pinned Python version, download address and checksum."""
    with open(path, "rb") as handle:
        return tomllib.load(handle)["python"]


def program_version() -> str:
    """Read the program's version from the package without importing it."""
    text = (ROOT / "src" / "dashboard" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise BuildError("Could not find __version__ in src/dashboard/__init__.py")
    return match.group(1)


def sha256_of(path: Path) -> str:
    """Return the sha256 checksum of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path: Path, expected: str, require_pinned: bool) -> str:
    """Check a download against its pinned checksum; return the actual checksum."""
    actual = sha256_of(path)
    if expected:
        if actual != expected.lower():
            raise BuildError(f"Checksum mismatch for {path.name}: expected {expected}, got {actual}")
    elif require_pinned:
        raise BuildError(f"No checksum is pinned in tools/portable.toml. The download's checksum is {actual}")
    else:
        print(f"WARNING: no checksum pinned yet. Downloaded file checksum: {actual}")
    return actual


def download(url: str, dest: Path) -> None:
    """Download a file."""
    print(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)


def write_pth(python_dir: Path) -> Path:
    """Tell the bundled Python where our code and libraries are, and nothing else."""
    candidates = sorted(python_dir.glob("python3*._pth"))
    if not candidates:
        raise BuildError("The Python download has no ._pth file; is it the embeddable package?")
    pth = candidates[0]
    stdlib_zip = pth.name.replace("._pth", ".zip")
    pth.write_text(
        "\n".join([stdlib_zip, ".", r"..\lib", r"..\src",
                   "# 'import site' is left off on purpose: nothing outside this folder is used."]) + "\n",
        encoding="utf-8",
    )
    return pth


def install_libraries(lib_dir: Path, lock: Path, python_version: str) -> None:
    """Install the pinned Windows libraries, checking every checksum."""
    major_minor = ".".join(python_version.split(".")[:2])
    tag = "cp" + major_minor.replace(".", "")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-compile", "--no-deps",
         "--require-hashes", "--only-binary=:all:", "--platform", "win_amd64",
         "--python-version", major_minor, "--implementation", "cp", "--abi", tag,
         "--target", str(lib_dir), "-r", str(lock)],
        check=True,
    )
    # pip adds command-line wrappers we never use; leave them out of the folder.
    shutil.rmtree(lib_dir / "bin", ignore_errors=True)


def copy_program(app_dir: Path) -> None:
    """Copy our own code and the shipped modules into the folder."""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "src" / "dashboard", app_dir / "src" / "dashboard", ignore=ignore)
    shutil.copytree(ROOT / "modules", app_dir / "modules", ignore=ignore)


def write_text_crlf(path: Path, text: str) -> None:
    """Write a file with Windows line endings (batch files need them)."""
    path.write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def make_zip(folder: Path, zip_path: Path) -> None:
    """Zip the folder so it unpacks as a single 'Dashboard Plus' folder."""
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(folder.rglob("*")):
            arcname = Path(folder.name) / item.relative_to(folder)
            archive.write(item, arcname.as_posix())


def build(out: Path, python_zip: Path | None = None, skip_libraries: bool = False,
          require_pinned: bool = False, config: dict | None = None) -> Path:
    """Build the folder and the zip in `out`; return the zip's path.

    `config` replaces tools/portable.toml; tests use it to pin a stand-in download.
    """
    config = config if config is not None else load_config()
    out = Path(out)
    folder = out / FOLDER_NAME
    if folder.exists():
        shutil.rmtree(folder)
    app_dir = folder / "app"
    python_dir = app_dir / "python"
    python_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(python_zip) if python_zip else Path(tmp) / "python-embed.zip"
        if not python_zip:
            download(config["url"], source)
        verify(source, config.get("sha256", ""), require_pinned)
        with zipfile.ZipFile(source) as archive:
            archive.extractall(python_dir)
    write_pth(python_dir)

    lib_dir = app_dir / "lib"
    lib_dir.mkdir()
    if not skip_libraries:
        install_libraries(lib_dir, ROOT / "requirements.lock", config["version"])
    copy_program(app_dir)
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE.txt")
    write_text_crlf(folder / "READ ME FIRST.txt", README_TXT)
    write_text_crlf(folder / "Open Dashboard.bat", OPEN_BAT)
    write_text_crlf(folder / "Close Dashboard safely.bat", CLOSE_BAT)

    zip_path = out / f"Dashboard-Plus-{program_version()}-windows.zip"
    if zip_path.exists():
        zip_path.unlink()
    make_zip(folder, zip_path)
    print(f"Built {folder} and {zip_path.name}")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "dist"))
    parser.add_argument("--python-zip", help="use this embeddable Python zip instead of downloading")
    parser.add_argument("--skip-libraries", action="store_true", help="for tests: do not install libraries")
    parser.add_argument("--release", action="store_true", help="refuse to build without a pinned checksum")
    args = parser.parse_args(argv)
    try:
        build(Path(args.out), Path(args.python_zip) if args.python_zip else None,
              args.skip_libraries, require_pinned=args.release)
    except (BuildError, subprocess.CalledProcessError, OSError) as error:
        print(f"Build failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
