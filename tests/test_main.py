"""Tests for the command-line entry point and its plain-language messages."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dashboard import __main__ as cli  # noqa: E402


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(list(args))
    return code, out.getvalue()


class MainTests(unittest.TestCase):
    def test_version(self):
        code, out = run("--version")
        self.assertEqual(code, 0)
        self.assertIn("Dashboard Plus", out)

    def test_close_when_not_running_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run("--data", tmp, "--close")
        self.assertEqual(code, 0)
        self.assertIn("not running", out)

    def test_failure_report_is_written_without_showing_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                raise ValueError("synthetic failure")
            except ValueError as error:
                path = cli.write_report(Path(tmp), error)
            self.assertTrue(path.exists())
            self.assertIn("synthetic failure", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
