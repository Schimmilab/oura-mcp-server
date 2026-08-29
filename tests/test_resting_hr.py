"""Tests for resting heart rate handling.

The bug these pin down shipped for months: the readiness *score*
(0-100, higher = better) was read as if it were bpm. Measured on 15 days of
real data the two correlate at -0.920, so the alarm fired on recovery and went
quiet during an infection. Direction is the whole point here.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oura_mcp.utils.alert_system import AlertSystem  # noqa: E402
from oura_mcp.utils.resting_hr import (  # noqa: E402
    extract_resting_hr_values,
    latest_resting_hr,
)
from oura_mcp.utils.sleep_aggregation import aggregate_sleep_sessions_by_day  # noqa: E402


def _nights(values):
    """Sleep sessions carrying the given nightly resting pulses."""
    return [
        {"day": f"2026-08-{i + 1:02d}", "lowest_heart_rate": v, "total_sleep_duration": 25000}
        for i, v in enumerate(values)
    ]


# ----------------------------------------------------------------- extraction

def test_extracts_real_bpm_from_sleep_sessions():
    assert extract_resting_hr_values(_nights([58, 61, 60])) == [58.0, 61.0, 60.0]


def test_ignores_zero_and_missing_values():
    """A nap reporting 0 is an artefact, not a pulse of zero."""
    sessions = _nights([58, 61])
    sessions.append({"day": "2026-08-03", "lowest_heart_rate": 0})
    sessions.append({"day": "2026-08-04", "lowest_heart_rate": None})
    assert extract_resting_hr_values(sessions) == [58.0, 61.0]


def test_series_is_ordered_oldest_first():
    """Baseline-vs-recent slicing is meaningless if the order is not guaranteed."""
    shuffled = list(reversed(_nights([58, 59, 60, 61])))
    assert extract_resting_hr_values(shuffled) == [58.0, 59.0, 60.0, 61.0]
    assert latest_resting_hr(shuffled) == 61.0


# --------------------------------------------------------------- alert direction

def test_alarm_fires_when_the_pulse_RISES():
    """Seven calm nights, then three clearly elevated ones."""
    alerts = AlertSystem()._check_resting_hr_alerts(
        _nights([58, 59, 58, 60, 59, 58, 59, 72, 73, 74])
    )
    assert alerts, "a 14bpm jump above baseline must raise an alert"
    assert alerts[0].category.value == "resting_hr"
    assert alerts[0].metric_value > 70


def test_alarm_stays_SILENT_when_the_pulse_FALLS():
    """⛔ The regression that shipped: recovery used to be reported as illness.

    With the score-based code these same nights (a falling pulse = a rising
    score) produced a CRITICAL "possible illness - consult doctor".
    """
    alerts = AlertSystem()._check_resting_hr_alerts(
        _nights([72, 73, 72, 74, 73, 72, 73, 58, 57, 58])
    )
    assert alerts == [], f"a falling pulse must not alarm, got: {[a.title for a in alerts]}"


def test_steady_pulse_does_not_alarm():
    assert AlertSystem()._check_resting_hr_alerts(
        _nights([60, 61, 60, 59, 60, 61, 60, 60, 61, 59])
    ) == []


def test_too_little_data_is_silent_rather_than_wrong():
    assert AlertSystem()._check_resting_hr_alerts(_nights([60, 61, 90])) == []


def test_readiness_scores_can_no_longer_reach_the_alarm():
    """The old input shape must now yield nothing, not a misread alarm.

    A rising score (= improving) would have been read as a rising pulse.
    """
    readiness = [
        {"day": f"2026-08-{i + 1:02d}", "contributors": {"resting_heart_rate": v}}
        for i, v in enumerate([51, 60, 58, 62, 59, 61, 60, 98, 99, 100])
    ]
    assert AlertSystem()._check_resting_hr_alerts(readiness) == []


# ------------------------------------------------------------------ aggregation

def test_naps_reporting_zero_do_not_drag_the_daily_mean_down():
    """The real 2026-08-18 case: 67.75 bpm was reported as 22.58."""
    day = aggregate_sleep_sessions_by_day([
        {"day": "2026-08-18", "total_sleep_duration": 25000,
         "average_heart_rate": 67.75, "lowest_heart_rate": 62},
        {"day": "2026-08-18", "total_sleep_duration": 900,
         "average_heart_rate": 0, "lowest_heart_rate": 0},
        {"day": "2026-08-18", "total_sleep_duration": 600,
         "average_heart_rate": 0, "lowest_heart_rate": 0},
    ])[0]
    assert day["average_heart_rate"] == pytest.approx(67.75)
    assert day["lowest_heart_rate"] == pytest.approx(62.0)
