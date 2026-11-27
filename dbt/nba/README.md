# dbt project `nba`

Builds the gold layer from the silver Delta tables on a Databricks SQL warehouse.

    sources  nba.silver        games, team_game_stats, player_game_stats     (models/_sources.yml)
             nba.bronze        scoreboard (for ESPN's season calendar)
    staging  nba.staging       views    stg_games, stg_team_game_stats, stg_player_game_stats,
                                        stg_schedule_dates
    seed     nba.staging       table    team_conferences (30 teams: conference, division)
    inter.   nba.intermediate  view     int_team_game_with_opponent
    gold     nba.gold          tables   dim_team, dim_player, fct_team_game, fct_player_game,
                                        mart_daily_leaders, mart_team_form, mart_standings_history,
                                        mart_home_away, mart_player_consistency, mart_back_to_back_impact

`dbt build` runs 15 models, 1 seed and 108 data tests (dbt_utils 1.4.1). Each
model's tests run right after it; a failure skips everything downstream.

## Gold tables

Every table and column is described in `models/marts/_marts.yml`; shared metric
definitions (net rating, true shooting %, game score, ...) are in
`models/_docs.md`. `persist_docs` writes them to Unity Catalog as comments.

| Table | One row per | Use it for |
|---|---|---|
| `dim_team` | team (30) | team names, conference, division |
| `dim_player` | player who has appeared in a box score | player name, position, current team |
| `fct_team_game` | team per completed game (2 per game) | any team-level query: ratings, pace, rest |
| `fct_player_game` | player per completed game, DNPs included | any player-level query |
| `mart_daily_leaders` | top-10 player per game date | "best performances last night" |
| `mart_team_form` | team, as of the latest game | current standings, last-10 form |
| `mart_standings_history` | team per date with regular-season games | standings and net-rating trends over the season |
| `mart_home_away` | team | home vs away record and net rating |
| `mart_back_to_back_impact` | team | second night of back-to-backs vs rested games |
| `mart_player_consistency` | player with 10+ games | scoring average and spread |

The marts count regular-season games only. The season-level marts (team form,
home/away, back-to-back, consistency) count the current season, the highest
regular-season `season` (`macros/current_season.sql`); `mart_standings_history`
and the facts keep every season.

## Singular tests

| Test | Fails when |
|---|---|
| `tests/assert_scheduled_dates_loaded.sql` | a date ESPN schedules games on, from `season_start` to yesterday, has no final game in silver |
| `tests/assert_standings_history_matches_team_form.sql` | the latest standings in `mart_standings_history` differ from `mart_team_form` |

What to do when either fails: `docs/runbook.md`.

## Vars

Set in `dbt_project.yml`:

| Var | Meaning |
|---|---|
| `season_start` | First day of the regular season. Same date as `SEASON_START` in `src/nba/config.py`; change both each season. |
| `schedule_exceptions` | Scheduled dates with no final game on purpose (every game postponed), skipped by the schedule test. |

## Run

In production the `dbt_build` task of the `nba_daily` job runs
`dbt deps`, `dbt seed`, `dbt build` in this folder.

From a laptop, with the project's virtual environment active:

    cd dbt/nba
    dbt deps
    dbt build            # everything
    dbt build -s +mart_team_form   # one mart and what it needs

`~/.dbt/profiles.yml` needs a profile named `nba`:

```yaml
nba:
  target: dev
  outputs:
    dev:
      type: databricks
      host: <workspace>.cloud.databricks.com
      http_path: /sql/1.0/warehouses/<warehouse-id>
      token: <personal access token>
      catalog: nba
      schema: gold
      threads: 1
    prod:
      # the same connection settings as dev
```

The token is a secret: keep it in `~/.dbt`, never in this repository.

`macros/generate_schema_name.sql` prefixes `dev_` for the `dev` target only, so
a plain `dbt build` from the laptop writes `nba.dev_staging`, `nba.dev_intermediate`
and `nba.dev_gold` and never production. Every other target, including the job's
and `--target prod`, uses the schemas as named; type `--target prod` only for a
deliberate production build.
