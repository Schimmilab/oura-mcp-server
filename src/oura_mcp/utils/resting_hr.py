"""Resting heart rate in real beats per minute.

⛔ Why this module exists: ``daily_readiness.contributors.resting_heart_rate``
looks like a heart rate but is a **score from 0 to 100 where higher is better**.
Reading it as bpm inverts every comparison — a rising score means the pulse has
*fallen*. Measured on 15 days of real data, the two correlate at **-0.920**.

That mistake shipped in ``alert_system`` until v0.9.1, where the illness alarm
fired on recovery and stayed silent during an actual infection.

A second reason to avoid the score even when the direction is handled correctly:
**it saturates.** Scores cluster at 100 for anyone with a healthy pulse, and a
metric pinned to its ceiling cannot show a change. Real bpm has no ceiling.

The honest source is the sleep session: ``lowest_heart_rate`` is the nightly
trough, which is what "resting heart rate" means physiologically.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# A plausibility window. Values outside it are aggregation artefacts rather than
# pulses — most often a nap session contributing a 0 to a daily mean.
MIN_PLAUSIBLE_BPM = 30.0
MAX_PLAUSIBLE_BPM = 120.0


def extract_resting_hr_series(sleep_data: List[Dict]) -> List[Tuple[str, float]]:
    """Return ``(day, bpm)`` pairs, oldest first, skipping implausible values.

    Uses ``lowest_heart_rate`` — the nightly trough. ``average_heart_rate`` is
    deliberately not a fallback: it is a mean over the whole night and sits well
    above the resting value.
    """
    series: List[Tuple[str, float]] = []
    for session in sleep_data:
        if not isinstance(session, dict):
            continue
        bpm = session.get("lowest_heart_rate")
        if bpm is None:
            continue
        try:
            bpm = float(bpm)
        except (TypeError, ValueError):
            continue
        if not MIN_PLAUSIBLE_BPM <= bpm <= MAX_PLAUSIBLE_BPM:
            continue
        series.append((session.get("day") or "", bpm))

    series.sort(key=lambda pair: pair[0])
    return series


def extract_resting_hr_values(sleep_data: List[Dict]) -> List[float]:
    """Just the bpm values, oldest first."""
    return [bpm for _day, bpm in extract_resting_hr_series(sleep_data)]


def latest_resting_hr(sleep_data: List[Dict]) -> Optional[float]:
    """Most recent plausible resting heart rate, or ``None``."""
    values = extract_resting_hr_values(sleep_data)
    return values[-1] if values else None
