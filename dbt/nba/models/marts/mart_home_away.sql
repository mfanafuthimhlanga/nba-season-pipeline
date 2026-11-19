with games as (
    select *
    from {{ ref('fct_team_game') }}
    where is_regular_season
),

splits as (
    select
        team_id,
        count(*)                                                as games,

        count(case when is_home then 1 end)                     as home_games,
        sum(case when is_home and won then 1 else 0 end)        as home_wins,
        avg(case when is_home then net_rtg end)                 as home_net_rtg,

        count(case when not is_home then 1 end)                 as away_games,
        sum(case when not is_home and won then 1 else 0 end)    as away_wins,
        avg(case when not is_home then net_rtg end)             as away_net_rtg
    from games
    group by team_id
)

select
    s.team_id,
    d.team_abbr,
    d.team_name,
    d.conference,
    s.games,
    s.home_games,
    s.home_wins,
    s.home_games - s.home_wins                                   as home_losses,
    round(s.home_wins / nullif(s.home_games, 0), 3)              as home_win_pct,
    round(s.home_net_rtg, 1)                                     as home_net_rtg,
    s.away_games,
    s.away_wins,
    s.away_games - s.away_wins                                   as away_losses,
    round(s.away_wins / nullif(s.away_games, 0), 3)              as away_win_pct,
    round(s.away_net_rtg, 1)                                     as away_net_rtg,
    round(s.home_net_rtg - s.away_net_rtg, 1)                    as home_court_edge

from splits s
join {{ ref('dim_team') }} d
    on d.team_id = s.team_id