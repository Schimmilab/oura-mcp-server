"""
Alert System

Monitors health metrics and trends to detect critical situations and
provide early warnings for potential health issues.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev
from enum import Enum

from .resting_hr import extract_resting_hr_values


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(Enum):
    """Alert categories."""
    SLEEP_QUALITY = "sleep_quality"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_DEBT = "sleep_debt"
    RECOVERY = "recovery"
    OVERTRAINING = "overtraining"
    HRV = "hrv"
    RESTING_HR = "resting_hr"
    CONSISTENCY = "consistency"
    ACTIVITY = "activity"
    TREND = "trend"


class HealthAlert:
    """Represents a health alert."""

    def __init__(
        self,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        message: str,
        metric_value: Optional[float] = None,
        threshold: Optional[float] = None,
        recommendation: Optional[str] = None
    ):
        self.category = category
        self.severity = severity
        self.title = title
        self.message = message
        self.metric_value = metric_value
        self.threshold = threshold
        self.recommendation = recommendation
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert alert to dictionary."""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat()
        }


class AlertSystem:
    """Monitors health metrics and generates alerts for critical situations."""

    # Base alert thresholds (will be scaled based on personal sleep need)
    THRESHOLDS = {
        'sleep_score': {
            'critical': 60,
            'warning': 70
        },
        'sleep_duration': {
            'critical': 6.0,  # hours (scaled based on personal need)
            'warning': 7.0     # (scaled based on personal need)
        },
        'sleep_debt': {
            'critical': 15.0,  # hours accumulated (scaled)
            'warning': 10.0    # (scaled)
        },
        'readiness_score': {
            'critical': 60,
            'warning': 70
        },
        'hrv_balance': {
            'critical': 50,
            'warning': 60
        },
        'resting_hr_increase': {
            'critical': 10,  # bpm above baseline
            'warning': 7
        },
        'consecutive_bad_nights': {
            'critical': 5,
            'warning': 3
        },
        'activity_streak': {
            'warning': 3  # days without activity
        }
    }

    def __init__(self, personal_sleep_need: Optional[float] = None):
        """
        Initialize the alert system.

        Args:
            personal_sleep_need: Personal sleep need in hours (default: None = use 8h)
        """
        self.personal_sleep_need = personal_sleep_need if personal_sleep_need else 8.0
        self.scale_factor = self.personal_sleep_need / 8.0

        # Scale sleep-related thresholds
        self.scaled_thresholds = self._scale_thresholds()

    def _scale_thresholds(self) -> Dict:
        """
        Scale sleep-related thresholds based on personal sleep need.

        Returns:
            Dictionary with scaled thresholds
        """
        scaled = {}

        for key, value in self.THRESHOLDS.items():
            if key in ['sleep_duration', 'sleep_debt']:
                # Scale sleep duration and debt thresholds
                scaled[key] = {
                    level: threshold * self.scale_factor
                    for level, threshold in value.items()
                }
            else:
                # Keep other thresholds unchanged
                scaled[key] = value.copy()

        return scaled

    def check_all_alerts(
        self,
        sleep_data: List[Dict],
        readiness_data: List[Dict],
        activity_data: List[Dict],
        lookback_days: int = 7
    ) -> List[HealthAlert]:
        """
        Check all metrics and return list of active alerts.

        Args:
            sleep_data: Recent sleep data
            readiness_data: Recent readiness data
            activity_data: Recent activity data
            lookback_days: Number of days to analyze

        Returns:
            List of active health alerts
        """
        alerts = []

        # Sleep alerts
        alerts.extend(self._check_sleep_quality_alerts(sleep_data))
        alerts.extend(self._check_sleep_duration_alerts(sleep_data))
        alerts.extend(self._check_sleep_debt_alerts(sleep_data))
        alerts.extend(self._check_sleep_consistency_alerts(sleep_data))
        alerts.extend(self._check_consecutive_bad_nights(sleep_data))

        # Readiness alerts
        alerts.extend(self._check_readiness_alerts(readiness_data))
        alerts.extend(self._check_hrv_alerts(readiness_data))
        alerts.extend(self._check_resting_hr_alerts(sleep_data))

        # Recovery alerts
        alerts.extend(self._check_overtraining_alerts(readiness_data, activity_data))

        # Activity alerts
        alerts.extend(self._check_activity_alerts(activity_data))

        # Trend alerts
        alerts.extend(self._check_declining_trends(sleep_data, readiness_data, activity_data))

        # Sort by severity (critical first)
        alerts.sort(key=lambda x: (
            0 if x.severity == AlertSeverity.CRITICAL
            else 1 if x.severity == AlertSeverity.WARNING
            else 2
        ))

        return alerts

    def _check_sleep_quality_alerts(self, sleep_data: List[Dict]) -> List[HealthAlert]:
        """Check for sleep quality alerts."""
        alerts = []

        if not sleep_data:
            return alerts

        # Get recent scores (last 3 days)
        recent_scores = [
            s.get('score', 0) for s in sleep_data[-3:]
            if isinstance(s, dict) and s.get('score') is not None
        ]

        if not recent_scores:
            return alerts

        avg_recent_score = mean(recent_scores)
        latest_score = recent_scores[-1] if recent_scores else 0

        # Critical: Latest night very poor
        if latest_score < self.scaled_thresholds['sleep_score']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_QUALITY,
                severity=AlertSeverity.CRITICAL,
                title="Critical Sleep Quality",
                message=f"Last night's sleep score was {latest_score}/100 - significantly below healthy range",
                metric_value=latest_score,
                threshold=self.scaled_thresholds['sleep_score']['critical'],
                recommendation="Prioritize sleep tonight: go to bed early, optimize environment, avoid alcohol/caffeine"
            ))

        # Warning: Average recent sleep poor
        elif avg_recent_score < self.scaled_thresholds['sleep_score']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_QUALITY,
                severity=AlertSeverity.WARNING,
                title="Declining Sleep Quality",
                message=f"Average sleep score over last 3 nights is {avg_recent_score:.0f}/100",
                metric_value=avg_recent_score,
                threshold=self.scaled_thresholds['sleep_score']['warning'],
                recommendation="Review sleep hygiene: consistent schedule, cool/dark room, wind-down routine"
            ))

        return alerts

    def _check_sleep_duration_alerts(self, sleep_data: List[Dict]) -> List[HealthAlert]:
        """Check for sleep duration alerts."""
        alerts = []

        if not sleep_data:
            return alerts

        # Get recent durations (last 3 days)
        recent_durations = [
            s.get('total_sleep_duration', 0) / 3600 for s in sleep_data[-3:]
            if isinstance(s, dict) and s.get('total_sleep_duration')
        ]

        if not recent_durations:
            return alerts

        avg_duration = mean(recent_durations)
        latest_duration = recent_durations[-1] if recent_durations else 0

        # Critical: Severe sleep deprivation
        if latest_duration < self.scaled_thresholds['sleep_duration']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_DURATION,
                severity=AlertSeverity.CRITICAL,
                title="Severe Sleep Deprivation",
                message=f"Only {latest_duration:.1f}h sleep last night - dangerously low",
                metric_value=latest_duration,
                threshold=self.scaled_thresholds['sleep_duration']['critical'],
                recommendation="Cancel non-essential activities. Aim for 9-10h sleep tonight to recover"
            ))

        # Warning: Insufficient sleep
        elif avg_duration < self.scaled_thresholds['sleep_duration']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_DURATION,
                severity=AlertSeverity.WARNING,
                title="Insufficient Sleep Duration",
                message=f"Averaging {avg_duration:.1f}h/night over last 3 nights",
                metric_value=avg_duration,
                threshold=self.scaled_thresholds['sleep_duration']['warning'],
                recommendation="Target 8+ hours of sleep. Adjust bedtime earlier by 30-60 minutes"
            ))

        return alerts

    def _check_sleep_debt_alerts(self, sleep_data: List[Dict]) -> List[HealthAlert]:
        """Check for accumulated sleep debt."""
        alerts = []

        if not sleep_data or len(sleep_data) < 3:
            return alerts

        # Calculate accumulated debt
        optimal_hours = 8.0
        accumulated_debt = 0

        for session in sleep_data[-7:]:  # Last week
            if not isinstance(session, dict):
                continue

            duration = session.get('total_sleep_duration', 0) / 3600
            deficit = optimal_hours - duration

            if deficit > 0:
                accumulated_debt += deficit
            else:
                # Payback debt at 50% rate
                accumulated_debt = max(0, accumulated_debt + (deficit * 0.5))

        # Critical: Severe accumulated debt
        if accumulated_debt >= self.scaled_thresholds['sleep_debt']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_DEBT,
                severity=AlertSeverity.CRITICAL,
                title="Critical Sleep Debt",
                message=f"Accumulated {accumulated_debt:.1f}h sleep debt over the last week",
                metric_value=accumulated_debt,
                threshold=self.scaled_thresholds['sleep_debt']['critical'],
                recommendation="Immediate recovery needed: add 1-2h extra sleep per night for next week"
            ))

        # Warning: Moderate debt
        elif accumulated_debt >= self.scaled_thresholds['sleep_debt']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_DEBT,
                severity=AlertSeverity.WARNING,
                title="Accumulating Sleep Debt",
                message=f"Accumulated {accumulated_debt:.1f}h sleep debt",
                metric_value=accumulated_debt,
                threshold=self.scaled_thresholds['sleep_debt']['warning'],
                recommendation="Prevent further debt: prioritize consistent 8h sleep schedule"
            ))

        return alerts

    def _check_sleep_consistency_alerts(self, sleep_data: List[Dict]) -> List[HealthAlert]:
        """Check for sleep consistency issues."""
        alerts = []

        if not sleep_data or len(sleep_data) < 5:
            return alerts

        # Get bedtimes for last week
        bedtimes = []
        for session in sleep_data[-7:]:
            if not isinstance(session, dict):
                continue

            bedtime_str = session.get('bedtime_start')
            if bedtime_str:
                try:
                    bedtime_dt = datetime.fromisoformat(bedtime_str.replace('Z', '+00:00'))
                    # Convert to minutes since midnight
                    minutes = bedtime_dt.hour * 60 + bedtime_dt.minute
                    if minutes < 12 * 60:  # After midnight
                        minutes += 24 * 60
                    bedtimes.append(minutes)
                except (ValueError, TypeError):
                    continue

        if len(bedtimes) < 5:
            return alerts

        # Calculate consistency
        std_minutes = stdev(bedtimes)
        std_hours = std_minutes / 60

        # Warning: Inconsistent sleep schedule
        if std_hours > 2.0:  # More than 2h variation
            alerts.append(HealthAlert(
                category=AlertCategory.CONSISTENCY,
                severity=AlertSeverity.WARNING,
                title="Inconsistent Sleep Schedule",
                message=f"Bedtime varies by {std_hours:.1f}h - affecting sleep quality",
                metric_value=std_hours,
                threshold=2.0,
                recommendation="Set consistent bedtime (±30min). Use bedtime alarm/reminder"
            ))

        return alerts

    def _check_consecutive_bad_nights(self, sleep_data: List[Dict]) -> List[HealthAlert]:
        """Check for consecutive bad nights (considering both score and duration vs personal need)."""
        alerts = []

        if not sleep_data or len(sleep_data) < 3:
            return alerts

        # Count consecutive nights that are truly "bad":
        # Use efficiency as proxy if score not available (aggregated sessions)
        consecutive_bad = 0
        for session in reversed(sleep_data[-7:]):
            if not isinstance(session, dict):
                continue

            # Get score (may be None for aggregated sessions)
            score = session.get('score')
            duration_hours = session.get('total_sleep_duration', 0) / 3600
            deficit = self.personal_sleep_need - duration_hours

            # If no score, use efficiency as proxy
            if score is None or score == 0:
                efficiency = session.get('efficiency', 0)
                # Convert efficiency to score-like metric (efficiency 85% ≈ score 70)
                score = min(100, efficiency * 1.2) if efficiency else 50

            # "Bad night" criteria:
            # - Score < 60 (critically low) OR
            # - (Score < 70 AND duration deficit > 1h significantly below need)
            is_bad = (score < 60) or (score < 70 and deficit > 1.0)

            if is_bad:
                consecutive_bad += 1
            else:
                break

        # Critical: 5+ bad nights in a row
        if consecutive_bad >= self.scaled_thresholds['consecutive_bad_nights']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_QUALITY,
                severity=AlertSeverity.CRITICAL,
                title="Extended Sleep Crisis",
                message=f"{consecutive_bad} consecutive nights with poor sleep",
                metric_value=consecutive_bad,
                threshold=self.scaled_thresholds['consecutive_bad_nights']['critical'],
                recommendation="Consider consulting sleep specialist. May indicate underlying issue"
            ))

        # Warning: 3+ bad nights
        elif consecutive_bad >= self.scaled_thresholds['consecutive_bad_nights']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.SLEEP_QUALITY,
                severity=AlertSeverity.WARNING,
                title="Consecutive Poor Sleep",
                message=f"{consecutive_bad} nights in a row with suboptimal sleep",
                metric_value=consecutive_bad,
                threshold=self.scaled_thresholds['consecutive_bad_nights']['warning'],
                recommendation="Break the pattern: review what changed, adjust environment/habits"
            ))

        return alerts

    def _check_readiness_alerts(self, readiness_data: List[Dict]) -> List[HealthAlert]:
        """Check for readiness alerts."""
        alerts = []

        if not readiness_data:
            return alerts

        # Get recent scores
        recent_scores = [
            r.get('score', 0) for r in readiness_data[-3:]
            if isinstance(r, dict) and r.get('score') is not None
        ]

        if not recent_scores:
            return alerts

        avg_score = mean(recent_scores)
        latest_score = recent_scores[-1] if recent_scores else 0

        # Critical: Very low readiness
        if latest_score < self.scaled_thresholds['readiness_score']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.RECOVERY,
                severity=AlertSeverity.CRITICAL,
                title="Critical Recovery State",
                message=f"Readiness score is {latest_score}/100 - body needs rest",
                metric_value=latest_score,
                threshold=self.scaled_thresholds['readiness_score']['critical'],
                recommendation="Take rest day. No intense training. Focus on sleep and recovery"
            ))

        # Warning: Low readiness
        elif avg_score < self.scaled_thresholds['readiness_score']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.RECOVERY,
                severity=AlertSeverity.WARNING,
                title="Suboptimal Readiness",
                message=f"Average readiness {avg_score:.0f}/100 over last 3 days",
                metric_value=avg_score,
                threshold=self.scaled_thresholds['readiness_score']['warning'],
                recommendation="Reduce training intensity. Prioritize recovery activities"
            ))

        return alerts

    def _check_hrv_alerts(self, readiness_data: List[Dict]) -> List[HealthAlert]:
        """Check for HRV alerts."""
        alerts = []

        if not readiness_data or len(readiness_data) < 3:
            return alerts

        # Get recent HRV balance scores
        hrv_scores = []
        for day in readiness_data[-7:]:
            if not isinstance(day, dict):
                continue

            contributors = day.get('contributors', {})
            hrv = contributors.get('hrv_balance')
            if hrv is not None:
                hrv_scores.append(hrv)

        if len(hrv_scores) < 3:
            return alerts

        avg_hrv = mean(hrv_scores)
        latest_hrv = hrv_scores[-1] if hrv_scores else 0

        # Critical: Very low HRV
        if latest_hrv < self.scaled_thresholds['hrv_balance']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.HRV,
                severity=AlertSeverity.CRITICAL,
                title="Critical HRV Drop",
                message=f"HRV balance at {latest_hrv} - indicates high stress or illness",
                metric_value=latest_hrv,
                threshold=self.scaled_thresholds['hrv_balance']['critical'],
                recommendation="Check for illness signs. Avoid intense exercise. Prioritize stress management"
            ))

        # Warning: Low HRV
        elif avg_hrv < self.scaled_thresholds['hrv_balance']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.HRV,
                severity=AlertSeverity.WARNING,
                title="Declining HRV",
                message=f"HRV balance averaging {avg_hrv:.0f} - below optimal",
                metric_value=avg_hrv,
                threshold=self.scaled_thresholds['hrv_balance']['warning'],
                recommendation="Monitor stress levels. Consider meditation, breathing exercises, lighter training"
            ))

        return alerts

    def _check_resting_hr_alerts(self, sleep_data: List[Dict]) -> List[HealthAlert]:
        """Alert when the resting heart rate rises above its own baseline.

        ⛔ Until v0.9.1 this read ``readiness.contributors.resting_heart_rate``,
        which is a 0-100 score where *higher is better* — the exact inverse of a
        pulse. The alarm therefore fired on recovery and stayed silent during an
        infection, when a rising pulse drives the score down. It now uses the
        nightly trough in real bpm; see ``utils/resting_hr``.
        """
        alerts: List[HealthAlert] = []
        resting_hrs = extract_resting_hr_values(sleep_data)

        if len(resting_hrs) < 7:
            return alerts

        baseline_rhr = mean(resting_hrs[:-3])  # Exclude last 3 days
        recent_rhr = mean(resting_hrs[-3:])  # Last 3 days

        # Direction matters: a HIGHER pulse is the warning sign.
        increase = recent_rhr - baseline_rhr

        # Critical: Significant elevation
        if increase >= self.scaled_thresholds['resting_hr_increase']['critical']:
            alerts.append(HealthAlert(
                category=AlertCategory.RESTING_HR,
                severity=AlertSeverity.CRITICAL,
                title="Elevated Resting Heart Rate",
                message=f"Resting HR {recent_rhr:.0f}bpm, {increase:+.1f}bpm above your {baseline_rhr:.0f}bpm baseline - possible illness or overtraining",
                metric_value=recent_rhr,
                threshold=baseline_rhr + self.scaled_thresholds['resting_hr_increase']['critical'],
                recommendation="Check for illness. Rest from training. Monitor temperature. Consult doctor if persists"
            ))

        # Warning: Moderate elevation
        elif increase >= self.scaled_thresholds['resting_hr_increase']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.RESTING_HR,
                severity=AlertSeverity.WARNING,
                title="Rising Resting Heart Rate",
                message=f"Resting HR {recent_rhr:.0f}bpm, {increase:+.1f}bpm above your {baseline_rhr:.0f}bpm baseline",
                metric_value=recent_rhr,
                threshold=baseline_rhr + self.scaled_thresholds['resting_hr_increase']['warning'],
                recommendation="Reduce training load. Monitor for illness signs. Ensure adequate hydration"
            ))

        return alerts

    def _check_overtraining_alerts(
        self,
        readiness_data: List[Dict],
        activity_data: List[Dict]
    ) -> List[HealthAlert]:
        """Check for overtraining signs."""
        alerts = []

        if not readiness_data or not activity_data or len(activity_data) < 7:
            return alerts

        # Get readiness scores
        readiness_scores = [
            r.get('score', 0) for r in readiness_data[-7:]
            if isinstance(r, dict) and r.get('score') is not None
        ]

        # Get training load
        high_intensity_days = sum([
            1 for a in activity_data[-7:]
            if isinstance(a, dict) and (a.get('high_activity_time', 0) or 0) > 0
        ])

        if len(readiness_scores) < 5:
            return alerts

        avg_readiness = mean(readiness_scores)

        # Critical: Low readiness + high training frequency
        if avg_readiness < 70 and high_intensity_days >= 5:
            alerts.append(HealthAlert(
                category=AlertCategory.OVERTRAINING,
                severity=AlertSeverity.CRITICAL,
                title="Overtraining Risk",
                message=f"Low readiness ({avg_readiness:.0f}) with {high_intensity_days} high-intensity days",
                metric_value=avg_readiness,
                recommendation="Mandatory rest days. Reduce training frequency to 3-4 days/week until readiness improves"
            ))

        # Warning: Declining readiness with consistent training
        elif avg_readiness < 75 and high_intensity_days >= 4:
            alerts.append(HealthAlert(
                category=AlertCategory.OVERTRAINING,
                severity=AlertSeverity.WARNING,
                title="Recovery Imbalance",
                message=f"Training load ({high_intensity_days} days) may exceed recovery capacity",
                metric_value=avg_readiness,
                recommendation="Add 1-2 rest days. Consider active recovery sessions instead of intense training"
            ))

        return alerts

    def _check_activity_alerts(self, activity_data: List[Dict]) -> List[HealthAlert]:
        """Check for activity-related alerts."""
        alerts = []

        if not activity_data or len(activity_data) < 3:
            return alerts

        # Check for inactivity streak
        inactive_days = 0
        for day in reversed(activity_data[-7:]):
            if not isinstance(day, dict):
                continue

            steps = day.get('steps', 0)
            if steps < 3000:  # Very low activity
                inactive_days += 1
            else:
                break

        # Warning: Extended inactivity
        if inactive_days >= self.scaled_thresholds['activity_streak']['warning']:
            alerts.append(HealthAlert(
                category=AlertCategory.ACTIVITY,
                severity=AlertSeverity.WARNING,
                title="Prolonged Inactivity",
                message=f"{inactive_days} consecutive days with minimal activity",
                metric_value=inactive_days,
                threshold=self.scaled_thresholds['activity_streak']['warning'],
                recommendation="Break inactivity: take a walk, do light exercise, or active recovery"
            ))

        return alerts

    def _check_declining_trends(
        self,
        sleep_data: List[Dict],
        readiness_data: List[Dict],
        activity_data: List[Dict]
    ) -> List[HealthAlert]:
        """Check for declining trends across metrics."""
        alerts = []

        # Check sleep trend
        if sleep_data and len(sleep_data) >= 7:
            scores = [s.get('score', 0) for s in sleep_data[-7:] if isinstance(s, dict)]
            if len(scores) >= 5:
                trend = self._calculate_trend(scores)
                if trend < -3:  # Declining
                    alerts.append(HealthAlert(
                        category=AlertCategory.TREND,
                        severity=AlertSeverity.WARNING,
                        title="Declining Sleep Trend",
                        message="Sleep scores have been declining over the past week",
                        recommendation="Identify and address factors affecting sleep quality"
                    ))

        # Check readiness trend
        if readiness_data and len(readiness_data) >= 7:
            scores = [r.get('score', 0) for r in readiness_data[-7:] if isinstance(r, dict)]
            if len(scores) >= 5:
                trend = self._calculate_trend(scores)
                if trend < -3:  # Declining
                    alerts.append(HealthAlert(
                        category=AlertCategory.TREND,
                        severity=AlertSeverity.WARNING,
                        title="Declining Readiness Trend",
                        message="Readiness has been declining - recovery may be insufficient",
                        recommendation="Evaluate training load, stress levels, and sleep quality"
                    ))

        return alerts

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope using linear regression."""
        if len(values) < 3:
            return 0

        n = len(values)
        x = list(range(n))
        y = values

        x_mean = mean(x)
        y_mean = mean(y)

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0

        slope = numerator / denominator
        return slope

    def format_alerts_report(self, alerts: List[HealthAlert]) -> str:
        """Generate human-readable alerts report."""
        if not alerts:
            return "✅ No health alerts - all metrics within healthy range!"

        # Group by severity
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        warning = [a for a in alerts if a.severity == AlertSeverity.WARNING]
        info = [a for a in alerts if a.severity == AlertSeverity.INFO]

        lines = [
            "# 🚨 Health Alerts",
            "",
            f"**Active Alerts:** {len(alerts)} ({len(critical)} critical, {len(warning)} warnings)",
            "",
        ]

        if critical:
            lines.extend([
                "## 🔴 CRITICAL ALERTS",
                "",
                "*Immediate attention required*",
                "",
            ])

            for alert in critical:
                lines.append(f"### {alert.title}")
                lines.append("")
                lines.append(f"**{alert.message}**")
                lines.append("")

                if alert.metric_value is not None and alert.threshold is not None:
                    lines.append(f"- Current: {alert.metric_value:.1f}")
                    lines.append(f"- Threshold: {alert.threshold:.1f}")
                    lines.append("")

                if alert.recommendation:
                    lines.append(f"**Action Required:**")
                    lines.append(f"{alert.recommendation}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        if warning:
            lines.extend([
                "## 🟡 WARNINGS",
                "",
                "*Monitor closely and take action*",
                "",
            ])

            for alert in warning:
                lines.append(f"### {alert.title}")
                lines.append("")
                lines.append(f"{alert.message}")
                lines.append("")

                if alert.metric_value is not None and alert.threshold is not None:
                    lines.append(f"- Current: {alert.metric_value:.1f}")
                    lines.append(f"- Threshold: {alert.threshold:.1f}")
                    lines.append("")

                if alert.recommendation:
                    lines.append(f"**Recommendation:**")
                    lines.append(f"{alert.recommendation}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Add summary of actions
        lines.extend([
            "## 💡 Priority Actions",
            "",
        ])

        if critical:
            lines.append("**Immediate (Critical):**")
            for i, alert in enumerate(critical[:3], 1):
                lines.append(f"{i}. {alert.recommendation}")
            lines.append("")

        if warning:
            lines.append("**This Week (Warnings):**")
            for i, alert in enumerate(warning[:3], 1):
                lines.append(f"{i}. {alert.recommendation}")
            lines.append("")

        lines.extend([
            "",
            "*💡 Tip: Address critical alerts immediately. Warnings should be resolved within 3-5 days.*",
            ""
        ])

        return "\n".join(lines)
