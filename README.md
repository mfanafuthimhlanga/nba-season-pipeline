# nba-season-pipeline

A daily batch pipeline for the 2026-27 NBA season on Databricks: ESPN box
scores → raw JSON → bronze → silver → dbt gold marts.

    ESPN site API ──► landing volume ──► bronze ──────► silver ───────► gold (dbt)
    scoreboard +      untouched JSON     one row per    typed tables,   2 dims, 2 facts,
    one summary       per game date      file, payload  MERGEd on keys  6 marts, tested
    per game                             as a string

| Layer | Where | Written by |
|---|---|---|
| landing | `/Volumes/nba/raw/landing/{scoreboard,summary}/game_date=YYYY-MM-DD/` | `src/nba/ingest.py` |
| bronze | `nba.bronze.scoreboard`, `nba.bronze.summary` | `src/nba/bronze.py` |
| silver | `nba.silver.games`, `team_game_stats`, `player_game_stats` | `src/nba/silver.py` |
| gold | `nba.staging` / `nba.intermediate` views, `nba.gold` tables | `dbt/nba` ([README](dbt/nba/README.md)) |

Every step takes one `game_date` (a US Eastern game day) and replaces only that
date, so any step can be rerun safely.

## Layout

    src/nba/          Python package: config (all names and rules), espn client,
                      ingest, bronze, silver
    src/jobs/         Databricks notebooks: 01_ingest_raw, 02_load_bronze,
                      03_build_silver, backfill
    src/setup/        00_setup.sql: catalog, schemas, volume, silver tables
    dbt/nba/          dbt project for the gold layer
    deploy/           nba_daily.job.json (the job, exported) and export_job.py
    tests/            unit tests for the parts that run without Spark
    docs/runbook.md   what to do when a run fails; rerunning a date; new season
    docs/issues.md    known issues and how each was resolved

## Production: the `nba_daily` job

A Databricks job runs daily at 11:00 Africa/Johannesburg (09:00 UTC), after the
night's games in the US are over:

    ingest_raw → load_bronze → build_silver → dbt_build (dbt deps, seed, build)

- Code comes from this repository's `main` branch: **a push to main is a deploy.**
- `ingest_raw` retries once after an hour: it refuses to write a date while any
  game is not final (`GamesNotFinalError`), and a late game is fixed by waiting.
  The other tasks do not retry: their failures are code or data problems.
- Job parameter `game_date`: blank = yesterday in New York. `ingest_raw`
  publishes the date it resolved as a task value; the later tasks use it.
- A run takes about 3.5 minutes. The definition lives in Databricks; after
  changing it in the UI, run `python deploy/export_job.py` and commit
  `deploy/nba_daily.job.json`.

## First-time setup

1. Run `src/setup/00_setup.sql` in the workspace.
2. Create the `nba_daily` job from `deploy/nba_daily.job.json` (fill in the
   SQL warehouse and notification e-mail), with Git source = this repository.
3. Load the season so far: run `src/jobs/backfill.py` with a two-day window
   first to check the output, then the full range. Then run `dbt build` once.

## Local development

    uv venv --python 3.12
    uv pip install -r requirements.txt
    .venv\Scripts\activate            # Windows (source .venv/bin/activate elsewhere)
    python -m pytest                  # config, ESPN client, ingest
    cd dbt/nba && dbt deps && dbt build

dbt needs a `nba` profile in `~/.dbt/profiles.yml` (see the
[dbt README](dbt/nba/README.md)). The Spark modules (`bronze.py`, `silver.py`)
run only on Databricks.

If the repository folder moves, recreate `.venv`: pip's `.exe` launchers and
the activate scripts store the venv's absolute path.

## Backfill

`src/jobs/backfill.py` runs ingest → bronze → silver for every date in a range,
with the same functions as the daily job. Widgets: `start_date` (blank = season
start) and `end_date` (blank = yesterday). A failed date does not stop the loop;
failures are listed and the notebook then raises, so the run ends red. Rerun a
single date by setting both widgets to it.

## Data quality

Every `dbt build` (the job's last task) checks the data as well as building it:

- **Every scheduled date is loaded.** `stg_schedule_dates` reads ESPN's season
  calendar from the latest scoreboard, and
  `tests/assert_scheduled_dates_loaded.sql` fails if any scheduled date from
  `season_start` to yesterday has no final game in silver. This catches an
  empty scoreboard on a game night and a failed date nobody reran, both of
  which otherwise leave every task green. It ends the run red without
  stopping gold from building.
- **Tests on every model** (keys, relationships, ranges, row counts), run right
  after the model they test; a failure skips everything downstream.
- **Marts agree with each other.** The latest date of `mart_standings_history`
  must match `mart_team_form`.

The job e-mails on failure. [docs/runbook.md](docs/runbook.md) lists each
failure and what to do.

The schedule check cannot tell you the job did not run at all (a paused
schedule, a workspace outage): then nothing runs and nothing e-mails. The
job's last run is in the Databricks UI, or `databricks jobs list-runs`.

## Using the data

Point dashboards and queries at `nba.gold` only; `nba.staging` and
`nba.intermediate` are internal views. Every gold table and column has a
description, written to Unity Catalog (Catalog Explorer shows it) and listed in
[dbt/nba/README.md](dbt/nba/README.md#gold-tables). Gold is rebuilt in full on
every run, after yesterday's games are loaded.

## Source

ESPN's site API (`site.api.espn.com`) is public but unofficial and
undocumented: no contract, no published rate limits. The client pauses 0.5 s
between calls, retries timeouts, 429 and 5xx with backoff, and parses only the
fields it uses so new ESPN fields cannot break silver.
