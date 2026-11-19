with played as (
    select *
    from {{ ref('fct_player_game') }}
    where is_regular_season
      and not did_not_play
),

player_totals as (
    select
        player_id,
        count(*)                as games_played,
        avg(minutes)            as avg_minutes,
        avg(pts)                as avg_pts,
        stddev(pts)             as stddev_pts,
        avg(game_score)         as avg_game_score,
        stddev(game_score)      as stddev_game_score,
        sum(pts)                as total_pts,
        sum(fga)                as total_fga,
        sum(fta)                as total_fta
    from played
    group by player_id
    having count(*) >= 10
)

select
    pt.player_id,
    dp.player_name,
    dp.position,
    dt.team_abbr                                                       as current_team_abbr,
    pt.games_played,
    round(pt.avg_minutes, 1)                                           as avg_minutes,
    round(pt.avg_pts, 1)                                               as avg_pts,
    round(pt.stddev_pts, 1)                                            as stddev_pts,
    round(pt.stddev_pts / nullif(pt.avg_pts, 0), 2)                    as pts_cv,
    round(pt.avg_game_score, 1)                                        as avg_game_score,
    round(pt.stddev_game_score, 1)                                     as stddev_game_score,
    round(pt.total_pts / nullif(2 * (pt.total_fga + 0.44 * pt.total_fta), 0), 3) as season_ts_pct

from player_totals pt
join {{ ref('dim_player') }} dp
    on dp.player_id = pt.player_id
join {{ ref('dim_team') }} dt
    on dt.team_id = dp.current_team_id