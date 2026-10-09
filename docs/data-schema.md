# Data schema (source-independent)

Every data source writes the same files. The model (`valopoint/dataset.py`) only reads these.

## `<data>/events.json`

A list of events:

| field | type | example |
|---|---|---|
| `event_id` | str | `vct-2026-champions` |
| `name` | str | `Valorant Champions 2026` |
| `region` | `AMER` · `EMEA` · `PAC` · `CN` · `INTL` | `INTL` |
| `tier` | `league` · `masters` · `champions` | `champions` |
| `year` | int | `2026` |
| `start`, `end` | ISO date | `2026-09-24` |
| `complete` | bool | every match finished and the end date passed |
| `source` | str | `liquipedia` |
| `page` | str | source page, e.g. `VCT/2026/Champions` |
| `url` | str | backlink for crediting |

## `<data>/rows/<event_id>.csv`

One row per (map, player). IDs are strings.

| column | meaning |
|---|---|
| `match_id`, `game_id` | series id; map id (`<match_id>_<map order>`) |
| `event_id`, `event`, `stage` | event id and name; stage or section |
| `date` | ISO date of the map |
| `map`, `map_order` | map name; 1-based position in the series |
| `team`, `opp` | team names (source page names) |
| `team_rounds`, `opp_rounds` | round score of the map |
| `player`, `player_id` | display name; stable id (source page name) |
| `agent` | lower-case agent name |
| `k`, `d`, `a` | kills, deaths, assists (**required**) |
| `fk`, `fd`, `adr`, `kast` | first kills, first deaths, ADR, KAST in % (**optional**: missing for the China league on Liquipedia) |
| `acs`, `hs` | descriptive only, not used by the model |
| `best_of`, `completed` | series length; series finished |

How rows with missing optional stats are handled: `dataset.load(partial=...)` (default `drop`; see the docstring for the measured comparison).

## `<data>/veto/<event_id>.json`

`[{match_id, event_id, date, team1, team2, best_of, steps: [[team, "ban"|"pick", map], ..., [null, "remains", map]], order: [maps in play order]}]`

## `<data>/schedule/<event_id>.json`

Every match, played or not, for bracket building:
`[{match_id, bracket_id, date, finished, best_of, winner, teams, scores, section, bracket}]`

## `<data>/rounds/<event_id>.csv`
One row per round of every played map, for maps that LPDB has round data for (absent for some events).

| column | meaning |
|---|---|
| `game_id`, `match_id`, `event_id`, `date`, `map` | same ids as `rows/` |
| `round` | round number (1–12 first half, 13–24 second half, 25+ overtime) |
| `team1`, `team2` | the two teams (LPDB opponent order) |
| `t1side` | side of `team1` in this round: `atk` or `def` |
| `winner` | team that won the round |
| `win_by` | `elimination`, `defuse`, `detonate` or `time` |
| `planted`, `defused`, `flawless` | booleans |
| `ceremony` | `Default`, `Clutch`, `Ace`, `Flawless`, `Closer`, … |
| `fk_team` | team that got the first kill (empty if unknown) |
