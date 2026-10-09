"""Liquipedia (LPDB API v3) source for VCT data.

Licensing and use (Liquipedia free API plan):
  * data is CC BY-SA 3.0: credit Liquipedia next to the data, with backlinks;
  * use the documented API only (never scrape wiki pages);
  * at most 60 requests per hour: this client spaces requests >= 65 s apart and
    stops after `max_requests` per run;
  * the project must be open source.

Output (source-independent schema, docs/data-schema.md) goes to <out>/:
  events.json, rows/<event_id>.csv, veto/<event_id>.json, schedule/<event_id>.json
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

API = "https://api.liquipedia.net/api/v3"
WIKI = "valorant"
# Liquipedia asks for a User-Agent that names the project and where it runs; the deploy sets
# LPDB_USER_AGENT (with the site URL), the default is for local runs.
UA = os.environ.get("LPDB_USER_AGENT") or "ValoPoint/0.2 (non-commercial fan project)"
WIKI_URL = "https://liquipedia.net/valorant/"

# VCT pages: VCT/<year>/<Region>_League/<Kickoff|Stage_N>, VCT/<year>/Stage_N/Masters, VCT/<year>/Champions
# 2024+: <Region>_League/<Kickoff|Stage_N>, Stage_N/Masters, Champions.
# 2023: one league season per region (+ Last_Chance_Qualifier), LOCK_IN_São_Paulo, Masters (Tokyo),
# China (qualifier for Champions), Champions.
EVENT_RE = re.compile(
    r"^VCT/(?P<year>20\d\d)/(?:(?P<league>Americas|EMEA|Pacific|China)_League"
    r"(?:/(?P<stage>Kickoff|Stage_\d|Last_Chance_Qualifier))?"
    r"|(?P<mstage>Stage_\d)/Masters|(?P<champ>Champions)|(?P<lockin>LOCK_IN_[^/]+)|(?P<m23>Masters)"
    r"|(?P<cnq>China))$")
REGION = {"Americas": "AMER", "EMEA": "EMEA", "Pacific": "PAC", "China": "CN"}
ROW_COLS = ["match_id", "game_id", "event_id", "event", "stage", "date", "map", "map_order", "team", "opp",
            "team_rounds", "opp_rounds", "player", "player_id", "agent", "acs", "k", "d", "a", "kast", "adr",
            "hs", "fk", "fd", "best_of", "completed"]


# ---------------------------------------------------------------- client

class LPDB:
    def __init__(self, key: str | None = None, min_interval: float = 65.0, max_requests: int = 50, log=print,
                 retries_429: int = 2, backoff_429: float = 300.0):
        self.key = key or os.environ.get("LPDB_API_KEY", "")
        if not self.key:
            raise RuntimeError("LPDB_API_KEY is not set")
        self.min_interval = min_interval
        self.max_requests = max_requests
        self.retries_429, self.backoff_429 = retries_429, backoff_429
        self.log = log
        self.requests = 0
        self._last = 0.0
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Apikey {self.key}", "User-Agent": UA,
                               "Accept-Encoding": "gzip", "Accept": "application/json"})

    def get(self, datatype: str, conditions: str, limit: int = 1000, offset: int = 0,
            order: str | None = None, query: str | None = None) -> list[dict]:
        if self.requests >= self.max_requests:
            raise RuntimeError(f"request budget for this run reached ({self.max_requests})")
        wait = self.min_interval - (time.time() - self._last)
        if self._last and wait > 0:
            time.sleep(wait)
        params = {"wiki": WIKI, "conditions": conditions, "limit": limit, "offset": offset}
        if order:
            params["order"] = order
        if query:
            params["query"] = query
        for attempt in range(self.retries_429 + 1):
            r = self.s.get(f"{API}/{datatype}", params=params, timeout=60)
            self._last = time.time()
            self.requests += 1
            self.log(f"    LPDB {datatype} [{conditions[:80]}] -> {r.status_code} ({len(r.content)} B), "
                     f"request {self.requests}/{self.max_requests}")
            if r.status_code != 429 or attempt == self.retries_429 or self.requests >= self.max_requests:
                break
            # rate limited (also happens on shared CI addresses): say why, wait long, retry a few times only
            text = re.sub(r"<[^>]+>|\s+", " ", r.text)[:300].strip()
            pause = max(float(r.headers.get("Retry-After") or 0), self.backoff_429 * (attempt + 1))
            self.log(f"    LPDB 429: {text!r}; waiting {pause:.0f} s")
            time.sleep(pause)
        r.raise_for_status()
        body = r.json()
        if body.get("error"):
            raise RuntimeError(f"LPDB error: {body['error']}")
        for w in body.get("warning") or []:
            self.log(f"    LPDB warning: {w}")
        return body.get("result") or []

    def all(self, datatype: str, conditions: str, limit: int = 1000, **kw) -> list[dict]:
        out, offset = [], 0
        while True:
            page = self.get(datatype, conditions, limit=limit, offset=offset, **kw)
            out.extend(page)
            if len(page) < limit:
                return out
            offset += limit


# ---------------------------------------------------------------- events

def classify(page: str) -> dict | None:
    """Event meta for a VCT tournament page name, or None if it is not one we use."""
    m = EVENT_RE.match(page.replace(" ", "_"))
    if not m:
        return None
    year = int(m["year"])
    if m["league"]:
        stage = (m["stage"] or "League").replace("_", " ").replace("Last Chance Qualifier", "LCQ")
        return {"region": REGION[m["league"]], "tier": "league", "year": year,
                "name": f"VCT {year}: {m['league']} {stage}"}
    if m["cnq"]:
        return {"region": "CN", "tier": "league", "year": year, "name": f"VCT {year}: China Qualifier"}
    if m["lockin"]:
        return {"region": "INTL", "tier": "masters", "year": year, "name": f"VCT {year}: LOCK//IN"}
    if m["m23"]:
        return {"region": "INTL", "tier": "masters", "year": year, "name": f"VALORANT Masters {year}"}
    if m["mstage"]:
        return {"region": "INTL", "tier": "masters", "year": year,
                "name": f"VCT {year}: Masters ({m['mstage'].replace('_', ' ')})"}
    return {"region": "INTL", "tier": "champions", "year": year, "name": f"Valorant Champions {year}"}


def event_id(page: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", page.lower()).strip("-")


def candidate_pages(years) -> list[str]:
    pages = []
    for y in years:
        for lg in REGION:
            pages += [f"VCT/{y}/{lg}_League/{st}" for st in ("Kickoff", "Stage_1", "Stage_2")]
        pages += [f"VCT/{y}/Stage_1/Masters", f"VCT/{y}/Stage_2/Masters", f"VCT/{y}/Champions"]
    return pages


def list_tournaments(client: LPDB, years) -> list[dict]:
    """Every VCT-series tournament record since the first given year (1 request), for checking page names."""
    since = f"{min(years)}-01-01"
    recs = client.all("tournament", f"[[seriespage::VALORANT_Champions_Tour]] AND [[startdate::>{since}]]")
    return [{"page": (t.get("pagename") or "").replace(" ", "_"), "name": t.get("name"),
             "start": t.get("startdate"), "end": t.get("enddate"), "tier": t.get("liquipediatier"),
             "type": t.get("type"), "used": bool(classify((t.get("pagename") or "").replace(" ", "_")))}
            for t in sorted(recs, key=lambda t: t.get("startdate") or "")]


def discover(client: LPDB, years) -> dict[str, dict]:
    """page -> tournament record (name, dates) for VCT events of the given years."""
    since = f"{min(years)}-01-01"
    # the tournament record has no `series` field; seriespage is the series page name (underscores)
    recs = client.all("tournament", f"[[seriespage::VALORANT_Champions_Tour]] AND [[startdate::>{since}]]")
    found = {}
    for t in recs:
        page = (t.get("pagename") or "").replace(" ", "_")
        if classify(page) and int(classify(page)["year"]) in set(years):
            found[page] = t
    return found


# ---------------------------------------------------------------- normalisation

def _num(x):
    if x in (None, "", "-"):
        return None
    try:
        return float(str(x).replace("%", ""))
    except ValueError:
        return None


def _json(x):
    if isinstance(x, str):
        try:
            return json.loads(x)
        except ValueError:
            return {}
    return x or {}


def _seq(x):
    """LPDB returns arrays either as lists or as {"1": ..., "2": ...} objects."""
    x = _json(x)
    if isinstance(x, dict):
        return [v for _, v in sorted(x.items(), key=lambda kv: int(re.sub(r"\D", "", str(kv[0])) or 0))]
    return list(x or [])


def _game_players(game: dict, idx: int, match_players: list[dict]) -> list[dict]:
    """Per-map player stat dicts of opponent `idx` (0-based), whatever the record layout."""
    opps = _seq(game.get("opponents"))
    if len(opps) > idx and isinstance(opps[idx], dict) and opps[idx].get("players"):
        players = [p for p in _seq(opps[idx]["players"]) if isinstance(p, dict) and p]
    else:
        parts = _json(game.get("participants"))
        players = [v for k, v in sorted(parts.items()) if str(k).startswith(f"{idx + 1}_") and isinstance(v, dict)]
        for k, v in sorted(parts.items()):
            if str(k).startswith(f"{idx + 1}_") and isinstance(v, dict):
                j = int(str(k).split("_")[1]) - 1
                if not v.get("player") and 0 <= j < len(match_players):
                    v["player"] = match_players[j].get("name")
    return players


def _stat(p: dict, *keys):
    for k in keys:
        if k in p:
            return _num(p[k])
    return None


def _played_games(m: dict):
    """(map order, game, map, [score1, score2]) of the maps actually played, in order."""
    games = sorted(_seq(m.get("match2games")), key=lambda g: int(_num(g.get("match2gameid")) or 0))
    order = 0
    for g in games:
        mp = (g.get("map") or "").strip()
        scores = [_num(s) for s in _seq(g.get("scores"))] or \
                 [_num(o.get("score")) for o in _seq(g.get("opponents")) if isinstance(o, dict)]
        if not mp or mp.upper() == "TBD" or len(scores) < 2 or scores[0] is None or scores[1] is None \
                or (scores[0] == 0 and scores[1] == 0):
            continue
        order += 1
        yield order, g, mp, scores


ROUND_COLS = ["game_id", "match_id", "event_id", "date", "map", "round", "team1", "team2", "t1side",
              "winner", "win_by", "planted", "defused", "flawless", "ceremony", "fk_team"]


def match_rounds(m: dict, ev_id: str) -> list[dict]:
    """One row per round of every played map (game extradata.rounds), team names resolved."""
    opps = _seq(m.get("match2opponents"))
    if len(opps) != 2:
        return []
    teams = [o.get("name") or o.get("template") or "" for o in opps]
    mid = str(m.get("match2id") or "")
    out = []
    for order, g, mp, _ in _played_games(m):
        rounds = _json(_json(g.get("extradata")).get("rounds"))
        if not isinstance(rounds, dict) or not rounds:
            continue
        for _, r in sorted(rounds.items(), key=lambda kv: int(_num(kv[0]) or 0)):
            if not isinstance(r, dict) or not r.get("winningSide"):
                continue
            t1 = r.get("t1side")
            fk = _json(r.get("firstKill")).get("byTeam") if isinstance(r.get("firstKill"), (dict, str)) else None
            out.append({"game_id": f"{mid}_{order}", "match_id": mid, "event_id": ev_id,
                        "date": str(g.get("date") or m.get("date") or "")[:10], "map": mp,
                        "round": int(_num(r.get("round")) or 0), "team1": teams[0], "team2": teams[1], "t1side": t1,
                        "winner": teams[0] if r.get("winningSide") == t1 else teams[1],
                        "win_by": r.get("winBy"), "planted": bool(r.get("planted")), "defused": bool(r.get("defused")),
                        "flawless": bool(r.get("flawless")), "ceremony": r.get("ceremony"),
                        "fk_team": teams[int(fk) - 1] if str(fk) in ("1", "2") else None})
    return out


def match_rows(m: dict, ev_id: str, ev_name: str) -> list[dict]:
    """Canonical player-map rows of one LPDB match2 record (finished maps only)."""
    opps = _seq(m.get("match2opponents"))
    if len(opps) != 2:
        return []
    teams = [o.get("name") or o.get("template") or "" for o in opps]
    if not all(teams):
        return []
    mplayers = [_seq(o.get("match2players")) for o in opps]
    display = {}
    for pl in mplayers:
        for p in pl:
            if isinstance(p, dict) and p.get("name"):
                display[p["name"]] = p.get("displayname") or p["name"]
    mid = str(m.get("match2id") or "")
    finished = str(m.get("finished")) in ("1", "true", "True")
    bo = int(_num(m.get("bestof")) or 3)
    stage = (m.get("section") or "").strip()
    rows = []
    for order, g, mp, scores in _played_games(m):
        gdate = str(g.get("date") or m.get("date") or "")[:10]
        gid = f"{mid}_{order}"
        for i in (0, 1):
            for p in _game_players(g, i, mplayers[i]):
                pid = p.get("player") or p.get("name") or ""
                if not pid:
                    continue
                rows.append({
                    "match_id": mid, "game_id": gid, "event_id": ev_id, "event": ev_name, "stage": stage,
                    "date": gdate, "map": mp, "map_order": order, "team": teams[i], "opp": teams[1 - i],
                    "team_rounds": scores[i], "opp_rounds": scores[1 - i],
                    "player": p.get("displayName") or p.get("displayname") or display.get(pid, pid),
                    "player_id": pid, "agent": (p.get("agent") or "").lower(),
                    "acs": _stat(p, "acs"), "k": _stat(p, "kills"), "d": _stat(p, "deaths"),
                    "a": _stat(p, "assists"), "kast": _stat(p, "kast"), "adr": _stat(p, "adr"),
                    "hs": _stat(p, "hs"), "fk": _stat(p, "firstKills", "firstkills"),
                    "fd": _stat(p, "firstDeaths", "firstdeaths"), "best_of": bo, "completed": finished,
                })
    return rows


def match_veto(m: dict, ev_id: str) -> dict | None:
    """Map veto as {steps: [[team, ban|pick|remains, map]], order: [...]} from match extradata."""
    ex = _json(m.get("extradata"))
    mv = _json(ex.get("mapveto"))
    opps = _seq(m.get("match2opponents"))
    if not mv or len(opps) != 2:
        return None
    teams = [o.get("name") or o.get("template") for o in opps]
    rounds = _seq(mv) if not isinstance(mv, list) else mv
    first = None
    steps, picks, decider = [], [], None
    for r in rounds:
        if not isinstance(r, dict):
            continue
        first = first or int(_num(r.get("vetostart") or r.get("firstpick") or ex.get("firstpick")) or 1)
        kind = (r.get("type") or "").lower()
        if kind == "decider":
            decider = r.get("decider") or r.get("team1") or r.get("map")
            continue
        if kind not in ("ban", "pick"):
            continue
        order = (0, 1) if first == 1 else (1, 0)
        for t in order:
            mp = r.get(f"team{t + 1}")
            if mp:
                steps.append([teams[t], kind, mp])
                if kind == "pick":
                    picks.append(mp)
    if decider:
        steps.append([None, "remains", decider])
    if not steps:
        return None
    return {"match_id": str(m.get("match2id")), "event_id": ev_id, "date": str(m.get("date") or "")[:10],
            "team1": teams[0], "team2": teams[1], "best_of": int(_num(m.get("bestof")) or 3),
            "steps": steps, "order": picks + ([decider] if decider else [])}


def match_schedule(m: dict) -> dict:
    """Compact record of any match (played or not) for bracket building."""
    opps = _seq(m.get("match2opponents"))
    return {"match_id": str(m.get("match2id")), "bracket_id": m.get("match2bracketid"),
            "date": m.get("date"), "finished": str(m.get("finished")) in ("1", "true", "True"),
            "best_of": int(_num(m.get("bestof")) or 3), "winner": m.get("winner"),
            "teams": [o.get("name") or o.get("template") or None for o in opps],
            "scores": [_num(o.get("score")) for o in opps],
            "section": m.get("section"), "bracket": _json(m.get("match2bracketdata"))}


# ---------------------------------------------------------------- import

def import_events(client: LPDB, out: str | Path, years, only: set | None = None, refresh_complete=False,
                  log=print) -> dict:
    """Fetch matches of VCT events and write the canonical files. Returns a summary."""
    import pandas as pd
    out = Path(out)
    for sub in ("rows", "veto", "schedule", "rounds"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    ev_path = out / "events.json"
    events = {e["page"]: e for e in json.loads(ev_path.read_text(encoding="utf-8")) if e.get("page")} \
        if ev_path.exists() else {}
    try:
        meta = discover(client, years)
    except Exception as e:     # discovery is a convenience; fall back to the known page names
        log(f"  tournament discovery failed ({e}); using candidate page names")
        meta = {}
    # discovered pages only (no requests for guessed page names); guesses only when discovery found nothing
    pages = sorted(meta) if meta else candidate_pages(years)
    summary = {}
    today = date.today().isoformat()
    for page in pages:
        if only and page not in only and event_id(page) not in only:
            continue
        known = events.get(page)
        if known and known.get("complete") and not refresh_complete:
            continue
        info = classify(page)
        t = meta.get(page, {})
        eid = event_id(page)
        recs = client.all("match", f"[[parent::{page}]]", order="date ASC")
        if not recs:
            continue
        name = t.get("name") or info["name"]
        rows, vetoes, sched, rnds = [], [], [], []
        for m in recs:
            rows += match_rows(m, eid, name)
            rnds += match_rounds(m, eid)
            v = match_veto(m, eid)
            if v:
                vetoes.append(v)
            sched.append(match_schedule(m))
        dates = sorted(str(m.get("date") or "")[:10] for m in recs if m.get("date"))
        end = str(t.get("enddate") or (dates[-1] if dates else ""))[:10]
        complete = all(s["finished"] for s in sched) and bool(end) and end < today
        if rows:
            pd.DataFrame(rows, columns=ROW_COLS).to_csv(out / "rows" / f"{eid}.csv", index=False)
        if rnds:
            pd.DataFrame(rnds, columns=ROUND_COLS).to_csv(out / "rounds" / f"{eid}.csv", index=False)
        (out / "veto" / f"{eid}.json").write_text(json.dumps(vetoes, ensure_ascii=False), encoding="utf-8")
        (out / "schedule" / f"{eid}.json").write_text(json.dumps(sched, ensure_ascii=False), encoding="utf-8")
        events[page] = {"event_id": eid, "name": name, "region": info["region"], "tier": info["tier"],
                        "year": info["year"], "start": str(t.get("startdate") or (dates[0] if dates else ""))[:10],
                        "end": end, "complete": complete, "source": "liquipedia", "page": page,
                        "url": WIKI_URL + page}
        summary[eid] = {"matches": len(recs), "rows": len(rows), "vetoes": len(vetoes), "complete": complete}
        log(f"  {eid}: {len(recs)} matches, {len(rows)} player-map rows, {len(vetoes)} vetoes")
        ev_path.write_text(json.dumps(sorted(events.values(), key=lambda e: e.get("start") or ""), indent=1,
                                      ensure_ascii=False), encoding="utf-8")
    summary["_requests"] = client.requests
    summary["_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return summary


def inspect(client: LPDB, page: str = "VCT/2026/Champions", n: int = 2) -> dict:
    """Raw sample for schema checks: one tournament record and `n` match records."""
    t = client.get("tournament", f"[[pagename::{page}]]", limit=1)
    m = client.get("match", f"[[parent::{page}]] AND [[finished::1]]", limit=n, order="date ASC")
    return {"tournament": t, "matches": [compact(x) for x in m]}


def compact(m: dict) -> dict:
    """A match record without the bulky per-round and duplicated per-player game data."""
    m = json.loads(json.dumps(m))
    for g in _seq(m.get("match2games")) if isinstance(m.get("match2games"), list) else []:
        ex = g.get("extradata")
        if isinstance(ex, dict) and "rounds" in ex:
            ex["rounds"] = f"<{len(_json(ex['rounds']))} rounds>"
        for o in g.get("opponents") or []:
            if isinstance(o, dict) and o.get("players"):
                o["players"] = f"<{len(_seq(o['players']))} players, same fields as participants>"
        parts = _json(g.get("participants"))
        if isinstance(parts, dict) and len(parts) > 2:
            keep = dict(list(sorted(parts.items()))[:1])
            keep["..."] = f"<{len(parts)} participants>"
            g["participants"] = keep
    return m
