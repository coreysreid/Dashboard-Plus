"""Tests that this repository passes its own checks."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_indexes  # noqa: E402
import check_privacy  # noqa: E402
import make_project_map  # noqa: E402


class RepositoryTests(unittest.TestCase):
    def test_nothing_private_is_committed(self):
        self.assertEqual([str(f) for f in check_privacy.scan(ROOT)], [])

    def test_every_folder_has_a_current_index(self):
        self.assertEqual(check_indexes.check(ROOT), [])

    def test_project_map_is_up_to_date(self):
        self.assertEqual(make_project_map.main(["--root", str(ROOT), "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
