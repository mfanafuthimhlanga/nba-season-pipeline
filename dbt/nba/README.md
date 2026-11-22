# dbt project `nba`

Builds the gold layer from the silver Delta tables on a Databricks SQL warehouse.

    sources  nba.silver.games / team_game_stats / player_game_stats   (models/schema.yml)
    staging  nba.staging       views    stg_games, stg_team_game_stats, stg_player_game_stats
    seed     nba.staging       table    team_conferences (30 teams: conference, division)
    inter.   nba.intermediate  view     int_team_game_with_opponent
    gold     nba.gold          tables   dim_team, dim_player, fct_team_game, fct_player_game,
                                        mart_daily_leaders, mart_team_form, mart_home_away,
                                        mart_player_consistency, mart_back_to_back_impact

`dbt build` runs 13 models, 1 seed and 89 data tests (dbt_utils 1.4.1). Each
model's tests run right after it; a failure skips everything downstream.

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
```

The token is a secret: keep it in `~/.dbt`, never in this repository.
