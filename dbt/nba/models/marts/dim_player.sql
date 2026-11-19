select
    p.player_id,
    p.player_name,
    p.position,
    p.team_id   as current_team_id,
    g.game_date as last_game_date
from {{ ref('stg_player_game_stats') }} p
join {{ ref('stg_games') }} g
    on g.game_id = p.game_id
qualify row_number() over (partition by p.player_id order by g.game_date desc) = 1