with base as (
    select * from {{ ref('int_team_game_with_opponent') }}
),

with_possessions as (
    select
        *,
        fga + 0.44 * fta - oreb + tov                 as possessions,
        opp_fga + 0.44 * opp_fta - opp_oreb + opp_tov as opp_possessions
    from base
),

with_rest as (
    select
        *,
        datediff(
            game_date,
            -- per season: the first game of a season has no previous game, not a 5-month rest
            lag(game_date) over (partition by team_id, season order by game_date)
        ) as rest_days
    from with_possessions
)

select
    -- keys and context
    game_id,
    team_id,
    opponent_team_id,
    game_date,
    season,
    season_type,
    is_regular_season,
    overtime_periods,
    team_abbr,
    opponent_abbr,
    is_home,

    -- result
    pts,
    opp_pts,
    pts > opp_pts as won,

    -- box score
    fgm, fga, fg3m, fg3a, ftm, fta,
    oreb, dreb, reb, ast, stl, blk, tov, pf,

    -- efficiency
    round(possessions, 1)                                        as possessions,
    round(opp_possessions, 1)                                    as opp_possessions,
    round(100.0 * pts / nullif(possessions, 0), 1)               as off_rtg,
    round(100.0 * opp_pts / nullif(opp_possessions, 0), 1)       as def_rtg,
    round(
        100.0 * pts / nullif(possessions, 0)
      - 100.0 * opp_pts / nullif(opp_possessions, 0), 1
    )                                                            as net_rtg,
    round(
        48 * ((possessions + opp_possessions) / 2) / (48 + 5 * overtime_periods), 1
    )                                                            as pace,

    -- schedule
    rest_days,
    coalesce(rest_days = 1, false)                               as is_back_to_back

from with_rest