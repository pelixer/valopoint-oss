"""Map-level player dataset: one row per (game, player).

Source-independent files (schema: docs/data-schema.md):
  <data>/events.json          [{event_id, name, region, tier, year, start, complete, source, page}]
  <data>/rows/<event_id>.csv  one row per (map, player): ids, teams, round score, agent and stats
  <data>/veto/<event_id>.json map vetoes per match

IDs (event_id, match_id, game_id, player_id) are strings. The stats FK, FD, ADR and
KAST may be missing for some rows (Liquipedia has only K/D/A/ACS for the China league).
`partial` decides what happens to such rows:
  "regress" (default) fill them from K/D/A/ACS per role (R^2 on held-out rows: ADR 0.94,
            KAST 0.56, FK 0.42, FD 0.31) and flag them in `imputed`. LPDB has only K/D/A/ACS
            before mid-2024 and for the China league; filling keeps those maps. Walk-forward on
            the 7 international events since Champions 2024 (450 maps, 178 series), with the
            current Params: series log loss 0.628, vs 0.648 for "drop" with the earlier
            2-year window (docs/model-research-2026-10.md).
  "drop"    leave them out.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .agents import role_of

# per-round outcome features used for the power point (Rating/ACS are excluded:
# they are fixed composites of the same inputs and would double count)
FEATURES = ["kpr", "dpr", "apr", "fkpr", "fdpr", "adr", "kast"]
REQUIRED = ["kpr", "dpr", "apr"]                 # rows without these are always dropped
OPTIONAL = ["fkpr", "fdpr", "adr", "kast"]       # missing: dropped or regression-filled (`partial`)
ID_COLS = ["event_id", "match_id", "game_id", "player_id"]


def load(data_dir: str | Path = "data", partial: str = "regress") -> pd.DataFrame:
    d = Path(data_dir)
    events = {str(e["event_id"]): e for e in json.loads((d / "events.json").read_text(encoding="utf-8"))}
    frames = [pd.read_csv(p, dtype={c: str for c in ID_COLS}) for p in sorted((d / "rows").glob("*.csv"))]
    if not frames:
        raise FileNotFoundError(f"no row files in {d/'rows'}")
    df = pd.concat(frames, ignore_index=True)
    df["region_ev"] = df["event_id"].map(lambda e: events.get(e, {}).get("region", ""))
    df["tier"] = df["event_id"].map(lambda e: events.get(e, {}).get("tier", "league"))
    return prepare(df, partial)


def prepare(df: pd.DataFrame, partial: str = "regress") -> pd.DataFrame:
    df = df.copy()
    df = df[df["team_rounds"].notna() & df["opp_rounds"].notna()]
    df["R"] = df["team_rounds"] + df["opp_rounds"]
    df = df[df["R"] > 0]
    df["date"] = pd.to_datetime(df["date"])
    for s, c in [("kpr", "k"), ("dpr", "d"), ("apr", "a"), ("fkpr", "fk"), ("fdpr", "fd")]:
        df[s] = df[c] / df["R"]
    df["kast"] = df["kast"] / 100.0
    df["agent"] = df["agent"].fillna("").str.lower()
    df["role"] = df["agent"].map(role_of)
    for c in ID_COLS:
        if c in df:
            df[c] = df[c].astype("string").str.replace(r"\.0$", "", regex=True)
    df["pkey"] = df["player_id"].fillna(df["player"]).astype(str)
    df["intl"] = df["tier"].isin(["masters", "champions"])
    df["team_region"] = team_regions(df)
    df = df.dropna(subset=REQUIRED)
    df["imputed"] = df[OPTIONAL].isna().any(axis=1)
    if partial == "drop":
        df = df[~df["imputed"]]
    else:
        df = _regress_fill(df)
    # a map must have exactly 5 players per side to be usable
    n = df.groupby(["game_id", "team"])["pkey"].transform("size")
    return df[n == 5].reset_index(drop=True)


def _regress_fill(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing optional stats from K/D/A/ACS with a per-role least-squares fit."""
    df = df.copy()
    acs = df["acs"] if "acs" in df else pd.Series(np.nan, index=df.index)
    acs = acs.fillna(acs.mean() if acs.notna().any() else 0.0) / 100.0
    X = np.column_stack([np.ones(len(df)), df["kpr"], df["dpr"], df["apr"], acs])
    full = df[OPTIONAL].notna().all(axis=1).to_numpy()
    for role in df["role"].unique():
        r = (df["role"] == role).to_numpy()
        if (r & full).sum() < 50:
            continue
        for c in OPTIONAL:
            beta, *_ = np.linalg.lstsq(X[r & full], df[c].to_numpy()[r & full], rcond=None)
            miss = r & df[c].isna().to_numpy()
            df.loc[miss, c] = X[miss] @ beta
    for c in OPTIONAL:
        df[c] = df[c].fillna(df.groupby("role")[c].transform("mean")).fillna(df[c].mean())
    return df


def team_regions(df: pd.DataFrame) -> pd.Series:
    """Home region of each team = most frequent region among its domestic events."""
    dom = df[~df["tier"].isin(["masters", "champions"]) & (df["region_ev"] != "")]
    home = dom.groupby("team")["region_ev"].agg(lambda s: s.mode().iat[0]).to_dict()
    return df["team"].map(home).fillna("UNK")


def games(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (game, team) side with outcome."""
    g = df.groupby(["game_id", "team"], as_index=False).agg(
        opp=("opp", "first"), date=("date", "first"), map=("map", "first"),
        event_id=("event_id", "first"), match_id=("match_id", "first"),
        map_order=("map_order", "first"), best_of=("best_of", "first"),
        team_rounds=("team_rounds", "first"), opp_rounds=("opp_rounds", "first"),
        team_region=("team_region", "first"), intl=("intl", "first"),
    )
    g["win"] = (g["team_rounds"] > g["opp_rounds"]).astype(float)
    return g
