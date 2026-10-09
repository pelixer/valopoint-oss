"""How complete is an imported data set, and how well does it agree with a baseline?

`report(lpdb_dir, baseline_dir)`:
  * per event: matches, finished matches, maps, player-map rows, share of rows with
    every model stat (FK, FD, ADR, KAST), vetoes per finished match;
  * against a baseline data set (e.g. the earlier vlr.gg import, kept only until the
    migration is verified): share of baseline maps found, and agreement of K/D/A,
    ADR and KAST on the matched player-maps.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

STATS = ["fk", "fd", "adr", "kast"]


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).casefold())


def _rows(d: Path) -> pd.DataFrame:
    files = sorted((d / "rows").glob("*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(p, dtype={"event_id": str, "match_id": str, "game_id": str, "player_id": str})
                      for p in files], ignore_index=True)


def per_event(d: Path) -> pd.DataFrame:
    rows = _rows(d)
    events = {str(e["event_id"]): e for e in json.loads((d / "events.json").read_text(encoding="utf-8"))}
    out = []
    for eid, e in events.items():
        r = rows[rows["event_id"] == eid] if len(rows) else rows
        sched = json.loads((d / "schedule" / f"{eid}.json").read_text()) if (d / "schedule" / f"{eid}.json").exists() else []
        veto = json.loads((d / "veto" / f"{eid}.json").read_text()) if (d / "veto" / f"{eid}.json").exists() else []
        fin = sum(1 for s in sched if s.get("finished"))
        out.append({"event": e.get("name", eid), "region": e.get("region"), "matches": len(sched), "finished": fin,
                    "maps": r["game_id"].nunique() if len(r) else 0, "rows": len(r),
                    "full_stats": round(float(r[STATS].notna().all(axis=1).mean()), 3) if len(r) else 0.0,
                    "agent": round(float((r["agent"].fillna("") != "").mean()), 3) if len(r) else 0.0,
                    "veto_per_match": round(len(veto) / fin, 2) if fin else 0.0})
    return pd.DataFrame(out).sort_values(["region", "event"]).reset_index(drop=True)


def compare(new: Path, base: Path) -> dict:
    a, b = _rows(new), _rows(base)
    if a.empty or b.empty:
        return {}
    for df in (a, b):
        df["pair"] = [tuple(sorted((_norm(x), _norm(y)))) for x, y in zip(df["team"], df["opp"])]
        df["mapk"] = df["map"].map(_norm)
        df["pk"] = df["player"].map(_norm)
        df["day"] = pd.to_datetime(df["date"]).dt.date
    gk = ["day", "pair", "mapk"]
    bm = b.drop_duplicates(gk)[gk]
    am = a.drop_duplicates(gk)[gk]
    # allow one day of difference (time zones)
    am_shift = pd.concat([am, am.assign(day=am["day"] + pd.Timedelta(days=1)),
                          am.assign(day=am["day"] - pd.Timedelta(days=1))]).drop_duplicates()
    found = bm.merge(am_shift, on=gk, how="left", indicator=True)["_merge"].eq("both").mean()
    m = b.merge(a, on=["pair", "mapk", "pk"], suffixes=("_b", "_a"))
    m = m[(pd.to_datetime(m["date_b"]) - pd.to_datetime(m["date_a"])).abs() <= pd.Timedelta(days=1)]
    agree = {}
    for c, tol in [("k", 0), ("d", 0), ("a", 0), ("adr", 1.0), ("kast", 1.0), ("fk", 0), ("fd", 0)]:
        x = m[[f"{c}_b", f"{c}_a"]].dropna()
        if len(x):
            agree[c] = round(float(((x[f"{c}_b"] - x[f"{c}_a"]).abs() <= tol).mean()), 3)
    return {"baseline_maps": int(len(bm)), "found_share": round(float(found), 3),
            "matched_player_maps": int(len(m)), "agreement": agree}


def report(new: Path, base: Path | None = Path("data")) -> str:
    lines = ["# coverage per event", per_event(new).to_string(index=False)]
    if base is not None and (base / "rows").exists() and Path(base).resolve() != Path(new).resolve():
        lines += ["", "# against baseline " + str(base), json.dumps(compare(new, base), indent=1)]
    return "\n".join(lines)
