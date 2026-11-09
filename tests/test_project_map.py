"""Tests for the project map generator."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import make_project_map  # noqa: E402


class ProjectMapTests(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "sub").mkdir()
        (root / "INDEX.md").write_text("# ./  (summary: top)\n| Entry |\n|---|\n| sub/ |\n", encoding="utf-8")
        (root / "sub" / "INDEX.md").write_text("# sub/  (summary: inner)\n| Entry |\n|---|\n| a.txt |\n", encoding="utf-8")
        return root

    def test_map_contains_each_index_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = make_project_map.build(self.make_root(tmp))
        self.assertLess(text.index("## ./"), text.index("## sub/"))
        self.assertIn("| a.txt |", text)

    def test_check_detects_stale_and_fresh_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.assertEqual(make_project_map.main(["--root", str(root), "--check"]), 1)
            self.assertEqual(make_project_map.main(["--root", str(root)]), 0)
            self.assertEqual(make_project_map.main(["--root", str(root), "--check"]), 0)
            (root / "sub" / "INDEX.md").write_text("# sub/  (summary: changed)\n", encoding="utf-8")
            self.assertEqual(make_project_map.main(["--root", str(root), "--check"]), 1)


if __name__ == "__main__":
    unittest.main()
