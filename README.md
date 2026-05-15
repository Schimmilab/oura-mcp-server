# Oura MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with structured, semantic access to your Oura Ring health data.

## Features

### 📊 Raw HRV Data Access (v0.7.0) ✅
- **Raw HRV Trend**: `get_hrv_trend` — retrieves `average_hrv` in real milliseconds from the detailed sleep endpoint (not score-based), with resting HR (lowest nightly value), sleep stages, and automatic trend analysis across configurable time windows (NEW in v0.7.0)

## Features

### 🍽️ Nutrition Intelligence (v0.6.0) ✅
- **Calorie Needs Prediction**: 7-day TDEE forecasts based on activity patterns (NEW in v0.6.0)
- **Flexible Macro Planning**: Choose from 9 nutrition styles OR set custom carb limits (NEW in v0.6.0)
- **BMR & TDEE Calculation**: Mifflin-St Jeor formula with Oura activity integration (NEW in v0.6.0)
- **Weekly Pattern Analysis**: Day-of-week calorie expenditure patterns (NEW in v0.6.0)
- **Personalized Recommendations**: Protein/carb/fat targets based on your approach (NEW in v0.6.0)

### 🧠 Health Intelligence (v0.5.0) ✅
- **Chronotype Analysis**: MSF-based classification (Night Owl, Morning Lark) with personalized recommendations
- **Personalized Sleep Need**: Auto-detection via readiness correlation - no more one-size-fits-all 8h target
- **Analytics**: Comprehensive statistical reports with correlations and trend detection
- **Predictions**: 7-day forecasts for sleep, readiness, and activity with ensemble learning
- **Sleep Optimization**: Optimal bedtime calculator and personalized sleep debt tracking
- **Supplement Analysis**: Correlation tracking between supplements and health metrics
- **Illness Detection**: Multi-signal early warning system (1-2 day advance notice)
- **Health Alerts**: Automated monitoring with personalized, adaptive thresholds
- **Weekly Reports**: Comprehensive summaries with week-over-week comparisons
- **Recovery Detection**: Multi-signal recovery assessment with weighted scoring
- **Training Readiness**: Sport-specific recommendations (general, endurance, strength, HIIT)
- **Anomaly Detection**: Statistical detection of concerning patterns

### 📊 Data Access Tools (v0.3.0+) ✅
- **Detailed Sleep Sessions**: Exact sleep/wake times, biphasic/polyphasic tracking
- **Heart Rate Monitoring**: Time-series data with HR zones and activity breakdown
- **Workout Sessions**: Complete workout history with metrics
- **Stress & Recovery**: Daily stress levels and recovery time tracking
- **SpO2 Monitoring**: Blood oxygen saturation trends
- **VO2 Max**: Cardiorespiratory fitness estimates
- **User Tags**: Custom notes and activity tracking

### 🏥 Health Resources (v0.2.0+) ✅
- **Sleep Analysis**: Detailed sleep stages, efficiency, scores
- **Readiness Metrics**: HRV, temperature, recovery indicators
- **Activity Tracking**: Steps, calories, activity scores
- **HRV Insights**: Baseline comparison and trend detection
- **Personal Info**: Age, weight, height, biological sex

### 🔧 Core Features ✅
- **Modular Architecture**: Clean separation of concerns (v0.3.1)
- **Smart Caching**: Respects Oura API rate limits
- **Privacy Controls**: Configurable access levels and audit logging
- **Comprehensive Testing**: 100% test coverage for all features

## Project Structure

```
oura-mcp-server/
├── src/oura_mcp/
│   ├── api/
│   │   └── client.py              # Oura API v2 client
│   ├── core/
│   │   └── server.py              # MCP server orchestration (1,100+ lines)
│   ├── resources/                 # MCP Resources (health data endpoints)
│   │   ├── formatters.py          # Data formatting utilities
│   │   ├── health_resources.py    # Sleep, readiness, activity, HRV
│   │   └── metrics_resources.py   # Personal info, stress, SpO2
│   ├── tools/                     # MCP Tools (analysis functions)
│   │   ├── analytics_tools.py     # Statistics, sleep debt, supplements
│   │   ├── prediction_tools.py    # Forecasting with ensemble learning
│   │   ├── intelligence_tools.py  # Recovery, training, illness detection
│   │   ├── data_tools.py          # Data access (sessions, HR, workouts)
│   │   └── debug_tools.py         # Weekly reports and utilities
│   └── utils/
│       ├── sleep_aggregation.py   # Biphasic/polyphasic sleep handling
│       ├── chronotype_analysis.py # Chronotype detection (MSF-based)
│       ├── illness_detection.py   # Multi-signal illness warning system
│       ├── sleep_debt.py          # Sleep debt tracking with recovery
│       ├── baselines.py           # Baseline tracking (30-day averages)
│       ├── anomalies.py           # Anomaly detection engine
│       ├── interpretation.py      # Health insights interpreter
│       ├── config.py              # Configuration management
│       └── logging.py             # Structured logging
├── tests/
│   ├── test_server.py             # Basic server tests
│   ├── test_advanced_features.py  # Intelligence features tests
│   └── test_api.py                # API integration tests
├── docs/                          # Comprehensive documentation
├── config/                        # Configuration templates
└── main.py                        # Server entry point
```

