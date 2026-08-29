"""Intelligence tools for health analysis."""

import statistics
from datetime import date, timedelta
from typing import Any, Dict

from ..api.client import OuraClient
from ..utils.baselines import BaselineManager
from ..utils.anomalies import AnomalyDetector
from ..utils.interpretation import InterpretationEngine
from ..utils.bedtime_calculator import BedtimeCalculator
from ..utils.alert_system import AlertSystem
from ..utils.sleep_aggregation import aggregate_sleep_sessions_by_day
from ..utils.illness_detection import IllnessDetector
from ..utils.chronotype_analysis import ChronotypeAnalyzer


class IntelligenceToolProvider:
    """Provides intelligence and analysis tools."""

    def __init__(
        self,
        oura_client: OuraClient,
        baseline_manager: BaselineManager,
        anomaly_detector: AnomalyDetector,
        interpreter: InterpretationEngine
    ):
        self.oura_client = oura_client
        self.baseline_manager = baseline_manager
        self.anomaly_detector = anomaly_detector
        self.interpreter = interpreter
        self.bedtime_calculator = BedtimeCalculator()
        self.alert_system = AlertSystem()
        self.illness_detector = IllnessDetector(baseline_days=30)
        self.chronotype_analyzer = ChronotypeAnalyzer(min_days=14)

    async def detect_recovery_status(self) -> str:
        """Detect current recovery status based on multiple signals."""
        today = date.today()

        # Gather all relevant data
        readiness_data = await self.oura_client.get_daily_readiness(today, today)
        sleep_data = await self.oura_client.get_daily_sleep(today, today)

        if not readiness_data:
            return "⚠️ No readiness data available for today"

        readiness = readiness_data[-1]
        contributors = readiness.get("contributors", {})

        # Extract key metrics
        readiness_score = readiness.get("score", 0)
        hrv_balance = contributors.get("hrv_balance", 50)
        temp_score = contributors.get("body_temperature", 100)

        sleep_score = sleep_data[-1].get("score", 70) if sleep_data else 70

        # Get baselines for context
        baseline_start = today - timedelta(days=30)
        baseline_readiness = await self.oura_client.get_daily_readiness(baseline_start, today)
        baselines = self.baseline_manager.calculate_readiness_baselines(baseline_readiness)

        # Interpret recovery state
        recovery_state = self.interpreter.interpret_recovery_state(
            readiness=readiness_score,
            hrv_balance=hrv_balance,
            resting_hr_deviation=0,  # We'd need to calculate this from baseline
            sleep_score=sleep_score,
            temperature_score=temp_score
        )

        # Format output
        result = "# 🏥 Recovery Status Assessment\n\n"
        result += f"**Overall State:** {recovery_state['emoji']} {recovery_state['state']}\n"
        result += f"**Recovery Score:** {recovery_state['recovery_score']}/100\n"
        result += f"**Confidence:** {recovery_state['confidence']*100:.0f}%\n\n"

        result += f"## Description\n{recovery_state['description']}\n\n"

        result += f"## Training Recommendation\n{recovery_state['training_recommendation']}\n\n"

        result += "## Contributing Signals\n\n"
        for signal_name, signal_data in recovery_state['signals'].items():
            name_display = signal_name.replace("_", " ").title()
            if 'value' in signal_data:
                result += f"- **{name_display}:** {signal_data['value']} (weight: {signal_data['weight']}, impact: {signal_data['impact']})\n"
            else:
                result += f"- **{name_display}:** {signal_data.get('deviation', 'N/A')} bpm deviation (weight: {signal_data['weight']})\n"

        result += "\n"

        # Add HRV interpretation
        hrv_interp = self.interpreter.interpret_hrv_balance(
            hrv_balance,
            baselines.get("hrv_balance", {}).get("mean")
        )
        result += f"## HRV Analysis\n"
        result += f"{hrv_interp['emoji']} **Status:** {hrv_interp['status']}\n"
        result += f"- {hrv_interp['description']}\n"
        result += f"- {hrv_interp['meaning']}\n"
        result += f"- **Implications:** {hrv_interp['implications']}\n"

        if 'baseline_status' in hrv_interp:
            result += f"- **Baseline:** {hrv_interp['baseline_status']}\n"

        return result

    async def assess_training_readiness(self, training_type: str) -> str:
        """Assess readiness for specific training type."""
        today = date.today()

        # Get recovery state first
        readiness_data = await self.oura_client.get_daily_readiness(today, today)
        sleep_data = await self.oura_client.get_daily_sleep(today, today)

        if not readiness_data:
            return "⚠️ No readiness data available for today"

        readiness = readiness_data[-1]
        contributors = readiness.get("contributors", {})
        readiness_score = readiness.get("score", 0)

        # Build recovery state
        recovery_state = self.interpreter.interpret_recovery_state(
            readiness=readiness_score,
            hrv_balance=contributors.get("hrv_balance", 50),
            resting_hr_deviation=0,
            sleep_score=sleep_data[-1].get("score", 70) if sleep_data else 70,
            temperature_score=contributors.get("body_temperature", 100)
        )

        # Get training-specific assessment
        assessment = self.interpreter.assess_training_readiness(
            readiness=readiness_score,
            recovery_state=recovery_state,
            training_type=training_type
        )

        # Format output
        result = f"# 🏋️ Training Readiness Assessment\n\n"
        result += f"**Training Type:** {assessment['training_type']}\n"
        result += f"**Recommendation:** {assessment['emoji']} {assessment['go_nogo']}\n"
        result += f"**Confidence:** {assessment['confidence']}\n\n"

        result += f"## Readiness Scores\n"
        result += f"- **Readiness Score:** {assessment['readiness_score']}/100\n"
        result += f"- **Recovery Score:** {assessment['recovery_score']}/100\n\n"

        result += f"## Recommendations\n"
        result += f"- **Intensity:** {assessment['intensity']}\n"
        result += f"- **Duration:** {assessment['duration']}\n\n"

        if assessment['modifications']:
            result += f"## Suggested Modifications\n"
            for mod in assessment['modifications']:
                result += f"- {mod}\n"
            result += "\n"

        result += f"## Limiting Factors\n"
        for factor in assessment['key_factors']:
            result += f"- {factor}\n"

        return result

    async def correlate_metrics(self, metric1: str, metric2: str, days: int) -> str:
        """Find correlations between two metrics."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Gather data
        sleep_data = await self.oura_client.get_daily_sleep(start_date, end_date)
        readiness_data = await self.oura_client.get_daily_readiness(start_date, end_date)
        activity_data = await self.oura_client.get_daily_activity(start_date, end_date)

        # Extract metric values
        def extract_metric(records, metric_name):
            values = []

            # List of contributor metrics (appear in contributors dict)
            sleep_contributors = ["deep_sleep", "rem_sleep", "light_sleep", "total_sleep",
                                 "efficiency", "restfulness", "latency", "timing"]
            readiness_contributors = ["hrv_balance", "resting_heart_rate", "body_temperature",
                                     "activity_balance", "previous_day_activity", "previous_night",
                                     "recovery_index", "sleep_balance", "sleep_regularity"]
            activity_contributors = ["meet_daily_targets", "move_every_hour", "recovery_time",
                                    "stay_active", "training_frequency", "training_volume"]

            for record in records:
                val = None

                # Check for score fields
                if metric_name == "sleep_score":
                    val = record.get("score")
                elif metric_name == "readiness_score":
                    val = record.get("score")
                elif metric_name == "activity_score":
                    val = record.get("score")
                # Check contributors
                elif metric_name in sleep_contributors or metric_name in readiness_contributors or metric_name in activity_contributors:
                    val = record.get("contributors", {}).get(metric_name)
                # Check direct fields (like steps, calories)
                else:
                    val = record.get(metric_name)

                if val is not None:
                    values.append(float(val))
            return values

        # Determine which dataset to use for each metric
        def get_data_for_metric(metric):
            if "sleep" in metric:
                return sleep_data
            elif "readiness" in metric or "hrv" in metric or "heart_rate" in metric or "temperature" in metric:
                return readiness_data
            elif "activity" in metric or "steps" in metric:
                return activity_data
            else:
                return readiness_data  # Default

        data1 = get_data_for_metric(metric1)
        data2 = get_data_for_metric(metric2)

        values1 = extract_metric(data1, metric1)
        values2 = extract_metric(data2, metric2)

        if not values1 or not values2:
            return f"⚠️ Insufficient data for correlation analysis\n- {metric1}: {len(values1)} values\n- {metric2}: {len(values2)} values"

        # Align datasets (use minimum length)
        min_len = min(len(values1), len(values2))
        values1 = values1[-min_len:]
        values2 = values2[-min_len:]

        # Calculate correlation (Pearson)
        if min_len < 2:
            return "⚠️ Not enough data points for correlation analysis (need at least 2)"

        mean1 = statistics.mean(values1)
        mean2 = statistics.mean(values2)

        covariance = sum((x - mean1) * (y - mean2) for x, y in zip(values1, values2)) / min_len
        std1 = statistics.stdev(values1) if len(values1) > 1 else 0
        std2 = statistics.stdev(values2) if len(values2) > 1 else 0

        if std1 == 0 or std2 == 0:
            correlation = 0
        else:
            correlation = covariance / (std1 * std2)

        # Interpret correlation
        if abs(correlation) > 0.7:
            strength = "Strong"
            emoji = "🔴"
        elif abs(correlation) > 0.5:
            strength = "Moderate"
            emoji = "🟡"
        elif abs(correlation) > 0.3:
            strength = "Weak"
            emoji = "🟢"
        else:
            strength = "Very Weak/None"
            emoji = "⚪"

        direction = "positive" if correlation > 0 else "negative"

        # Format output
        result = f"# 📊 Correlation Analysis ({days} days)\n\n"
        result += f"**Metrics:**\n"
        result += f"- {metric1.replace('_', ' ').title()}\n"
        result += f"- {metric2.replace('_', ' ').title()}\n\n"

        result += f"## Results\n"
        result += f"{emoji} **Correlation:** {correlation:+.3f}\n"
        result += f"**Strength:** {strength}\n"
        result += f"**Direction:** {direction}\n"
        result += f"**Data Points:** {min_len}\n\n"

        result += f"## Interpretation\n"
        if abs(correlation) > 0.5:
            result += f"These metrics show a {strength.lower()} {direction} relationship.\n"
            if correlation > 0:
                result += f"When {metric1} increases, {metric2} tends to increase as well.\n"
            else:
                result += f"When {metric1} increases, {metric2} tends to decrease.\n"
        else:
            result += f"These metrics show little to no clear relationship.\n"

        result += f"\n## Statistics\n"
        result += f"**{metric1.replace('_', ' ').title()}:**\n"
        result += f"- Mean: {mean1:.1f}\n"
        result += f"- Std Dev: {std1:.1f}\n"
        result += f"- Range: {min(values1):.1f} - {max(values1):.1f}\n\n"

        result += f"**{metric2.replace('_', ' ').title()}:**\n"
        result += f"- Mean: {mean2:.1f}\n"
        result += f"- Std Dev: {std2:.1f}\n"
        result += f"- Range: {min(values2):.1f} - {max(values2):.1f}\n"

        return result

    async def detect_anomalies(self, metric_type: str, days: int) -> str:
        """Detect anomalies in specified metric type."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        if metric_type == "sleep":
            current_data = await self.oura_client.get_daily_sleep(end_date, end_date)
            recent_data = await self.oura_client.get_daily_sleep(start_date, end_date)

            if not current_data or not recent_data:
                return "⚠️ Insufficient sleep data for anomaly detection"

            anomalies = self.anomaly_detector.detect_sleep_anomalies(
                current_data[-1],
                recent_data
            )

        elif metric_type == "readiness":
            current_data = await self.oura_client.get_daily_readiness(end_date, end_date)
            recent_data = await self.oura_client.get_daily_readiness(start_date, end_date)

            if not current_data or not recent_data:
                return "⚠️ Insufficient readiness data for anomaly detection"

            anomalies = self.anomaly_detector.detect_readiness_anomalies(
                current_data[-1],
                recent_data
            )

        else:
            return f"⚠️ Anomaly detection not yet implemented for {metric_type}"

        # Format output
        result = f"# 🔍 Anomaly Detection Report\n\n"
        result += f"**Period:** Last {days} days\n"
        result += f"**Metric Type:** {metric_type.title()}\n"
        result += f"**Date:** {end_date.isoformat()}\n\n"

        result += self.anomaly_detector.format_anomalies_report(anomalies)

        return result

    async def calculate_optimal_bedtime(
        self,
        days: int = 30,
        top_percentile: float = 0.25
    ) -> str:
        """
        Calculate optimal bedtime based on historical best nights.

        Args:
            days: Number of days to analyze (default: 30)
            top_percentile: Fraction of best nights to analyze (default: 0.25 = top 25%)

        Returns:
            Formatted bedtime recommendation report
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get sleep sessions
        sleep_sessions = await self.oura_client.get_sleep(start_date, end_date)

        if not sleep_sessions:
            return "⚠️ No sleep data available for analysis"

        # Aggregate biphasic/multiple sleep sessions per day
        sleep_data = aggregate_sleep_sessions_by_day(sleep_sessions)

        # Analyze and generate recommendations
        analysis = self.bedtime_calculator.analyze_best_nights(
            sleep_data,
            top_percentile=top_percentile
        )

        return self.bedtime_calculator.generate_recommendation_report(analysis)

    async def check_health_alerts(self, lookback_days: int = 7) -> str:
        """
        Check all health metrics and generate alerts for critical situations.

        Args:
            lookback_days: Number of days to analyze (default: 7)

        Returns:
            Formatted health alerts report
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Get recent data
        sleep_sessions = await self.oura_client.get_sleep(start_date, end_date)
        readiness_data = await self.oura_client.get_daily_readiness(start_date, end_date)
        activity_data = await self.oura_client.get_daily_activity(start_date, end_date)

        # Aggregate biphasic/multiple sleep sessions per day
        sleep_data = aggregate_sleep_sessions_by_day(sleep_sessions)

        # Calculate personal sleep need for accurate thresholds
        from ..utils.sleep_debt import SleepDebtTracker
        tracker = SleepDebtTracker()
        personal_sleep_need, _ = tracker.calculate_personal_sleep_need(sleep_data, readiness_data)

        # Create alert system with personalized thresholds
        alert_system = AlertSystem(personal_sleep_need=personal_sleep_need)

        # Check for alerts
        alerts = alert_system.check_all_alerts(
            sleep_data,
            readiness_data,
            activity_data,
            lookback_days
        )

        return alert_system.format_alerts_report(alerts)

    async def detect_illness_risk(self, lookback_days: int = 30) -> str:
        """
        Detect potential illness using multi-signal analysis.

        Combines body temperature, HRV, resting HR, respiratory rate,
        and recovery scores to provide early warning 1-2 days before symptoms.

        Args:
            lookback_days: Number of days for baseline calculation (default: 30)

        Returns:
            Formatted illness detection report
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Get data for analysis
        readiness_data = await self.oura_client.get_daily_readiness(start_date, end_date)
        sleep_sessions = await self.oura_client.get_sleep(start_date, end_date)

        if not readiness_data or len(readiness_data) < 7:
            return "⚠️ Insufficient data for illness detection (need at least 7 days of readiness data)"

        # Aggregate sleep sessions
        sleep_data = aggregate_sleep_sessions_by_day(sleep_sessions) if sleep_sessions else []

        # Detect illness signals
        detection = self.illness_detector.detect_illness_signals(
            readiness_data,
            sleep_data
        )

        return self.illness_detector.format_illness_report(detection)

    async def analyze_chronotype(
        self,
        lookback_days: int = 30,
        include_activity: bool = True
    ) -> str:
        """
        Analyze chronotype (morning lark, night owl, intermediate) based on sleep timing
        and activity patterns.

        Args:
            lookback_days: Number of days to analyze (minimum 14, recommended 30+)
            include_activity: Include activity pattern analysis

        Returns:
            Formatted chronotype analysis report
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Get sleep session data (need timing information)
        sleep_sessions = await self.oura_client.get_sleep(start_date, end_date)

        if not sleep_sessions:
            return "⚠️ No sleep data available for chronotype analysis"

        # For chronotype analysis, pass RAW sessions (not aggregated)
        # The analyzer will extract main sleep sessions internally
        # This ensures naps don't skew the chronotype classification

        # Get activity data if requested
        activity_data = None
        if include_activity:
            activity_data = await self.oura_client.get_daily_activity(start_date, end_date)

        # Run chronotype analysis with raw sessions
        analysis = self.chronotype_analyzer.analyze_chronotype(
            sleep_sessions,
            activity_data
        )

        return self.chronotype_analyzer.format_chronotype_report(analysis)
