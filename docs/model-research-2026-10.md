# Model research, October 2026

Question: can the model get much better with more history (data from January 2023)?

## Data
- LPDB import of 2023–2024 (24 events: LOCK//IN, Masters Tokyo / Madrid / Shanghai, Champions 2023 / 2024,
  league seasons, LCQs, China qualifier).
- LPDB has only K/D/A/ACS (no ADR, KAST, first kills/deaths) for matches before mid-2024
  (full from Champions 2024) and for the China league in every year.

## Evaluation
Walk-forward on the international events since Champions 2024 (7 events, 450 maps, 178 series):
each match predicted from data before its match day, in-event updates as on the site ("live").
Log loss (lower is better; a coin is 0.693).

Noise ceiling: a model fitted with the evaluated maps included ("hindsight") reaches only
map log loss 0.62 / accuracy 65%, so single maps are mostly noise for any public-stat model.

| | map log loss | series log loss | series accuracy |
|---|---|---|---|
| previous (drop partial rows, 2-year window, half-life 180 d) | 0.668 | 0.648 | 61% |
| adopted | 0.659 | 0.628 | 66% |
| adopted, events since 2025-06 only | 0.653 | 0.604 | 68% |

Paired bootstrap by match: new better with probability 0.90 (maps) / 0.91 (series);
the 95% intervals still include 0. Better in 5 of 7 events (worse: Masters Bangkok and Toronto 2025).

## What helped (adopted)
1. Fill missing stats from K/D/A/ACS (`partial="regress"`) instead of dropping those rows:
   keeps 2023–2024 and the China league (the China league teams return to the app).
2. Window 3 years (was 2), half-life 365 days (was 180).
3. Calibration (beta, region gamma) fitted on the same 3-year window, i.e. from 2023.
4. `w_live` 2 (in-event maps count twice), `k_dev` 8000 (stronger shrinkage of player×map / agent).

## What did not help
- Results-based team ratings (map Elo with margin, decayed round-share ratings), alone or stacked
  with the stat model: Elo alone 0.683, stacking never beat the stat model.
- Host-region advantage (host-region teams won 47.8% of maps vs 46.2% expected).
- Roster continuity (maps the lineup played together), international experience.
- Longer window without filling, `w_intl`, Huber clipping, ridge, region shrinkage floor changes.
- Filling only pre-2024 rows and still dropping recent China league rows (worse than filling all).

## Next
- Round-level data (sides, pistol rounds, win types) that LPDB has and the import used to drop.
- A larger evaluation set (domestic playoffs) so that 0.005 differences can be told from noise.

## Round-level data (added 2026-10-09)
LPDB round data (`data/rounds/`): 2025–2026, 24 events, 46k rounds (none for the China league).

Is a round-level team trait a skill or luck? Split-half reliability across each team's maps:

| trait | r | |
|---|---|---|
| pistol round win rate (rounds 1, 13) | 0.01 | luck |
| rounds 2–3 won after winning the pistol | 0.04 | luck |
| rounds 2–3 won after losing the pistol | 0.32 | weak skill |
| round won after own first kill | 0.50 | skill |
| round won after conceding the first kill | 0.65 | skill (most stable) |
| attack / defence round win rate | 0.58 / 0.40 | skill |
| post-plant win (attack) / retake (defence) | 0.38 / 0.42 | skill |

Added to the stat model (walk-forward stacking, international maps since Masters Toronto 2025,
322 maps): no trait improved log loss (stat model 0.654; with a trait 0.653–0.663). The stable
traits are already explained by the player stats (first kills, deaths, KAST); pistol and
conversion rates are noise. Round data is not used by the model.
