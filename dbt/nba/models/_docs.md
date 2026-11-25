{# Shared column definitions, used in the model YAML as "{{ doc('name') }}".
   One definition per metric, so a formula is described in one place. #}

{% docs game_id %}ESPN event id of the game.{% enddocs %}

{% docs team_id %}ESPN team id. Joins to dim_team.team_id.{% enddocs %}

{% docs opponent_team_id %}ESPN team id of the opponent in that game. Joins to dim_team.team_id.{% enddocs %}

{% docs player_id %}ESPN athlete id. Joins to dim_player.player_id.{% enddocs %}

{% docs game_date %}US Eastern game day (a game starting at 22:30 ET on 1 Nov has game_date 1 Nov).{% enddocs %}

{% docs season %}Season by its ending year, as ESPN numbers it: 2027 = the 2026-27 season.{% enddocs %}

{% docs is_regular_season %}True for regular-season games (ESPN season type 2). Preseason and postseason games are false. The season-level marts count regular-season games only.{% enddocs %}

{% docs is_home %}True if the team (or the player's team) was the home side.{% enddocs %}

{% docs won %}True if the team (or the player's team) won the game.{% enddocs %}

{% docs team_abbr %}Team abbreviation as ESPN shows it, e.g. BOS.{% enddocs %}

{% docs conference %}East or West, from the team_conferences seed.{% enddocs %}

{% docs division %}NBA division, from the team_conferences seed.{% enddocs %}

{% docs possessions %}Estimated possessions: FGA + 0.44 x FTA - offensive rebounds + turnovers. Not scaled for overtime.{% enddocs %}

{% docs off_rtg %}Offensive rating: points scored per 100 own possessions.{% enddocs %}

{% docs def_rtg %}Defensive rating: points allowed per 100 opponent possessions.{% enddocs %}

{% docs net_rtg %}Net rating: offensive rating minus defensive rating. Positive = outscored the opponent per 100 possessions.{% enddocs %}

{% docs net_rtg_avg %}Average of the per-game net ratings over the games counted (each game weighs the same, whatever its pace).{% enddocs %}

{% docs pace %}Possessions per 48 minutes: the average of both teams' possessions, scaled down for overtime.{% enddocs %}

{% docs ts_pct %}True shooting %: points / (2 x (FGA + 0.44 x FTA)). Counts threes and free throws; league-wide about 0.575 in 2026-27 so far. Null when there were no shots.{% enddocs %}

{% docs game_score %}John Hollinger's game score: PTS + 0.4 FGM - 0.7 FGA - 0.4 (FTA - FTM) + 0.7 OREB + 0.3 DREB + STL + 0.7 AST + 0.7 BLK - 0.4 PF - TOV. On Hollinger's scale about 10 is an average game and 40+ an outstanding one.{% enddocs %}

{% docs rest_days %}Days since the team's previous game in the same season (1 = played yesterday). Null for its first game of the season.{% enddocs %}

{% docs is_back_to_back %}True when the team also played the day before (rest_days = 1).{% enddocs %}

{% docs win_pct %}Wins / games, rounded to 3 decimals.{% enddocs %}

{% docs conference_rank %}Rank within the conference by win_pct, best = 1. Ties share a rank; no tiebreakers are applied.{% enddocs %}

{% docs last10 %}Over the team's 10 most recent regular-season games (fewer early in the season).{% enddocs %}
