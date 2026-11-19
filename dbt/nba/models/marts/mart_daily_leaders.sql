select
    p.game_date,
    rank() over (partition by p.game_date order by p.game_score desc) as daily_rank,
    p.game_id,
    p.player_id,
    p.player_name,
    t.team_abbr,
    o.team_abbr as opponent_abbr,
    t.conference,
    p.is_home,
    p.won,
    p.is_regular_season,
    p.minutes,
    p.pts,
    p.reb,
    p.ast,
    p.stl,
    p.blk,
    p.ts_pct,
    p.game_score

from {{ ref('fct_player_game') }} p
join {{ ref('dim_team') }} t
    on t.team_id = p.team_id
join {{ ref('dim_team') }} o
    on o.team_id = p.opponent_team_id
where not p.did_not_play
qualify daily_rank <= 10
