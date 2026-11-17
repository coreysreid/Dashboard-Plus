"""Check every Stock place and Medical kit against the Home layout promotion map."""
from __future__ import annotations

import csv
import hashlib
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE_SHA256 = {
    "smith": "08181bfa3492364dd4d927d7536550b648221e16decf5bf3a6b01cff941827af",
    "garcia": "0670f1030fd0e3893f88fa380b62b513ce560a444218580c420b391477cf3ab0",
    "taylor": "9c4ca42a9b1a059f8b878456d971b917eeaf71eb9ee70af01716a36e87e8c757",
}


def rows(name):
    with (HERE / name).open(newline="") as file:
        return list(csv.DictReader(file))


def check() -> None:
    target = tomllib.loads((HERE / "example.toml").read_text())
    places_map, kits_map = rows("STOCK_PLACE_MAP.csv"), rows("MEDICAL_KIT_MAP.csv")
    assert len(places_map) == 31 and len(kits_map) == 3
    tables = tomllib.loads((HERE / "tables.toml").read_text())
    assert tables["tables"]["places"]["parent"] == "parent", "Full-path display needs the parent declaration"
    for household, digest in SOURCE_SHA256.items():
        source_path = ROOT / "examples" / "households" / f"{household}.toml"
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == digest, f"{household}: source changed; review mapping"
        source = tomllib.loads(source_path.read_text())
        old = source["stock"]["places"]
        new = target[household]["home_layout"]["places"]
        matching = [r for r in places_map if r["household"] == household]
        assert len(matching) == len(old)
        assert len({r["new_home_place_id"] for r in matching}) == len(old)
        old_ids = {p["name"]: i for i, p in enumerate(old, 1)}
        new_ids = {p["name"]: i for i, p in enumerate(new, 1)}
        assert len(new_ids) == len(new), "Target place names must be unique within each example"
        def path(place, parent_field, by_name):
            parts = [place]
            while by_name[place].get(parent_field):
                place = by_name[place][parent_field]
                parts.append(place)
            return " › ".join(reversed(parts))
        old_by_name = {p["name"]: p for p in old}
        new_by_name = {p["name"]: p for p in new}
        for i, (before, after, row) in enumerate(zip(old, new, matching), 1):
            assert row["old_stock_place_id"] == row["new_home_place_id"] == str(i)
            assert after["name"] == before["name"] == row["old_name"]
            assert after.get("parent") == before.get("inside")
            assert after.get("notes") == before.get("notes")
            assert row["old_parent_id"] == row["new_parent_id"] == str(old_ids.get(before.get("inside"), ""))
            assert row["old_full_path"] == path(before["name"], "inside", old_by_name)
            assert row["new_full_path"] == path(after["name"], "parent", new_by_name)
            assert row["old_full_path"] == row["new_full_path"]
            assert row["new_kind"] == after["kind"]
            stock_items = [item["name"] for item in source["stock"]["items"] if item.get("place") == before["name"]]
            kits = [kit["name"] for kit in source["medical"]["kits"] if kit.get("place") == before["name"]]
            assert int(row["direct_stock_item_count"]) == len(stock_items)
            assert row["direct_stock_items"] == "|".join(stock_items)
            assert int(row["direct_medical_kit_count"]) == len(kits)
            assert row["direct_medical_kits"] == "|".join(kits)
        for row in [r for r in kits_map if r["household"] == household]:
            kit = source["medical"]["kits"][int(row["medical_kit_id"]) - 1]
            place = kit["place"]
            assert row["kit_name"] == kit["name"] and row["kept"] == kit["kept"]
            assert row["old_stock_place_id"] == str(old_ids[place])
            assert row["new_home_place_id"] == str(new_ids[place])
            assert row["old_full_path"] == row["new_full_path"] == path(place, "parent", new_by_name)
        for table in ("exits", "shutoffs", "equipment", "meters"):
            for record in target[household]["home_layout"].get(table, []):
                assert record.get("place") in new_ids, f"{household}: {table} has an unknown place"
    print("PASS: 31 old-to-new places, 63 Stock links, three Medical kit links and all Home layout references")


if __name__ == "__main__":
    check()
