"""LPDB normalisation against records shaped like the VALORANT match2 module output
(Module:MatchGroup/Input/Custom: per-map players with kills, deaths, assists, acs, adr,
kast, hs, agent, firstKills, firstDeaths; map veto in match extradata)."""
import json

import pandas as pd

from valopoint.sources import lpdb
from valopoint.sources.coverage import compare, per_event


def _player(name, k, d, a, adr=None, kast=None, fk=None, fd=None, agent="jett"):
    p = {"player": name, "displayName": name.title(), "agent": agent, "kills": k, "deaths": d, "assists": a, "acs": 200}
    if adr is not None:
        p.update(adr=adr, kast=kast, firstKills=fk, firstDeaths=fd, hs=25)
    return p


def _match(full=True, layout="opponents"):
    stats = dict(adr=150.0, kast=70, fk=2, fd=1) if full else {}
    t1 = [_player(f"a{i}", 15, 12, 4, **stats) for i in range(5)]
    t2 = [_player(f"b{i}", 12, 15, 3, **stats) for i in range(5)]
    g1 = {"match2gameid": 1, "map": "Lotus", "scores": [13, 9], "date": "2026-09-27 09:00:00"}
    if layout == "opponents":
        g1["opponents"] = [{"score": 13, "players": t1}, {"score": 9, "players": t2}]
    else:   # older "participants" layout keyed <opponent>_<player>
        g1["participants"] = {**{f"1_{i + 1}": p for i, p in enumerate(t1)}, **{f"2_{i + 1}": p for i, p in enumerate(t2)}}
    g2 = {"match2gameid": 2, "map": "Haven", "scores": [0, 0]}                 # not played
    return {"match2id": "CHAMP26GrA_0001", "match2bracketid": "CHAMP26GrA", "finished": 1, "bestof": 3,
            "date": "2026-09-27 09:00:00", "section": "Group Stage",
            "match2opponents": [{"name": "100 Thieves", "score": 2, "match2players": [{"name": f"a{i}"} for i in range(5)]},
                                {"name": "T1", "score": 0, "match2players": [{"name": f"b{i}"} for i in range(5)]}],
            "match2games": [g1, g2],
            "extradata": {"mapveto": {"1": {"type": "ban", "team1": "Lotus", "team2": "Split", "vetostart": 2},
                                      "2": {"type": "pick", "team1": "Ascent", "team2": "Summit"},
                                      "3": {"type": "decider", "decider": "Sunset"}}}}


def test_rows_from_opponents_and_participants_layouts():
    for layout in ("opponents", "participants"):
        rows = lpdb.match_rows(_match(layout=layout), "vct-2026-champions", "Valorant Champions 2026")
        df = pd.DataFrame(rows)
        assert len(df) == 10, layout                       # only the played map
        assert set(df["team"]) == {"100 Thieves", "T1"}
        r = df[df["player_id"] == "a0"].iloc[0]
        assert (r["k"], r["d"], r["a"], r["adr"], r["kast"], r["fk"], r["fd"]) == (15, 12, 4, 150, 70, 2, 1)
        assert (r["team_rounds"], r["opp_rounds"], r["map_order"], r["date"]) == (13, 9, 1, "2026-09-27")
        assert r["game_id"] == "CHAMP26GrA_0001_1"


def test_missing_stats_stay_missing_for_imputation():
    df = pd.DataFrame(lpdb.match_rows(_match(full=False), "e", "E"))
    assert df[["k", "d", "a"]].notna().all().all() and df[["adr", "kast", "fk", "fd"]].isna().all().all()


def test_veto_order_follows_first_team():
    v = lpdb.match_veto(_match(), "e")
    assert v["steps"][0] == ["T1", "ban", "Split"] and v["steps"][1] == ["100 Thieves", "ban", "Lotus"]
    assert v["steps"][-1] == [None, "remains", "Sunset"]
    assert v["order"] == ["Summit", "Ascent", "Sunset"]


def test_classify_and_ids():
    assert lpdb.classify("VCT/2026/Pacific League/Stage 2")["region"] == "PAC"
    assert lpdb.classify("VCT/2026/Stage_2/Masters")["tier"] == "masters"
    assert lpdb.classify("VCT/2026/Champions")["tier"] == "champions"
    assert lpdb.classify("VCT/2026/Game Changers/EMEA/Stage 1") is None
    assert lpdb.event_id("VCT/2026/Pacific_League/Stage_2") == "vct-2026-pacific-league-stage-2"
    assert len(lpdb.candidate_pages([2026])) == 15


