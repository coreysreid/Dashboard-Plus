"""Check every draft module in workbench/drafts: it loads, its migrations match, and it starts cleanly."""
import shutil
import unittest

from support import ROOT, TempDirTestCase
from dashboard.core import modules, startup
from dashboard.core.schema import next_migration_sql

DRAFTS = ROOT / "workbench" / "drafts"


def draft_folders():
    if not DRAFTS.is_dir():
        return []
    return sorted(p for p in DRAFTS.iterdir() if p.is_dir() and (p / "module.toml").exists())


class WorkbenchDraftTests(TempDirTestCase):
    def test_every_draft_loads_and_its_migrations_match(self):
        folders = draft_folders()
        if not folders:
            raise unittest.SkipTest("no draft modules yet")
        for folder in folders:
            with self.subTest(draft=folder.name):
                module = modules.load_module(folder)
                self.assertTrue(module.migrations, "generate migrations with tools/make_migration.py")
                self.assertIsNone(next_migration_sql(module),
                                  "tables.toml has changed since the last migration was generated")

    def test_every_draft_starts_beside_the_shipped_modules(self):
        folders = draft_folders()
        if not folders:
            raise unittest.SkipTest("no draft modules yet")
        for folder in folders:
            with self.subTest(draft=folder.name):
                target = self.tmp / folder.name
                for shipped in (ROOT / "modules").iterdir():
                    if shipped.is_dir():
                        shutil.copytree(shipped, target / "modules" / shipped.name)
                shutil.copytree(folder, target / "modules" / folder.name)
                report = startup.prepare(target / "data", target / "modules")
                self.assertEqual(report.module_problems, {})
                self.assertIn(folder.name, report.modules)
