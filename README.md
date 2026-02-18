# eMCP

**Tool Access Broker for MCP systems.** Filters which tools AI agents can access to reduce token costs and cognitive overhead.

Every enabled MCP tool consumes tokens. eMCP sits between your AI agent and your MCP servers, letting you control exactly which tools are exposed through a web UI.

## Architecture

```
AI Agent
    |
    v
eMCP Gateway (MCPJungle)     <-- Aggregates servers, filters by group
    |         |
    v         v
  MCP       MCP              <-- Your MCP servers
 Server    Server
```

| Service | Port | Purpose |
|---------|------|---------|
| `emcp-server` | 8090 | MCPJungle gateway - aggregates servers, routes tool calls |
| `emcp-manager` | 5010 | Web UI for tool selection and server management |
| `db` | 5432 | PostgreSQL for gateway state |

## Quick Start

```bash
git clone https://github.com/IMUR/eMCP.git
cd eMCP

cp .env.example .env
# Edit .env — set POSTGRES_USER and POSTGRES_PASSWORD

mkdir -p demo-data
echo "eMCP is running" > demo-data/readme.txt

make up
```

Open **http://localhost:5010** — the web UI shows available tools from the included demo server.

## Adding MCP Servers

### Via Web UI

1. Open http://localhost:5010
2. Click **Add MCP Server**
3. Enter a GitHub repo URL, npm package, or Docker image
4. Configure and provision

### Manually

1. Add a service to `docker-compose.yaml`
2. Create a config in `configs/<name>.json`
3. `docker compose up -d <name>`
4. `docker exec emcp-server /mcpjungle register -c /configs/<name>.json`

See [`examples/README.md`](examples/README.md) for a complete walkthrough.

## Group System

Groups control which tools are exposed. Each group is a JSON file in `groups/`:

```json
{
    "name": "my-group",
    "description": "Tools for my workflow",
    "included_tools": ["server__tool_name"]
}
```

Access a group's MCP endpoint at: `http://localhost:8090/v0/groups/{group-name}/mcp`

Manage groups via the web UI or by editing the JSON files directly.

## Secret Management

Secrets are stored in a `.env` file (never committed to git):

```bash
cp .env.example .env
```

The `.env` file is created with restricted permissions. Add API keys for any MCP servers you configure. See `.env.example` for the format.

## Systemd Integration

For automatic container reloads when adding servers via the web UI:

```bash
cd systemd
sudo ./install.sh
```

## Make Targets

```
make help       Show all targets
make up         Start all services
make down       Stop all services
make restart    Restart all services
make logs       Tail gateway logs
make status     Service health + tool count
make register   Re-register all configs with MCPJungle
make clean      Remove containers, volumes, runtime data
```

## API

```bash
curl http://localhost:5010/api/tools      # All available tools
curl http://localhost:5010/api/current    # Current tool selection
curl http://localhost:5010/api/servers    # Registered servers
```

## License

[MIT](LICENSE)
