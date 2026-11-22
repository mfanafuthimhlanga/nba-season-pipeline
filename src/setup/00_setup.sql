-- One-time setup for a new workspace. Safe to rerun: everything is IF NOT EXISTS.
-- Run it in a SQL editor or notebook before the first job run.
--
-- Creates what the Python jobs cannot create for themselves:
--   catalog nba, schemas raw / bronze / silver, the landing volume, and the
--   silver tables (MERGE needs an existing target).
-- Bronze tables are created by the first load (saveAsTable). dbt creates the
-- staging, intermediate and gold schemas itself.
--
-- If CREATE CATALOG is refused (Databricks Free Edition), use the existing
-- "workspace" catalog instead and change the names listed in src/nba/config.py.

CREATE CATALOG IF NOT EXISTS nba;
CREATE SCHEMA IF NOT EXISTS nba.raw;
CREATE SCHEMA IF NOT EXISTS nba.bronze;
CREATE SCHEMA IF NOT EXISTS nba.silver;
CREATE VOLUME IF NOT EXISTS nba.raw.landing;

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