def test_coverage_and_compare(tmp_path):
    for name, full in (("new", False), ("base", True)):
        d = tmp_path / name
        (d / "rows").mkdir(parents=True)
        (d / "schedule").mkdir()
        (d / "veto").mkdir()
        pd.DataFrame(lpdb.match_rows(_match(full=full), "e1", "E1"), columns=lpdb.ROW_COLS).to_csv(d / "rows" / "e1.csv", index=False)
        (d / "events.json").write_text(json.dumps([{"event_id": "e1", "name": "E1", "region": "INTL"}]))
        (d / "schedule" / "e1.json").write_text(json.dumps([lpdb.match_schedule(_match())]))
        (d / "veto" / "e1.json").write_text(json.dumps([lpdb.match_veto(_match(), "e1")]))
    pe = per_event(tmp_path / "new")
    assert pe.loc[0, "maps"] == 1 and pe.loc[0, "full_stats"] == 0.0 and pe.loc[0, "veto_per_match"] == 1.0
    c = compare(tmp_path / "new", tmp_path / "base")
    assert c["found_share"] == 1.0 and c["agreement"]["k"] == 1.0


def test_compact_drops_round_data_without_touching_the_record():
    m = {"match2id": "X_0001", "match2games": [{
        "map": "Ascent", "extradata": {"rounds": {"1": {"round": 1}, "2": {"round": 2}}},
        "opponents": [{"score": 13, "players": [{"player": "a"}, {"player": "b"}]}],
        "participants": {"1_1": {"player": "a"}, "1_2": {"player": "b"}, "2_1": {"player": "c"}}}]}
    c = lpdb.compact(m)
    g = c["match2games"][0]
    assert g["extradata"]["rounds"] == "<2 rounds>"
    assert g["opponents"][0]["players"].startswith("<2 players")
    assert list(g["participants"]) == ["1_1", "..."]
    assert len(m["match2games"][0]["participants"]) == 3


def _gsl(letter, names, results):
    """5 GSL matchlist records of one group; results: winners of O1, O2, W, E, D."""
    heads = ["Opening Matches", "", "Winners Match", "Elimination Match", "Decider Match"]
    o1, o2 = names[:2], names[2:]
    w1, w2 = results[0], results[1]
    l1, l2 = [t for t in o1 if t != w1][0], [t for t in o2 if t != w2][0]
    ww, we = results[2], results[3]
    lw = w2 if ww == w1 else w1
    teams = [o1, o2, [w1, w2], [l1, l2], [lw, we]]
    out = []
    for i, (h, t) in enumerate(zip(heads, teams)):
        win = results[i]
        out.append({"match_id": f"X{letter}_{i + 1:04d}", "bracket_id": f"X{letter}", "section": f"Group {letter}",
                    "date": f"2026-01-0{i + 1} 09:00:00", "finished": win is not None, "best_of": 3,
                    "winner": None if win is None else ("1" if t[0] == win else "2"), "teams": t,
                    "bracket": {"type": "matchlist", "header": h, "inheritedheader": h or "Opening Matches"}})
    return out


