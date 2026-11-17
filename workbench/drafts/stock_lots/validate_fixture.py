"""Check the three fixed-date lots fixtures against the shipped example Stock rows."""
from __future__ import annotations

import csv
import hashlib
import tomllib
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TODAY = date(2026, 11, 17)
SOURCE_SHA256 = {
    "smith": "08181bfa3492364dd4d927d7536550b648221e16decf5bf3a6b01cff941827af",
    "garcia": "0670f1030fd0e3893f88fa380b62b513ce560a444218580c420b391477cf3ab0",
    "taylor": "9c4ca42a9b1a059f8b878456d971b917eeaf71eb9ee70af01716a36e87e8c757",
}


def fixed(value):
    if isinstance(value, str) and value.startswith("today"):
        return (TODAY + timedelta(days=int(value[5:] or 0))).isoformat()
    return value


def check() -> None:
    target = tomllib.loads((HERE / "example_lots.toml").read_text())
    with (HERE / "ITEM_TO_LOT.csv").open(newline="") as file:
        mapping = list(csv.DictReader(file))
    assert len(mapping) == 63, "Every old item needs a mapping row"
    for household, digest in SOURCE_SHA256.items():
        source_path = ROOT / "examples" / "households" / f"{household}.toml"
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == digest, f"{household}: source changed; review this fixture"
        old = tomllib.loads(source_path.read_text())["stock"]
        new = target[household]["stock"]
        rows = [r for r in mapping if r["household"] == household]
        assert len(rows) == len(old["items"]) == len(new["items"])
        assert old["places"] == new["places"], f"{household}: place rows changed"
        assert len(old["movements"]) == len(new["legacy_movements"])
        for a, b in zip(old["movements"], new["legacy_movements"]):
            assert {k: fixed(v) for k, v in a.items()} == b, f"{household}: item-level history changed"
        lots_by_item: dict[str, list[dict]] = {}
        for lot in new["lots"]:
            lots_by_item.setdefault(lot["item"], []).append(lot)
        assert len(new["lots"]) == len(old["items"]) + (household == "smith")
        for ordinal, (before, after, row) in enumerate(zip(old["items"], new["items"], rows), 1):
            name = before["name"]
            assert row["source_item_ordinal"] == str(ordinal) and row["item_name"] == name
            assert after == {k: v for k, v in before.items() if k not in ("quantity", "place", "expires")}
            lots = lots_by_item[name]
            assert row["migration_amount"] == str(before["quantity"]), f"{household}: migration must preserve the current amount"
            assert len(lots) == len(row["target_lot_refs"].split("|"))
            assert [str(lot["quantity"]) for lot in lots] == row["target_lot_amounts"].split("|")
            assert sum(lot["quantity"] for lot in lots) == float(row["target_total"])
            if household == "smith" and name == "Kidney beans":
                assert [(lot["quantity"], lot["place"], lot["use_by"]) for lot in lots] == [
                    (3, "Shelf 3", "2026-12-20"), (10, "Garage shelves", "2027-05-20")]
                assert before["quantity"] == 5 and row["target_total"] == "13"
            else:
                assert len(lots) == 1
                assert lots[0]["quantity"] == before["quantity"]
                assert lots[0].get("place") == before.get("place")
                assert lots[0].get("use_by") == fixed(before.get("expires"))
    print("PASS: 63 item mappings, 64 target lots, 15 preserved legacy movements, three unchanged place sets")


if __name__ == "__main__":
    check()