## Quick Start

### Prerequisites
- Python 3.10+ (or Docker)
- Oura Ring with API access
- Personal Access Token from [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens)

### Option 1: Docker (Recommended)

```bash
# Set your token
export OURA_ACCESS_TOKEN="your_token_here"

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

**See [docs/DOCKER.md](docs/DOCKER.md) for complete Docker documentation.**

### Option 2: Local Python Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your Oura token
export OURA_ACCESS_TOKEN="your_token_here"

# Run the server
python main.py
```

### Configuration

Copy `config/config.example.yaml` to `config/config.yaml` and customize:

```yaml
oura:
  api:
    access_token: "${OURA_ACCESS_TOKEN}"
  cache:
    enabled: true
    ttl_seconds: 3600

mcp:
  server:
    name: "Oura Health MCP"
    transport: "stdio"
```

## Usage with AI Clients

### Claude Desktop

Add to your Claude config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "oura": {
      "command": "python",
      "args": ["/path/to/oura-mcp-server/main.py"]
    }
  }
}
```

### Example Queries

**Basic Queries:**
- "How did I sleep last night?"
- "What's my readiness score today?"
- "Give me my daily health brief"

**Detailed Data (NEW in v0.3.0):**
- "Show me my sleep sessions for the last 3 days"
- "What was my heart rate during my workout yesterday?"
- "Get my stress levels for the past week"
- "Show me my blood oxygen levels"
- "What's my VO2 Max?"
- "Show me the tags I created this week"

**Nutrition & Calorie Planning (NEW in v0.6.0):**
- "Predict my calorie needs for the next 7 days with max 30g carbs"
- "Show me my TDEE forecast with keto macros"
- "What's my calorie expenditure prediction with carnivore diet?"
- "Calculate my macro targets for next week with 50g carb limit"

**Chronotype & Sleep Optimization:**
- "What's my chronotype based on my sleep patterns?"
- "Calculate my personal sleep need using my readiness data"
- "What's my sleep debt and how long will recovery take?"
- "Calculate my optimal bedtime based on recent patterns"

**Analytics & Statistics:**
- "Generate a statistics report for the last 30 days"
- "Does my magnesium supplement improve my sleep quality?"
- "Show me a comprehensive weekly health report"

**Predictions & Intelligence:**
- "Predict my sleep quality for the next 7 days"
- "Forecast my readiness and activity scores for this week"
- "Am I at risk of getting sick? Check for early warning signs"
- "Generate health alerts for any concerning trends"

**Recovery & Training:**
- "Am I recovered enough for a hard workout today?"
- "Assess my readiness for high-intensity training"
- "What's my HRV trend over the last week?"
- "Is there a correlation between my sleep and activity levels?"
- "Are there any concerning anomalies in my recent data?"

## Development

```bash
# Run all tests
python3 tests/test_advanced_features.py

# Run API tests
python3 tests/test_api.py

# Run server tests
python3 tests/test_server.py

# Run with debug logging
python main.py --log-level debug

# Type checking
mypy src/

# Linting
ruff check src/
```

## Documentation

- **[v0.6.0 Release Notes](releases/v0.6.0_RELEASE_NOTES.md)** - Nutrition intelligence & calorie forecasting (NEW)
- **[v0.5.0 Release Notes](releases/v0.5.0_RELEASE_NOTES.md)** - Personalized health insights
- **[v0.4.0 Release Notes](releases/v0.4.0_RELEASE_NOTES.md)** - Complete v0.4.0 documentation
- **[Phase 2 Quick Start Guide](docs/PHASE2_QUICKSTART.md)** - User guide for intelligence features
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Complete Phase 2 documentation
- **[MCP Design](docs/MCP_DESIGN.md)** - Architecture and design documentation
- **[Release Notes](docs/RELEASE_NOTES.md)** - Version history and changelog
- **[Bug Fixes](docs/BUGFIXES.md)** - Known issues and fixes
- **[Oura API Research](docs/OURA_API_RESEARCH.md)** - API documentation
- **[Test Results](docs/TEST_RESULTS.md)** - Test validation results

## Security

- Tokens stored in environment variables only
- Audit logging of all MCP requests
- Configurable access levels (summary/standard/full)
- Local-only data processing

## Roadmap

- [x] **v0.1.0 - v0.2.0**: Core MVP (basic resources + authentication)
- [x] **v0.3.0**: Complete API coverage (all Oura v2 endpoints) ✅ **2025-01-15**
- [x] **v0.3.1**: Code refactoring & modular architecture ✅ **2026-01-17**
- [x] **v0.4.0**: Health intelligence platform (analytics, predictions, illness detection) ✅ **2026-01-17**
- [x] **v0.5.0**: Personalized health insights (chronotype, adaptive thresholds) ✅ **2026-01-17**
- [x] **v0.6.0**: Nutrition intelligence & calorie forecasting ✅ **2026-01-18**

## License

MIT

## Contributing

This is a personal project, but suggestions and improvements are welcome via issues.
