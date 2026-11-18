"""Say an amount of 1 with its unit in the singular: "1 tube", not "1 tubes"."""
from __future__ import annotations

# Plural household units and their singular. Anything else is left exactly as the household typed it.
_SINGULAR = {
    "tubes": "tube", "bottles": "bottle", "tins": "tin", "packs": "pack", "boxes": "box",
    "cans": "can", "jars": "jar", "bags": "bag", "packets": "packet", "litres": "litre",
    "liters": "liter", "rolls": "roll", "sachets": "sachet", "cartons": "carton", "pairs": "pair",
}


def unit_for(amount, unit: str) -> str:
    """The unit as it reads next to this amount: singular only when the amount is exactly 1."""
    try:
        exactly_one = float(amount) == 1
    except (TypeError, ValueError):
        return unit
    if not exactly_one or not unit:
        return unit
    word = unit.strip()
    singular = _SINGULAR.get(word.lower())
    if singular is None:
        return unit
    return singular.capitalize() if word[:1].isupper() else singular
