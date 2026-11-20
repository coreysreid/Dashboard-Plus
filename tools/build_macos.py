"""Build the unsigned Mac app and zip (Dashboard Plus.app) for this Mac's processor: bundled Python, libraries, launcher."""
from __future__ import annotations

import argparse
import os
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_portable import BuildError, copy_program, download, program_version, verify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FOLDER_NAME = "Dashboard Plus"
APP_NAME = "Dashboard Plus.app"
BUNDLE_ID = "io.github.coreysreid.dashboard-plus"
MINIMUM_MACOS = "11.0"  # the first macOS for Apple silicon; python-build-standalone supports it
ARCHES = {"arm64": "Apple silicon", "x86_64": "Intel"}

# The app's main program. Finder starts it with no arguments; it starts the bundled Python in the
# background, waits a little to see whether that worked, and says so in a window if it did not.
# Leaving straight away matters: macOS will not start an app again while it is still running, and
# opening the app again is how the browser page comes back (the program then just reopens it).
LAUNCHER = """#!/bin/sh
# Starts Dashboard Plus with the Python inside this app. It installs nothing and changes no settings.
# Records are kept in this Mac account's Application Support folder, never inside the app.
RESOURCES="$(cd "$(dirname "$0")/../Resources" && pwd)"
PYTHON="$RESOURCES/python/bin/python3"
# -I: ignore any Python settings on this Mac; only what is inside the app is used.
if [ -t 1 ] || [ -n "$DASHBOARD_PLUS_NO_ALERT" ]; then
  exec "$PYTHON" -I -m dashboard "$@"
fi
OUTPUT="$(mktemp "${TMPDIR:-/tmp}/dashboard-plus.XXXXXX")" || OUTPUT=/dev/null
"$PYTHON" -I -u -m dashboard "$@" >"$OUTPUT" 2>&1 &  # -u: messages reach the file at once
PID=$!
TRIES=0
CODE=0
# Wait up to 20 seconds. "Dashboard Plus is running" means it started and opened the browser page;
# it keeps running after this script ends. Still starting at 20 seconds, with nothing wrong, is left be.
while [ "$TRIES" -lt 40 ] && kill -0 "$PID" 2>/dev/null; do
  grep -q "Dashboard Plus is running" "$OUTPUT" 2>/dev/null && break
  sleep 0.5
  TRIES=$((TRIES + 1))
done
if ! kill -0 "$PID" 2>/dev/null; then
  wait "$PID"
  CODE=$?
fi
if [ "$CODE" -ne 0 ]; then
  MESSAGE="$(tail -n 6 "$OUTPUT" 2>/dev/null)"
  /usr/bin/osascript -e 'on run argv' \\
    -e 'display alert "Dashboard Plus could not start" message (item 1 of argv)' \\
    -e 'end run' "$MESSAGE" >/dev/null 2>&1
fi
[ "$OUTPUT" = /dev/null ] || rm -f "$OUTPUT"
exit "$CODE"
"""

PTH_LINES = [
    "# Dashboard Plus: our code and pinned libraries, inside this app. Nothing outside the app is used.",
    "../../../../lib",
    "../../../../src",
]

README_TXT = """Dashboard Plus for Mac (preview)
================================

Look after what your household has.

This is an early test build. It is NOT signed or notarised by Apple yet, so
macOS will warn you the first time. Only use it if you are helping to test.

To install:  drag "Dashboard Plus.app" into your Applications folder.
To start:    double-click Dashboard Plus. Your browser opens the dashboard.
To stop:     click "Save and exit" on the page.
To get the page back: open Dashboard Plus again.

The first time, macOS says it "could not verify" Dashboard Plus. Click Done
(not Move to Bin). Then open System Settings, Privacy & Security, scroll down
and click "Open Anyway" next to Dashboard Plus, and confirm. You only do this
once. Do not change any other security setting.

Your records are kept in your own Mac account, in
Library/Application Support/Dashboard Plus (in your home folder), not inside
the app. Replacing or deleting the app does not touch them. Nothing is sent
anywhere; the program only listens on this Mac.
"""


def load_config(path: Path = ROOT / "tools" / "macos.toml") -> dict:
    """Read the pinned Python version and, for each kind of Mac processor, its download and checksum."""
    with open(path, "rb") as handle:
        return tomllib.load(handle)["python"]


def host_arch() -> str:
    """This Mac's processor in Apple's words: arm64 (Apple silicon) or x86_64 (Intel)."""
    machine = platform.machine().lower()
    return {"aarch64": "arm64", "amd64": "x86_64"}.get(machine, machine)


def extract_python(archive: Path, resources: Path) -> Path:
    """Unpack python-build-standalone's install_only archive as Resources/python; leave out pip."""
    with tarfile.open(archive) as tar:
        tar.extractall(resources, filter="data")  # refuses anything that would land outside
    python_dir = resources / "python"
    if not (python_dir / "bin" / "python3").exists():
        raise BuildError("The Python download has no python/bin/python3; is it an install_only archive?")
    for site in python_dir.glob("lib/python3.*/site-packages"):
        for item in site.glob("pip*"):  # the app never installs anything, so it does not carry pip
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    for item in (python_dir / "bin").glob("pip*"):
        item.unlink()
    return python_dir


def write_pth(python_dir: Path, major_minor: str) -> Path:
    """Tell the bundled Python where our code and libraries are (paths inside the app only)."""
    site = python_dir / "lib" / f"python{major_minor}" / "site-packages"
    if not site.is_dir():
        raise BuildError(f"The Python download has no lib/python{major_minor}/site-packages folder.")
    pth = site / "dashboard-plus.pth"
    pth.write_text("\n".join(PTH_LINES) + "\n", encoding="utf-8")
    return pth


