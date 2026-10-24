"""The daily brief must show the duration of the night its score belongs to.

⛔ On 2026-10-24 the brief printed:

    ## Sleep (Score: 83)
    - Total: 5h 27m

83 is the score of the night that ended on 24.10. (7h13m); 5h27m is the night
before. The sleep periods were filtered on `day == yesterday` ("Oura
convention"), while the score came from daily_sleep for `today`. Oura dates a
sleep period by the day it ENDS, the same as daily_sleep -- the comment was
wrong, and the two halves of the section described two different nights.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from oura_mcp.tools.debug_tools import DebugToolProvider


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)

LAST_NIGHT = {
    "day": TODAY.isoformat(), "type": "long_sleep",
    "total_sleep_duration": 25980, "deep_sleep_duration": 4980,
    "rem_sleep_duration": 5340,
}
NIGHT_BEFORE = {
    "day": YESTERDAY.isoformat(), "type": "long_sleep",
    "total_sleep_duration": 19620, "deep_sleep_duration": 2280,
    "rem_sleep_duration": 3120,
}


class _FakeClient:
    async def get_sleep(self, start_date=None, end_date=None):
        return [NIGHT_BEFORE, LAST_NIGHT]

    async def get_daily_sleep(self, start_date=None, end_date=None):
        return [{"day": TODAY.isoformat(), "score": 83}]

    async def get_daily_readiness(self, start_date=None, end_date=None):
        return [{"day": TODAY.isoformat(), "score": 70,
                 "contributors": {"hrv_balance": 16, "body_temperature": 86}}]

    async def get_daily_activity(self, start_date=None, end_date=None):
        return []


async def _brief():
    return await DebugToolProvider(_FakeClient()).generate_daily_brief()


# --- MUSS ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duration_belongs_to_the_scored_night():
    out = await _brief()
    assert "Score: 83" in out
    assert "7h 13m" in out, "The brief shows a different night than its score."


# --- DARF NICHT --------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_night_before_does_not_leak_in():
    out = await _brief()
    assert "5h 27m" not in out
    assert "Periods" not in out, "Two nights were summed as one polyphasic day."
