# Release Notes

## Version 0.2.0 - Phase 2: Intelligence Layer (2025-12-25)

### 🎉 Major New Features

#### Docker Support 🐳 **NEW**
- **Dockerfile**: Multi-stage build for optimal image size (~200MB)
- **docker-compose.yml**: Easy deployment with one command
- **Makefile**: Convenient Docker commands (`make up`, `make logs`, etc.)
- **Full documentation**: See [DOCKER.md](../DOCKER.md)
- **Health checks**: Automatic container health monitoring
- **Resource limits**: Pre-configured CPU and memory limits
- **Non-root user**: Security-focused container design

#### Intelligence Core
- **BaselineManager**: 30-day rolling averages for personal baselines
- **InterpretationEngine**: Semantic interpretation of all health metrics
- **AnomalyDetector**: Statistical anomaly detection with severity classification

#### New MCP Resources
- `oura://hrv/latest` - Latest HRV with baseline comparison
- `oura://hrv/trend/7_days` - 7-day HRV trend analysis
- `oura://hrv/trend/30_days` - 30-day HRV trend analysis

#### New MCP Tools
1. **detect_recovery_status** - Multi-signal recovery assessment
   - Weighted scoring (HRV 35%, Readiness 30%, Sleep 20%, RHR 10%, Temp 5%)
   - Recovery state classification
   - Contributing signals breakdown
   - Training recommendations

2. **assess_training_readiness** - Sport-specific readiness assessment
   - Support for: general, endurance, strength, high_intensity
   - GO/NO-GO/CAUTION recommendations
   - Intensity & duration modifications
   - Limiting factors identification

3. **correlate_metrics** - Pearson correlation analysis
   - **All Oura metrics supported** (see below)
   - Strength classification (Strong/Moderate/Weak/None)
   - Statistical summaries
   - Relationship interpretation

4. **detect_anomalies** - Pattern & anomaly detection
   - Sleep & readiness anomalies
   - Severity classification (High/Medium/Low)
   - Possible causes identification
   - Personalized thresholds

### 📊 Supported Metrics for Correlation Analysis

**Sleep Metrics:**
- `sleep_score`, `deep_sleep`, `rem_sleep`, `light_sleep`
- `total_sleep`, `efficiency`, `restfulness`, `latency`, `timing`

**Readiness Metrics:**
- `readiness_score`, `hrv_balance`, `resting_heart_rate`, `body_temperature`
- `activity_balance`, `previous_day_activity`, `previous_night`
- `recovery_index`, `sleep_balance`, `sleep_regularity`

**Activity Metrics:**
- `activity_score`, `steps`, `total_calories`, `active_calories`

### 🐛 Bug Fixes
- Fixed `correlate_metrics` not recognizing sleep contributor metrics
- Added proper handling for all Oura API contributor scores
- Improved error messages for insufficient data

### 📚 Documentation
- Added `IMPLEMENTATION_SUMMARY.md` - Comprehensive Phase 2 documentation
- Added `PHASE2_QUICKSTART.md` - User guide for new features
- Added `BUGFIXES.md` - Bug tracking and known limitations
- Updated `README.md` with Phase 2 features
- Updated `MCP_DESIGN.md` with complete metric lists

### ✅ Testing
- 100% test success rate
- All features validated with real Oura data
- Test suite: `test_advanced_features.py`

### 🎯 Real-World Insights Discovered
- HRV ↔ Readiness: **+0.706** correlation (Strong positive)
- Deep Sleep anomaly detection: 49% below baseline detected
- Recovery scoring accuracy validated with personal data

### 🚀 Performance
- Efficient baseline calculations
- Smart caching of API requests
- Rate limit compliance (60/min, 5000/day)

---

## Version 0.1.0 - Phase 1: Core MVP (2025-12-24)

### Initial Release Features

#### Core MCP Server
- stdio transport for Claude Desktop integration
- Async/await architecture
- Configuration via YAML + environment variables

#### Oura API Client
- OAuth2 Bearer token authentication
- Rate limiting (60 req/min, 5000 req/day)
- Comprehensive error handling
- Context manager lifecycle

#### MCP Resources
- `oura://sleep/today` - Today's sleep data
- `oura://sleep/yesterday` - Previous night's sleep
- `oura://readiness/today` - Today's readiness
- `oura://activity/today` - Today's activity

#### MCP Tools
- `generate_daily_brief` - Comprehensive health summary
- `analyze_sleep_trend` - Sleep pattern analysis
- `get_raw_sleep_data` - Debug tool for raw API data

#### Semantic Formatting
- Human-readable health reports
- Score interpretations
- Duration formatting
- Edge case handling (zero values, missing data)

### Documentation
- `README.md` - Project overview and setup
- `SETUP.md` - Installation instructions
- `MCP_DESIGN.md` - Architecture documentation
- `OURA_API_RESEARCH.md` - API documentation
- `TEST_RESULTS.md` - Test validation

### Testing
- `test_api.py` - Oura API connectivity tests
- `test_server.py` - MCP server functionality tests
- All tests passed with real data

---

## Upgrade Guide

### From 0.1.0 to 0.2.0

**No breaking changes!** All existing functionality remains compatible.

**New capabilities:**
1. Update your Claude Desktop config (optional - server auto-discovers new tools)
2. Start asking intelligence-focused questions
3. Explore correlations in your data
4. Get training recommendations

**Example queries to try:**
```
"Am I recovered enough for training today?"
"What's my HRV trend this week?"
"Correlate my deep_sleep with sleep_score"
"Detect anomalies in my recent data"
```

**Configuration updates:**
- No changes required to existing `config.yaml`
- All new tools enabled by default
- New resources automatically available

---

## Roadmap

### Phase 3: Advanced (Planned)
- Sleep debt calculator
- Recovery time predictions
- Pattern recognition (weekly cycles, seasonal)
- Personalized recommendation engine
- Export capabilities (JSON, CSV, PDF)

### Phase 4: Polish (Future)
- Comprehensive unit tests
- Integration test suite
- Redis caching support
- SQLite audit logging
- Performance optimization
- Enhanced documentation

---

## Contributing

This is a personal project, but suggestions are welcome via:
- GitHub Issues for bug reports
- Feature requests via discussions
- Documentation improvements via PRs

---

## License

MIT License - See LICENSE file

---

## Credits

Built with:
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) by Anthropic
- [Oura Ring API v2](https://cloud.ouraring.com/v2/docs)
- Python 3.10+
- Love for data-driven health optimization

Developed using Claude Code and real Oura Ring data.

---

## Quick Links

- **[Phase 2 Quick Start Guide](../PHASE2_QUICKSTART.md)** - Get started with new features
- **[Implementation Summary](../IMPLEMENTATION_SUMMARY.md)** - Detailed technical documentation
- **[MCP Design](../MCP_DESIGN.md)** - Architecture documentation
- **[Bug Fixes](../BUGFIXES.md)** - Known issues and fixes
- **[Test Results](../TEST_RESULTS.md)** - Validation results
