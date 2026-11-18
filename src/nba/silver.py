def build_games(scoreboard: DataFrame) -> DataFrame:
    df = _parse(scoreboard, SCOREBOARD_SCHEMA)     
    events = df.select("game_date", F.explode("j.events").alias("e"))
    
    return events.select(
        F.col("e.id").alias("game_id"),
        "game_date",
        F.to_timestamp("e.date", "yyyy-MM-dd'T'HH:mmX").alias("start_time_utc"),
        F.col("e.season.year").alias("season"),
        season_type,
        home["team"]["id"].alias("home_team_id"),
        away["team"]["id"].alias("away_team_id"),
        _to_int(home["score"]).alias("home_score"),
        _to_int(away["score"]).alias("away_score"),
        F.col("e.status.type.name").alias("status"),
        F.col("e.status.type.completed").alias("completed"),
        F.col("e.status.period").alias("periods")
    )                                   