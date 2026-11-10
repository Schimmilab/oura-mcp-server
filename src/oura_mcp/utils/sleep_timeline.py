"""5-minute sleep timeline: phases (classified) next to HR and HRV (measured).

Oura delivers three series for a sleep period on one time axis starting at
``bedtime_start``: ``heart_rate.items`` and ``hrv.items`` (interval 300 s,
None = gap) and ``sleep_phase_5_min`` (one character per 5 minutes).
Phase codes per OpenAPI 1.43: 1 deep, 2 light, 3 REM, 4 awake.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

PHASE_NAMES = {"1": "Tief", "2": "Leicht", "3": "REM", "4": "Wach"}


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _series(record: Dict[str, Any], key: str) -> List[Optional[float]]:
    return list((record.get(key) or {}).get("items") or [])


def timeline_rows(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One row per 5-minute slot: time, phase name, hr, hrv (None stays None)."""
    phases = record.get("sleep_phase_5_min") or ""
    hr = _series(record, "heart_rate")
    hrv = _series(record, "hrv")
    start_ts = (record.get("heart_rate") or {}).get("timestamp") or record["bedtime_start"]
    step = int((record.get("heart_rate") or {}).get("interval") or 300)
    start = _parse(start_ts)
    n = max(len(phases), len(hr), len(hrv))
    rows = []
    for i in range(n):
        rows.append({
            "time": _hhmm(start + timedelta(seconds=step * i)),
            "phase": PHASE_NAMES.get(phases[i]) if i < len(phases) else None,
            "hr": hr[i] if i < len(hr) else None,
            "hrv": hrv[i] if i < len(hrv) else None,
        })
    return rows


def phase_runs(phases: str, start: str, step_seconds: int) -> List[Dict[str, Any]]:
    """Run-length encode a phase string into blocks with start/end/minutes."""
    runs: List[Dict[str, Any]] = []
    t0 = _parse(start)
    i = 0
    while i < len(phases):
        j = i
        while j < len(phases) and phases[j] == phases[i]:
            j += 1
        a = t0 + timedelta(seconds=step_seconds * i)
        b = t0 + timedelta(seconds=step_seconds * j)
        runs.append({
            "start": _hhmm(a),
            "end": _hhmm(b),
            "phase": PHASE_NAMES.get(phases[i], phases[i]),
            # Minutes between the printed clock times, so "00:14–00:39" reads 25 min.
            "minutes": int((b.replace(second=0, microsecond=0)
                            - a.replace(second=0, microsecond=0)).total_seconds() // 60),
        })
        i = j
    return runs


def hr_summary(record: Dict[str, Any], window: int = 6) -> Dict[str, Optional[float]]:
    """Mean HR, lowest rolling mean over ``window`` slots (6 = 30 min) and its start,
    plus the mean of the first hour of valid values. Gaps are skipped, never zeroed."""
    hr = _series(record, "heart_rate")
    meta = record.get("heart_rate") or {}
    valid = [v for v in hr if v is not None]
    empty = {"mean": None, "nadir_mean": None, "nadir_time": None, "first_hour_mean": None}
    if not valid:
        return empty
    step = int(meta.get("interval") or 300)
    start = _parse(meta.get("timestamp") or record["bedtime_start"])
    best = None
    for i in range(len(hr) - window + 1):
        chunk = hr[i:i + window]
        if any(v is None for v in chunk):
            continue
        m = sum(chunk) / window
        if best is None or m < best[0]:
            best = (m, i)
    first_hour = valid[: max(1, 3600 // step)]
    return {
        "mean": round(sum(valid) / len(valid), 1),
        "nadir_mean": round(best[0], 1) if best else None,
        "nadir_time": _hhmm(start + timedelta(seconds=step * best[1])) if best else None,
        "first_hour_mean": round(sum(first_hour) / len(first_hour), 1),
    }
