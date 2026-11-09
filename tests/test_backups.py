"""Tests for automatic backups: daily, on close, in two places, and keeping only recent ones."""
import sqlite3
from datetime import date

from support import TempDirTestCase
from dashboard.core import backups, startup


class BackupTests(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.data = self.tmp / "data"
        startup.prepare(self.data, self.tmp / "modules")
        self.extra = self.tmp / "computer-copy"

    def test_daily_backup_once_a_day_in_both_places(self):
        made = backups.daily(self.data, self.extra, today=date(2026, 6, 1))
        self.assertEqual([p.name for p in made], ["daily-2026-06-01.db"] * 2)
        self.assertEqual(backups.daily(self.data, self.extra, today=date(2026, 6, 1)), [])
        copy = sqlite3.connect(self.extra / "daily-2026-06-01.db")
        try:
            self.assertEqual(copy.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            copy.close()

    def test_close_backup_and_latest(self):
        backups.on_close(self.data)
        name, _ = backups.latest(self.data)
        self.assertTrue(name.startswith("close-"))

    def test_second_copy_failing_does_not_stop_the_main_backup(self):
        blocker = self.tmp / "not-a-folder"
        blocker.write_text("x", encoding="utf-8")
        made = backups.daily(self.data, blocker, today=date(2026, 6, 2))
        self.assertEqual(len(made), 1)
        self.assertTrue((self.data / "backups" / "daily-2026-06-02.db").exists())

    def test_old_backups_are_pruned_but_recent_ones_kept(self):
        for day in range(1, 21):
            backups.daily(self.data, today=date(2026, 6, day))
        kept = sorted(p.name for p in (self.data / "backups").glob("daily-*.db"))
        self.assertEqual(len(kept), backups.KEEP["daily"])
        self.assertEqual(kept[-1], "daily-2026-06-20.db")
        self.assertEqual(kept[0], "daily-2026-06-07.db")
