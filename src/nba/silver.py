from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def build_games(scoreboard: DataFrame) -> DataFrame:
    """bronze.scoreboard rows (one per date) -> one row per game."""
    df = _parse(scoreboard, SCOREBOARD_SCHEMA)

    # G1: one row per event
    events = df.select("game_date", F.explode("j.events").alias("e"))

    competitors = F.col("e.competitions")[0]["competitors"]
    home = F.filter(competitors, lambda c: c["homeAway"] == "home")[0]
    away = F.filter(competitors, lambda c: c["homeAway"] == "away")[0]

    # G2: the silver.games columns, in table order
    return events.select(
        F.col("e.id").alias("game_id"),
        "game_date",
        F.to_timestamp("e.date", "yyyy-MM-dd'T'HH:mmX").alias("start_time_utc"),
        F.col("e.season.year").alias("season"),
        F.col("e.season.type").alias("season_type"),
        home["team"]["id"].alias("home_team_id"),
        away["team"]["id"].alias("away_team_id"),
        _to_int(home["score"]).alias("home_score"),
        _to_int(away["score"]).alias("away_score"),
        F.col("e.status.type.name").alias("status"),
        F.col("e.status.type.completed").alias("completed"),
        F.col("e.status.period").alias("periods"),
    )                               