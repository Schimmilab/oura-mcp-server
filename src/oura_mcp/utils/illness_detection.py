"""
Illness Detection System

Early warning system that combines multiple physiological signals
to detect potential illness 1-2 days before symptoms appear.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev
from enum import Enum

from .resting_hr import extract_resting_hr_values


class IllnessRiskLevel(Enum):
    """Risk levels for illness detection."""
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class IllnessSignal:
    """Represents a single illness warning signal."""

    def __init__(
        self,
        signal_type: str,
        severity: float,  # 0-1 scale
        value: float,
        baseline: float,
        deviation: float,
        message: str
    ):
        self.signal_type = signal_type
        self.severity = severity
        self.value = value
        self.baseline = baseline
        self.deviation = deviation
        self.message = message
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert signal to dictionary."""
        return {
            'signal_type': self.signal_type,
            'severity': self.severity,
            'value': self.value,
            'baseline': self.baseline,
            'deviation': self.deviation,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }


class IllnessDetector:
    """Detects potential illness using multiple physiological signals."""

    # Signal thresholds
    THRESHOLDS = {
        'temperature_score_drop': {
            'elevated': -10,   # points below baseline
            'high': -20,
            'critical': -30
        },
        'hrv_drop': {
            'elevated': -15,   # % below baseline
            'high': -25,
            'critical': -35
        },
        'resting_hr_increase': {
            'elevated': 5,     # bpm above baseline
            'high': 8,
            'critical': 12
        },
        'respiratory_rate_increase': {
            'elevated': 2,     # breaths/min above baseline
            'high': 3,
            'critical': 5
        },
        'recovery_score_drop': {
            'elevated': -15,   # points below baseline
            'high': -25,
            'critical': -35
        }
    }

    # Signal weights for composite risk score
    SIGNAL_WEIGHTS = {
        'temperature': 0.35,
        'hrv': 0.25,
        'resting_hr': 0.20,
        'respiratory_rate': 0.10,
        'recovery': 0.10
    }

    def __init__(self, baseline_days: int = 30):
        """
        Initialize illness detector.

        Args:
            baseline_days: Number of days to use for baseline calculation
        """
        self.baseline_days = baseline_days

    def detect_illness_signals(
        self,
        readiness_data: List[Dict],
        sleep_data: List[Dict]
    ) -> Dict:
        """
        Analyze multiple signals to detect potential illness.

        Args:
            readiness_data: Recent readiness data (at least 7 days)
            sleep_data: Recent sleep data (at least 7 days)

        Returns:
            Dictionary with illness detection results
        """
        if not readiness_data or len(readiness_data) < 7:
            return {
                'risk_level': IllnessRiskLevel.NORMAL,
                'risk_score': 0,
                'signals': [],
                'error': 'Insufficient data (need at least 7 days)'
            }

        # Calculate baselines (exclude last 3 days to detect changes)
        baselines = self._calculate_baselines(readiness_data[:-3], sleep_data[:-3] if sleep_data else [])

        # Analyze recent data (last 3 days)
        recent_readiness = readiness_data[-3:]
        recent_sleep = sleep_data[-3:] if sleep_data else []

        # Check each signal
        signals = []

        # 1. Body temperature
        temp_signal = self._check_temperature(recent_readiness, baselines)
        if temp_signal:
            signals.append(temp_signal)

        # 2. HRV
        hrv_signal = self._check_hrv(recent_readiness, baselines)
        if hrv_signal:
            signals.append(hrv_signal)

        # 3. Resting heart rate
        rhr_signal = self._check_resting_hr(recent_sleep, baselines)
        if rhr_signal:
            signals.append(rhr_signal)

        # 4. Respiratory rate
        resp_signal = self._check_respiratory_rate(recent_sleep, baselines)
        if resp_signal:
            signals.append(resp_signal)

        # 5. Recovery/Readiness score
        recovery_signal = self._check_recovery_score(recent_readiness, baselines)
        if recovery_signal:
            signals.append(recovery_signal)

        # Calculate composite risk score
        risk_score = self._calculate_risk_score(signals)
        risk_level = self._determine_risk_level(risk_score)

        # Detect patterns
        pattern = self._detect_illness_pattern(signals)

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'signals': signals,
            'baselines': baselines,
            'pattern': pattern,
            'confidence': self._calculate_confidence(signals),
            'recommendation': self._generate_recommendation(risk_level, pattern)
        }

    def _calculate_baselines(
        self,
        readiness_data: List[Dict],
        sleep_data: List[Dict]
    ) -> Dict:
        """Calculate baseline values for comparison."""
        baselines = {}

        # Body temperature baseline
        temp_deviations = []
        for day in readiness_data:
            contributors = day.get('contributors', {})
            temp = contributors.get('body_temperature')
            if temp is not None:
                temp_deviations.append(temp)

        if temp_deviations:
            baselines['temperature'] = mean(temp_deviations)
            baselines['temperature_std'] = stdev(temp_deviations) if len(temp_deviations) > 1 else 0

        # HRV baseline
        hrv_values = []
        for day in readiness_data:
            contributors = day.get('contributors', {})
            hrv = contributors.get('hrv_balance')
            if hrv is not None:
                hrv_values.append(hrv)

        if hrv_values:
            baselines['hrv'] = mean(hrv_values)
            baselines['hrv_std'] = stdev(hrv_values) if len(hrv_values) > 1 else 0

        # Resting HR baseline — real bpm from the nightly trough.
        # ⛔ NOT readiness.contributors.resting_heart_rate: that is a 0-100 score
        # (higher = better) which saturates at 100 and hides deterioration.
        rhr_values = extract_resting_hr_values(sleep_data)

        if rhr_values:
            baselines['resting_hr'] = mean(rhr_values)
            baselines['resting_hr_std'] = stdev(rhr_values) if len(rhr_values) > 1 else 0

        # Respiratory rate baseline
        if sleep_data:
            resp_values = []
            for session in sleep_data:
                resp = session.get('breath_average')
                if resp is not None:
                    resp_values.append(resp)

            if resp_values:
                baselines['respiratory_rate'] = mean(resp_values)
                baselines['respiratory_rate_std'] = stdev(resp_values) if len(resp_values) > 1 else 0

        # Recovery score baseline
        scores = [r.get('score') for r in readiness_data if r.get('score') is not None]
        if scores:
            baselines['recovery_score'] = mean(scores)
            baselines['recovery_score_std'] = stdev(scores) if len(scores) > 1 else 0

        return baselines

    def _check_temperature(
        self,
        recent_data: List[Dict],
        baselines: Dict
    ) -> Optional[IllnessSignal]:
        """Check for drop in body temperature score (low score = high temp/illness)."""
        if 'temperature' not in baselines:
            return None

        # Get recent temperature scores (Oura gives 0-100 score, lower = more deviation)
        recent_temps = []
        for day in recent_data:
            contributors = day.get('contributors', {})
            temp = contributors.get('body_temperature')
            if temp is not None:
                recent_temps.append(temp)

        if not recent_temps:
            return None

        avg_recent = mean(recent_temps)
        baseline = baselines['temperature']
        deviation = avg_recent - baseline

        # Check thresholds (NEGATIVE deviation = problem, score DROP indicates fever)
        thresholds = self.THRESHOLDS['temperature_score_drop']
        severity = 0

        if deviation <= thresholds['critical']:
            severity = 1.0
        elif deviation <= thresholds['high']:
            severity = 0.7
        elif deviation <= thresholds['elevated']:
            severity = 0.4

        if severity > 0:
            return IllnessSignal(
                signal_type='temperature',
                severity=severity,
                value=avg_recent,
                baseline=baseline,
                deviation=deviation,
                message=f"Body temp score {deviation:.0f} points below baseline (elevated temperature detected)"
            )

        return None

    def _check_hrv(
        self,
        recent_data: List[Dict],
        baselines: Dict
    ) -> Optional[IllnessSignal]:
        """Check for HRV drop."""
        if 'hrv' not in baselines:
            return None

        recent_hrvs = []
        for day in recent_data:
            contributors = day.get('contributors', {})
            hrv = contributors.get('hrv_balance')
            if hrv is not None:
                recent_hrvs.append(hrv)

        if not recent_hrvs:
            return None

        avg_recent = mean(recent_hrvs)
        baseline = baselines['hrv']
        deviation = avg_recent - baseline
        percent_change = (deviation / baseline) * 100 if baseline > 0 else 0

        thresholds = self.THRESHOLDS['hrv_drop']
        severity = 0

        if percent_change <= thresholds['critical']:
            severity = 1.0
        elif percent_change <= thresholds['high']:
            severity = 0.7
        elif percent_change <= thresholds['elevated']:
            severity = 0.4

        if severity > 0:
            return IllnessSignal(
                signal_type='hrv',
                severity=severity,
                value=avg_recent,
                baseline=baseline,
                deviation=deviation,
                message=f"HRV {percent_change:.0f}% below baseline"
            )

        return None

    def _check_resting_hr(
        self,
        sleep_data: List[Dict],
        baselines: Dict
    ) -> Optional[IllnessSignal]:
        """Check for an elevated resting heart rate, in real bpm.

        Before v0.9.1 this used the readiness RHR *score* and inverted the
        comparison to compensate. That was directionally right but numerically
        wrong twice over: the thresholds below are documented in bpm, and the
        score saturates at 100, so a deterioration starting from a healthy pulse
        barely moves it. Real bpm has no ceiling.
        """
        if 'resting_hr' not in baselines:
            return None

        recent_rhrs = extract_resting_hr_values(sleep_data)
        if not recent_rhrs:
            return None

        avg_recent = mean(recent_rhrs)
        baseline = baselines['resting_hr']

        # A HIGHER pulse is the illness signal.
        deviation = avg_recent - baseline

        thresholds = self.THRESHOLDS['resting_hr_increase']
        severity = 0

        if deviation >= thresholds['critical']:
            severity = 1.0
        elif deviation >= thresholds['high']:
            severity = 0.7
        elif deviation >= thresholds['elevated']:
            severity = 0.4

        if severity > 0:
            return IllnessSignal(
                signal_type='resting_hr',
                severity=severity,
                value=avg_recent,
                baseline=baseline,
                deviation=deviation,
                message=f"Resting HR {avg_recent:.0f}bpm, {deviation:+.1f}bpm above baseline"
            )

        return None

    def _check_respiratory_rate(
        self,
        recent_data: List[Dict],
        baselines: Dict
    ) -> Optional[IllnessSignal]:
        """Check for elevated respiratory rate."""
        if 'respiratory_rate' not in baselines or not recent_data:
            return None

        recent_rates = []
        for session in recent_data:
            rate = session.get('breath_average')
            if rate is not None:
                recent_rates.append(rate)

        if not recent_rates:
            return None

        avg_recent = mean(recent_rates)
        baseline = baselines['respiratory_rate']
        deviation = avg_recent - baseline

        thresholds = self.THRESHOLDS['respiratory_rate_increase']
        severity = 0

        if deviation >= thresholds['critical']:
            severity = 1.0
        elif deviation >= thresholds['high']:
            severity = 0.7
        elif deviation >= thresholds['elevated']:
            severity = 0.4

        if severity > 0:
            return IllnessSignal(
                signal_type='respiratory_rate',
                severity=severity,
                value=avg_recent,
                baseline=baseline,
                deviation=deviation,
                message=f"Resp rate {deviation:+.1f}br/min above baseline"
            )

        return None

    def _check_recovery_score(
        self,
        recent_data: List[Dict],
        baselines: Dict
    ) -> Optional[IllnessSignal]:
        """Check for drop in recovery/readiness score."""
        if 'recovery_score' not in baselines:
            return None

        recent_scores = [r.get('score') for r in recent_data if r.get('score') is not None]

        if not recent_scores:
            return None

        avg_recent = mean(recent_scores)
        baseline = baselines['recovery_score']
        deviation = avg_recent - baseline

        thresholds = self.THRESHOLDS['recovery_score_drop']
        severity = 0

        if deviation <= thresholds['critical']:
            severity = 1.0
        elif deviation <= thresholds['high']:
            severity = 0.7
        elif deviation <= thresholds['elevated']:
            severity = 0.4

        if severity > 0:
            return IllnessSignal(
                signal_type='recovery',
                severity=severity,
                value=avg_recent,
                baseline=baseline,
                deviation=deviation,
                message=f"Recovery score {deviation:.0f} points below baseline"
            )

        return None

    def _calculate_risk_score(self, signals: List[IllnessSignal]) -> float:
        """Calculate composite risk score from all signals."""
        if not signals:
            return 0

        weighted_score = 0
        total_weight = 0

        for signal in signals:
            weight = self.SIGNAL_WEIGHTS.get(signal.signal_type, 0.1)
            weighted_score += signal.severity * weight
            total_weight += weight

        # Normalize to 0-100 scale
        if total_weight > 0:
            return (weighted_score / total_weight) * 100
        return 0

    def _determine_risk_level(self, risk_score: float) -> IllnessRiskLevel:
        """Determine risk level from composite score."""
        if risk_score >= 70:
            return IllnessRiskLevel.CRITICAL
        elif risk_score >= 50:
            return IllnessRiskLevel.HIGH
        elif risk_score >= 30:
            return IllnessRiskLevel.ELEVATED
        else:
            return IllnessRiskLevel.NORMAL

    def _detect_illness_pattern(self, signals: List[IllnessSignal]) -> Optional[str]:
        """Detect specific illness patterns from signal combinations."""
        if not signals:
            return None

        signal_types = {s.signal_type for s in signals}

        # Classic illness pattern: temp + HRV drop + elevated RHR
        if {'temperature', 'hrv', 'resting_hr'}.issubset(signal_types):
            return "classic_infection"

        # Respiratory infection: resp rate + temp
        if {'temperature', 'respiratory_rate'}.issubset(signal_types):
            return "respiratory_infection"

        # Stress/overtraining: HRV drop + elevated RHR without temp
        if {'hrv', 'resting_hr'}.issubset(signal_types) and 'temperature' not in signal_types:
            return "stress_overtraining"

        # Early infection: temp + recovery drop
        if {'temperature', 'recovery'}.issubset(signal_types):
            return "early_infection"

        return "unknown_pattern"

    def _calculate_confidence(self, signals: List[IllnessSignal]) -> float:
        """Calculate confidence level based on number and severity of signals."""
        if not signals:
            return 0

        # More signals = higher confidence
        signal_count_factor = min(len(signals) / 3, 1.0)  # Max at 3+ signals

        # Higher severity = higher confidence
        avg_severity = mean([s.severity for s in signals])

        # Combine factors
        confidence = (signal_count_factor * 0.6 + avg_severity * 0.4) * 100

        return min(confidence, 100)

    def _generate_recommendation(
        self,
        risk_level: IllnessRiskLevel,
        pattern: Optional[str]
    ) -> str:
        """Generate actionable recommendation based on risk level."""
        if risk_level == IllnessRiskLevel.CRITICAL:
            return (
                "🚨 CRITICAL: Strong illness indicators detected. "
                "Take rest day immediately. Monitor symptoms closely. "
                "Consider seeking medical attention if symptoms develop."
            )
        elif risk_level == IllnessRiskLevel.HIGH:
            return (
                "⚠️ HIGH RISK: Multiple illness signals detected. "
                "Cancel training. Prioritize rest and recovery. "
                "Stay hydrated. Monitor temperature. Avoid contact with others."
            )
        elif risk_level == IllnessRiskLevel.ELEVATED:
            if pattern == "stress_overtraining":
                return (
                    "⚡ ELEVATED: Stress/overtraining signals detected. "
                    "Reduce training intensity by 50%. Add extra rest day. "
                    "Focus on sleep quality and stress management."
                )
            else:
                return (
                    "⚠️ ELEVATED: Early warning signs detected. "
                    "Reduce activity intensity. Get extra sleep tonight. "
                    "Increase hydration. Consider vitamin C/zinc supplementation."
                )
        else:
            return "✅ No illness signals detected. Continue normal routine."

    def format_illness_report(self, detection: Dict) -> str:
        """Generate human-readable illness detection report."""
        risk_level = detection['risk_level']
        risk_score = detection['risk_score']
        signals = detection['signals']
        pattern = detection.get('pattern')
        confidence = detection.get('confidence', 0)

        # Risk level emoji
        risk_emoji = {
            IllnessRiskLevel.CRITICAL: "🚨",
            IllnessRiskLevel.HIGH: "⚠️",
            IllnessRiskLevel.ELEVATED: "🟡",
            IllnessRiskLevel.NORMAL: "✅"
        }

        lines = [
            "# 🌡️ Illness Detection Report",
            "",
            f"## {risk_emoji[risk_level]} Risk Level: {risk_level.value.upper()}",
            "",
            f"**Risk Score:** {risk_score:.0f}/100",
            f"**Confidence:** {confidence:.0f}%",
            "",
        ]

        if pattern:
            pattern_names = {
                'classic_infection': 'Classic Infection Pattern',
                'respiratory_infection': 'Respiratory Infection',
                'stress_overtraining': 'Stress/Overtraining',
                'early_infection': 'Early Stage Infection',
                'unknown_pattern': 'Unknown Pattern'
            }
            lines.append(f"**Pattern:** {pattern_names.get(pattern, pattern)}")
            lines.append("")

        if signals:
            lines.extend([
                "## 📊 Warning Signals Detected",
                "",
            ])

            # Sort by severity
            sorted_signals = sorted(signals, key=lambda s: s.severity, reverse=True)

            for signal in sorted_signals:
                severity_bar = "█" * int(signal.severity * 10)
                lines.append(f"### {signal.signal_type.replace('_', ' ').title()}")
                lines.append(f"**Severity:** {severity_bar} {signal.severity*100:.0f}%")
                lines.append(f"**{signal.message}**")
                lines.append(f"- Current: {signal.value:.1f}")
                lines.append(f"- Baseline: {signal.baseline:.1f}")
                lines.append(f"- Deviation: {signal.deviation:+.1f}")
                lines.append("")

        # Recommendation
        lines.extend([
            "## 💡 Recommendation",
            "",
            detection['recommendation'],
            "",
        ])

        # Baseline reference
        if 'baselines' in detection and detection['baselines']:
            lines.extend([
                "## 📏 Your Baselines",
                "",
                "*30-day averages for comparison:*",
                "",
            ])
            baselines = detection['baselines']
            if 'temperature' in baselines:
                lines.append(f"- Body Temperature Score: {baselines['temperature']:.0f}/100")
            if 'hrv' in baselines:
                lines.append(f"- HRV Balance: {baselines['hrv']:.0f}/100")
            if 'resting_hr' in baselines:
                lines.append(f"- Resting HR Score: {baselines['resting_hr']:.0f}/100 *(score, not BPM)*")
            if 'respiratory_rate' in baselines:
                lines.append(f"- Respiratory Rate: {baselines['respiratory_rate']:.1f} br/min")
            if 'recovery_score' in baselines:
                lines.append(f"- Recovery Score: {baselines['recovery_score']:.0f}/100")
            lines.append("")

        lines.extend([
            "---",
            "",
            "*💡 Tip: Early detection allows you to rest before symptoms worsen, potentially reducing illness duration.*",
            ""
        ])

        return "\n".join(lines)
