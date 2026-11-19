select
    -- keys
    p.game_id,
    p.player_id,
    p.team_id,
    f.opponent_team_id,

    -- game context (from the player's own team row)
    f.game_date,
    f.season,
    f.is_regular_season,
    f.is_home,
    f.won,
    f.is_back_to_back,

    -- who
    p.player_name,
    p.position,
    p.starter,
    p.did_not_play,
    p.ejected,

    -- box score (null for DNP rows)
    p.minutes,
    p.pts,
    p.fgm,
    p.fga,
    p.fg3m,
    p.fg3a,
    p.ftm,
    p.fta,
    p.reb,
    p.oreb,
    p.dreb,
    p.ast,
    p.tov,
    p.stl,
    p.blk,
    p.pf,
    p.plus_minus,

    -- derived
    round(p.pts / nullif(2 * (p.fga + 0.44 * p.fta), 0), 3) as ts_pct,
    round(
        p.pts
      + 0.4 * p.fgm
      - 0.7 * p.fga
      - 0.4 * (p.fta - p.ftm)
      + 0.7 * p.oreb
      + 0.3 * p.dreb
      + p.stl
      + 0.7 * p.ast
      + 0.7 * p.blk
      - 0.4 * p.pf
      - p.tov, 1
    ) as game_score

from {{ ref('stg_player_game_stats') }} p
join {{ ref('fct_team_game') }} f
    on  f.game_id = p.game_id
    and f.team_id = p.team_id