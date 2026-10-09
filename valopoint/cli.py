from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main(argv=None):
    ap = argparse.ArgumentParser(prog="valopoint")
    ap.add_argument("--data", default="data", help="data dir with events.json and rows/")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("lpdb", help="Liquipedia (LPDB API) data: inspect | discover | import | coverage")
    s.add_argument("action", choices=["inspect", "discover", "import", "coverage"])
    s.add_argument("--out", default="data/lpdb", help="output dir for imported data")
    s.add_argument("--years", type=int, nargs="+", help="default: last year and this year")
    s.add_argument("--event", nargs="*", help="only these tournament pages or event ids")
    s.add_argument("--page", default="VCT/2026/Champions", help="tournament page for inspect")
    s.add_argument("--max-requests", type=int, default=50, help="request budget per run (free plan: 60/hour)")
    s.add_argument("--refresh", action="store_true", help="re-import events already marked complete")

    s = sub.add_parser("brackets", help="bracket of the most relevant event -> web/public/data/brackets.json")
    s.add_argument("--out", default="web/public/data/brackets.json")

    s = sub.add_parser("due", help="exit 0 when a started match of the published bracket still has no result")
    s.add_argument("--brackets", default="web/public/data/brackets.json")

    s = sub.add_parser("ledger", help="append pre-match predictions to the append-only ledger")
    s.add_argument("--model", default="web/public/data/model.json")
    s.add_argument("--brackets", default="web/public/data/brackets.json")
    s.add_argument("--out", default="web/public/data/ledger.json")

    s = sub.add_parser("synth", help="write a synthetic dataset (for testing)")
    s.add_argument("out")

    s = sub.add_parser("players", help="player power points")
    s.add_argument("--top", type=int, default=25)
    s.add_argument("--map"); s.add_argument("--agent")

    sub.add_parser("backtest", help="walk-forward: live vs frozen vs Elo")

    s = sub.add_parser("tune", help="grid search Params on international maps")
    s.add_argument("--grid", default='{"w_live":[1,2,4],"half_life_days":[90,180,365]}')

    s = sub.add_parser("export", help="build web/public/data/model.json")
    s.add_argument("--out", default="web/public/data/model.json")
    s.add_argument("--source", help="override the data source name shown in the app")
    s.add_argument("--as-of")

    a = ap.parse_args(argv)
    data = Path(a.data)

    if a.cmd == "lpdb":
        from datetime import date
        from .sources import lpdb
        years = a.years or [date.today().year - 1, date.today().year]
        if a.action == "coverage":
            from .sources.coverage import report
            print(report(Path(a.out)))
            return
        client = lpdb.LPDB(max_requests=a.max_requests)
        if a.action == "discover":
            for t in lpdb.list_tournaments(client, years):
                print(f"{'+' if t['used'] else ' '} {t['start']} {t['end']} tier={t['tier']} {t['page']}  |  {t['name']}")
            return
        if a.action == "inspect":
            sample = lpdb.inspect(client, a.page)
            print(json.dumps(sample, ensure_ascii=False, indent=1))
            return
        summary = lpdb.import_events(client, a.out, years, only=set(a.event) if a.event else None,
                                     refresh_complete=a.refresh)
        print(json.dumps(summary, indent=1))
        return
    if a.cmd == "brackets":
        from .sources.lpdb_bracket import write_brackets
        br = write_brackets(data, a.out)
        print(f"brackets: {br['name']} ({br['kind']}, {len(br['matches'])} matches, {len(br['results'])} results)"
              if br else "brackets: no event with a schedule")
        return
    if a.cmd == "due":
        from datetime import datetime, timezone
        from .brackets import results_due
        p = Path(a.brackets)
        brs = json.loads(p.read_text(encoding="utf-8")).get("brackets", []) if p.exists() else []
        due = [f"{b['name']}: {mid}" for b in brs for mid in results_due(b, datetime.now(timezone.utc))]
        print("results due: " + ", ".join(due) if due else "no results due")
        raise SystemExit(0 if due else 10)
    if a.cmd == "ledger":
        from .ledger import update
        n = update(a.model, a.brackets, a.out)
        print(f"ledger: {n} new snapshot(s)")
        return
    if a.cmd == "synth":
        from .synth import generate
        generate(a.out)
        print("wrote synthetic dataset to", a.out)
        return

    from .dataset import load
    df = load(data)

    if a.cmd == "players":
        from .model import fit, pp
        m = fit(df)
        pl = m.player.copy()
        pl["pp"] = [m.theta(k, a.map, a.agent) for k in pl.index]
        pl["pp"] = pp(pl["pp"])
        pl = pl[pl["rounds"] >= 200].sort_values("pp", ascending=False).head(a.top)
        print(pl[["name", "team", "region", "rounds", "pp"]].round(1).to_string())
        print("\nregion offsets (PP/player):", {k: round(v * 1000, 1) for k, v in m.region.items()})
        print("learned stat weights:", {k: round(v, 5) for k, v in m.diag["weights"].items()})
    elif a.cmd == "backtest":
        from .backtest import compare
        print(json.dumps(compare(df, log=print), indent=1))
    elif a.cmd == "tune":
        from .backtest import tune
        print(tune(df, json.loads(a.grid)).to_string())
    elif a.cmd == "export":
        from .export import build, write
        mj = build(df, as_of=a.as_of, source=a.source, brackets_dir=data / "brackets", data_dir=data)
        write(mj, a.out)
        print(f"wrote {a.out}: {len(mj['teams'])} teams, {len(mj['players'])} players")


if __name__ == "__main__":
    main()
