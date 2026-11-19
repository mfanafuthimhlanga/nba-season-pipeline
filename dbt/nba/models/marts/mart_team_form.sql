with games as (
    select
        team_id,
        game_date,
        won,
        net_rtg,
        row_number() over (partition by team_id order by game_date desc) as recency
    from {{ ref('fct_team_game') }}
    where is_regular_season
),

team_totals as (
    select
        team_id,
        count(*)                                               as games,
        sum(case when won then 1 else 0 end)                   as wins,
        avg(net_rtg)                                           as season_net_rtg,
        count(case when recency <= 10 then 1 end)              as last10_games,
        sum(case when recency <= 10 and won then 1 else 0 end) as last10_wins,
        avg(case when recency <= 10 then net_rtg end)          as last10_net_rtg,
        max(game_date)                                         as last_game_date
    from games
    group by team_id
),

final as (
    select
        tt.team_id,
        d.team_abbr,
        d.team_name,
        d.conference,
        d.division,
        tt.games,
        tt.wins,
        tt.games - tt.wins                                   as losses,
        round(tt.wins / tt.games, 3)                         as win_pct,
        round(tt.season_net_rtg, 1)                          as season_net_rtg,
        tt.last10_games,
        tt.last10_wins,
        tt.last10_games - tt.last10_wins                     as last10_losses,
        round(tt.last10_net_rtg, 1)                          as last10_net_rtg,
        round(tt.last10_net_rtg - tt.season_net_rtg, 1)      as form_trend,
        tt.last_game_date
    from team_totals tt
    join {{ ref('dim_team') }} d
        on d.team_id = tt.team_id
)

select
    *,
    rank() over (partition by conference order by win_pct desc) as conference_rank
from final