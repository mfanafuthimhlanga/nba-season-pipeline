# Runbook: `nba_daily`

What to do when the daily job sends a failure e-mail, and the routine tasks
that keep the pipeline correct. For how the pipeline works, see the
[README](../README.md).

## Checking on the job

The job runs at 11:00 Africa/Johannesburg (09:00 UTC) and loads yesterday's
US Eastern game day. A normal run takes 3.5 to 4 minutes; `dbt_build` is about
half of that.

    databricks jobs list-runs --job-id <nba_daily job id> --limit 7 --expand-tasks

On this laptop the CLI needs `DATABRICKS_AUTH_STORAGE=plaintext`: the Windows
keyring cannot be reached, so tokens are kept in a file. If the CLI says it
has no cached credentials, sign in again:

    databricks auth login --host https://<workspace>.cloud.databricks.com --profile DEFAULT

## When a run fails

Find the failed task in the run, then use the matching row.

| Task | Error | Cause | Action |
|---|---|---|---|
| `ingest_raw` | `GamesNotFinalError` on both attempts | A game was still not final an hour after the first attempt: a very late finish, a suspended game, or ESPN being slow to mark it final. | Check the game on ESPN. When it is final, repair the run (Databricks: *Repair run*, all tasks) or rerun the date (below). A suspended game finishes on a later date; see [Postponed games](#postponed-and-suspended-games). |
| `ingest_raw` | HTTP 4xx, `ValueError: scoreboard has no 'events' key`, `game ids are not numeric` | ESPN changed or broke its API. | Look at the raw response in the error. A code change in `src/nba/espn.py` or `ingest.py` is needed; nothing was written for the date. |
| `ingest_raw` | HTTP 5xx, connection error, timeout (after 3 attempts) | ESPN was down. | Repair the run later. |
| `load_bronze` | `No complete raw date` | Ingest did not finish writing the date. | Rerun the date from ingest. |
| `build_silver` | Spark / schema error | ESPN changed a field silver reads, or a code bug. | Investigate `src/nba/silver.py`; bronze still holds the raw data, so no data is lost. |
| `dbt_build` | `assert_scheduled_dates_loaded` fails | A date ESPN schedules games on has no final game in silver: an empty scoreboard on a game night, or a date that failed and was never rerun. The failing rows list the dates. | Rerun each listed date (below). If every game that date was genuinely postponed, add it to `schedule_exceptions` in `dbt/nba/dbt_project.yml`. Gold was still built; it is just missing those dates. |
| `dbt_build` | `assert_standings_history_matches_team_form` fails | `mart_standings_history` and `mart_team_form` disagree for some team. The season-level marts count the current season only (issue #29), so a mismatch is a real bug. | Compare the rows the test returns; fix whichever model is wrong. |
| `dbt_build` | any other test fails | Data outside the expected range (a new team, a 4-overtime game, an ESPN data error). dbt skips the models downstream of the failure, so gold keeps yesterday's data for them. | Read the test name, run `dbt test -s <test>` and look at the failing rows (`--store-failures` keeps them in a table). Fix the data or the test's assumption. |
| any | task timed out (30 min) | A hung request or a stuck warehouse. | Repair the run. If it repeats, look at the task's output for where it stopped. |

## Rerunning a date

Every step replaces exactly one date, so a rerun is always safe.

1. In Databricks, open `src/jobs/backfill.py` (from the repository, `main`).
2. Set `start_date` and `end_date` to the date, e.g. `2026-11-23`. Run it.
3. Rebuild gold: run the `nba_daily` job's `dbt_build` task alone (*Repair
   run* on that task), or `dbt build --target prod` from the laptop.

A run of the whole job with parameter `game_date` = the date does the same in
one step.

## Postponed and suspended games

- A **postponed or cancelled** game is skipped by ingest and kept in
  `silver.games` with its status. When it is played on a new date, it appears on
  that date's scoreboard and loads then.
- If **every** game on a scheduled date is postponed, `assert_scheduled_dates_loaded`
  fails for that date. Add the date to `schedule_exceptions` in
  `dbt/nba/dbt_project.yml` and merge.

## Start of a new season

1. Set `SEASON_START` in `src/nba/config.py` and the var `season_start` in
   `dbt/nba/dbt_project.yml` to the first day of the regular season. Clear
   `schedule_exceptions`.
2. Review `seeds/team_conferences.csv` for realignment or new abbreviations.

## Making changes

A push to `main` is a deploy: the job reads `main` at its next run.

1. Work on a branch; CI runs the unit tests, `compileall` and `dbt parse`.
2. Build dbt changes from the laptop with a plain `dbt build`: the default
   `dev` target writes `nba.dev_staging`, `nba.dev_intermediate` and
   `nba.dev_gold` (issue #31), reading the real silver tables. Production gets
   the change when it is merged. `--target prod` writes production directly;
   use it only on purpose, for code already on `main`.
3. Merge when CI is green. After changing the job in the Databricks UI, run
   `python deploy/export_job.py` and commit `deploy/nba_daily.job.json`.
