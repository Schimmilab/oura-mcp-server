"""
Weekly Report Generator

Creates comprehensive weekly health reports summarizing key metrics,
trends, achievements, and recommendations.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev
from collections import defaultdict

from .resting_hr import extract_resting_hr_values


class WeeklyReportGenerator:
    """Generates comprehensive weekly health reports."""

    def __init__(self):
        """Initialize the weekly report generator."""
        pass

    def generate_weekly_report(
        self,
        sleep_data: List[Dict],
        readiness_data: List[Dict],
        activity_data: List[Dict],
        start_date: date,
        end_date: date,
        previous_week_data: Optional[Dict] = None
    ) -> Dict:
        """
        Generate comprehensive weekly report.

        Args:
            sleep_data: Sleep session data for the week
            readiness_data: Readiness data for the week
            activity_data: Activity data for the week
            start_date: Start of the week
            end_date: End of the week
            previous_week_data: Optional data from previous week for comparison

        Returns:
            Dictionary with weekly report data
        """
        # Calculate key metrics
        sleep_metrics = self._analyze_sleep_metrics(sleep_data)
        readiness_metrics = self._analyze_readiness_metrics(readiness_data, sleep_data)
        activity_metrics = self._analyze_activity_metrics(activity_data)

        # Identify highlights and lowlights
        highlights = self._identify_highlights(sleep_data, readiness_data, activity_data)
        lowlights = self._identify_lowlights(sleep_data, readiness_data, activity_data)

        # Calculate trends
        trends = self._calculate_trends(sleep_data, readiness_data, activity_data)

        # Week-over-week comparison
        week_comparison = None
        if previous_week_data:
            week_comparison = self._compare_weeks(
                {
                    'sleep': sleep_metrics,
                    'readiness': readiness_metrics,
                    'activity': activity_metrics
                },
                previous_week_data
            )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            sleep_metrics,
            readiness_metrics,
            activity_metrics,
            trends
        )

        # Calculate weekly score
        weekly_score = self._calculate_weekly_score(
            sleep_metrics,
            readiness_metrics,
            activity_metrics
        )

        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': (end_date - start_date).days + 1
            },
            'weekly_score': weekly_score,
            'sleep_metrics': sleep_metrics,
            'readiness_metrics': readiness_metrics,
            'activity_metrics': activity_metrics,
            'highlights': highlights,
            'lowlights': lowlights,
            'trends': trends,
            'week_comparison': week_comparison,
            'recommendations': recommendations
        }

    def _analyze_sleep_metrics(self, sleep_data: List[Dict]) -> Dict:
        """Analyze sleep metrics for the week."""
        if not sleep_data:
            return {}

        scores = []
        efficiencies = []
        durations = []
        deep_sleep = []
        rem_sleep = []
        latencies = []
        restlessness = []

        for session in sleep_data:
            if not isinstance(session, dict):
                continue

            score = session.get('score')
            if score:
                scores.append(score)

            efficiency = session.get('efficiency')
            if efficiency:
                efficiencies.append(efficiency)

            duration = session.get('total_sleep_duration')
            if duration:
                durations.append(duration / 3600)  # hours

            deep = session.get('deep_sleep_duration')
            if deep:
                deep_sleep.append(deep / 3600)

            rem = session.get('rem_sleep_duration')
            if rem:
                rem_sleep.append(rem / 3600)

            latency = session.get('latency')
            if latency:
                latencies.append(latency / 60)  # minutes

            restless = session.get('restlessness')
            if restless is not None:
                restlessness.append(restless)

        return {
            'nights_tracked': len(sleep_data),
            'avg_score': mean(scores) if scores else 0,
            'avg_efficiency': mean(efficiencies) if efficiencies else 0,
            'avg_duration': mean(durations) if durations else 0,
            'avg_deep_sleep': mean(deep_sleep) if deep_sleep else 0,
            'avg_rem_sleep': mean(rem_sleep) if rem_sleep else 0,
            'avg_latency': mean(latencies) if latencies else 0,
            'avg_restlessness': mean(restlessness) if restlessness else 0,
            'best_night_score': max(scores) if scores else 0,
            'worst_night_score': min(scores) if scores else 0,
            'consistency': self._calculate_consistency(durations) if durations else 0
        }

    def _analyze_readiness_metrics(
        self,
        readiness_data: List[Dict],
        sleep_data: Optional[List[Dict]] = None,
    ) -> Dict:
        """Analyze readiness metrics for the week."""
        if not readiness_data:
            return {}

        scores = []
        hrv_balances = []
        body_temps = []
        recovery_indexes = []

        for day in readiness_data:
            if not isinstance(day, dict):
                continue

            score = day.get('score')
            if score:
                scores.append(score)

            contributors = day.get('contributors', {})
            if contributors:
                hrv = contributors.get('hrv_balance')
                if hrv:
                    hrv_balances.append(hrv)


                temp = contributors.get('body_temperature')
                if temp:
                    body_temps.append(temp)

                recovery = contributors.get('recovery_index')
                if recovery:
                    recovery_indexes.append(recovery)

        resting_hrs = extract_resting_hr_values(sleep_data or [])

        return {
            'days_tracked': len(readiness_data),
            'avg_score': mean(scores) if scores else 0,
            'avg_hrv_balance': mean(hrv_balances) if hrv_balances else 0,
            # ⛔ Real bpm from the nightly trough, NOT contributors.resting_heart_rate
            # — that is a 0-100 score and was printed here as "bpm" until v0.9.2.
            'avg_resting_hr': mean(resting_hrs) if resting_hrs else 0,
            'avg_body_temp': mean(body_temps) if body_temps else 0,
            'avg_recovery_index': mean(recovery_indexes) if recovery_indexes else 0,
            'best_day_score': max(scores) if scores else 0,
            'worst_day_score': min(scores) if scores else 0,
            'readiness_variability': stdev(scores) if len(scores) > 1 else 0
        }

    def _analyze_activity_metrics(self, activity_data: List[Dict]) -> Dict:
        """Analyze activity metrics for the week."""
        if not activity_data:
            return {}

        scores = []
        steps = []
        calories = []
        active_calories = []
        training_volume = []
        training_frequency = []

        for day in activity_data:
            if not isinstance(day, dict):
                continue

            score = day.get('score')
            if score:
                scores.append(score)

            step_count = day.get('steps')
            if step_count:
                steps.append(step_count)

            cal = day.get('total_calories')
            if cal:
                calories.append(cal)

            active_cal = day.get('active_calories')
            if active_cal:
                active_calories.append(active_cal)

            # Training metrics
            high_intensity = day.get('high_activity_time', 0) or 0
            medium_intensity = day.get('medium_activity_time', 0) or 0
            volume = (high_intensity + medium_intensity) / 60  # minutes

            if volume > 0:
                training_volume.append(volume)
                training_frequency.append(1)

        total_steps = sum(steps) if steps else 0
        total_calories = sum(calories) if calories else 0
        total_active_calories = sum(active_calories) if active_calories else 0
        total_training_days = len(training_frequency)
        avg_training_volume = mean(training_volume) if training_volume else 0

        return {
            'days_tracked': len(activity_data),
            'avg_score': mean(scores) if scores else 0,
            'total_steps': total_steps,
            'avg_steps': mean(steps) if steps else 0,
            'total_calories': total_calories,
            'avg_calories': mean(calories) if calories else 0,
            'total_active_calories': total_active_calories,
            'training_days': total_training_days,
            'avg_training_volume': avg_training_volume,
            'best_day_score': max(scores) if scores else 0,
            'worst_day_score': min(scores) if scores else 0
        }

    def _identify_highlights(
        self,
        sleep_data: List[Dict],
        readiness_data: List[Dict],
        activity_data: List[Dict]
    ) -> List[Dict]:
        """Identify weekly highlights/achievements."""
        highlights = []

        # Sleep highlights
        if sleep_data:
            scores = [s.get('score', 0) for s in sleep_data if isinstance(s, dict)]
            if scores:
                avg_score = mean(scores)
                best_score = max(scores)

                if best_score >= 90:
                    highlights.append({
                        'emoji': '🌟',
                        'category': 'sleep',
                        'title': 'Outstanding Sleep',
                        'description': f'Achieved exceptional sleep score of {best_score}'
                    })
                elif avg_score >= 80:
                    highlights.append({
                        'emoji': '😴',
                        'category': 'sleep',
                        'title': 'Excellent Sleep Week',
                        'description': f'Average sleep score of {avg_score:.0f}'
                    })

            # Check for consistency
            durations = [s.get('total_sleep_duration', 0) / 3600 for s in sleep_data if isinstance(s, dict)]
            if durations and len(durations) >= 5:
                consistency = self._calculate_consistency(durations)
                if consistency >= 85:
                    highlights.append({
                        'emoji': '🎯',
                        'category': 'sleep',
                        'title': 'Great Sleep Consistency',
                        'description': f'Maintained consistent sleep schedule ({consistency:.0f}% consistency)'
                    })

        # Readiness highlights
        if readiness_data:
            scores = [r.get('score', 0) for r in readiness_data if isinstance(r, dict)]
            if scores:
                avg_score = mean(scores)
                if avg_score >= 85:
                    highlights.append({
                        'emoji': '💪',
                        'category': 'readiness',
                        'title': 'High Readiness Week',
                        'description': f'Average readiness score of {avg_score:.0f}'
                    })

        # Activity highlights
        if activity_data:
            total_steps = sum([a.get('steps', 0) for a in activity_data if isinstance(a, dict)])

            if total_steps >= 70000:  # 10k/day average
                highlights.append({
                    'emoji': '🚶',
                    'category': 'activity',
                    'title': 'Step Goal Achieved',
                    'description': f'Walked {total_steps:,} steps this week'
                })

            # Check training frequency
            training_days = sum([
                1 for a in activity_data
                if isinstance(a, dict) and (a.get('high_activity_time', 0) or 0) > 0
            ])

            if training_days >= 4:
                highlights.append({
                    'emoji': '🏋️',
                    'category': 'activity',
                    'title': 'Consistent Training',
                    'description': f'Trained {training_days} days this week'
                })

        return highlights

    def _identify_lowlights(
        self,
        sleep_data: List[Dict],
        readiness_data: List[Dict],
        activity_data: List[Dict]
    ) -> List[Dict]:
        """Identify areas needing attention."""
        lowlights = []

        # Sleep concerns
        if sleep_data:
            scores = [s.get('score', 0) for s in sleep_data if isinstance(s, dict)]
            if scores:
                avg_score = mean(scores)
                worst_score = min(scores)

                if worst_score < 60:
                    lowlights.append({
                        'emoji': '⚠️',
                        'category': 'sleep',
                        'title': 'Poor Sleep Night',
                        'description': f'Sleep score dropped to {worst_score}',
                        'priority': 'high'
                    })
                elif avg_score < 70:
                    lowlights.append({
                        'emoji': '😴',
                        'category': 'sleep',
                        'title': 'Below Average Sleep',
                        'description': f'Average sleep score was {avg_score:.0f}',
                        'priority': 'medium'
                    })

            # Check duration
            durations = [s.get('total_sleep_duration', 0) / 3600 for s in sleep_data if isinstance(s, dict)]
            if durations:
                avg_duration = mean(durations)
                if avg_duration < 7:
                    lowlights.append({
                        'emoji': '⏰',
                        'category': 'sleep',
                        'title': 'Insufficient Sleep',
                        'description': f'Averaged only {avg_duration:.1f}h per night',
                        'priority': 'high'
                    })

        # Readiness concerns
        if readiness_data:
            scores = [r.get('score', 0) for r in readiness_data if isinstance(r, dict)]
            if scores:
                avg_score = mean(scores)
                if avg_score < 70:
                    lowlights.append({
                        'emoji': '🔋',
                        'category': 'readiness',
                        'title': 'Low Readiness',
                        'description': f'Average readiness was {avg_score:.0f}',
                        'priority': 'medium'
                    })

        # Activity concerns
        if activity_data:
            total_steps = sum([a.get('steps', 0) for a in activity_data if isinstance(a, dict)])
            avg_steps = total_steps / len(activity_data) if activity_data else 0

            if avg_steps < 5000:
                lowlights.append({
                    'emoji': '🚶',
                    'category': 'activity',
                    'title': 'Low Activity',
                    'description': f'Averaged only {avg_steps:.0f} steps per day',
                    'priority': 'medium'
                })

        return lowlights

    def _calculate_trends(
        self,
        sleep_data: List[Dict],
        readiness_data: List[Dict],
        activity_data: List[Dict]
    ) -> Dict:
        """Calculate weekly trends."""
        trends = {}

        # Sleep trend
        if sleep_data and len(sleep_data) >= 3:
            scores = [s.get('score', 0) for s in sleep_data if isinstance(s, dict)]
            if scores:
                trend = self._calculate_trend_direction(scores)
                trends['sleep'] = {
                    'direction': trend,
                    'values': scores
                }

        # Readiness trend
        if readiness_data and len(readiness_data) >= 3:
            scores = [r.get('score', 0) for r in readiness_data if isinstance(r, dict)]
            if scores:
                trend = self._calculate_trend_direction(scores)
                trends['readiness'] = {
                    'direction': trend,
                    'values': scores
                }

        # Activity trend
        if activity_data and len(activity_data) >= 3:
            scores = [a.get('score', 0) for a in activity_data if isinstance(a, dict)]
            if scores:
                trend = self._calculate_trend_direction(scores)
                trends['activity'] = {
                    'direction': trend,
                    'values': scores
                }

        return trends

    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Calculate if values are trending up, down, or stable."""
        if len(values) < 3:
            return 'stable'

        # Simple linear regression
        n = len(values)
        x = list(range(n))
        y = values

        x_mean = mean(x)
        y_mean = mean(y)

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 'stable'

        slope = numerator / denominator

        # Determine trend based on slope
        if slope > 2:
            return 'improving'
        elif slope < -2:
            return 'declining'
        else:
            return 'stable'

    def _compare_weeks(self, current_week: Dict, previous_week: Dict) -> Dict:
        """Compare current week to previous week."""
        comparison = {}

        # Sleep comparison
        if 'sleep' in current_week and 'sleep' in previous_week:
            curr_sleep = current_week['sleep']
            prev_sleep = previous_week['sleep']

            comparison['sleep'] = {
                'score_change': curr_sleep.get('avg_score', 0) - prev_sleep.get('avg_score', 0),
                'duration_change': curr_sleep.get('avg_duration', 0) - prev_sleep.get('avg_duration', 0),
                'efficiency_change': curr_sleep.get('avg_efficiency', 0) - prev_sleep.get('avg_efficiency', 0)
            }

        # Readiness comparison
        if 'readiness' in current_week and 'readiness' in previous_week:
            curr_ready = current_week['readiness']
            prev_ready = previous_week['readiness']

            comparison['readiness'] = {
                'score_change': curr_ready.get('avg_score', 0) - prev_ready.get('avg_score', 0)
            }

        # Activity comparison
        if 'activity' in current_week and 'activity' in previous_week:
            curr_act = current_week['activity']
            prev_act = previous_week['activity']

            comparison['activity'] = {
                'steps_change': curr_act.get('total_steps', 0) - prev_act.get('total_steps', 0),
                'training_days_change': curr_act.get('training_days', 0) - prev_act.get('training_days', 0)
            }

        return comparison

    def _generate_recommendations(
        self,
        sleep_metrics: Dict,
        readiness_metrics: Dict,
        activity_metrics: Dict,
        trends: Dict
    ) -> List[Dict]:
        """Generate personalized recommendations for next week."""
        recommendations = []

        # Sleep recommendations
        if sleep_metrics:
            avg_score = sleep_metrics.get('avg_score', 0)
            avg_duration = sleep_metrics.get('avg_duration', 0)
            consistency = sleep_metrics.get('consistency', 0)

            if avg_score < 75:
                recommendations.append({
                    'category': 'sleep',
                    'priority': 'high',
                    'title': 'Improve Sleep Quality',
                    'action': 'Focus on sleep hygiene: consistent bedtime, dark room, cool temperature'
                })

            if avg_duration < 7.5:
                recommendations.append({
                    'category': 'sleep',
                    'priority': 'high',
                    'title': 'Increase Sleep Duration',
                    'action': f'Target 8 hours of sleep (currently averaging {avg_duration:.1f}h)'
                })

            if consistency < 70:
                recommendations.append({
                    'category': 'sleep',
                    'priority': 'medium',
                    'title': 'Improve Sleep Consistency',
                    'action': 'Go to bed and wake up at the same time daily'
                })

        # Readiness recommendations
        if readiness_metrics:
            avg_score = readiness_metrics.get('avg_score', 0)

            if avg_score < 70:
                recommendations.append({
                    'category': 'readiness',
                    'priority': 'high',
                    'title': 'Focus on Recovery',
                    'action': 'Reduce training intensity and prioritize rest'
                })

        # Activity recommendations
        if activity_metrics:
            avg_steps = activity_metrics.get('avg_steps', 0)
            training_days = activity_metrics.get('training_days', 0)

            if avg_steps < 7500:
                recommendations.append({
                    'category': 'activity',
                    'priority': 'medium',
                    'title': 'Increase Daily Movement',
                    'action': f'Aim for 10,000 steps per day (currently {avg_steps:.0f})'
                })

            if training_days < 3:
                recommendations.append({
                    'category': 'activity',
                    'priority': 'medium',
                    'title': 'Add Training Sessions',
                    'action': f'Target 3-4 training sessions per week (currently {training_days})'
                })

        return recommendations

    def _calculate_weekly_score(
        self,
        sleep_metrics: Dict,
        readiness_metrics: Dict,
        activity_metrics: Dict
    ) -> Dict:
        """Calculate overall weekly score."""
        # Weight: Sleep 40%, Readiness 30%, Activity 30%
        sleep_score = sleep_metrics.get('avg_score', 0) * 0.4
        readiness_score = readiness_metrics.get('avg_score', 0) * 0.3
        activity_score = activity_metrics.get('avg_score', 0) * 0.3

        total_score = sleep_score + readiness_score + activity_score

        # Classify week
        if total_score >= 85:
            classification = "🌟 Excellent Week"
            emoji = "🌟"
        elif total_score >= 75:
            classification = "👍 Good Week"
            emoji = "👍"
        elif total_score >= 65:
            classification = "➖ Average Week"
            emoji = "➖"
        else:
            classification = "⚠️ Challenging Week"
            emoji = "⚠️"

        return {
            'total_score': round(total_score, 1),
            'classification': classification,
            'emoji': emoji,
            'components': {
                'sleep': round(sleep_metrics.get('avg_score', 0), 1),
                'readiness': round(readiness_metrics.get('avg_score', 0), 1),
                'activity': round(activity_metrics.get('avg_score', 0), 1)
            }
        }

    def _calculate_consistency(self, values: List[float]) -> float:
        """Calculate consistency score (0-100) based on standard deviation."""
        if len(values) < 2:
            return 100.0

        avg = mean(values)
        std = stdev(values)

        if avg == 0:
            return 100.0

        # Convert coefficient of variation to consistency score
        cv = (std / avg) * 100
        consistency = max(0, 100 - cv * 10)

        return consistency

    def format_weekly_report(self, report: Dict) -> str:
        """Generate human-readable weekly report."""
        period = report['period']
        start = period['start_date']
        end = period['end_date']

        lines = [
            f"# 📅 Weekly Health Report",
            "",
            f"**Week:** {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}",
            "",
            "---",
            ""
        ]

        # Overall score
        weekly_score = report['weekly_score']
        lines.extend([
            f"## {weekly_score['emoji']} Overall: {weekly_score['classification']}",
            "",
            f"**Weekly Score:** {weekly_score['total_score']}/100",
            "",
            "**Component Scores:**",
            f"- 😴 Sleep: {weekly_score['components']['sleep']}/100",
            f"- 🔋 Readiness: {weekly_score['components']['readiness']}/100",
            f"- 🏃 Activity: {weekly_score['components']['activity']}/100",
            "",
        ])

        # Week-over-week comparison
        if report.get('week_comparison'):
            comp = report['week_comparison']
            lines.extend([
                "## 📊 Week-over-Week Changes",
                "",
            ])

            if 'sleep' in comp:
                sleep_change = comp['sleep']['score_change']
                arrow = "📈" if sleep_change > 0 else "📉" if sleep_change < 0 else "➖"
                lines.append(f"- Sleep Score: {arrow} {sleep_change:+.1f} points")

            if 'readiness' in comp:
                ready_change = comp['readiness']['score_change']
                arrow = "📈" if ready_change > 0 else "📉" if ready_change < 0 else "➖"
                lines.append(f"- Readiness Score: {arrow} {ready_change:+.1f} points")

            if 'activity' in comp:
                steps_change = comp['activity']['steps_change']
                arrow = "📈" if steps_change > 0 else "📉" if steps_change < 0 else "➖"
                lines.append(f"- Total Steps: {arrow} {steps_change:+,} steps")

            lines.append("")

        # Highlights
        if report.get('highlights'):
            lines.extend([
                "## ✨ Week Highlights",
                "",
            ])
            for highlight in report['highlights']:
                lines.append(f"- {highlight['emoji']} **{highlight['title']}** - {highlight['description']}")
            lines.append("")

        # Lowlights
        if report.get('lowlights'):
            lines.extend([
                "## ⚠️ Areas for Improvement",
                "",
            ])
            for lowlight in report['lowlights']:
                lines.append(f"- {lowlight['emoji']} **{lowlight['title']}** - {lowlight['description']}")
            lines.append("")

        # Detailed metrics
        lines.extend([
            "## 📈 Detailed Metrics",
            "",
        ])

        # Sleep details
        sleep = report['sleep_metrics']
        if sleep:
            lines.extend([
                "### 😴 Sleep",
                "",
                f"- **Average Score:** {sleep['avg_score']:.0f}/100",
                f"- **Average Duration:** {sleep['avg_duration']:.1f} hours",
                f"- **Average Efficiency:** {sleep['avg_efficiency']:.0f}%",
                f"- **Deep Sleep:** {sleep['avg_deep_sleep']:.1f}h/night",
                f"- **REM Sleep:** {sleep['avg_rem_sleep']:.1f}h/night",
                f"- **Sleep Latency:** {sleep['avg_latency']:.0f} minutes",
                f"- **Best Night:** {sleep['best_night_score']:.0f}",
                f"- **Consistency:** {sleep['consistency']:.0f}%",
                "",
            ])

        # Readiness details
        readiness = report['readiness_metrics']
        if readiness:
            lines.extend([
                "### 🔋 Readiness",
                "",
                f"- **Average Score:** {readiness['avg_score']:.0f}/100",
                f"- **HRV Balance:** {readiness['avg_hrv_balance']:.0f}",
                f"- **Resting Heart Rate:** {readiness['avg_resting_hr']:.0f} bpm",
                f"- **Best Day:** {readiness['best_day_score']:.0f}",
                "",
            ])

        # Activity details
        activity = report['activity_metrics']
        if activity:
            lines.extend([
                "### 🏃 Activity",
                "",
                f"- **Average Score:** {activity['avg_score']:.0f}/100",
                f"- **Total Steps:** {activity['total_steps']:,}",
                f"- **Average Steps:** {activity['avg_steps']:,.0f}/day",
                f"- **Total Calories:** {activity['total_calories']:,}",
                f"- **Training Days:** {activity['training_days']}/{activity['days_tracked']}",
                "",
            ])

        # Trends
        if report.get('trends'):
            lines.extend([
                "## 📉 Trends",
                "",
            ])

            trends = report['trends']
            trend_emojis = {
                'improving': '📈',
                'stable': '➖',
                'declining': '📉'
            }

            if 'sleep' in trends:
                emoji = trend_emojis.get(trends['sleep']['direction'], '➖')
                lines.append(f"- Sleep: {emoji} {trends['sleep']['direction'].title()}")

            if 'readiness' in trends:
                emoji = trend_emojis.get(trends['readiness']['direction'], '➖')
                lines.append(f"- Readiness: {emoji} {trends['readiness']['direction'].title()}")

            if 'activity' in trends:
                emoji = trend_emojis.get(trends['activity']['direction'], '➖')
                lines.append(f"- Activity: {emoji} {trends['activity']['direction'].title()}")

            lines.append("")

        # Recommendations
        if report.get('recommendations'):
            lines.extend([
                "## 💡 Recommendations for Next Week",
                "",
            ])

            # Group by priority
            high_priority = [r for r in report['recommendations'] if r.get('priority') == 'high']
            medium_priority = [r for r in report['recommendations'] if r.get('priority') == 'medium']

            if high_priority:
                lines.append("**High Priority:**")
                for rec in high_priority:
                    lines.append(f"- 🔴 **{rec['title']}** - {rec['action']}")
                lines.append("")

            if medium_priority:
                lines.append("**Medium Priority:**")
                for rec in medium_priority:
                    lines.append(f"- 🟡 **{rec['title']}** - {rec['action']}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "*Keep up the great work! Focus on consistency and gradual improvements.*",
            ""
        ])

        return "\n".join(lines)
