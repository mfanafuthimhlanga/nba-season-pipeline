select
    t.team_id,
    t.team_abbr,
    t.team_name,
    c.conference,
    c.division
from {{ ref('stg_team_game_stats') }} t
join {{ ref('stg_games') }} g
    on g.game_id = t.game_id
left join {{ ref('team_conferences') }} c
    on c.team_abbr = t.team_abbr
qualify row_number() over (partition by t.team_id order by g.game_date desc) = 1
