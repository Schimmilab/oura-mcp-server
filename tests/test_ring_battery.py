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
