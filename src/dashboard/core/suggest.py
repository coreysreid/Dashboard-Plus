"""Suggestions while typing: a household's own records first, then a module's list of common things."""
from __future__ import annotations

import re
import unicodedata

LIMIT = 8


def normalise(text: str) -> str:
    """Lower case, no accents or punctuation, single spaces: "Crème-fraîche " -> "creme fraiche"."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _score(query: str, name: str, also: list[str]) -> int | None:
    """0: the name starts with what was typed; 1: a word in the name does; 2: another name for it does."""
    singular = query[:-1] if len(query) > 3 and query.endswith("s") else query
    words = normalise(name)
    for q in (query, singular):
        if words.startswith(q):
            return 0
    for q in (query, singular):
        if any(word.startswith(q) for word in words.split()):
            return 1
    for alias in also:
        alias = normalise(alias)
        if any(alias.startswith(q) or any(w.startswith(q) for w in alias.split()) for q in (query, singular)):
            return 2
    return None


def suggestions(typed: str, own: list[dict], catalogue: list[dict], limit: int = LIMIT) -> list[dict]:
    """Best matches for what was typed.

    `own` holds the household's existing records ({"id", "name"}); they come first so the same thing is
    not added twice. `catalogue` holds a module's common things ({"name", "also", "fills"})."""
    query = normalise(typed)
    if not query:
        return []
    found, seen = [], set()
    for record in own:
        score = _score(query, record["name"], [])
        if score is not None:
            found.append((score - 3, record["name"], {"name": record["name"], "existing_id": record["id"]}))
            seen.add(normalise(record["name"]))
    for entry in catalogue:
        if normalise(entry["name"]) in seen:
            continue
        score = _score(query, entry["name"], entry.get("also", []))
        if score is not None:
            found.append((score, entry["name"], {"name": entry["name"], "fills": entry.get("fills", {})}))
    found.sort(key=lambda item: (item[0], len(item[1]), item[1].lower()))
    return [item[2] for item in found[:limit]]
