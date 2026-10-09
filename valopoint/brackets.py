"""Source-independent bracket helpers.

A bracket is {"id", "event_id", "name", "region", "teams", "matches", "results", ...}
where each match is {"id", "a", "b", "best_of", "round", "time", "match_id"} and
"a"/"b" are team names or references "W:<match id>" / "L:<match id>".
"""
from __future__ import annotations

import re

PRIORITY = {"INTL": 0, "PAC": 1, "AMER": 2, "EMEA": 3, "CN": 4}


def pick_event(events: list[dict]) -> dict | None:
    """Most relevant event: ongoing/upcoming first, then region priority
    (international > Pacific > Americas > EMEA > China), newest first."""
    if not events:
        return None

    def key(e):
        return (bool(e.get("complete")), PRIORITY.get(e.get("region"), 9), _neg(e.get("start") or ""))
    return sorted(events, key=key)[0]


def _neg(s: str) -> str:
    """Sort key that orders ISO dates newest first."""
    return "".join(chr(255 - ord(c)) for c in s)


def resolve_teams(br: dict) -> dict[str, tuple]:
    """match id -> (team a, team b), W:/L: refs resolved from played results (None if unknown)."""
    res, out = {}, {}

    def known(ref):
        mm = re.match(r"^([WL]):(.+)$", ref or "")
        if mm:
            r = res.get(mm.group(2))
            return None if r is None else r[0 if mm.group(1) == "W" else 1]
        return ref

    for m in br["matches"]:
        a, b = known(m["a"]), known(m["b"])
        out[m["id"]] = (a, b)
        w = br.get("results", {}).get(m["id"])
        if a and b and w in (a, b):
            res[m["id"]] = (w, b if w == a else a)
    return out


def results_due(br: dict, now, after_min: float = 75, max_age_h: float = 48) -> list[str]:
    """Matches that started at least `after_min` minutes ago (a Bo3 ending 2:0 takes about that long),
    within the last `max_age_h` hours, and still have no result: time to ask for results."""
    from datetime import datetime, timedelta
    out = []
    for m in br.get("matches", []):
        if not m.get("time") or m["id"] in (br.get("results") or {}):
            continue
        t = datetime.fromisoformat(m["time"])
        if now - timedelta(hours=max_age_h) <= t <= now - timedelta(minutes=after_min):
            out.append(m["id"])
    return out
