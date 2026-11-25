-- Every date ESPN schedules games on, from the season start up to yesterday
-- (US Eastern), must have at least one final game in silver.
--
-- Catches what the job alone cannot see:
--   * an empty scoreboard on a game night (ESPN returned no events: the date
--     loads as "no games" and every task succeeds)
--   * a date that was never loaded (a failed run that nobody reran)
-- Each row returned is a missing date. Fix: rerun that date (src/jobs/backfill.py
-- with start_date = end_date = the date), then dbt build. See docs/runbook.md.
--
-- The test reads silver directly and refs only stg_schedule_dates, which nothing
-- builds on, so a failure ends the run red without skipping any gold model.
--
-- A date that genuinely had no final game (every game postponed) is listed in
-- the var `schedule_exceptions` in dbt_project.yml.

{% set exceptions = var('schedule_exceptions', []) %}

select s.game_date as missing_game_date
from {{ ref('stg_schedule_dates') }} s
where s.game_date >= date'{{ var("season_start") }}'
  and s.game_date < to_date(from_utc_timestamp(current_timestamp(), 'America/New_York'))
  {% if exceptions %}
  and s.game_date not in ({% for d in exceptions %}date'{{ d }}'{% if not loop.last %}, {% endif %}{% endfor %})
  {% endif %}
  and not exists (
      select 1
      from {{ source('silver', 'games') }} g
      where g.game_date = s.game_date
        and g.status = 'STATUS_FINAL'
  )
