select
    game_id,
    game_date,
    start_time_utc,

    season,
    concat(
        cast(season - 1 as string),
        '-',
        right(cast(season as string), 2)
    ) as season_label,

    season_type,
    case season_type
        when 1 then 'Preseason'
        when 2 then 'Regular season'
        when 3 then 'Postseason'
        else 'Other'
    end as season_type_name,
    season_type = 2 as is_regular_season,

    home_team_id,
    away_team_id,
    home_score,
    away_score,
    status,
    completed,

    periods,
    case
        when completed then greatest(periods - 4, 0)
    end as overtime_periods

from {{ source('silver', 'games') }}
