"""Semantic interpretation engine for Oura metrics."""

from typing import Dict, Any, Optional


class InterpretationEngine:
    """
    Converts raw Oura values into semantic, human-understandable meanings.

    Provides context-aware interpretations that help AI models (and humans)
    understand what metric values actually mean for health and recovery.
    """

    def __init__(self):
        """Initialize interpretation engine."""
        pass

    # === Score Interpretations ===

    def interpret_sleep_score(self, score: int) -> Dict[str, str]:
        """
        Interpret sleep score (0-100).

        Returns:
            Dictionary with quality, description, and recommendation
        """
        if score >= 85:
            return {
                "quality": "Excellent",
                "description": "Optimal sleep - body fully recovered",
                "emoji": "🌟",
                "recommendation": "Great foundation for high performance today"
            }
        elif score >= 70:
            return {
                "quality": "Good",
                "description": "Solid sleep - adequate recovery",
                "emoji": "✅",
                "recommendation": "Ready for normal activities and moderate training"
            }
        elif score >= 60:
            return {
                "quality": "Fair",
                "description": "Acceptable but not optimal",
                "emoji": "⚠️",
                "recommendation": "Consider lighter activities; focus on recovery tonight"
            }
        else:
            return {
                "quality": "Poor",
                "description": "Insufficient sleep - recovery incomplete",
                "emoji": "🔴",
                "recommendation": "Prioritize rest today; avoid intense activities"
            }

    def interpret_readiness_score(self, score: int) -> Dict[str, str]:
        """Interpret readiness score (0-100)."""
        if score >= 85:
            return {
                "quality": "Optimal",
                "description": "Fully recovered and ready",
                "emoji": "💪",
                "recommendation": "Good day for challenging workouts or high performance"
            }
        elif score >= 70:
            return {
                "quality": "Good",
                "description": "Ready for normal activities",
                "emoji": "✅",
                "recommendation": "Suitable for moderate training and work"
            }
        elif score >= 60:
            return {
                "quality": "Fair",
                "description": "Adequate but not primed",
                "emoji": "⚠️",
                "recommendation": "Light activities preferred; monitor energy levels"
            }
        else:
            return {
                "quality": "Low",
                "description": "Body needs recovery",
                "emoji": "🔴",
                "recommendation": "Rest day recommended; focus on recovery activities"
            }

    def interpret_activity_score(self, score: int) -> Dict[str, str]:
        """Interpret activity score (0-100)."""
        if score >= 85:
            return {
                "quality": "Excellent",
                "description": "Optimal activity level achieved",
                "emoji": "🎯",
                "recommendation": "Great balance of movement and recovery"
            }
        elif score >= 70:
            return {
                "quality": "Good",
                "description": "Good activity level",
                "emoji": "✅",
                "recommendation": "Maintaining healthy activity patterns"
            }
        elif score >= 60:
            return {
                "quality": "Fair",
                "description": "Below optimal activity",
                "emoji": "⚠️",
                "recommendation": "Consider more movement or gentler recovery"
            }
        else:
            return {
                "quality": "Low",
                "description": "Activity needs attention",
                "emoji": "🔴",
                "recommendation": "Either too sedentary or overtraining"
            }

    # === HRV Interpretation ===

    def interpret_hrv_balance(self, hrv_balance: int, baseline: Optional[float] = None) -> Dict[str, Any]:
        """
        Interpret HRV balance score (0-100).

        Args:
            hrv_balance: Oura's HRV balance score
            baseline: Optional baseline for comparison

        Returns:
            Interpretation dictionary
        """
        interpretation = {
            "score": hrv_balance,
            "baseline": baseline
        }

        if hrv_balance >= 75:
            interpretation.update({
                "status": "Balanced",
                "emoji": "💚",
                "description": "HRV is balanced - good recovery",
                "meaning": "Autonomic nervous system is well-balanced",
                "implications": "Body is recovered and ready for stress"
            })
        elif hrv_balance >= 50:
            interpretation.update({
                "status": "Moderate",
                "emoji": "🟡",
                "description": "HRV is moderate - adequate recovery",
                "meaning": "Some stress response present",
                "implications": "Body is functioning but not optimally primed"
            })
        elif hrv_balance >= 30:
            interpretation.update({
                "status": "Low",
                "emoji": "🟠",
                "description": "HRV is low - incomplete recovery",
                "meaning": "Elevated sympathetic nervous system activity",
                "implications": "Body is under stress or recovering from load"
            })
        else:
            interpretation.update({
                "status": "Very Low",
                "emoji": "🔴",
                "description": "HRV is very low - significant stress detected",
                "meaning": "Autonomic nervous system is strained",
                "implications": "High stress, illness, or severe overtraining"
            })

        # Add baseline comparison if available
        if baseline:
            deviation_pct = ((hrv_balance - baseline) / baseline * 100) if baseline > 0 else 0
            interpretation["deviation_pct"] = round(deviation_pct, 1)

            if abs(deviation_pct) < 10:
                interpretation["baseline_status"] = "Normal variation"
            elif deviation_pct < -20:
                interpretation["baseline_status"] = f"Significantly below baseline ({abs(deviation_pct):.0f}%)"
            elif deviation_pct < 0:
                interpretation["baseline_status"] = f"Below baseline ({abs(deviation_pct):.0f}%)"
            elif deviation_pct > 20:
                interpretation["baseline_status"] = f"Significantly above baseline ({deviation_pct:.0f}%)"
            else:
                interpretation["baseline_status"] = f"Above baseline ({deviation_pct:.0f}%)"

        return interpretation

    # === Resting Heart Rate ===

    def interpret_resting_hr(
        self,
        current_hr: float,
        baseline_hr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Interpret resting heart rate.

        Args:
            current_hr: Current resting HR (bpm)
            baseline_hr: Baseline HR for comparison

        Returns:
            Interpretation dictionary
        """
        interpretation = {
            "current": current_hr,
            "baseline": baseline_hr
        }

        if baseline_hr:
            deviation = current_hr - baseline_hr
            deviation_pct = (deviation / baseline_hr * 100) if baseline_hr > 0 else 0

            interpretation["deviation"] = round(deviation, 1)
            interpretation["deviation_pct"] = round(deviation_pct, 1)

            if abs(deviation) <= 2:
                interpretation.update({
                    "status": "Normal",
                    "emoji": "✅",
                    "description": "Resting HR within normal variation",
                    "implications": "Good cardiovascular recovery"
                })
            elif deviation > 5:
                interpretation.update({
                    "status": "Elevated",
                    "emoji": "⚠️",
                    "description": f"Resting HR elevated by {deviation:.0f} bpm",
                    "implications": "May indicate stress, fatigue, dehydration, or illness onset",
                    "causes": [
                        "Incomplete recovery from training",
                        "Stress or anxiety",
                        "Dehydration",
                        "Illness or infection onset",
                        "Alcohol consumption",
                        "Poor sleep quality"
                    ]
                })
            elif deviation < -5:
                interpretation.update({
                    "status": "Lower",
                    "emoji": "💚",
                    "description": f"Resting HR lower by {abs(deviation):.0f} bpm",
                    "implications": "Excellent recovery or improved fitness"
                })
            else:
                interpretation.update({
                    "status": "Slight Variation",
                    "emoji": "✅",
                    "description": f"Resting HR {'+' if deviation > 0 else ''}{deviation:.0f} bpm from baseline",
                    "implications": "Minor variation - within acceptable range"
                })
        else:
            # No baseline - provide general interpretation
            interpretation.update({
                "status": "No Baseline",
                "description": f"Current resting HR: {current_hr:.0f} bpm",
                "implications": "Need more data to establish personal baseline"
            })

        return interpretation

    # === Body Temperature ===

    def interpret_temperature_deviation(
        self,
        temp_score: int,
        temp_deviation: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Interpret body temperature score and deviation.

        Args:
            temp_score: Oura's temperature score (0-100)
            temp_deviation: Temperature deviation in Celsius (if available)

        Returns:
            Interpretation dictionary
        """
        interpretation = {
            "score": temp_score,
            "deviation_celsius": temp_deviation
        }

        if temp_score >= 95:
            interpretation.update({
                "status": "Normal",
                "emoji": "✅",
                "description": "Body temperature within normal range",
                "implications": "No temperature-related stress detected"
            })
        elif temp_score >= 85:
            interpretation.update({
                "status": "Slight Variation",
                "emoji": "🟡",
                "description": "Minor temperature variation",
                "implications": "Normal fluctuation - monitor if persistent"
            })
        elif temp_score >= 70:
            interpretation.update({
                "status": "Moderate Deviation",
                "emoji": "⚠️",
                "description": "Temperature deviation detected",
                "implications": "May indicate hormonal changes, stress, or early illness",
                "causes": [
                    "Menstrual cycle (for females)",
                    "Overtraining or high training load",
                    "Early illness onset",
                    "Insufficient recovery",
                    "Environmental factors"
                ]
            })
        else:
            interpretation.update({
                "status": "Significant Deviation",
                "emoji": "🔴",
                "description": "Significant temperature deviation",
                "implications": "Strong signal - investigate further",
                "causes": [
                    "Possible illness or infection",
                    "Severe overtraining",
                    "Hormonal imbalance",
                    "Need medical evaluation if persistent"
                ]
            })

        return interpretation

    # === Recovery State ===

    def interpret_recovery_state(
        self,
        readiness: int,
        hrv_balance: int,
        resting_hr_deviation: Optional[float],
        sleep_score: int,
        temperature_score: int
    ) -> Dict[str, Any]:
        """
        Holistic recovery state interpretation based on multiple signals.

        Args:
            readiness: Readiness score
            hrv_balance: HRV balance score
            resting_hr_deviation: RHR deviation from baseline (bpm)
            sleep_score: Sleep score
            temperature_score: Temperature score

        Returns:
            Comprehensive recovery interpretation
        """
        # Calculate weighted recovery state
        # Prioritize: HRV (35%), Readiness (30%), Sleep (20%), RHR (10%), Temp (5%)

        # A missing signal must LOWER the confidence, never score full marks.
        # Until v0.9.4 the caller passed a hardcoded 0 here, so the RHR term
        # always contributed its maximum 10 points -- see the module note in
        # utils/resting_hr.py and tests/test_recovery_rhr_deviation.py.
        rhr_available = resting_hr_deviation is not None

        if rhr_available:
            # ⛔ Kept as ONE literal expression, in its original term order.
            # Summing the same weights in a different order moved an otherwise
            # unchanged day from 78.1 to 78.2 (78.14999999999999 vs 78.15 in
            # binary floating point). A fix must not shift numbers it was not
            # asked to touch -- the regression test pins this value.
            recovery_score = (
                hrv_balance * 0.35 +
                readiness * 0.30 +
                sleep_score * 0.20 +
                max(0, 100 - abs(resting_hr_deviation) * 10) * 0.10 +
                temperature_score * 0.05
            )
        else:
            # Renormalise over the weights actually present. Just dropping the
            # term would deduct a flat 10 points, which reads as "bad recovery"
            # instead of "one signal unknown" -- the opposite of what is meant.
            present = ((hrv_balance, 0.35), (readiness, 0.30),
                       (sleep_score, 0.20), (temperature_score, 0.05))
            recovery_score = (
                sum(value * weight for value, weight in present)
                / sum(weight for _value, weight in present)
            )

        # Determine recovery state
        if recovery_score >= 80:
            state = "Fully Recovered"
            emoji = "💪"
            description = "All systems green - optimal state"
            training_rec = "Ready for high-intensity or long-duration training"
            confidence = 0.9
        elif recovery_score >= 70:
            state = "Well Recovered"
            emoji = "✅"
            description = "Good recovery - ready for normal training"
            training_rec = "Suitable for moderate to high intensity work"
            confidence = 0.85
        elif recovery_score >= 60:
            state = "Adequately Recovered"
            emoji = "🟡"
            description = "Moderate recovery - some fatigue present"
            training_rec = "Light to moderate intensity recommended"
            confidence = 0.75
        elif recovery_score >= 50:
            state = "Partially Recovered"
            emoji = "🟠"
            description = "Incomplete recovery - significant fatigue"
            training_rec = "Very light activity only; prioritize recovery"
            confidence = 0.7
        else:
            state = "Not Recovered"
            emoji = "🔴"
            description = "Body under significant stress"
            training_rec = "Rest day strongly recommended"
            confidence = 0.85

        return {
            "state": state,
            "emoji": emoji,
            "recovery_score": round(recovery_score, 1),
            "description": description,
            "training_recommendation": training_rec,
            "confidence": confidence,
            "signals": {
                "hrv_balance": {"value": hrv_balance, "weight": "35%", "impact": "High"},
                "readiness": {"value": readiness, "weight": "30%", "impact": "High"},
                "sleep": {"value": sleep_score, "weight": "20%", "impact": "Medium"},
                "resting_hr": (
                    {"deviation": resting_hr_deviation, "weight": "10%", "impact": "Medium"}
                    if rhr_available
                    else {"deviation": None, "weight": "excluded", "impact": "not available"}
                ),
                "temperature": {"value": temperature_score, "weight": "5%", "impact": "Low"}
            }
        }

    # === Training Readiness ===

    def assess_training_readiness(
        self,
        readiness: int,
        recovery_state: Dict[str, Any],
        training_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Assess readiness for specific training types.

        Args:
            readiness: Overall readiness score
            recovery_state: Recovery state from interpret_recovery_state
            training_type: Type of training (general, endurance, strength, high_intensity)

        Returns:
            Training-specific recommendation
        """
        recovery_score = recovery_state["recovery_score"]

        # Thresholds vary by training type
        thresholds = {
            "general": {"optimal": 70, "acceptable": 55, "minimum": 45},
            "endurance": {"optimal": 70, "acceptable": 60, "minimum": 50},
            "strength": {"optimal": 75, "acceptable": 65, "minimum": 55},
            "high_intensity": {"optimal": 80, "acceptable": 70, "minimum": 60}
        }

        threshold = thresholds.get(training_type, thresholds["general"])

        if recovery_score >= threshold["optimal"]:
            recommendation = {
                "go_nogo": "GO",
                "emoji": "✅",
                "confidence": "High",
                "intensity": "Full intensity - no restrictions",
                "duration": "Normal to extended duration acceptable",
                "modifications": []
            }
        elif recovery_score >= threshold["acceptable"]:
            recommendation = {
                "go_nogo": "GO (Modified)",
                "emoji": "🟡",
                "confidence": "Medium",
                "intensity": "Reduce to 70-85% of planned intensity",
                "duration": "Reduce duration by 20-30%",
                "modifications": [
                    "Shorten work intervals",
                    "Extend rest periods",
                    "Focus on technique over load",
                    "Monitor how you feel - stop if struggling"
                ]
            }
        elif recovery_score >= threshold["minimum"]:
            recommendation = {
                "go_nogo": "CAUTION",
                "emoji": "⚠️",
                "confidence": "Medium-Low",
                "intensity": "Very light only (50-60%)",
                "duration": "Significantly shortened",
                "modifications": [
                    "Consider active recovery instead",
                    "Very light aerobic work only",
                    "No high heart rates",
                    "Listen to body carefully"
                ]
            }
        else:
            recommendation = {
                "go_nogo": "NO-GO",
                "emoji": "🔴",
                "confidence": "High",
                "intensity": "Rest day recommended",
                "duration": "N/A",
                "modifications": [
                    "Complete rest or very gentle movement",
                    "Focus on sleep and nutrition",
                    "Re-assess tomorrow",
                    "Training today may impair recovery"
                ]
            }

        recommendation.update({
            "training_type": training_type.replace("_", " ").title(),
            "readiness_score": readiness,
            "recovery_score": round(recovery_score, 1),
            "key_factors": self._identify_limiting_factors(recovery_state)
        })

        return recommendation

    def _identify_limiting_factors(self, recovery_state: Dict[str, Any]) -> list:
        """Identify which factors are limiting recovery."""
        factors = []
        signals = recovery_state.get("signals", {})

        if signals.get("hrv_balance", {}).get("value", 100) < 60:
            factors.append("Low HRV - autonomic stress")

        if signals.get("sleep", {}).get("value", 100) < 70:
            factors.append("Poor sleep quality")

        if abs(signals.get("resting_hr", {}).get("deviation", 0)) > 4:
            factors.append("Elevated resting heart rate")

        if signals.get("temperature", {}).get("value", 100) < 85:
            factors.append("Body temperature deviation")

        if not factors:
            factors.append("All metrics within acceptable ranges")

        return factors