def test_bracket_builder_gsl_groups_and_double_elimination():
    from valopoint.sources.lpdb_bracket import DE8, DE8_IDS, build_bracket
    groups = {"A": ["a1", "a2", "a3", "a4"], "B": ["b1", "b2", "b3", "b4"]}
    sched = _gsl("A", groups["A"], ["a1", "a3", "a1", "a2", "a2"]) + _gsl("B", groups["B"], ["b1", "b3", "b3", "b2", "b1"])
    sched += _gsl("C", ["c1", "c2", "c3", "c4"], [None] * 5) + _gsl("D", ["d1", "d2", "d3", "d4"], [None] * 5)
    feeds = {"R02-M001": ["R01-M001", "R01-M002"], "R02-M002": ["R01-M003", "R01-M004"],
             "R02-M003": ["R01-M005"], "R02-M004": ["R01-M006"], "R03-M001": ["R02-M003", "R02-M004"],
             "R04-M001": ["R02-M001", "R02-M002"], "R04-M002": ["R03-M001"], "R05-M001": ["R04-M001", "R04-M002"]}
    for s in DE8_IDS:
        low = feeds.get(s, [])
        edges = [{"opponentIndex": i if len(low) == 2 else 1, "lowerMatchIndex": i} for i in range(len(low))]
        teams = ["a1", "b1"] if s == "R01-M001" else [None, None]   # drawn seed named by LPDB
        sched.append({"match_id": f"XPLF_{s}", "bracket_id": "XPLF", "section": "Playoffs", "date": "2026-01-10 09:00:00",
                      "finished": False, "best_of": 5 if s in ("R04-M002", "R05-M001") else 3, "winner": None,
                      "teams": teams, "bracket": {"type": "bracket", "bracketType": DE8,
                                                  "lowerMatchIds": [f"XPLF_{x}" for x in low], "loweredges": edges}})
    br = build_bracket({"event_id": "x", "name": "X"}, sched)
    m = {x["id"]: x for x in br["matches"]}
    assert br["kind"] == "full" and br["final"] == "GF" and len(m) == 34
    assert (m["A-W"]["a"], m["A-W"]["b"], m["A-D"]["a"], m["A-D"]["b"]) == ("W:A-O1", "W:A-O2", "L:A-W", "W:A-E")
    # drawn seed named by LPDB -> references to the group result (b1 went through the B decider)
    assert (m["UQF1"]["a"], m["UQF1"]["b"]) == ("W:A-W", "W:B-D")
    assert "UQF1" not in br["assumed"] and "UQF3" in br["assumed"]
    assert (m["LR1-1"]["a"], m["LR1-1"]["b"]) == ("L:UQF1", "L:UQF2")
    assert (m["LR2-1"]["a"], m["LR2-1"]["b"]) == ("L:USF2", "W:LR1-1")
    assert (m["LF"]["a"], m["LF"]["b"]) == ("L:UF", "W:LSF")
    assert (m["GF"]["a"], m["GF"]["b"]) == ("W:UF", "W:LF")
    assert br["results"]["A-W"] == "a1" and "C-O1" not in br["results"]
    # the previous bracket of the same event keeps its id; renamed teams become aliases
    prev = {"id": "old-1", "name": "x", "matches": [{"id": "A-O1", "a": "a-one", "b": "a2"}]}
    br2 = build_bracket({"event_id": "x", "name": "X"}, sched, prev=prev)
    assert br2["id"] == "old-1" and br2["aliases"] == {"a-one": "a1"}


def test_client_retries_429_a_few_times_then_succeeds(monkeypatch):
    class R:
        def __init__(self, code):
            self.status_code, self.content, self.text, self.headers = code, b"x", "<p>Too many</p>", {}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)
        def json(self):
            return {"result": [{"ok": 1}]}
    codes = iter([429, 200])
    c = lpdb.LPDB(key="k", min_interval=0, log=lambda *_: None, backoff_429=0)
    monkeypatch.setattr(c.s, "get", lambda *a, **k: R(next(codes)))
    assert c.get("match", "x") == [{"ok": 1}] and c.requests == 2
    c2 = lpdb.LPDB(key="k", min_interval=0, log=lambda *_: None, backoff_429=0, retries_429=1)
    monkeypatch.setattr(c2.s, "get", lambda *a, **k: R(429))
    import pytest
    with pytest.raises(RuntimeError):
        c2.get("match", "x")
    assert c2.requests == 2


def test_match_rounds_resolve_teams_and_sides():
    m = {"match2id": "M_0001", "date": "2026-01-01 09:00:00",
         "match2opponents": [{"name": "A"}, {"name": "B"}],
         "match2games": [{"match2gameid": 1, "map": "Ascent", "scores": [13, 11], "extradata": {"rounds": {
             "1": {"round": 1, "t1side": "atk", "winningSide": "atk", "winBy": "elimination", "planted": True,
                   "firstKill": {"byTeam": 2}, "ceremony": "Default"},
             "2": {"round": 2, "t1side": "atk", "winningSide": "def", "winBy": "defuse", "defused": True}}}}]}
    r = lpdb.match_rounds(m, "e")
    assert [(x["round"], x["winner"], x["t1side"], x["fk_team"]) for x in r] == [(1, "A", "atk", "B"), (2, "B", "atk", None)]
    assert r[0]["game_id"] == "M_0001_1" and r[1]["win_by"] == "defuse"
