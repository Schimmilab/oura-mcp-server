"""
Supplement Correlation Analysis

Correlates supplement/intervention tags with sleep and health metrics to identify
what actually works for improving your health outcomes.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev
from collections import defaultdict


class SupplementCorrelation:
    """Analyzes correlation between tags (supplements, interventions) and health metrics."""

    def __init__(self):
        """Initialize the supplement correlation analyzer."""
        pass

    def analyze_tag_correlations(
        self,
        sleep_data: List[Dict],
        tags_data: List[Dict],
        min_occurrences: int = 3
    ) -> Dict:
        """
        Analyze correlations between tags and sleep/health metrics.

        Args:
            sleep_data: List of sleep session data
            tags_data: List of tag data (supplements, interventions, notes)
            min_occurrences: Minimum number of tag occurrences to analyze (default: 3)

        Returns:
            Dictionary with correlation analysis results
        """
        if not sleep_data or not tags_data:
            return self._empty_result("Insufficient data for analysis")

        # Index sleep data by date
        sleep_by_date = self._index_sleep_by_date(sleep_data)

        # Group tags by tag text and collect associated sleep data
        tag_groups = self._group_tags_with_sleep_data(tags_data, sleep_by_date)

        # Filter out tags with too few occurrences
        tag_groups = {
            tag: data for tag, data in tag_groups.items()
            if len(data['sleep_sessions']) >= min_occurrences
        }

        if not tag_groups:
            return self._empty_result(
                f"No tags found with at least {min_occurrences} occurrences"
            )

        # Calculate baseline metrics (all days without specific tags)
        baseline_metrics = self._calculate_baseline_metrics(sleep_by_date, tag_groups)

        # Analyze each tag
        tag_analyses = {}
        for tag_name, tag_data in tag_groups.items():
            analysis = self._analyze_single_tag(
                tag_name,
                tag_data,
                baseline_metrics
            )
            tag_analyses[tag_name] = analysis

        # Rank tags by effectiveness
        ranked_tags = self._rank_tags_by_effectiveness(tag_analyses)

        return {
            'tag_analyses': tag_analyses,
            'ranked_tags': ranked_tags,
            'baseline_metrics': baseline_metrics,
            'total_tags_analyzed': len(tag_analyses),
            'total_sleep_sessions': len(sleep_by_date)
        }

    def _index_sleep_by_date(self, sleep_data: List[Dict]) -> Dict:
        """Index sleep data by date for efficient lookup."""
        sleep_by_date = {}

        for session in sleep_data:
            if not isinstance(session, dict):
                continue

            # Get bedtime date
            bedtime_str = session.get("bedtime_start")
            if not bedtime_str:
                continue

            try:
                bedtime_dt = datetime.fromisoformat(bedtime_str.replace('Z', '+00:00'))
                date_key = bedtime_dt.date().isoformat()

                # Store sleep data with calculated metrics
                sleep_by_date[date_key] = {
                    'session': session,
                    'score': session.get('score', 0),
                    'efficiency': session.get('efficiency', 0),
                    'duration': session.get('total_sleep_duration', 0) / 3600,  # hours
                    'deep_sleep': session.get('deep_sleep_duration', 0) / 3600,
                    'rem_sleep': session.get('rem_sleep_duration', 0) / 3600,
                    'latency': session.get('latency', 0) / 60,  # minutes
                    'restlessness': session.get('restlessness', 0),
                    'hrv': session.get('heart_rate', {}).get('average', 0) if isinstance(session.get('heart_rate'), dict) else 0,
                    # The nightly trough is the resting pulse; average_heart_rate is
                    # the mean across the whole night and sits well above it.
                    'resting_hr': session.get('lowest_heart_rate', 0)
                }
            except (ValueError, TypeError, AttributeError):
                continue

        return sleep_by_date

    def _group_tags_with_sleep_data(
        self,
        tags_data: List[Dict],
        sleep_by_date: Dict
    ) -> Dict:
        """Group tags and associate with sleep data from same/next day."""
        tag_groups = defaultdict(lambda: {
            'occurrences': 0,
            'sleep_sessions': [],
            'dates': []
        })

        for tag_entry in tags_data:
            if not isinstance(tag_entry, dict):
                continue

            tag_text = tag_entry.get('tag', '').strip()
            tag_date_str = tag_entry.get('day', '').strip()

            if not tag_text or not tag_date_str:
                continue

            # Normalize tag text (case-insensitive)
            tag_text = tag_text.lower()

            try:
                tag_date = datetime.fromisoformat(tag_date_str).date()

                # Look for sleep session on same day and next day
                # (supplements taken during the day affect that night's sleep)
                sleep_session = None
                sleep_date = None

                # Try same day first
                same_day_key = tag_date.isoformat()
                if same_day_key in sleep_by_date:
                    sleep_session = sleep_by_date[same_day_key]
                    sleep_date = same_day_key
                else:
                    # Try next day
                    next_day = tag_date + timedelta(days=1)
                    next_day_key = next_day.isoformat()
                    if next_day_key in sleep_by_date:
                        sleep_session = sleep_by_date[next_day_key]
                        sleep_date = next_day_key

                if sleep_session:
                    tag_groups[tag_text]['occurrences'] += 1
                    tag_groups[tag_text]['sleep_sessions'].append(sleep_session)
                    tag_groups[tag_text]['dates'].append(sleep_date)

            except (ValueError, TypeError):
                continue

        return dict(tag_groups)

    def _calculate_baseline_metrics(
        self,
        sleep_by_date: Dict,
        tag_groups: Dict
    ) -> Dict:
        """Calculate baseline metrics from days without any analyzed tags."""
        # Get all dates that have tags
        tagged_dates = set()
        for tag_data in tag_groups.values():
            tagged_dates.update(tag_data['dates'])

        # Get sleep data from untagged dates
        baseline_sessions = [
            sleep_data for date_key, sleep_data in sleep_by_date.items()
            if date_key not in tagged_dates
        ]

        if not baseline_sessions:
            # If all days are tagged, use overall average
            baseline_sessions = list(sleep_by_date.values())

        return self._calculate_metrics(baseline_sessions)

    def _calculate_metrics(self, sleep_sessions: List[Dict]) -> Dict:
        """Calculate average metrics from sleep sessions."""
        if not sleep_sessions:
            return {}

        metrics = {
            'score': [],
            'efficiency': [],
            'duration': [],
            'deep_sleep': [],
            'rem_sleep': [],
            'latency': [],
            'restlessness': [],
            'resting_hr': []
        }

        for session in sleep_sessions:
            for metric in metrics.keys():
                value = session.get(metric)
                if value is not None and value > 0:
                    metrics[metric].append(value)

        # Calculate averages and std dev
        result = {}
        for metric, values in metrics.items():
            if values:
                result[f'{metric}_mean'] = mean(values)
                result[f'{metric}_std'] = stdev(values) if len(values) > 1 else 0
                result[f'{metric}_count'] = len(values)
            else:
                result[f'{metric}_mean'] = 0
                result[f'{metric}_std'] = 0
                result[f'{metric}_count'] = 0

        return result

    def _analyze_single_tag(
        self,
        tag_name: str,
        tag_data: Dict,
        baseline_metrics: Dict
    ) -> Dict:
        """Analyze a single tag's correlation with metrics."""
        sleep_sessions = tag_data['sleep_sessions']
        tag_metrics = self._calculate_metrics(sleep_sessions)

        # Calculate differences from baseline
        differences = {}
        effect_sizes = {}

        key_metrics = ['score', 'efficiency', 'duration', 'deep_sleep', 'rem_sleep', 'latency', 'restlessness', 'resting_hr']

        for metric in key_metrics:
            tag_mean = tag_metrics.get(f'{metric}_mean', 0)
            baseline_mean = baseline_metrics.get(f'{metric}_mean', 0)
            baseline_std = baseline_metrics.get(f'{metric}_std', 1)

            if baseline_mean > 0:
                diff = tag_mean - baseline_mean
                pct_change = (diff / baseline_mean) * 100

                # Calculate effect size (Cohen's d)
                if baseline_std > 0:
                    effect_size = diff / baseline_std
                else:
                    effect_size = 0

                differences[metric] = {
                    'absolute': diff,
                    'percentage': pct_change,
                    'tag_value': tag_mean,
                    'baseline_value': baseline_mean
                }
                effect_sizes[metric] = effect_size

        # Calculate overall effectiveness score
        effectiveness_score = self._calculate_effectiveness_score(differences, effect_sizes)

        # Determine if tag is beneficial, neutral, or harmful
        classification = self._classify_tag_effect(effectiveness_score, differences)

        return {
            'tag_name': tag_name,
            'occurrences': tag_data['occurrences'],
            'metrics': tag_metrics,
            'differences': differences,
            'effect_sizes': effect_sizes,
            'effectiveness_score': effectiveness_score,
            'classification': classification,
            'dates': tag_data['dates']
        }

    def _calculate_effectiveness_score(
        self,
        differences: Dict,
        effect_sizes: Dict
    ) -> float:
        """
        Calculate overall effectiveness score.

        Weights:
        - Sleep Score: 30%
        - Efficiency: 20%
        - Deep Sleep: 20%
        - REM Sleep: 15%
        - Duration: 10%
        - Latency: 5% (negative is good)
        """
        weights = {
            'score': 0.30,
            'efficiency': 0.20,
            'deep_sleep': 0.20,
            'rem_sleep': 0.15,
            'duration': 0.10,
            'latency': -0.05  # Negative because lower latency is better
        }

        score = 0
        for metric, weight in weights.items():
            effect_size = effect_sizes.get(metric, 0)
            score += effect_size * weight * 100  # Scale to 0-100 range

        return score

    def _classify_tag_effect(
        self,
        effectiveness_score: float,
        differences: Dict
    ) -> Dict:
        """Classify tag effect as beneficial, neutral, or harmful."""
        if effectiveness_score >= 10:
            classification = "✅ Highly Beneficial"
            emoji = "✅"
        elif effectiveness_score >= 5:
            classification = "👍 Beneficial"
            emoji = "👍"
        elif effectiveness_score >= 2:
            classification = "🔆 Slightly Beneficial"
            emoji = "🔆"
        elif effectiveness_score >= -2:
            classification = "➖ Neutral"
            emoji = "➖"
        elif effectiveness_score >= -5:
            classification = "⚠️ Slightly Harmful"
            emoji = "⚠️"
        else:
            classification = "❌ Harmful"
            emoji = "❌"

        # Check for sleep score improvement
        score_change = differences.get('score', {}).get('percentage', 0)

        return {
            'label': classification,
            'emoji': emoji,
            'score': effectiveness_score,
            'sleep_score_change': score_change
        }

    def _rank_tags_by_effectiveness(self, tag_analyses: Dict) -> List[Tuple[str, float, str]]:
        """Rank tags by effectiveness score."""
        ranked = []
        for tag_name, analysis in tag_analyses.items():
            ranked.append((
                tag_name,
                analysis['effectiveness_score'],
                analysis['classification']['emoji']
            ))

        # Sort by effectiveness score (descending)
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def _empty_result(self, reason: str) -> Dict:
        """Return empty result with reason."""
        return {
            'error': reason,
            'tag_analyses': {},
            'ranked_tags': [],
            'baseline_metrics': {}
        }

    def generate_correlation_report(self, analysis: Dict, top_n: int = 10) -> str:
        """Generate human-readable supplement correlation report."""
        if 'error' in analysis:
            return f"❌ Unable to analyze correlations: {analysis['error']}"

        report_lines = [
            "# 💊 Supplement & Intervention Correlation Analysis",
            "",
            f"*Analyzed {analysis['total_tags_analyzed']} tags across {analysis['total_sleep_sessions']} sleep sessions*",
            "",
        ]

        # Top beneficial supplements
        ranked = analysis['ranked_tags']
        if ranked:
            report_lines.extend([
                "## 🏆 Most Effective Interventions",
                "",
            ])

            beneficial = [t for t in ranked if t[1] >= 2][:top_n]
            if beneficial:
                for i, (tag, score, emoji) in enumerate(beneficial, 1):
                    analysis_data = analysis['tag_analyses'][tag]
                    occurrences = analysis_data['occurrences']
                    score_change = analysis_data['differences']['score']['percentage']

                    report_lines.append(
                        f"{i}. {emoji} **{tag.title()}** "
                        f"(+{score_change:.1f}% sleep score, n={occurrences}, effect={score:.1f})"
                    )
                report_lines.append("")
            else:
                report_lines.append("*No highly beneficial interventions found*")
                report_lines.append("")

            # Harmful/negative correlations
            harmful = [t for t in ranked if t[1] < -2][:5]
            if harmful:
                report_lines.extend([
                    "## ⚠️ Interventions to Avoid",
                    "",
                ])
                for tag, score, emoji in harmful:
                    analysis_data = analysis['tag_analyses'][tag]
                    occurrences = analysis_data['occurrences']
                    score_change = analysis_data['differences']['score']['percentage']

                    report_lines.append(
                        f"- {emoji} **{tag.title()}** "
                        f"({score_change:+.1f}% sleep score, n={occurrences}, effect={score:.1f})"
                    )
                report_lines.append("")

        # Detailed analysis of top tags
        report_lines.extend([
            "## 📊 Detailed Analysis",
            "",
        ])

        top_tags = ranked[:5]  # Show top 5 in detail
        baseline = analysis['baseline_metrics']

        for tag_name, _, emoji in top_tags:
            tag_analysis = analysis['tag_analyses'][tag_name]
            diff = tag_analysis['differences']

            report_lines.extend([
                f"### {emoji} {tag_name.title()}",
                "",
                f"**Occurrences:** {tag_analysis['occurrences']} times",
                f"**Effectiveness Score:** {tag_analysis['effectiveness_score']:.1f}",
                f"**Classification:** {tag_analysis['classification']['label']}",
                "",
                "**Impact on Metrics:**",
                "",
            ])

            # Show key metrics
            key_metrics = [
                ('Sleep Score', 'score', 'points', False),
                ('Sleep Efficiency', 'efficiency', '%', False),
                ('Sleep Duration', 'duration', 'hours', False),
                ('Deep Sleep', 'deep_sleep', 'hours', False),
                ('REM Sleep', 'rem_sleep', 'hours', False),
                ('Sleep Latency', 'latency', 'min', True),  # Lower is better
            ]

            for label, metric, unit, lower_better in key_metrics:
                if metric in diff:
                    d = diff[metric]
                    change = d['absolute']
                    pct = d['percentage']
                    tag_val = d['tag_value']
                    base_val = d['baseline_value']

                    # Determine if change is positive or negative
                    if lower_better:
                        indicator = "📉" if change < 0 else "📈"
                        good_change = change < -1
                    else:
                        indicator = "📈" if change > 0 else "📉"
                        good_change = abs(pct) > 2 and change > 0

                    change_str = f"{change:+.2f}" if abs(change) >= 0.1 else f"{change:+.3f}"

                    if good_change:
                        report_lines.append(
                            f"- **{label}:** {tag_val:.1f}{unit} vs {base_val:.1f}{unit} "
                            f"({change_str} / {pct:+.1f}%) {indicator}"
                        )
                    else:
                        report_lines.append(
                            f"- {label}: {tag_val:.1f}{unit} vs {base_val:.1f}{unit} "
                            f"({change_str} / {pct:+.1f}%)"
                        )

            report_lines.append("")

        # Baseline reference
        report_lines.extend([
            "## 📏 Baseline Metrics",
            "",
            "*Average metrics on days without any tracked interventions:*",
            "",
            f"- Sleep Score: {baseline.get('score_mean', 0):.1f}",
            f"- Sleep Efficiency: {baseline.get('efficiency_mean', 0):.1f}%",
            f"- Sleep Duration: {baseline.get('duration_mean', 0):.1f} hours",
            f"- Deep Sleep: {baseline.get('deep_sleep_mean', 0):.1f} hours",
            f"- REM Sleep: {baseline.get('rem_sleep_mean', 0):.1f} hours",
            f"- Sleep Latency: {baseline.get('latency_mean', 0):.1f} minutes",
            "",
        ])

        # Recommendations
        report_lines.extend([
            "## 💡 Recommendations",
            "",
        ])

        if beneficial:
            report_lines.append("**Continue or increase:**")
            for tag, score, emoji in beneficial[:3]:
                report_lines.append(f"- {emoji} {tag.title()}")
            report_lines.append("")

        if harmful:
            report_lines.append("**Consider eliminating:**")
            for tag, score, emoji in harmful[:3]:
                report_lines.append(f"- {emoji} {tag.title()}")
            report_lines.append("")

        report_lines.extend([
            "**Note:** Correlation does not imply causation. These patterns suggest potential relationships",
            "but may be influenced by other factors. Consider controlled testing of promising interventions.",
            "",
        ])

        return "\n".join(report_lines)
