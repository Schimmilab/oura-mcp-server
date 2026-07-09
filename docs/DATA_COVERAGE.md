# Oura MCP Server - Complete Data Coverage

## Overview

This document provides a complete overview of all Oura Ring data accessible through the MCP server.

## ✅ Available via MCP Tools

### High-Priority Data (v0.3.0)

| Data Type | Tool Name | Parameters | Description |
|-----------|-----------|------------|-------------|
| **Sleep Sessions** | `get_sleep_sessions` | days (default: 3) | Detailed sleep periods with timestamps, including naps and biphasic sleep |
| **Heart Rate** | `get_heart_rate_data` | hours (default: 24) | Time-series HR data with zone analysis |
| **Workout Sessions** | `get_workout_sessions` | days (default: 7) | Detailed workout/activity sessions with HR and calories |
| **Daily Stress** | `get_daily_stress` | days (default: 7) | Daytime stress levels, stress load, recovery time |
| **SpO2** | `get_spo2_data` | days (default: 7) | Blood oxygen saturation during sleep |
| **VO2 Max** | `get_vo2_max` | days (default: 30) | Cardiorespiratory fitness estimates |
| **Tags** | `get_tags` | days (default: 7) | User-created tags and notes |
| **Daily Resilience** | `get_daily_resilience` | days (default: 7) | Long-term stress-recovery balance (level + sleep/daytime recovery & stress contributors) |
| **Cardiovascular Age** | `get_daily_cardiovascular_age` | days (default: 30) | Estimated vascular age (requires token scope; graceful message if unavailable) |
| **Sleep Time** | `get_sleep_time` | days (default: 7) | Optimal bedtime window + recommendation/status per day |
| **Rest Mode Periods** | `get_rest_mode_periods` | days (default: 30) | User-activated recovery-mode periods with episodes |
| **Enhanced Tags** | `get_enhanced_tags` | days (default: 7) | Named tags with time ranges and comments |
| **Ring Configuration** | `get_ring_configuration` | — | Ring hardware details (color, design, firmware, size) |

### Intelligence Tools (Phase 2)

| Tool Name | Description |
|-----------|-------------|
| `generate_daily_brief` | Comprehensive daily health summary |
| `analyze_sleep_trend` | Sleep pattern analysis over time |
| `detect_recovery_status` | Multi-signal recovery assessment |
| `assess_training_readiness` | Sport-specific training recommendations |
| `correlate_metrics` | Find relationships between metrics |
| `detect_anomalies` | Statistical anomaly detection |

## ✅ Available via MCP Resources

Resources are read-only data endpoints that Claude can access directly.

### Sleep & Recovery

| Resource URI | Description |
|--------------|-------------|
| `oura://sleep/today` | Last night's sleep data |
| `oura://sleep/yesterday` | Previous night's sleep data |
| `oura://readiness/today` | Today's readiness score and factors |
| `oura://activity/today` | Today's activity data |

### HRV & Heart Health

| Resource URI | Description |
|--------------|-------------|
| `oura://hrv/latest` | Latest HRV with baseline comparison |
| `oura://hrv/trend/7_days` | 7-day HRV trend |
| `oura://hrv/trend/30_days` | 30-day HRV trend |

### New in v0.3.0

| Resource URI | Description |
|--------------|-------------|
| `oura://personal_info` | User profile (age, weight, height, sex) |
| `oura://stress/today` | Today's daytime stress levels |
| `oura://spo2/latest` | Latest blood oxygen saturation |

## 📊 Data Types & Metrics

### Sleep Data
- **Daily Summary**: Sleep scores, efficiency, latency, timing
- **Detailed Sessions**: Exact bedtime start/end, multiple sleep periods
- **Sleep Stages**: Deep, REM, Light, Awake (duration and percentages)
- **Contributors**: Deep sleep, REM, efficiency, restfulness, latency, timing scores

### Readiness Data
- **Overall Score**: 0-100 readiness assessment
- **Contributors**: HRV balance, resting heart rate, body temperature, activity balance, previous day activity, previous night, recovery index, sleep balance, sleep regularity

### Activity Data
- **Daily Summary**: Activity score, steps, calories, movement
- **Metrics**: Total calories, active calories, target calories, METs (high/medium/low), inactivity alerts
- **Contributors**: Meet daily targets, move every hour, recovery time, stay active, training frequency, training volume

### Heart Rate Data
- **Time-Series**: Continuous HR measurements (5-minute intervals)
- **Context**: Source (sleep/awake/rest/activity)
- **Analysis**: HR zones, average, min, max, range
- **Workout HR**: Session-specific average and maximum HR

### Stress Data (Gen 3+)
- **Daytime Balance**: High stress time vs. high recovery time
- **Stress Load**: Cumulative stress throughout the day
- **Recovery Time**: Periods of physiological recovery

