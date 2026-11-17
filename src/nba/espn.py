"""Thin HTTP client for the ESPN NBA endpoints. Returns parsed JSON dicts."""

import time
from datetime import date

import requests

from nba import config

_session = requests.Session()
_session.headers.update({"User-Agent": "nba-season-pipeline/0.1"})


def _get(path: str, params: dict) -> dict:
    """GET one endpoint.

    Retries connection errors, timeouts and 5xx with backoff (2s, 4s).
    Raises immediately on 4xx: a bad request will not fix itself on retry.
    """
    url = f"{config.ESPN_BASE}/{path}"

    for attempt in range(1, config.MAX_ATTEMPTS + 1):
        last_try = attempt == config.MAX_ATTEMPTS
        try:
            response = _session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout):
            if last_try:
                raise
            time.sleep(2 ** attempt)
            continue

        if response.status_code >= 500 and not last_try:
            time.sleep(2 ** attempt)
            continue

        response.raise_for_status()  # any remaining 4xx/5xx becomes an exception
        time.sleep(config.REQUEST_PAUSE_S)
        return response.json()

    raise RuntimeError(f"unreachable: no response for {url}")


def get_scoreboard(game_date: date) -> dict:
    """All games on one US Eastern game day. One date per call (ranges return 400)."""
    return _get("scoreboard", {"dates": game_date.strftime("%Y%m%d")})


def get_summary(game_id: str) -> dict:
    """Full game summary, including boxscore.players and boxscore.teams."""
    return _get("summary", {"event": game_id})