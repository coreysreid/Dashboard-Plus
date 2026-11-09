"""Tests for the requirements lock generator."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lock_requirements  # noqa: E402


class LockTests(unittest.TestCase):
    def test_unpinned_library_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "req.txt"
            path.write_text("flask>=3\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                lock_requirements.read_pins(path)

    def test_lock_lists_every_hash(self):
        text = lock_requirements.build_lock([("demo", "1.0")], fetch=lambda n, v: ["a" * 64, "b" * 64])
        self.assertIn("demo==1.0 \\", text)
        self.assertEqual(text.count("--hash=sha256:"), 2)

    def test_committed_lock_matches_requirements(self):
        pins = lock_requirements.read_pins(ROOT / "requirements.txt")
        lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
        for name, version in pins:
            self.assertIn(f"{name}=={version} \\", lock)
            self.assertIn("--hash=sha256:", lock)


if __name__ == "__main__":
    unittest.main()
