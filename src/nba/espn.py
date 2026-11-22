"""Thin HTTP client for the ESPN NBA endpoints. Returns parsed JSON dicts."""

import time
from datetime import date

import requests

from nba import config

_session = requests.Session()
_session.headers.update({"User-Agent": "nba-season-pipeline/0.1"})


def _wait_seconds(response: requests.Response | None, attempt: int) -> float:
    """Backoff before the next attempt: 2s, 4s, ...

    A 429 may say how long to wait in Retry-After (seconds). Honour it, capped,
    so a bad header cannot stall the job.
    """
    backoff = 2 ** attempt
    if response is not None and response.status_code == 429:
        try:
            return min(max(float(response.headers.get("Retry-After", backoff)), backoff), config.MAX_RETRY_AFTER_S)
        except ValueError:
            return backoff
    return backoff


def _get(path: str, params: dict) -> dict:
    """GET one endpoint.

    Retries connection errors, timeouts, 429 (rate limited) and 5xx with
    backoff (2s, 4s). Raises immediately on any other 4xx: a bad request will
    not fix itself on retry.
    """
    url = f"{config.ESPN_BASE}/{path}"

    for attempt in range(1, config.MAX_ATTEMPTS + 1):
        last_try = attempt == config.MAX_ATTEMPTS
        try:
            response = _session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout):
            if last_try:
                raise
            time.sleep(_wait_seconds(None, attempt))
            continue

        retryable = response.status_code == 429 or response.status_code >= 500
        if retryable and not last_try:
            time.sleep(_wait_seconds(response, attempt))
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
