"""next_token must be followed — otherwise long ranges are cut off silently.

⛔ Measured 2026-11-10 on the real account: heartrate over 14 days returned
exactly 1000 rows plus a next_token. The client returned those 1000 as if they
were the whole range; the tool output looked complete.
"""

from __future__ import annotations

import pytest

from oura_mcp.api.client import OuraClient


def _client_with_pages(pages):
    """OuraClient without config/network: _get replays the given pages."""
    client = OuraClient.__new__(OuraClient)
    calls = []

    async def fake_get(path, params=None):
        calls.append(dict(params or {}))
        return pages[len(calls) - 1]

    client._get = fake_get
    return client, calls


# --- MUSS ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_follows_next_token_until_exhausted():
    client, calls = _client_with_pages([
        {"data": [1, 2], "next_token": "A"},
        {"data": [3], "next_token": "B"},
        {"data": [4], "next_token": None},
    ])
    rows = await client._get_all("/v2/usercollection/heartrate", {"start_datetime": "x"})
    assert rows == [1, 2, 3, 4]
    assert [c.get("next_token") for c in calls] == [None, "A", "B"]
    assert all(c["start_datetime"] == "x" for c in calls), "filters must survive paging"


@pytest.mark.asyncio
async def test_single_page_makes_one_call():
    client, calls = _client_with_pages([{"data": [1], "next_token": None}])
    assert await client._get_all("/p", {}) == [1]
    assert len(calls) == 1


# --- DARF NICHT ------------------------------------------------------------

@pytest.mark.asyncio
async def test_runaway_paging_raises_instead_of_looping():
    endless = [{"data": [0], "next_token": "again"}] * 1000
    client, _ = _client_with_pages(endless)
    with pytest.raises(RuntimeError, match="next_token"):
        await client._get_all("/p", {}, max_pages=5)


import re
from pathlib import Path

CLIENT_SRC = Path(__file__).parent.parent / "src" / "oura_mcp" / "api" / "client.py"
# personal_info is a single object, not a paginated list.
NOT_PAGINATED = {"/v2/usercollection/personal_info"}


def _direct_list_calls(src: str) -> list[str]:
    return [p for p in re.findall(r'self\._get\(\s*"(/v2/usercollection/[^"]+)"', src)
            if p not in NOT_PAGINATED]


def test_no_list_getter_bypasses_get_all():
    offenders = _direct_list_calls(CLIENT_SRC.read_text())
    assert not offenders, f"these getters ignore next_token: {offenders}"


def test_guard_actually_detects_a_bypass():
    """Negative control: a planted direct call must be found."""
    planted = 'response = await self._get("/v2/usercollection/heartrate", params)'
    assert _direct_list_calls(planted) == ["/v2/usercollection/heartrate"]
