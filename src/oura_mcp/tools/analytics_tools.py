"""Statistical analytics tools for health data."""

import statistics
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..api.client import OuraClient
from ..utils.sleep_debt import SleepDebtTracker
from ..utils.supplement_correlation import SupplementCorrelation
from ..utils.sleep_aggregation import aggregate_sleep_sessions_by_day

from ..utils.resting_hr import extract_resting_hr_values


class AnalyticsToolProvider:
    """Provides statistical analytics tools for health data."""

    def __init__(self, oura_client: OuraClient):
        self.oura_client = oura_client
        self.sleep_debt_tracker = SleepDebtTracker()  # Auto-detect personal sleep need
        self.supplement_correlation = SupplementCorrelation()

    async def generate_statistics_report(self, days: int = 30) -> str:
        """
        Generate comprehensive statistics report across all metrics.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Formatted statistics report with insights
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Gather all data
        sleep_data = await self.oura_client.get_daily_sleep(start_date, end_date)
        # ⚠️ daily_sleep carries scores only. The resting heart rate lives in the
        # detailed sleep sessions, so fetch those too rather than reporting a score.
        sleep_sessions = aggregate_sleep_sessions_by_day(
            await self.oura_client.get_sleep(start_date, end_date)
        )
        readiness_data = await self.oura_client.get_daily_readiness(start_date, end_date)
        activity_data = await self.oura_client.get_daily_activity(start_date, end_date)

        result = f"# 📊 Health Statistics Report ({days} days)\n\n"
        result += f"**Period:** {start_date.isoformat()} to {end_date.isoformat()}\n"
        result += f"**Generated:** {date.today().isoformat()}\n\n"

        # Sleep Statistics
        if sleep_data:
            result += await self._analyze_sleep_statistics(sleep_data)

        # Readiness Statistics
        if readiness_data:
            result += await self._analyze_readiness_statistics(readiness_data, sleep_sessions)

        # Activity Statistics
        if activity_data:
            result += await self._analyze_activity_statistics(activity_data)

        # Cross-metric insights
        if sleep_data and readiness_data:
            result += await self._analyze_cross_metrics(sleep_data, readiness_data, activity_data)

        return result

    async def _analyze_sleep_statistics(self, data: List[Dict[str, Any]]) -> str:
        """Analyze sleep data statistics."""
        result = "## 😴 Sleep Statistics\n\n"

        # Extract scores
        scores = [d.get("score") for d in data if d.get("score") is not None]
        total_sleep_durations = [d.get("total_sleep_duration", 0) for d in data]
        deep_sleep_durations = [d.get("deep_sleep_duration", 0) for d in data]
        rem_sleep_durations = [d.get("rem_sleep_duration", 0) for d in data]
        efficiency_scores = [
            d.get("contributors", {}).get("efficiency")
            for d in data
            if d.get("contributors", {}).get("efficiency") is not None
        ]

        if scores:
            stats = self._calculate_statistics(scores)
            result += f"### Sleep Score\n"
            result += self._format_stats_table(stats, "points")
            result += self._add_percentile_info(scores, "sleep score")
            result += "\n"

        if total_sleep_durations:
            # Convert to hours
            sleep_hours = [d / 3600 for d in total_sleep_durations if d > 0]
            if sleep_hours:
                stats = self._calculate_statistics(sleep_hours)
                result += f"### Total Sleep Duration\n"
                result += self._format_stats_table(stats, "hours")

                # Sleep consistency (std dev as % of mean)
                consistency = (stats["std_dev"] / stats["mean"] * 100) if stats["mean"] > 0 else 0
                result += f"**Consistency:** {100 - consistency:.1f}% "
                result += f"({'High' if consistency < 10 else 'Moderate' if consistency < 20 else 'Low'})\n\n"

        if deep_sleep_durations and rem_sleep_durations:
            deep_minutes = [d / 60 for d in deep_sleep_durations if d > 0]
            rem_minutes = [d / 60 for d in rem_sleep_durations if d > 0]

            if deep_minutes:
                result += f"### Sleep Stages (Average)\n"
                result += f"- **Deep Sleep:** {statistics.mean(deep_minutes):.0f} minutes/night\n"
            if rem_minutes:
                result += f"- **REM Sleep:** {statistics.mean(rem_minutes):.0f} minutes/night\n"
            result += "\n"

        if efficiency_scores:
            stats = self._calculate_statistics(efficiency_scores)
            result += f"### Sleep Efficiency\n"
            result += self._format_stats_table(stats, "%")

        result += "---\n\n"
        return result

    async def _analyze_readiness_statistics(
        self,
        data: List[Dict[str, Any]],
        sleep_data: List[Dict[str, Any]] | None = None,
    ) -> str:
        """Analyze readiness data statistics."""
        result = "## 🎯 Readiness Statistics\n\n"

        # Extract scores
        scores = [d.get("score") for d in data if d.get("score") is not None]
        hrv_values = [
            d.get("contributors", {}).get("hrv_balance")
            for d in data
            if d.get("contributors", {}).get("hrv_balance") is not None
        ]
        # ⛔ NOT contributors.resting_heart_rate — that is a 0-100 score, not bpm.
        # Reported as "bpm" until v0.9.1, which put a median of 97 "bpm" in the
        # report while the real resting pulse was 61.
        rhr_values = extract_resting_hr_values(sleep_data or [])
        temp_values = [
            d.get("contributors", {}).get("body_temperature")
            for d in data
            if d.get("contributors", {}).get("body_temperature") is not None
        ]

        if scores:
            stats = self._calculate_statistics(scores)
            result += f"### Readiness Score\n"
            result += self._format_stats_table(stats, "points")
            result += self._add_percentile_info(scores, "readiness score")
            result += "\n"

        if hrv_values:
            stats = self._calculate_statistics(hrv_values)
            result += f"### HRV Balance\n"
            result += self._format_stats_table(stats, "points")

            # HRV variability (higher is generally better for athletes)
            result += f"**Variability:** {stats['std_dev']:.1f} points "
            result += f"({'High' if stats['std_dev'] > 15 else 'Moderate' if stats['std_dev'] > 8 else 'Low'})\n\n"

        if rhr_values:
            stats = self._calculate_statistics(rhr_values)
            result += f"### Resting Heart Rate\n"
            result += self._format_stats_table(stats, "bpm")
            result += "\n"

        if temp_values:
            stats = self._calculate_statistics(temp_values)
            result += f"### Body Temperature Deviation\n"
            result += self._format_stats_table(stats, "points")

        result += "---\n\n"
        return result

    async def _analyze_activity_statistics(self, data: List[Dict[str, Any]]) -> str:
        """Analyze activity data statistics."""
        result = "## 🏃 Activity Statistics\n\n"

        # Extract metrics
        scores = [d.get("score") for d in data if d.get("score") is not None]
        steps = [d.get("steps") for d in data if d.get("steps") is not None]
        calories = [d.get("total_calories") for d in data if d.get("total_calories") is not None]
        active_calories = [d.get("active_calories") for d in data if d.get("active_calories") is not None]

        if scores:
            stats = self._calculate_statistics(scores)
            result += f"### Activity Score\n"
            result += self._format_stats_table(stats, "points")
            result += self._add_percentile_info(scores, "activity score")
            result += "\n"

        if steps:
            stats = self._calculate_statistics(steps)
            result += f"### Daily Steps\n"
            result += self._format_stats_table(stats, "steps")

            # Active days (>10k steps)
            active_days = sum(1 for s in steps if s >= 10000)
            result += f"**Active Days (≥10k steps):** {active_days}/{len(steps)} ({active_days/len(steps)*100:.0f}%)\n\n"

        if calories and active_calories:
            total_stats = self._calculate_statistics(calories)
            active_stats = self._calculate_statistics(active_calories)

            result += f"### Calories\n"
            result += f"- **Total (avg):** {total_stats['mean']:.0f} kcal/day\n"
            result += f"- **Active (avg):** {active_stats['mean']:.0f} kcal/day\n"
            result += f"- **Activity Ratio:** {active_stats['mean']/total_stats['mean']*100:.1f}%\n\n"

        result += "---\n\n"
        return result

    async def _analyze_cross_metrics(
        self,
        sleep_data: List[Dict[str, Any]],
        readiness_data: List[Dict[str, Any]],
        activity_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Analyze relationships between metrics."""
        result = "## 🔗 Cross-Metric Insights\n\n"

        # Sleep vs Readiness
        sleep_scores = [d.get("score") for d in sleep_data if d.get("score") is not None]
        readiness_scores = [d.get("score") for d in readiness_data if d.get("score") is not None]

        if len(sleep_scores) >= 7 and len(readiness_scores) >= 7:
            # Align datasets
            min_len = min(len(sleep_scores), len(readiness_scores))
            sleep_aligned = sleep_scores[-min_len:]
            readiness_aligned = readiness_scores[-min_len:]

            correlation = self._calculate_correlation(sleep_aligned, readiness_aligned)

            result += f"### Sleep ↔ Readiness Relationship\n"
            result += f"**Correlation:** {correlation:+.3f} "
            result += f"({'Strong' if abs(correlation) > 0.7 else 'Moderate' if abs(correlation) > 0.4 else 'Weak'})\n"

            if correlation > 0.5:
                result += "*Your readiness closely follows your sleep quality*\n\n"
            elif correlation > 0.3:
                result += "*Your readiness is influenced by sleep, but other factors matter too*\n\n"
            else:
                result += "*Your readiness is driven by multiple factors beyond sleep*\n\n"

        # Weekly patterns
        if len(sleep_scores) >= 14:
            result += await self._analyze_weekly_patterns(sleep_data, readiness_data, activity_data)

        # Trend detection
        result += await self._analyze_trends(sleep_data, readiness_data)

        return result

    async def _analyze_weekly_patterns(
        self,
        sleep_data: List[Dict[str, Any]],
        readiness_data: List[Dict[str, Any]],
        activity_data: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Analyze weekly patterns in data."""
        result = "### 📅 Weekly Patterns\n\n"

        # Group by day of week
        from datetime import datetime

        day_groups = {i: [] for i in range(7)}  # 0=Monday, 6=Sunday

        for record in sleep_data:
            day_str = record.get("day")
            score = record.get("score")
            if day_str and score:
                day_date = datetime.fromisoformat(day_str)
                weekday = day_date.weekday()
                day_groups[weekday].append(score)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Find best and worst days
        day_averages = {}
        for day, scores in day_groups.items():
            if scores:
                day_averages[day] = statistics.mean(scores)

        if day_averages:
            best_day = max(day_averages, key=day_averages.get)
            worst_day = min(day_averages, key=day_averages.get)

            result += f"**Best Sleep Day:** {day_names[best_day]} (avg: {day_averages[best_day]:.0f})\n"
            result += f"**Worst Sleep Day:** {day_names[worst_day]} (avg: {day_averages[worst_day]:.0f})\n\n"

        return result

    async def _analyze_trends(
        self,
        sleep_data: List[Dict[str, Any]],
        readiness_data: List[Dict[str, Any]]
    ) -> str:
        """Analyze trends over time."""
        result = "### 📈 Trends\n\n"

        # Sleep trend
        sleep_scores = [d.get("score") for d in sleep_data if d.get("score") is not None]
        if len(sleep_scores) >= 7:
            # Simple linear trend
            first_half = sleep_scores[:len(sleep_scores)//2]
            second_half = sleep_scores[len(sleep_scores)//2:]

            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            trend = second_avg - first_avg

            result += f"**Sleep Trend:** "
            if abs(trend) < 2:
                result += f"Stable (~{trend:+.1f} points)\n"
            elif trend > 0:
                result += f"📈 Improving (+{trend:.1f} points)\n"
            else:
                result += f"📉 Declining ({trend:.1f} points)\n"

        # Readiness trend
        readiness_scores = [d.get("score") for d in readiness_data if d.get("score") is not None]
        if len(readiness_scores) >= 7:
            first_half = readiness_scores[:len(readiness_scores)//2]
            second_half = readiness_scores[len(readiness_scores)//2:]

            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            trend = second_avg - first_avg

            result += f"**Readiness Trend:** "
            if abs(trend) < 2:
                result += f"Stable (~{trend:+.1f} points)\n"
            elif trend > 0:
                result += f"📈 Improving (+{trend:.1f} points)\n"
            else:
                result += f"📉 Declining ({trend:.1f} points)\n"

        result += "\n"
        return result

    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical measures."""
        if not values:
            return {}

        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "count": len(values)
        }

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        covariance = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / len(x)
        std_x = statistics.stdev(x)
        std_y = statistics.stdev(y)

        if std_x == 0 or std_y == 0:
            return 0.0

        return covariance / (std_x * std_y)

    def _format_stats_table(self, stats: Dict[str, float], unit: str) -> str:
        """Format statistics as a table."""
        if not stats:
            return "*No data available*\n\n"

        result = ""
        result += f"- **Mean:** {stats['mean']:.1f} {unit}\n"
        result += f"- **Median:** {stats['median']:.1f} {unit}\n"
        result += f"- **Std Dev:** {stats['std_dev']:.1f} {unit}\n"
        result += f"- **Range:** {stats['min']:.1f} - {stats['max']:.1f} {unit}\n"
        result += f"- **Data Points:** {stats['count']}\n\n"
        return result

    def _add_percentile_info(self, values: List[float], metric_name: str) -> str:
        """Add percentile interpretation."""
        if not values:
            return ""

        sorted_values = sorted(values)
        p25 = sorted_values[len(sorted_values) // 4]
        p75 = sorted_values[3 * len(sorted_values) // 4]

        result = f"**Performance Distribution:**\n"
        result += f"- Top 25%: ≥{p75:.0f}\n"
        result += f"- Bottom 25%: ≤{p25:.0f}\n"

        return result

    async def analyze_sleep_debt(self, days: int = 30) -> str:
        """
        Analyze accumulated sleep debt over time.

        Args:
            days: Number of days to analyze (default: 30)

        Returns:
            Formatted sleep debt report with recovery recommendations
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get sleep data - use get_sleep() which has accurate durations
        sleep_sessions = await self.oura_client.get_sleep(start_date, end_date)

        if not sleep_sessions:
            return "⚠️ No sleep data available for debt analysis"

        # Get readiness data for personal sleep need calculation
        readiness_data = await self.oura_client.get_daily_readiness(start_date, end_date)

        # Aggregate biphasic/multiple sleep sessions per day
        sleep_data = aggregate_sleep_sessions_by_day(sleep_sessions)

        # Generate comprehensive debt report (includes personal sleep need detection)
        report = self.sleep_debt_tracker.generate_debt_report(sleep_data, days, readiness_data)

        # Add efficiency-based debt analysis
        efficiency_debt = self.sleep_debt_tracker.calculate_sleep_efficiency_debt(sleep_data)

        if efficiency_debt.get("status") == "calculated":
            report += "\n## 🎨 Sleep Quality Debt\n\n"
            report += f"*Based on sleep efficiency (target: 85%+)*\n\n"
            report += f"- **Average Efficiency:** {efficiency_debt['avg_efficiency']}%\n"
            report += f"- **Quality Debt:** ~{efficiency_debt['quality_debt_hours_equivalent']} hours equivalent\n"
            report += f"- **Nights with Poor Efficiency:** {efficiency_debt['nights_poor_efficiency']}/{len(sleep_data)}\n\n"

            if efficiency_debt['avg_efficiency'] < 85:
                report += "⚠️ **Low sleep efficiency detected**\n"
                report += "Consider: sleep environment improvements, stress reduction, or consulting a sleep specialist.\n\n"

        return report

    async def analyze_supplement_correlation(
        self,
        days: int = 60,
        min_occurrences: int = 3,
        top_n: int = 10
    ) -> str:
        """
        Analyze correlation between tags (supplements, interventions) and sleep metrics.

        Args:
            days: Number of days to analyze (default: 60)
            min_occurrences: Minimum tag occurrences to analyze (default: 3)
            top_n: Number of top results to show in detail (default: 10)

        Returns:
            Formatted supplement correlation report
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get sleep and tag data
        sleep_sessions = await self.oura_client.get_sleep(start_date, end_date)
        tags_data = await self.oura_client.get_tags(start_date, end_date)

        if not sleep_sessions:
            return "⚠️ No sleep data available for correlation analysis"

        # Aggregate biphasic/multiple sleep sessions per day
        sleep_data = aggregate_sleep_sessions_by_day(sleep_sessions)

        if not tags_data:
            return "⚠️ No tags found. Please add tags in the Oura app to track supplements and interventions."

        # Perform correlation analysis
        analysis = self.supplement_correlation.analyze_tag_correlations(
            sleep_data,
            tags_data,
            min_occurrences=min_occurrences
        )

        return self.supplement_correlation.generate_correlation_report(analysis, top_n=top_n)
