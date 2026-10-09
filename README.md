# valopoint

A non-commercial fan project for VALORANT Champions Tour (VCT): player-stat based power points
for every team and player, and predictions for international matches and brackets.

```
Liquipedia ──LPDB API──▶ data/rows/*.csv ──model (Python)──▶ web/public/data/model.json ──▶ Svelte PWA
                         (one row per player per map)                                    (bracket simulation in the browser)
```

## Data

Match and player data come from [Liquipedia](https://liquipedia.net/valorant/) through the
LPDB API, under [CC BY-SA 3.0](https://liquipedia.net/commons/Liquipedia:Copyrights).
This repository holds the code only. To build the data yourself you need your own LPDB API key
(see [Liquipedia API](https://liquipedia.net/api)) and must follow its terms: credit Liquipedia
next to the data, use the documented API only, and stay within the request limits
(the client spaces requests at least 65 s apart, stops at a per-run budget and backs off on HTTP 429).
Set `LPDB_USER_AGENT` to a string that names your project and where it runs.

The data layout is described in [docs/data-schema.md](docs/data-schema.md); model experiments and
their results in [docs/model-research-2026-10.md](docs/model-research-2026-10.md).

## Model in short (`valopoint/model.py`)

1. Per-round stats of each player on each map: KPR, DPR, APR, FKPR, FDPR, ADR, KAST. Where only
   K/D/A/ACS exist (LPDB before mid-2024, China league), the other stats are filled by a per-role regression.
2. Standardised within role (duelist, initiator, controller, sentinel).
3. Stat weights learned by ridge regression of map round-win rate on the team stat gap.
4. Opponent adjustment, Huber clipping, time decay (half-life 365 days), three-year window.
5. Hierarchical empirical Bayes: theta(player, map, agent) = region + player + player×agent + player×map.
   Region offsets are identified by international maps only (shrinkage floor against small samples).
6. Power points: PP = 100 + 1000·theta; +10 PP ≈ +1 point of team round-win rate.
7. Map → series: round-win probability → map win probability (first to 13, overtime) →
   ban/pick model (Bo1/Bo3/Bo5) → series win probability, calibrated on past international maps.
8. During an international event its maps count twice and the model is refitted on every update.

Walk-forward backtests (`valopoint backtest`) compare in-event updates with pre-event predictions
and an Elo baseline.

## Use

```bash
pip install -e '.[dev]'
export LPDB_API_KEY=...                  # your own key
valopoint lpdb discover                  # VCT tournament pages (1 request)
valopoint lpdb import --out data         # VCT events of last year and this year
valopoint brackets                       # bracket of the current event -> web/public/data/brackets.json
valopoint export                         # model -> web/public/data/model.json
valopoint backtest
pytest

cd web && npm install && npm run dev     # the app (Svelte 5, Vite)
```

Without an API key, `valopoint synth data` writes a synthetic data set for trying the pipeline.

`web/worker/` is the Cloudflare Worker that serves the app and, on an hourly cron, asks a CI job
to refresh the data when a started match has no result yet.

## License

Code: MIT (see [LICENSE](LICENSE)). Data built with this code from Liquipedia: CC BY-SA 3.0.

valopoint was created under Riot Games' "Legal Jibber Jabber" policy using assets owned by Riot Games.
Riot Games does not endorse or sponsor this project.
