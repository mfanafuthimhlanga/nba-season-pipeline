"""Tests for the parts that run without Spark: config, the ESPN client, ingest.

Run from the repo root:  python -m pytest
"""

import json
import os
from datetime import date, datetime

import pytest
import requests

from nba import config, espn, ingest


# --- config -------------------------------------------------------------------

def test_blank_game_date_is_yesterday_in_new_york(monkeypatch):
    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 02:00 UTC on 22 Nov is still 21 Nov in New York, so "yesterday" is the 20th.
            return datetime(2026, 11, 21, 21, 0, tzinfo=tz)
    monkeypatch.setattr(config, "datetime", FakeDatetime)
    assert config.resolve_game_date("") == date(2026, 11, 20)
    assert config.resolve_game_date(None) == date(2026, 11, 20)


def test_explicit_game_date_and_bad_input():
    assert config.resolve_game_date(" 2026-11-15 ") == date(2026, 11, 15)
    with pytest.raises(ValueError):
        config.resolve_game_date("15/11/2026")


def test_date_partition():
    assert config.date_partition(date(2026, 11, 5)) == "game_date=2026-11-05"


# --- espn client ----------------------------------------------------------------

class FakeResponse:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(espn.time, "sleep", slept.append)
    return slept


def _serve(monkeypatch, responses):
    calls = iter(responses)
    def get(url, params, timeout):
        r = next(calls)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(espn._session, "get", get)


def test_retries_5xx_then_succeeds(monkeypatch, no_sleep):
    _serve(monkeypatch, [FakeResponse(503), FakeResponse(200, {"ok": 1})])
    assert espn._get("scoreboard", {}) == {"ok": 1}
    assert no_sleep == [2, config.REQUEST_PAUSE_S]


def test_retries_429_honouring_retry_after(monkeypatch, no_sleep):
    _serve(monkeypatch, [FakeResponse(429, headers={"Retry-After": "30"}), FakeResponse(200, {"ok": 1})])
    assert espn._get("scoreboard", {}) == {"ok": 1}
    assert no_sleep[0] == 30


def test_retry_after_is_capped(monkeypatch, no_sleep):
    _serve(monkeypatch, [FakeResponse(429, headers={"Retry-After": "86400"}), FakeResponse(200)])
    espn._get("scoreboard", {})
    assert no_sleep[0] == config.MAX_RETRY_AFTER_S


def test_other_4xx_fails_at_once(monkeypatch, no_sleep):
    _serve(monkeypatch, [FakeResponse(400)])
    with pytest.raises(requests.HTTPError):
        espn._get("scoreboard", {})
    assert no_sleep == []


def test_gives_up_after_max_attempts(monkeypatch, no_sleep):
    _serve(monkeypatch, [requests.ConnectionError()] * config.MAX_ATTEMPTS)
    with pytest.raises(requests.ConnectionError):
        espn._get("scoreboard", {})
    assert no_sleep == [2, 4]


# --- ingest ---------------------------------------------------------------------

def _event(game_id, status="STATUS_FINAL"):
    return {"id": game_id, "status": {"type": {"name": status}}}


@pytest.fixture
def landing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SCOREBOARD_DIR", str(tmp_path / "scoreboard"))
    monkeypatch.setattr(config, "SUMMARY_DIR", str(tmp_path / "summary"))
    return tmp_path


def _fake_espn(monkeypatch, events, fail_summary_for=None):
    monkeypatch.setattr(espn, "get_scoreboard", lambda d: {"events": events})
    def summary(game_id):
        if game_id == fail_summary_for:
            raise requests.HTTPError("boom")
        return {"id": game_id}
    monkeypatch.setattr(espn, "get_summary", summary)


D = date(2026, 11, 21)
DAY = config.date_partition(D)


def test_writes_summaries_and_scoreboard(landing, monkeypatch):
    _fake_espn(monkeypatch, [_event("401"), _event("402"), _event("403", "STATUS_POSTPONED")])
    result = ingest.run(D)
    assert result["expected"] == 2 and result["written_summaries"] == 2
    assert sorted(os.listdir(landing / "summary" / DAY)) == ["401.json", "402.json"]
    assert json.loads((landing / "scoreboard" / DAY / "scoreboard.json").read_text())["events"]


def test_gate_refuses_before_writing(landing, monkeypatch):
    _fake_espn(monkeypatch, [_event("401"), _event("402", "STATUS_IN_PROGRESS")])
    with pytest.raises(ingest.GamesNotFinalError):
        ingest.run(D)
    assert not (landing / "scoreboard").exists()


def test_failed_summary_writes_nothing(landing, monkeypatch):
    _fake_espn(monkeypatch, [_event("401"), _event("402")], fail_summary_for="402")
    with pytest.raises(requests.HTTPError):
        ingest.run(D)
    assert not (landing / "summary").exists()


def test_non_numeric_game_id_is_refused(landing, monkeypatch):
    _fake_espn(monkeypatch, [_event("abc")])
    with pytest.raises(ValueError, match="not numeric"):
        ingest.run(D)


def test_scoreboard_is_written_last(landing, monkeypatch):
    """A crash while writing summaries must leave no scoreboard.json behind."""
    _fake_espn(monkeypatch, [_event("401"), _event("402")])
    (landing / "scoreboard" / DAY).mkdir(parents=True)
    (landing / "scoreboard" / DAY / "scoreboard.json").write_text("{}")  # from an earlier run
    real_write = ingest._write_json
    def crash_on_second(path, payload):
        if path.endswith("402.json"):
            raise OSError("disk full")
        real_write(path, payload)
    monkeypatch.setattr(ingest, "_write_json", crash_on_second)
    with pytest.raises(OSError):
        ingest.run(D)
    assert not (landing / "scoreboard" / DAY / "scoreboard.json").exists()
