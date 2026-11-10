"""Pure helpers for the 5-minute sleep timeline.

Fixture mirrors the real night of 2026-11-10 (long_sleep, start 00:14:31,
interval 300 s, leading None values while the ring was still settling).
"""

from __future__ import annotations

from oura_mcp.utils.sleep_timeline import (
    PHASE_NAMES,
    hr_summary,
    phase_runs,
    timeline_rows,
)

SAMPLE = {
    "bedtime_start": "2026-11-10T00:14:31.000+01:00",
    "heart_rate": {"interval": 300.0, "timestamp": "2026-11-10T00:14:31.000+01:00",
                   "items": [None, None, 78.0, 76.0, 72.0, 60.0, 58.0, 64.0]},
    "hrv": {"interval": 300.0, "timestamp": "2026-11-10T00:14:31.000+01:00",
            "items": [None, None, 15.0, 13.0, 12.0, 20.0, 22.0, None]},
    "sleep_phase_5_min": "44221134",
}


def test_phase_codes_follow_the_spec():
    assert PHASE_NAMES == {"1": "Tief", "2": "Leicht", "3": "REM", "4": "Wach"}


def test_rows_share_one_time_axis():
    rows = timeline_rows(SAMPLE)
    assert len(rows) == 8
    assert rows[0]["time"] == "00:14" and rows[1]["time"] == "00:19" and rows[7]["time"] == "00:49"
    assert rows[2] == {"time": "00:24", "phase": "Leicht", "hr": 78.0, "hrv": 15.0}


def test_missing_values_stay_none_not_zero():
    rows = timeline_rows(SAMPLE)
    assert rows[0]["hr"] is None and rows[0]["hrv"] is None
    assert rows[7]["hrv"] is None


def test_phase_runs_compress_the_string():
    runs = phase_runs("44221134", start="2026-11-10T00:14:31.000+01:00", step_seconds=300)
    assert runs == [
        {"start": "00:14", "end": "00:24", "phase": "Wach", "minutes": 10},
        {"start": "00:24", "end": "00:34", "phase": "Leicht", "minutes": 10},
        {"start": "00:34", "end": "00:44", "phase": "Tief", "minutes": 10},
        {"start": "00:44", "end": "00:49", "phase": "REM", "minutes": 5},
        {"start": "00:49", "end": "00:54", "phase": "Wach", "minutes": 5},
    ]


def test_phase_runs_work_at_30_seconds():
    runs = phase_runs("1111", start="2026-11-10T01:00:00+01:00", step_seconds=30)
    assert runs == [{"start": "01:00", "end": "01:02", "phase": "Tief", "minutes": 2}]


def test_hr_summary_finds_the_nadir_and_ignores_gaps():
    s = hr_summary(SAMPLE, window=2)
    assert s["mean"] == round((78 + 76 + 72 + 60 + 58 + 64) / 6, 1)
    assert s["nadir_mean"] == 59.0          # (60 + 58) / 2
    assert s["nadir_time"] == "00:39"       # window starts at index 5
    assert s["first_hour_mean"] is not None


def test_hr_summary_without_data_returns_none_values():
    s = hr_summary({"heart_rate": {"interval": 300, "items": [None, None], "timestamp": SAMPLE["bedtime_start"]}})
    assert s == {"mean": None, "nadir_mean": None, "nadir_time": None, "first_hour_mean": None}


import pytest

from oura_mcp.tools.data_tools import DataToolProvider

NIGHT = dict(SAMPLE, day="2026-11-10", type="long_sleep",
             bedtime_end="2026-11-10T00:54:31.000+01:00",
             sleep_phase_30_sec="4444" * 20, average_breath=14.25,
             restless_periods=193, sleep_algorithm_version="v2")
NAP = {"day": "2026-11-10", "type": "sleep", "bedtime_start": "2026-11-09T22:00:00+01:00",
       "heart_rate": {"interval": 300, "items": [70.0], "timestamp": "2026-11-09T22:00:00+01:00"},
       "hrv": {"interval": 300, "items": [10.0], "timestamp": "2026-11-09T22:00:00+01:00"},
       "sleep_phase_5_min": "4"}


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows

    async def get_sleep(self, start_date=None, end_date=None):
        return self.rows


@pytest.mark.asyncio
async def test_timeline_tool_shows_main_sleep_with_caveat():
    out = await DataToolProvider(_FakeClient([NAP, NIGHT])).get_sleep_timeline("2026-11-10")
    assert "00:14" in out and "Leicht" in out and "| 78 |" in out
    assert "klassifiziert" in out                      # phases are labelled
    assert "14.25" in out and "193" in out             # breath + restless shown
    assert "22:00" not in out                          # the nap is not the main sleep


@pytest.mark.asyncio
async def test_timeline_tool_30s_gives_runs_not_rows():
    out = await DataToolProvider(_FakeClient([NIGHT])).get_sleep_timeline("2026-11-10", resolution="30s")
    assert "Wach" in out and "min" in out
    assert out.count("\n|") < 40, "30-second output must be run-length encoded"


@pytest.mark.asyncio
async def test_timeline_tool_without_night():
    out = await DataToolProvider(_FakeClient([])).get_sleep_timeline("2026-11-10")
    assert "Keine" in out
