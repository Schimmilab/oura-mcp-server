# Changelog

All notable changes to the Oura MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.9.4] - 2026-09-13

### 🐛 Fixed — the night was invisible whenever it began after midnight

Two defects, found together because the second hid the first. Both were found by
a control, not by reading the code.

**1. `/sleep` dropped a night that started after midnight** (`api/client.py`)

Oura filters this endpoint on `bedtime_start` and treats `end_date` as
**exclusive** — unlike the `daily_*` endpoints, which filter on `day`
inclusively. A night beginning at 02:20 carries `day == end_date` and is still
not returned.

The damage was not an empty result, which someone would have noticed. What came
back was the 23-minute doze from the previous evening, so every caller reading
"the latest session" got a **4-minute fragment instead of a 9-hour night**.
Measured against a real account:

```
end_date=2026-09-13  ->  only type="sleep",      start 09-12T23:06
end_date=2026-09-14  ->  plus type="long_sleep", start 09-13T02:20, 7h43m
```

Cross-checked against two independent instruments for that night: a Withings
mattress sensor logged 02:16–11:28 and a CPAP 02:16:20 for 9.0 h. Three devices
agreed within four minutes; only the query was wrong. For anyone who habitually
falls asleep after midnight this fired nearly every day.

The query now asks for one day more and trims the answer back on `day`.

**2. The recovery score's resting-HR term was a hardcoded 0**
(`tools/intelligence_tools.py`)

Both callers of `interpret_recovery_state` passed `resting_hr_deviation=0` with
the comment *"we'd need to calculate this from baseline"*. The term
`max(0, 100 - abs(dev) * 10) * 0.10` therefore contributed its full 10 points
every single day, and a red criterion such as "resting HR ≥ +5 bpm above
baseline" could never fire.

The control that exposed it is cheap and should have run much earlier: the
reported pulse moved 62 · 62 · 61 · 63 · 57 · 55 bpm over six days while the
reported deviation stayed 0 — and on a day with no pulse at all it still read 0.
The real values are +1.0 · +0.9 · +0.1 · +2.1 · −3.9 · −5.8.

It is now computed from `lowest_heart_rate` against its own 30-day baseline, and
`None` when it cannot be measured. A missing signal is excluded and the
remaining weights renormalised, so it widens the uncertainty instead of quietly
scoring full marks.

**3. A missing pulse rendered as `0` in `get_hrv_trend`** (`tools/debug_tools.py`)

Naps and short fragments return no `lowest_heart_rate` and an
`average_heart_rate` of 0, and the table printed that straight into a bpm
column:

```
| 2026-09-13 | — | 0 | 0h4m | — | — |
```

That row is a doze; the real night sat underneath it. Implausible pulses now
render as `—`, and any session too short to be a night is labelled
`*(Fragment)*` — labelled rather than dropped, because silently removing rows is
how the night went missing in the first place.

### ➕ Added
- `resting_hr.extract_resting_hr_series(..., long_sleep_only=True)`: on one
  measured day a `late_nap` reported 65 bpm and the `long_sleep` 61 bpm for the
  same date, so which value a "take the latest" caller saw depended on the order
  the API returned them in. The default is unchanged; whether the illness
  baseline should also exclude naps is a separate question with its own evidence.

### 🧪 Tests
27 → **60**. New: `test_sleep_window_off_by_one.py`,
`test_recovery_rhr_deviation.py`, `test_hrv_trend_zero_pulse.py`. Every fix was
accepted with a sabotage run — a deliberately broken copy that **must** fail the
new tests.

Three mistakes of my own during the work, each caught by a control rather than
by review, and each recorded in the test files:

- The first version of the score summed the same weights in a different order
  and moved an **unchanged** day from 78.1 to 78.2 (78.14999999999999 vs 78.15).
  The normal path is one literal expression again.
- The fixtures had one session per day, so the nap ambiguity could not appear in
  them — self-built test data shares the assumptions of its author. The live run
  found it.
- The leak test was **blind**: its candidate fell outside the widened window
  too, so "widen the query, delete the trim" stayed green. The real leak case is
  an evening doze that Oura dates to the next day.

### ⚠️ Known limits
- The RHR baseline is a plain mean over 30 days, so a run of elevated nights
  raises the reference along with the value. It detects a single bad night, not a
  slow drift.
- A sleep session without a `type` is **not** assumed to be the main night. That
  yields an admitted gap rather than a number that might be a nap.

---

## [0.8.0] - 2026-07-09

### 🎉 Added - Complete Oura v2 User-Data Coverage
- **Daily Resilience** (`get_daily_resilience`): long-term stress-recovery balance with level and sleep/daytime-recovery & stress contributors
- **Cardiovascular Age** (`get_daily_cardiovascular_age`): estimated vascular age (graceful message when the token scope is unavailable)
- **Sleep Time Recommendations** (`get_sleep_time`): optimal bedtime window plus per-day recommendation and status
- **Rest Mode Periods** (`get_rest_mode_periods`): user-activated recovery-mode periods with episodes
- **Enhanced Tags** (`get_enhanced_tags`): named tags with time ranges and comments
- **Ring Configuration** (`get_ring_configuration`): ring hardware details (color, design, firmware, size)

### 📝 Notes
- API coverage now ~98% of user-data endpoints (all six added above)
- **Webhooks** intentionally out of scope: they require OAuth application credentials (not the personal access token this server uses) and manage push delivery rather than readable user data — documented in `docs/DATA_COVERAGE.md`

---

## [0.5.0] - 2026-01-17

