-- Regular-season standings as they stood after each game date: one row per team
-- per date on which any regular-season game was played.
--
-- Rebuilt in full from fct_team_game on every run, so it covers the whole season
-- (backfilled dates included) and a rerun of an old date corrects every later
-- row. A team that did not play on a date carries its previous record forward.
-- The latest date matches mart_team_form (tests/assert_standings_history_matches_team_form.sql).

with team_games as (
    select
        season,
        team_id,
        game_date,
        won,
        net_rtg
    from {{ ref('fct_team_game') }}
    where is_regular_season
),

-- Running record per team, one row per game it played
team_running as (
    select
        season,
        team_id,
        game_date,
        count(*) over to_date                                 as games,
        sum(case when won then 1 else 0 end) over to_date     as wins,
        avg(net_rtg) over to_date                             as net_rtg,
        count(*) over last10                                  as last10_games,
        sum(case when won then 1 else 0 end) over last10      as last10_wins
    from team_games
    window
        to_date as (partition by season, team_id order by game_date
                    rows between unbounded preceding and current row),
        last10  as (partition by season, team_id order by game_date
                    rows between 9 preceding and current row)
),

-- Every team on every date that had games
spine as (
    select
        d.season,
        d.as_of_date,
        t.team_id,
        t.team_abbr,
        t.team_name,
        t.conference,
        t.division
    from (select distinct season, game_date as as_of_date from team_games) d
    cross join {{ ref('dim_team') }} t
),

-- On dates a team did not play, carry its last record forward
carried as (
    select
        s.*,
        r.game_date is not null                     as played_on_date,
        last_value(r.games, true)        over carry as games,
        last_value(r.wins, true)         over carry as wins,
        last_value(r.net_rtg, true)      over carry as net_rtg,
        last_value(r.last10_games, true) over carry as last10_games,
        last_value(r.last10_wins, true)  over carry as last10_wins
    from spine s
    left join team_running r
        on  r.season    = s.season
        and r.team_id   = s.team_id
        and r.game_date = s.as_of_date
    window carry as (partition by s.season, s.team_id order by s.as_of_date
                     rows between unbounded preceding and current row)
),

record as (
    select
        season,
        as_of_date,
        team_id,
        team_abbr,
        team_name,
        conference,
        division,
        played_on_date,
        coalesce(games, 0)                                   as games,
        coalesce(wins, 0)                                    as wins,
        coalesce(games, 0) - coalesce(wins, 0)               as losses,
        -- same rounding as mart_team_form, so ranks agree
        round(wins / nullif(games, 0), 3)                    as win_pct,
        round(net_rtg, 1)                                    as net_rtg,
        coalesce(last10_games, 0)                            as last10_games,
        coalesce(last10_wins, 0)                             as last10_wins,
        coalesce(last10_games, 0) - coalesce(last10_wins, 0) as last10_losses
    from carried
)

select
    *,
    -- nulls (no games yet) rank last
    rank() over (partition by season, as_of_date, conference order by win_pct desc) as conference_rank,
    -- behind the team in the conference with the best wins minus losses
    cast(
        (max(wins - losses) over (partition by season, as_of_date, conference)
            - (wins - losses)) / 2.0
        as decimal(4, 1))                                                            as games_behind
from record
