"""Run the real-browser check (tools/browser_check.py) when Node, Playwright and Chromium are here; skip otherwise."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import browser_check  # noqa: E402

# Set DASHBOARD_BROWSER_CHECK=required to fail instead of skipping. (CI runs tools/browser_check.py itself.)
REQUIRED = os.environ.get("DASHBOARD_BROWSER_CHECK") == "required"


class BrowserCheckTests(unittest.TestCase):
    def test_the_dashboard_works_in_a_real_browser(self):
        reason = browser_check.unavailable()
        if reason and not REQUIRED:
            self.skipTest(f"Real-browser check not run: {reason} See docs/decisions/0064-real-browser-check.md.")
        self.assertIsNone(reason, "The real-browser check was required but cannot run here.")
        try:
            done = browser_check.check()
        except browser_check.CheckFailed as failure:
            self.fail(str(failure))
        self.assertTrue(any("save and exit" in line for line in done), done)


if __name__ == "__main__":
    unittest.main()
