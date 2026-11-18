-- declare silver tables so merge has a target

CREATE TABLE IF NOT EXISTS nba.silver.games ( 
        game_id STRING, 
        game_date DATE, 
        start_time_utc TIMESTAMP, 
        season INT, 
        season_type INT, 
        home_team_id STRING, 
        away_team_id STRING, 
        home_score INT, 
        away_score INT, 
        status STRING, 
        completed BOOLEAN, 
        periods INT 
)USING DELTA;

CREATE TABLE IF NOT EXISTS nba.silver.team_game_stats (
        game_id STRING, 
        team_id STRING, 
        team_abbr STRING, 
        team_name STRING, 
        is_home BOOLEAN, 
        fgm INT, 
        fga INT, 
        fg3m INT, 
        fg3a INT, 
        ftm INT, 
        fta INT, 
        oreb INT, 
        dreb INT, 
        reb INT, 
        ast INT, 
        stl INT, 
        blk INT, 
        tov INT, 
        pf INT, 
        fast_break_pts INT, 
        paint_pts INT, 
        pts_off_tov INT
)USING DELTA;

CREATE TABLE IF NOT EXISTS nba.silver.player_game_stats (
        game_id STRING, 
        team_id STRING, 
        player_id STRING, 
        player_name STRING, 
        position STRING, 
        starter BOOLEAN, 
        did_not_play BOOLEAN, 
        ejected BOOLEAN, 
        minutes INT, 
        pts INT, 
        fgm INT, 
        fga INT, 
        fg3m INT, 
        fg3a INT, 
        ftm INT, 
        fta INT, 
        reb INT, 
        oreb INT, 
        dreb INT, 
        ast INT, 
        tov INT, 
        stl INT, 
        blk INT, 
        pf INT, 
        plus_minus INT
)USING DELTA;