"""Bracket of the most relevant event from imported LPDB schedules (data/schedule/<event>.json).

LPDB match2 records link a bracket match to the matches that feed it with their
winners (match2bracketdata.lowerMatchIds / loweredges). Losers dropping into the
lower bracket are not linked, so they come from the bracket template (checked on
completed events: see LOSER_FEEDS). Group stage (GSL) matchlists are not linked
either: their order is fixed (2 openings, winners, elimination, decider).

Output: the source-independent bracket of valopoint.brackets, with W:/L: references
so the app can follow a user's picks before teams are known:
  * GSL group X: X-O1, X-O2, X-W, X-E, X-D
  * 8-team double elimination: UQF1-4, USF1-2, UF, LR1-1/2, LR2-1/2, LSF, LF, GF
Upper quarter-final seeds are drawn after the groups. Once LPDB names them they are
written as references to the group result that sent each team there (W:A-W, W:C-D);
until then a cross seeding is assumed and listed in "assumed".
Other formats fall back to the matches whose two teams are known (kind "list").
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..brackets import pick_event

# app id of each match of the 8-team double elimination template (LPDB id suffix -> id, label)
DE8 = "Bracket/8U4L2DSL1D"
DE8_IDS = {
    "R01-M001": ("UQF1", "상위 8강"), "R01-M002": ("UQF2", "상위 8강"),
    "R01-M003": ("UQF3", "상위 8강"), "R01-M004": ("UQF4", "상위 8강"),
    "R01-M005": ("LR1-1", "하위 1R"), "R01-M006": ("LR1-2", "하위 1R"),
    "R02-M001": ("USF1", "상위 4강"), "R02-M002": ("USF2", "상위 4강"),
    "R02-M003": ("LR2-1", "하위 2R"), "R02-M004": ("LR2-2", "하위 2R"),
    "R03-M001": ("LSF", "하위 4강"), "R04-M001": ("UF", "상위 결승"),
    "R04-M002": ("LF", "하위 결승"), "R05-M001": ("GF", "결승"),
}
# lower-bracket slots filled by an upper-bracket loser: (match, opponent index) -> upper match.
# Matches every completed 8U4L2DSL1D event in the 2025-2026 data (Champions, Masters, leagues).
LOSER_FEEDS = {
    DE8: {("R01-M005", 0): "R01-M001", ("R01-M005", 1): "R01-M002",
          ("R01-M006", 0): "R01-M003", ("R01-M006", 1): "R01-M004",
          ("R02-M003", 0): "R02-M002", ("R02-M004", 0): "R02-M001",
          ("R04-M002", 0): "R04-M001"},
}
GSL = {"opening": "O", "winner": "W", "elimination": "E", "decider": "D"}
GSL_LABEL = {"O": "오프닝", "W": "승자전", "E": "패자전", "D": "최종전"}


def _sfx(match_id: str) -> str:
    return re.sub(r"^.*_", "", match_id)


def _iso(d) -> str | None:
    if not d:
        return None
    try:
        return datetime.fromisoformat(str(d)).replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None


def _winner(m: dict) -> str | None:
    w = str(m.get("winner") or "")
    if not m.get("finished") or w not in ("1", "2"):
        return None
    t = (m.get("teams") or [None, None])[int(w) - 1]
    return t or None


def _groups(sched: list[dict]) -> dict[str, dict[str, dict]] | None:
    """{letter: {O1, O2, W, E, D: match}} when every group is a 5-match GSL, else None."""
    out: dict[str, list] = {}
    for m in sched:
        g = re.match(r"^Group ([A-H])$", m.get("section") or "")
        if g and (m.get("bracket") or {}).get("type") == "matchlist":
            out.setdefault(g.group(1), []).append(m)
    if not out:
        return None
    groups = {}
    for g, ms in out.items():
        ms = sorted(ms, key=lambda m: m["match_id"])
        roles, opening = {}, 0
        for m in ms:
            head = ((m["bracket"].get("header") or m["bracket"].get("inheritedheader") or "")).lower()
            r = next((v for k, v in GSL.items() if k in head), None)
            if r == "O":
                opening += 1
                r = f"O{opening}"
            if not r or r in roles:
                return None
            roles[r] = m
        if set(roles) != {"O1", "O2", "W", "E", "D"}:
            return None
        groups[g] = roles
    return groups


def build_bracket(event: dict, sched: list[dict], vetoes: list[dict] | None = None,
                  prev: dict | None = None) -> dict:
    vetoes = {v["match_id"]: {"order": v.get("order") or [], "steps": v.get("steps") or []} for v in (vetoes or [])}
    matches, results, assumed = [], {}, []

    def add(app_id, a, b, label, m, bo=None):
        rec = {"id": app_id, "a": a, "b": b, "best_of": int(bo or m.get("best_of") or 3), "round": label,
               "match_id": m["match_id"], "time": _iso(m.get("date"))}
        if m["match_id"] in vetoes and all(m.get("teams") or [None]):
            rec["veto"] = vetoes[m["match_id"]]
        matches.append(rec)
        w = _winner(m)
        if w:
            results[app_id] = w

    groups = _groups(sched)
    group_of = {}                       # team -> "W:A-W" / "W:A-D" (how it left its group)
    if groups:
        for g in sorted(groups):
            r = groups[g]
            for i in (1, 2):
                o = r[f"O{i}"]
                add(f"{g}-O{i}", *(o.get("teams") or [None, None]), f"그룹 {g} {GSL_LABEL['O']}", o)
            add(f"{g}-W", f"W:{g}-O1", f"W:{g}-O2", f"그룹 {g} {GSL_LABEL['W']}", r["W"])
            add(f"{g}-E", f"L:{g}-O1", f"L:{g}-O2", f"그룹 {g} {GSL_LABEL['E']}", r["E"])
            add(f"{g}-D", f"L:{g}-W", f"W:{g}-E", f"그룹 {g} {GSL_LABEL['D']}", r["D"])
            for role in ("W", "D"):
                w = _winner(r[role])
                if w:
                    group_of[w] = f"W:{g}-{role}"

    po = [m for m in sched if (m.get("bracket") or {}).get("bracketType") == DE8]
    by_sfx = {_sfx(m["match_id"]): m for m in po}
    kind, final = "list", None
    if set(by_sfx) == set(DE8_IDS):
        app = {s: DE8_IDS[s][0] for s in by_sfx}
        G = sorted(groups or {})
        cross = []
        if len(G) == 4:   # assumed until the draw is known: A1-B2, B1-A2, C1-D2, D1-C2
            A, B, C, D = G
            cross = [(f"W:{A}-W", f"W:{B}-D"), (f"W:{B}-W", f"W:{A}-D"),
                     (f"W:{C}-W", f"W:{D}-D"), (f"W:{D}-W", f"W:{C}-D")]
        complete = True
        for s in sorted(by_sfx, key=lambda s: list(DE8_IDS).index(s)):
            m, (aid, label) = by_sfx[s], DE8_IDS[s]
            b = m["bracket"]
            slot = [None, None]
            ids = b.get("lowerMatchIds") or []
            for e in b.get("loweredges") or []:
                j = e.get("lowerMatchIndex")
                if isinstance(j, int) and j < len(ids):
                    slot[e["opponentIndex"]] = f"W:{app.get(_sfx(ids[j]), ids[j])}"
            for i in (0, 1):
                src = LOSER_FEEDS[DE8].get((s, i))
                if src and slot[i] is None:
                    slot[i] = f"L:{app[src]}"
            if s in ("R01-M001", "R01-M002", "R01-M003", "R01-M004"):
                names = m.get("teams") or [None, None]
                k = int(s[-1]) - 1
                if all(names) and (not groups or all(n in group_of for n in names)):
                    slot = [group_of.get(n, n) for n in names]
                elif cross:
                    slot = list(cross[k])
                    assumed.append(aid)
                else:
                    slot = list(names)
            if None in slot:
                complete = False
                break
            add(aid, slot[0], slot[1], label, m)
        if complete:
            kind, final = "full", "GF"
        else:
            matches = [x for x in matches if re.match(r"^[A-H]-", x["id"])]
            results = {k: v for k, v in results.items() if re.match(r"^[A-H]-", k)}
            assumed = []
    if kind != "full":
        # unknown format: matches whose two teams are known, in time order
        known = [m for m in sched if all(m.get("teams") or [None])
                 and not (groups and re.match(r"^Group [A-H]$", m.get("section") or ""))]
        for m in sorted(known, key=lambda m: (m.get("date") or "", m["match_id"])):
            add(f"P{_sfx(m['match_id'])}-{m.get('bracket_id') or ''}", *m["teams"], m.get("section") or "", m)
        kind = "groups" if groups else "list"
        final = matches[-1]["id"] if matches else None

    teams = sorted({x[s] for x in matches for s in ("a", "b") if x[s] and not re.match(r"^[WL]:", x[s])})
    # keep the id of the bracket already published for this event, so picks saved on
    # devices and the prediction ledger stay attached across the source change
    bid = f"lpdb-{event['event_id']}"
    aliases = {}
    if prev and prev.get("name", "").casefold() == event.get("name", "").casefold():
        bid = prev.get("id", bid)
        aliases = _aliases(prev, matches)
    out = {"id": bid, "event_id": event["event_id"], "name": event["name"], "region": event.get("region"),
           "kind": kind, "teams": teams, "matches": matches, "final": final, "results": results,
           "assumed": assumed}
    if aliases:
        out["aliases"] = aliases
    return out


def _aliases(prev: dict, matches: list[dict]) -> dict[str, str]:
    """Old team name -> new name, from the same match slots of the previous bracket."""
    old = {m["id"]: m for m in prev.get("matches", [])}
    out = {}
    for m in matches:
        o = old.get(m["id"])
        if not o:
            continue
        for s in ("a", "b"):
            a, b = o.get(s), m.get(s)
            if a and b and a != b and not re.match(r"^[WL]:", a) and not re.match(r"^[WL]:", b):
                out[a] = b
    return {a: b for a, b in out.items() if a not in out.values()}


def write_brackets(data: str | Path = "data", out: str | Path = "web/public/data/brackets.json") -> dict | None:
    """Pick the event, build its bracket and write brackets.json. Returns the bracket."""
    data, out = Path(data), Path(out)
    events = [e for e in json.loads((data / "events.json").read_text(encoding="utf-8"))
              if (data / "schedule" / f"{e['event_id']}.json").exists()]
    ev = pick_event(events)
    if not ev:
        return None
    sched = json.loads((data / "schedule" / f"{ev['event_id']}.json").read_text(encoding="utf-8"))
    vp = data / "veto" / f"{ev['event_id']}.json"
    vetoes = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else []
    prev = None
    if out.exists():
        old = json.loads(out.read_text(encoding="utf-8")).get("brackets") or []
        prev = old[0] if old else None
    br = build_bracket(ev, sched, vetoes, prev)
    out.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "brackets": [br]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return br
