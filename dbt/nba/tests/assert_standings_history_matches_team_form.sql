-- On the latest date of the latest season, mart_standings_history must agree
-- with mart_team_form: same record, last-10 record, net rating and conference
-- rank for every team. Each row returned is a team where the two disagree.
--
-- mart_team_form aggregates every regular-season game in fct_team_game, of any
-- season (docs/issues.md #29), so this test also fails on the first night of a
-- second season until that mart is limited to the current season.

with latest as (
    select *
    from {{ ref('mart_standings_history') }}
    qualify as_of_date = max(as_of_date) over (partition by season)
        and season = max(season) over ()
)

select
    coalesce(h.team_id, f.team_id) as team_id,
    h.wins           as history_wins,         f.wins            as form_wins,
    h.losses         as history_losses,       f.losses          as form_losses,
    h.last10_wins    as history_last10_wins,  f.last10_wins     as form_last10_wins,
    h.net_rtg        as history_net_rtg,      f.season_net_rtg  as form_net_rtg,
    h.conference_rank as history_rank,        f.conference_rank as form_rank
from latest h
full outer join {{ ref('mart_team_form') }} f
    on f.team_id = h.team_id
where h.team_id is null
   or f.team_id is null
   or h.wins            <> f.wins
   or h.losses          <> f.losses
   or h.last10_wins     <> f.last10_wins
   or h.last10_games    <> f.last10_games
   or h.net_rtg         <> f.season_net_rtg
   or h.conference_rank <> f.conference_rank
