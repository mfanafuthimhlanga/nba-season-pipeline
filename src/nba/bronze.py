"""Bronze: raw JSON files -> Delta tables, one row per file, payload kept as a string."""

import os
from datetime import date

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from nba import config

SCOREBOARD_TABLE = f"{config.BRONZE}.scoreboard"
SUMMARY_TABLE = f"{config.BRONZE}.summary"


def _spark() -> SparkSession:
    # Notebooks have `spark` built in. Modules do not, so we fetch the active session.
    return SparkSession.builder.getOrCreate()


def _read_folder(path: str, game_date: date) -> DataFrame:
    """Read every file in `path` as ONE row each, with audit columns."""
    df = _spark().read.text(path, wholetext=True)
    return df.select(
        F.col("value").alias("payload"),
        F.col("_metadata.file_path").alias("source_file"),
        F.lit(game_date).alias("game_date"),
        F.current_timestamp().alias("ingested_at"),
    )


def _replace_date(df: DataFrame, table: str, game_date: date) -> None:
    """Overwrite only this game_date's rows in `table`. Other dates are untouched."""
    (df.write.mode("overwrite")
        .option("replaceWhere", f"game_date = '{game_date.isoformat()}'")
        .saveAsTable(table))


def run(game_date: date) -> dict:
    partition = config.date_partition(game_date)
    scoreboard_dir = os.path.join(config.SCOREBOARD_DIR, partition)
    summary_dir = os.path.join(config.SUMMARY_DIR, partition)

    # ingest writes scoreboard.json last, so without it the date is missing or half-written.
    if not os.path.isfile(os.path.join(scoreboard_dir, config.SCOREBOARD_FILE)):
        raise FileNotFoundError(f"No complete raw date for {game_date}. Run ingest first: {scoreboard_dir}")

    # Scoreboard: always exactly one file per date
    scoreboard = _read_folder(scoreboard_dir, game_date)
    _replace_date(
        scoreboard.select("game_date", "payload", "source_file", "ingested_at"),
        SCOREBOARD_TABLE,
        game_date,
    )

    # Summaries: zero files on days with no games
    summary_files = os.listdir(summary_dir) if os.path.isdir(summary_dir) else []
    if summary_files:
        summary = _read_folder(summary_dir, game_date).withColumn(
            "game_id", F.regexp_extract("source_file", r"(\d+)\.json$", 1)
        )
        # regexp_extract returns '' instead of failing when a name does not match.
        unnamed = summary.filter(F.col("game_id") == "").select("source_file").limit(5).collect()
        if unnamed:
            raise ValueError(f"{game_date}: summary files without a numeric game id: {[r.source_file for r in unnamed]}")

        _replace_date(
            summary.select("game_id", "game_date", "payload", "source_file", "ingested_at"),
            SUMMARY_TABLE,
            game_date,
        )
    else:
        # No games this date: clear any rows left from an earlier run
        _spark().sql(f"DELETE FROM {SUMMARY_TABLE} WHERE game_date = '{game_date.isoformat()}'")

    result = {"game_date": game_date.isoformat(), "summary_files": len(summary_files)}
    print(result)
    return result
