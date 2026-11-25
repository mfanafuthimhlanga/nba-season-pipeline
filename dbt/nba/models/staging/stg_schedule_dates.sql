-- The dates ESPN lists as game days, from the calendar in the latest scoreboard.
--
-- Every scoreboard response carries the whole season's calendar
-- (leagues[0].calendar): one entry per date with games, preseason included,
-- e.g. "2026-10-21T07:00Z". 07:00 UTC is still the same day in New York, so the
-- first 10 characters are the US Eastern game day. Dates without games
-- (Election Day, Thanksgiving, Christmas Eve, the All-Star break) are absent.
-- ESPN updates the calendar as dates are added (NBA Cup knockout games), so the
-- most recently ingested scoreboard is used.

with latest_scoreboard as (
    select payload
    from {{ source('bronze', 'scoreboard') }}
    qualify row_number() over (order by ingested_at desc, game_date desc) = 1
),

calendar as (
    select
        explode(
            from_json(get_json_object(payload, '$.leagues[0].calendar'), 'array<string>')
        ) as calendar_entry
    from latest_scoreboard
)

select distinct
    to_date(left(calendar_entry, 10)) as game_date
from calendar
