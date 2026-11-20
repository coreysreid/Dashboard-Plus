"""Tests for choosing the data folder: Application Support inside a Mac app, never inside the app (decision 0096)."""
import contextlib
import io
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path, PurePath, PurePosixPath
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dashboard import __main__ as cli  # noqa: E402
from dashboard import data_location  # noqa: E402

IN_APP = PurePosixPath("/Applications/Dashboard Plus.app/Contents/Resources/src/dashboard/data_location.py")
FROM_SOURCE = PurePosixPath("/home/someone/projects/dashboard-plus/src/dashboard/data_location.py")
HOME = PurePosixPath("/Users/example")


class DefaultDataFolderTests(unittest.TestCase):
    def test_mac_app_uses_application_support(self):
        self.assertEqual(data_location.default_data_dir("darwin", IN_APP, HOME),
                         PurePosixPath("/Users/example/Library/Application Support/Dashboard Plus"))

    def test_mac_app_folder_is_never_inside_the_app(self):
        chosen = data_location.default_data_dir("darwin", IN_APP, HOME)
        self.assertNotIn(".app", str(chosen))

    def test_running_from_source_on_a_mac_keeps_the_old_default(self):
        self.assertEqual(data_location.default_data_dir("darwin", FROM_SOURCE, HOME), PurePath("data"))

    def test_other_systems_keep_the_old_default(self):
        for platform in ("win32", "linux"):
            with self.subTest(platform=platform):
                self.assertEqual(data_location.default_data_dir(platform, IN_APP, HOME), PurePath("data"))

    def test_finds_the_app_folder(self):
        self.assertEqual(data_location.app_bundle(IN_APP), PurePosixPath("/Applications/Dashboard Plus.app"))
        self.assertIsNone(data_location.app_bundle(FROM_SOURCE))
        # A folder merely called ".app", or an .app with no Contents below it, is not a Mac app.
        self.assertIsNone(data_location.app_bundle(PurePosixPath("/x/.app/Contents/a.py")))
        self.assertIsNone(data_location.app_bundle(PurePosixPath("/x/Notes.app/readme.txt")))


class InsideTheAppTests(unittest.TestCase):
    def test_data_folder_inside_the_app_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "Dashboard Plus.app" / "Contents" / "Resources" / "src" / "dashboard" / "x.py"
            inside = Path(tmp) / "Dashboard Plus.app" / "Contents" / "Resources" / "data"
            with self.assertRaises(data_location.DataFolderError) as caught:
                data_location.check_not_in_bundle(inside, package)
            self.assertIn("inside the app", str(caught.exception))
            data_location.check_not_in_bundle(Path(tmp) / "elsewhere", package)  # outside: allowed

    def test_command_line_refuses_without_writing_inside_the_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "Dashboard Plus.app" / "Contents" / "Resources" / "src" / "dashboard" / "x.py"
            inside = Path(tmp) / "Dashboard Plus.app" / "Contents" / "data"
            out = io.StringIO()
            with mock.patch.object(data_location, "PACKAGE_FILE", package), contextlib.redirect_stdout(out):
                code = cli.main(["--data", str(inside), "--close"])
            self.assertEqual(code, 1)
            self.assertIn("inside the app", out.getvalue())
            self.assertFalse(inside.exists(), "nothing may be written inside the app")


class DefaultIsUsedTests(unittest.TestCase):
    def test_no_data_option_uses_the_chosen_default_and_given_data_still_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            support = Path(tmp) / "Library" / "Application Support" / "Dashboard Plus"
            given = Path(tmp) / "given"
            with mock.patch.object(data_location, "default_data_dir", return_value=support), \
                    mock.patch("dashboard.server.serve") as serve, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["--no-browser", "--no-extra-backup"]), 0)
                self.assertEqual(serve.call_args.args[0], support.resolve())
                self.assertTrue(support.is_dir())
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(support.stat().st_mode), 0o700)
                self.assertEqual(cli.main(["--data", str(given), "--no-browser", "--no-extra-backup"]), 0)
                self.assertEqual(serve.call_args.args[0], given.resolve())


if __name__ == "__main__":
    unittest.main()
