# Oura MCP Server

A Model Context Protocol (MCP) server that provides AI assistants with structured, semantic access to your Oura Ring health data.

## Features

**30 tools** across data access, analysis, prediction and reporting. Every name below is registered in the running server — the list is generated from `core/server.py`, not maintained by hand.

### 📥 Data access

| Tool | What it returns |
|---|---|
| `get_sleep_sessions` | Detailed sessions with exact times and durations, including naps and couch sleep |
| `get_raw_sleep_data` | Raw sleep payload for debugging |
| `get_heart_rate_data` | Time-series heart rate with zones and activity breakdown |
| `get_hrv_trend` | Raw HRV in **milliseconds** (`average_hrv`), not the score — plus resting HR and sleep stages |
| `get_workout_sessions` | Workout and activity sessions with HR data and metrics |
| `get_daily_stress` | Stress levels, stress load and recovery time |
| `get_daily_resilience` | Long-term stress-recovery balance and its contributors |
| `get_daily_cardiovascular_age` | Estimated vascular age |
| `get_spo2_data` | Blood oxygen saturation trends |
| `get_vo2_max` | Cardiorespiratory fitness estimates |
| `get_sleep_time` | Optimal bedtime window and recommendation |
| `get_rest_mode_periods` | User-activated recovery mode |
| `get_tags` / `get_enhanced_tags` | User notes; enhanced adds time ranges and comments |
| `get_ring_configuration` | Hardware: colour, design, firmware, size |

### 🧠 Analysis

| Tool | What it does |
|---|---|
| `analyze_sleep_trend` | Sleep patterns over a chosen period |
| `analyze_sleep_debt` | Accumulated debt with severity and recovery advice |
| `analyze_chronotype` | Morning lark / night owl / intermediate, from sleep timing |
| `analyze_supplement_correlation` | Which tagged supplements and interventions actually moved the metrics |
| `correlate_metrics` | Correlation between any two metrics |
| `detect_anomalies` | Statistical outliers in recent data |
| `detect_illness_risk` | Multi-signal early warning (temperature, HRV, resting HR, respiratory rate) |
| `detect_recovery_status` | Recovery state from several physiological signals |
| `assess_training_readiness` | Readiness for a specific training type |
| `check_health_alerts` | Critical alerts and warnings from recent metrics and trends |
| `calculate_optimal_bedtime` | Derived from your own best nights |

### 🔮 Prediction

| Tool | What it forecasts |
|---|---|
| `predict_sleep_quality` | Upcoming nights, via trend / moving average / weekly pattern |
| `predict_readiness` | Readiness scores and training recommendations |
| `predict_calorie_needs` | TDEE with macro recommendations across 9 nutrition styles or a custom carb limit |

### 📄 Reports

| Tool | Output |
|---|---|
| `generate_daily_brief` | Daily health brief |
| `generate_weekly_report` | Weekly report with trends, highlights and week-over-week comparison |
| `generate_statistics_report` | Statistical analysis with trends and patterns |

### 🏥 Health resources

Sleep analysis, readiness metrics, activity tracking, HRV insights and personal info are also exposed as MCP **resources**, not just tools.

### 🔧 Core