### 🎉 Added - Personalized Health Insights
- **Chronotype Analysis**: MSF-based scientific chronotype classification (Night Owl, Morning Lark, etc.)
  - Main sleep extraction from biphasic/polyphasic patterns
  - Social jetlag calculation
  - Weekday vs weekend comparison
  - Activity pattern correlation
  - Personalized recommendations by chronotype
- **Personal Sleep Need Calculation**: Auto-detection via readiness correlation
  - Method 1: Readiness correlation (top 25% performance days)
  - Method 2: Sleep score correlation
  - Method 3: Duration percentile (75th)
  - Fallback: Chronotype-based defaults
- **Adaptive Severity Thresholds**: All thresholds now scale to personal sleep need
  - New "elevated" severity level (between moderate and severe)
  - Scale factor pattern: `personal_need / 8.0`
  - Applied to sleep debt, duration alerts, consecutive nights

### 🐛 Fixed
- **Chronotype Misclassification**: Naps no longer skew bedtime averages
- **Consecutive Bad Nights**: Fixed false positives from aggregated sessions with score=0
  - Added efficiency-as-proxy logic when score unavailable
  - Dual criteria: score + duration deficit
- **RHR Data Type Confusion**: Clarified that RHR values are scores (0-100), not BPM
  - Inverted deviation logic (lower score = elevated HR)
  - Updated all reporting with clear labels

### 🔧 Changed
- **Sleep Debt Tracker**: Now auto-detects personal sleep need (no hardcoded 8h)
- **Alert System**: Constructor accepts `personal_sleep_need` parameter
- **Chronotype Analyzer**: Works with raw sessions (not aggregated)
- **Intelligence Tools**: Pass raw sessions to chronotype analyzer

### 📚 Documentation
- Created comprehensive v0.5.0 release notes
- Updated README.md with chronotype examples
- Added scientific basis documentation (MSF methodology)

### ✅ Testing
- Validated with 30+ days of real biphasic sleep data
- Tested night owl chronotype detection
- Verified readiness correlation accuracy
- Confirmed threshold scaling correctness

---

## [0.3.1] - 2026-01-17

### 🏗️ Changed - Major Code Refactoring
- **Modular Architecture**: Reorganized codebase into clean, maintainable modules
- **server.py**: Reduced from 1,856 to 930 lines (50% reduction)
- **Provider Pattern**: Extracted business logic into dedicated provider classes
  - Created `resources/metrics_resources.py` (132 lines)
  - Created `tools/data_tools.py` (408 lines)
  - Created `tools/intelligence_tools.py` (333 lines)
  - Created `tools/debug_tools.py` (114 lines)

### 🐛 Fixed
- **Stress Data Type Safety**: Added `isinstance()` check for `day_summary` to prevent AttributeError
- **VO2 Max Error Handling**: Graceful handling of API 404 with informative user message

### 📚 Documentation
- Updated README.md with new module structure
- Created comprehensive v0.3.1 release notes
- Added refactoring documentation

### ✅ Testing
- All tests pass (100% coverage maintained)
- No breaking changes - fully backward compatible

---

## [0.3.0] - 2025-01-15

### 🎉 Added - Complete Oura API v2 Coverage
- **Sleep Sessions**: Detailed sleep/wake times with biphasic/polyphasic tracking
- **Heart Rate Data**: Time-series HR with zones and activity breakdown
- **Workout Sessions**: Complete workout history with metrics
- **Stress Tracking**: Daily stress levels and recovery time
- **SpO2 Monitoring**: Blood oxygen saturation data
- **VO2 Max**: Cardiorespiratory fitness estimates
- **User Tags**: Custom notes and activity tracking

### 📚 Documentation
- Added comprehensive v0.3.0 release notes
- Updated API documentation

---

## [0.2.1] - 2025-01-14

### 🐛 Fixed
- Sleep sessions tool now correctly handles multiple periods per day
- Improved error messages for missing data

---

## [0.2.0] - 2025-01-12

### 🎉 Added - Intelligence Features
- **Baseline Tracking**: 30-day rolling averages for all metrics
- **Recovery Detection**: Multi-signal recovery assessment
- **Training Readiness**: Sport-specific recommendations
- **Anomaly Detection**: Statistical detection of concerning patterns
- **Correlation Analysis**: Discover relationships between metrics
- **HRV Insights**: Detailed HRV analysis with baseline comparison

### 📚 Documentation
- Added Phase 2 Quick Start Guide
- Added Implementation Summary
- Added comprehensive test results

---

## [0.1.0] - 2025-01-05

### 🎉 Added - Initial Release
- **MCP Server**: Basic Model Context Protocol implementation
- **Oura API Client**: v2 API integration with rate limiting
- **Resources**: Sleep, readiness, activity, HRV
- **Tools**: Daily health brief, sleep trend analysis
- **Configuration**: YAML-based config with environment variables
- **Caching**: Smart caching system with TTL
- **Logging**: Structured logging with rotation
- **Docker**: Docker and docker-compose support

### 🔒 Security
- Environment-based token storage
- Audit logging of all requests
- Configurable access levels

### 📚 Documentation
- Complete README with examples
- Docker documentation
- MCP design documentation
- API research documentation

---

## Version History

- **v0.3.1** (2026-01-17): Code refactoring & modular architecture
- **v0.3.0** (2025-01-15): Complete Oura API v2 coverage
- **v0.2.1** (2025-01-14): Bug fixes for sleep sessions
- **v0.2.0** (2025-01-12): Intelligence features (recovery, training, correlations)
- **v0.1.0** (2025-01-05): Initial release (MVP)

---

## Links

- **Repository**: https://github.com/schimmmi/oura-mcp-server
- **Issues**: https://github.com/schimmmi/oura-mcp-server/issues
- **Releases**: https://github.com/schimmmi/oura-mcp-server/releases
