# Issues register

Issues 1–28: a review of the whole repository, its dbt logs and the live
`nba_daily` job on 2026-11-22, fixed on branch `fix/audit-2026-11-22`.
Issues 29–38: a review of data completeness, dashboard readiness and the
documentation on 2026-11-24, on branch `feat/freshness-standings-history`
([below](#2026-11-24-data-completeness-and-documentation)).

Status: **fixed** (code changed and verified) · **fixed in workspace** (needs
a change to the Databricks job, not this repo) · **accepted** (reviewed, left
as is on purpose, reason given) · **no action** (not present) · **open** (not
fixed yet).

## How the fixes were verified

- `python -m pytest`: 13 unit tests for config, the ESPN client and ingest.
- `dbt parse` with a placeholder profile: the project compiles, 89 tests, and
  the 5 `MissingArgumentsPropertyInGenericTestDeprecation` warnings are gone.
- Changed dbt SQL run read-only against the live gold data (`dbt show`):
  the new possessions test has 0 failures over 482 team-games, and partitioning
  rest days by season changes 0 rows.
- The Spark changes ran in two temporary one-off Databricks runs (serverless,
  ANSI mode on), against copies of the tables in a scratch schema that was
  dropped afterwards. Production tables were only read:
  - silver rebuilt from all of bronze with the new code is identical, row for
    row, to the current silver tables (241 / 482 / 6,396 rows, 0 differences)
  - rerunning a date changes nothing
  - a planted stale game on that date, with its 2 team and 25 player rows, is
    deleted; other dates are untouched
  - a final game is not overwritten by a non-final listing of the same id
  - `bronze.run` reloads 2026-11-21 identically and refuses a date with no
    complete landing folder
  - the `game_date` task value set by `ingest_raw` reaches the next task

## Pipeline code

| # | Issue | Where | Status | Resolution |
|---|---|---|---|---|
| 1 | A backfill with failed dates still finished green, so a job's failure e-mail would not fire. | `src/jobs/backfill.py` | fixed | After listing failures the notebook raises `RuntimeError` naming the failed dates. |
| 2 | Backfill hard-coded `2026-10-20` instead of `config.SEASON_START`. | `src/jobs/backfill.py` | fixed | Blank `start_date` now means `config.SEASON_START`. |
| 3 | HTTP 429 (rate limited) failed at once; only 5xx was retried. | `src/nba/espn.py` | fixed | 429 is retried like 5xx. The wait is `Retry-After`, but never less than the normal backoff nor more than `MAX_RETRY_AFTER_S` = 60 s. |
| 4 | A crash part-way through writing a date left a half-written landing folder that bronze would load, because bronze only checked that the folder existed. | `src/nba/ingest.py`, `src/nba/bronze.py` | fixed | Ingest writes the summaries first and `scoreboard.json` last, so that file marks a complete date. Bronze requires the file, not the folder. |
| 5 | Bronze took `game_id` from the file name with `regexp_extract`, which returns `''` silently if a name does not match. | `src/nba/bronze.py`, `src/nba/ingest.py` | fixed | Ingest refuses non-numeric game ids. Bronze raises if any summary file yields an empty id. |
| 6 | Silver's MERGE never deleted: a game that ESPN stopped listing for a date, and its stats rows, stayed in silver for good, while bronze did clear them. | `src/nba/silver.py` | fixed | `whenNotMatchedBySourceDelete`, limited to the date being loaded: `games` by `game_date`, the stats tables by the game ids that date had before or after the merge. |
| 7 | A rerun of an old date could overwrite a final game with a stale listing (for example a game first postponed, then played on another date). | `src/nba/silver.py` | fixed | Games update only when the incoming row is final or the stored one is not: `s.completed OR NOT coalesce(t.completed, false)`. |
| 8 | `[0]` on arrays (`competitions`, the home/away filter, `statistics`) and `split("-")[1]` raise `INVALID_ARRAY_INDEX` under ANSI mode if ESPN ever sends an empty list or an empty stat. | `src/nba/silver.py` | fixed | `F.get(arr, i)` returns null instead; the dbt `not_null` tests then fail with a clear message. Output on the season so far is unchanged. |
| 9 | Each task resolved "yesterday" on its own, so a run crossing midnight in New York could load different dates in different tasks. | `src/jobs/0*.py` | fixed | `ingest_raw` publishes the resolved date as task value `game_date`; bronze and silver use it when no date is given. |
| 10 | `dropDuplicates(keys)` before MERGE keeps an arbitrary row per key. | `src/nba/silver.py` | accepted | Within one date the rows come from a single ESPN response; a repeated key would be ESPN listing the same thing twice, so either copy is the same data. Commented in the code. |
| 11 | `silver.run` counts its three DataFrames after the MERGE, which recomputes the parse. | `src/nba/silver.py` | accepted | About a second per date at this size, and serverless compute does not support `cache()`. The counts feed the backfill summary. |
| 12 | Odd indentation in `bronze._read_folder`. | `src/nba/bronze.py` | fixed | Reformatted. |

## Setup and configuration

| # | Issue | Where | Status | Resolution |
|---|---|---|---|---|
| 13 | `config.py` said that changing the catalog needs nothing else, but `00_setup.sql`, the dbt sources and the dbt profile also hard-code `nba`. | `src/nba/config.py` | fixed | The comment now lists the three other places. |
| 14 | Nothing in the repo created the catalog, the schemas or the landing volume; `00_setup.sql` only created the silver tables. | `src/setup/00_setup.sql` | fixed | Creates catalog `nba`, schemas `raw`, `bronze`, `silver` and volume `raw.landing`, all `IF NOT EXISTS`. |
| 15 | `requirements.txt` was empty, so the environment could not be rebuilt from the repo (it had to be recovered from an old venv when the folder moved). | `requirements.txt` | fixed (partly) | The six direct dependencies are pinned: dbt-core 1.12.6, dbt-databricks 1.13.0, requests, databricks-sdk, PyYAML, pytest. Their own dependencies still float; a lock file (`uv pip compile`) would pin those too, if a rebuild ever drifts. |
| 16 | The job definition (schedule, task chain, retries) lived only in the Databricks workspace. | `deploy/` | fixed | `deploy/export_job.py` writes `deploy/nba_daily.job.json`, with e-mails and the warehouse id replaced by placeholders (the repo is public). |
| 17 | The job's dbt environment installs `dbt-databricks>=1.0.0,<2.0.0`, unpinned, while the laptop runs 1.13.0: production can change version without a commit. | job `nba_daily` | fixed in workspace | Pinned `dbt-databricks==1.13.0` in the `dbt-default` environment on 2026-11-22; re-exported. |
| 18 | No timeouts on the job or its tasks (`timeout_seconds: 0`). A hung task would hold the run, and with `max_concurrent_runs: 1` the next day's run would queue behind it. | job `nba_daily` | fixed in workspace | Applied 2026-11-22: each task times out after 1,800 s (a normal task takes 16-121 s) and the job after 7,200 s, which leaves room for the ingest task's one-hour retry wait. |
| 19 | No CI. | `.github/workflows/ci.yml` | fixed | On every push and pull request: unit tests, `compileall`, `dbt deps` + `dbt parse` with a placeholder profile, and a check that at least 89 tests are defined. CI reports but cannot stop the job reading main: work on a branch and merge when green. |
| 20 | The top-level README was empty and `dbt/nba/README.md` was the dbt starter text. | `README.md`, `dbt/nba/README.md` | fixed | Both written: architecture, the job, setup, local development, backfill. |
| 21 | Moving the repository folder broke the local `.venv` (pip's `.exe` launchers and the activate scripts store absolute paths). | local only | fixed | Venv repaired after the 2026-11-22 move; the README now says to recreate `.venv` after a move. |

## dbt project

| # | Issue | Where | Status | Resolution |
|---|---|---|---|---|
| 22 | `stg_games.sql` and `stg_team_game_stats.sql` ended with `;`. It works for views today, but any tool that wraps a model's SQL as a subquery (for example `dbt show --select` or an ephemeral materialisation) fails on the stray `;`, and the third staging model had none. | `models/staging/` | fixed | Semicolons removed. |
| 23 | Staging and intermediate tests used the old argument style; dbt logged `MissingArgumentsPropertyInGenericTestDeprecation` 5 times. | `_staging.yml`, `_intermediate.yml` | fixed | Arguments nested under `arguments:`, as in `_marts.yml`. `dbt parse` is now warning-free. |
| 24 | `fct_team_game.possessions` had to be 70–130, but possessions are not scaled for overtime, so a long multi-overtime game could fail the build. | `_marts.yml` | fixed | The test now checks possessions per 48 minutes: `possessions * 48 / (48 + 5 * overtime_periods) between 70 and 130`. Still 89 tests. |
| 25 | Rest days were computed across seasons (`lag` over all of a team's games). | `fct_team_game.sql` | fixed | `partition by team_id, season`. No change to current data (one season so far). |
| 26 | `mart_player_consistency` lists a traded player's whole season under his current team. | `_marts.yml` | accepted | By design (the column is `current_team_abbr`); now stated in the model's description. |
| 27 | A run on 18 Nov created views in `nba.gold_staging` before the schema macro existed; dbt never drops what it stops building. | warehouse | no action | Checked `nba.information_schema` on 2026-11-22: the schema no longer exists. |
| 28 | `dbt_project.yml` still carried the starter comments about an `example/` folder. | `dbt_project.yml` | fixed | Replaced with a note on the schema naming. |

## 2026-11-24: data completeness and documentation

State at review: 6 successful `nba_daily` runs in a row (19–24 Nov, about 3.5
minutes each, no retries needed). Bronze shows the 28-date backfill on 18 Nov,
then exactly one new date per daily run. 34 game dates and 258 games loaded,
all final; the one calendar gap, 3 Nov, had no games.

### Verification

- `dbt parse` with the CI profile: 15 models, 108 tests, no warnings.
- `dbt seed` + `dbt build` of the branch on the live warehouse, written to
  temporary `nba.zz_verify_*` schemas (a copy of the project with a prefixing
  `generate_schema_name`), reading production silver and bronze only:
  124 of 124 nodes passed. The schemas were dropped afterwards.
- `assert_scheduled_dates_loaded` against silver with 22 and 23 Nov removed and
  22 Nov listed in `schedule_exceptions`: returned exactly 2026-11-23.
  `dbt ls -s stg_schedule_dates+` lists no other model, so a failure skips no
  gold model.
- ESPN's calendar (174 dates) against silver: every calendar date from 20 Oct
  to 23 Nov is loaded and every loaded date is in the calendar.
- `persist_docs`: all 179 gold columns and all 10 gold tables carry comments
  in `information_schema`.

| # | Issue | Where | Status | Resolution |
|---|---|---|---|---|
| 29 | The season-level marts (`mart_team_form`, `mart_home_away`, `mart_back_to_back_impact`, `mart_player_consistency`) aggregate every regular-season game in `fct_team_game` / `fct_player_game`, of any season. With one season loaded the numbers are right; on the first night of 2027-28 they would mix two seasons. | `models/marts/` | open | Filter each to the latest season before October 2027. `assert_standings_history_matches_team_form` fails when the second season starts, so this cannot be missed. Listed under "Start of a new season" in `docs/runbook.md`. |
| 30 | An empty ESPN scoreboard on a game night loads as "no games" and every task succeeds; a date whose run failed and was never rerun also leaves the job green from the next day on. Nothing compared what was loaded with what was scheduled. | `dbt/nba` | fixed | `stg_schedule_dates` reads ESPN's season calendar from the latest scoreboard; `tests/assert_scheduled_dates_loaded.sql` fails for any scheduled date since `season_start` with no final game in silver, and `dbt_utils.at_least_one` fails if the calendar is ever empty. Exceptions go in the var `schedule_exceptions`. |
| 31 | The dbt profile has one target and schemas are used as named, so a `dbt build` from the laptop writes the production `nba.gold`, `nba.staging` and `nba.intermediate`. There is no dev environment. | `macros/generate_schema_name.sql`, `~/.dbt/profiles.yml` | open | Documented in `dbt/nba/README.md` and `docs/runbook.md`, with the prefixed-copy method used to verify this branch. A `dev` target that prefixes schemas would remove the risk; it touches the macro the job relies on, so it needs its own change. |
| 32 | The marts only held the current state: no way to chart standings or form over the season. | `models/marts/` | fixed | `mart_standings_history`: one row per team per regular-season game date, rebuilt in full from `fct_team_game`, so backfilled and rerun dates are always included. Its latest date is tested against `mart_team_form`. |
| 33 | No column in any model had a description; a dashboard author had to read SQL to learn what `net_rtg`, `form_trend` or `pts_cv` mean, and Unity Catalog showed nothing. | `_marts.yml` | fixed | Every gold column described; shared metric definitions as doc blocks in `models/_docs.md`; `persist_docs` writes them to Unity Catalog. |
| 34 | Sources and the seed had no descriptions, and the sources file was `models/schema.yml`, unlike the `_<folder>.yml` convention of the other YAML files. | `models/`, `seeds/` | fixed | Renamed to `models/_sources.yml` with descriptions; `seeds/_seeds.yml` added with tests (`team_abbr` unique, not null). |
| 35 | Model and test counts were written in the top README, the dbt README and CI, and go stale whenever a model is added. | docs, CI | fixed | Exact counts only in `dbt/nba/README.md`; the top README no longer has them; CI's minimum is now 108. |
| 36 | No runbook: what to do for each kind of failure lived only in people's heads and in this register. | `docs/` | fixed | `docs/runbook.md`: per-task failure table, rerunning a date, postponed games, start-of-season steps, how to try a dbt change safely. |
| 37 | The season start is written in two places, `SEASON_START` in `src/nba/config.py` and the dbt var `season_start`, because dbt cannot read the Python config. | `config.py`, `dbt_project.yml` | accepted | Each comment points to the other, and both are in the runbook's start-of-season steps. |
| 38 | If the job does not run at all (schedule paused, workspace outage), no task fails and no e-mail is sent; the schedule test runs inside the job, so it cannot catch this. | job `nba_daily` | open | Needs a check outside the job: a Databricks SQL alert on the hours since `max(ingested_at)` in `nba.bronze.scoreboard`, which gains a row on every run, games or not (`max(game_date)` in silver stalls over the All-Star break). Checked at 12:00 UTC, a run that happened is about 3 hours old and a missed one about 27, so alert above 12 hours. A workspace-wide outage would silence the alert too; only a check outside Databricks covers that. Noted in the README's data quality section. |

## Incidents (already resolved before this review)

| Date | What happened | Fix |
|---|---|---|
| 2026-11-19 17:46 UTC | First manual run of `nba_daily` failed at `build_silver`: "Unable to access the notebook src/jobs/03_build_silver". The file on `main` was empty, so it was not a notebook; `dbt_build` was skipped. | Commit `058911a` added the notebook at 17:53 UTC; the rerun at 17:55 UTC succeeded. CI's `compileall` would not catch an empty file; the job's first run did. |
| 2026-11-19 | Four dbt failures while building gold: a missing colon in `version: 2`, tests run before their model existed, a YAML error in `_marts.yml`, and `fct_team_game` needing a column (`overtime_periods`) the intermediate model did not carry. | Fixed in commits `ceab77b`, `913ef97`; `dbt build` (models before their tests) is the default command. |