### SpO2 Data (Gen 3)
- **Average Percentage**: Mean blood oxygen saturation during sleep
- **Range**: Min/max values
- **Status**: Normal (≥95%), Borderline (90-94%), Low (<90%)

### VO2 Max
- **Estimate**: ml/kg/min cardiorespiratory fitness
- **Fitness Level**: Excellent/Good/Average/Below Average/Poor
- **Trend**: Historical values over time

### Workout Sessions
- **Type**: Activity type (running, cycling, walking, etc.)
- **Duration**: Total session time
- **Heart Rate**: Average and maximum HR during session
- **Calories**: Energy expenditure
- **Distance**: For distance-based activities

### Tags
- **User Notes**: Free-text notes and observations
- **Tag Types**: Custom tag categories
- **Timestamps**: When tags were created

### Personal Info
- **Demographics**: Age, biological sex
- **Physical**: Weight (kg), height (cm)
- **Contact**: Email (if available)

## 🔌 API Endpoints Used

### Core Endpoints
- `/v2/usercollection/daily_sleep` - Daily sleep summaries
- `/v2/usercollection/sleep` - Detailed sleep sessions ⭐ NEW
- `/v2/usercollection/daily_readiness` - Readiness scores
- `/v2/usercollection/daily_activity` - Activity summaries
- `/v2/usercollection/heartrate` - Heart rate time-series ⭐ NEW
- `/v2/usercollection/session` - Workout sessions ⭐ NEW
- `/v2/usercollection/personal_info` - User profile ⭐ NEW

### New Endpoints (v0.3.0)
- `/v2/usercollection/daily_stress` - Daytime stress ⭐ NEW
- `/v2/usercollection/daily_spo2` - Blood oxygen ⭐ NEW
- `/v2/usercollection/vo2_max` - Cardio fitness ⭐ NEW
- `/v2/usercollection/tag` - User tags ⭐ NEW

## 📝 Usage Examples

### Ask Claude for Data

```
"Show me my sleep sessions for the last 3 days"
"What was my heart rate during my workout yesterday?"
"Get my stress levels for the past week"
"What's my current VO2 Max?"
"Show me my blood oxygen levels"
"What tags did I create this week?"
"What's my personal profile info?"
```

### Programmatic Access

```python
# Via MCP tool
{
  "tool": "get_heart_rate_data",
  "arguments": {"hours": 24}
}

# Via MCP resource
{
  "resource": "oura://personal_info"
}
```

## ⚠️ Data Availability Notes

### Generation Requirements

| Data Type | Required Ring | Notes |
|-----------|---------------|-------|
| Sleep, Readiness, Activity | Gen 2+ | Core features |
| SpO2 | Gen 3 | Must be enabled in settings |
| Stress | Gen 3 | Daytime stress tracking |
| VO2 Max | Gen 2+ | Requires regular cardio activity |
| Heart Rate | Gen 2+ | 5-minute intervals |
| Workout Sessions | Gen 2+ | Must tag workouts in app |

### Subscription Requirements

- **Free Tier**: Basic sleep, readiness, activity
- **Paid Subscription**: Full feature access including stress, detailed analytics

## 🚫 Not Available via This Server

- **Webhooks** (`/v2/webhook/subscription`) — **out of scope by design.** Webhook
  subscriptions are managed with OAuth **application** credentials
  (`x-client-id` / `x-client-secret`), not the personal access token this MCP
  server uses. They control push-notification delivery to a public callback URL,
  not user data an assistant would read. Managing them belongs in an OAuth app,
  not this read-only data server. (With a personal access token the endpoint
  returns `401 Invalid access token`.)

## 🎯 Coverage Summary

**API Coverage: ~98%** (all user-data endpoints; only OAuth-app webhooks are out of scope)

- ✅ All core daily metrics (sleep, readiness, activity)
- ✅ Detailed session data (sleep periods, workouts)
- ✅ Time-series data (heart rate)
- ✅ Advanced metrics (stress, SpO2, VO2 Max)
- ✅ User data (personal info, tags)
- ✅ Intelligence layer (baselines, recovery, correlations, anomalies)
- ✅ Resilience, Cardiovascular Age, Sleep Time, Rest Mode, Enhanced Tags, Ring Configuration
- ⚙️ Out of scope: Webhooks (OAuth-app management, not user data)

## 📚 Related Documentation

- [Phase 2 Quick Start](PHASE2_QUICKSTART.md) - Intelligence features guide
- [MCP Design](MCP_DESIGN.md) - Architecture and design
- [Oura API Research](OURA_API_RESEARCH.md) - API documentation
- [Release Notes](../releases/) - Version history

---

*Last Updated: v0.3.0 - 2026-01-17*