- **OAuth2** with automatic token refresh — Oura refresh tokens are single-use, so rotation is serialised with a file lock and written atomically (see [Authentication](#authentication-oauth2))
- **Modular architecture**: API layer, tools, resources and utilities are separated
- **Smart caching** that respects Oura API rate limits
- **Privacy controls**: configurable access levels and audit logging
- **Tests**: 27 unit tests covering the token lifecycle and resting-heart-rate handling. Three live smoke scripts against the real API are run manually — see `tests/conftest.py`. Coverage is **not** complete; the analysis and prediction layers are largely untested.

### Version history

| Version | What it brought |
|---|---|
| **v0.9.3** | Sleep score never reached the checks that needed it — two alerts could never fire. Alerts now report checks they had to skip |
| **v0.9.2** | Three more surfaces still printed the resting-HR score as bpm |
| **v0.9.1** | Resting-HR alarm was inverted: it fired on recovery and stayed silent during illness |
| **v0.9.0** | OAuth2 migration (Oura deprecated Personal Access Tokens) + three silent API bugs |
| **v0.8.0** | Complete Oura v2 user-data coverage: resilience, cardiovascular age, sleep time, rest mode, enhanced tags, ring configuration |
| **v0.7.0** | Raw HRV in milliseconds via `get_hrv_trend` |
| **v0.6.0** | Nutrition intelligence: TDEE forecasting and macro planning |
| **v0.5.0** | Health intelligence: chronotype, illness detection, alerts, predictions |
| **v0.3.0** | Data access tools and modular architecture |
| **v0.2.0** | Health resources |

Full notes for every release: https://github.com/Schimmilab/oura-mcp-server/releases

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
- An OAuth2 application — see **Authentication** below

## Authentication (OAuth2)

> ⚠️ **Personal Access Tokens are deprecated.** Oura stopped issuing new ones in
> August 2026; existing tokens keep working for a while but will be switched off.
> This server uses the OAuth2 authorization code flow.

### 1. Register an application

Go to **https://developer.ouraring.com/applications** and create one.

| Field | What to put |
|---|---|
| Display Name | anything, e.g. `Oura MCP Server` |
| Description | e.g. `Self-hosted MCP server for my own Oura data` |
| Contact Email | your address |
| Website | your repo or homepage URL |
| Privacy Policy | a reachable URL — this repo's [PRIVACY.md](PRIVACY.md) works |
| Terms of Service | likewise [TERMS.md](TERMS.md) |
| **Redirect URIs** | **`http://localhost:8080/callback`** |
| Scopes | tick what you need — see the note below |

**On scopes:** this server never sends a `scope` parameter, because Oura grants
every scope the application is registered with when it is left blank. That keeps
the scope list in one place — the portal — instead of hard-coded where it can
drift out of sync. Tick `personal`, `daily`, `heartrate`, `workout`, `tag`,
`session`, `spo2` and ring configuration; `email` is not used by any tool.

💡 **Add a second redirect URI on a spare port** (e.g. `http://localhost:8321/callback`)
while you are there. Port 8080 is popular, and if something else is listening
when you re-authorize, the callback silently goes to that process instead. With a
second URI registered you just change `OURA_REDIRECT_URI` instead of hunting down
whatever holds the port.

### 2. Put the credentials in `.env`

```bash
OURA_CLIENT_ID=...
OURA_CLIENT_SECRET=...
OURA_REDIRECT_URI=http://localhost:8080/callback
```

`.env` is git-ignored. Keep the credentials **only here** — a second copy in an
MCP client config will shadow this file, because `load_dotenv` does not override
variables that are already set in the environment.

### 3. Authorize once

```bash
python generate_tokens.py
```

This opens the Oura consent screen, catches the redirect on a local HTTP server,
exchanges the code and writes `OURA_ACCESS_TOKEN` and `OURA_REFRESH_TOKEN` into
`.env` with mode 600. It then makes a real API call and tells you whether it
worked — a green message here means data actually came back, not just that a file
was written.

If the port is taken, the script says so and stops instead of letting the callback
disappear into another process.

### How tokens are kept alive

Access tokens are refreshed automatically. A `401` from the API triggers one
refresh and one retry; a second `401` means the credentials are dead rather than
stale, and the error tells you to re-run `generate_tokens.py`.

⛔ **Oura refresh tokens are single-use** — each refresh invalidates the previous
one. Two consequences the implementation handles for you:

- **Refreshes are serialized with a file lock** (`.env.lock`). Several server
  processes can run at once (one per client session, plus any cron jobs); without
  the lock two of them would spend the same single-use token and one would be left
  with a dead credential. Inside the lock the stored tokens are re-read first, so a
  rotation another process just completed is adopted instead of duplicated.
- **The new pair is written atomically** (temp file + `os.replace`). A crash
  mid-write would otherwise truncate the only copy of the new refresh token and
  force a manual re-authorization.

If you ever do end up locked out, `python generate_tokens.py` is always the way
back.

### Option 1: Docker (Recommended)

```bash
# Credentials come from .env (see Authentication above)
docker-compose up -d

# View logs
docker-compose logs -f
```

**See [docs/DOCKER.md](docs/DOCKER.md) for complete Docker documentation.**

### Option 2: Local Python Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Authorize once (see Authentication above)
python generate_tokens.py

# Run the server
python main.py
```

### Configuration

Copy `config/config.example.yaml` to `config/config.yaml` and customize:

```yaml
oura:
  api:
    # Resolved from .env — see Authentication above
    client_id: "${OURA_CLIENT_ID}"
    client_secret: "${OURA_CLIENT_SECRET}"
    access_token: "${OURA_ACCESS_TOKEN}"
    refresh_token: "${OURA_REFRESH_TOKEN}"
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
# Run the unit test suite
python3 -m pytest tests/ -q

# Live smoke scripts — these hit the real Oura API and need working
# credentials, so they are excluded from the suite and run by hand
python3 tests/test_api.py
python3 tests/test_server.py
python3 tests/test_advanced_features.py

# Run with debug logging
python main.py --log-level debug

# Type checking
mypy src/

# Linting
ruff check src/
```

## Documentation

- **[Release Notes](https://github.com/Schimmilab/oura-mcp-server/releases)** - Version history, one entry per release
- **[Phase 2 Quick Start Guide](docs/PHASE2_QUICKSTART.md)** - User guide for intelligence features
- **[Implementation Summary](docs/IMPLEMENTATION_SUMMARY.md)** - Complete Phase 2 documentation
- **[MCP Design](docs/MCP_DESIGN.md)** - Architecture and design documentation
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
- [x] **v0.7.0**: Raw HRV access in milliseconds ✅ **2026-05-15**
- [x] **v0.8.0**: Complete Oura v2 user-data coverage ✅ **2026-07-09**
- [x] **v0.9.0**: OAuth2 migration — Oura deprecated Personal Access Tokens ✅ **2026-08-29**
- [x] **v0.9.1 – v0.9.3**: Resting-heart-rate and sleep-score corrections ✅ **2026-08-29**
- [ ] **Next**: CI on push (there is none yet), and a sleep-consistency metric that
      does not floor at 0 for ordinary variation

## License

MIT

## Contributing

This is a personal project, but suggestions and improvements are welcome via issues.

## Maintainer

Schimmi — https://schimmilab.de
Issues und Pull Requests willkommen.
