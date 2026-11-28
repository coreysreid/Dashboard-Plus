"""Shared helpers for tests: temporary folders and made-up (synthetic) modules."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT / "src", ROOT / "tools"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

DEMO_MODULE = '''name = "demo"
title = "Demo"
version = "1.0.0"
description = "A made-up module for tests."
core_api = "1"
kind = "declarative"
requires = []
outbound_hosts = []
'''

DEMO_TABLES = '''[tables.owners]
title = "Owners"
columns.name = { type = "text", required = true }

[tables.things]
title = "Things"
columns.name = { type = "text", required = true }
columns.kind = { type = "choice", choices = ["tool", "food", { key = "first_aid", label = "First aid" }] }
columns.owner = { type = "link", to = "owners", on_delete = "restrict" }
columns.quantity = { type = "measure", unit = "kg", min = 0 }
columns.bought = { type = "date" }
columns.helpers = { type = "links", to = "owners" }
'''

DEMO_LABELS = '''[tables.things]
title = "Things we keep"
form = ["name", "kind", "quantity"]
columns.quantity = { label = "How much", help = "In kilograms" }
'''


def freeze_today(test: unittest.TestCase, day: date | None = None) -> date:
    """Fix "today" for one test, so the app and the test cannot disagree if midnight passes mid-run.

    The day is `day`, else the real date, read once (a test file whose `TODAY` was read when it loaded passes
    that, so the whole file shares one day). Every `date` name in the dashboard modules and in the test file then answers `date.today()`
    with that one day; everything else about `date` is unchanged. Calling it again in the same test fixes another day. Undone when the test ends."""
    module = sys.modules[type(test).__module__]
    if day is None:
        day = date.today()

    class Real(type(date)):  # a plain date still counts as a date in isinstance checks
        def __instancecheck__(cls, obj):
            return isinstance(obj, date)

    class FrozenDate(date, metaclass=Real):
        frozen = True

        @classmethod
        def today(cls):
            return day

    for owner in [module] + [m for name, m in list(sys.modules.items()) if name.startswith("dashboard") or name == "load_example"]:
        now = getattr(owner, "date", None)
        if now is date or getattr(now, "frozen", False):  # a day fixed earlier in setUp is replaced
            patcher = mock.patch.object(owner, "date", FrozenDate)
            patcher.start()
            test.addCleanup(patcher.stop)
    return day


class TempDirTestCase(unittest.TestCase):
    """A test with its own temporary folder, removed afterwards, and a fixed "today" (see freeze_today)."""

    def setUp(self):
        freeze_today(self)
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        # Clean-ups run last-registered-first, so anything a test opens later
        # (database connections) is closed before the folder is removed.
        # Windows cannot delete a file that is still open.
        self.addCleanup(self._tmp.cleanup)

    def write(self, relative: str, text: str) -> Path:
        path = self.tmp / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def make_module(self, name="demo", module=DEMO_MODULE, tables=DEMO_TABLES, labels=DEMO_LABELS,
                    root="modules") -> Path:
        folder = self.tmp / root / name
        self.write(f"{root}/{name}/module.toml", module.replace('name = "demo"', f'name = "{name}"'))
        self.write(f"{root}/{name}/tables.toml", tables)
        if labels is not None:
            self.write(f"{root}/{name}/labels.toml", labels)
        return folder
