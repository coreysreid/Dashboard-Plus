"""Tests for the portable Windows build, using a stand-in for the Python download."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_portable  # noqa: E402


def fake_embeddable_zip(folder: Path) -> Path:
    path = folder / "embed.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("python312._pth", "python312.zip\n.\n#import site\n")
        archive.writestr("python.exe", "stand-in")
        archive.writestr("python312.zip", "")
    return path


class BuildPortableTests(unittest.TestCase):
    def test_build_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            zip_path = build_portable.build(tmp / "out", fake_embeddable_zip(tmp), skip_libraries=True)
            folder = tmp / "out" / build_portable.FOLDER_NAME
            for name in ("Open Dashboard.bat", "Close Dashboard safely.bat", "READ ME FIRST.txt", "LICENSE.txt"):
                self.assertTrue((folder / name).exists(), name)
            self.assertTrue((folder / "app" / "src" / "dashboard" / "__main__.py").exists())
            self.assertFalse(list((folder / "app" / "src").rglob("__pycache__")))
            pth = (folder / "app" / "python" / "python312._pth").read_text(encoding="utf-8").splitlines()
            self.assertEqual(pth[:4], ["python312.zip", ".", r"..\lib", r"..\src"])
            self.assertNotIn("import site", [line.strip() for line in pth])
            bat = (folder / "Open Dashboard.bat").read_bytes()
            self.assertIn(b"\r\n", bat)
            self.assertNotIn(b"\r\r", bat)
            self.assertIn(b'--data "%~dp0data"', bat)
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
            self.assertIn(f"{build_portable.FOLDER_NAME}/Open Dashboard.bat", names)
            self.assertFalse(any("/data/" in n for n in names), "the data folder must not be shipped")

    def test_checksum_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fake_embeddable_zip(Path(tmp))
            with self.assertRaises(build_portable.BuildError):
                build_portable.verify(path, "0" * 64, require_pinned=False)

    def test_release_requires_a_pinned_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fake_embeddable_zip(Path(tmp))
            with self.assertRaises(build_portable.BuildError):
                build_portable.verify(path, "", require_pinned=True)
            actual = build_portable.verify(path, "", require_pinned=False)
            self.assertEqual(build_portable.verify(path, actual, require_pinned=True), actual)

    def test_config_pins_an_exact_python_version(self):
        config = build_portable.load_config()
        self.assertRegex(config["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn(config["version"], config["url"])


if __name__ == "__main__":
    unittest.main()
