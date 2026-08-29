# Oura MCP Server - Setup Guide

## 🚀 Quick Start

### 1. Get Your Oura Access Token

1. Go to [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens)
2. Sign in with your Oura account
3. Create a new Personal Access Token
4. Copy the token (you'll only see it once!)

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your token
nano .env
```

Add your token:
```
OURA_ACCESS_TOKEN=YOUR_TOKEN_HERE
```

### 3. Create Configuration File

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Optional: Customize settings
nano config/config.yaml
```

### 4. Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Test the Server

```bash
# Run the server
python main.py
```

The server will start in stdio mode, waiting for MCP protocol messages.

## 🔧 Configuration

### Basic Configuration

The `config/config.yaml` file controls all server behavior:

```yaml
oura:
  api:
    access_token: "${OURA_ACCESS_TOKEN}"  # Reads from .env
  cache:
    enabled: true
    ttl_seconds: 3600  # Cache data for 1 hour
  security:
    access_level: "full"  # summary | standard | full
    audit_logging: true

mcp:
  server:
    name: "Oura Health MCP"
    transport: "stdio"
  resources:
    enabled:
      - "sleep"
      - "readiness"
      - "activity"
      - "hrv"
      - "metrics"
  tools:
    enabled:
      - "generate_daily_brief"
      - "analyze_sleep_trend"
```

### Access Levels

- **summary**: Only high-level scores, no detailed metrics
- **standard**: Scores + aggregated data, no raw sensor data
- **full**: Complete access to all data (default)

## 🤖 Using with AI Clients

### Claude Desktop

1. Find your Claude Desktop config:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add the Oura MCP server:

```json
{
  "mcpServers": {
    "oura": {
      "command": "python",
      "args": ["/absolute/path/to/oura-mcp-server/main.py"],
      "env": {
        "OURA_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

3. Restart Claude Desktop

4. Test with queries like:
   - "How did I sleep last night?"
   - "Show me my readiness for today"
   - "Generate my daily health brief"

### Other MCP Clients

The server uses standard stdio transport and works with any MCP-compatible client:

- **Cursor**: Add to MCP settings
- **Continue**: Configure in settings.json
- **Custom clients**: Connect via stdio transport

## 📊 Available Resources

### Sleep Resources

- `oura://sleep/today` - Last night's sleep
- `oura://sleep/yesterday` - Previous night's sleep

### Readiness Resources

- `oura://readiness/today` - Today's readiness score

### Activity Resources

- `oura://activity/today` - Today's activity data

## 🛠 Available Tools

### `generate_daily_brief`

Generate comprehensive daily health report.

**Usage in AI chat:**
```
Generate my daily health brief
```

### `analyze_sleep_trend`

Analyze sleep patterns over multiple days.

**Parameters:**
- `days` (optional, default: 7) - Number of days to analyze

**Usage in AI chat:**
```
Analyze my sleep trend for the last 7 days
```

## 🧪 Testing

### Manual Test

```bash
# Activate venv
source .venv/bin/activate

# Run server
python main.py
```

The server will wait for MCP protocol input. Press `Ctrl+C` to stop.

### Verify Configuration

```bash
# Check if config loads correctly
python -c "from src.oura_mcp.utils.config import get_config; print(get_config())"
```

### Test Oura API Access

```bash
# Test API connection
python -c "
import asyncio
from src.oura_mcp.api.client import OuraClient
from src.oura_mcp.utils.config import get_config

async def test():
    config = get_config()
    async with OuraClient(config.oura.api) as client:
        info = await client.get_personal_info()
        print(f'Connected! Age: {info.get(\"age\")}')

asyncio.run(test())
"
```

## 🔒 Security Best Practices

1. **Never commit tokens**: Keep `.env` and `config/config.yaml` out of git
2. **Use environment variables**: Store sensitive data in `.env`
3. **Enable audit logging**: Track what AI queries your data
4. **Limit access**: Use `access_level` to restrict data exposure
5. **Rotate tokens**: Periodically regenerate your Oura access token

## 🐛 Troubleshooting

### "Configuration file not found"

```bash
# Make sure you copied the example config
cp config/config.example.yaml config/config.yaml
```

### "Environment variable not set: OURA_ACCESS_TOKEN"

```bash
# Make sure .env file exists and contains token
cat .env

# If missing, create it
echo "OURA_ACCESS_TOKEN=your_token" > .env
```

### "Invalid access token"

- Check your token in [Oura Cloud](https://cloud.ouraring.com/personal-access-tokens)
- Make sure you copied the entire token
- Try generating a new token

### Rate limit errors

The server respects Oura's rate limits:
- 60 requests per minute
- 5000 requests per day

If you hit limits, the server will automatically slow down.

## 📈 Next Steps

1. **Test resources**: Query your sleep, readiness, and activity data
2. **Try tools**: Use analysis tools for insights
3. **Customize**: Adjust config for your needs
4. **Extend**: Add custom resources or tools (see [MCP_DESIGN.md](MCP_DESIGN.md))

## 🆘 Getting Help

- **Documentation**: See the [docs/](.) folder
- **API Reference**: [Oura API Docs](https://cloud.ouraring.com/v2/docs)
- **MCP Protocol**: [Model Context Protocol](https://modelcontextprotocol.io)

## 🎯 Example Queries

Once configured with an AI client, try:

- "How did I sleep last night?"
- "What's my readiness score today?"
- "Show me my activity for today"
- "Generate my daily health brief"
- "Analyze my sleep trend for the last week"
- "Am I recovered enough for a hard workout?"

Enjoy your personal health AI! 🎉
