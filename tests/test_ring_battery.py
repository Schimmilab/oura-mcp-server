"""ring_battery_level takes start_datetime/end_datetime, not start_date/end_date.

⛔ Spec 1.43 lists start_datetime, end_datetime, next_token, latest. The client
sent start_date/end_date, which the API ignores — the requested range never
reached the server.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from oura_mcp.api.client import OuraClient


def _recording_client():
    client = OuraClient.__new__(OuraClient)
    seen = {}

    async def fake_get_all(path, params=None, max_pages=200):
        seen["path"], seen["params"] = path, dict(params or {})
        return []

    client._get_all = fake_get_all
    return client, seen


@pytest.mark.asyncio
async def test_sends_datetime_parameters():
    client, seen = _recording_client()
    await client.get_ring_battery_level(
        datetime(2026, 11, 9, 0, 0), datetime(2026, 11, 10, 7, 0)
    )
    assert seen["params"]["start_datetime"].startswith("2026-11-09T00:00")
    assert seen["params"]["end_datetime"].startswith("2026-11-10T07:00")
    assert "start_date" not in seen["params"] and "end_date" not in seen["params"]


@pytest.mark.asyncio
async def test_latest_only():
    client, seen = _recording_client()
    await client.get_ring_battery_level(latest=True)
    assert seen["params"] == {"latest": "true"}


from oura_mcp.tools.data_tools import DataToolProvider

SAMPLES = [
    {"timestamp": "2026-11-10T04:00:00Z", "level": 90, "charging": False, "in_charger": False},
    {"timestamp": "2026-11-10T05:00:00Z", "level": 85, "charging": True, "in_charger": True},
    {"timestamp": "2026-11-10T05:20:00Z", "level": 95, "charging": True, "in_charger": True},
    {"timestamp": "2026-11-10T05:40:00Z", "level": 81, "charging": False, "in_charger": False},
]


class _BatteryClient:
    async def get_ring_battery_level(self, start_datetime=None, end_datetime=None, latest=False):
        return SAMPLES[-1:] if latest else SAMPLES


@pytest.mark.asyncio
async def test_battery_tool_lists_charger_periods():
    out = await DataToolProvider(_BatteryClient()).get_ring_battery(24)
    assert "81 %" in out                      # latest level
    assert "Im Ladegerät" in out              # a charger period is reported
    assert "06:00" in out and "06:40" in out  # local time (UTC+1): in at 06:00, out at 06:40


@pytest.mark.asyncio
async def test_battery_tool_handles_no_data():
    class Empty:
        async def get_ring_battery_level(self, **kw):
            return []
    out = await DataToolProvider(Empty()).get_ring_battery(24)
    assert "Keine" in out


@pytest.mark.asyncio
async def test_charger_periods_carry_the_date():
    """Over a multi-day window, '10:08–12:06' alone cannot be placed on a day."""
    out = await DataToolProvider(_BatteryClient()).get_ring_battery(168)
    assert "10.11. 06:00–06:40" in out
