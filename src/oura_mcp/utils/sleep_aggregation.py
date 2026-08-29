"""
Sleep Aggregation Utilities

Handles aggregation of multiple sleep sessions per day (e.g., biphasic sleep,
naps) into consolidated daily sleep data for accurate analysis.
"""

from datetime import datetime
from typing import Dict, List
from collections import defaultdict


def aggregate_sleep_sessions_by_day(sleep_sessions: List[Dict]) -> List[Dict]:
    """
    Aggregate multiple sleep sessions per day into single daily records.

    This handles biphasic sleep, naps, and other multi-session sleep patterns
    by combining all sessions from the same calendar day.

    Args:
        sleep_sessions: List of sleep session data from Oura API

    Returns:
        List of aggregated daily sleep records with combined durations
    """
    if not sleep_sessions:
        return []

    # Group sessions by day
    sessions_by_day = defaultdict(list)

    for session in sleep_sessions:
        if not isinstance(session, dict):
            continue

        day = session.get('day')
        if not day:
            continue

        sessions_by_day[day].append(session)

    # Aggregate sessions for each day
    aggregated = []

    for day, sessions in sorted(sessions_by_day.items()):
        aggregated_session = _aggregate_sessions(day, sessions)
        if aggregated_session:
            aggregated.append(aggregated_session)

    return aggregated


def _aggregate_sessions(day: str, sessions: List[Dict]) -> Dict:
    """
    Aggregate multiple sessions from the same day into a single record.

    Strategy:
    - Sum: total_sleep_duration, deep_sleep_duration, rem_sleep_duration, light_sleep_duration
    - Average: efficiency, score, restlessness, heart rate metrics
    - Take first: bedtime_start
    - Take last: bedtime_end
    - Min: latency (first session's sleep onset)
    - Count: number of sessions combined
    """
    if not sessions:
        return None

    # Sort by bedtime to get chronological order
    sorted_sessions = sorted(
        sessions,
        key=lambda s: s.get('bedtime_start', '')
    )

    # Initialize aggregated values
    aggregated = {
        'day': day,
        'combined_sessions': len(sorted_sessions)
    }

    # Fields to sum
    sum_fields = [
        'total_sleep_duration',
        'deep_sleep_duration',
        'rem_sleep_duration',
        'light_sleep_duration',
        'awake_time'
    ]

    # Fields to average
    avg_fields = [
        'efficiency',
        'score',
        'restlessness',
        'average_heart_rate',
        'lowest_heart_rate'
    ]

    # Sum durations
    for field in sum_fields:
        total = 0
        count = 0
        for session in sorted_sessions:
            value = session.get(field)
            if value is not None:
                total += value
                count += 1

        if count > 0:
            aggregated[field] = total

    # Average metrics
    #
    # ⛔ A zero is not a measurement here. Short sessions (naps) come back with
    # average_heart_rate = 0, and averaging that in produced values like 22.6 bpm
    # from a real 67.8 — a third of the truth, because two of three sessions
    # contributed a 0. The old guard tested `is not None`, and 0 passes that.
    #
    # Fields where 0 is a legitimate value (restlessness can genuinely be 0) keep
    # counting it; only the physiological rates are guarded.
    nonzero_only = {'average_heart_rate', 'lowest_heart_rate'}

    for field in avg_fields:
        total = 0
        count = 0
        for session in sorted_sessions:
            value = session.get(field)
            if value is None:
                continue
            if field in nonzero_only and value <= 0:
                continue
            total += value
            count += 1

        if count > 0:
            aggregated[field] = total / count

    # Take first bedtime (start of first session)
    aggregated['bedtime_start'] = sorted_sessions[0].get('bedtime_start')

    # Take last bedtime end (end of last session)
    aggregated['bedtime_end'] = sorted_sessions[-1].get('bedtime_end')

    # Use minimum latency (first session's sleep onset)
    latencies = [s.get('latency') for s in sorted_sessions if s.get('latency') is not None]
    if latencies:
        aggregated['latency'] = min(latencies)

    # Time in bed = sum of all sessions
    time_in_bed_values = [s.get('time_in_bed') for s in sorted_sessions if s.get('time_in_bed') is not None]
    if time_in_bed_values:
        aggregated['time_in_bed'] = sum(time_in_bed_values)

    # Recalculate efficiency if we have duration and time in bed
    if aggregated.get('total_sleep_duration') and aggregated.get('time_in_bed'):
        aggregated['efficiency'] = (aggregated['total_sleep_duration'] / aggregated['time_in_bed']) * 100

    # Heart rate data (take from longest session)
    longest_session = max(sorted_sessions, key=lambda s: s.get('total_sleep_duration', 0))

    heart_rate_fields = [
        'heart_rate',  # May be dict or value
        'hrv',
        'breath_average',
        'temperature_delta',
        'temperature_trend_deviation'
    ]

    for field in heart_rate_fields:
        value = longest_session.get(field)
        if value is not None:
            aggregated[field] = value

    # Movement metrics (average)
    movement_fields = ['movement_30_sec']
    for field in movement_fields:
        values = [s.get(field) for s in sorted_sessions if s.get(field) is not None]
        if values:
            # For movement data, concatenate or take longest
            aggregated[field] = longest_session.get(field)

    # Sleep phase type (use most common or longest)
    types = [s.get('type') for s in sorted_sessions if s.get('type')]
    if types:
        # If any session is 'long_sleep', prefer that
        if 'long_sleep' in types:
            aggregated['type'] = 'long_sleep'
        else:
            aggregated['type'] = types[0]

    # Add metadata about aggregation
    if len(sorted_sessions) > 1:
        aggregated['is_aggregated'] = True
        aggregated['session_details'] = [
            {
                'start': s.get('bedtime_start'),
                'duration': s.get('total_sleep_duration', 0) / 3600,
                'type': s.get('type')
            }
            for s in sorted_sessions
        ]
    else:
        aggregated['is_aggregated'] = False

    return aggregated


def format_aggregation_summary(aggregated_session: Dict) -> str:
    """
    Format a human-readable summary of an aggregated sleep session.

    Args:
        aggregated_session: Aggregated session data

    Returns:
        Formatted string describing the aggregation
    """
    if not aggregated_session.get('is_aggregated'):
        duration = aggregated_session.get('total_sleep_duration', 0) / 3600
        return f"{duration:.1f}h (single session)"

    combined_count = aggregated_session.get('combined_sessions', 0)
    total_duration = aggregated_session.get('total_sleep_duration', 0) / 3600

    lines = [f"{total_duration:.1f}h (combined from {combined_count} sessions)"]

    # Add session details if available
    session_details = aggregated_session.get('session_details', [])
    if session_details:
        lines.append("Sessions:")
        for i, detail in enumerate(session_details, 1):
            duration = detail.get('duration', 0)
            session_type = detail.get('type', 'sleep')
            lines.append(f"  {i}. {duration:.1f}h ({session_type})")

    return "\n".join(lines)
