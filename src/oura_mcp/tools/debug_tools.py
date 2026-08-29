"""Debug and utility tools."""

import json
from datetime import date, timedelta
from typing import Any, Dict

from ..api.client import OuraClient
from ..utils.weekly_report import WeeklyReportGenerator
from ..utils.sleep_aggregation import (
    aggregate_sleep_sessions_by_day,
    merge_daily_sleep_scores,
)


class DebugToolProvider:
    """Provides debug and utility tools."""

    def __init__(self, oura_client: OuraClient):
        self.oura_client = oura_client
        self.weekly_report_generator = WeeklyReportGenerator()

    async def generate_daily_brief(self) -> str:
        """Generate daily health brief."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Gather all data
        # Sleep uses yesterday's date (Oura convention)
        all_sleep_periods = await self.oura_client.get_sleep(yesterday - timedelta(days=1), today)
        sleep_periods = [p for p in all_sleep_periods if p.get("day") == yesterday.isoformat()]

        sleep_summary = await self.oura_client.get_daily_sleep(today, today)
        readiness_data = await self.oura_client.get_daily_readiness(today, today)
        activity_data = await self.oura_client.get_daily_activity(today, today)

        brief = "# Daily Health Brief\n\n"
        brief += f"**Date:** {today.isoformat()}\n\n"

        # Sleep
        if sleep_periods:
            # Aggregate all sleep periods
            total_sleep = sum(p.get("total_sleep_duration", 0) for p in sleep_periods)
            deep_sleep = sum(p.get("deep_sleep_duration", 0) for p in sleep_periods)
            rem_sleep = sum(p.get("rem_sleep_duration", 0) for p in sleep_periods)

            score = sleep_summary[0].get("score", 0) if sleep_summary else 0

            brief += f"## Sleep (Score: {score})\n"
            brief += f"- Total: {total_sleep // 3600}h {(total_sleep % 3600) // 60}m\n"
            brief += f"- Deep: {deep_sleep // 60}m\n"
            brief += f"- REM: {rem_sleep // 60}m\n"
            if len(sleep_periods) > 1:
                brief += f"- Periods: {len(sleep_periods)} (biphasic/polyphasic)\n"
            brief += "\n"
        else:
            brief += f"## Sleep\n*No sleep data available*\n\n"

        # Readiness
        if readiness_data:
            readiness = readiness_data[-1]
            score = readiness.get("score")
            brief += f"## Readiness (Score: {score})\n"
            contributors = readiness.get("contributors", {})
            brief += f"- HRV Balance: {contributors.get('hrv_balance', 'N/A')}\n"
            brief += f"- Temperature: {contributors.get('body_temperature', 'N/A')}\n\n"

        # Activity
        if activity_data:
            activity = activity_data[-1]
            score = activity.get("score")
            brief += f"## Activity (Score: {score})\n"
            brief += f"- Steps: {activity.get('steps', 0):,}\n"
            brief += f"- Calories: {activity.get('total_calories', 0)}\n\n"

        return brief

    async def analyze_sleep_trend(self, days: int) -> str:
        """Analyze sleep trend."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        data = await self.oura_client.get_daily_sleep(start_date, end_date)

        if not data:
            return f"No sleep data available for the last {days} days"

        scores = [d.get("score") for d in data if d.get("score") is not None]

        if not scores:
            return "No sleep scores available"

        avg_score = sum(scores) / len(scores)
        trend = "improving" if scores[-1] > avg_score else "declining"

        analysis = f"# Sleep Trend Analysis ({days} days)\n\n"
        analysis += f"- **Average Score:** {avg_score:.1f}\n"
        analysis += f"- **Latest Score:** {scores[-1]}\n"
        analysis += f"- **Trend:** {trend}\n"
        analysis += f"- **Data Points:** {len(scores)}\n"

        return analysis

    async def get_raw_sleep_data(self, days: int) -> str:
        """Get raw sleep data from Oura API for debugging."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        data = await self.oura_client.get_daily_sleep(start_date, end_date)

        if not data:
            return f"No sleep data available for the last {days} days"

        result = f"# Raw Oura Sleep Data (Last {days} days)\n\n"
        result += f"**Retrieved {len(data)} records**\n\n"

        for record in data:
            result += f"## Date: {record.get('day')}\n"
            result += f"```json\n{json.dumps(record, indent=2)}\n```\n\n"

        return result

    async def get_hrv_trend(self, days: int) -> str:
        """Get raw HRV values in milliseconds from the detailed sleep endpoint."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        data = await self.oura_client.get_sleep(start_date, end_date)

        if not data:
            return f"No sleep data available for the last {days} days"

        # Filter to main sleep sessions only (type == 'long_sleep'), skip naps
        main_sessions = [d for d in data if d.get("type") in ("long_sleep", "sleep")]
        if not main_sessions:
            main_sessions = data

        result = f"# HRV Trend — Raw Values in ms (Last {days} days)\n\n"
        result += "| Datum | HRV Ø (ms) | Ruhepuls (bpm) | Schlaf gesamt | Tiefschlaf | REM |\n"
        result += "|---|---|---|---|---|---|\n"

        hrv_values = []
        for session in sorted(main_sessions, key=lambda x: x.get("day", "")):
            day = session.get("day", "?")
            hrv = session.get("average_hrv")
            hr = session.get("average_heart_rate")
            lowest_hr = session.get("lowest_heart_rate")
            total = session.get("total_sleep_duration", 0)
            deep = session.get("deep_sleep_duration", 0)
            rem = session.get("rem_sleep_duration", 0)

            hrv_str = f"{hrv:.0f}" if hrv is not None else "—"
            hr_str = f"{lowest_hr}" if lowest_hr is not None else (f"{hr:.0f}" if hr is not None else "—")
            total_str = f"{total // 3600}h{(total % 3600) // 60}m" if total else "—"
            deep_str = f"{deep // 60}m" if deep else "—"
            rem_str = f"{rem // 60}m" if rem else "—"

            result += f"| {day} | {hrv_str} | {hr_str} | {total_str} | {deep_str} | {rem_str} |\n"
            if hrv is not None:
                hrv_values.append(hrv)

        if hrv_values:
            avg = sum(hrv_values) / len(hrv_values)
            first_half = hrv_values[:len(hrv_values)//2]
            second_half = hrv_values[len(hrv_values)//2:]
            avg_first = sum(first_half) / len(first_half) if first_half else 0
            avg_second = sum(second_half) / len(second_half) if second_half else 0
            trend_dir = "📈 steigend" if avg_second > avg_first else "📉 fallend"

            result += f"\n**Gesamt-Ø:** {avg:.1f} ms · "
            result += f"**Erste Hälfte Ø:** {avg_first:.1f} ms · "
            result += f"**Zweite Hälfte Ø:** {avg_second:.1f} ms · "
            result += f"**Trend:** {trend_dir} ({avg_second - avg_first:+.1f} ms)\n"

        return result

    async def generate_weekly_report(
        self,
        weeks_ago: int = 0,
        include_previous_week: bool = True
    ) -> str:
        """
        Generate comprehensive weekly health report.

        Args:
            weeks_ago: Number of weeks ago to report (0 = current week, 1 = last week, etc.)
            include_previous_week: Include week-over-week comparison

        Returns:
            Formatted weekly report
        """
        # Calculate date range
        today = date.today()
        days_since_monday = today.weekday()  # Monday = 0

        # Calculate start and end of target week
        week_start = today - timedelta(days=days_since_monday) - timedelta(weeks=weeks_ago)
        week_end = week_start + timedelta(days=6)

        # Get data for the week
        sleep_sessions = await self.oura_client.get_sleep(week_start, week_end)
        readiness_data = await self.oura_client.get_daily_readiness(week_start, week_end)
        activity_data = await self.oura_client.get_daily_activity(week_start, week_end)

        # Aggregate biphasic/multiple sleep sessions per day
        daily_sleep = await self.oura_client.get_daily_sleep(week_start, week_end)
        sleep_data = merge_daily_sleep_scores(
            aggregate_sleep_sessions_by_day(sleep_sessions), daily_sleep
        )

        # Get previous week data if requested
        previous_week_data = None
        if include_previous_week:
            prev_week_start = week_start - timedelta(days=7)
            prev_week_end = prev_week_start + timedelta(days=6)

            prev_sleep_sessions = await self.oura_client.get_sleep(prev_week_start, prev_week_end)
            prev_readiness = await self.oura_client.get_daily_readiness(prev_week_start, prev_week_end)
            prev_activity = await self.oura_client.get_daily_activity(prev_week_start, prev_week_end)

            # Aggregate previous week sleep sessions
            prev_daily_sleep = await self.oura_client.get_daily_sleep(
                prev_week_start, prev_week_end
            )
            prev_sleep = merge_daily_sleep_scores(
                aggregate_sleep_sessions_by_day(prev_sleep_sessions), prev_daily_sleep
            )

            # Analyze previous week
            prev_sleep_metrics = self.weekly_report_generator._analyze_sleep_metrics(prev_sleep)
            prev_readiness_metrics = self.weekly_report_generator._analyze_readiness_metrics(
                prev_readiness, prev_sleep
            )
            prev_activity_metrics = self.weekly_report_generator._analyze_activity_metrics(prev_activity)

            previous_week_data = {
                'sleep': prev_sleep_metrics,
                'readiness': prev_readiness_metrics,
                'activity': prev_activity_metrics
            }

        # Generate report
        report = self.weekly_report_generator.generate_weekly_report(
            sleep_data,
            readiness_data,
            activity_data,
            week_start,
            week_end,
            previous_week_data
        )

        return self.weekly_report_generator.format_weekly_report(report)