def install_libraries(lib_dir: Path, lock: Path, python_version: str, arch: str) -> None:
    """Install the pinned Mac libraries for this processor, checking every checksum."""
    major_minor = ".".join(python_version.split(".")[:2])
    tag = "cp" + major_minor.replace(".", "")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--no-compile", "--no-deps",
         "--require-hashes", "--only-binary=:all:", "--platform", f"macosx_{MINIMUM_MACOS.replace('.', '_')}_{arch}",
         "--python-version", major_minor, "--implementation", "cp", "--abi", tag,
         "--target", str(lib_dir), "-r", str(lock)],
        check=True,
    )
    shutil.rmtree(lib_dir / "bin", ignore_errors=True)


def info_plist(version: str) -> dict:
    """What macOS reads to know the app's name, version and main program."""
    return {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": "Dashboard Plus",
        "CFBundleExecutable": "Dashboard Plus",
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "Dashboard Plus",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": MINIMUM_MACOS,
        # No Dock icon or menu: the dashboard is the browser page, and "Save and exit" closes it.
        "LSUIElement": True,
        "NSHumanReadableCopyright": "Copyright (C) 2026 Corey Reid. GNU AGPL v3 or later.",
    }


def make_zip(folder: Path, zip_path: Path) -> None:
    """Zip the folder so it unpacks as one 'Dashboard Plus' folder, keeping the app runnable.

    On a Mac, Apple's own `ditto` makes the zip (the way Finder does). Elsewhere (tests) the zip
    keeps each file's permissions and stores links as links, which Archive Utility understands."""
    if sys.platform == "darwin" and shutil.which("ditto"):
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(folder), str(zip_path)],
                       check=True)
        return
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(folder.rglob("*")):
            arcname = (Path(folder.name) / item.relative_to(folder)).as_posix()
            mode = item.lstat().st_mode
            if item.is_symlink():
                info = zipfile.ZipInfo(arcname)
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, os.readlink(item))
            elif item.is_dir():
                info = zipfile.ZipInfo(arcname + "/")
                info.external_attr = (stat.S_IFDIR | stat.S_IMODE(mode)) << 16 | 0x10
                archive.writestr(info, b"")
            else:
                info = zipfile.ZipInfo.from_file(item, arcname, strict_timestamps=False)
                info.compress_type = zipfile.ZIP_DEFLATED
                if _must_be_runnable(arcname):
                    # Windows disks keep no "runnable" flag, so it is set here for the Mac (decision 0096).
                    info.external_attr = (stat.S_IFREG | 0o755) << 16
                with open(item, "rb") as handle:
                    archive.writestr(info, handle.read())


def _must_be_runnable(arcname: str) -> bool:
    """The app's launcher and the bundled Python's programs must stay runnable after unzipping."""
    return "/Contents/MacOS/" in arcname or "/Contents/Resources/python/bin/" in arcname


def build(out: Path, python_archive: Path | None = None, arch: str | None = None,
          skip_libraries: bool = False, config: dict | None = None) -> Path:
    """Build the folder (app, read-me, licence) and the zip in `out`; return the zip's path.

    `config` replaces tools/macos.toml; tests use it to pin a stand-in download."""
    config = config if config is not None else load_config()
    arch = arch or host_arch()
    if arch not in ARCHES:
        raise BuildError(f"Mac builds are made for arm64 (Apple silicon) or x86_64 (Intel), not {arch!r}.")
    pinned = config.get(arch, {})
    out = Path(out)
    folder = out / FOLDER_NAME
    if folder.exists():
        shutil.rmtree(folder)
    contents = folder / APP_NAME / "Contents"
    resources = contents / "Resources"
    (contents / "MacOS").mkdir(parents=True)
    resources.mkdir()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(python_archive) if python_archive else Path(tmp) / "python.tar.gz"
        if not python_archive:
            download(pinned["url"], source)
        verify(source, pinned.get("sha256", ""), require_pinned=True)
        python_dir = extract_python(source, resources)
    major_minor = ".".join(config["version"].split(".")[:2])
    write_pth(python_dir, major_minor)

    lib_dir = resources / "lib"
    lib_dir.mkdir()
    if not skip_libraries:
        install_libraries(lib_dir, ROOT / "requirements.lock", config["version"], arch)
    copy_program(resources)
    shutil.copy2(ROOT / "LICENSE", resources / "LICENSE.txt")
    with open(contents / "Info.plist", "wb") as handle:
        plistlib.dump(info_plist(program_version()), handle)
    launcher = contents / "MacOS" / "Dashboard Plus"
    launcher.write_text(LAUNCHER, encoding="utf-8")
    launcher.chmod(0o755)
    (folder / "READ ME FIRST.txt").write_text(README_TXT, encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE.txt")

    zip_path = out / f"Dashboard-Plus-{program_version()}-macos-{arch}-unsigned.zip"
    if zip_path.exists():
        zip_path.unlink()
    make_zip(folder, zip_path)
    print(f"Built {folder / APP_NAME} ({ARCHES[arch]}, not signed) and {zip_path.name}")
    return zip_path


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "dist"))
    parser.add_argument("--arch", choices=sorted(ARCHES), help="default: this computer's processor")
    parser.add_argument("--python-archive", help="use this python-build-standalone archive instead of downloading")
    parser.add_argument("--skip-libraries", action="store_true", help="for tests: do not install libraries")
    args = parser.parse_args(argv)
    try:
        build(Path(args.out), Path(args.python_archive) if args.python_archive else None,
              args.arch, args.skip_libraries)
    except (BuildError, subprocess.CalledProcessError, OSError, tarfile.TarError) as error:
        print(f"Build failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
