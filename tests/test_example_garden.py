"""Exercise the garden example with a temporary database and synthetic harvest."""
import shutil

from support import ROOT, TempDirTestCase
from dashboard.core import db, modules, records, startup
from dashboard.core.schema import next_migration_sql


class GardenExampleTests(TempDirTestCase):
    def test_garden_loads_migrates_and_saves_a_harvest(self):
        garden = modules.load_module(ROOT / "examples" / "garden")
        self.assertEqual(len(garden.tables), 5)
        self.assertEqual(len(garden.migrations), 1)
        self.assertIsNone(next_migration_sql(garden))

        shutil.copytree(ROOT / "examples" / "garden", self.tmp / "modules" / "garden")
        data = self.tmp / "data"
        report = startup.prepare(data, self.tmp / "modules")
        self.assertEqual(report.module_problems, {})
        self.assertEqual([item.name for item in report.loaded], ["garden"])
        conn = db.connect(data / "dashboard.db")
        self.addCleanup(conn.close)
        store = records.Records(conn, records.build_registry(report.loaded))
        bed = store.create("garden__beds", {"name": "North bed"})
        crop = store.create("garden__crops", {"name": "Tomato", "variety": "Cherry"})
        planting = store.create("garden__plantings", {
            "bed": bed, "crop": crop, "planted_on": "2026-09-01", "quantity": 2,
        })
        harvest = store.create("garden__harvests", {
            "planting": planting, "harvested_on": "2026-11-01", "amount": 1.5, "unit": "kg",
        })
        job = store.create("garden__jobs", {"title": "Mulch bed", "bed": bed, "done": False})
        self.assertEqual(store.get("garden__harvests", harvest)["amount"], 1.5)
        self.assertEqual(store.get("garden__jobs", job)["title"], "Mulch bed")
