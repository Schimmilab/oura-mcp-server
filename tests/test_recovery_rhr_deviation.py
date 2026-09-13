"""The RHR term of the recovery score must come from data, not from a constant.

⛔ The bug this pins down: both callers of ``interpret_recovery_state`` passed a
hardcoded ``resting_hr_deviation=0`` with the comment "we'd need to calculate
this from baseline". The term ``max(0, 100 - abs(dev) * 10) * 0.10`` therefore
contributed its full 10 points every single day, and the documented red
criterion "resting HR >= +5 bpm above baseline" could never fire.

Found on 2026-09-13 by a control that is cheap and should have run much earlier:
the reported pulse moved 62 - 62 - 61 - 63 - 57 - 55 bpm over six days while the
reported deviation stayed 0 the whole time -- and on a seventh day with no pulse
at all it still read 0.

⭐ The decisive test is MUST_FAIL_WITH_CONSTANT below. A "fix" that keeps
awarding full marks passes every other assertion in this file.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from oura_mcp.utils.interpretation import InterpretationEngine
from oura_mcp.utils.resting_hr import extract_resting_hr_series


BASE = dict(readiness=76, hrv_balance=73, sleep_score=79, temperature_score=80)


def score(dev):
    return InterpretationEngine().interpret_recovery_state(
        resting_hr_deviation=dev, **BASE
    )["recovery_score"]


# --- MUSS melden (positive controls) ---------------------------------------

def test_elevated_pulse_lowers_the_score():
    """MUST_FAIL_WITH_CONSTANT: +6 bpm has to cost points."""
    assert score(6.0) < score(0.0) - 3, (
        "A pulse 6 bpm above baseline scored the same as one on baseline -- "
        "the deviation is being ignored, which is exactly the shipped bug."
    )


def test_red_criterion_can_actually_fire():
    """+5 bpm is the documented threshold; it must be visible in the score."""
    assert score(5.0) < score(0.0)


def test_larger_deviation_costs_more_than_smaller():
    assert score(8.0) < score(3.0) < score(0.0)


def test_negative_deviation_also_costs():
    """A pulse far BELOW baseline is a deviation too, not a bonus."""
    assert score(-8.0) < score(0.0)


def test_missing_value_is_reported_as_missing():
    signals = InterpretationEngine().interpret_recovery_state(
        resting_hr_deviation=None, **BASE
    )["signals"]
    assert signals["resting_hr"]["deviation"] is None
    assert signals["resting_hr"]["weight"] == "excluded"


# --- DARF NICHT melden (negative controls) --------------------------------

def test_on_baseline_still_scores_full_marks():
    """The normal path must not regress: 0 bpm deviation is a good value."""
    assert score(0.0) == pytest.approx(78.1, abs=0.1)


def test_missing_value_is_not_silently_worth_ten_points():
    """None must not be treated as 0 -- that is the bug in its other form."""
    assert score(None) != pytest.approx(score(0.0), abs=0.05)


def test_missing_value_renormalises_instead_of_subtracting_ten():
    """Dropping the term must widen uncertainty, not deduct a flat 10 points."""
    naive_subtraction = score(0.0) - 10.0
    assert score(None) > naive_subtraction + 5


def test_missing_value_stays_within_the_scale():
    assert 0.0 <= score(None) <= 100.0


# --- the dating guard ------------------------------------------------------

def _session(day, bpm):
    """A main night. ``type`` matters: the deviation path filters on it."""
    return {"day": day, "type": "long_sleep", "lowest_heart_rate": bpm}


def test_series_skips_sessions_without_a_pulse():
    """A nap contributing no pulse must not enter the series as a value."""
    series = extract_resting_hr_series(
        [_session("2026-09-12", 57), {"day": "2026-09-13"}]
    )
    assert [bpm for _day, bpm in series] == [57.0]


class _FakeClient:
    def __init__(self, sessions):
        self.sessions = sessions

    async def get_sleep(self, start_date=None, end_date=None):
        return self.sessions


def _provider(sessions):
    from oura_mcp.tools.intelligence_tools import IntelligenceToolProvider
    from oura_mcp.utils.baselines import BaselineManager
    from oura_mcp.utils.anomalies import AnomalyDetector

    return IntelligenceToolProvider(
        oura_client=_FakeClient(sessions),
        baseline_manager=BaselineManager(),
        anomaly_detector=AnomalyDetector(BaselineManager()),
        interpreter=InterpretationEngine(),
    )


@pytest.mark.asyncio
async def test_deviation_is_none_when_tonight_is_missing():
    """⭐ The 13.09. case: Oura had a daily score but no main sleep session.

    Comparing the LAST DELIVERED night against the baseline would answer for
    the wrong date -- silently, and with a plausible number.
    """
    today = date(2026, 9, 13)
    sessions = [
        _session((today - timedelta(days=n)).isoformat(), 60.0)
        for n in range(1, 15)
    ]
    assert await _provider(sessions)._resting_hr_deviation(today) is None


@pytest.mark.asyncio
async def test_deviation_is_none_on_too_thin_a_baseline():
    today = date(2026, 9, 13)
    sessions = [_session(today.isoformat(), 63.0)] + [
        _session((today - timedelta(days=n)).isoformat(), 57.0) for n in range(1, 4)
    ]
    assert await _provider(sessions)._resting_hr_deviation(today) is None


@pytest.mark.asyncio
async def test_deviation_is_measured_when_the_night_is_there():
    today = date(2026, 9, 13)
    sessions = [_session(today.isoformat(), 63.0)] + [
        _session((today - timedelta(days=n)).isoformat(), 57.0) for n in range(1, 11)
    ]
    dev = await _provider(sessions)._resting_hr_deviation(today)
    assert dev == pytest.approx(6.0, abs=0.01)


# --- the nap trap ----------------------------------------------------------
# ⛔ These exist because the first version of this fix passed every test above
# while selecting the wrong session. My fixtures had exactly ONE session per
# day, so the ambiguity could not appear in them -- self-built test data shares
# the assumptions of its author. The live positive control found it.

def _nap(day, bpm):
    return {"day": day, "type": "late_nap", "lowest_heart_rate": bpm}


def _night(day, bpm):
    return {"day": day, "type": "long_sleep", "lowest_heart_rate": bpm}


def test_nap_is_excluded_when_asked():
    """Real 2026-09-08 shape: nap 65 bpm, main night 61 bpm, same day."""
    rows = [_nap("2026-09-08", 65), _night("2026-09-08", 61)]
    assert extract_resting_hr_series(rows, long_sleep_only=True) == [("2026-09-08", 61.0)]


def test_nap_order_does_not_decide_the_answer():
    """⭐ The actual defect: 'take the latest' depended on API ordering."""
    forward = extract_resting_hr_series(
        [_nap("2026-09-08", 65), _night("2026-09-08", 61)], long_sleep_only=True
    )
    reversed_ = extract_resting_hr_series(
        [_night("2026-09-08", 61), _nap("2026-09-08", 65)], long_sleep_only=True
    )
    assert forward == reversed_ == [("2026-09-08", 61.0)]


def test_default_still_returns_both_sessions():
    """DARF NICHT: the shared helper must not change for existing callers."""
    rows = [_nap("2026-09-08", 65), _night("2026-09-08", 61)]
    assert len(extract_resting_hr_series(rows)) == 2


@pytest.mark.asyncio
async def test_deviation_uses_the_night_not_the_nap():
    today = date(2026, 9, 13)
    sessions = [_night(today.isoformat(), 61.0), _nap(today.isoformat(), 75.0)]
    sessions += [
        _night((today - timedelta(days=n)).isoformat(), 61.0) for n in range(1, 11)
    ]
    dev = await _provider(sessions)._resting_hr_deviation(today)
    assert dev == pytest.approx(0.0, abs=0.01), (
        "The nap's 75 bpm leaked into the answer -- either as today's value or "
        "by inflating the baseline."
    )


@pytest.mark.asyncio
async def test_session_without_a_type_is_not_guessed_to_be_the_night():
    """DARF NICHT: an untyped session must not be assumed to be the main sleep.

    Excluding it yields "not available", which is a gap. Including it would
    yield a number that might be a nap -- a plausible wrong value is worse than
    an admitted gap.
    """
    today = date(2026, 9, 13)
    sessions = [{"day": today.isoformat(), "lowest_heart_rate": 61.0}]
    sessions += [_session((today - timedelta(days=n)).isoformat(), 61.0) for n in range(1, 11)]
    assert await _provider(sessions)._resting_hr_deviation(today) is None
