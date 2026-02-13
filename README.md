# eMCP

**Tool Access Broker for MCP systems.** Filters which tools AI agents can access to reduce context overhead and token costs.

Every enabled MCP tool consumes tokens and adds cognitive overhead for AI agents. eMCP sits between your AI agent and your MCP servers, letting you control exactly which tools are exposed.

## Architecture

```
AI Agent (Claude, etc.)
    |
    v
eMCP Gateway (MCPJungle)     <-- Aggregates MCP servers, filters by group
    |         |
    v         v
  MCP       MCP              <-- Individual MCP servers (GitHub, Perplexity, etc.)
 Server    Server
```

**Components:**

| Service | Port | Purpose |
|---------|------|---------|
| `emcp-server` | 8090 | MCPJungle gateway - aggregates servers, routes tool calls, manages groups |
| `emcp-manager` | 5010 | Web UI and API for tool selection and server management |
| `db` | 5432 | PostgreSQL for MCPJungle state |

## Quick Start

```bash
# Clone
git clone https://github.com/IMUR/eMCP.git
cd eMCP

# Configure
cp .env.example .env
# Edit .env with your POSTGRES_USER and POSTGRES_PASSWORD

# Create demo data directory
mkdir -p demo-data
echo "eMCP is running!" > demo-data/readme.txt

# Start
docker compose up -d
```

Open http://localhost:5010 to access the eMCP Manager dashboard.

The demo includes a **filesystem MCP server** that requires no API keys. You should see its tools appear in the dashboard.

## Adding MCP Servers

eMCP ships with one demo server. To add real MCP servers:

### Via Web UI

1. Open http://localhost:5010
2. Click "Add MCP Server"
3. Enter a GitHub repo URL, npm package, or Docker image
4. Follow the prompts to configure and provision

### Manually

1. Add the service to `docker-compose.yaml`
2. Create a config in `configs/<name>.json`
3. Start: `docker compose up -d <service-name>`
4. Register: `docker exec emcp-server /mcpjungle register -c /configs/<name>.json`

See the [`examples/`](examples/) directory for ready-to-use configurations for GitHub, Perplexity, Gitea, ElevenLabs, Mapbox, and more.

## Group System

Groups control which tools are exposed to AI agents. Each group is a JSON file in `groups/`:

```json
{
    "name": "my-group",
    "description": "Tools for my workflow",
    "included_tools": [
        "github__create_issue",
        "github__search_code",
        "perplexity__perplexity_ask"
    ]
}
```

MCPJungle exposes groups at: `http://localhost:8090/v0/groups/{group-name}/mcp`

The default group is `emcp-global`. Manage groups via the web UI or by editing the JSON files directly.

## Secret Management

eMCP supports two methods for managing secrets:

### Option A: `.env` file (simple)

```bash
cp .env.example .env
# Add your secrets
```

### Option B: Infisical (recommended for production)

1. Install Infisical CLI
2. Configure `.infisical.json` with your workspace
3. Add secrets at path `/emcp`
4. Run `./scripts/start-emcp.sh` (auto-fetches from Infisical)

The startup script falls back to `.env` if Infisical is unavailable.

## Systemd Integration

For automatic container reloads when adding servers via the web UI:

```bash
cd systemd
sudo ./install.sh
```

This installs a path watcher that runs `docker compose up -d` when the web UI provisions a new server.

## Directory Structure

```
eMCP/
├── configs/          # MCPJungle server configs
├── dockerfiles/      # Gateway Dockerfile
├── emcp-manager/     # Flask web UI + API
├── examples/         # Example server configurations
├── groups/           # Tool group definitions
├── scripts/          # Start/stop/validation scripts
├── systemd/          # Systemd units for auto-reload
└── docker-compose.yaml
```

## API

```bash
# List all available tools
curl http://localhost:5010/api/tools

# Get current tool selection
curl http://localhost:5010/api/current

# List registered servers
curl http://localhost:5010/api/servers
```

## Re-registering Tools

If tools go missing after a restart:

```bash
python3 scripts/re-register-tools.py
```

## License

[MIT](LICENSE)
