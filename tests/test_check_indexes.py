"""Tests for the index check."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_indexes  # noqa: E402

GOOD_ROOT = """# ./  (summary: test)
| Entry | What it is | Open it when |
|---|---|---|
| README.md | Intro | reading |
| pkg/ | Package | coding |
"""
GOOD_PKG = """# pkg/  (summary: package)
| Entry | What it is | Open it when |
|---|---|---|
| mod.py | Does one clear thing. | changing it |
"""
GOOD_FILES = {
    "INDEX.md": GOOD_ROOT,
    "README.md": "hello\n",
    "pkg/INDEX.md": GOOD_PKG,
    "pkg/mod.py": '"""Does one clear thing."""\n',
}


def problems_for(files: dict[str, str]) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
        return check_indexes.check(root)


def with_changes(**changes):
    files = dict(GOOD_FILES)
    for key, value in changes.items():
        path = key.replace("__", "/").replace("_md", ".md").replace("_py", ".py")
        if value is None:
            files.pop(path, None)
        else:
            files[path] = value
    return files


class IndexCheckTests(unittest.TestCase):
    def test_good_tree_passes(self):
        self.assertEqual(problems_for(GOOD_FILES), [])

    def test_windows_line_endings_pass(self):
        files = {k: v.replace("\n", "\r\n") for k, v in GOOD_FILES.items()}
        self.assertEqual(problems_for(files), [])

    def test_missing_index(self):
        found = problems_for(with_changes(pkg__INDEX_md=None))
        self.assertTrue(any("no INDEX.md" in p for p in found))

    def test_unlisted_entry(self):
        files = with_changes(pkg__other_py='"""Another thing."""\n')
        self.assertTrue(any("'other.py' is not listed" in p for p in problems_for(files)))

    def test_stale_entry(self):
        files = with_changes(pkg__INDEX_md=GOOD_PKG + "| gone.py | Old | never |\n")
        self.assertTrue(any("stale" in p for p in problems_for(files)))

    def test_too_long(self):
        files = with_changes(INDEX_md=GOOD_ROOT + "\n" * 30)
        self.assertTrue(any("limit" in p for p in problems_for(files)))

    def test_placeholder_rejected(self):
        files = with_changes(INDEX_md=GOOD_ROOT.replace("Intro", check_indexes.PLACEHOLDER))
        self.assertTrue(any("placeholder" in p for p in problems_for(files)))

    def test_python_file_needs_summary(self):
        files = with_changes(pkg__mod_py="x = 1\n")
        self.assertTrue(any("one-line summary" in p for p in problems_for(files)))

    def test_row_must_quote_summary(self):
        files = with_changes(pkg__mod_py='"""A different summary."""\n')
        self.assertTrue(any("must quote" in p for p in problems_for(files)))

    def test_glob_rows_cover_families(self):
        index = GOOD_PKG.replace("| mod.py | Does one clear thing. | changing it |", "| m*.py | Modules | coding |")
        files = dict(GOOD_FILES)
        files["pkg/INDEX.md"] = index
        files["pkg/more.py"] = '"""Second."""\n'
        self.assertEqual(problems_for(files), [])

    def test_glob_that_matches_nothing_is_stale(self):
        index = GOOD_PKG.replace("mod.py |", "zzz*.py |")
        found = problems_for(with_changes(pkg__INDEX_md=index))
        self.assertTrue(any("nothing matches" in p for p in found))

    def test_link_style_first_cell(self):
        index = GOOD_PKG.replace("| mod.py |", "| [mod](mod.py) |")
        self.assertEqual(problems_for(with_changes(pkg__INDEX_md=index)), [])

    def test_hidden_files_need_no_entry(self):
        files = with_changes(**{".github__ci_yml": "x"})
        files[".github/ci.yml"] = "x"
        self.assertEqual(problems_for(files), [])


if __name__ == "__main__":
    unittest.main()
