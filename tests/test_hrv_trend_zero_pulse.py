"""A missing pulse must not render as the number 0 in a bpm column.

⛔ On 2026-09-13 the trend table produced this for the night:

    | 2026-09-13 | — | 0 | 0h4m | — | — |

That row is a 23-minute doze from the previous evening; the real 7h43m night sat
in the row underneath. The "0" was read as "Oura delivered no pulse", and the
whole night was written up in the vault as missing -- twice, on 12.09. and
13.09. Naps come back with lowest_heart_rate absent and average_heart_rate 0,
and the renderer formatted that straight into the column.

⭐ The fix labels rather than hides. Dropping short sessions would have been the
smaller diff, but silently removing rows is exactly how the night went missing.
"""

from __future__ import annotations

import pytest

from oura_mcp.tools.debug_tools import DebugToolProvider


NIGHT = {
    "day": "2026-09-13", "type": "long_sleep",
    "average_hrv": 14, "lowest_heart_rate": 59, "average_heart_rate": 68,
    "total_sleep_duration": 27780, "deep_sleep_duration": 4500,
    "rem_sleep_duration": 4380,
}
DOZE = {
    "day": "2026-09-13", "type": "sleep",
    "average_hrv": None, "lowest_heart_rate": None, "average_heart_rate": 0,
    "total_sleep_duration": 270, "deep_sleep_duration": 0, "rem_sleep_duration": 0,
}
NAP = {
    "day": "2026-09-12", "type": "late_nap",
    "average_hrv": 11, "lowest_heart_rate": 65, "average_heart_rate": 72,
    "total_sleep_duration": 3210, "deep_sleep_duration": 180, "rem_sleep_duration": 0,
}


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows

    async def get_sleep(self, start_date=None, end_date=None):
        return self.rows


async def _table(rows):
    return await DebugToolProvider(_FakeClient(rows)).get_hrv_trend(3)


# --- MUSS ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zero_pulse_is_rendered_as_missing():
    out = await _table([DOZE])
    assert "| 0 |" not in out, "A pulse of 0 was printed as a measurement."
    assert "—" in out


@pytest.mark.asyncio
async def test_fragment_is_labelled():
    out = await _table([NIGHT, DOZE])
    fragment_line = [l for l in out.splitlines() if "0h4m" in l][0]
    assert "Fragment" in fragment_line


@pytest.mark.asyncio
async def test_the_real_night_is_not_labelled_a_fragment():
    """DARF NICHT: the 7h43m night must stay an ordinary row."""
    out = await _table([NIGHT, DOZE])
    night_line = [l for l in out.splitlines() if "7h43m" in l][0]
    assert "Fragment" not in night_line
    assert "| 59 |" in night_line
    assert "| 14 |" in night_line


@pytest.mark.asyncio
async def test_a_lone_nap_falls_back_into_the_table_and_is_labelled():
    """⭐ The trap: 65 bpm is plausible, so no value check catches this one.

    A late_nap is normally filtered out (see the next test). But the renderer
    falls back to showing everything when the filter leaves nothing, and a
    53-minute nap with a real pulse would then read as a short night.
    """
    out = await _table([NAP])
    assert "2026-09-12" in out
    assert "Fragment" in out


# --- DARF NICHT ------------------------------------------------------------

@pytest.mark.asyncio
async def test_short_sleep_typed_sessions_are_labelled_not_removed():
    """A "sleep"-typed fragment must stay visible.

    Silently removing rows is how the night went missing in the first place, so
    the doze is labelled rather than dropped.
    """
    out = await _table([NIGHT, DOZE])
    assert out.count("| 2026-09-13") == 2


@pytest.mark.asyncio
async def test_late_naps_are_excluded_by_design():
    """Documents existing behaviour that this test file discovered.

    ⚠️ Found while writing the test above: late_nap sessions never reach the
    table -- the filter keeps only ("long_sleep", "sleep"). That is intended for
    a trend over nights, but it was nowhere pinned down, so a future change to
    the filter would pass silently.
    """
    out = await _table([NIGHT, NAP])
    assert "2026-09-12" not in out
    assert "7h43m" in out


@pytest.mark.asyncio
async def test_the_hrv_average_ignores_fragments_but_keeps_the_night():
    out = await _table([NIGHT, DOZE])
    assert "**Gesamt-Ø:** 14.0 ms" in out
