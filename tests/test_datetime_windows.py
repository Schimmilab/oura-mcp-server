"""heartrate and ring_battery_level refuse ranges longer than 30 days.

⛔ Measured 2026-11-10 on the real account: 30 days → 200, 31 days → 400
"Timerange between start and endtime has to be less than or equal to 30 days"
for BOTH endpoints. get_ring_battery(hours=168*5) and any heart-rate request over
a month failed outright. The client now splits such ranges into ≤30-day windows.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from oura_mcp.api.client import OuraClient

T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _recording_client(rows_per_call=None):
    client = OuraClient.__new__(OuraClient)
    calls = []

    async def fake_get_all(path, params=None, max_pages=200):
        p = dict(params or {})
        calls.append(p)
        a = datetime.fromisoformat(p["start_datetime"])
        b = datetime.fromisoformat(p["end_datetime"])
        assert b - a <= timedelta(days=30), f"window too long: {b - a}"
        # one sample at each window edge -> boundary duplicates must be removed
        return [{"timestamp": p["start_datetime"]}, {"timestamp": p["end_datetime"]}]

    client._get_all = fake_get_all
    return client, calls


# --- MUSS ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_long_battery_range_is_split_into_30_day_windows():
    client, calls = _recording_client()
    rows = await client.get_ring_battery_level(T0, T0 + timedelta(days=75))
    assert len(calls) == 3                                   # 30 + 30 + 15
    assert calls[0]["start_datetime"] == T0.isoformat()
    assert calls[-1]["end_datetime"] == (T0 + timedelta(days=75)).isoformat()
    stamps = [r["timestamp"] for r in rows]
    assert len(stamps) == len(set(stamps)), "boundary samples must not be duplicated"
    assert stamps == sorted(stamps)


@pytest.mark.asyncio
async def test_long_heart_rate_range_is_split_too():
    client, calls = _recording_client()
    await client.get_heart_rate(T0, T0 + timedelta(days=31))
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_exactly_30_days_stays_one_call():
    client, calls = _recording_client()
    await client.get_heart_rate(T0, T0 + timedelta(days=30))
    assert len(calls) == 1


# --- DARF NICHT ------------------------------------------------------------

@pytest.mark.asyncio
async def test_latest_battery_is_not_windowed():
    client, calls = _recording_client()

    async def fake_latest(path, params=None, max_pages=200):
        calls.append(dict(params or {}))
        return [{"timestamp": "x", "level": 70}]

    client._get_all = fake_latest
    await client.get_ring_battery_level(latest=True)
    assert calls == [{"latest": "true"}]
