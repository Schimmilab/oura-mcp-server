"""The /sleep window must not drop a night that began after midnight.

⛔ The defect: Oura's ``/v2/usercollection/sleep`` filters on ``bedtime_start``
and treats ``end_date`` as EXCLUSIVE -- unlike the ``daily_*`` endpoints, which
filter on ``day`` inclusively. A night starting at 02:20 therefore carries
``day == end_date`` but is not returned when ``end_date`` is that same day.

⚠️ The damage was not an empty result, which someone would have noticed. What
came back was the 23-minute doze from the evening before, so "the latest
session" was a 4-minute fragment instead of a 9-hour night. Measured against the
real account on 2026-09-13:

    end_date=2026-09-13  ->  only  type="sleep",      start 09-12T23:06
    end_date=2026-09-14  ->  plus  type="long_sleep", start 09-13T02:20 (7h43m)

Cross-checked against two independent instruments for the same night: the
Withings mat logged 02:16-11:28 and the CPAP 02:16:20 for 9.0 h. Three devices
agreed within four minutes; only the query was wrong.
"""

from __future__ import annotations

from datetime import date

import pytest

from oura_mcp.api.client import OuraClient


class _Recorder:
    """Stands in for the HTTP layer and answers like the real endpoint does."""

    def __init__(self, sessions):
        self.sessions = sessions
        self.params = None

    async def __call__(self, path, params):
        self.params = params
        end = params["end_date"]
        start = params["start_date"]
        # The quirk under test: bedtime_start, end EXCLUSIVE.
        return {
            "data": [
                s for s in self.sessions
                if start <= s["bedtime_start"][:10] < end
            ]
        }


NIGHT = {"day": "2026-09-13", "type": "long_sleep",
         "bedtime_start": "2026-09-13T02:20:00.000+02:00", "lowest_heart_rate": 59}
DOZE = {"day": "2026-09-13", "type": "sleep",
        "bedtime_start": "2026-09-12T23:06:00.000+02:00", "lowest_heart_rate": None}
EARLIER = {"day": "2026-09-12", "type": "long_sleep",
           "bedtime_start": "2026-09-12T02:55:29.000+02:00", "lowest_heart_rate": 60}
TOMORROW = {"day": "2026-09-14", "type": "long_sleep",
            "bedtime_start": "2026-09-14T01:10:00.000+02:00", "lowest_heart_rate": 58}
# ⛔ THE leak candidate, and the reason this file has a second sabotage run.
# My first version used TOMORROW above -- but its bedtime_start (09-14) falls
# outside the widened query window too, so the fake dropped it and the trim had
# nothing to remove. The sabotage "widen the window, delete the trim" stayed
# GREEN. A tonight-evening doze is the case that actually leaks: Oura dates a
# 23:50 session to the NEXT day, exactly as the real 23:06 doze became day
# 2026-09-13. bedtime_start 09-13 is inside the window, day 09-14 is not.
LATE_DOZE_TONIGHT = {"day": "2026-09-14", "type": "sleep",
                     "bedtime_start": "2026-09-13T23:50:00.000+02:00",
                     "lowest_heart_rate": 70}


def _client(sessions):
    c = OuraClient.__new__(OuraClient)
    rec = _Recorder(sessions)
    c._get = rec
    c._format_date = lambda d: d.isoformat()
    return c, rec


# --- MUSS liefern ----------------------------------------------------------

@pytest.mark.asyncio
async def test_night_starting_after_midnight_is_returned():
    """MUSS: the 02:20 night for end_date=its own day."""
    client, _ = _client([EARLIER, DOZE, NIGHT])
    rows = await client.get_sleep(date(2026, 9, 13), date(2026, 9, 13))
    assert NIGHT in rows


@pytest.mark.asyncio
async def test_the_long_night_wins_over_the_evening_doze():
    """⭐ The symptom that made this visible: 'latest session' was 4 minutes."""
    client, _ = _client([EARLIER, DOZE, NIGHT])
    rows = await client.get_sleep(date(2026, 9, 13), date(2026, 9, 13))
    long_sleeps = [r for r in rows if r["type"] == "long_sleep"]
    assert long_sleeps == [NIGHT]


@pytest.mark.asyncio
async def test_it_asks_the_api_for_one_day_more():
    client, rec = _client([NIGHT])
    await client.get_sleep(date(2026, 9, 13), date(2026, 9, 13))
    assert rec.params["end_date"] == "2026-09-14"
    assert rec.params["start_date"] == "2026-09-13"


# --- DARF NICHT liefern ---------------------------------------------------

@pytest.mark.asyncio
async def test_the_extra_day_does_not_leak_into_the_result():
    """The compensation must widen the QUERY, not the answer.

    Without trimming, every caller would silently receive a session from
    beyond the range it asked for -- and a 'latest session' reader would then
    report tomorrow's night as today's.
    """
    client, _ = _client([NIGHT, LATE_DOZE_TONIGHT, TOMORROW])
    rows = await client.get_sleep(date(2026, 9, 13), date(2026, 9, 13))
    assert LATE_DOZE_TONIGHT not in rows, (
        "A session dated to tomorrow came back for today -- the widened query "
        "is leaking, and a 'latest session' reader would report this doze as "
        "tonight's sleep."
    )
    assert TOMORROW not in rows
    assert rows == [NIGHT]


@pytest.mark.asyncio
async def test_earlier_days_are_still_excluded():
    client, _ = _client([EARLIER, NIGHT])
    rows = await client.get_sleep(date(2026, 9, 13), date(2026, 9, 13))
    assert EARLIER not in rows


@pytest.mark.asyncio
async def test_a_multi_day_range_keeps_both_ends():
    client, _ = _client([EARLIER, DOZE, NIGHT, TOMORROW])
    rows = await client.get_sleep(date(2026, 9, 12), date(2026, 9, 13))
    assert EARLIER in rows and NIGHT in rows and TOMORROW not in rows
