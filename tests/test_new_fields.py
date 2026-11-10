"""Fields the API delivers that the tools never showed (found 2026-11-10)."""

from __future__ import annotations

import pytest

from oura_mcp.tools.data_tools import DataToolProvider


class _Client:
    async def get_daily_spo2(self, start_date=None, end_date=None):
        return [
            {"day": "2026-11-09", "spo2_percentage": {"average": 98.1}, "breathing_disturbance_index": 0},
            {"day": "2026-11-10", "spo2_percentage": {"average": 98.0}, "breathing_disturbance_index": 1},
            {"day": "2026-11-08", "spo2_percentage": {"average": 97.9}, "breathing_disturbance_index": None},
        ]

    async def get_daily_cardiovascular_age(self, start_date=None, end_date=None):
        return [{"day": "2026-11-10", "vascular_age": 55, "pulse_wave_velocity": 8.1919}]

    async def get_sleep(self, start_date=None, end_date=None):
        return [{"day": "2026-11-10", "type": "long_sleep",
                 "bedtime_start": "2026-11-10T00:14:31+01:00", "bedtime_end": "2026-11-10T06:42:01+01:00",
                 "total_sleep_duration": 18240, "average_breath": 14.25, "restless_periods": 193}]


@pytest.mark.asyncio
async def test_spo2_shows_bdi_per_day_and_zero_is_a_value():
    out = await DataToolProvider(_Client()).get_spo2_data(7)
    assert "BDI" in out
    assert "| 2026-11-09 | 98.1 % | 0 |" in out     # 0 is a real BDI, must be shown
    assert "| 2026-11-08 | 97.9 % | — |" in out     # None must not become 0


@pytest.mark.asyncio
async def test_cardiovascular_age_shows_pwv_with_caveat():
    out = await DataToolProvider(_Client()).get_daily_cardiovascular_age(30)
    assert "8.19 m/s" in out
    assert "abgeleitet" in out


@pytest.mark.asyncio
async def test_sleep_sessions_show_breath_and_restless():
    out = await DataToolProvider(_Client()).get_sleep_sessions(3)
    assert "14.25" in out and "193" in out
