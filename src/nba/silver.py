"""Silver: bronze JSON payloads -> typed, flat tables, MERGEd on their keys.

Tables:
  silver.games              key game_id              source: bronze.scoreboard
  silver.team_game_stats    key game_id, team_id     source: bronze.summary boxscore.teams
  silver.player_game_stats  key game_id, player_id   source: bronze.summary boxscore.players
"""

from datetime import date

from delta.tables import DeltaTable
from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from nba import config

GAMES_TABLE = f"{config.SILVER}.games"
TEAM_TABLE = f"{config.SILVER}.team_game_stats"
PLAYER_TABLE = f"{config.SILVER}.player_game_stats"


# =============================================================================
# Schemas: ONLY the fields we use. from_json ignores everything else, so new
# ESPN fields never break silver. Scalars we cast later are read as strings.
# =============================================================================

TEAM_REF = StructType([
    StructField("id", StringType()),
    StructField("abbreviation", StringType()),
    StructField("displayName", StringType()),
])

SCOREBOARD_SCHEMA = StructType([
    StructField("events", ArrayType(StructType([
        StructField("id", StringType()),
        StructField("date", StringType()),
        StructField("season", StructType([
            StructField("year", IntegerType()),
            StructField("type", IntegerType()),
        ])),
        StructField("status", StructType([
            StructField("period", IntegerType()),
            StructField("type", StructType([
                StructField("name", StringType()),
                StructField("completed", BooleanType()),
            ])),
        ])),
        StructField("competitions", ArrayType(StructType([
            StructField("competitors", ArrayType(StructType([
                StructField("homeAway", StringType()),
                StructField("score", StringType()),
                StructField("team", TEAM_REF),
            ]))),
        ]))),
    ]))),
])

ATHLETE = StructType([
    StructField("athlete", StructType([
        StructField("id", StringType()),
        StructField("displayName", StringType()),
        StructField("position", StructType([StructField("abbreviation", StringType())])),
    ])),
    StructField("starter", BooleanType()),
    StructField("didNotPlay", BooleanType()),
    StructField("ejected", BooleanType()),
    StructField("stats", ArrayType(StringType())),
])

SUMMARY_SCHEMA = StructType([
    StructField("boxscore", StructType([
        StructField("players", ArrayType(StructType([
            StructField("team", TEAM_REF),
            StructField("statistics", ArrayType(StructType([
                StructField("keys", ArrayType(StringType())),
                StructField("athletes", ArrayType(ATHLETE)),
            ]))),
        ]))),
        StructField("teams", ArrayType(StructType([
            StructField("team", TEAM_REF),
            StructField("homeAway", StringType()),
            StructField("statistics", ArrayType(StructType([
                StructField("name", StringType()),
                StructField("displayValue", StringType()),
            ]))),
        ]))),
    ])),
])


# =============================================================================
# Helpers
# =============================================================================

def _spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()


def _parse(df: DataFrame, schema: StructType) -> DataFrame:
    """Add column `j`: the payload string parsed into a struct."""
    return df.withColumn("j", F.from_json("payload", schema))


def _to_int(c: Column) -> Column:
    """'34' -> 34, '+5' -> 5, '-7' -> -7, '' / '--' / null -> null.

    A plain .cast("int") raises on bad input when ANSI mode is on (the default
    on serverless). Checking the pattern first makes bad values null instead.
    """
    return F.when(c.rlike(r"^[+-]?\d+$"), c.cast("int"))


def _made(c: Column) -> Column:
    """'12-19' -> 12"""
    return _to_int(F.split(c, "-")[0])


def _att(c: Column) -> Column:
    """'12-19' -> 19"""
    return _to_int(F.split(c, "-")[1])


FG = "fieldGoalsMade-fieldGoalsAttempted"
FG3 = "threePointFieldGoalsMade-threePointFieldGoalsAttempted"
FT = "freeThrowsMade-freeThrowsAttempted"


# =============================================================================
# Builders
# =============================================================================

def build_games(scoreboard: DataFrame) -> DataFrame:
    """bronze.scoreboard rows (one per date) -> one row per game."""
    df = _parse(scoreboard, SCOREBOARD_SCHEMA)

    # One row per event. game_date is copied down from bronze.
    events = df.select("game_date", F.explode("j.events").alias("e"))

    # Home and away competitor structs, picked by a higher-order filter.
    competitors = F.col("e.competitions")[0]["competitors"]
    home = F.filter(competitors, lambda c: c["homeAway"] == "home")[0]
    away = F.filter(competitors, lambda c: c["homeAway"] == "away")[0]

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


