select

    t.game_id,
    t.team_id,
    o.team_id as opponent_team_id,
    g.game_date,
    g.season,
    g.season_type,
    g.is_regular_season,
    g.overtime_periods,
    t.team_abbr,
    o.team_abbr as opponent_abbr,
    t.is_home,
    case when t.is_home then g.home_score else g.away_score end as pts,
    case when o.is_home then g.home_score else g.away_score end as opp_pts,
    t.fgm,
    t.fga,
    t.fg3m,
    t.fg3a,
    t.ftm,
    t.fta,
    t.oreb,
    t.dreb,
    t.reb,
    t.ast,
    t.stl,
    t.blk,
    t.tov,
    t.pf,
    o.fgm as opp_fgm,
    o.fga as opp_fga,
    o.fg3m as opp_fg3m,
    o.fg3a as opp_fg3a,
    o.ftm as opp_ftm,
    o.fta as opp_fta,
    o.oreb as opp_oreb,
    o.dreb as opp_dreb,
    o.reb as opp_reb,
    o.ast as opp_ast,
    o.stl as opp_stl,
    o.blk as opp_blk,
    o.tov as opp_tov,
    o.pf as opp_pf

from {{ ref('stg_team_game_stats') }} t      
join {{ ref('stg_team_game_stats') }} o      
    on t.game_id = o.game_id                  
    and t.team_id <> o.team_id                 
join {{ ref('stg_games') }} g
    on t.game_id = g.game_id
    where g.completed
