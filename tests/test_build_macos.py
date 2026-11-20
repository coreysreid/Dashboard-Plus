"""Tests for the unsigned Mac app build, using a stand-in for the Python download (runs on any system)."""
import io
import os
import plistlib
import stat
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_macos  # noqa: E402
import build_portable  # noqa: E402
import smoke_test_portable  # noqa: E402


def add(tar: tarfile.TarFile, name: str, data: bytes = b"stand-in", mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name)
    info.size, info.mode = len(data), mode
    tar.addfile(info, io.BytesIO(data))


def fake_python_archive(folder: Path, extra: str | None = None) -> Path:
    path = folder / "python.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        add(tar, "python/bin/python3", mode=0o755)
        add(tar, "python/bin/pip3", mode=0o755)
        add(tar, "python/lib/python3.12/os.py")
        add(tar, "python/lib/python3.12/site-packages/README.txt")
        add(tar, "python/lib/python3.12/site-packages/pip/__init__.py")
        if extra:
            add(tar, extra)
    return path


def pinned(path: Path) -> dict:
    config = build_macos.load_config()
    return dict(config, arm64=dict(config["arm64"], sha256=build_portable.sha256_of(path)))


class BuildMacTests(unittest.TestCase):
    def test_app_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake = fake_python_archive(tmp)
            zip_path = build_macos.build(tmp / "out", fake, "arm64", skip_libraries=True, config=pinned(fake))
            self.assertTrue(zip_path.name.endswith("-macos-arm64-unsigned.zip"), zip_path.name)
            folder = tmp / "out" / build_macos.FOLDER_NAME
            contents = folder / build_macos.APP_NAME / "Contents"
            for path in (folder / "READ ME FIRST.txt", folder / "LICENSE.txt",
                         contents / "Resources" / "src" / "dashboard" / "data_location.py",
                         contents / "Resources" / "modules" / "people" / "module.toml"):
                self.assertTrue(path.exists(), path)
            self.assertFalse(list((contents / "Resources" / "src").rglob("__pycache__")))
            # pip is left out: the app never installs anything.
            self.assertFalse((contents / "Resources" / "python" / "bin" / "pip3").exists())
            site = contents / "Resources" / "python" / "lib" / "python3.12" / "site-packages"
            self.assertFalse((site / "pip").exists())
            self.assertEqual((site / "dashboard-plus.pth").read_text(encoding="utf-8").splitlines()[1:],
                             ["../../../../lib", "../../../../src"])

            with open(contents / "Info.plist", "rb") as handle:
                plist = plistlib.load(handle)
            self.assertEqual(plist["CFBundleExecutable"], "Dashboard Plus")
            self.assertEqual(plist["CFBundlePackageType"], "APPL")
            self.assertEqual(plist["CFBundleShortVersionString"], build_portable.program_version())
            launcher = contents / "MacOS" / plist["CFBundleExecutable"]
            if os.name == "posix":  # Windows disks have no "runnable" flag; the zip below carries it everywhere
                self.assertTrue(launcher.stat().st_mode & stat.S_IXUSR)
            text = launcher.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#!/bin/sh\n"))
            self.assertIn('"$PYTHON" -I', text)  # nothing from outside the app is used
            self.assertNotIn("--data", text)  # the program chooses Application Support itself

            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                mode = archive.getinfo("Dashboard Plus/Dashboard Plus.app/Contents/MacOS/Dashboard Plus").external_attr >> 16
            self.assertTrue(mode & stat.S_IXUSR, "the launcher must stay runnable after unzipping")
            self.assertIn("Dashboard Plus/READ ME FIRST.txt", names)
            self.assertFalse(any("/data/" in n for n in names), "no data folder may be shipped")

    def test_checksum_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with self.assertRaises(build_portable.BuildError):
                build_macos.build(tmp / "out", fake_python_archive(tmp), "arm64", skip_libraries=True)

    def test_archive_reaching_outside_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fake = fake_python_archive(tmp, extra="../outside.txt")
            with self.assertRaises(tarfile.TarError):
                build_macos.build(tmp / "out", fake, "arm64", skip_libraries=True, config=pinned(fake))
            self.assertFalse((tmp / "out" / "outside.txt").exists())

    def test_unknown_processor_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(build_portable.BuildError):
                build_macos.build(Path(tmp), arch="sparc", skip_libraries=True)

    def test_config_pins_python_for_both_kinds_of_mac(self):
        config = build_macos.load_config()
        self.assertEqual(config["version"], build_portable.load_config()["version"])  # same Python as Windows
        for arch in ("arm64", "x86_64"):
            self.assertIn(config["version"], config[arch]["url"])
            self.assertIn("apple-darwin-install_only", config[arch]["url"])
            self.assertRegex(config[arch]["sha256"], r"^[0-9a-f]{64}$")

    def test_smoke_test_starts_the_app_through_its_launcher(self):
        app = Path("dist") / "Dashboard Plus" / "Dashboard Plus.app"
        start, python = smoke_test_portable.commands(app)
        self.assertEqual(start, [str(app / "Contents" / "MacOS" / "Dashboard Plus")])
        self.assertEqual(python[1:], ["-I"])


if __name__ == "__main__":
    unittest.main()