def build_team_stats(summary: DataFrame) -> DataFrame:
    """bronze.summary rows (one per game) -> one row per team per game."""
    df = _parse(summary, SUMMARY_SCHEMA)

    # One row per team (2 per game). game_id is copied down.
    teams = df.select("game_id", F.explode("j.boxscore.teams").alias("t"))

    # Turn the list of {name, displayValue} into one map: name -> value.
    m = F.map_from_entries(
        F.transform("t.statistics", lambda s: F.struct(s["name"], s["displayValue"]))
    )

    return teams.select(
        "game_id",
        F.col("t.team.id").alias("team_id"),
        F.col("t.team.abbreviation").alias("team_abbr"),
        F.col("t.team.displayName").alias("team_name"),
        (F.col("t.homeAway") == "home").alias("is_home"),
        _made(m[FG]).alias("fgm"),
        _att(m[FG]).alias("fga"),
        _made(m[FG3]).alias("fg3m"),
        _att(m[FG3]).alias("fg3a"),
        _made(m[FT]).alias("ftm"),
        _att(m[FT]).alias("fta"),
        _to_int(m["offensiveRebounds"]).alias("oreb"),
        _to_int(m["defensiveRebounds"]).alias("dreb"),
        _to_int(m["totalRebounds"]).alias("reb"),
        _to_int(m["assists"]).alias("ast"),
        _to_int(m["steals"]).alias("stl"),
        _to_int(m["blocks"]).alias("blk"),
        _to_int(m["totalTurnovers"]).alias("tov"),
        _to_int(m["fouls"]).alias("pf"),
        _to_int(m["fastBreakPoints"]).alias("fast_break_pts"),
        _to_int(m["pointsInPaint"]).alias("paint_pts"),
        _to_int(m["turnoverPoints"]).alias("pts_off_tov"),
    )


def build_player_stats(summary: DataFrame) -> DataFrame:
    """bronze.summary rows (one per game) -> one row per player per game."""
    df = _parse(summary, SUMMARY_SCHEMA)

    # One row per team block (2 per game). Keep the team id and the first
    # statistics block, which holds `keys` and `athletes`.
    blocks = (
        df.select("game_id", F.explode("j.boxscore.players").alias("p"))
          .select(
              "game_id",
              F.col("p.team.id").alias("team_id"),
              F.col("p.statistics")[0].alias("b"),
          )
    )

    # One row per athlete. keys is copied down so every player can map stats.
    athletes = blocks.select(
        "game_id",
        "team_id",
        F.col("b.keys").alias("keys"),
        F.explode("b.athletes").alias("a"),
    )

    # keys + stats -> one map per player. DNP rows have empty stats, and
    # map_from_arrays fails on arrays of different length, so guard it.
    m = F.when(F.size("a.stats") > 0, F.map_from_arrays("keys", "a.stats"))

    return athletes.select(
        "game_id",
        "team_id",
        F.col("a.athlete.id").alias("player_id"),
        F.col("a.athlete.displayName").alias("player_name"),
        F.col("a.athlete.position.abbreviation").alias("position"),
        F.col("a.starter").alias("starter"),
        F.col("a.didNotPlay").alias("did_not_play"),
        F.col("a.ejected").alias("ejected"),
        _to_int(m["minutes"]).alias("minutes"),
        _to_int(m["points"]).alias("pts"),
        _made(m[FG]).alias("fgm"),
        _att(m[FG]).alias("fga"),
        _made(m[FG3]).alias("fg3m"),
        _att(m[FG3]).alias("fg3a"),
        _made(m[FT]).alias("ftm"),
        _att(m[FT]).alias("fta"),
        _to_int(m["rebounds"]).alias("reb"),
        _to_int(m["offensiveRebounds"]).alias("oreb"),
        _to_int(m["defensiveRebounds"]).alias("dreb"),
        _to_int(m["assists"]).alias("ast"),
        _to_int(m["turnovers"]).alias("tov"),
        _to_int(m["steals"]).alias("stl"),
        _to_int(m["blocks"]).alias("blk"),
        _to_int(m["fouls"]).alias("pf"),
        _to_int(m["plusMinus"]).alias("plus_minus"),
    )


# =============================================================================
# MERGE
# =============================================================================

def _merge(df: DataFrame, table: str, keys: list[str]) -> None:
    """Upsert df into table on keys. Rerunning a date updates rows, never duplicates."""
    # MERGE fails if two source rows match the same target row.
    df = df.dropDuplicates(keys)

    on = " AND ".join(f"t.{k} = s.{k}" for k in keys)  # e.g. "t.game_id = s.game_id"

    (DeltaTable.forName(_spark(), table).alias("t")
        .merge(df.alias("s"), on)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute())


# =============================================================================
# Run
# =============================================================================

def run(game_date: date) -> dict:
    spark = _spark()
    day = F.col("game_date") == F.lit(game_date)

    scoreboard = spark.table(f"{config.BRONZE}.scoreboard").filter(day)
    summary = spark.table(f"{config.BRONZE}.summary").filter(day)

    games = build_games(scoreboard)
    teams = build_team_stats(summary)
    players = build_player_stats(summary)

    _merge(games, GAMES_TABLE, ["game_id"])
    _merge(teams, TEAM_TABLE, ["game_id", "team_id"])
    _merge(players, PLAYER_TABLE, ["game_id", "player_id"])

    result = {
        "game_date": game_date.isoformat(),
        "games": games.count(),
        "team_rows": teams.count(),
        "player_rows": players.count(),
    }
    print(result)
    return result