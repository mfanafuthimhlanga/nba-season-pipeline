"""Raw ingestion: ESPN -> untouched JSON files in the landing volume, one date per run."""

import json
import os
import re
from datetime import date

from nba import config, espn


class GamesNotFinalError(RuntimeError):
    """Raised when a game that should have a box score is not final yet.

    The job task retries on this, so a late-finishing game is picked up later.
    """


_GAME_ID = re.compile(r"^\d+$")  # bronze reads game_id back from "<game_id>.json"


def _status(event: dict) -> str:
    return event["status"]["type"]["name"]


def _reset_dir(path: str) -> None:
    """Make an empty folder at path. Removes old files so a rerun replaces the date."""
    os.makedirs(path, exist_ok=True)
    for name in os.listdir(path):
        os.remove(os.path.join(path, name))


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload))


def run(game_date: date) -> dict:
    """Fetch one game date, gate on final status, write raw files. Returns a run summary."""
    # 1. Scoreboard: the list of games expected on this date
    scoreboard = espn.get_scoreboard(game_date)
    if "events" not in scoreboard:
        raise ValueError(f"{game_date}: scoreboard has no 'events' key. Keys: {list(scoreboard)}")
    events = scoreboard["events"]

    # 2. Split expected games from postponed/cancelled ones
    expected = [e for e in events if _status(e) not in config.SKIP_STATUSES]
    skipped = [e for e in events if _status(e) in config.SKIP_STATUSES]

    # 3. Gate: every expected game must be final. Raise BEFORE writing anything.
    not_final = [(e["id"], _status(e)) for e in expected if _status(e) != config.FINAL_STATUS]
    if not_final:
        raise GamesNotFinalError(f"{game_date}: {len(not_final)} game(s) not final: {not_final}")

    bad_ids = [e["id"] for e in expected if not _GAME_ID.match(str(e["id"]))]
    if bad_ids:
        raise ValueError(f"{game_date}: game ids are not numeric, bronze could not read them back: {bad_ids}")

    # 4. Fetch every summary into memory first, so a failed fetch writes nothing
    summaries = {e["id"]: espn.get_summary(e["id"]) for e in expected}

    # 5. Replace this date's folders. The scoreboard folder is emptied first and
    #    scoreboard.json is written last, so it marks a complete date: a crash
    #    part-way leaves no scoreboard.json and bronze refuses the date.
    partition = config.date_partition(game_date)
    scoreboard_dir = os.path.join(config.SCOREBOARD_DIR, partition)
    summary_dir = os.path.join(config.SUMMARY_DIR, partition)
    _reset_dir(scoreboard_dir)
    _reset_dir(summary_dir)

    for game_id, summary in summaries.items():
        _write_json(os.path.join(summary_dir, f"{game_id}.json"), summary)
    _write_json(os.path.join(scoreboard_dir, config.SCOREBOARD_FILE), scoreboard)

    # 6. Report
    result = {
        "game_date": game_date.isoformat(),
        "expected": len(expected),
        "skipped": [(e["id"], _status(e)) for e in skipped],
        "written_summaries": len(summaries),
    }
    print(result)
    return result