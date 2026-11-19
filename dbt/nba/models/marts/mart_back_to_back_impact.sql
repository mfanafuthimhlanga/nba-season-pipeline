with games as (
    select *
    from {{ ref('fct_team_game') }}
    where is_regular_season
),

splits as (
    select
        team_id,
        count(*)                                                         as games,

        count(case when is_back_to_back then 1 end)                      as b2b_games,
        sum(case when is_back_to_back and won then 1 else 0 end)         as b2b_wins,
        avg(case when is_back_to_back then net_rtg end)                  as b2b_net_rtg,
        sum(case when is_back_to_back then fgm end)                      as b2b_fgm,
        sum(case when is_back_to_back then fga end)                      as b2b_fga,

        count(case when not is_back_to_back then 1 end)                  as rested_games,
        sum(case when not is_back_to_back and won then 1 else 0 end)     as rested_wins,
        avg(case when not is_back_to_back then net_rtg end)              as rested_net_rtg,
        sum(case when not is_back_to_back then fgm end)                  as rested_fgm,
        sum(case when not is_back_to_back then fga end)                  as rested_fga
    from games
    group by team_id
)

select
    s.team_id,
    d.team_abbr,
    d.team_name,
    d.conference,
    s.games,

    s.b2b_games,
    s.b2b_wins,
    round(s.b2b_wins / nullif(s.b2b_games, 0), 3)                      as b2b_win_pct,
    round(s.b2b_net_rtg, 1)                                            as b2b_net_rtg,
    round(s.b2b_fgm / nullif(s.b2b_fga, 0), 3)                         as b2b_fg_pct,

    s.rested_games,
    s.rested_wins,
    round(s.rested_wins / nullif(s.rested_games, 0), 3)                as rested_win_pct,
    round(s.rested_net_rtg, 1)                                         as rested_net_rtg,
    round(s.rested_fgm / nullif(s.rested_fga, 0), 3)                   as rested_fg_pct,

    round(s.b2b_net_rtg - s.rested_net_rtg, 1)                         as b2b_net_rtg_diff,
    round(s.b2b_fgm / nullif(s.b2b_fga, 0)
        - s.rested_fgm / nullif(s.rested_fga, 0), 3)                   as b2b_fg_pct_diff

from splits s
join {{ ref('dim_team') }} d
    on d.team_id = s.team_id